# Skip Metadata Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `--skip-metadata` CLI option that lets users skip downloading companion metadata files (`.thm`, `.3gf`, `.gps`).

**Architecture:** A custom argparse type function validates the argument string, converting it to a `set[str]`. A module-level global `skip_metadata` holds the set. `download_recording()` checks the set before each companion download. Docker support via `SKIP_METADATA` env var in `blackvuesync.sh`.

**Tech Stack:** Python stdlib only (argparse). pytest for unit tests, behave for integration tests.

---

## Task 1: Add `parse_skip_metadata` type function and unit tests

Files: modify `blackvuesync.py:111` (insert before `parse_duration`), test `test/blackvuesync_test.py`

Step 1 -- Write the failing tests. Add to `test/blackvuesync_test.py`:

```python
@pytest.mark.parametrize(
    "value, expected",
    [
        ("t", {"t"}),
        ("3", {"3"}),
        ("g", {"g"}),
        ("t3g", {"t", "3", "g"}),
        ("3g", {"3", "g"}),
        ("tg", {"t", "g"}),
        ("t3", {"t", "3"}),
    ],
)
def test_parse_skip_metadata(value, expected):
    from blackvuesync import parse_skip_metadata

    assert parse_skip_metadata(value) == expected


@pytest.mark.parametrize("value", ["x", "t3x", "abc", "T", "mp4"])
def test_parse_skip_metadata_invalid(value):
    from blackvuesync import parse_skip_metadata

    with pytest.raises(argparse.ArgumentTypeError):
        parse_skip_metadata(value)
```

Step 2 -- Run tests to verify they fail.
Run: `pytest test/blackvuesync_test.py::test_parse_skip_metadata -v` -- expect FAIL with ImportError.

Step 3 -- Write minimal implementation. Add to `blackvuesync.py` before `parse_duration` (around line 111):

```python
# valid metadata type codes for --skip-metadata
VALID_METADATA_TYPES = frozenset("t3g")


def parse_skip_metadata(value: str) -> set[str]:
    """parses and validates the --skip-metadata argument"""
    types = set(value)
    invalid = types - VALID_METADATA_TYPES
    if invalid:
        invalid_char = sorted(invalid)[0]
        raise argparse.ArgumentTypeError(
            f"invalid value '{value}': unknown metadata type '{invalid_char}'"
            f" (valid: t, 3, g)"
        )
    return types
```

Step 4 -- Run tests to verify they pass.
Run: `pytest test/blackvuesync_test.py::test_parse_skip_metadata test/blackvuesync_test.py::test_parse_skip_metadata_invalid -v` -- expect PASS.

Step 5 -- Commit: `git add blackvuesync.py test/blackvuesync_test.py && git commit -m "Add parse_skip_metadata validation function (#14)"`

---

## Task 2: Add `--skip-metadata` CLI argument and module-level global

Files: modify `blackvuesync.py:80-91` (globals), `parse_args` function, `main` function.

Step 1 -- Add the module-level global after the `affinity_key` global (around line 91):

```python
# metadata types to skip downloading
skip_metadata: set[str] = set()  # pylint: disable=invalid-name
```

Step 2 -- Add the argparse argument to `parse_args()`, after `--retry-failed-after` and before `-v`/`--verbose`:

```python
    arg_parser.add_argument(
        "--skip-metadata",
        metavar="TYPES",
        default=set(),
        type=parse_skip_metadata,
        help="skips downloading metadata file types; t=thumbnail (.thm),"
        " 3=accelerometer (.3gf), g=gps (.gps); e.g. --skip-metadata t3g"
        " skips all metadata files",
    )
```

Step 3 -- Wire up the global in `main()`. Add `global skip_metadata` to the global declarations, and after `args = parse_args()`:

```python
    skip_metadata = args.skip_metadata
```

Step 4 -- Run all existing tests to verify nothing is broken.
Run: `pytest test/blackvuesync_test.py -v` -- expect all PASS.

Step 5 -- Commit: `git add blackvuesync.py && git commit -m "Add --skip-metadata CLI argument (#14)"`

---

## Task 3: Guard companion downloads and add integration tests

Files: modify `blackvuesync.py` `download_recording` function (lines 504-525), add `features/sync_basic.feature` scenarios, modify `features/steps/blackvuesync_steps.py`, modify `features/steps/downloaded_recordings_steps.py`.

Step 1 -- Write the failing integration tests. Add to `features/sync_basic.feature`:

```gherkin
  Scenario: Sync recordings skipping all metadata files
    Given recordings for the past "1d" of types "N", directions "F"
    When blackvuesync runs with skip-metadata "t3g"
    Then blackvuesync exits with code 0
    Then only mp4 files are downloaded

  Scenario: Sync recordings skipping only gps files
    Given recordings for the past "1d" of types "N", directions "F"
    When blackvuesync runs with skip-metadata "g"
    Then blackvuesync exits with code 0
    Then no gps files are downloaded
    Then all the recordings are downloaded
```

Add `skip_metadata` parameter to `execute_blackvuesync`, `_execute_direct`, and `_execute_docker`.

In `_execute_direct`, after the `retry_failed_after` block:

```python
    if skip_metadata:
        cmd.extend(["--skip-metadata", skip_metadata])
```

In `_execute_docker`, after the `retry_failed_after` block:

```python
    if skip_metadata:
        container.with_env("SKIP_METADATA", skip_metadata)
```

Add the new `when` step:

```python
@when('blackvuesync runs with skip-metadata "{skip_metadata}"')
def run_blackvuesync_with_skip_metadata(context: Context, skip_metadata: str) -> None:
    """executes blackvuesync with --skip-metadata option."""
    execute_blackvuesync(
        context,
        context.mock_dashcam_address,
        str(context.dest_dir),
        context.scenario_token,
        skip_metadata=skip_metadata,
    )
```

Add assertion steps to `features/steps/downloaded_recordings_steps.py`:

```python
@then("only mp4 files are downloaded")
def assert_only_mp4_files(context: Context) -> None:
    """verifies that only .mp4 files exist in the destination."""
    non_mp4_files = [
        f.name
        for f in context.dest_dir.rglob("*")
        if f.is_file() and not f.name.startswith(".") and not f.name.endswith(".mp4")
    ]
    assert_that(
        non_mp4_files,
        empty(),
        f"Expected only .mp4 files, but found: {non_mp4_files}",
    )


@then("no gps files are downloaded")
def assert_no_gps_files(context: Context) -> None:
    """verifies that no .gps files exist in the destination."""
    gps_files = [
        f.name
        for f in context.dest_dir.rglob("*")
        if f.is_file() and f.name.endswith(".gps")
    ]
    assert_that(
        gps_files,
        empty(),
        f"Expected no .gps files, but found: {gps_files}",
    )
```

Step 2 -- Run the integration tests to verify they fail.
Run: `behave features/sync_basic.feature` -- expect FAIL.

Step 3 -- Guard the downloads in `download_recording`. In `blackvuesync.py`, wrap each companion download block with a skip check.

For thumbnail (around line 504):

```python
    # downloads the thumbnail file
    if "t" not in skip_metadata:
        thm_filename = (
            f"{recording.base_filename}_{recording.type}{recording.direction}.thm"
        )
        downloaded, _ = download_file(
            base_url, thm_filename, destination, recording.group_name
        )
        any_downloaded |= downloaded
```

For accelerometer (around line 514):

```python
    # downloads the accelerometer data
    if "3" not in skip_metadata:
        tgf_filename = f"{recording.base_filename}_{recording.type}.3gf"
        downloaded, _ = download_file(
            base_url, tgf_filename, destination, recording.group_name
        )
        any_downloaded |= downloaded
```

For GPS (around line 522):

```python
    # downloads the gps data
    if "g" not in skip_metadata:
        gps_filename = f"{recording.base_filename}_{recording.type}.gps"
        downloaded, _ = download_file(
            base_url, gps_filename, destination, recording.group_name
        )
        any_downloaded |= downloaded
```

Step 4 -- Run integration tests to verify they pass.
Run: `behave features/sync_basic.feature` -- expect all PASS.

Step 5 -- Run all tests.
Run: `pytest test/blackvuesync_test.py -v && behave` -- expect all PASS.

Step 6 -- Commit: `git add blackvuesync.py features/ && git commit -m "Skip metadata file downloads based on --skip-metadata (#14)"`

---

## Task 4: Add Docker support in `blackvuesync.sh`

Files: modify `blackvuesync.sh`.

Step 1 -- Add the env var mapping after the `retry_failed_after` line:

```bash
# skip-metadata option if SKIP_METADATA set
skip_metadata=${SKIP_METADATA:+--skip-metadata $SKIP_METADATA}
```

Step 2 -- Add `${skip_metadata}` to the final command invocation line.

Step 3 -- Commit: `git add blackvuesync.sh && git commit -m "Add SKIP_METADATA env var for Docker support (#14)"`

---

## Task 5: Update README documentation

Files: modify `README.md` (options section, around line 129).

Step 1 -- Add documentation after the `--retry-failed-after` entry (line 129):

```markdown
* `--skip-metadata`: Skips downloading metadata file types. Takes a string of characters: `t` for thumbnail (`.thm`), `3` for accelerometer (`.3gf`), `g` for GPS (`.gps`). For example, `--skip-metadata t3g` skips all metadata files, downloading only the `.mp4` video recordings.
```

Also add `SKIP_METADATA` to the Docker environment variables table if one exists.

Step 2 -- Commit: `git add README.md && git commit -m "Document --skip-metadata option in README (#14)"`

---

## Task 6: Final verification

Step 1 -- Run all tests.
Run: `pytest test/blackvuesync_test.py -v && behave` -- expect all PASS.

Step 2 -- Manual smoke test.
Run: `python3 blackvuesync.py --help` and verify `--skip-metadata` appears in output.
Run: `python3 blackvuesync.py 192.168.1.99 --skip-metadata xyz 2>&1` and verify validation error.
