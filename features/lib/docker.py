"""docker image management for integration tests"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from testcontainers.core.image import DockerImage

# logger for docker operations
logger = logging.getLogger("features.docker")

# default docker image tag for tests
DEFAULT_IMAGE_TAG = "acolomba/blackvuesync:test"


@dataclass
class ImageReference:
    """reference to a pre-existing docker image."""

    tag: str


def get_docker_image(
    image_name: str | None = None,
) -> tuple[DockerImage | ImageReference, str]:
    """gets docker image for testing, building if necessary.

    args:
        image_name: optional image name to use. if provided, uses existing image.
                   if not provided, builds image with default tag.

    returns:
        tuple of (DockerImage or ImageReference, image_tag)
    """
    if image_name:
        logger.info("using existing docker image: %s", image_name)
        # creates reference to existing image without building
        image = ImageReference(tag=image_name)
        return image, image_name

    # builds image if no name provided
    logger.info("building docker image: %s", DEFAULT_IMAGE_TAG)

    # finds project root (parent of features/)
    project_root = Path(__file__).parent.parent.parent

    # builds image using testcontainers
    docker_image = DockerImage(path=str(project_root), tag=DEFAULT_IMAGE_TAG)
    docker_image.build()

    logger.info("docker image built successfully: %s", DEFAULT_IMAGE_TAG)

    return docker_image, DEFAULT_IMAGE_TAG
