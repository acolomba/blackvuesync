# Retry-failed integration tests design

## Overview

Add integration tests for the `--retry-failed-after` feature. This requires:

1. Mock server support for simulating per-file download errors
2. A hidden `s` (seconds) suffix in `parse_duration()` for fast retry window tests
3. Three integration test scenarios covering the failure tracking lifecycle

## Mock server: download error simulation

### New state

Add a per-session error set to `MockDashcam`, mirroring the existing `_recordings_by_session` pattern:

```python
self._download_errors_by_session: defaultdict[str, set[str]] = defaultdict(set)
```

Thread-safe access via the existing `_sessions_lock`.

### New endpoints

**`POST /mock/downloads/errors`** -- configures which files return errors.

```text
X-Affinity-Key: <session-key>
Body: {"filenames": ["20181029_131513_NF.mp4", ...]}
```

Returns 201 with `{"status": "configured", "count": N}`.

**`DELETE /mock/downloads/errors`** -- clears the error set for the session.

```text
X-Affinity-Key: <session-key>
```

Returns 200 with `{"status": "cleared"}`.

### Modified route

**`GET /Record/<filename>`** -- before serving the file, checks if the filename is in the session's error set. If so, returns HTTP 500 (Internal Server Error). This triggers the `urllib.error.URLError` handler in `download_file()`, which calls `mark_download_failed()`.

### Cleanup

`MockDashcam.clear_recordings()` (called in `after_scenario`) also clears the download error set for the session. Rename to `clear_session()` or add a separate `clear_download_errors()` -- TBD during implementation, but the session must be fully cleaned between scenarios.

## Hidden "s" suffix for seconds

### `blackvuesync.py` changes

In the `duration_re` regex (line 94):

```python
# before
duration_re = re.compile(r"""(?P<range>\d+)(?P<unit>[hdw]?)""")

# after
duration_re = re.compile(r"""(?P<range>\d+)(?P<unit>[shdw]?)""")
```

In `parse_duration()`, add a case before the `h` branch:

```python
if duration_unit == "s":
    return datetime.timedelta(seconds=duration_range)
```

The `--retry-failed-after` and `--keep` help text stays unchanged -- only documents `h`, `d`, `w`. The `s` suffix is intentionally undocumented, for test use only.

### Error message update

The error message in `parse_duration()` changes from `<number>[hdw]` to `<number>[shdw]` (or stays as `[hdw]` since `s` is hidden -- TBD).

## Integration test scenarios

### New feature file: `features/sync_retry_failed.feature`

```gherkin
Feature: Retry failed downloads

  Scenario: Failed downloads create failure markers
    Given recordings for the past "1d" of types "N", directions "F"
    Given downloads of these recordings fail: "first 2 mp4"
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then the successful recordings are downloaded
    Then failure markers exist for the failed recordings

  Scenario: Failed downloads are skipped on next sync
    Given recordings for the past "1d" of types "N", directions "F"
    Given downloads of these recordings fail: "first 2 mp4"
    When blackvuesync runs
    When download errors are cleared
    When blackvuesync runs with retry-failed-after "1h"
    Then blackvuesync exits with code 0
    Then the previously failed recordings are not downloaded

  Scenario: Failed downloads are retried after retry window expires
    Given recordings for the past "1d" of types "N", directions "F"
    Given downloads of these recordings fail: "first 2 mp4"
    When blackvuesync runs
    When download errors are cleared
    When 2 seconds elapse
    When blackvuesync runs with retry-failed-after "1s"
    Then blackvuesync exits with code 0
    Then all the recordings are downloaded
    Then no failure markers exist
```

Note: the exact step wording for selecting which files fail is flexible. The key requirement is that we can deterministically pick a subset of recordings from `context.expected_recordings` to configure as failures, and later assert against them.

### New step definitions

**File: `features/steps/retry_failed_steps.py`**

Steps organized by Given/When/Then:

- `@given` -- `download_errors`: POSTs selected filenames to `/mock/downloads/errors`. Stores them in `context.failed_recordings`.
- `@when` -- `clear_download_errors`: DELETEs `/mock/downloads/errors`.
- `@when` -- `run_blackvuesync_with_retry_failed_after`: calls `execute_blackvuesync()` with `retry_failed_after=duration`.
- `@when` -- `wait_seconds`: `time.sleep(n)` for the retry window to expire.
- `@then` -- `assert_successful_recordings_downloaded`: checks that recordings NOT in `context.failed_recordings` are present in destination.
- `@then` -- `assert_failure_markers_exist`: checks `.failed` files exist for `context.failed_recordings`.
- `@then` -- `assert_no_failure_markers_exist`: checks no `.failed` files in destination.
- `@then` -- `assert_failed_recordings_not_downloaded`: checks that recordings in `context.failed_recordings` are NOT in destination.

### Changes to `execute_blackvuesync()`

Add `retry_failed_after: str | None = None` parameter to `execute_blackvuesync()`, `_execute_direct()`, and `_execute_docker()`. In direct mode, passes `--retry-failed-after <value>`. In docker mode, sets `RETRY_FAILED_AFTER` env var.

### Changes to `after_scenario`

Clear download errors alongside recordings. Either extend `clear_recordings()` to also clear errors, or call a new method.

## Test data strategy

The scenarios use `"N"` type and `"F"` direction for simplicity -- generates fewer files (only mp4, thm, 3gf, gps per recording, single direction). The "first 2 mp4" selector picks 2 .mp4 filenames from `context.expected_recordings` to configure as errors, giving a clear split between files that succeed and files that fail.

## What this does NOT cover

- `socket.timeout` path (raises `UserWarning`, aborts the whole sync -- not retry-related)
- Partial/corrupted downloads (the temp dotfile mechanism is separate from retry-failed)
- Grouping interaction (unit tests already cover markers with grouping)
