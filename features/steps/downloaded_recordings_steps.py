"""downloaded recording setup and verification step definitions"""

import re

from behave import given, then
from behave.runner import Context
from hamcrest import assert_that, empty, has_items

from features.lib.recordings import create_recording_files

# recording filename pattern - matches BlackVue recording filenames
# format: YYYYMMDD_HHMMSS_TD.ext where T=type, D=direction, ext=mp4/thm/3gf/gps
recording_filename_re = re.compile(
    r"^\d{8}_\d{6}_[NEPMIOATBRXGDLYF][FRIO]?[LS]?\.(mp4|thm|3gf|gps)$"
)


@given(
    'downloaded recordings for the past "{period}" of types "{recording_types}",'
    ' directions "{recording_directions}", other "{recording_others}"'
)
def downloaded_recordings(
    context: Context,
    period: str,
    recording_types: str,
    recording_directions: str,
    recording_others: str,
) -> None:
    """pre-populates destination with recordings matching the specified criteria."""
    # creates recording files directly in destination from mock files
    create_recording_files(
        context.dest_dir,
        period,
        recording_types,
        recording_directions,
        recording_others,
    )


@given(
    'downloaded recordings for the past "{period}" of types "{recording_types}",'
    ' directions "{recording_directions}"'
)
def downloaded_recordings_no_other(
    context: Context, period: str, recording_types: str, recording_directions: str
) -> None:
    """pre-populates destination with recordings matching the specified criteria."""
    downloaded_recordings(context, period, recording_types, recording_directions, "")


@then("all the recordings are downloaded")
def assert_all_recordings_downloaded(context: Context) -> None:
    """verifies that all recordings from the mock dashcam exist in the destination."""
    # validates prerequisites
    if not hasattr(context, "expected_recordings"):
        raise RuntimeError(
            "Cannot verify recordings: test scenario is missing 'Given recordings...' step. "
            "Expected recordings were never configured."
        )

    # gets all recording files in destination
    downloaded_recording_files = {
        f.name
        for f in context.dest_dir.rglob("*")
        if f.is_file() and recording_filename_re.match(f.name)
    }

    # gets expected recordings from context
    expected_recordings = set(context.expected_recordings)

    # checks that all expected recordings are downloaded
    assert_that(downloaded_recording_files, has_items(*expected_recordings))


@then("the destination is empty")
def assert_destination_empty(context: Context) -> None:
    """verifies that the destination directory contains no recording files."""
    # gets all recording files
    downloaded_recording_files = [
        f.name
        for f in context.dest_dir.rglob("*")
        if f.is_file() and recording_filename_re.match(f.name)
    ]
    assert_that(
        downloaded_recording_files,
        empty(),
        f"Expected no recordings, but found: {downloaded_recording_files}",
    )
