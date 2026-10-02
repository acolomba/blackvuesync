"""docker image management for behavioral tests."""

from __future__ import annotations

import logging

from testcontainers.core.image import DockerImage

from features.lib import PROJECT_ROOT

logger = logging.getLogger("features.docker")

# tag of the blackvuesync image the tests build
DEFAULT_IMAGE_TAG = "acolomba/blackvuesync:test"

# tag of the mock dashcam image the tests build
MOCK_DASHCAM_IMAGE_TAG = "blackvuesync-mock-dashcam:test"


def build_blackvuesync_image() -> str:
    """builds the blackvuesync image and returns its tag."""
    logger.info("building docker image: %s", DEFAULT_IMAGE_TAG)
    DockerImage(path=str(PROJECT_ROOT), tag=DEFAULT_IMAGE_TAG).build()
    return DEFAULT_IMAGE_TAG


def build_mock_dashcam_image() -> str:
    """builds the mock dashcam image and returns its tag."""
    logger.info("building docker image: %s", MOCK_DASHCAM_IMAGE_TAG)
    DockerImage(
        path=str(PROJECT_ROOT),
        dockerfile_path=str(PROJECT_ROOT / "features" / "mock_dashcam" / "Dockerfile"),
        tag=MOCK_DASHCAM_IMAGE_TAG,
    ).build()
    return MOCK_DASHCAM_IMAGE_TAG
