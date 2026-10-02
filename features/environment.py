"""behave hooks: starts the mock dashcam for the run and isolates each scenario."""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

from behave.model import Scenario
from behave.runner import Context
from behave.userdata import UserData
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from features.lib import PROJECT_ROOT
from features.lib.dashcam import MockDashcamClient
from features.lib.docker import build_blackvuesync_image, build_mock_dashcam_image
from features.mock_dashcam import MockDashcam
from features.mock_dashcam.server import MOCK_DASHCAM_PORT

logger = logging.getLogger("features.environment")


def _configure_logging(userdata: UserData) -> None:
    """prints the records of the features loggers at the configured levels."""
    suite_logger = logging.getLogger("features")
    suite_logger.setLevel(userdata.get("log_level", "INFO").upper())
    # the suite prints its own records, so behave's log capture never repeats them
    suite_logger.propagate = False
    if not suite_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        suite_logger.addHandler(handler)

    logging.getLogger("features.mock_dashcam").setLevel(
        userdata.get("log_level_mock_dashcam", "INFO").upper()
    )
    logging.getLogger("werkzeug").setLevel(
        userdata.get("log_level_http", "WARN").upper()
    )


def _start_direct_mode(context: Context) -> None:
    """serves the mock dashcam from a thread on an ephemeral loopback port."""
    mock_dashcam = MockDashcam()
    mock_dashcam.start()
    context.add_cleanup(mock_dashcam.stop)

    context.mock_dashcam_address = f"127.0.0.1:{mock_dashcam.port}"
    context.mock_dashcam_url = f"http://{context.mock_dashcam_address}"
    logger.info("mock dashcam running at: %s", context.mock_dashcam_url)


def _start_docker_mode(context: Context) -> None:
    """runs the mock dashcam in a container on a network.

    the blackvuesync containers join the same network.
    """
    image_name = context.config.userdata.get("image_name")
    if image_name:
        logger.info("using existing docker image: %s", image_name)
        context.docker_image_tag = image_name
    else:
        context.docker_image_tag = build_blackvuesync_image()

    context.docker_network = Network()
    context.docker_network.create()
    context.add_cleanup(context.docker_network.remove)

    container = (
        DockerContainer(image=build_mock_dashcam_image())
        # publishes the port on an ephemeral host port, on loopback only
        .with_bind_ports(MOCK_DASHCAM_PORT, ("127.0.0.1", None))
        .with_network(context.docker_network)
        .waiting_for(LogMessageWaitStrategy("mock dashcam listening"))
    )
    # registered first so a container that fails its wait strategy is removed
    context.add_cleanup(container.stop)
    container.start()

    # blackvuesync containers reach the mock by container id on the network;
    # the test runner reaches it through the port mapped on the host
    container_id = container.get_wrapped_container().short_id
    context.mock_dashcam_address = f"{container_id}:{MOCK_DASHCAM_PORT}"
    host_port = container.get_exposed_port(MOCK_DASHCAM_PORT)
    context.mock_dashcam_url = f"http://127.0.0.1:{host_port}"
    logger.info(
        "mock dashcam container running at: %s (network address %s)",
        context.mock_dashcam_url,
        context.mock_dashcam_address,
    )


def _remove_test_run_dir(context: Context) -> None:
    """removes the test run directory unless it holds a failed scenario's directory.

    passing scenarios remove their own directories, so any directory left holds
    a failed scenario, including one that failed in a hook; context.failed
    covers only step failures.
    """
    if any(context.test_run_dir.iterdir()):
        logger.warning(
            "failed scenarios' run logs and destinations preserved under: %s",
            context.test_run_dir,
        )
        return
    shutil.rmtree(context.test_run_dir)


def _remove_scenario_dir(scenario: Scenario, scenario_dir: Path) -> None:
    """removes the directory of a scenario, keeping it when the scenario failed.

    behave runs the cleanups after after_scenario, once the status is final.
    """
    if scenario.status.has_failed():
        logger.warning(
            "scenario %r failed; run logs and destination preserved at: %s",
            scenario.name,
            scenario_dir,
        )
        return
    # docker mode runs blackvuesync with PUID and PGID of the test runner, so
    # the runner owns the files in the destination
    shutil.rmtree(scenario_dir)


def before_all(context: Context) -> None:
    """configures logging and starts the mock dashcam for the run."""
    userdata = context.config.userdata
    _configure_logging(userdata)

    context.legacy_api = userdata.getbool("legacy_api", False)
    context.implementation = userdata.get("implementation", "direct")
    if context.implementation not in ("direct", "docker"):
        raise ValueError(
            f"unknown implementation {context.implementation!r}; "
            "expected direct or docker"
        )

    # coverage run --parallel-mode suffixes the name per process, so the files
    # match the .coverage.* pattern that coverage combine reads
    context.coverage_file = None
    if (
        userdata.getbool("collect_coverage", False)
        and context.implementation == "direct"
    ):
        mode = "legacy" if context.legacy_api else "v1009"
        context.coverage_file = PROJECT_ROOT / f".coverage.behave.{mode}"

    context.test_run_dir = Path(tempfile.mkdtemp(prefix="blackvuesync_test_"))
    context.add_cleanup(_remove_test_run_dir, context)
    logger.info("test run directory: %s", context.test_run_dir)

    if context.implementation == "docker":
        _start_docker_mode(context)
    else:
        _start_direct_mode(context)


def before_scenario(context: Context, scenario: Scenario) -> None:
    """gives the scenario its own destination and mock dashcam session."""
    # scenarios tagged @legacy exercise protocol features absent on V1.009+
    if "legacy" in scenario.effective_tags and not context.legacy_api:
        scenario.skip("legacy protocol only")
        return
    # scenarios tagged @direct assert a nonzero exit code, which docker mode
    # cannot observe
    if "direct" in scenario.effective_tags and context.implementation != "direct":
        scenario.skip(
            "direct mode only: the image's entrypoint.sh exits 0 after a RUN_ONCE "
            "run, whatever blackvuesync's exit status"
        )
        return

    scenario_name = scenario.name.replace(" ", "_").replace("/", "_")
    context.scenario_dir = Path(
        tempfile.mkdtemp(dir=context.test_run_dir, prefix=f"{scenario_name}_")
    )
    context.add_cleanup(_remove_scenario_dir, scenario, context.scenario_dir)
    context.dest_dir = context.scenario_dir / "destination"
    context.dest_dir.mkdir()

    # the unique directory name also keys the scenario's dashcam session
    context.dashcam = MockDashcamClient(
        context.mock_dashcam_url, context.scenario_dir.name
    )
    context.add_cleanup(context.dashcam.delete_session)
    context.dashcam.set_legacy_api(context.legacy_api)

    # recording files the dashcam lists
    context.dashcam_recordings = []
    # recording files in the destination before blackvuesync runs
    context.preexisting_recordings = set()
    # recording files the dashcam fails to serve
    context.failed_recordings = set()
    # --skip-metadata codes of the latest run
    context.skip_metadata = set()
    # --grouping of the latest run
    context.grouping = "none"
    # numbers the run logs of the scenario
    context.run_count = 0
