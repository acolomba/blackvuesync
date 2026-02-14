"""retry-failed download step definitions"""

import re
import time

import requests
from behave import given, then, when
from behave.runner import Context
from hamcrest import assert_that, empty, has_items

from features.steps.blackvuesync_steps import execute_blackvuesync

# recording filename pattern
recording_filename_re = re.compile(
    r"^\d{8}_\d{6}_[NEPMIOATBRXGDLYF][FRIO]?[LS]?\.(mp4|thm|3gf|gps)$"
)


@given("the first {count:d} mp4 recordings are configured to fail")
def download_errors(context: Context, count: int) -> None:
    """configures the first N mp4 recordings to return download errors."""
    if not hasattr(context, "expected_recordings"):
        raise RuntimeError(
            "Cannot configure download errors: no recordings configured yet."
        )

    mp4_files = [f for f in context.expected_recordings if f.endswith(".mp4")]
    failed_filenames = mp4_files[:count]

    url = f"{context.mock_dashcam_url}/mock/downloads/errors"
    headers = {"X-Affinity-Key": context.scenario_token}
    data = {"filenames": failed_filenames}

    response = requests.post(url, json=data, headers=headers, timeout=10)
    response.raise_for_status()

    context.failed_recordings = set(failed_filenames)


@when("download errors are cleared")
def clear_download_errors(context: Context) -> None:
    """clears all configured download errors."""
    url = f"{context.mock_dashcam_url}/mock/downloads/errors"
    headers = {"X-Affinity-Key": context.scenario_token}

    response = requests.delete(url, headers=headers, timeout=10)
    response.raise_for_status()


@when('blackvuesync runs with retry-failed-after "{duration}"')
def run_blackvuesync_with_retry_failed_after(context: Context, duration: str) -> None:
    """executes blackvuesync with a retry-failed-after duration."""
    execute_blackvuesync(
        context,
        context.mock_dashcam_address,
        str(context.dest_dir),
        context.scenario_token,
        retry_failed_after=duration,
    )


@when("{seconds:d} seconds elapse")
def wait_seconds(_context: Context, seconds: int) -> None:
    """waits for the specified number of seconds."""
    time.sleep(seconds)


@then("the successful recordings are downloaded")
def assert_successful_recordings_downloaded(context: Context) -> None:
    """verifies that recordings not configured to fail exist in destination."""
    if not hasattr(context, "expected_recordings"):
        raise RuntimeError("No expected recordings configured.")

    failed: set[str] = getattr(context, "failed_recordings", set())
    successful = {f for f in context.expected_recordings if f not in failed}

    downloaded = {
        f.name
        for f in context.dest_dir.rglob("*")
        if f.is_file() and recording_filename_re.match(f.name)
    }

    assert_that(downloaded, has_items(*successful))


@then("failure markers exist for the failed recordings")
def assert_failure_markers_exist(context: Context) -> None:
    """verifies that .failed marker files exist for failed recordings."""
    if not hasattr(context, "failed_recordings"):
        raise RuntimeError("No failed recordings configured.")

    marker_files = {f.name for f in context.dest_dir.rglob("*.failed") if f.is_file()}

    expected_markers = {f"{f}.failed" for f in context.failed_recordings}
    assert_that(marker_files, has_items(*expected_markers))


@then("the previously failed recordings are not downloaded")
def assert_failed_recordings_not_downloaded(context: Context) -> None:
    """verifies that previously failed recordings are not in destination."""
    if not hasattr(context, "failed_recordings"):
        raise RuntimeError("No failed recordings configured.")

    downloaded = {
        f.name
        for f in context.dest_dir.rglob("*")
        if f.is_file() and recording_filename_re.match(f.name)
    }

    found_failed = downloaded & context.failed_recordings
    assert_that(
        list(found_failed),
        empty(),
        f"Expected failed recordings to not be downloaded, but found: {sorted(found_failed)}",
    )


@then("no failure markers exist")
def assert_no_failure_markers_exist(context: Context) -> None:
    """verifies that no .failed marker files exist in destination."""
    marker_files = [f.name for f in context.dest_dir.rglob("*.failed") if f.is_file()]
    assert_that(
        marker_files,
        empty(),
        f"Expected no failure markers, but found: {marker_files}",
    )
