# Retry-Failed Integration Tests Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add integration tests for the `--retry-failed-after` feature, including mock server error simulation and a hidden `s` (seconds) duration suffix for fast tests.

**Architecture:** Extend the mock dashcam server with per-session download error state (same pattern as recordings). Add a hidden `s` suffix to `parse_duration()` in `blackvuesync.py`. Create 3 BDD scenarios in a new feature file with supporting step definitions.

**Tech Stack:** Python, Behave (BDD), Flask (mock server), PyHamcrest (assertions)

---

## Task 1: Add seconds support to `parse_duration()`

**Files:**

- Modify: `blackvuesync.py:94` (regex), `blackvuesync.py:111-132` (function)
- Modify: `test/blackvuesync_test.py:413-435` (unit tests)

### Step 1: Add unit test for seconds duration

In `test/blackvuesync_test.py`, add `("1s", datetime.timedelta(seconds=1))` and `("30s", datetime.timedelta(seconds=30))` to the `test_parse_duration` parametrize list (line 415), and add `"0s"` to the `test_parse_duration_invalid` parametrize list (line 431).

```python
# in the test_parse_duration parametrize list, add before the first entry:
("1s", datetime.timedelta(seconds=1)),
("30s", datetime.timedelta(seconds=30)),

# in the test_parse_duration_invalid parametrize list, add:
"0s",
```

### Step 2: Run tests to verify they fail

Run: `pytest test/blackvuesync_test.py::test_parse_duration -v`
Expected: FAIL for the `1s` and `30s` cases (regex doesn't match `s`)

### Step 3: Implement seconds in `parse_duration()`

In `blackvuesync.py`:

Line 94 - add `s` to the regex character class:

```python
# before
duration_re = re.compile(r"""(?P<range>\d+)(?P<unit>[hdw]?)""")
# after
duration_re = re.compile(r"""(?P<range>\d+)(?P<unit>[shdw]?)""")
```

Lines 124-129 - add `s` case before the `h` case:

```python
if duration_unit == "s":
    return datetime.timedelta(seconds=duration_range)
if duration_unit == "h":
    return datetime.timedelta(hours=duration_range)
```

Do NOT change the error message on line 115 or the `--retry-failed-after` help text - `s` is intentionally undocumented.

### Step 4: Run tests to verify they pass

Run: `pytest test/blackvuesync_test.py::test_parse_duration test/blackvuesync_test.py::test_parse_duration_invalid -v`
Expected: all PASS

### Step 5: Commit

```bash
git add blackvuesync.py test/blackvuesync_test.py
git commit -m "Add hidden seconds suffix to parse_duration()"
```

---

## Task 2: Add download error simulation to mock dashcam server

**Files:**

- Modify: `features/mock_dashcam/server.py:75-295` (MockDashcam class)

### Step 1: Add error state and accessor methods

In `features/mock_dashcam/server.py`, add to `__init__` (after line 91):

```python
self._download_errors_by_session: defaultdict[str, set[str]] = defaultdict(set)
```

Add two accessor methods after `_set_recordings` (after line 113):

```python
def _get_download_errors(self, affinity_key: str) -> set[str]:
    """thread-safe read access to session-specific download errors"""
    with self._sessions_lock:
        return self._download_errors_by_session[affinity_key].copy()

def _set_download_errors(self, affinity_key: str, filenames: set[str]) -> None:
    """thread-safe write access to session-specific download errors"""
    with self._sessions_lock:
        self._download_errors_by_session[affinity_key] = filenames
```

### Step 2: Add error check to the `/Record/<filename>` route

In `_setup_routes`, in the `record()` function, after the 404 check for "not in session recordings" (after line 151) and before `if recording := to_recording(filename):` (line 153), add:

```python
# checks if file is configured to fail
download_errors = self._get_download_errors(affinity_key)
if filename in download_errors:
    logger.debug("Response: 500 Internal Server Error (configured error)")
    flask.abort(500)
```

### Step 3: Add POST/DELETE `/mock/downloads/errors` routes

Add inside `_setup_routes`, after the `set_recordings` route (after line 226):

```python
@self.app.route("/mock/downloads/errors", methods=["POST"])
def set_download_errors() -> tuple[dict[str, Any], int]:
    """configures which files return download errors"""
    data = flask.request.get_json() or {}
    logger.debug("POST /mock/downloads/errors")
    logger.debug("Request body: %s", data)
    affinity_key = self._get_affinity_key()

    filenames = set(data.get("filenames", []))
    self._set_download_errors(affinity_key, filenames)

    response = {"status": "configured", "count": len(filenames)}
    logger.debug("Response body: %s", response)

    return response, 201

@self.app.route("/mock/downloads/errors", methods=["DELETE"])
def clear_download_errors_route() -> tuple[dict[str, str], int]:
    """clears download errors for the session"""
    logger.debug("DELETE /mock/downloads/errors")
    affinity_key = self._get_affinity_key()
    self._set_download_errors(affinity_key, set())
    logger.debug("Response body: {'status': 'cleared'}")
    return {"status": "cleared"}, 200
```

### Step 4: Update `clear_recordings` to also clear errors

Rename `clear_recordings` to `clear_session` (line 286) and update it to also clear download errors:

```python
def clear_session(self, affinity_key: str | None = None) -> None:
    """clears all session state (recordings, download errors) for cleanup"""
    with self._sessions_lock:
        if affinity_key:
            self._recordings_by_session[affinity_key] = []
            self._download_errors_by_session[affinity_key] = set()
        else:
            self._recordings_by_session.clear()
            self._download_errors_by_session.clear()
```

### Step 5: Update environment.py to use new method name

In `features/environment.py` line 221, change `clear_recordings` to `clear_session`:

```python
# before
context.mock_dashcam.clear_recordings(context.scenario_token)
# after
context.mock_dashcam.clear_session(context.scenario_token)
```

### Step 6: Run existing integration tests to verify no regression

Run: `behave`
Expected: all existing scenarios PASS

### Step 7: Commit

```bash
git add features/mock_dashcam/server.py features/environment.py
git commit -m "Add download error simulation to mock dashcam"
```

---

## Task 3: Add `retry_failed_after` parameter to `execute_blackvuesync()`

**Files:**

- Modify: `features/steps/blackvuesync_steps.py:17-314` (all three functions)
- Modify: `blackvuesync.sh:1-37` (docker env var mapping)

### Step 1: Add parameter to `execute_blackvuesync()`

In `features/steps/blackvuesync_steps.py`, add `retry_failed_after: str | None = None` parameter to all three functions: `execute_blackvuesync` (after `dry_run` on line 31), `_execute_direct` (after `dry_run` on line 86), and `_execute_docker` (after `dry_run` on line 206).

In `execute_blackvuesync`, pass it through to both `_execute_docker` and `_execute_direct` (add after `dry_run` in both call sites, lines 52 and 68).

In `_execute_direct`, add after the `dry_run` block (after line 150):

```python
if retry_failed_after:
    cmd.extend(["--retry-failed-after", retry_failed_after])
```

In `_execute_docker`, add after the `dry_run` block (after line 279):

```python
if retry_failed_after:
    container.with_env("RETRY_FAILED_AFTER", retry_failed_after)
```

### Step 2: Add env var to `blackvuesync.sh`

In `blackvuesync.sh`, add after the `dry_run` line (after line 30):

```bash
# retry-failed-after option if RETRY_FAILED_AFTER set
retry_failed_after=${RETRY_FAILED_AFTER:+--retry-failed-after $RETRY_FAILED_AFTER}
```

Add `${retry_failed_after}` to the command line on line 35-36 (before the trailing backslash continuation or at the end).

### Step 3: Run existing integration tests to verify no regression

Run: `behave`
Expected: all existing scenarios PASS

### Step 4: Commit

```bash
git add features/steps/blackvuesync_steps.py blackvuesync.sh
git commit -m "Add retry-failed-after to test execution helpers"
```

---

## Task 4: Create feature file and step definitions

**Files:**

- Create: `features/sync_retry_failed.feature`
- Create: `features/steps/retry_failed_steps.py`

### Step 1: Create the feature file

Create `features/sync_retry_failed.feature`:

```gherkin
Feature: Retry failed downloads

  Scenario: Failed downloads create failure markers
    Given recordings for the past "1d" of types "N", directions "F"
    Given the first 2 mp4 recordings are configured to fail
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then the successful recordings are downloaded
    Then failure markers exist for the failed recordings

  Scenario: Failed downloads are skipped on next sync
    Given recordings for the past "1d" of types "N", directions "F"
    Given the first 2 mp4 recordings are configured to fail
    When blackvuesync runs
    When download errors are cleared
    When blackvuesync runs with retry-failed-after "1h"
    Then blackvuesync exits with code 0
    Then the previously failed recordings are not downloaded

  Scenario: Failed downloads are retried after retry window expires
    Given recordings for the past "1d" of types "N", directions "F"
    Given the first 2 mp4 recordings are configured to fail
    When blackvuesync runs
    When download errors are cleared
    When 2 seconds elapse
    When blackvuesync runs with retry-failed-after "1s"
    Then blackvuesync exits with code 0
    Then all the recordings are downloaded
    Then no failure markers exist
```

### Step 2: Create the step definitions file

Create `features/steps/retry_failed_steps.py`:

```python
"""retry-failed download step definitions"""

import re
import time

import requests
from behave import given, then, when
from behave.runner import Context
from hamcrest import assert_that, empty, has_items, not_

from features.steps.blackvuesync_steps import execute_blackvuesync

# recording filename pattern
recording_filename_re = re.compile(
    r"^\d{8}_\d{6}_[NEPMIOATBRXGDLYF][FRIO]?[LS]?\.(mp4|thm|3gf|gps)$"
)


@given("the first {count:d} mp4 recordings are configured to fail")
def download_errors(context: Context, count: int) -> None:
    """configures the first N mp4 recordings to return download errors."""
    if not hasattr(context, "expected_recordings"):
        raise RuntimeError(
            "Cannot configure download errors: no recordings configured yet."
        )

    mp4_files = [f for f in context.expected_recordings if f.endswith(".mp4")]
    failed_filenames = mp4_files[:count]

    url = f"{context.mock_dashcam_url}/mock/downloads/errors"
    headers = {"X-Affinity-Key": context.scenario_token}
    data = {"filenames": failed_filenames}

    response = requests.post(url, json=data, headers=headers, timeout=10)
    response.raise_for_status()

    context.failed_recordings = set(failed_filenames)


@when("download errors are cleared")
def clear_download_errors(context: Context) -> None:
    """clears all configured download errors."""
    url = f"{context.mock_dashcam_url}/mock/downloads/errors"
    headers = {"X-Affinity-Key": context.scenario_token}

    response = requests.delete(url, headers=headers, timeout=10)
    response.raise_for_status()


@when('blackvuesync runs with retry-failed-after "{duration}"')
def run_blackvuesync_with_retry_failed_after(context: Context, duration: str) -> None:
    """executes blackvuesync with a retry-failed-after duration."""
    execute_blackvuesync(
        context,
        context.mock_dashcam_address,
        str(context.dest_dir),
        context.scenario_token,
        retry_failed_after=duration,
    )


@when("{seconds:d} seconds elapse")
def wait_seconds(context: Context, seconds: int) -> None:
    """waits for the specified number of seconds."""
    time.sleep(seconds)


@then("the successful recordings are downloaded")
def assert_successful_recordings_downloaded(context: Context) -> None:
    """verifies that recordings not configured to fail exist in destination."""
    if not hasattr(context, "expected_recordings"):
        raise RuntimeError("No expected recordings configured.")

    failed = getattr(context, "failed_recordings", set())
    successful = {f for f in context.expected_recordings if f not in failed}

    downloaded = {
        f.name
        for f in context.dest_dir.rglob("*")
        if f.is_file() and recording_filename_re.match(f.name)
    }

    assert_that(downloaded, has_items(*successful))


@then("failure markers exist for the failed recordings")
def assert_failure_markers_exist(context: Context) -> None:
    """verifies that .failed marker files exist for failed recordings."""
    if not hasattr(context, "failed_recordings"):
        raise RuntimeError("No failed recordings configured.")

    marker_files = {
        f.name for f in context.dest_dir.rglob("*.failed") if f.is_file()
    }

    expected_markers = {f"{f}.failed" for f in context.failed_recordings}
    assert_that(marker_files, has_items(*expected_markers))


@then("the previously failed recordings are not downloaded")
def assert_failed_recordings_not_downloaded(context: Context) -> None:
    """verifies that previously failed recordings are not in destination."""
    if not hasattr(context, "failed_recordings"):
        raise RuntimeError("No failed recordings configured.")

    downloaded = {
        f.name
        for f in context.dest_dir.rglob("*")
        if f.is_file() and recording_filename_re.match(f.name)
    }

    found_failed = downloaded & context.failed_recordings
    assert_that(
        list(found_failed),
        empty(),
        f"Expected failed recordings to not be downloaded, but found: {sorted(found_failed)}",
    )


@then("no failure markers exist")
def assert_no_failure_markers_exist(context: Context) -> None:
    """verifies that no .failed marker files exist in destination."""
    marker_files = [
        f.name for f in context.dest_dir.rglob("*.failed") if f.is_file()
    ]
    assert_that(
        marker_files,
        empty(),
        f"Expected no failure markers, but found: {marker_files}",
    )
```

### Step 3: Run the new integration tests

Run: `behave features/sync_retry_failed.feature -v`
Expected: all 3 scenarios PASS

### Step 4: Run all tests to verify no regression

Run: `pytest test/blackvuesync_test.py -v && behave`
Expected: all PASS

### Step 5: Commit

```bash
git add features/sync_retry_failed.feature features/steps/retry_failed_steps.py
git commit -m "Add integration tests for retry-failed-after feature"
```
