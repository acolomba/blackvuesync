# --include / --exclude filter rework implementation plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to
> implement this plan task-by-task.

**Goal:** Replace the half-implemented `--filter` option with validated
`--include` and `--exclude` options that support comma-separated type/direction
codes.

**Architecture:** Extract recording type and direction characters into shared
constants. Add a `parse_filter` argparse type function (following the existing
`parse_skip_metadata` pattern). Replace `get_filtered_recordings` with a
function that applies include then exclude logic. Wire through `sync()` and
update Docker wrapper, integration tests, and README.

**Tech Stack:** Python 3.9+ stdlib only (argparse, re). Pytest for unit tests.
Behave for integration tests. Bash for Docker wrapper.

---

## Task 1: Extract shared constants

Files:

- Modify: `blackvuesync.py:212-219` (filename_re) and surrounding area

### Step 1: Add constants before filename_re

Add two constants right before `filename_re` (line 212), after the existing
`RECORDING_EXTENSIONS` constant area. These are the single source of truth for
valid type and direction characters:

```python
RECORDING_TYPES = "NEPMIOATBRXGDLYF"
RECORDING_DIRECTIONS = "FRIO"
```

### Step 2: Update filename_re to use the constants

Change the hard-coded character classes in `filename_re` to reference the new
constants:

```python
filename_re = re.compile(
    rf"""(?P<base_filename>(?P<year>\d\d\d\d)(?P<month>\d\d)(?P<day>\d\d)
    _(?P<hour>\d\d)(?P<minute>\d\d)(?P<second>\d\d))
    _(?P<type>[{RECORDING_TYPES}])
    (?P<direction>[{RECORDING_DIRECTIONS}])
    (?P<upload>[LS]?)
    \.(?P<extension>mp4)""",
    re.VERBOSE,
)
```

### Step 3: Run existing tests to verify no regression

Run: `pytest test/blackvuesync_test.py -v`
Expected: All existing tests pass (especially `test_to_recording`).

### Step 4: Commit

```bash
git add blackvuesync.py
git commit -m "Extract recording type and direction constants"
```

---

## Task 2: Add parse_filter and unit tests (TDD)

Files:

- Modify: `blackvuesync.py` (near `parse_skip_metadata` at line 121)
- Modify: `test/blackvuesync_test.py` (near `test_parse_skip_metadata` at
  line 664)

### Step 1: Write failing tests for parse_filter

Add parametrized tests after the `test_parse_skip_metadata_invalid` tests
(around line 686). Follow the same pattern as `test_parse_skip_metadata`:

```python
@pytest.mark.parametrize(
    "value, expected",
    [
        ("PF", ("PF",)),
        ("P", ("P",)),
        ("PF,PR", ("PF", "PR")),
        ("P,NF", ("P", "NF")),
        ("N", ("N",)),
        ("NF,NR,NI,NO", ("NF", "NR", "NI", "NO")),
    ],
)
def test_parse_filter(value: str, expected: tuple[str, ...]) -> None:
    assert blackvuesync.parse_filter(value) == expected


@pytest.mark.parametrize(
    "value",
    ["ZZ", "PX", "ABC", "", "P,", ",P", "P,,N", "pf", "1F"],
)
def test_parse_filter_invalid(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        blackvuesync.parse_filter(value)
```

### Step 2: Run tests to verify they fail

Run: `pytest test/blackvuesync_test.py::test_parse_filter -v`
Expected: FAIL with `AttributeError: module 'blackvuesync' has no attribute
'parse_filter'`

### Step 3: Implement parse_filter

Add `parse_filter` right after `parse_skip_metadata` (line 130) in
`blackvuesync.py`:

```python
def parse_filter(value: str) -> tuple[str, ...]:
    """parses and validates a comma-separated filter of recording type/direction codes"""
    codes = value.split(",")
    for code in codes:
        if len(code) == 1:
            if code not in RECORDING_TYPES:
                raise argparse.ArgumentTypeError(
                    f"invalid filter code '{code}': unknown recording type"
                    f" (valid: {', '.join(RECORDING_TYPES)})"
                )
        elif len(code) == 2:
            if code[0] not in RECORDING_TYPES:
                raise argparse.ArgumentTypeError(
                    f"invalid filter code '{code}': unknown recording type"
                    f" '{code[0]}' (valid: {', '.join(RECORDING_TYPES)})"
                )
            if code[1] not in RECORDING_DIRECTIONS:
                raise argparse.ArgumentTypeError(
                    f"invalid filter code '{code}': unknown direction"
                    f" '{code[1]}' (valid: {', '.join(RECORDING_DIRECTIONS)})"
                )
        else:
            raise argparse.ArgumentTypeError(
                f"invalid filter code '{code}': must be 1 or 2 characters"
                " (type, or type + direction)"
            )
    return tuple(codes)
```

### Step 4: Run tests to verify they pass

Run: `pytest test/blackvuesync_test.py::test_parse_filter test/blackvuesync_test.py::test_parse_filter_invalid -v`
Expected: All pass.

### Step 5: Commit

```bash
git add blackvuesync.py test/blackvuesync_test.py
git commit -m "Add parse_filter with validation and unit tests"
```

---

## Task 3: Replace get_filtered_recordings and unit tests (TDD)

Files:

- Modify: `blackvuesync.py:727-735` (`get_filtered_recordings`)
- Modify: `test/blackvuesync_test.py`

### Step 1: Write failing tests for the new matching function

Add tests after the `test_parse_filter_invalid` tests. Use `Recording`
objects with known type/direction values. The function name changes to
`apply_recording_filters`:

```python
def _recording(type: str, direction: str) -> blackvuesync.Recording:
    """creates a minimal Recording for filter tests"""
    return blackvuesync.Recording(
        filename=f"20250101_120000_{type}{direction}.mp4",
        base_filename="20250101_120000",
        group_name=None,
        datetime=datetime.datetime(2025, 1, 1, 12, 0, 0),
        type=type,
        direction=direction,
    )


class TestApplyRecordingFilters:
    """tests for apply_recording_filters"""

    def test_no_filters_returns_all(self) -> None:
        recordings = [_recording("N", "F"), _recording("P", "R")]
        result = blackvuesync.apply_recording_filters(recordings, None, None)
        assert result == recordings

    def test_include_type_only(self) -> None:
        recordings = [
            _recording("N", "F"),
            _recording("N", "R"),
            _recording("P", "F"),
        ]
        result = blackvuesync.apply_recording_filters(
            recordings, ("N",), None
        )
        assert result == [recordings[0], recordings[1]]

    def test_include_type_and_direction(self) -> None:
        recordings = [
            _recording("N", "F"),
            _recording("N", "R"),
            _recording("P", "F"),
        ]
        result = blackvuesync.apply_recording_filters(
            recordings, ("NF",), None
        )
        assert result == [recordings[0]]

    def test_include_multiple_codes(self) -> None:
        recordings = [
            _recording("N", "F"),
            _recording("P", "F"),
            _recording("E", "F"),
        ]
        result = blackvuesync.apply_recording_filters(
            recordings, ("N", "PF"), None
        )
        assert result == [recordings[0], recordings[1]]

    def test_exclude_type_only(self) -> None:
        recordings = [
            _recording("N", "F"),
            _recording("P", "F"),
            _recording("E", "F"),
        ]
        result = blackvuesync.apply_recording_filters(
            recordings, None, ("P",)
        )
        assert result == [recordings[0], recordings[2]]

    def test_exclude_type_and_direction(self) -> None:
        recordings = [
            _recording("N", "F"),
            _recording("N", "R"),
        ]
        result = blackvuesync.apply_recording_filters(
            recordings, None, ("NR",)
        )
        assert result == [recordings[0]]

    def test_include_and_exclude_combined(self) -> None:
        recordings = [
            _recording("N", "F"),
            _recording("N", "R"),
            _recording("P", "F"),
        ]
        result = blackvuesync.apply_recording_filters(
            recordings, ("N",), ("NR",)
        )
        assert result == [recordings[0]]

    def test_empty_result(self) -> None:
        recordings = [_recording("N", "F")]
        result = blackvuesync.apply_recording_filters(
            recordings, ("P",), None
        )
        assert result == []
```

### Step 2: Run tests to verify they fail

Run: `pytest test/blackvuesync_test.py::TestApplyRecordingFilters -v`
Expected: FAIL with `AttributeError: module 'blackvuesync' has no attribute
'apply_recording_filters'`

### Step 3: Implement apply_recording_filters

Replace `get_filtered_recordings` (line 727) with:

```python
def _matches_filter(recording: Recording, code: str) -> bool:
    """checks if a recording matches a single filter code"""
    if len(code) == 1:
        return recording.type == code
    return f"{recording.type}{recording.direction}" == code


def apply_recording_filters(
    recordings: list[Recording],
    include: tuple[str, ...] | None,
    exclude: tuple[str, ...] | None,
) -> list[Recording]:
    """returns recordings filtered by include/exclude codes"""
    result = recordings
    if include is not None:
        result = [
            r for r in result if any(_matches_filter(r, c) for c in include)
        ]
    if exclude is not None:
        result = [
            r
            for r in result
            if not any(_matches_filter(r, c) for c in exclude)
        ]
    return result
```

### Step 4: Run tests to verify they pass

Run: `pytest test/blackvuesync_test.py::TestApplyRecordingFilters -v`
Expected: All pass.

### Step 5: Commit

```bash
git add blackvuesync.py test/blackvuesync_test.py
git commit -m "Add apply_recording_filters with include/exclude logic"
```

---

## Task 4: Wire up argparse and sync()

Files:

- Modify: `blackvuesync.py:787-815` (`sync` function)
- Modify: `blackvuesync.py:937-943` (argparse `--filter` definition)
- Modify: `blackvuesync.py:1063` (`main` call to `sync`)

### Step 1: Replace --filter argparse definition with --include and --exclude

Remove the `--filter` argument (lines 937-943) and replace with:

```python
    arg_parser.add_argument(
        "-i",
        "--include",
        default=None,
        type=parse_filter,
        help="downloads only recordings matching the given codes; each code"
        " is a recording type optionally followed by a camera direction;"
        " e.g. --include P,NF downloads all Parking and Normal Front"
        " recordings",
    )
    arg_parser.add_argument(
        "-e",
        "--exclude",
        default=None,
        type=parse_filter,
        help="excludes recordings matching the given codes; takes priority"
        " over --include; e.g. --include N --exclude NR downloads all Normal"
        " recordings except Normal Rear",
    )
```

### Step 2: Update sync() signature and body

Change the `sync` function signature to accept `include` and `exclude`
instead of `recording_filter`. Update the call to `apply_recording_filters`:

```python
def sync(
    address: str,
    destination: str,
    grouping: str,
    download_priority: str,
    include: tuple[str, ...] | None,
    exclude: tuple[str, ...] | None,
) -> None:
```

And the filter call becomes:

```python
    # filters recordings according to include/exclude options
    current_dashcam_recordings = apply_recording_filters(
        current_dashcam_recordings, include, exclude
    )
```

### Step 3: Update main() call to sync()

Change line 1063 from:

```python
sync(args.address, destination, grouping, args.priority, args.filter)
```

to:

```python
sync(args.address, destination, grouping, args.priority, args.include, args.exclude)
```

### Step 4: Update test_main mocks

In `test/blackvuesync_test.py`, find the existing mock for `sync` (around
lines 768 and 786). The mock lambda signatures need to accept the new
parameters. Change `_filter` to `_include, _exclude`. Also update the
`filter=None` in `parse_args` return to `include=None, exclude=None`.

### Step 5: Run all tests

Run: `pytest test/blackvuesync_test.py -v`
Expected: All pass.

### Step 6: Commit

```bash
git add blackvuesync.py test/blackvuesync_test.py
git commit -m "Replace --filter with --include and --exclude options"
```

---

## Task 5: Docker wrapper support

Files:

- Modify: `blackvuesync.sh`

### Step 1: Add INCLUDE and EXCLUDE env var handling

Add after the existing `skip_metadata` line (near end of variable
declarations):

```bash
# include option if INCLUDE set
include=${INCLUDE:+--include $INCLUDE}

# exclude option if EXCLUDE set
exclude=${EXCLUDE:+--exclude $EXCLUDE}
```

### Step 2: Add to command line

Append `${include} ${exclude}` to the final command invocation.

### Step 3: Commit

```bash
git add blackvuesync.sh
git commit -m "Add INCLUDE and EXCLUDE env vars to Docker wrapper"
```

---

## Task 6: Integration test step definitions

Files:

- Modify: `features/steps/blackvuesync_steps.py`

### Step 1: Update execute_blackvuesync and helpers

In all three functions (`execute_blackvuesync`, `_execute_direct`,
`_execute_docker`):

- Replace `filter_list: list[str] | None = None` parameter with
  `include: str | None = None` and `exclude: str | None = None`
- In `_execute_direct`: replace the `-f` / `filter_list` cmd building with
  `-i` / `include` and `-e` / `exclude`
- In `_execute_docker`: replace the `NotImplementedError` for filter with
  `INCLUDE` and `EXCLUDE` env vars

For `_execute_direct`, the filter command building changes from:

```python
    if filter_list:
        cmd.append("-f")
        cmd.extend(filter_list)
```

to:

```python
    if include:
        cmd.extend(["-i", include])

    if exclude:
        cmd.extend(["-e", exclude])
```

For `_execute_docker`, replace:

```python
    if filter_list:
        raise NotImplementedError(
            "filter option not supported in docker implementation"
        )
```

with:

```python
    if include:
        container.with_env("INCLUDE", include)

    if exclude:
        container.with_env("EXCLUDE", exclude)
```

### Step 2: Run existing integration tests to check nothing breaks

Run: `behave`
Expected: All existing scenarios pass (no scenario uses filter yet).

### Step 3: Commit

```bash
git add features/steps/blackvuesync_steps.py
git commit -m "Update integration test steps for include/exclude"
```

---

## Task 7: Integration test scenarios

Files:

- Create: `features/sync_filter.feature`
- Create: `features/steps/filter_steps.py`

### Step 1: Create step definitions

Create `features/steps/filter_steps.py`:

```python
"""include/exclude filter step definitions"""

from __future__ import annotations

from behave import when
from behave.runner import Context

from features.steps.blackvuesync_steps import execute_blackvuesync


@when('blackvuesync runs with include "{include}"')
def run_blackvuesync_with_include(context: Context, include: str) -> None:
    """executes blackvuesync with --include option."""
    execute_blackvuesync(
        context,
        context.mock_dashcam_address,
        str(context.dest_dir),
        context.scenario_token,
        include=include,
    )


@when('blackvuesync runs with include "{include}" exclude "{exclude}"')
def run_blackvuesync_with_include_exclude(
    context: Context, include: str, exclude: str
) -> None:
    """executes blackvuesync with --include and --exclude options."""
    execute_blackvuesync(
        context,
        context.mock_dashcam_address,
        str(context.dest_dir),
        context.scenario_token,
        include=include,
        exclude=exclude,
    )


@when('blackvuesync runs with exclude "{exclude}"')
def run_blackvuesync_with_exclude(context: Context, exclude: str) -> None:
    """executes blackvuesync with --exclude option."""
    execute_blackvuesync(
        context,
        context.mock_dashcam_address,
        str(context.dest_dir),
        context.scenario_token,
        exclude=exclude,
    )
```

### Step 2: Create feature file

Create `features/sync_filter.feature`. Use types and directions from the
`Given` step that creates recordings, then verify only the expected subset
is downloaded. The existing step `recordings for the past "{period}" of types
"{recording_types}", directions "{recording_directions}"` sets up recordings
with specific types and directions. The existing `then` step
`all the recordings are downloaded` checks all expected recordings are present.
We need to use the more specific verification steps.

Look at existing feature files for the assertion pattern. We need to verify
that only recordings matching the filter are present. The existing `then`
steps in `downloaded_recordings_steps.py` check for recordings by listing
files. We should check that the destination only contains recordings matching
our filter.

```gherkin
Feature: Sync with include/exclude filters

  Scenario: Include by type downloads all directions
    Given recordings for the past "1d" of types "N,P", directions "F,R"
    When blackvuesync runs with include "N"
    Then blackvuesync exits with code 0
    Then the destination contains "N" recordings
    Then the destination does not contain "P" recordings

  Scenario: Include by type and direction
    Given recordings for the past "1d" of types "N,P", directions "F,R"
    When blackvuesync runs with include "NF"
    Then blackvuesync exits with code 0
    Then the destination contains "NF" recordings
    Then the destination does not contain "NR" recordings
    Then the destination does not contain "P" recordings

  Scenario: Exclude by type
    Given recordings for the past "1d" of types "N,P,E", directions "F"
    When blackvuesync runs with exclude "P"
    Then blackvuesync exits with code 0
    Then the destination contains "N" recordings
    Then the destination contains "E" recordings
    Then the destination does not contain "P" recordings

  Scenario: Include and exclude combined
    Given recordings for the past "1d" of types "N", directions "F,R"
    When blackvuesync runs with include "N" exclude "NR"
    Then blackvuesync exits with code 0
    Then the destination contains "NF" recordings
    Then the destination does not contain "NR" recordings

  Scenario: Include multiple codes
    Given recordings for the past "1d" of types "N,P,E", directions "F"
    When blackvuesync runs with include "N,E"
    Then blackvuesync exits with code 0
    Then the destination contains "N" recordings
    Then the destination contains "E" recordings
    Then the destination does not contain "P" recordings
```

Note: the `then` steps for checking recording type/direction presence will
need to be added to the step definitions. Add to `filter_steps.py`:

```python
import os
import re


_recording_filename_re = re.compile(
    r"^\d{8}_\d{6}_([NEPMIOATBRXGDLYF])([FRIO])[LS]?\.(mp4|thm|3gf|gps)$"
)


@then('the destination contains "{code}" recordings')
def destination_contains_recordings(context: Context, code: str) -> None:
    """verifies that the destination contains recordings matching the code."""
    matching = _find_recordings_matching(context.dest_dir, code)
    assert matching, f"expected recordings matching '{code}' but found none"


@then('the destination does not contain "{code}" recordings')
def destination_does_not_contain_recordings(
    context: Context, code: str
) -> None:
    """verifies that the destination does not contain recordings matching the
    code."""
    matching = _find_recordings_matching(context.dest_dir, code)
    assert not matching, (
        f"expected no recordings matching '{code}' but found: {matching}"
    )


def _find_recordings_matching(dest_dir: str, code: str) -> list[str]:
    """finds recording files in dest_dir matching a filter code."""
    matching = []
    for root, _dirs, files in os.walk(str(dest_dir)):
        for filename in files:
            m = _recording_filename_re.match(filename)
            if m:
                rec_type, rec_direction = m.group(1), m.group(2)
                if len(code) == 1 and rec_type == code:
                    matching.append(filename)
                elif len(code) == 2 and rec_type == code[0] and rec_direction == code[1]:
                    matching.append(filename)
    return matching
```

Add the `then` import at the top:

```python
from behave import then, when
```

### Step 3: Run integration tests

Run: `behave features/sync_filter.feature`
Expected: All scenarios pass.

### Step 4: Run full test suite

Run: `pytest test/blackvuesync_test.py -v && behave`
Expected: All pass.

### Step 5: Commit

```bash
git add features/sync_filter.feature features/steps/filter_steps.py
git commit -m "Add integration tests for include/exclude filters"
```

---

## Task 8: README documentation

Files:

- Modify: `README.md` (around line 130, after `--skip-metadata`)

### Step 1: Add --include and --exclude documentation

Add after the `--skip-metadata` bullet (line 130) and before `--quiet`:

```markdown
* `--include`: Downloads only recordings matching the given codes. Each code is
  a recording type letter optionally followed by a camera direction letter,
  comma-separated. For example, `--include P,NF` downloads all Parking
  recordings and Normal Front recordings. See the table below for valid codes.
* `--exclude`: Excludes recordings matching the given codes, same format as
  `--include`. Takes priority over `--include`. For example,
  `--include N --exclude NR` downloads all Normal recordings except Normal
  Rear.
```

Also add a reference table after the options list and before the "Unattended
Usage" section. This table lists the type and direction codes:

```markdown
#### Recording type and direction codes

Recording type codes:

| Code | Type |
| ---- | ---- |
| N | Normal |
| E | Event |
| P | Parking |
| M | Manual |
| I | Impact |
| O | Overspeed |
| A | Acceleration |
| T | Cornering |
| B | Braking |
| R | Geofence (R) |
| X | Geofence (X) |
| G | Geofence (G) |
| D | DMS (D) |
| L | DMS (L) |
| Y | DMS (Y) |
| F | DMS (F) |

Direction codes:

| Code | Direction |
| ---- | --------- |
| F | Front |
| R | Rear |
| I | Interior |
| O | Optional |
```

### Step 2: Update Docker documentation

Find the Docker environment variable documentation section and add `INCLUDE`
and `EXCLUDE` env vars.

### Step 3: Commit

```bash
git add README.md
git commit -m "Document --include and --exclude options in README"
```

---

## Task 9: Final verification

### Step 1: Run full test suite

Run: `pytest test/blackvuesync_test.py -v && behave`
Expected: All pass.

### Step 2: Manual smoke test

Run: `python3 blackvuesync.py --help`
Expected: Shows `--include` and `--exclude` in help output, no `--filter`.

### Step 3: Test validation error

Run: `python3 blackvuesync.py 192.168.1.99 --include ZZ`
Expected: Error message about invalid filter code.
