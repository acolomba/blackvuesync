"""mock dashcam setup and request step definitions."""

from __future__ import annotations

from behave import given, then, when
from behave.runner import Context
from hamcrest import assert_that, equal_to

from features.lib.recordings import (
    generate_recording_filenames,
    select_by_period,
    servable_filenames,
)


@given(
    'the dashcam has recordings for the past "{period}" of types "{recording_types}", directions "{recording_directions}"'
)
def dashcam_recordings(
    context: Context, period: str, recording_types: str, recording_directions: str
) -> None:
    """lists generated recordings dated up to today on the dashcam."""
    context.dashcam_recordings = list(
        generate_recording_filenames(
            recording_types, recording_directions, period, "0d"
        )
    )
    context.dashcam.set_recordings(context.dashcam_recordings)


@given(
    'the dashcam has the destination recordings between "{period_start}" and "{period_end}" ago'
)
def dashcam_destination_recordings(
    context: Context, period_start: str, period_end: str
) -> None:
    """lists on the dashcam the pre-existing destination recordings in the period."""
    filenames = select_by_period(
        context.preexisting_recordings, period_start, period_end
    )
    if not filenames:
        raise ValueError(
            f"the destination has no recordings between {period_start} and "
            f"{period_end} ago"
        )
    context.dashcam_recordings = sorted(filenames)
    context.dashcam.set_recordings(context.dashcam_recordings)


@given("the dashcam has no recordings")
def dashcam_no_recordings(context: Context) -> None:
    """lists no recordings on the dashcam."""
    context.dashcam_recordings = []
    context.dashcam.set_recordings(context.dashcam_recordings)


@given('the dashcam fails to serve {count:d} "{extension}" files')
def dashcam_failed_downloads(context: Context, count: int, extension: str) -> None:
    """fails the downloads of the first count listed files with the extension.

    the dashcam answers every request for those files with a 500 error until
    it stops failing downloads.
    """
    matching = [f for f in context.dashcam_recordings if f.endswith(f".{extension}")]
    if len(matching) < count:
        raise ValueError(
            f"expected at least {count} .{extension} files on the dashcam, "
            f"got {len(matching)}"
        )
    context.failed_recordings = set(matching[:count])
    context.dashcam.fail_downloads(context.failed_recordings)


@given("the dashcam fails to list its recordings")
def dashcam_failed_listing(context: Context) -> None:
    """fails the dashcam's recording list on both protocols with a 500 error."""
    context.dashcam.fail_listing()


@when("the dashcam stops failing downloads")
def stop_failing_downloads(context: Context) -> None:
    """makes the dashcam serve every recording file again."""
    context.dashcam.fail_downloads([])


@then("the dashcam receives no download requests")
def assert_no_download_requests(context: Context) -> None:
    """verifies the latest run requests no recording file."""
    assert_that(context.dashcam.requested_files(), equal_to([]))


@then("the dashcam receives download requests for only the missing recordings")
def assert_missing_download_requests(context: Context) -> None:
    """verifies the latest run requests exactly the files the destination lacks."""
    missing = (
        servable_filenames(
            context.dashcam_recordings, context.legacy_api, context.skip_metadata
        )
        - context.preexisting_recordings
    )
    requested = context.dashcam.requested_files()
    assert_that(
        sorted(requested),
        equal_to(sorted(missing)),
        f"not requested: {sorted(missing.difference(requested))}; "
        f"unexpected: {sorted(set(requested) - missing)}",
    )
