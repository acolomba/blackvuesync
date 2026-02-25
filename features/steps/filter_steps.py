"""include/exclude filter step definitions"""

from __future__ import annotations

import os
import re

from behave import then, when
from behave.runner import Context

from blackvuesync import RECORDING_DIRECTIONS, RECORDING_TYPES
from features.steps.blackvuesync_steps import execute_blackvuesync

_recording_filename_re = re.compile(
    rf"^\d{{8}}_\d{{6}}_([{RECORDING_TYPES}])([{RECORDING_DIRECTIONS}])[LS]?\.(mp4|thm|3gf|gps)$"
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


@then('the destination contains "{code}" recordings')
def assert_destination_contains_recordings(context: Context, code: str) -> None:
    """verifies that the destination contains recordings matching the code."""
    matching = _find_recordings_matching(context.dest_dir, code)
    assert matching, f"expected recordings matching '{code}' but found none"


@then('the destination does not contain "{code}" recordings')
def assert_destination_does_not_contain_recordings(context: Context, code: str) -> None:
    """verifies that the destination does not contain recordings matching the code."""
    matching = _find_recordings_matching(context.dest_dir, code)
    assert not matching, f"unexpected recordings matching '{code}': {matching}"


def _find_recordings_matching(dest_dir: str, code: str) -> list[str]:
    """finds recording files in dest_dir matching a filter code."""
    matching = []
    for _root, _dirs, files in os.walk(str(dest_dir)):
        for filename in files:
            m = _recording_filename_re.match(filename)
            if m:
                rec_type, rec_direction = m.group(1), m.group(2)
                if (len(code) == 1 and rec_type == code) or (
                    len(code) == 2 and rec_type == code[0] and rec_direction == code[1]
                ):
                    matching.append(filename)
    return matching
