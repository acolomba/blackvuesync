"""dashcam recording setup step definitions"""

import requests
from behave import given
from behave.runner import Context

from features.lib.recordings import filter_recording_filenames_by_period


@given(
    'recordings between "{period_start}" and "{period_end}" ago of types "{recording_types}", directions "{recording_directions}", other "{recording_others}"'
)
def dashcam_recordings(
    context: Context,
    period_start: str,
    period_end: str,
    recording_types: str,
    recording_directions: str,
    recording_others: str,
) -> None:
    """configures mock dashcam with recordings between specified time periods."""
    url = f"{context.mock_dashcam_url}/mock/recordings"
    data = {
        "period_start": period_start,
        "period_end": period_end,
        "recording_types": recording_types,
        "recording_directions": recording_directions,
        "recording_others": recording_others,
    }
    headers = {"X-Session-Key": context.scenario_token}

    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()

    # stores recordings in context for later verification
    result = response.json()
    context.expected_recordings = result["recordings"]


@given(
    'recordings between "{period_start}" and "{period_end}" ago of types "{recording_types}", directions "{recording_directions}"'
)
def dashcam_recordings_no_other(
    context: Context,
    period_start: str,
    period_end: str,
    recording_types: str,
    recording_directions: str,
) -> None:
    """configures mock dashcam with recordings between specified time periods (no other)."""
    dashcam_recordings(
        context, period_start, period_end, recording_types, recording_directions, ""
    )


@given(
    'recordings for the past "{period}" of types "{recording_types}", directions "{recording_directions}", other "{recording_others}"'
)
def dashcam_recordings_past(
    context: Context,
    period: str,
    recording_types: str,
    recording_directions: str,
    recording_others: str,
) -> None:
    """configures mock dashcam with recordings for the past period (shortcut for 'between' with 0d end)."""
    dashcam_recordings(
        context, period, "0d", recording_types, recording_directions, recording_others
    )


@given(
    'recordings for the past "{period}" of types "{recording_types}", directions "{recording_directions}"'
)
def dashcam_recordings_past_no_other(
    context: Context, period: str, recording_types: str, recording_directions: str
) -> None:
    """configures mock dashcam with recordings for the past period (shortcut for 'between' with 0d end, no other)."""
    dashcam_recordings_past(context, period, recording_types, recording_directions, "")


@given(
    'recordings same as the downloaded recordings between "{period_start}" and "{period_end}" ago'
)
def dashcam_recordings_same_as_downloaded(
    context: Context, period_start: str, period_end: str
) -> None:
    """configures mock dashcam with recordings matching downloaded recordings in a time range."""
    if not hasattr(context, "downloaded_recordings"):
        raise RuntimeError(
            "Cannot set up camera recordings from downloaded: no recordings were downloaded. Expected scenario to have 'Given downloaded recordings...' step first."
        )

    # filters downloaded recordings to those within the specified period
    filtered_recordings = filter_recording_filenames_by_period(
        list(context.downloaded_recordings), period_start, period_end
    )

    url = f"{context.mock_dashcam_url}/mock/recordings/set"
    headers = {"X-Session-Key": context.scenario_token}
    data = {"recordings": filtered_recordings}

    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()

    # stores in context for later verification
    context.expected_recordings = filtered_recordings


@given('recordings same as the downloaded recordings for the past "{period}"')
def dashcam_recordings_same_as_downloaded_past(context: Context, period: str) -> None:
    """configures mock dashcam with recordings matching downloaded recordings (shortcut for 'between' with 0d end)."""
    dashcam_recordings_same_as_downloaded(context, period, "0d")
