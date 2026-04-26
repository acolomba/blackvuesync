# Download Resiliency Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to
> implement this plan task-by-task.

**Goal:** Add per-file download retry with exponential backoff for transient
network errors, while preserving existing `.failed` marker semantics for
permanent HTTP errors.

**Architecture:** Wrap the HTTP request block in `download_file()` with a retry
loop. Transient errors (`URLError`, `socket.timeout`) trigger retries with
exponential backoff. Permanent errors (`HTTPError`) break immediately and create
`.failed` markers as before. A new `--retry-count` CLI option (default 3)
controls the number of attempts.

**Tech Stack:** Python 3.9+ stdlib only (`time.sleep` for backoff). Pytest for
unit tests. Behave for integration tests.

---

## Task 1: Add `--retry-count` global variable and CLI argument

Files:

- Modify: `blackvuesync.py:90` (global variables area)
- Modify: `blackvuesync.py:1020-1025` (argument parsing, near `--retry-failed-after`)
- Modify: `blackvuesync.py:1068-1078` (main function, global declarations)
- Modify: `blackvuesync.py:1108-1110` (main function, argument assignment)

### Step 1: Add global variable

After line 90 (`retry_failed_after`), add:

```python
# number of download attempts per file before giving up
retry_count: int = 3  # pylint: disable=invalid-name
```

### Step 2: Add CLI argument

After the `--retry-failed-after` argument (line 1025), add:

```python
arg_parser.add_argument(
    "--retry-count",
    metavar="N",
    default=3,
    type=int,
    help="number of download attempts per file before giving up; defaults to 3",
)
```

### Step 3: Wire up in `main()`

Add `global retry_count` to the global declarations block (after line 1078).
After the `retry_failed_after` assignment (line 1110), add:

```python
retry_count = args.retry_count
if retry_count < 1:
    raise RuntimeError("RETRY_COUNT must be at least 1.")
```

### Step 4: Run existing tests to confirm no regressions

Run: `pytest test/blackvuesync_test.py -v`
Expected: all existing tests pass.

### Step 5: Commit

```bash
git add blackvuesync.py
git commit -m "Add --retry-count CLI option (default 3)"
```

---

## Task 2: Add retry loop to `download_file()`

Files:

- Modify: `blackvuesync.py:461-539` (`download_file()` function)

### Step 1: Add `import time` if not already present

Check top of file. `time` is already imported (used at line 496 for
`time.perf_counter()`), so no change needed.

### Step 2: Wrap HTTP block in retry loop

Replace the try/except block (lines 493-539) with a retry loop. The structure:

```python
    for attempt in range(retry_count):
        try:
            url = urllib.parse.urljoin(base_url, f"Record/{filename}")

            start = time.perf_counter()
            try:
                # request
                request = urllib.request.Request(url)
                if affinity_key:
                    request.add_header("X-Affinity-Key", affinity_key)

                # downloads file
                with urllib.request.urlopen(request) as response:
                    headers = response.info()
                    size = headers.get("Content-Length")

                    # writes response to temp file
                    with open(temp_filepath, "wb") as f:
                        while chunk := response.read(DOWNLOAD_CHUNK_SIZE):
                            f.write(chunk)
            finally:
                end = time.perf_counter()
                elapsed_s = end - start

            os.rename(temp_filepath, destination_filepath)

            speed_bps = int(10.0 * float(size) / elapsed_s) if size else None
            speed_str = format_natural_speed(speed_bps)
            logger.debug("Downloaded file : %s%s", filename, speed_str)

            return True, speed_bps
        except urllib.error.HTTPError as e:
            # permanent error -- no retry, mark as failed
            cron_logger.warning(
                "Could not download file : %s; error : %s; ignoring.",
                filename,
                e,
            )
            mark_download_failed(destination, group_name, filename)
            return False, None
        except (urllib.error.URLError, socket.timeout) as e:
            # transient error -- retry with exponential backoff
            if attempt < retry_count - 1:
                backoff = 2**attempt
                logger.debug(
                    "Transient error downloading %s : %s; retrying in %ds (%d/%d)",
                    filename,
                    e,
                    backoff,
                    attempt + 1,
                    retry_count,
                )
                time.sleep(backoff)
            else:
                cron_logger.warning(
                    "Could not download file : %s; error : %s;"
                    " giving up after %d attempts.",
                    filename,
                    e,
                    retry_count,
                )
                return False, None

    return False, None  # unreachable, but satisfies type checker
```

Key changes from original:

- `socket.timeout` no longer raises `UserWarning` -- caught alongside `URLError`
- Transient errors get exponential backoff and retry
- `HTTPError` still breaks immediately with `.failed` marker
- Temp file not cleaned between retries (supports resume)

### Step 3: Run existing tests

Run: `pytest test/blackvuesync_test.py -v`
Expected: all existing tests pass.

### Step 4: Commit

```bash
git add blackvuesync.py
git commit -m "Add retry loop with exponential backoff to download_file"
```

---

## Task 3: Unit tests for retry logic

Files:

- Modify: `test/blackvuesync_test.py` (add tests in `TestFailedMarker` class or
  new `TestDownloadRetry` class)

### Step 1: Write test -- retry succeeds on 2nd attempt after URLError

Add a new `TestDownloadRetry` class after `TestFailedMarker`. These tests mock
`urllib.request.urlopen` to simulate failures.

```python
class TestDownloadRetry:
    """tests for download retry logic."""

    def test_retry_succeeds_after_transient_urlerror(self) -> None:
        """verifies that a transient URLError is retried and succeeds."""
        with tempfile.TemporaryDirectory() as dest:
            filename = "20181029_131513_NF.mp4"
            original_retry_count = blackvuesync.retry_count

            try:
                blackvuesync.retry_count = 3

                call_count = 0

                def mock_urlopen(request, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        raise urllib.error.URLError("Connection reset")
                    # returns a mock response on 2nd attempt
                    response = unittest.mock.MagicMock()
                    response.__enter__ = lambda s: s
                    response.__exit__ = unittest.mock.MagicMock(return_value=False)
                    response.info.return_value = {"Content-Length": "4"}
                    response.read.side_effect = [b"test", b""]
                    return response

                with unittest.mock.patch(
                    "urllib.request.urlopen", side_effect=mock_urlopen
                ), unittest.mock.patch("time.sleep"):
                    downloaded, _ = blackvuesync.download_file(
                        "http://127.0.0.1:0", filename, dest, None
                    )

                assert downloaded is True
                assert call_count == 2
                assert os.path.exists(os.path.join(dest, filename))
            finally:
                blackvuesync.retry_count = original_retry_count
```

### Step 2: Run test to verify it passes

Run: `pytest test/blackvuesync_test.py::TestDownloadRetry::test_retry_succeeds_after_transient_urlerror -v`
Expected: PASS

### Step 3: Write test -- all retries exhausted, no marker created

```python
    def test_retries_exhausted_no_failed_marker(self) -> None:
        """verifies that exhausted transient retries do not create a .failed marker."""
        with tempfile.TemporaryDirectory() as dest:
            filename = "20181029_131513_NF.mp4"
            original_retry_count = blackvuesync.retry_count

            try:
                blackvuesync.retry_count = 3

                with unittest.mock.patch(
                    "urllib.request.urlopen",
                    side_effect=urllib.error.URLError("Connection reset"),
                ), unittest.mock.patch("time.sleep"):
                    downloaded, _ = blackvuesync.download_file(
                        "http://127.0.0.1:0", filename, dest, None
                    )

                assert downloaded is False
                marker = blackvuesync.get_failed_marker_filepath(dest, None, filename)
                assert not os.path.exists(marker)
            finally:
                blackvuesync.retry_count = original_retry_count
```

### Step 4: Write test -- HTTPError not retried, marker created

```python
    def test_http_error_not_retried(self) -> None:
        """verifies that HTTPError is not retried and creates a .failed marker."""
        with tempfile.TemporaryDirectory() as dest:
            filename = "20181029_131513_NF.mp4"
            original_retry_count = blackvuesync.retry_count
            call_count = 0

            try:
                blackvuesync.retry_count = 3

                def mock_urlopen(request, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    raise urllib.error.HTTPError(
                        "http://x", 500, "Server Error", {}, None
                    )

                with unittest.mock.patch(
                    "urllib.request.urlopen", side_effect=mock_urlopen
                ), unittest.mock.patch("time.sleep"):
                    downloaded, _ = blackvuesync.download_file(
                        "http://127.0.0.1:0", filename, dest, None
                    )

                assert downloaded is False
                assert call_count == 1  # only one attempt
                marker = blackvuesync.get_failed_marker_filepath(dest, None, filename)
                assert os.path.exists(marker)
            finally:
                blackvuesync.retry_count = original_retry_count
```

### Step 5: Write test -- socket.timeout retried (not raised)

```python
    def test_socket_timeout_retried_not_raised(self) -> None:
        """verifies that socket.timeout during download is retried, not raised."""
        with tempfile.TemporaryDirectory() as dest:
            filename = "20181029_131513_NF.mp4"
            original_retry_count = blackvuesync.retry_count

            try:
                blackvuesync.retry_count = 2
                call_count = 0

                def mock_urlopen(request, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        raise socket.timeout("timed out")
                    response = unittest.mock.MagicMock()
                    response.__enter__ = lambda s: s
                    response.__exit__ = unittest.mock.MagicMock(return_value=False)
                    response.info.return_value = {"Content-Length": "4"}
                    response.read.side_effect = [b"test", b""]
                    return response

                with unittest.mock.patch(
                    "urllib.request.urlopen", side_effect=mock_urlopen
                ), unittest.mock.patch("time.sleep"):
                    downloaded, _ = blackvuesync.download_file(
                        "http://127.0.0.1:0", filename, dest, None
                    )

                assert downloaded is True
                assert call_count == 2
            finally:
                blackvuesync.retry_count = original_retry_count
```

### Step 6: Write test -- retry-count 1 gives no retries

```python
    def test_retry_count_one_no_retries(self) -> None:
        """verifies that --retry-count 1 means single attempt, no retries."""
        with tempfile.TemporaryDirectory() as dest:
            filename = "20181029_131513_NF.mp4"
            original_retry_count = blackvuesync.retry_count
            call_count = 0

            try:
                blackvuesync.retry_count = 1

                def mock_urlopen(request, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    raise urllib.error.URLError("Connection reset")

                with unittest.mock.patch(
                    "urllib.request.urlopen", side_effect=mock_urlopen
                ), unittest.mock.patch("time.sleep"):
                    downloaded, _ = blackvuesync.download_file(
                        "http://127.0.0.1:0", filename, dest, None
                    )

                assert downloaded is False
                assert call_count == 1
            finally:
                blackvuesync.retry_count = original_retry_count
```

### Step 7: Write test -- retry succeeds on 3rd attempt

```python
    def test_retry_succeeds_on_third_attempt(self) -> None:
        """verifies recovery after two consecutive transient errors."""
        with tempfile.TemporaryDirectory() as dest:
            filename = "20181029_131513_NF.mp4"
            original_retry_count = blackvuesync.retry_count

            try:
                blackvuesync.retry_count = 3
                call_count = 0

                def mock_urlopen(request, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count <= 2:
                        raise urllib.error.URLError("Connection reset")
                    response = unittest.mock.MagicMock()
                    response.__enter__ = lambda s: s
                    response.__exit__ = unittest.mock.MagicMock(return_value=False)
                    response.info.return_value = {"Content-Length": "4"}
                    response.read.side_effect = [b"test", b""]
                    return response

                with unittest.mock.patch(
                    "urllib.request.urlopen", side_effect=mock_urlopen
                ), unittest.mock.patch("time.sleep"):
                    downloaded, _ = blackvuesync.download_file(
                        "http://127.0.0.1:0", filename, dest, None
                    )

                assert downloaded is True
                assert call_count == 3
            finally:
                blackvuesync.retry_count = original_retry_count
```

### Step 8: Run all tests

Run: `pytest test/blackvuesync_test.py -v`
Expected: all tests pass.

### Step 9: Commit

```bash
git add test/blackvuesync_test.py
git commit -m "Add unit tests for download retry logic"
```

---

## Task 4: Add transient error support to mock dashcam server

Files:

- Modify: `features/mock_dashcam/server.py:86-92` (add transient error tracking)
- Modify: `features/mock_dashcam/server.py:152-184` (record endpoint)
- Modify: `features/mock_dashcam/server.py:245-268` (mock endpoints)
- Modify: `features/mock_dashcam/server.py:329-333` (cleanup)

The mock server needs to support "transient" errors that succeed after N
failures. This is different from existing download errors (which always fail
with HTTP 500).

### Step 1: Add transient error tracking

Near line 92 (`_download_errors_by_session`), add a parallel dict for transient
errors:

```python
# tracks transient download errors: {affinity_key: {filename: remaining_failures}}
self._transient_errors_by_session: defaultdict[str, dict[str, int]] = defaultdict(dict)
```

Add thread-safe accessors following the existing pattern for
`_download_errors_by_session`.

### Step 2: Update record endpoint

In the `record()` function (line 152), after the permanent error check
(line 166-168), add a transient error check:

```python
# checks if file has transient errors remaining
transient_errors = self._get_transient_errors(affinity_key)
if filename in transient_errors and transient_errors[filename] > 0:
    self._decrement_transient_error(affinity_key, filename)
    logger.debug("Response: connection reset (transient error)")
    # closes connection abruptly to simulate network error
    flask.request.environ.get("werkzeug.server.shutdown", lambda: None)()
    return flask.Response(status=500, headers={"Connection": "close"})
```

Note: simulating a true connection reset from Flask is tricky. A simpler
approach is to abort the response partway through (send partial data then
close). However, the simplest reliable approach is to return a 500 but with
a distinct marker that the integration test step can configure as "transient."
Actually, the cleanest approach: close the socket mid-transfer to trigger a
`URLError` on the client side. Flask can do this by raising `ConnectionError`.

Actually, the simplest approach that reliably triggers `URLError` (not
`HTTPError`) on the client: have the server close the connection without sending
a response. In werkzeug/Flask, we can do:

```python
raise ConnectionError("simulated network drop")
```

Or use `flask.abort(503)` -- but that would be an `HTTPError`. Instead, we need
the server to drop the connection. The most reliable way in Flask:

```python
import socket as _socket
# gets the underlying socket and closes it
sock = flask.request.environ.get("werkzeug.request").raw._sock
sock.close()
raise ConnectionAbortedError("simulated transient failure")
```

Given the complexity of simulating true connection drops in Flask, a pragmatic
approach for the integration test is:

**Option A:** Add a `/mock/downloads/transient-errors` endpoint that configures
files to fail N times then succeed. The mock server returns HTTP 503
(Service Unavailable) for transient errors, and the integration test validates
that the retry mechanism recovers. Since 503 is an `HTTPError`, this won't
test the exact `URLError` retry path -- but the unit tests already cover that.

**Option B:** Instead of connection drops, configure the mock server to send a
partial response then close, which triggers `urllib.error.URLError:
<urlopen error [Errno 104] Connection reset by peer>` on the client.

Go with **Option A** for simplicity, using a custom response that aborts the
connection. The key integration test assertion is: "transient failures recover
within a single sync run."

Actually, reviewing the retry logic more carefully: both `HTTPError` and
`URLError` are subclasses of `URLError`, but `HTTPError` is caught first.
A 503 would be caught as `HTTPError` (permanent), not retried.

The simplest reliable approach: make the mock server close the TCP connection
mid-response by writing partial content. This approach:

```python
if filename in transient_errors and transient_errors[filename] > 0:
    self._decrement_transient_error(affinity_key, filename)
    logger.debug("Response: connection drop (transient error, %d remaining)",
                 transient_errors[filename])
    # sends partial response then abruptly closes connection
    def generate():
        yield b"partial"
        raise ConnectionError("simulated network drop")
    return flask.Response(generate(), mimetype="application/octet-stream")
```

This should cause a `URLError` or `http.client.IncompleteRead` on the client.
Test this in step 3 to verify the client sees it as a retryable error.

### Step 3: Add mock API endpoints

Add `POST /mock/downloads/transient-errors` and
`DELETE /mock/downloads/transient-errors`:

```python
@self.app.route("/mock/downloads/transient-errors", methods=["POST"])
def set_transient_errors() -> tuple[dict[str, Any], int]:
    """configures files to fail transiently N times then succeed."""
    data = flask.request.get_json() or {}
    affinity_key = self._get_affinity_key()

    # format: {"filenames": ["file1.mp4", "file2.mp4"], "fail_count": 2}
    filenames = data.get("filenames", [])
    fail_count = data.get("fail_count", 1)
    errors = {f: fail_count for f in filenames}
    self._set_transient_errors(affinity_key, errors)

    return {"status": "configured", "count": len(filenames)}, 201

@self.app.route("/mock/downloads/transient-errors", methods=["DELETE"])
def clear_transient_errors_route() -> tuple[dict[str, str], int]:
    """clears transient errors for the session."""
    affinity_key = self._get_affinity_key()
    self._set_transient_errors(affinity_key, {})
    return {"status": "cleared"}, 200
```

### Step 4: Update cleanup

In `clear_session_state()` (line 329), also clear transient errors.

### Step 5: Run existing integration tests to confirm no regressions

Run: `behave`
Expected: all existing scenarios pass.

### Step 6: Commit

```bash
git add features/mock_dashcam/server.py
git commit -m "Add transient error support to mock dashcam server"
```

---

## Task 5: Integration test for transient retry recovery

Files:

- Modify: `features/sync_retry_failed.feature` (add scenario)
- Modify: `features/steps/retry_failed_steps.py` (add step definitions)
- Modify: `features/steps/blackvuesync_steps.py:17-35` (add `retry_count`
  parameter to `execute_blackvuesync`)

### Step 1: Add `retry_count` parameter to `execute_blackvuesync`

In `features/steps/blackvuesync_steps.py`, add `retry_count: int | None = None`
to the function signature. Wire it through to the CLI args (`--retry-count`).

### Step 2: Add step definitions for transient errors

In `features/steps/retry_failed_steps.py`, add:

```python
@given("the first {count:d} mp4 recordings have {fail_count:d} transient errors")
def transient_download_errors(context: Context, count: int, fail_count: int) -> None:
    """configures the first N mp4 recordings to fail transiently."""
    if not hasattr(context, "expected_recordings"):
        raise RuntimeError(
            "Cannot configure transient errors: no recordings configured yet."
        )

    mp4_files = [f for f in context.expected_recordings if f.endswith(".mp4")]
    failed_filenames = mp4_files[:count]

    url = f"{context.mock_dashcam_url}/mock/downloads/transient-errors"
    headers = {"X-Affinity-Key": context.scenario_token}
    data = {"filenames": failed_filenames, "fail_count": fail_count}

    response = requests.post(url, json=data, headers=headers, timeout=10)
    response.raise_for_status()


@when('blackvuesync runs with retry-count "{count:d}"')
def run_blackvuesync_with_retry_count(context: Context, count: int) -> None:
    """executes blackvuesync with a specific retry count."""
    execute_blackvuesync(
        context,
        context.mock_dashcam_address,
        str(context.dest_dir),
        context.scenario_token,
        retry_count=count,
    )
```

### Step 3: Add integration test scenario

In `features/sync_retry_failed.feature`, add:

```gherkin
  Scenario: Transient download errors recover within a single sync run
    Given recordings for the past "1d" of types "N", directions "F"
    Given the first 2 mp4 recordings have 2 transient errors
    When blackvuesync runs with retry-count "3"
    Then blackvuesync exits with code 0
    Then all the recordings are downloaded
    Then no failure markers exist
```

### Step 4: Run integration tests

Run: `behave`
Expected: all scenarios pass, including the new one.

### Step 5: Commit

```bash
git add features/sync_retry_failed.feature features/steps/retry_failed_steps.py features/steps/blackvuesync_steps.py
git commit -m "Add integration test for transient download retry"
```

---

## Task 6: Docker wrapper and documentation

Files:

- Modify: `blackvuesync.sh` (add `RETRY_COUNT` env var mapping)
- Modify: `README.md:129` (add `--retry-count` to CLI options)
- Modify: `README.md:265` (add `RETRY_COUNT` to Docker env vars)

### Step 1: Add env var mapping to Docker wrapper

In `blackvuesync.sh`, after the `RETRY_FAILED_AFTER` line (line 36), add:

```bash
# retry-count option if RETRY_COUNT set
[ -n "${RETRY_COUNT:-}" ] && set -- "$@" --retry-count "$RETRY_COUNT"
```

### Step 2: Document `--retry-count` in README CLI options

After the `--retry-failed-after` entry (line 129), add:

```markdown
* `--retry-count`: Sets the number of download attempts per file before giving up. Transient network errors (connection resets, timeouts) trigger retries with exponential backoff. HTTP errors (e.g. server errors for corrupted files) are not retried. Defaults to `3`.
```

### Step 3: Document `RETRY_COUNT` in README Docker section

After the `RETRY_FAILED_AFTER` entry (line 265), add:

```markdown
* `RETRY_COUNT`: If set, sets the number of download attempts per file before giving up. (Default: `3`.)
```

### Step 4: Run shellcheck on wrapper

Run: `shellcheck blackvuesync.sh`
Expected: no errors.

### Step 5: Commit

```bash
git add blackvuesync.sh README.md
git commit -m "Document --retry-count in README and Docker wrapper"
```

---

## Task 7: Final verification

### Step 1: Run all unit tests

Run: `pytest test/blackvuesync_test.py -v`
Expected: all tests pass.

### Step 2: Run all integration tests

Run: `behave`
Expected: all scenarios pass.

### Step 3: Run pre-commit hooks on all changed files

Run: `pre-commit run --all-files`
Expected: all hooks pass.

### Step 4: Verify git log

Run: `git log --oneline main..HEAD`
Expected: clean commit history with descriptive messages.
