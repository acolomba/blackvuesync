# Firmware V1.009 listing API support

**Goal:** Restore recording sync for BlackVue cameras running firmware V1.009+
(e.g. Elite 9), which replaced the plaintext `blackvue_vod.cgi` index with a JSON
`/vodList` endpoint, while keeping older cameras working unchanged. See issue #87.

**Architecture:** The firmware change affects exactly one thing -- how the
recording index is fetched and parsed. The current style becomes the main path
in `get_dashcam_filenames`; the old `blackvue_vod.cgi` path becomes a
backwards-compatibility appendix reached by an early return. Everything
downstream (the `Recording` structure, `to_recording`, the filename regex,
grouping, retention, and file downloads via `/Record/<filename>`) is untouched,
because it all operates on a plain `list[str]` of filenames that is identical
between the two firmware styles.

**Tech Stack:** Python 3.9+ stdlib only (`json` is added for parsing `/vodList`;
no third-party dependency). The mock dashcam server (Flask) gains the new
endpoints. Behave drives integration coverage; pytest is unchanged.

---

## Background

Findings were confirmed against a live V1.009 camera in issue #87:

- The camera exposes `GET /accessible` for firmware detection. It returns
  `200 {"accessible":"OK","message":"Access possible."}` on V1.009 and does not
  exist (404) on older firmware.
- The recording index moved from `GET /blackvue_vod.cgi` (plaintext lines
  `n:/Record/<file>,s:<size>`) to `GET /vodList`, which returns
  `{"filelist":[{"filename":"20260702_141045_PF.mp4"}, ...]}`. Note the live
  response carries only `filename` -- no `size`.
- On V1.009 the old `blackvue_vod.cgi` returns HTTP 415 with body `mp4 only`.
- File downloads are unchanged: recordings remain available at
  `GET /Record/<filename>`, and direct file access confirmed working on V1.009.

## Naming

The current style is *the* style and carries no special name. The old style is
"legacy", expressed as a binary yes/no. Do not use the name "restful". The
endpoint URL literals
`/accessible` and `/vodList` are kept verbatim only because they are the actual
firmware wire endpoints, not names chosen here.

## `blackvuesync.py`

`get_dashcam_filenames(base_url) -> list[str]` keeps its public contract. It is
restructured to detect once, then branch:

```python
def get_dashcam_filenames(base_url):
    try:
        if is_legacy_camera(base_url):
            return get_dashcam_filenames_legacy(base_url)   # early return: appendix

        # the current style: GET /vodList -> JSON
        url = urllib.parse.urljoin(base_url, "vodList")
        with urllib.request.urlopen(_build_request(url)) as response:
            response_status_code = response.getcode()
            if response_status_code != 200:
                raise RuntimeError(...)
            data = json.load(response)
        return get_filenames_from_json(data)
    except urllib.error.URLError as e:
        ...unchanged unavailable / RuntimeError handling...
    except socket.timeout as e:
        ...unchanged...
    except http.client.RemoteDisconnected as e:
        ...unchanged...
```

New and changed units:

- `is_legacy_camera(base_url) -> bool` -- issues `GET /accessible` and returns
  `True` when the response is not `200` (an `HTTPError` such as 404 means older
  firmware). Connection-level errors (`URLError` without an HTTP status,
  timeouts) are not caught here; they propagate to the shared handler in
  `get_dashcam_filenames` and are reported as "dashcam unavailable" exactly as
  today.
- `get_dashcam_filenames_legacy(base_url) -> list[str]` -- the existing
  `blackvue_vod.cgi` request and `get_filenames(file_lines)` body, moved into a
  plain function with no try/except of its own; it raises into the shared
  handler above.
- `get_filenames_from_json(data) -> list[str]` -- pure parser returning
  `[f["filename"] for f in data["filelist"]]`, mirroring the existing
  `get_filenames`. A malformed response (missing `filelist`/`filename`) raises
  and is surfaced as an error rather than silently returning an empty list; a
  valid camera always returns the documented shape.
- `_build_request(url)` -- small helper that builds a `urllib.request.Request`
  and conditionally adds the `X-Affinity-Key` header. Used by the three
  index-related requests (`/accessible`, `/vodList`, `blackvue_vod.cgi`) to
  avoid copy-paste. The download path is left untouched.
- `get_filenames` and `file_line_re` (plaintext) are unchanged, used only by the
  legacy appendix.
- Add `import json`.

This is the whole blackvuesync change. The only genuinely new logic is the
`/accessible` probe and the JSON parse, both inherent to obtaining the index.

## Mock dashcam server (`features/mock_dashcam/server.py`)

Add a per-session `legacy_api` boolean (keyed by affinity key, like recordings),
**defaulting to `False`** (current style). A binary is sufficient.

- `POST /mock/legacy-api` with `{"legacy_api": true|false}` sets the session flag.
- `GET /accessible` → `200 {"accessible":"OK","message":"Access possible."}`
  when not legacy; `404` when legacy.
- `GET /vodList` → `200 {"filelist":[{"filename": f}, ...]}` when not legacy;
  `404` when legacy.
- `GET /blackvue_vod.cgi` → existing plaintext when legacy; `415` with body
  `mp4 only` when not legacy (faithful to real V1.009, and guards against
  accidental use).
- `GET /Record/<filename>` -- unchanged.

Because the default is the current style, all five existing feature files run
against `/vodList` with no edits, and their assertions still pass (identical
filenames).

## Integration tests

New `features/sync_api_parity.feature` runs the identical sync over both styles:

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

New step `@given('the dashcam is legacy: {legacy_api}')` parses the boolean and
POSTs `/mock/legacy-api` with the scenario's affinity key. It lives in
`dashcam_recordings_steps.py` (dashcam setup) and follows the feature
conventions (lowercase, present tense, "the dashcam").

## Testing and verification

- Primary coverage is integration, matching the current suite (which has no
  `get_filenames` unit tests -- index parsing is integration-tested):
  - The parity feature exercises both parsers end-to-end.
  - The default (current-style) suite exercises the new path across all
    behaviors (basic, filter, retention, retry, skip-metadata).
- Verify: `behave` green; `behave -D implementation=docker` green; existing
  `pytest test/blackvuesync_test.py` unchanged.

## Docs

- `CHANGELOG.md`: one entry noting V1.009 JSON listing support with legacy
  fallback (issue #87).

## Out of scope

- No change to the download path; `/Record/<filename>` is confirmed unchanged on
  V1.009.
- No auth/HTTPS handling changes. The app probes HTTP then HTTPS; blackvuesync
  targets HTTP as today.
- The `size` field is not consumed (it is absent from live `/vodList` anyway);
  real file sizes continue to come from `Content-Length` at download time.
