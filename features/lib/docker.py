"""docker image management for integration tests"""

import logging
import subprocess
from pathlib import Path

# logger for docker operations
logger = logging.getLogger("features.docker")

# module-level flag to track if image has been built
_IMAGE_BUILT = False

# docker image tag for tests
IMAGE_TAG = "blackvuesync:local"


def _check_docker_available() -> None:
    """verifies docker is installed and running."""
    try:
        subprocess.run(
            ["docker", "info"],
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as e:
        raise RuntimeError("docker is not installed or not in PATH") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError("docker daemon is not running") from e


def ensure_docker_image_built() -> str:
    """builds docker image once per session, returns tag."""
    global _IMAGE_BUILT

    if _IMAGE_BUILT:
        logger.info("docker image already built: %s", IMAGE_TAG)
        return IMAGE_TAG

    # checks docker is available before attempting build
    _check_docker_available()

    logger.info("building docker image: %s", IMAGE_TAG)

    # finds project root (parent of features/)
    project_root = Path(__file__).parent.parent.parent

    # builds image
    cmd = [
        "docker",
        "build",
        "-t",
        IMAGE_TAG,
        str(project_root),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )

    if result.returncode != 0:
        logger.error("docker build failed")
        logger.error("stdout: %s", result.stdout)
        logger.error("stderr: %s", result.stderr)
        raise RuntimeError(f"docker build failed with exit code {result.returncode}")

    logger.info("docker image built successfully: %s", IMAGE_TAG)
    _IMAGE_BUILT = True

    return IMAGE_TAG
