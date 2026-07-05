# Firmware V1.009 download path and metadata support

**Goal:** Restore actual recording downloads for BlackVue cameras running
firmware V1.009+ (e.g. Elite 9). The listing side (`/vodList`) already landed
(see `2026-07-02-firmware-v1009-listing-api.md`), but downloads still fail on
V1.009 because the firmware moved video files and dropped plain metadata-file
access. See issue #87.

**Architecture:** The firmware change affects the download path only. Video
files moved from `/Record/<filename>` to the server root `/<filename>`, and the
`.thm`/`.gps`/`.3gf` metadata files are no longer served as plain files -- a
plain `GET` of a non-`.mp4` name returns `415 mp4 only`. Thumbnail and GPS data
are instead obtained from the firmware's `POST /vodMetadata` endpoint (the same
endpoint the BlackVue mobile app uses), which returns the data base64-encoded in
JSON. The accelerometer `.3gf` has no `/vodMetadata` counterpart and is not
retrievable on V1.009; it is skipped there. Legacy cameras are unchanged.

**Tech Stack:** Python 3.9+ stdlib only (`base64` is added for decoding the
metadata payloads; `json` is already imported). The mock dashcam server (Flask)
gains root-served videos and the `/vodMetadata` endpoint. Behave drives
integration coverage; pytest is unchanged.

---

## Background

The listing-API doc assumed downloads were unchanged on V1.009. Issue #87 has
since falsified that. Confirmed against the reporter's live V1.009 camera
(browser address-bar `GET`s) and consistent with the BlackVue mobile app's
behavior:

- **Video moved to root.** `GET /Record/<filename>.mp4` returns `400`;
  `GET /<filename>.mp4` (server root) downloads the video. The reporter also
  confirmed raw stream access works.
- **Metadata files are not served as plain files.** `GET /<name>.thm` and
  `GET /<name>.3gf` at the root both return `415 mp4 only` -- the root file
  server serves `.mp4` only.
- **Thumbnail and GPS come from `POST /vodMetadata`.** For each recording the
  app issues one request per metadata type (they are never bundled):

  ```text
  POST /vodMetadata   Content-Type: application/json
  {"file": "20260704_102813_IF.mp4", "types": ["thumbnail"]}
  -> {"resultcode": "BC_ERR_OK", "thumbnail": "<base64>"}
  ```

  and the same with `"types": ["gps"]`. The base64 payload decodes to the same
  bytes the legacy `.thm` / `.gps` files contained.
- **The accelerometer `.3gf` has no metadata type.** Only `thumbnail` and `gps`
  are retrievable through `/vodMetadata`; there is no `.3gf` counterpart. On
  V1.009 the accelerometer data is unavailable and is skipped.

## Naming

Consistent with the listing-API doc: the current style is *the* style and the
old style is "legacy", a binary yes/no. Do not use the name "restful". The
endpoint literals `/vodMetadata`, `/vodList`, `/accessible` are kept verbatim
because they are the actual firmware wire endpoints, not names chosen here. The
`.thm`/`.gps`/`.3gf` files are "metadata files", matching the existing
`--skip-metadata` vocabulary.

## `blackvuesync.py`

The download path currently ignores firmware version: `download_recording`
builds four `download_file` calls (video + `.thm` + `.3gf` + `.gps`), and
`download_file` hardcodes `urljoin(base_url, f"Record/{filename}")`. The change
threads a single `legacy: bool` into the download path and branches on it.

New and changed units:

- **Surface the legacy flag from `get_dashcam_filenames`.** The `/accessible`
  probe already lives inside `get_dashcam_filenames`, where its result is
  currently discarded. Instead of hoisting the probe into `sync` (which would
  fire the real probe during unit tests that monkeypatch `get_dashcam_filenames`
  by name), `get_dashcam_filenames` returns `(legacy, filenames)`. `sync` unpacks
  the flag and passes it into the download loop, so the probe still happens
  exactly once and no unit test wiring changes.
- **`download_recording(..., legacy: bool)`** -- routes each part of a recording:
  - *Video:* `download_file(..., legacy)`.
  - *Thumbnail / GPS:* on legacy, the existing plain-`GET` `download_file` path;
    on V1.009, `download_metadata_file(...)` (below). Both remain gated by the
    existing `--skip-metadata` flags (`t`, `g`).
  - *Accelerometer (`.3gf`):* on legacy, unchanged; on V1.009, skipped with a
    single `logger.debug` note that the accelerometer data is unavailable on this
    firmware. (The `--skip-metadata` `3` flag is moot there.)
- **`download_file(..., legacy: bool)`** -- the only behavioral change is the URL:
  `urljoin(base_url, f"Record/{filename}")` when legacy, `urljoin(base_url,
  filename)` (root) when not. Everything else (temp dotfile, resume, failure
  markers, metrics, tolerant `HTTPError` handling) is untouched.
- **`download_metadata_file(base_url, video_filename, metadata_filename,
  metadata_type, destination, group_name, metrics) -> tuple[bool, int | None]`**
  -- new. Mirrors `download_file`'s contract (already-downloaded skip, dry-run,
  failure markers, temp-file-then-rename) but obtains bytes via `POST
  /vodMetadata` instead of a `GET`:
  - Builds the JSON request `{"file": video_filename, "types": [metadata_type]}`
    with `Content-Type: application/json` (and the affinity header when set),
    where `metadata_type` is `"thumbnail"` or `"gps"`.
  - Parses the response, requires `resultcode == "BC_ERR_OK"`, base64-decodes the
    payload for the requested type, and writes it to `metadata_filename`.
  - Any non-OK `resultcode`, missing/empty payload, or malformed response is
    logged and treated as a non-fatal skip -- identical in spirit to a failed
    metadata `GET` today, so a metadata hiccup never aborts the video sync.
- Add `import base64`.

The exact JSON key the payload sits under for `gps` (flat vs. nested under a
`metadata` object) is confirmed during implementation against the mock and, where
possible, the live camera; the parser handles the documented shape and degrades
gracefully on anything else.

## Mock dashcam server (`features/mock_dashcam/server.py`)

The server already has a per-session `legacy_api` flag. Extend the non-legacy
side to mirror V1.009 downloads:

- `GET /<filename>.mp4` (root) -- serves the video when not legacy.
- `GET /Record/<filename>` -- serves the video when legacy (unchanged); on the
  non-legacy side a root `GET` of a non-`.mp4` name returns `415 mp4 only`, for
  fidelity and to guard against accidental plain metadata-file fetches.
- `POST /vodMetadata` -- when not legacy, accepts `{"file", "types":[type]}` and
  returns `{"resultcode": "BC_ERR_OK", <type>: "<base64>"}` for `thumbnail` and
  `gps`, sourced from the same fixture bytes the legacy metadata files serve.
  Returns a non-OK `resultcode` for an unknown file so the tolerant path is
  exercised.
- Legacy behavior (`/Record/<filename>`, plain `.thm`/`.gps`/`.3gf`) is
  unchanged.

## Integration tests

Extend the existing parity coverage (`features/sync_api_parity.feature`) so the
both-firmwares run also asserts the metadata outcome, not just the videos:

- On both firmwares, the video and the thumbnail/GPS metadata files land.
- On V1.009 specifically, `.3gf` is **absent** (no retrieval path), whereas on
  legacy it is present.

A focused scenario drives a non-legacy sync and checks that `.thm` and `.gps`
exist with the expected bytes and that no `.3gf` is written.

## Testing and verification

- Primary coverage is integration, matching the current suite:
  - The parity feature exercises both download paths end-to-end, including the
    `/vodMetadata` decode.
  - The default (current-style) suite continues to exercise the new download path
    across all behaviors.
- Verify: `behave` green; `behave -D implementation=docker` green; existing
  `pytest test/blackvuesync_test.py` unchanged.

## Docs

- `CHANGELOG.md`: note V1.009 downloads -- root video path plus thumbnail/GPS via
  the metadata endpoint, accelerometer unavailable on that firmware (issue #87).
- Correct the superseded claim in `2026-07-02-firmware-v1009-listing-api.md`
  (the "download path unchanged" out-of-scope note) with a pointer here.

## Risks and out of scope

- **`/vodMetadata` is not browser-verifiable by the reporter** (a JSON `POST`
  is not address-bar-testable), so it ships against the app's known protocol
  without independent confirmation of the exact response shape. The safety net is
  the tolerant, non-fatal metadata path: if the shape differs, thumbnail/GPS
  quietly skip and the video sync -- the reporter's actual complaint -- still
  succeeds. The shape can be corrected in a follow-up once observed on a live
  camera.
- **Accelerometer `.3gf` is not recovered on V1.009.** No external retrieval path
  exists on that firmware (the data appears only embedded in the mp4, whose
  client-side extraction is out of scope for a stdlib-only tool).
- No auth/HTTPS changes; blackvuesync targets HTTP as today.
