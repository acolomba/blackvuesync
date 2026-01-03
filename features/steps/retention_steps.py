"""retention policy step definitions"""

import re

from behave import then, when
from behave.runner import Context
from hamcrest import assert_that, empty, has_items

from features.lib.recordings import filter_recording_filenames_by_period
from features.steps.blackvuesync_steps import execute_blackvuesync

# recording filename pattern - matches BlackVue recording filenames
# format: YYYYMMDD_HHMMSS_TD.ext where T=type, D=direction, ext=mp4/thm/3gf/gps
recording_filename_re = re.compile(
    r"^\d{8}_\d{6}_[NEPMIOATBRXGDLYF][FRIO]?[LS]?\.(mp4|thm|3gf|gps)$"
)


@when('blackvuesync runs with keep "{period}"')
def run_blackvuesync_with_keep(context: Context, period: str) -> None:
    """executes blackvuesync with a retention period."""
    execute_blackvuesync(
        context,
        context.mock_dashcam_address,
        str(context.dest_dir),
        context.scenario_token,
        keep=period,
    )


@then('recordings between "{period_start}" and "{period_end}" ago are downloaded')
def assert_recordings_between_downloaded(
    context: Context, period_start: str, period_end: str
) -> None:
    """verifies that recordings from dashcam within the specified period exist in destination."""
    # validates prerequisites
    if not hasattr(context, "expected_recordings"):
        raise RuntimeError(
            "Cannot verify recordings: test scenario is missing 'Given recordings...' step. Expected recordings were never configured."
        )

    # filters expected recordings to those within the period
    expected_in_period = set(
        filter_recording_filenames_by_period(
            context.expected_recordings, period_start, period_end
        )
    )

    # gets all recording files in destination
    downloaded_recording_files = {
        f.name
        for f in context.dest_dir.rglob("*")
        if f.is_file() and recording_filename_re.match(f.name)
    }

    # checks that all expected recordings in period are downloaded
    assert_that(downloaded_recording_files, has_items(*expected_in_period))


@then('no recordings between "{period_start}" and "{period_end}" ago exist')
def assert_no_recordings_between_exist(
    context: Context, period_start: str, period_end: str
) -> None:
    """verifies that no recordings within the specified period exist in destination."""
    # validates prerequisites
    if not hasattr(context, "expected_recordings"):
        raise RuntimeError(
            "Cannot verify recordings: test scenario is missing 'Given recordings...' step. Expected recordings were never configured."
        )

    # filters expected recordings to those within the period
    expected_in_period = set(
        filter_recording_filenames_by_period(
            context.expected_recordings, period_start, period_end
        )
    )

    # gets all recording files in destination
    downloaded_recording_files = {
        f.name
        for f in context.dest_dir.rglob("*")
        if f.is_file() and recording_filename_re.match(f.name)
    }

    # finds any recordings from this period that exist
    found_in_period = downloaded_recording_files & expected_in_period

    # asserts none exist
    assert_that(
        list(found_in_period),
        empty(),
        f"Expected no recordings between {period_start} and {period_end} ago, but found: {sorted(found_in_period)}",
    )


@then('downloaded recordings between "{period_start}" and "{period_end}" ago exist')
def assert_downloaded_recordings_between_exist(
    context: Context, period_start: str, period_end: str
) -> None:
    """verifies that previously downloaded recordings within the specified period still exist."""
    if not hasattr(context, "downloaded_recordings"):
        return

    # filters downloaded recordings to those within the period
    expected_in_period = set(
        filter_recording_filenames_by_period(
            list(context.downloaded_recordings), period_start, period_end
        )
    )

    # gets all recording files in destination
    downloaded_recording_files = {
        f.name
        for f in context.dest_dir.rglob("*")
        if f.is_file() and recording_filename_re.match(f.name)
    }

    # verifies all downloaded recordings in period still exist
    assert_that(downloaded_recording_files, has_items(*expected_in_period))


@then('no downloaded recordings between "{period_start}" and "{period_end}" ago exist')
def assert_no_downloaded_recordings_between_exist(
    context: Context, period_start: str, period_end: str
) -> None:
    """verifies that previously downloaded recordings within the specified period no longer exist."""
    if not hasattr(context, "downloaded_recordings"):
        return

    # filters downloaded recordings to those within the period
    expected_in_period = set(
        filter_recording_filenames_by_period(
            list(context.downloaded_recordings), period_start, period_end
        )
    )

    # gets all recording files in destination
    downloaded_recording_files = {
        f.name
        for f in context.dest_dir.rglob("*")
        if f.is_file() and recording_filename_re.match(f.name)
    }

    # finds any downloaded recordings from this period that still exist
    found_in_period = downloaded_recording_files & expected_in_period

    # asserts none exist
    assert_that(
        list(found_in_period),
        empty(),
        f"Expected no downloaded recordings between {period_start} and {period_end} ago, but found: {sorted(found_in_period)}",
    )
