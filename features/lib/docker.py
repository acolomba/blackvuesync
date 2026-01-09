"""docker image management for integration tests"""

import logging
from pathlib import Path
from typing import Optional

from testcontainers.core.image import DockerImage

# logger for docker operations
logger = logging.getLogger("features.docker")

# default docker image tag for tests
DEFAULT_IMAGE_TAG = "acolomba/blackvuesync:test"


def get_docker_image(image_name: Optional[str] = None) -> tuple[DockerImage, str]:
    """gets docker image for testing, building if necessary.

    args:
        image_name: optional image name to use. if provided, uses existing image.
                   if not provided, builds image with default tag.

    returns:
        tuple of (DockerImage, image_tag)
    """
    if image_name:
        logger.info("using existing docker image: %s", image_name)
        # creates DockerImage reference without building
        image = DockerImage(tag=image_name)
        return image, image_name

    # builds image if no name provided
    logger.info("building docker image: %s", DEFAULT_IMAGE_TAG)

    # finds project root (parent of features/)
    project_root = Path(__file__).parent.parent.parent

    # builds image using testcontainers
    image = DockerImage(path=str(project_root), tag=DEFAULT_IMAGE_TAG)
    image.build()

    logger.info("docker image built successfully: %s", DEFAULT_IMAGE_TAG)

    return image, DEFAULT_IMAGE_TAG
