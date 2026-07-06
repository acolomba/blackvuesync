# Firmware V1.009 listing API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make blackvuesync sync recordings from BlackVue firmware V1.009+ cameras
(JSON `/vodList` index) while keeping older cameras (plaintext `blackvue_vod.cgi`)
working, verified end-to-end by the mock dashcam in both modes.

**Architecture:** The only behavioral change is how the recording index is
fetched and parsed. `get_dashcam_filenames` probes `GET /accessible`; when absent
it returns early to the legacy `blackvue_vod.cgi` path (a backwards-compatibility
appendix), otherwise it fetches and parses `GET /vodList` JSON. Everything
downstream (the `Recording` structure, grouping, retention, `/Record/<filename>`
downloads) is untouched because it consumes an identical `list[str]` of filenames.

**Tech Stack:** Python 3.9+ stdlib only (`json` already imported). Flask mock
dashcam for integration. Behave for integration coverage; pytest unchanged.

**User decisions (already made):**

- "one dedicated parity feature" -- not a full both-ways matrix over every feature.
- "default the emulator to the new version"; "the new style is _the_ style, the rest is legacy yes/no".
- "use 'legacy' for the old style"; "avoid references to 'restful'".
- Detection: probe `/accessible` first (option A).
- "flip the logic ... to is_legacy_camera and have an early exit/return to get_dashcam_filenames_legacy".
- Mock: "a legacy_api flag ... a binary is sufficient".
- Parity examples: "legacy_api true false, and the given is 'the dashcam is legacy'".
- "minimize the changes to blackvuesync down to the parser of the file list".
- Work in a feature branch (`firmware-v1009-listing-api`, already created).

**Ordering rationale (why blackvuesync changes land before the emulator flips):**
The current emulator has no `/accessible` route, so after Task 1 blackvuesync's
probe receives a 404 and falls back to legacy -- the existing suite stays green
with no emulator change. Task 2 then flips the emulator default to the new style,
which is green because blackvuesync already speaks it. No temporary defaults;
every commit is green.

**Note:** `import json` is already present at `blackvuesync.py:33` -- do NOT re-add
it. There is no `from typing import Any`; annotate the JSON parser param as bare
`dict` (no new import needed).

---

## Task 1: blackvuesync -- /accessible detection, /vodList parsing, legacy appendix

**Goal:** `get_dashcam_filenames` speaks the new `/vodList` JSON API, falling back
to the legacy `blackvue_vod.cgi` path when `/accessible` is absent; the existing
behave suite stays green (emulator unchanged, so `/accessible` 404s → legacy).

**Files:**

- Modify: `blackvuesync.py` (around `get_filenames`/`get_dashcam_filenames`, lines 758-805)

**Acceptance Criteria:**

- [ ] `is_legacy_camera(base_url)` returns `False` on a `200` from `/accessible`, `True` on `HTTPError` (e.g. 404).
- [ ] The new-style branch fetches `/vodList`, parses JSON, and returns `[entry["filename"] for entry in data["filelist"]]`.
- [ ] The legacy branch is reached by an early return and preserves the existing `blackvue_vod.cgi` plaintext behavior byte-for-byte.
- [ ] Connection-level errors during the `/accessible` probe still surface as "Dashcam unavailable" via the existing handler.
- [ ] Existing `pytest` and `behave` suites remain green (blackvuesync falls back to legacy against the unchanged emulator).

**Verify:** `pytest test/blackvuesync_test.py -q && behave --no-capture --format progress` → both green.

**Steps:**

- [ ] **Step 1: Add helpers and the new parser above `get_dashcam_filenames`.**

Insert immediately after `get_filenames` (after line 766), before `get_dashcam_filenames`:

```python
def _build_request(url: str) -> urllib.request.Request:
    """builds a GET request, adding the affinity header when configured"""
    request = urllib.request.Request(url)
    if affinity_key:
        request.add_header("X-Affinity-Key", affinity_key)
    return request


def is_legacy_camera(base_url: str) -> bool:
    """returns True for older cameras that lack the /accessible endpoint (pre-V1.009)"""
    url = urllib.parse.urljoin(base_url, "accessible")
    try:
        with urllib.request.urlopen(_build_request(url)) as response:
            return response.getcode() != 200
    except urllib.error.HTTPError:
        return True


def get_filenames_from_json(data: dict) -> list[str]:
    """extracts the recording filenames from the dashcam /vodList JSON response"""
    return [entry["filename"] for entry in data["filelist"]]
```

- [ ] **Step 2: Rewrite `get_dashcam_filenames` to detect then branch.**

Replace the body of `get_dashcam_filenames` (lines 769-805) with:

```python
def get_dashcam_filenames(base_url: str) -> list[str]:
    """gets the recording filenames from the dashcam"""
    try:
        if is_legacy_camera(base_url):
            return get_dashcam_filenames_legacy(base_url)

        url = urllib.parse.urljoin(base_url, "vodList")
        with urllib.request.urlopen(_build_request(url)) as response:
            response_status_code = response.getcode()
            if response_status_code != 200:
                raise RuntimeError(
                    f"Error response from : {base_url} ; status code : {response_status_code}"
                )

            data = json.load(response)

        return get_filenames_from_json(data)
    except urllib.error.URLError as e:
        if isinstance(e.reason, OSError) and (
            isinstance(e.reason, (TimeoutError, socket.timeout))
            or e.reason.errno in dashcam_unavailable_errno_codes
        ):
            raise UserWarning(f"Dashcam unavailable : {e}") from e

        raise RuntimeError(
            f"Cannot obtain list of recordings from dashcam at address : {base_url}; error : {e}"
        ) from e
    except socket.timeout as e:
        raise UserWarning(
            f"Timeout communicating with dashcam at address : {base_url}; error : {e}"
        ) from e
    except http.client.RemoteDisconnected as e:
        raise UserWarning(
            f"Dashcam disconnected without a response; address : {base_url}; error : {e}"
        ) from e
```

- [ ] **Step 3: Add the legacy appendix function immediately after `get_dashcam_filenames`.**

```python
def get_dashcam_filenames_legacy(base_url: str) -> list[str]:
    """gets recording filenames from an older dashcam via the blackvue_vod.cgi index"""
    url = urllib.parse.urljoin(base_url, "blackvue_vod.cgi")
    with urllib.request.urlopen(_build_request(url)) as response:
        response_status_code = response.getcode()
        if response_status_code != 200:
            raise RuntimeError(
                f"Error response from : {base_url} ; status code : {response_status_code}"
            )

        charset = response.info().get_param("charset", "UTF-8")
        file_lines = [x.decode(charset) for x in response.readlines()]

    return get_filenames(file_lines)
```

- [ ] **Step 4: Run the suites to confirm no regression.**

Run: `pytest test/blackvuesync_test.py -q`
Expected: PASS (unchanged count).

Run: `behave --no-capture --format progress`
Expected: PASS. blackvuesync now probes `/accessible`, the unchanged emulator returns 404, so it falls back to `blackvue_vod.cgi` -- identical end behavior.

- [ ] **Step 5: Commit.**

```bash
git add blackvuesync.py
git commit -m "Support the V1.009 /vodList index with legacy fallback"
```

(Include the repo's standard Co-Authored-By / Claude-Session trailers.)

---

## Task 2: Mock dashcam -- /accessible, /vodList, legacy switch; default to new style

**Goal:** The mock serves the new-style API by default (`/accessible` + JSON
`/vodList`), deprecates `blackvue_vod.cgi` with `415 "mp4 only"` when not legacy,
and exposes a per-session `legacy_api` switch. The full behave suite passes
against the new default because blackvuesync (Task 1) already speaks it.

**Files:**

- Modify: `features/mock_dashcam/server.py`

**Acceptance Criteria:**

- [ ] Per-session `legacy_api` boolean, defaulting to `False` (new style), with thread-safe getter/setter.
- [ ] `POST /mock/legacy-api` `{"legacy_api": bool}` sets the session flag; `clear_session` resets it.
- [ ] `GET /accessible` returns `200 {"accessible":"OK","message":"Access possible."}` when not legacy, `404` when legacy.
- [ ] `GET /vodList` returns `200 {"filelist":[{"filename": ...}, ...]}` when not legacy, `404` when legacy.
- [ ] `GET /blackvue_vod.cgi` returns the plaintext index when legacy, `415` body `mp4 only` when not legacy.
- [ ] Full `behave` suite green with the new default.

**Verify:** `behave --no-capture --format progress` → green (existing features now exercise `/vodList` end-to-end).

**Steps:**

- [ ] **Step 1: Add per-session `legacy_api` state in `__init__`.**

In `MockDashcam.__init__`, after the `self._download_errors_by_session` line (around line 92), add:

```python
        self._legacy_api_by_session: defaultdict[str, bool] = defaultdict(bool)
```

- [ ] **Step 2: Add thread-safe getter/setter** next to `_get_download_errors`/`_set_download_errors` (after line 124):

```python
    def _get_legacy_api(self, affinity_key: str) -> bool:
        """thread-safe read access to the session-specific legacy-api flag"""
        with self._sessions_lock:
            return self._legacy_api_by_session[affinity_key]

    def _set_legacy_api(self, affinity_key: str, legacy_api: bool) -> None:
        """thread-safe write access to the session-specific legacy-api flag"""
        with self._sessions_lock:
            self._legacy_api_by_session[affinity_key] = legacy_api
```

- [ ] **Step 3: Add `/accessible` and `/vodList` routes** inside `_setup_routes`, just before the existing `/blackvue_vod.cgi` route (before line 134):

```python
        @self.app.route("/accessible", methods=["GET"])
        def accessible() -> flask.Response | tuple[dict[str, str], int]:
            """reports the new-style API is reachable; absent on legacy firmware"""
            logger.debug("GET /accessible")
            affinity_key = self._get_affinity_key()
            if self._get_legacy_api(affinity_key):
                return flask.abort(404)
            return {"accessible": "OK", "message": "Access possible."}, 200

        @self.app.route("/vodList", methods=["GET"])
        def vod_list() -> flask.Response | tuple[dict[str, Any], int]:
            """returns the index of recordings as JSON (new style)"""
            logger.debug("GET /vodList")
            affinity_key = self._get_affinity_key()
            if self._get_legacy_api(affinity_key):
                return flask.abort(404)
            recordings = self._get_recordings(affinity_key)
            filelist = [{"filename": filename} for filename in recordings]
            return {"filelist": filelist}, 200
```

- [ ] **Step 4: Gate the existing `/blackvue_vod.cgi` route on the legacy flag.**

In the `vod()` handler, right after `affinity_key = self._get_affinity_key()` (line 138), add:

```python
            if not self._get_legacy_api(affinity_key):
                # firmware V1.009+ deprecated this endpoint
                return flask.Response("mp4 only", status=415, mimetype="text/plain")
```

(The route's return type annotation becomes `flask.Response | str`.)

- [ ] **Step 5: Add the `POST /mock/legacy-api` control route** next to the other `/mock/...` routes (after the `set_download_errors` block, around line 259):

```python
        @self.app.route("/mock/legacy-api", methods=["POST"])
        def set_legacy_api() -> tuple[dict[str, Any], int]:
            """configures whether the session serves the legacy blackvue_vod.cgi index"""
            data = flask.request.get_json() or {}
            logger.debug("POST /mock/legacy-api")
            logger.debug("Request body: %s", data)
            affinity_key = self._get_affinity_key()

            legacy_api = bool(data.get("legacy_api", False))
            self._set_legacy_api(affinity_key, legacy_api)

            response = {"status": "configured", "legacy_api": legacy_api}
            logger.debug("Response body: %s", response)

            return response, 201
```

- [ ] **Step 6: Reset the flag in `clear_session`.**

In `clear_session`, add to the `if affinity_key:` branch:

```python
                self._legacy_api_by_session[affinity_key] = False
```

and to the `else:` branch:

```python
                self._legacy_api_by_session.clear()
```

- [ ] **Step 7: Run the full suite.**

Run: `behave --no-capture --format progress`
Expected: PASS. Existing features now default to the new style: blackvuesync probes `/accessible` (200), fetches `/vodList`, downloads via `/Record/`.

- [ ] **Step 8: Commit.**

```bash
git add features/mock_dashcam/server.py
git commit -m "Add new-style dashcam API to the mock with a legacy switch"
```

---

## Task 3: Parity feature and step

**Goal:** A dedicated feature runs the identical sync over both the legacy and
new styles and asserts the same recordings download.

**Files:**

- Create: `features/sync_api_parity.feature`
- Modify: `features/steps/dashcam_recordings_steps.py`

**Acceptance Criteria:**

- [ ] `features/sync_api_parity.feature` is a Scenario Outline with `Examples` rows `true` and `false`.
- [ ] A `@given('the dashcam is legacy: {legacy_api}')` step POSTs `/mock/legacy-api` with the scenario affinity key.
- [ ] Both example rows pass: all recordings download under legacy and new styles.

**Verify:** `behave features/sync_api_parity.feature --no-capture --format progress` → both scenarios pass.

**Steps:**

- [ ] **Step 1: Add the step** to `features/steps/dashcam_recordings_steps.py` (append after the last `@given`):

```python
@given('the dashcam is legacy: {legacy_api}')
def dashcam_legacy_api(context: Context, legacy_api: str) -> None:
    """configures whether the mock dashcam serves the legacy blackvue_vod.cgi index."""
    url = f"{context.mock_dashcam_url}/mock/legacy-api"
    headers = {"X-Affinity-Key": context.scenario_token}
    data = {"legacy_api": legacy_api.lower() == "true"}

    response = requests.post(url, json=data, headers=headers, timeout=10)
    response.raise_for_status()
```

- [ ] **Step 2: Create `features/sync_api_parity.feature`:**

```gherkin
Feature: API version parity

  Scenario Outline: sync yields the same recordings whether the camera is legacy
    Given the dashcam is legacy: <legacy_api>
    Given recordings for the past "1d" of types "NE", directions "FR"
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then all the recordings are downloaded

    Examples:
      | legacy_api |
      | true       |
      | false      |
```

- [ ] **Step 3: Run the parity feature.**

Run: `behave features/sync_api_parity.feature --no-capture --format progress`
Expected: PASS -- 2 scenarios (legacy true and false), all steps passing.

- [ ] **Step 4: Run the whole suite to confirm nothing else moved.**

Run: `behave --no-capture --format progress`
Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add features/sync_api_parity.feature features/steps/dashcam_recordings_steps.py
git commit -m "Add API version parity integration feature"
```

---

## Task 4: Changelog entry

**Goal:** Record the new firmware support in the changelog.

**Files:**

- Modify: `CHANGELOG.md`

**Acceptance Criteria:**

- [ ] A bullet documents V1.009 `/vodList` JSON listing support with legacy fallback, referencing issue #87.

**Verify:** `head -8 CHANGELOG.md` shows the new entry; `git diff --stat` shows only `CHANGELOG.md`.

**Steps:**

- [ ] **Step 1: Add a new version section** at the top of `CHANGELOG.md`, above `## 2.2.0`:

```markdown
## 2.3.0

* Support BlackVue firmware V1.009+ cameras, which serve the recording index as JSON from `/vodList` instead of the legacy `blackvue_vod.cgi` endpoint. Older cameras continue to work unchanged. (#87)
```

(If `2.2.0` is still unreleased at execution time, fold the bullet into it instead of adding `2.3.0`.)

- [ ] **Step 2: Commit.**

```bash
git add CHANGELOG.md
git commit -m "Note V1.009 listing API support in the changelog"
```

---

## Verification summary

- `pytest test/blackvuesync_test.py -q` -- unchanged, green.
- `behave --no-capture --format progress` -- green (existing features exercise the new style by default; parity feature covers both).
- `behave -D implementation=docker --no-capture --format progress` -- green (containerized mock).
