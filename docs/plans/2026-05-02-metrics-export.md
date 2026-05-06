# Metrics export implementation plan

**Goal:** Add opt-in Prometheus-format metrics for sync health, file pull
failures, and time since the last successful file pull while preserving the
current cron-style execution model.

**Architecture:** Keep `blackvuesync.py` as a one-shot CLI. During each run,
collect metrics in a small stats object and emit them at process shutdown to one
or both configured sinks:

- `--metrics-file PATH`: writes Prometheus text exposition format atomically.
- `--metrics-pushgateway-url URL`: pushes the same exposition payload to a
  Prometheus Pushgateway for Kubernetes CronJob-style deployments.
- `--metrics-state-file PATH`: persists cross-run metric state. Defaults to a
  hidden state file under the destination directory when metrics are enabled.

**Tech Stack:** Python 3.9+ stdlib only. Use `urllib.request` for Pushgateway
HTTP calls and hand-render the limited Prometheus text format needed here.
Pytest for unit tests. Bash for Docker wrapper env wiring.

---

## Metrics

Primary metrics:

- `blackvuesync_last_run_timestamp_seconds`: completion timestamp for the most
  recent run.
- `blackvuesync_last_run_success`: sync result for the last run. This is `0`
  when the sync could not reach/list/download from the camera, even if `--cron`
  maps the process exit code to `0`.
- `blackvuesync_last_run_exit_code`: process exit code for the last run.
- `blackvuesync_last_successful_file_pull_timestamp_seconds`: timestamp of the
  most recent successful file download, persisted across runs.
- `blackvuesync_file_download_failures_last_run{reason="..."}`: count of file
  download failures observed in the most recent run.
- `blackvuesync_files_downloaded_last_run`: count of files downloaded in the
  most recent run.

Secondary metrics:

- `blackvuesync_run_duration_seconds`: elapsed runtime for the sync command.
- `blackvuesync_dashcam_recordings_seen`: recording count returned by the
  dashcam index.
- `blackvuesync_recordings_selected`: recording count after cutoff and
  include/exclude filtering.
- `blackvuesync_bytes_downloaded_last_run`: bytes downloaded in the current run
  when content length is available.
- `blackvuesync_destination_disk_used_ratio`: destination disk usage ratio.
- `blackvuesync_failed_marker_files`: count of `.failed` marker files under the
  destination.

Failure reasons should start coarse and stable: `http`, `network`, `timeout`,
`disk`, and `unknown`.

Do not expose per-process `*_total` counters in the initial implementation.
Because the program exits after each run, download and failure counts should be
last-run gauges unless cumulative counters are explicitly persisted in a future
change.

Dry runs should emit run metrics but must not update
`blackvuesync_last_successful_file_pull_timestamp_seconds`.

---

## Task 1: Add metrics configuration

Files:

- Modify: `blackvuesync.py`
- Modify: `test/blackvuesync_test.py`

Steps:

1. Add argparse options:
   - `--metrics-file PATH`
   - `--metrics-pushgateway-url URL`
   - `--metrics-job NAME`, defaulting to `blackvuesync`
   - `--metrics-instance NAME`, defaulting to the dashcam address
   - `--metrics-state-file PATH`, defaulting to a file under the destination
     when metrics are enabled.
2. Validate the Pushgateway URL with `urllib.parse`.
3. Default the state file to
   `<destination>/.blackvuesync.metrics-state.json` when any metrics sink is
   enabled and no explicit state file is provided.
4. Add unit tests for defaults, explicit state override, and invalid
   Pushgateway URLs.

---

## Task 2: Add metrics data model

Files:

- Modify: `blackvuesync.py`
- Modify: `test/blackvuesync_test.py`

Steps:

1. Add a `SyncMetrics` dataclass with fields for timestamps, run result,
   last-run gauges, and per-reason failure counts.
2. Add helper methods for:
   - recording a successful file download,
   - recording a failed file download,
   - recording selected/seen recording counts,
   - finalizing run outcome and duration.
3. Add tests for the helper methods without doing network or filesystem work.

---

## Task 3: Persist last successful file pull timestamp

Files:

- Modify: `blackvuesync.py`
- Modify: `test/blackvuesync_test.py`

Steps:

1. Add small JSON state load/save helpers.
2. Store only stable cross-run values initially:
   - `last_successful_file_pull_timestamp_seconds`
3. Load state before sync starts when metrics are enabled.
4. Save state after metrics are finalized, but only after successful state
   serialization.
5. Do not update last-successful state during dry runs.
6. Add tests for missing, valid, corrupt, and dry-run state behavior. Corrupt
   state should not fail the sync; it should be ignored with a warning.

---

## Task 4: Instrument sync flow

Files:

- Modify: `blackvuesync.py`
- Modify: `test/blackvuesync_test.py`

Steps:

1. Thread the metrics object through `main()`, `sync()`,
   `download_recording()`, and `download_file()`.
2. Count dashcam recordings seen after parsing the dashcam index.
3. Count recordings selected after cutoff and include/exclude filters.
4. Record destination disk usage before each recording download check.
5. Count successful file downloads and bytes downloaded in `download_file()`.
6. Count file download failures by reason in the existing exception handlers.
7. Count failed marker files during finalization or destination cleanup.
8. Record sync success separately from process exit code. In cron mode, expected
   dashcam unavailability may return exit code `0` but must still emit
   `blackvuesync_last_run_success 0`.

---

## Task 5: Render Prometheus text exposition

Files:

- Modify: `blackvuesync.py`
- Modify: `test/blackvuesync_test.py`

Steps:

1. Add a renderer that emits `# HELP`, `# TYPE`, and metric samples.
2. Keep labels low-cardinality. Do not include recording filenames as labels.
3. Escape label values according to Prometheus text format requirements.
4. Add snapshot-style unit tests for the rendered output.

---

## Task 6: Add metrics file sink

Files:

- Modify: `blackvuesync.py`
- Modify: `test/blackvuesync_test.py`

Steps:

1. Write metrics to a temporary sibling file.
2. Flush and `fsync` the temporary file.
3. Rename it atomically over the target path.
4. Add tests proving failed writes do not leave partial target files.

---

## Task 7: Add Pushgateway sink

Files:

- Modify: `blackvuesync.py`
- Modify: `test/blackvuesync_test.py`

Steps:

1. Build the Pushgateway endpoint as
   `/metrics/job/<metrics-job>/instance/<metrics-instance>`.
2. Use HTTP `PUT` so each run replaces the job's metric group.
3. Use a short timeout tied to the existing socket timeout where practical.
4. Treat Pushgateway failures as warnings by default so metrics delivery does
   not mask the sync exit result.
5. Add unit tests for the generated endpoint path and request method with a fake
   `urllib.request.urlopen`.

---

## Task 8: Wire Docker and documentation

Files:

- Modify: `blackvuesync.sh`
- Modify: `Dockerfile`
- Modify: `docker-compose.yml`
- Modify: `README.md`

Steps:

1. Add env-to-CLI wiring for:
   - `METRICS_FILE`
   - `METRICS_PUSHGATEWAY_URL`
   - `METRICS_JOB`
   - `METRICS_INSTANCE`
   - `METRICS_STATE_FILE`
2. Document host/Docker textfile usage.
3. Document Kubernetes CronJob Pushgateway usage.
4. Include example alert expressions for:
   - last run failed,
   - no run completed recently,
   - no successful file pull recently,
   - file download failures in the last hour.
5. Document that metrics delivery failures are warning-only and do not replace
   the sync exit result.

---

## Task 9: Validate end to end

Steps:

1. Run unit tests:
   - `python -m pytest -q`
2. Run Ruff:
   - `ruff check blackvuesync.py test/blackvuesync_test.py`
   - `ruff format --check blackvuesync.py test/blackvuesync_test.py`
3. Smoke-test metrics file output with an unreachable dashcam.
4. Smoke-test Pushgateway output against a small local HTTP server or test
   fixture.
5. Confirm existing text and JSON logging behavior still works.
6. Confirm dry-run metrics do not update persisted last-success state.
