"""skip-metadata step definitions"""

from __future__ import annotations

from behave import when
from behave.runner import Context

from features.steps.blackvuesync_steps import execute_blackvuesync


@when('blackvuesync runs with skip-metadata "{skip_metadata}"')
def run_blackvuesync_with_skip_metadata(context: Context, skip_metadata: str) -> None:
    """executes blackvuesync with --skip-metadata option."""
    context.skip_metadata = set(skip_metadata)
    execute_blackvuesync(
        context,
        context.mock_dashcam_address,
        str(context.dest_dir),
        context.scenario_token,
        skip_metadata=skip_metadata,
    )
