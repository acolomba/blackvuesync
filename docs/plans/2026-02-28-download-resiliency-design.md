# Download Resiliency Design

## Problem

BlackVue Sync has no per-download retry logic. A transient network drop during a
file download means waiting for the next cron run (typically 15 minutes) to retry.
Additionally, `socket.timeout` during a file download kills the entire sync run,
which is disproportionate for a per-file issue.

## Goals

- Recover quickly from brief network drops within a single sync run.
- Avoid retrying too often for files with persistent problems (e.g. corrupted SD
  card).
- A failure in a file subject to `--retry-failed-after` must not stop downloading
  other files (already the case today).

## Error Classification

**Transient** (`URLError`, `socket.timeout` during file download): retry up to
`--retry-count` with exponential backoff. No `.failed` marker.

**Permanent** (`HTTPError`): no retry. Immediate `.failed` marker, subject to
`--retry-failed-after`.

The dashcam listing request (`get_dashcam_filenames()`) is unchanged -- `socket.timeout`
and dashcam-unavailable errors still abort the sync.

## Design

### CLI Option

```text
--retry-count N    number of download attempts per file before giving up;
                   defaults to 3
```

Stored as a global variable following the existing pattern. Must be a positive
integer (>= 1). A value of 1 means no retries (single attempt).

### Retry Loop in `download_file()`

The HTTP request + streaming block is wrapped in a retry loop:

- `HTTPError` breaks out immediately -- no retry, creates `.failed` marker.
- `URLError` and `socket.timeout` trigger exponential backoff (1s, 2s, 4s) and
  retry.
- The temp dotfile is not cleaned up between retries, so partial downloads can
  resume.
- `socket.timeout` no longer raises `UserWarning` from `download_file()`.
- If all retries are exhausted for a transient error, no `.failed` marker is
  created. The file retries on the next sync run.
- Logging: debug-level for retry attempts, warning on final give-up.

### What Doesn't Change

- Dashcam listing request error handling.
- `.failed` marker semantics (only HTTP errors, subject to `--retry-failed-after`).
- Temp dotfile mechanism.
- `download_recording()` loop (continues past individual file failures).
- Exit codes.
- Logging hierarchy (cron_logger vs logger).

## Testing

### Unit Tests

- Retry succeeds on 2nd attempt after transient `URLError`.
- Retry succeeds on 3rd attempt after two transient errors.
- All retries exhausted -- no `.failed` marker created.
- `HTTPError` is not retried -- `.failed` marker created immediately.
- `socket.timeout` during download is retried (not raised as `UserWarning`).
- `--retry-count 1` gives current behavior (no retries).

### Integration Tests

- New scenario: transient failure during download recovers within the same sync
  run.
- Existing retry-failed scenarios pass unchanged.

### Documentation

- Document `--retry-count` in README options table.
