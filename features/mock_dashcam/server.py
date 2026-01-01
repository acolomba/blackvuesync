"""flask-based mock dashcam server for functional testing"""

from __future__ import annotations

import datetime
import logging
import re
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import flask
import requests

from features.lib.recordings import generate_recording_filenames

# logger for mock dashcam
logger = logging.getLogger("features.mock_dashcam")

# dashcam filename pattern
filename_re = re.compile(
    r"""(?P<base_filename>(?P<year>\d\d\d\d)(?P<month>\d\d)(?P<day>\d\d)
    _(?P<hour>\d\d)(?P<minute>\d\d)(?P<second>\d\d))
    _(?P<type>[NEPMIOATBRXGDLYF])
    (?P<direction>[FRIO]?)
    (?P<upload>[LS]?)
    \.(?P<extension>(3gf|gps|mp4|thm))""",
    re.VERBOSE,
)


@dataclass(frozen=True)
class Recording:
    """represents a recording: filename and metadata"""

    filename: str
    base_filename: str
    datetime: datetime.datetime
    type: str
    direction: str
    extension: str


def to_recording(filename: str) -> Recording | None:
    """extracts recording information from a filename"""
    if (filename_match := re.fullmatch(filename_re, filename)) is None:
        return None

    year = int(filename_match.group("year"))
    month = int(filename_match.group("month"))
    day = int(filename_match.group("day"))
    hour = int(filename_match.group("hour"))
    minute = int(filename_match.group("minute"))
    second = int(filename_match.group("second"))
    recording_datetime = datetime.datetime(year, month, day, hour, minute, second)

    recording_base_filename = filename_match.group("base_filename")
    recording_type = filename_match.group("type")
    recording_direction = filename_match.group("direction")
    recording_extension = filename_match.group("extension")

    return Recording(
        filename,
        recording_base_filename,
        recording_datetime,
        recording_type,
        recording_direction,
        recording_extension,
    )


class MockDashcam:
    """mock blackvue dashcam server"""

    def __init__(self, port: int = 5000, log_level: str = "INFO"):
        # validates port
        if not (4001 <= port <= 65535):
            raise ValueError(f"Port must be between 4001 and 65535, got {port}")

        self.port = port
        self.log_level = log_level
        self.app = flask.Flask(__name__)
        self.server_thread: threading.Thread | None = None
        self._sessions_lock = threading.RLock()
        self._recordings_by_session: defaultdict[str, list[str]] = defaultdict(list)

        # sets up routes
        self._setup_routes()

    def _get_session_key(self) -> str:
        """extracts session key from request header, raises 400 if missing"""
        session_key = flask.request.headers.get("X-Session-Key")
        if not session_key:
            flask.abort(400, description="X-Session-Key header is required")
        return session_key

    def _get_recordings(self, session_key: str) -> list[str]:
        """thread-safe read access to session-specific recordings"""
        with self._sessions_lock:
            return self._recordings_by_session[session_key].copy()

    def _set_recordings(self, session_key: str, recordings: list[str]) -> None:
        """thread-safe write access to session-specific recordings"""
        with self._sessions_lock:
            self._recordings_by_session[session_key] = recordings

    def _setup_routes(self) -> None:
        """sets up flask routes"""

        @self.app.route("/mock/ping", methods=["GET"])
        def ping() -> tuple[dict[str, str], int]:
            """health check endpoint for server startup verification"""
            return {"status": "ok"}, 200

        @self.app.route("/blackvue_vod.cgi", methods=["GET"])
        def vod() -> str:
            """returns the index of recordings"""
            logger.debug("GET /blackvue_vod.cgi")
            session_key = self._get_session_key()

            # format: n:/Record/filename.ext,s:1000000
            # we'll use a fixed size for simplicity
            lines = ["v:1.00"]
            recordings = self._get_recordings(session_key)
            for filename in recordings:
                lines.append(f"n:/Record/{filename},s:1000000")

            response = "\r\n".join(lines) + "\r\n"
            logger.debug("Response body:\n%s", response)

            return response

        @self.app.route("/Record/<filename>", methods=["GET"])
        def record(filename: str) -> flask.Response:
            """serves any file associated to recordings"""
            logger.debug("GET /Record/%s", filename)
            session_key = self._get_session_key()

            # validates that filename exists in session-specific recordings
            recordings = self._get_recordings(session_key)
            if filename not in recordings:
                logger.debug("Response: 404 Not Found (not in session recordings)")
                return flask.abort(404)

            if recording := to_recording(filename):
                # uses the mock file with the same extension
                files_dir = Path(__file__).parent / "files"
                filepath = files_dir / f"mock.{recording.extension}"
                if filepath.exists():
                    logger.debug(
                        "Response: %s (%s bytes)",
                        filepath.name,
                        filepath.stat().st_size,
                    )
                    return flask.send_file(filepath)

            logger.debug("Response: 404 Not Found")
            return flask.abort(404)

        @self.app.route("/mock/recordings", methods=["POST"])
        def create_recordings() -> tuple[dict[str, Any], int]:
            """generates and stores recordings based on criteria"""
            data = flask.request.get_json() or {}
            logger.debug("POST /mock/recordings")
            logger.debug("Request body: %s", data)
            session_key = self._get_session_key()

            period_past = data.get("period_past", "0d")
            recording_types = data.get("recording_types", "")
            recording_directions = data.get("recording_directions", "")
            recording_others = data.get("recording_others", "")

            # generates recordings
            filenames = list(
                generate_recording_filenames(
                    period_past, recording_types, recording_directions, recording_others
                )
            )

            # stores in session-specific server state
            self._set_recordings(session_key, filenames)

            response = {"recordings": filenames, "count": len(filenames)}
            logger.debug("Response body: %s", response)

            return response, 201

        @self.app.route("/mock/recordings", methods=["DELETE"])
        def clear_recordings_route() -> tuple[dict[str, str], int]:
            """clears all recordings from server state"""
            logger.debug("DELETE /mock/recordings")
            session_key = self._get_session_key()
            self._set_recordings(session_key, [])
            logger.debug("Response body: {'status': 'cleared'}")
            return {"status": "cleared"}, 200

    def start(self) -> None:
        """starts the flask server in a background thread"""
        if self.server_thread is not None:
            return

        # configures mock dashcam logging
        mock_logger = logging.getLogger("features.mock_dashcam")
        mock_logger.setLevel(getattr(logging, self.log_level.upper()))

        # ensures logger has a handler (console output)
        if not mock_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            mock_logger.addHandler(handler)

        def run_server() -> None:
            # runs flask dev server - if it fails, thread dies and HTTP check will timeout
            self.app.run(host="127.0.0.1", port=self.port, use_reloader=False)

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        # verifies server started by pinging the health check endpoint
        max_attempts = 50
        retry_interval = 0.1
        for _ in range(max_attempts):
            time.sleep(retry_interval)

            try:
                response = requests.get(
                    f"http://127.0.0.1:{self.port}/mock/ping",
                    timeout=1.0,
                )
                if response.status_code == 200:
                    logger.info(
                        f"Mock dashcam server started successfully on port {self.port}"
                    )
                    return
            except requests.ConnectionError:
                # server not ready yet, continues waiting
                continue
            except requests.RequestException as e:
                # unexpected HTTP error - let it bubble up for visibility
                raise RuntimeError(
                    f"Unexpected HTTP error during health check on port {self.port}: {e}"
                ) from e

        raise RuntimeError(
            f"Mock dashcam server did not start within {max_attempts * retry_interval:.0f}s on port "
            f"{self.port}"
        )

    def stop(self) -> None:
        """stops the flask server"""
        # intentionally skipping graceful shutdown for test simplicity
        # daemon threads will terminate automatically when the test process exits
        self.server_thread = None

    def clear_recordings(self, session_key: str | None = None) -> None:
        """clears recordings (for cleanup)"""
        with self._sessions_lock:
            if session_key:
                # clears only session-specific recordings
                self._recordings_by_session[session_key] = []
            else:
                # clears all recordings across all sessions
                self._recordings_by_session.clear()
