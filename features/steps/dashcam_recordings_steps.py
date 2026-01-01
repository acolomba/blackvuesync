"""dashcam recording setup step definitions"""

import requests
from behave import given
from behave.runner import Context


@given(
    'recordings for the past "{period}" of types "{recording_types}", directions "{recording_directions}", other "{recording_others}"'
)
def dashcam_recordings(
    context: Context,
    period: str,
    recording_types: str,
    recording_directions: str,
    recording_others: str,
) -> None:
    """configures mock dashcam with recordings matching the specified criteria."""
    url = f"{context.mock_dashcam_url}/mock/recordings"
    data = {
        "period_past": period,
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
    'recordings for the past "{period}" of types "{recording_types}", directions "{recording_directions}"'
)
def dashcam_recordings_no_other(
    context: Context, period: str, recording_types: str, recording_directions: str
) -> None:
    """configures mock dashcam with recordings matching the specified criteria."""
    dashcam_recordings(context, period, recording_types, recording_directions, "")
