# Firmware V1.009 download path and metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore recording downloads on BlackVue firmware V1.009+ cameras by fetching videos from the server root and thumbnail/GPS data from the `/vodMetadata` endpoint, while leaving legacy cameras unchanged.

**Architecture:** A single `legacy: bool` (produced by the existing `/accessible` probe) drives the download path. `get_dashcam_filenames` returns `(legacy, filenames)` so the flag reaches `download_recording`/`download_file` without a second probe. Non-legacy video downloads drop the `/Record/` prefix; non-legacy thumbnail/GPS come from a new `download_metadata_file` (POST + base64-decode); the `.3gf` accelerometer file is skipped on non-legacy firmware. The Flask mock gains root video serving and a `/vodMetadata` endpoint, and the test suite's expectations become legacy-aware.

**Tech Stack:** Python 3.9+ stdlib only (`base64` added; `json` already imported). Behave integration tests + Flask mock dashcam; pytest unit tests.

**User decisions (already made):**

- "B" -- recover thumbnail + GPS via `/vodMetadata`; skip `.3gf` on V1.009.
- ".3gf" skipped on the new API with a debug-level log ("get cracking" approved this).
- Terminology: "metadata" / "metadata file"; never "sidecar". Helper named `download_metadata_file`.
- No mention of reverse engineering / decompiling in any docs.

---

## Design refinement vs. spec

The spec (`2026-07-05-firmware-v1009-download-metadata.md`) proposed hoisting `is_legacy_camera()` into `sync()` and passing `legacy` as a parameter to `get_dashcam_filenames`. Implementation review found this breaks two unit tests that monkeypatch `get_dashcam_filenames` by name (the real `is_legacy_camera` would then fire against a dead address). This plan instead has `get_dashcam_filenames` **return** `(legacy, filenames)`, keeping the probe where it already lives and requiring no pytest changes. Behavior is identical; only the internal wiring differs.

## File structure

- `blackvuesync.py` -- the application. Adds `legacy` wiring, root video URL, `download_metadata_file`, `.3gf` skip.
- `features/mock_dashcam/server.py` -- mock dashcam. Adds root video route, `/vodMetadata`, and (for fidelity) makes `/Record/` reject non-legacy.
- `features/lib/recordings.py` -- adds one pure helper for legacy-aware expectations.
- `features/environment.py` -- one default (`context.legacy_api`).
- `features/steps/dashcam_recordings_steps.py` -- stores the legacy flag in context.
- `features/steps/downloaded_recordings_steps.py`, `features/steps/retry_failed_steps.py` -- apply the legacy-aware filter.
- `features/steps/metadata_content_steps.py` -- new, one byte-comparison assertion.
- `features/sync_api_parity.feature` -- one focused non-legacy scenario.
- `CHANGELOG.md` -- one entry.

---

### Task 1: Mock dashcam -- add V1.009 download endpoints

**Goal:** Give the mock the ability to serve videos from the root and thumbnail/GPS from `/vodMetadata`, without changing any existing behavior.

**Files:**

- Modify: `features/mock_dashcam/server.py`

**Acceptance Criteria:**

- [ ] A shared `_serve_recording_file(affinity_key, filename)` method holds the 404/500/`send_file` logic; `/Record/<filename>` uses it.
- [ ] `GET /<filename>` serves the video for non-legacy sessions, returns `415 mp4 only` for non-`.mp4` names, and honors configured download errors.
- [ ] `POST /vodMetadata` returns `{"resultcode":"BC_ERR_OK","thumbnail":"<base64>"}` for `thumbnail` and `{"resultcode":"BC_ERR_OK","metadata":{"gps":"<base64>"}}` for `gps`, base64-encoding the matching `mock.<ext>` fixture.
- [ ] The full existing suite still passes (new routes are unused by current code).

**Verify:** `behave` → all scenarios pass.

**Steps:**

- [ ] **Step 1: Add the base64 import**

In `features/mock_dashcam/server.py`, add `import base64` with the other stdlib imports (after `import datetime`):

```python
import base64
import datetime
```

- [ ] **Step 2: Extract the shared file-serving helper**

Add this method to `MockDashcam` (next to `_set_legacy_api`, before `_setup_routes`):

```python
    def _serve_recording_file(
        self, affinity_key: str, filename: str
    ) -> flask.Response:
        """serves the mock file for a recording, or aborts 404/500 as configured"""
        recordings = self._get_recordings(affinity_key)
        if filename not in recordings:
            logger.debug("Response: 404 Not Found (not in session recordings)")
            return flask.abort(404)

        download_errors = self._get_download_errors(affinity_key)
        if filename in download_errors:
            logger.debug("Response: 500 Internal Server Error (configured error)")
            flask.abort(500)

        if recording := to_recording(filename):
            files_dir = Path(__file__).parent / "files"
            filepath = files_dir / f"mock.{recording.extension}"
            if filepath.exists():
                logger.debug(
                    "Response: %s (%s bytes)", filepath.name, filepath.stat().st_size
                )
                return flask.send_file(filepath)

        logger.debug("Response: 404 Not Found")
        return flask.abort(404)
```

- [ ] **Step 3: Refactor `/Record/<filename>` to use the helper**

Replace the body of the `record` route (currently the recordings-check / download-errors / `to_recording` / `send_file` block) so it reads:

```python
        @self.app.route("/Record/<filename>", methods=["GET"])
        def record(filename: str) -> flask.Response:
            """serves any file associated to recordings"""
            logger.debug("GET /Record/%s", filename)
            affinity_key = self._get_affinity_key()
            return self._serve_recording_file(affinity_key, filename)
```

- [ ] **Step 4: Run the suite -- refactor is behavior-preserving**

Run: `behave`
Expected: all scenarios pass (the `/Record/` refactor changed nothing observable).

- [ ] **Step 5: Add the root video route and `/vodMetadata`**

Add both routes inside `_setup_routes` (e.g. right after the `record` route). The root route must be registered after the static routes it must not shadow -- it is, because all of `/accessible`, `/vodList`, `/blackvue_vod.cgi`, `/vodMetadata`, `/mock/...` are static and win over the single-segment converter.

```python
        @self.app.route("/vodMetadata", methods=["POST"])
        def vod_metadata() -> flask.Response | tuple[dict[str, Any], int]:
            """returns base64-encoded thumbnail/gps metadata (new style)"""
            logger.debug("POST /vodMetadata")
            affinity_key = self._get_affinity_key()
            if self._get_legacy_api(affinity_key):
                return flask.abort(404)

            data = flask.request.get_json() or {}
            logger.debug("Request body: %s", data)
            video_filename = data.get("file")
            types = data.get("types", [])
            metadata_type = types[0] if types else None

            recordings = self._get_recordings(affinity_key)
            extension = {"thumbnail": "thm", "gps": "gps"}.get(metadata_type)
            if video_filename not in recordings or extension is None:
                return {"resultcode": "BC_ERR_NG"}, 200

            files_dir = Path(__file__).parent / "files"
            encoded = base64.b64encode(
                (files_dir / f"mock.{extension}").read_bytes()
            ).decode("ascii")

            # thumbnail sits at the top level; gps is nested under "metadata"
            if metadata_type == "gps":
                return {"resultcode": "BC_ERR_OK", "metadata": {"gps": encoded}}, 200
            return {"resultcode": "BC_ERR_OK", "thumbnail": encoded}, 200

        @self.app.route("/<filename>", methods=["GET"])
        def root_record(filename: str) -> flask.Response:
            """serves videos from the root on V1.009; rejects non-mp4 with 'mp4 only'"""
            logger.debug("GET /%s", filename)
            affinity_key = self._get_affinity_key()
            if self._get_legacy_api(affinity_key):
                # legacy firmware serves downloads only under /Record/
                return flask.abort(404)
            if not filename.endswith(".mp4"):
                return flask.Response("mp4 only", status=415, mimetype="text/plain")
            return self._serve_recording_file(affinity_key, filename)
```

- [ ] **Step 6: Run the suite -- new routes are additive**

Run: `behave`
Expected: all scenarios pass (current blackvuesync still downloads via `/Record/`, so the new routes are unused).

- [ ] **Step 7: Commit**

```bash
git add features/mock_dashcam/server.py
git commit -m "test: add V1.009 root video and vodMetadata routes to mock dashcam"
```

---

### Task 2: Legacy-aware test expectations

**Goal:** Make the shared "recordings downloaded" assertions expect no `.3gf` on non-legacy cameras (the default), so the suite stays correct once blackvuesync stops fetching it.

**Files:**

- Modify: `features/environment.py`
- Modify: `features/steps/dashcam_recordings_steps.py:116-125`
- Modify: `features/lib/recordings.py`
- Modify: `features/steps/downloaded_recordings_steps.py:90-125`
- Modify: `features/steps/retry_failed_steps.py:68-83`

**Acceptance Criteria:**

- [ ] `context.legacy_api` defaults to `False` and is set to the scenario's value by the `the dashcam is legacy:` step.
- [ ] A pure `filter_available_metadata_filenames(filenames, legacy)` drops `.3gf` entries when `legacy` is `False`.
- [ ] `all the recordings are downloaded` and `the successful recordings are downloaded` both apply the filter.
- [ ] The full existing suite still passes.

**Verify:** `behave` → all scenarios pass.

**Steps:**

- [ ] **Step 1: Default `context.legacy_api` in `before_scenario`**

In `features/environment.py`, next to the existing `context.skip_metadata = set()` line, add:

```python
    # legacy_api defaults to False (current firmware); the legacy step overrides it
    context.legacy_api = False
```

- [ ] **Step 2: Store the flag in the legacy step**

In `features/steps/dashcam_recordings_steps.py`, update `dashcam_legacy_api` to record the flag in context:

```python
@given("the dashcam is legacy: {legacy_api}")
def dashcam_legacy_api(context: Context, legacy_api: str) -> None:
    """configures whether the mock dashcam serves the legacy blackvue_vod.cgi index."""
    context.legacy_api = legacy_api.lower() == "true"
    url = f"{context.mock_dashcam_url}/mock/legacy-api"
    headers = {"X-Affinity-Key": context.scenario_token}
    data = {"legacy_api": context.legacy_api}

    response = requests.post(url, json=data, headers=headers, timeout=10)
    response.raise_for_status()
```

- [ ] **Step 3: Add the pure filter helper**

In `features/lib/recordings.py`, add (e.g. after `get_mock_file_for_extension`):

```python
def filter_available_metadata_filenames(
    filenames: list[str] | set[str], legacy: bool
) -> set[str]:
    """returns the filenames a camera actually serves.

    V1.009+ (non-legacy) cameras have no accelerometer endpoint, so .3gf files
    are never retrievable there.
    """
    if legacy:
        return set(filenames)
    return {filename for filename in filenames if not filename.endswith(".3gf")}
```

- [ ] **Step 4: Apply the filter in `all the recordings are downloaded`**

In `features/steps/downloaded_recordings_steps.py`, import the helper and filter `expected_recordings` before the skip-metadata filtering. Update the import near the top:

```python
from features.lib.recordings import (
    create_recording_files,
    filter_available_metadata_filenames,
)
```

and change the expected-set construction inside `assert_all_recordings_downloaded`:

```python
    # gets expected recordings, dropping metadata the camera can't serve
    expected_recordings = filter_available_metadata_filenames(
        context.expected_recordings, context.legacy_api
    )
```

(Leave the subsequent `skip_extensions` block exactly as-is; it further narrows this set.)

- [ ] **Step 5: Apply the filter in `the successful recordings are downloaded`**

In `features/steps/retry_failed_steps.py`, add the import:

```python
from features.lib.recordings import filter_available_metadata_filenames
```

and update the `successful` set in `assert_successful_recordings_downloaded`:

```python
    failed: set[str] = getattr(context, "failed_recordings", set())
    available = filter_available_metadata_filenames(
        context.expected_recordings, context.legacy_api
    )
    successful = {f for f in available if f not in failed}
```

- [ ] **Step 6: Run the suite**

Run: `behave`
Expected: all scenarios pass. (`.3gf` is still fetched via `/Record/` by current blackvuesync, so it is present but no longer *required* -- `has_items` is a subset check.)

- [ ] **Step 7: Commit**

```bash
git add features/environment.py features/steps/dashcam_recordings_steps.py features/lib/recordings.py features/steps/downloaded_recordings_steps.py features/steps/retry_failed_steps.py
git commit -m "test: make recording expectations legacy-aware for .3gf"
```

---

### Task 3: blackvuesync -- non-legacy download path

**Goal:** Download videos from the root and thumbnail/GPS from `/vodMetadata` on non-legacy cameras, skip `.3gf` there, and make the mock reject `/Record/` on non-legacy so the change is actually exercised.

**Files:**

- Modify: `blackvuesync.py` (imports; `get_dashcam_filenames:803-819`; `download_file:960-1024`; `download_recording:1112-1187`; `sync:1471-1493`)
- Modify: `features/mock_dashcam/server.py` (`record` route)

**Acceptance Criteria:**

- [ ] `get_dashcam_filenames` returns `(legacy, filenames)`; `sync` unpacks it and threads `legacy` into every `download_recording`.
- [ ] `download_file` builds the URL at the root when `legacy` is `False`, and under `Record/` when `True`.
- [ ] On non-legacy cameras, thumbnail and GPS are fetched via `download_metadata_file` (POST `/vodMetadata`, base64-decoded), gated by `--skip-metadata` `t`/`g`; `.3gf` is skipped with a `logger.debug` note.
- [ ] The mock returns `400` for `/Record/<filename>` on non-legacy sessions.
- [ ] `behave` and `behave -D implementation=docker` pass; `pytest test/blackvuesync_test.py` passes unchanged.

**Verify:** `behave && pytest test/blackvuesync_test.py -q`

**Steps:**

- [ ] **Step 1: Make the mock reject `/Record/` on non-legacy (the failing setup)**

In `features/mock_dashcam/server.py`, add a legacy guard to the `record` route so V1.009 sessions no longer serve `/Record/`:

```python
        @self.app.route("/Record/<filename>", methods=["GET"])
        def record(filename: str) -> flask.Response:
            """serves any file associated to recordings (legacy firmware only)"""
            logger.debug("GET /Record/%s", filename)
            affinity_key = self._get_affinity_key()
            if not self._get_legacy_api(affinity_key):
                # firmware V1.009+ moved downloads to the root
                return flask.abort(400)
            return self._serve_recording_file(affinity_key, filename)
```

- [ ] **Step 2: Run the suite to confirm it now fails**

Run: `behave`
Expected: FAIL -- non-legacy scenarios (the default, plus the `legacy: false` parity row) can no longer download via `/Record/`. This is the red state the code change turns green.

- [ ] **Step 3: Add the base64 import**

In `blackvuesync.py`, add `import base64` in the stdlib import block (alphabetical, before `import datetime`/`import json`):

```python
import base64
```

- [ ] **Step 4: Return `(legacy, filenames)` from `get_dashcam_filenames`**

Change the signature and the two success `return`s (the `try` body only; the `except` handlers are unchanged):

```python
def get_dashcam_filenames(base_url: str) -> tuple[bool, list[str]]:
    """gets whether the camera is legacy and its recording filenames"""
    try:
        legacy = is_legacy_camera(base_url)
        if legacy:
            return legacy, get_dashcam_filenames_legacy(base_url)

        url = urllib.parse.urljoin(base_url, "vodList")
        with urllib.request.urlopen(_build_request(url)) as response:
            response_status_code = response.getcode()
            if response_status_code != 200:
                raise RuntimeError(
                    f"Error response from : {base_url} ; status code : {response_status_code}"
                )

            data = json.load(response)

        return legacy, [entry["filename"] for entry in data["filelist"]]
    except urllib.error.URLError as e:
        # ...unchanged...
```

- [ ] **Step 5: Add the `legacy` parameter and root URL to `download_file`**

Change the signature (add `legacy` after `metrics`) and the URL construction at `blackvuesync.py:1024`:

```python
def download_file(
    base_url: str,
    filename: str,
    destination: str,
    group_name: str | None,
    metrics: SyncMetrics | None = None,
    legacy: bool = False,
) -> tuple[bool, int | None]:
```

```python
        # V1.009+ serves videos from the root; legacy firmware under /Record/
        url = urllib.parse.urljoin(
            base_url, f"Record/{filename}" if legacy else filename
        )
```

- [ ] **Step 6: Add `download_metadata_file`**

Add this new function immediately before `download_recording` (around `blackvuesync.py:1112`):

```python
def download_metadata_file(
    base_url: str,
    video_filename: str,
    metadata_filename: str,
    metadata_type: str,
    destination: str,
    group_name: str | None,
    metrics: SyncMetrics | None = None,
) -> tuple[bool, int | None]:
    """downloads thumbnail or gps data via the /vodMetadata endpoint (V1.009+)"""
    # pylint: disable=too-many-branches,too-many-return-statements
    if group_name:
        ensure_destination(os.path.join(destination, group_name))

    destination_filepath = get_filepath(destination, group_name, metadata_filename)
    if os.path.exists(destination_filepath):
        logger.debug(
            "Ignoring already downloaded file : %s",
            metadata_filename,
            extra={
                "event": "file_already_downloaded",
                "recording_filename": metadata_filename,
                "destination_path": destination_filepath,
            },
        )
        return False, None

    if dry_run:
        logger.debug(
            "DRY RUN Would download file : %s",
            metadata_filename,
            extra={"event": "file_download_dry_run", "recording_filename": metadata_filename},
        )
        return True, None

    if is_download_blocked_by_failure(destination, group_name, metadata_filename):
        logger.debug(
            "Skipping recently failed download : %s",
            metadata_filename,
            extra={"event": "file_download_recently_failed", "recording_filename": metadata_filename},
        )
        return False, None

    remove_download_failed_marker(destination, group_name, metadata_filename)

    temp_filepath = os.path.join(destination, f".{metadata_filename}")
    try:
        url = urllib.parse.urljoin(base_url, "vodMetadata")
        body = json.dumps({"file": video_filename, "types": [metadata_type]}).encode("utf-8")
        request = urllib.request.Request(url, data=body, method="POST")
        request.add_header("Content-Type", "application/json")
        if affinity_key:
            request.add_header("X-Affinity-Key", affinity_key)

        with urllib.request.urlopen(request) as response:
            data = json.load(response)

        if data.get("resultcode") != "BC_ERR_OK":
            cron_logger.warning(
                "Could not download file : %s; metadata result : %s; ignoring.",
                metadata_filename,
                data.get("resultcode"),
                extra={
                    "event": "file_download_failed",
                    "recording_filename": metadata_filename,
                    "error": str(data.get("resultcode")),
                },
            )
            return False, None

        # the payload sits at the top level, or nested under "metadata"
        encoded = data.get(metadata_type)
        if encoded is None and isinstance(data.get("metadata"), dict):
            encoded = data["metadata"].get(metadata_type)
        if not encoded:
            cron_logger.warning(
                "Metadata response missing %s data : %s; ignoring.",
                metadata_type,
                metadata_filename,
                extra={
                    "event": "file_download_failed",
                    "recording_filename": metadata_filename,
                    "error": "missing metadata payload",
                },
            )
            return False, None

        content = base64.b64decode(encoded)
        with open(temp_filepath, "wb") as f:
            f.write(content)
        os.rename(temp_filepath, destination_filepath)

        logger.debug(
            "Downloaded file : %s",
            metadata_filename,
            extra={
                "event": "file_downloaded",
                "recording_filename": metadata_filename,
                "destination_path": destination_filepath,
                "content_length_bytes": len(content),
            },
        )
        if metrics:
            metrics.record_file_download(len(content))
        return True, None
    except urllib.error.HTTPError as e:
        cron_logger.warning(
            "Could not download file : %s; error : %s; ignoring.",
            metadata_filename,
            e,
            extra={
                "event": "file_download_failed",
                "recording_filename": metadata_filename,
                "error_type": type(e).__name__,
                "error": str(e),
            },
        )
        if metrics:
            metrics.record_file_download_failure("http")
        mark_download_failed(destination, group_name, metadata_filename)
        return False, None
    except urllib.error.URLError as e:
        cron_logger.warning(
            "Could not download file : %s; error : %s; ignoring.",
            metadata_filename,
            e,
            extra={
                "event": "file_download_failed",
                "recording_filename": metadata_filename,
                "error_type": type(e).__name__,
                "error": str(e),
            },
        )
        if metrics:
            metrics.record_file_download_failure("network")
        return False, None
    except socket.timeout as e:
        if metrics:
            metrics.record_file_download_failure("timeout")
        raise UserWarning(
            f"Timeout communicating with dashcam at address : {base_url}; error : {e}"
        ) from e
    except ValueError as e:
        # malformed JSON or base64; non-fatal, mirrors a failed metadata fetch
        cron_logger.warning(
            "Could not parse metadata response : %s; error : %s; ignoring.",
            metadata_filename,
            e,
            extra={
                "event": "file_download_failed",
                "recording_filename": metadata_filename,
                "error_type": type(e).__name__,
                "error": str(e),
            },
        )
        return False, None
```

- [ ] **Step 7: Thread `legacy` through `download_recording` and route metadata**

Change the `download_recording` signature to accept `legacy`:

```python
def download_recording(
    base_url: str,
    recording: Recording,
    destination: str,
    metrics: SyncMetrics | None = None,
    legacy: bool = False,
) -> None:
```

Pass `legacy` to the video download:

```python
    downloaded, speed_bps = download_file(
        base_url, filename, destination, recording.group_name, metrics, legacy
    )
    any_downloaded |= downloaded
```

Route the thumbnail (replace the `download_file` call inside the `"t" not in skip_metadata` branch):

```python
    if "t" not in skip_metadata:
        thm_filename = (
            f"{recording.base_filename}_{recording.type}{recording.direction}.thm"
        )
        if legacy:
            downloaded, _ = download_file(
                base_url, thm_filename, destination, recording.group_name, metrics, legacy
            )
        else:
            downloaded, _ = download_metadata_file(
                base_url,
                recording.filename,
                thm_filename,
                "thumbnail",
                destination,
                recording.group_name,
                metrics,
            )
        any_downloaded |= downloaded
    else:
        logger.debug(
            "Skipping thumbnail : %s (--skip-metadata)",
            recording.base_filename,
            extra={
                "event": "metadata_skipped",
                "metadata_type": "thumbnail",
                "recording_base_filename": recording.base_filename,
            },
        )
```

Replace the accelerometer block so it only runs on legacy cameras:

```python
    # downloads the accelerometer data (legacy firmware only; V1.009+ has no endpoint)
    if legacy:
        if "3" not in skip_metadata:
            tgf_filename = f"{recording.base_filename}_{recording.type}.3gf"
            downloaded, _ = download_file(
                base_url, tgf_filename, destination, recording.group_name, metrics, legacy
            )
            any_downloaded |= downloaded
        else:
            logger.debug(
                "Skipping accelerometer : %s (--skip-metadata)",
                recording.base_filename,
                extra={
                    "event": "metadata_skipped",
                    "metadata_type": "accelerometer",
                    "recording_base_filename": recording.base_filename,
                },
            )
    else:
        logger.debug(
            "Skipping accelerometer : %s (unavailable on this firmware)",
            recording.base_filename,
            extra={
                "event": "metadata_skipped",
                "metadata_type": "accelerometer",
                "recording_base_filename": recording.base_filename,
            },
        )
```

Route the gps download (replace the `download_file` call inside the `"g" not in skip_metadata` branch):

```python
    if "g" not in skip_metadata:
        gps_filename = f"{recording.base_filename}_{recording.type}.gps"
        if legacy:
            downloaded, _ = download_file(
                base_url, gps_filename, destination, recording.group_name, metrics, legacy
            )
        else:
            downloaded, _ = download_metadata_file(
                base_url,
                recording.filename,
                gps_filename,
                "gps",
                destination,
                recording.group_name,
                metrics,
            )
        any_downloaded |= downloaded
    else:
        logger.debug(
            "Skipping gps : %s (--skip-metadata)",
            recording.base_filename,
            extra={
                "event": "metadata_skipped",
                "metadata_type": "gps",
                "recording_base_filename": recording.base_filename,
            },
        )
```

- [ ] **Step 8: Unpack `legacy` in `sync` and pass it down**

At `blackvuesync.py:1472` and `:1493`:

```python
    base_url = f"http://{address}"
    legacy, dashcam_filenames = get_dashcam_filenames(base_url)
```

```python
    for recording in current_dashcam_recordings:
        download_recording(base_url, recording, destination, metrics, legacy)
```

- [ ] **Step 9: Run both test suites**

Run: `behave`
Expected: all scenarios pass -- non-legacy downloads now use the root and `/vodMetadata`.

Run: `pytest test/blackvuesync_test.py -q`
Expected: all pass unchanged (the monkeypatched `get_dashcam_filenames` stubs raise before the tuple is unpacked; the direct `download_file` calls use the `legacy=False` default).

- [ ] **Step 10: Run the docker integration suite**

Run: `behave -D implementation=docker`
Expected: all scenarios pass (exercises the same paths against the containerized mock).

- [ ] **Step 11: Commit**

```bash
git add blackvuesync.py features/mock_dashcam/server.py
git commit -m "feat: download from root and vodMetadata on V1.009 cameras (#87)"
```

---

### Task 4: Parity feature -- verify metadata content on V1.009

**Goal:** Prove the `/vodMetadata` path writes correct thumbnail/GPS bytes and no `.3gf` on a non-legacy camera.

**Files:**

- Create: `features/steps/metadata_content_steps.py`
- Modify: `features/sync_api_parity.feature`

**Acceptance Criteria:**

- [ ] A `the downloaded "{extension}" files match the mock fixture` step compares each downloaded `.{extension}` file's bytes to `features/mock_dashcam/files/mock.{extension}`.
- [ ] A non-legacy scenario asserts thumbnail and gps files match the fixtures and no `.3gf` files exist.
- [ ] `behave features/sync_api_parity.feature` passes.

**Verify:** `behave features/sync_api_parity.feature`

**Steps:**

- [ ] **Step 1: Add the byte-comparison step**

Create `features/steps/metadata_content_steps.py`:

```python
"""metadata content verification step definitions"""

from pathlib import Path

from behave import then
from behave.runner import Context
from hamcrest import assert_that, equal_to, not_

_MOCK_FILES_DIR = Path(__file__).parent.parent / "mock_dashcam" / "files"


@then('the downloaded "{extension}" files match the mock fixture')
def assert_downloaded_files_match_fixture(context: Context, extension: str) -> None:
    """verifies every downloaded file of the given extension equals the mock fixture."""
    expected_bytes = (_MOCK_FILES_DIR / f"mock.{extension}").read_bytes()

    downloaded = [
        f for f in context.dest_dir.rglob(f"*.{extension}") if f.is_file()
    ]
    assert_that(downloaded, not_(equal_to([])))
    for downloaded_file in downloaded:
        assert_that(downloaded_file.read_bytes(), equal_to(expected_bytes))
```

- [ ] **Step 2: Add the non-legacy content scenario**

Append to `features/sync_api_parity.feature` (sentence-case name, lowercase steps, no `And`):

```gherkin
  Scenario: sync retrieves thumbnail and gps metadata on V1.009 cameras
    Given the dashcam is legacy: false
    Given recordings for the past "1d" of types "N", directions "F"
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then all the recordings are downloaded
    Then the downloaded "thm" files match the mock fixture
    Then the downloaded "gps" files match the mock fixture
    Then the destination contains no "3gf" files
```

- [ ] **Step 3: Run the parity feature**

Run: `behave features/sync_api_parity.feature`
Expected: all scenarios pass, including the new content assertions.

- [ ] **Step 4: Commit**

```bash
git add features/steps/metadata_content_steps.py features/sync_api_parity.feature
git commit -m "test: verify V1.009 thumbnail/gps content and no .3gf"
```

---

### Task 5: Documentation

**Goal:** Record the V1.009 download support in the changelog.

**Files:**

- Modify: `CHANGELOG.md`

**Acceptance Criteria:**

- [ ] The `2.2.0` section notes root video downloads plus thumbnail/GPS via the metadata endpoint, with accelerometer unavailable on that firmware, referencing #87.

**Verify:** `git diff CHANGELOG.md` shows the new entry; `behave && pytest test/blackvuesync_test.py -q` still green.

**Steps:**

- [ ] **Step 1: Add the changelog entry**

In `CHANGELOG.md`, under `## 2.2.0`, add a bullet after the existing `/vodList` entry:

```markdown
* Download recordings from BlackVue firmware V1.009+ cameras, which serve videos from the root path and provide thumbnail and GPS data through a metadata endpoint. Accelerometer data is unavailable on that firmware. (#87)
```

- [ ] **Step 2: Final full verification**

Run: `behave && pytest test/blackvuesync_test.py -q`
Expected: all green.

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: note V1.009 download support in changelog (#87)"
```

---

## Self-Review

**Spec coverage:**

- Root video path → Task 3 (Step 5). ✓
- `/vodMetadata` thumbnail/GPS (base64, tolerant) → Task 3 (Step 6, `download_metadata_file`). ✓
- `.3gf` skipped on non-legacy with debug log → Task 3 (Step 7). ✓
- `legacy` from a single probe → Task 3 (Step 4, returned tuple; refinement documented). ✓
- Mock root serving + `/vodMetadata` + non-mp4 `415` + `/Record/` fidelity → Tasks 1 & 3. ✓
- Parity coverage incl. metadata outcome and `.3gf` absence → Tasks 2 & 4. ✓
- CHANGELOG + earlier-doc correction → Task 5 (correction already applied in the spec commit). ✓
- Risk (vodMetadata not browser-verified; tolerant path) → realized as non-fatal returns in `download_metadata_file`. ✓

**Placeholder scan:** No TBD/TODO; every code step shows complete code. ✓

**Type consistency:** `get_dashcam_filenames -> tuple[bool, list[str]]` unpacked as `legacy, filenames` in `sync`. `download_file(..., legacy=False)` and `download_recording(..., legacy=False)` signatures match their call sites. `download_metadata_file` returns `tuple[bool, int | None]`, consumed as `downloaded, _`. `filter_available_metadata_filenames(filenames, legacy) -> set[str]` matches both call sites. Mock helper `_serve_recording_file(affinity_key, filename)` matches its two callers. ✓
