"""destination setup and verification step definitions."""

from __future__ import annotations

import datetime
import hashlib
from collections.abc import Iterable, Set

from behave import given, then, when
from behave.runner import Context

from features.lib.recordings import (
    LOCK_FILENAME,
    MOCK_FILES_DIR,
    copy_fixture_files,
    create_recording_files,
    generate_recording_filenames,
    grouped_path,
    list_failure_markers,
    list_files,
    select_by_codes,
    select_by_period,
    servable_filenames,
)


def _servable_recordings(context: Context) -> set[str]:
    """returns the dashcam recording files blackvuesync downloads."""
    return servable_filenames(
        context.dashcam_recordings, context.legacy_api, context.skip_metadata
    )


def _grouped_paths(context: Context, filenames: Iterable[str]) -> set[str]:
    """returns the destination paths the latest run downloads the files to."""
    return {grouped_path(filename, context.grouping) for filename in filenames}


def _expected_recordings(context: Context) -> set[str]:
    """returns the destination paths of the pre-existing and servable recording files.

    the pre-existing files stay where the scenario puts them; blackvuesync
    downloads the servable files under the grouping of the latest run.
    """
    preexisting: set[str] = context.preexisting_recordings
    return preexisting | _grouped_paths(context, _servable_recordings(context))


def _failed_paths(context: Context) -> set[str]:
    """returns the destination paths of the files the dashcam fails to serve."""
    return _grouped_paths(context, context.failed_recordings)


def _destination_files(context: Context) -> set[str]:
    """returns the destination files the recording checks compare.

    the files are paths relative to the destination. the lock file and the
    markers of the failed recordings are left out, so leftover temporary
    dotfiles, stray files, and unexpected markers remain.
    """
    expected_extras = {LOCK_FILENAME}
    expected_extras.update(f"{path}.failed" for path in _failed_paths(context))
    return list_files(context.dest_dir) - expected_extras


def _assert_same_files(actual: Set[str], expected: Set[str], label: str) -> None:
    """asserts two sets of filenames are equal, listing the differences."""
    assert actual == expected, (
        f"{label} differ; missing: {sorted(expected - actual)}; "
        f"unexpected: {sorted(actual - expected)}"
    )


def _digest(data: bytes) -> str:
    """returns the sha256 hex digest of the content."""
    return hashlib.sha256(data).hexdigest()


def _destination_recordings(
    context: Context,
    period_start: str,
    period_end: str,
    recording_types: str,
    recording_directions: str,
) -> None:
    """copies fixture recordings dated in the period into the destination."""
    context.preexisting_recordings.update(
        create_recording_files(
            context.dest_dir,
            recording_types,
            recording_directions,
            period_start,
            period_end,
        )
    )


@given(
    'the destination has recordings between "{period_start}" and "{period_end}" ago of types "{recording_types}", directions "{recording_directions}"'
)
def destination_recordings_between(
    context: Context,
    period_start: str,
    period_end: str,
    recording_types: str,
    recording_directions: str,
) -> None:
    """puts recordings dated in the period in the destination."""
    _destination_recordings(
        context, period_start, period_end, recording_types, recording_directions
    )


@given(
    'the destination has recordings for the past "{period}" of types "{recording_types}", directions "{recording_directions}"'
)
def destination_recordings_past(
    context: Context, period: str, recording_types: str, recording_directions: str
) -> None:
    """puts recordings dated up to today in the destination."""
    _destination_recordings(
        context, period, "0d", recording_types, recording_directions
    )


@given(
    'the destination has the dashcam recordings between "{period_start}" and "{period_end}" ago'
)
def destination_dashcam_recordings(
    context: Context, period_start: str, period_end: str
) -> None:
    """puts the dashcam recordings dated in the period in the destination."""
    filenames = select_by_period(context.dashcam_recordings, period_start, period_end)
    if not filenames:
        raise ValueError(
            f"the dashcam lists no recordings between {period_start} and "
            f"{period_end} ago"
        )
    copy_fixture_files(context.dest_dir, filenames)
    context.preexisting_recordings.update(filenames)


def _partial_download(context: Context, filename: str) -> None:
    """writes the first half of the fixture video to the temporary dotfile.

    blackvuesync downloads into .<filename> in the destination itself and
    renames the file once the download completes.
    """
    content = (MOCK_FILES_DIR / "mock.mp4").read_bytes()
    (context.dest_dir / f".{filename}").write_bytes(content[: len(content) // 2])


@given("the destination has a partial download of a dashcam recording")
def destination_dashcam_partial_download(context: Context) -> None:
    """puts an interrupted download of the first dashcam video in the destination."""
    videos = sorted(f for f in context.dashcam_recordings if f.endswith(".mp4"))
    if not videos:
        raise ValueError("the dashcam lists no videos")
    _partial_download(context, videos[0])


@given('the destination has a partial download of a recording from "{period}" ago')
def destination_unlisted_partial_download(context: Context, period: str) -> None:
    """puts an interrupted download of a video the dashcam does not list."""
    video = next(
        f
        for f in generate_recording_filenames("N", "F", period, period)
        if f.endswith(".mp4")
    )
    if video in context.dashcam_recordings:
        raise ValueError(f"the dashcam lists the recording {video}")
    _partial_download(context, video)


@when("the failure markers age by {hours:d} hours")
def age_failure_markers(context: Context, hours: int) -> None:
    """moves the timestamp in each .failed marker file back by the hours."""
    markers = [context.dest_dir / m for m in list_failure_markers(context.dest_dir)]
    if not markers:
        raise ValueError(f"the destination has no failure markers: {context.dest_dir}")

    for marker in markers:
        failed_at = datetime.datetime.fromisoformat(marker.read_text().strip())
        aged = failed_at - datetime.timedelta(hours=hours)
        marker.write_text(aged.isoformat())


@then("the destination contains no recordings")
def assert_no_recordings(context: Context) -> None:
    """verifies the destination holds no recordings and no stray files."""
    _assert_same_files(_destination_files(context), set(), "destination files")


@then("the destination contains all the recordings")
def assert_all_recordings(context: Context) -> None:
    """verifies the destination holds exactly the expected recordings."""
    _assert_same_files(
        _destination_files(context),
        _expected_recordings(context),
        "destination files",
    )


@then("the destination contains all but the failed recordings")
def assert_all_but_failed_recordings(context: Context) -> None:
    """verifies the destination holds the expected recordings less the failed ones."""
    _assert_same_files(
        _destination_files(context),
        _expected_recordings(context) - _failed_paths(context),
        "destination files",
    )


@then(
    'the destination contains only the recordings between "{period_start}" and "{period_end}" ago'
)
def assert_only_recordings_between(
    context: Context, period_start: str, period_end: str
) -> None:
    """verifies the destination holds exactly the expected recordings in the period.

    the period counts back from the date of the latest run; a run across
    midnight passes with either date.
    """
    actual = _destination_files(context)
    candidates = [
        select_by_period(_expected_recordings(context), period_start, period_end, day)
        for day in context.run_dates
    ]
    expected = actual if actual in candidates else candidates[0]
    _assert_same_files(actual, expected, "destination files")


@then('the destination contains only the "{codes}" recordings')
def assert_only_code_recordings(context: Context, codes: str) -> None:
    """verifies the destination holds exactly the recordings the codes select.

    the codes are comma-separated --include style codes. blackvuesync filters
    only the dashcam recordings, so the pre-existing recordings remain.
    """
    preexisting: set[str] = context.preexisting_recordings
    selected = select_by_codes(_servable_recordings(context), codes.split(","))
    _assert_same_files(
        _destination_files(context),
        preexisting | _grouped_paths(context, selected),
        "destination files",
    )


@then('the destination contains no "{extension}" files')
def assert_no_extension_files(context: Context, extension: str) -> None:
    """verifies no destination file has the extension."""
    _assert_same_files(
        {f for f in list_files(context.dest_dir) if f.endswith(f".{extension}")},
        set(),
        f".{extension} files",
    )


@then("the destination contains failure markers for the failed recordings")
def assert_failure_markers(context: Context) -> None:
    """verifies the destination holds a .failed marker for each failed recording.

    the destination holds no other markers.
    """
    _assert_same_files(
        list_failure_markers(context.dest_dir),
        {f"{path}.failed" for path in _failed_paths(context)},
        "failure markers",
    )


@then("the destination contains no failure markers")
def assert_no_failure_markers(context: Context) -> None:
    """verifies the destination holds no .failed marker files."""
    _assert_same_files(list_failure_markers(context.dest_dir), set(), "failure markers")


@then('the "{extension}" files in the destination match the mock fixture')
def assert_files_match_fixture(context: Context, extension: str) -> None:
    """verifies each expected file with the extension holds the fixture content.

    the check compares full sha256 digests; the failure message shortens them.
    """
    expected_names = {
        f for f in _expected_recordings(context) if f.endswith(f".{extension}")
    }
    if not expected_names:
        raise ValueError(f"the scenario expects no .{extension} files")

    fixture_digest = _digest((MOCK_FILES_DIR / f"mock.{extension}").read_bytes())
    actual = {
        path.relative_to(context.dest_dir).as_posix(): _digest(path.read_bytes())
        for path in context.dest_dir.rglob(f"*.{extension}")
        if path.is_file()
    }
    expected = dict.fromkeys(expected_names, fixture_digest)
    mismatched = {name: d[:16] for name, d in actual.items() if expected.get(name) != d}
    assert actual == expected, (
        f".{extension} files differ from the fixture (digest {fixture_digest[:16]}); "
        f"mismatched: {mismatched}; missing: {sorted(expected.keys() - actual.keys())}"
    )
