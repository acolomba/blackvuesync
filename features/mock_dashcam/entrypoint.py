#!/usr/bin/env python3
"""entrypoint for mock dashcam container"""

import logging
import sys

# adds parent directory to path so we can import modules
sys.path.insert(0, "/app")

from features.mock_dashcam.server import MockDashcam

# configures logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("starting mock dashcam server on 0.0.0.0:5000")

    # creates dashcam instance (binds to 0.0.0.0 for container access)
    dashcam = MockDashcam(port=5000, log_level="INFO", host="0.0.0.0")

    # runs flask server directly (blocking)
    dashcam.app.run(host=dashcam.host, port=dashcam.port, use_reloader=False)
