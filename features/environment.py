import logging
import shutil
import tempfile
import uuid
from pathlib import Path

from behave.model import Scenario, Step
from behave.runner import Context

from features.mock_dashcam import MockDashcam

# logger for environment hooks
logger = logging.getLogger("features.steps")


def before_all(context: Context) -> None:
    """before all"""
    # step definitions logging
    log_level = context.config.userdata.get("log_level", "INFO")
    logger.setLevel(getattr(logging, log_level.upper()))

    # werkzeug (flask) logging
    log_level_http = context.config.userdata.get("log_level_http", "INFO")
    logging.getLogger("werkzeug").setLevel(getattr(logging, log_level_http.upper()))

    # starts mock dashcam
    log_level_mock_dashcam = context.config.userdata.get(
        "log_level_mock_dashcam", "INFO"
    )
    mock_dashcam_port = int(context.config.userdata.get("mock_dashcam_port", "5000"))
    context.mock_dashcam = MockDashcam(
        port=mock_dashcam_port, log_level=log_level_mock_dashcam
    )
    context.mock_dashcam.start()
    context.mock_dashcam_url = f"http://127.0.0.1:{mock_dashcam_port}"
    context.mock_dashcam_address = f"127.0.0.1:{mock_dashcam_port}"

    logger.info("mock dashcam running at: %s", context.mock_dashcam_url)

    # creates a temporary directory for test artifacts
    context.test_run_dir = Path(tempfile.mkdtemp(prefix="blackvuesync_test_"))

    logger.info("test run directory: %s", context.test_run_dir)


def after_all(context: Context) -> None:
    """after all"""
    # stops mock dashcam server
    if hasattr(context, "mock_dashcam"):
        context.mock_dashcam.stop()

    # cleans up test run directory
    if hasattr(context, "test_run_dir") and context.test_run_dir.exists():
        shutil.rmtree(context.test_run_dir)

    # ensures all logging handlers flush before exit
    for handler in logging.root.handlers:
        handler.flush()


def before_scenario(context: Context, scenario: Scenario) -> None:
    """before scenario"""
    # scenario-specific directories
    scenario_name = scenario.name.replace(" ", "_").replace("/", "_")
    context.scenario_dir = context.test_run_dir / scenario_name
    context.scenario_dir.mkdir(parents=True, exist_ok=True)

    # download destination directory
    context.dest_dir = context.scenario_dir / "destination"
    context.dest_dir.mkdir(parents=True, exist_ok=True)

    # logs directory
    context.log_dir = context.scenario_dir / "logs"
    context.log_dir.mkdir(parents=True, exist_ok=True)

    # generates scenario affinity token (unique id for this scenario)
    context.scenario_token = f"{scenario_name}_{uuid.uuid4()}"


def after_scenario(context: Context, scenario: Scenario) -> None:
    """after scenario"""
    # clears recordings from mock dashcam
    if hasattr(context, "mock_dashcam"):
        # passes session token to clear only this scenario's recordings
        context.mock_dashcam.clear_recordings(context.scenario_token)

    # if scenario failed, preserve the directory for debugging
    if scenario.status == "failed":
        logger.info("scenario failed. artifacts preserved at: %s", context.scenario_dir)
    # otherwise, optionally clean up (for now, we'll keep everything for debugging)
    # else:
    #     shutil.rmtree(context.scenario_dir)


def before_step(context: Context, step: Step) -> None:
    """before each step"""
    pass


def after_step(context: Context, step: Step) -> None:
    """after each step"""
    pass
