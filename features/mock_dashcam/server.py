"""flask-based mock BlackVue dashcam for behavioral testing.

every request carries an X-Affinity-Key header naming the scenario's session,
so scenarios share one server without seeing each other's state.
the /mock/ routes let scenarios configure a session and read what it received.
"""

from __future__ import annotations

import base64
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field

import flask
from werkzeug.exceptions import BadRequest
from werkzeug.serving import make_server

from features.lib.recordings import MOCK_FILES_DIR, RECORDING_FILENAME_RE

logger = logging.getLogger("features.mock_dashcam")

# port the mock dashcam listens on in its container; matches EXPOSE in the
# Dockerfile
MOCK_DASHCAM_PORT = 5000

# metadata types the /vodMetadata endpoint serves, and their file extensions
METADATA_EXTENSIONS = {"thumbnail": "thm", "gps": "gps"}


@dataclass
class _Session:
    """the state of one scenario's session."""

    recordings: list[str] = field(default_factory=list)
    download_errors: set[str] = field(default_factory=set)
    # answers the recording list requests with a 500 error
    listing_error: bool = False
    legacy_api: bool = False
    # recording filenames blackvuesync requested, in order
    requested_files: list[str] = field(default_factory=list)


def _metadata_filename(video_filename: str, metadata_type: str) -> str:
    """returns the filename blackvuesync stores a video's metadata under.

    Raises:
        BadRequest: the video filename or the metadata type is invalid.
    """
    match = RECORDING_FILENAME_RE.fullmatch(video_filename)
    if match is None or match.group("extension") != "mp4":
        raise BadRequest(f"invalid video filename {video_filename!r}")
    if metadata_type not in METADATA_EXTENSIONS:
        raise BadRequest(f"invalid metadata type {metadata_type!r}")

    extension = METADATA_EXTENSIONS[metadata_type]
    prefix = f"{match.group('base_filename')}_{match.group('type')}"
    if extension == "thm":
        return f"{prefix}{match.group('direction')}.thm"
    return f"{prefix}.gps"


class MockDashcam:
    """a mock dashcam serving the legacy and V1.009+ protocols over HTTP.

    binding to port 0 picks a free ephemeral port, available as `port`.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self.app = flask.Flask(__name__)
        self._lock = threading.Lock()
        self._sessions: defaultdict[str, _Session] = defaultdict(_Session)
        self._setup_routes()

        self._server = make_server(host, port, self.app, threaded=True)
        self.port = self._server.server_port
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def start(self) -> None:
        """serves requests on a background thread."""
        self._thread.start()

    def stop(self) -> None:
        """stops the background thread and closes the listening socket."""
        self._server.shutdown()
        self._thread.join()
        self._server.server_close()

    def serve_forever(self) -> None:
        """serves requests on the calling thread until the process ends."""
        self._server.serve_forever()

    def _affinity_key(self) -> str:
        """returns the request's affinity key; aborts 400 without one."""
        affinity_key = flask.request.headers.get("X-Affinity-Key")
        if not affinity_key:
            flask.abort(400, description="X-Affinity-Key header is required")
        return affinity_key

    def _session(self) -> _Session:
        """returns the session named by the request's affinity key."""
        affinity_key = self._affinity_key()
        with self._lock:
            return self._sessions[affinity_key]

    def _serve_recording_file(self, session: _Session, filename: str) -> flask.Response:
        """serves the fixture for a listed recording, or aborts 404/500 as configured."""
        with self._lock:
            listed = filename in session.recordings
            failing = filename in session.download_errors

        if not listed:
            logger.debug("answers %s with 404: not in the session recordings", filename)
            flask.abort(404)
        if failing:
            logger.info("answers %s with 500: configured download error", filename)
            flask.abort(500)

        extension = filename.rsplit(".", 1)[-1]
        return flask.send_file(MOCK_FILES_DIR / f"mock.{extension}")

    def _abort_on_listing_error(self, session: _Session) -> None:
        """aborts 500 when the session is configured to fail its recording list."""
        with self._lock:
            failing = session.listing_error
        if failing:
            logger.info(
                "answers %s with 500: configured listing error", flask.request.path
            )
            flask.abort(500)

    def _record_request(self, session: _Session, filename: str) -> None:
        """appends a requested recording filename to the session's request log."""
        with self._lock:
            session.requested_files.append(filename)

    def _setup_routes(self) -> None:
        """registers the dashcam and /mock/ control routes."""

        @self.app.route("/accessible", methods=["GET"])
        def accessible() -> tuple[dict[str, str], int]:
            """reports the V1.009+ API is reachable; absent on legacy firmware."""
            if self._session().legacy_api:
                flask.abort(404)
            return {"accessible": "OK", "message": "Access possible."}, 200

        @self.app.route("/vodList", methods=["GET"])
        def vod_list() -> tuple[dict[str, object], int]:
            """returns the index of video recordings as JSON (V1.009+)."""
            session = self._session()
            self._abort_on_listing_error(session)
            if session.legacy_api:
                flask.abort(404)
            with self._lock:
                filelist = [
                    {"filename": filename}
                    for filename in session.recordings
                    if filename.endswith(".mp4")
                ]
            return {"filelist": filelist}, 200

        @self.app.route("/blackvue_vod.cgi", methods=["GET"])
        def vod() -> flask.Response | str:
            """returns the index of all recording files (legacy firmware)."""
            session = self._session()
            self._abort_on_listing_error(session)
            if not session.legacy_api:
                # firmware V1.009+ deprecated this endpoint
                return flask.Response("mp4 only", status=415, mimetype="text/plain")

            with self._lock:
                lines = ["v:1.00"] + [
                    f"n:/Record/{filename},s:1000000" for filename in session.recordings
                ]
            return "\r\n".join(lines) + "\r\n"

        @self.app.route("/Record/<filename>", methods=["GET"])
        def record(filename: str) -> flask.Response:
            """serves any recording file (legacy firmware)."""
            session = self._session()
            self._record_request(session, filename)
            if not session.legacy_api:
                # firmware V1.009+ moved downloads to the root
                flask.abort(400)
            return self._serve_recording_file(session, filename)

        @self.app.route("/vodMetadata", methods=["POST"])
        def vod_metadata() -> tuple[dict[str, object], int]:
            """returns base64-encoded thumbnail or gps data (V1.009+)."""
            session = self._session()
            # indexes strictly, so a malformed request fails with an error
            # instead of passing as a request for missing metadata
            data = flask.request.get_json()
            video_filename: str = data["file"]
            (metadata_type,) = data["types"]
            metadata_filename = _metadata_filename(video_filename, metadata_type)
            self._record_request(session, metadata_filename)

            if session.legacy_api:
                flask.abort(404)

            with self._lock:
                listed = video_filename in session.recordings
                failing = metadata_filename in session.download_errors

            if not listed:
                # blackvuesync requests metadata only for listed videos; it would
                # treat this empty object as missing metadata and mark it failed
                return {}, 200
            if failing:
                logger.info(
                    "answers %s with 500: configured download error", metadata_filename
                )
                flask.abort(500)

            extension = METADATA_EXTENSIONS[metadata_type]
            encoded = base64.b64encode(
                (MOCK_FILES_DIR / f"mock.{extension}").read_bytes()
            ).decode("ascii")

            # the firmware nests the base64 payload under "metadata", keyed by type
            return {"metadata": {metadata_type: encoded}}, 200

        @self.app.route("/<filename>", methods=["GET"])
        def root_record(filename: str) -> flask.Response:
            """serves videos from the root (V1.009+); rejects non-mp4 with 'mp4 only'."""
            session = self._session()
            self._record_request(session, filename)
            if session.legacy_api:
                # legacy firmware serves downloads only under /Record/
                flask.abort(404)
            if not filename.endswith(".mp4"):
                return flask.Response("mp4 only", status=415, mimetype="text/plain")
            return self._serve_recording_file(session, filename)

        @self.app.route("/mock/recordings", methods=["PUT"])
        def set_recordings() -> tuple[dict[str, object], int]:
            """replaces the session's recording files."""
            session = self._session()
            with self._lock:
                session.recordings = list(flask.request.get_json()["recordings"])
            return {"count": len(session.recordings)}, 200

        @self.app.route("/mock/legacy-api", methods=["PUT"])
        def set_legacy_api() -> tuple[dict[str, object], int]:
            """makes the session behave as a legacy camera or a V1.009+ one."""
            session = self._session()
            with self._lock:
                session.legacy_api = bool(flask.request.get_json()["legacy_api"])
            return {"legacy_api": session.legacy_api}, 200

        @self.app.route("/mock/download-errors", methods=["PUT"])
        def set_download_errors() -> tuple[dict[str, object], int]:
            """replaces the recording files the session answers with a 500 error."""
            session = self._session()
            with self._lock:
                session.download_errors = set(flask.request.get_json()["filenames"])
            return {"count": len(session.download_errors)}, 200

        @self.app.route("/mock/listing-error", methods=["PUT"])
        def set_listing_error() -> tuple[dict[str, object], int]:
            """makes the session fail or serve its recording list."""
            session = self._session()
            with self._lock:
                session.listing_error = bool(flask.request.get_json()["failing"])
            return {"failing": session.listing_error}, 200

        @self.app.route("/mock/requests", methods=["GET"])
        def get_requests() -> tuple[dict[str, object], int]:
            """returns the recording filenames the session received requests for."""
            session = self._session()
            with self._lock:
                return {"filenames": list(session.requested_files)}, 200

        @self.app.route("/mock/requests", methods=["DELETE"])
        def clear_requests() -> tuple[dict[str, object], int]:
            """clears the session's request log."""
            session = self._session()
            with self._lock:
                session.requested_files.clear()
            return {}, 200

        @self.app.route("/mock/session", methods=["DELETE"])
        def delete_session() -> tuple[dict[str, object], int]:
            """discards all of the session's state."""
            affinity_key = self._affinity_key()
            with self._lock:
                self._sessions.pop(affinity_key, None)
            return {}, 200
