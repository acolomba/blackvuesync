import logging
import shutil
import tempfile
import uuid
from pathlib import Path

from behave.model import Scenario, Step
from behave.runner import Context
from testcontainers.core.container import DockerContainer
from testcontainers.core.image import DockerImage
from testcontainers.core.network import Network

from features.lib.docker import get_docker_image
from features.mock_dashcam import MockDashcam

# logger for environment hooks
logger = logging.getLogger("features.steps")


def _setup_direct_mode(context: Context) -> None:
    """sets up mock dashcam in direct (threaded) mode"""
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


def _setup_docker_mode(context: Context) -> None:
    """sets up docker mode with containerized mock dashcam"""
    # builds blackvuesync docker image
    image_name = context.config.userdata.get("image_name")
    context.docker_image, image_tag = get_docker_image(image_name)
    logger.info("docker implementation enabled with image: %s", image_tag)

    # builds mock dashcam docker image
    project_root = Path(__file__).parent.parent
    mock_dashcam_dockerfile = project_root / "features" / "mock_dashcam"

    logger.info("building mock dashcam docker image")
    context.mock_dashcam_image = DockerImage(
        path=str(project_root),
        dockerfile_path=str(mock_dashcam_dockerfile / "Dockerfile"),
        tag="blackvuesync-mock-dashcam:test",
    )
    context.mock_dashcam_image.build()
    logger.info("mock dashcam docker image built successfully")

    # creates docker network for container communication
    context.docker_network = Network()
    context.docker_network.create()
    logger.info("docker network created: %s", context.docker_network.name)

    # starts mock dashcam container
    context.mock_dashcam_container = DockerContainer(
        image=context.mock_dashcam_image.tag
    )
    context.mock_dashcam_container.with_exposed_ports(5000)
    context.mock_dashcam_container.with_network(context.docker_network)

    logger.info("starting mock dashcam container")
    context.mock_dashcam_container.start()

    # gets container's network alias (short container ID)
    container_id = context.mock_dashcam_container.get_wrapped_container().short_id

    # gets exposed port on host for test runner to connect to
    host_port = context.mock_dashcam_container.get_exposed_port(5000)

    # sets addresses:
    # - mock_dashcam_address: used by blackvuesync container (container ID on network)
    # - mock_dashcam_url: used by test runner on host (localhost with mapped port)
    context.mock_dashcam_address = f"{container_id}:5000"
    context.mock_dashcam_url = f"http://127.0.0.1:{host_port}"

    # waits for mock dashcam to be ready
    import time

    import requests

    max_attempts = 50
    for attempt in range(max_attempts):
        try:
            response = requests.get(
                f"{context.mock_dashcam_url}/mock/ping", timeout=1.0
            )
            if response.status_code == 200:
                logger.info("mock dashcam container is ready")
                break
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt < max_attempts - 1:
                time.sleep(0.1)
                continue
            raise RuntimeError(
                f"mock dashcam container did not become ready within {max_attempts * 0.1}s"
            ) from e

    logger.info(
        "mock dashcam container running - container_id: %s, host: %s, network: %s",
        container_id,
        context.mock_dashcam_url,
        f"http://{context.mock_dashcam_address}",
    )


def before_all(context: Context) -> None:
    """before all"""
    # step definitions logging
    log_level = context.config.userdata.get("log_level", "INFO")
    logger.setLevel(getattr(logging, log_level.upper()))

    # werkzeug (flask) logging
    log_level_http = context.config.userdata.get("log_level_http", "INFO")
    logging.getLogger("werkzeug").setLevel(getattr(logging, log_level_http.upper()))

    # creates a temporary directory for test artifacts
    context.test_run_dir = Path(tempfile.mkdtemp(prefix="blackvuesync_test_"))
    logger.info("test run directory: %s", context.test_run_dir)

    # checks implementation mode
    implementation = context.config.userdata.get("implementation", "direct")

    if implementation == "docker":
        # docker mode: runs mock dashcam in container
        _setup_docker_mode(context)
    else:
        # direct mode: runs mock dashcam in thread
        _setup_direct_mode(context)


def after_all(context: Context) -> None:
    """after all"""
    # combines coverage data if collection was enabled (direct mode only)
    collect_coverage = context.config.userdata.getbool("collect_coverage", False)
    implementation = context.config.userdata.get("implementation", "direct")
    if (
        collect_coverage
        and implementation == "direct"
        and hasattr(context, "test_run_dir")
    ):
        _combine_coverage(context.test_run_dir)

    # stops mock dashcam (threaded or containerized)
    if hasattr(context, "mock_dashcam"):
        # direct mode: stops threaded server
        context.mock_dashcam.stop()

    if hasattr(context, "mock_dashcam_container"):
        # docker mode: stops and removes container
        logger.info("stopping mock dashcam container")
        context.mock_dashcam_container.stop()

    if hasattr(context, "docker_network"):
        # docker mode: removes network
        logger.info("removing docker network")
        context.docker_network.remove()

    # cleans up test run directory
    if hasattr(context, "test_run_dir") and context.test_run_dir.exists():
        shutil.rmtree(context.test_run_dir)

    # ensures all logging handlers flush before exit
    for handler in logging.root.handlers:
        handler.flush()


def _combine_coverage(test_run_dir: Path) -> None:
    """copies all coverage files from scenario directories to project root."""
    # finds all .coverage files in scenario directories
    coverage_files = list(test_run_dir.glob("*/coverage/.coverage*"))

    if not coverage_files:
        logger.warning("no coverage files found to copy")
        return

    logger.info("found %d coverage file(s) to copy", len(coverage_files))

    # copies all coverage files to project root for combining
    project_root = Path(__file__).parent.parent
    for i, coverage_file in enumerate(coverage_files):
        dest = project_root / f".coverage.behave.{i}"
        shutil.copy2(coverage_file, dest)
        logger.info("copied %s to %s", coverage_file, dest)

    logger.info("coverage files ready for combining")


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
    # clears recordings from mock dashcam (direct mode only)
    # in docker mode, each scenario uses session key isolation, and container is destroyed in after_all
    if hasattr(context, "mock_dashcam"):
        # direct mode: clears via method call
        context.mock_dashcam.clear_recordings(context.scenario_token)

    # if scenario failed, preserve the directory for debugging
    if scenario.status == "failed":
        logger.info("scenario failed. artifacts preserved at: %s", context.scenario_dir)


def before_step(context: Context, step: Step) -> None:
    """before each step"""
    pass


def after_step(context: Context, step: Step) -> None:
    """after each step"""
    pass
