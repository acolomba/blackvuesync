# Retry Failed Downloads Design

## Problem

The dashcam sometimes serves HTTP 500 errors for certain recordings (likely
corrupted on-device). BlackVue Sync retries these every run (typically every 15
minutes via cron), wasting time and filling logs with noise. See
[issue #22](https://github.com/acolomba/blackvuesync/issues/22).

## Solution

Track download failures with marker files and skip retries until a configurable
duration has passed.

## Duration Parsing (shared infrastructure)

The existing `keep_re` regex and `calc_cutoff_date()` handle `--keep` durations
with `d` and `w` units. This design generalizes the duration parsing:

- Extend the regex to accept `h`, `d`, or `w`: `(?P<range>\d+)(?P<unit>[hdw]?)`
- Extract a shared `parse_duration()` function that takes a duration string
  (e.g., `12h`, `1d`, `2w`) and returns a `datetime.timedelta`. Default unit
  when omitted remains `d` for backward compatibility with `--keep`.
- Refactor `calc_cutoff_date()` to call `parse_duration()` internally, keeping
  its existing behavior and validation (range >= 1).
- Rename `keep_re` to `duration_re` since it is now shared.

## Marker Files

When a download fails with an HTTP error, a visible marker file is created:

- **Path:** `{filename}.failed` in the same directory where the recording would
  be saved (inside grouping subdirectories when grouping is active). For
  example, a failed `20250911_162008_NF.mp4` creates
  `20250911_162008_NF.mp4.failed`.
- **Content:** `datetime.datetime.now().isoformat()` -- the timestamp of the
  failure.
- **Blocking logic:** Before downloading a file, check if a marker exists. If
  it does, read the timestamp, compute elapsed time, and compare against the
  `--retry-failed-after` timedelta. If within the window, skip. If the marker
  is stale (past the window) or corrupted/unreadable, allow the retry.
- **On successful download:** Remove any existing marker for that file.

## Marker Lifecycle

Markers are persistent and follow the same lifecycle as recordings for retention
purposes. The `--retry-failed-after` duration only governs whether to attempt a
re-download, not when to delete the marker.

1. **Download fails:** Create/update `filename.failed` with current timestamp.
2. **Next sync run:** Check marker age against `--retry-failed-after`. If within
   window, skip. If past the window, retry the download.
3. **Retry succeeds:** Remove the marker.
4. **Retry fails again:** Update the marker timestamp (resets the retry window).
5. **Retention (`--keep`):** Markers are subject to the same cutoff date as
   recordings. The retention logic removes `.failed` files whose recording
   timestamp (parsed from the filename) falls before the cutoff, just like
   `.mp4`, `.thm`, `.3gf`, and `.gps` files.

`clean_destination()` does not need special marker cleanup -- retention handles
it. The existing temp dotfile and empty directory cleanup remain unchanged.

## CLI

- **Flag:** `--retry-failed-after`
- **Metavar:** `DURATION`
- **Format:** `<number>[hdw]` -- same as `--keep` but with the added `h` unit
- **Default:** `1d`
- **Help text:** `"waits at least the given duration before retrying a failed
  download; defaults to days, but can suffix with h, d, w for hours, days or
  weeks respectively; defaults to 1d"`
- **Storage:** Parsed via `parse_duration()` into a `timedelta`, stored as a
  global `retry_failed_after: datetime.timedelta`

### Interactions

- **`--keep`:** Independent. A recording can be blocked by a failure marker and
  also be subject to retention cleanup. If `--keep 7d` removes recordings older
  than 7 days, it removes their `.failed` markers too.
- **`--dry-run`:** Marker creation and removal are skipped during dry runs.
  Skip/block logging still happens.
- **`--cron`:** No special behavior. Failed downloads log at WARNING (existing
  behavior), skip messages log at DEBUG.

## Testing

### Unit tests

- `parse_duration()`: `h`, `d`, `w` units, default unit (no suffix = days),
  invalid inputs, zero/negative values.
- `get_failed_marker_filepath()`: Path construction with and without grouping.
- `mark_download_failed()` / `remove_failed_marker()`: Create, update, and
  remove markers using temp directories.
- `is_download_blocked_by_failure()`: Recent marker blocks, stale marker allows
  retry, missing marker allows download, corrupted marker allows retry.
- Retention: `.failed` files are removed alongside recordings when past the
  cutoff date.

### Time-sensitive logic

Tests write markers with backdated timestamps to simulate stale markers, same
approach as the existing `today` override pattern.
