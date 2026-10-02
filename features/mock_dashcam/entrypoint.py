"""entrypoint for the mock dashcam container."""

import logging

from features.mock_dashcam.server import MOCK_DASHCAM_PORT, MockDashcam

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    dashcam = MockDashcam(host="0.0.0.0", port=MOCK_DASHCAM_PORT)
    # the test runner waits for this line before sending requests
    logging.getLogger(__name__).info("mock dashcam listening on port %d", dashcam.port)
    dashcam.serve_forever()
