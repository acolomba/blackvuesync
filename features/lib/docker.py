"""docker image management for integration tests"""

import logging
from pathlib import Path

from testcontainers.core.image import DockerImage

# logger for docker operations
logger = logging.getLogger("features.docker")

# docker image tag for tests
IMAGE_TAG = "acolomba/blackvuesync:local"


def build_docker_image() -> DockerImage:
    """builds docker image for testing, returns DockerImage."""
    logger.info("building docker image: %s", IMAGE_TAG)

    # finds project root (parent of features/)
    project_root = Path(__file__).parent.parent.parent

    # builds image using testcontainers
    image = DockerImage(path=str(project_root), tag=IMAGE_TAG)
    image.build()

    logger.info("docker image built successfully: %s", IMAGE_TAG)

    return image
