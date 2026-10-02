"""client for the mock dashcam's /mock/ control routes."""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

import requests


class MockDashcamClient:
    """configures and inspects one scenario's session on the mock dashcam."""

    def __init__(self, url: str, affinity_key: str) -> None:
        self.affinity_key = affinity_key
        self._url = url

    # JSON responses are untyped, hence Any
    def _request(self, method: str, path: str, json: object = None) -> dict[str, Any]:
        """sends a control request and returns the decoded JSON response."""
        response = requests.request(
            method,
            f"{self._url}{path}",
            json=json,
            headers={"X-Affinity-Key": self.affinity_key},
            timeout=10,
        )
        response.raise_for_status()
        body: dict[str, Any] = response.json()
        return body

    def set_legacy_api(self, legacy_api: bool) -> None:
        """makes the session behave as a legacy camera or a V1.009+ one."""
        self._request("PUT", "/mock/legacy-api", {"legacy_api": legacy_api})

    def set_recordings(self, filenames: Collection[str]) -> None:
        """replaces the recording files the dashcam lists and serves."""
        self._request("PUT", "/mock/recordings", {"recordings": list(filenames)})

    def fail_downloads(self, filenames: Collection[str]) -> None:
        """makes the dashcam answer downloads of the filenames with a 500 error."""
        self._request("PUT", "/mock/download-errors", {"filenames": list(filenames)})

    def fail_listing(self) -> None:
        """makes the dashcam answer requests for its recording list with a 500 error."""
        self._request("PUT", "/mock/listing-error", {"failing": True})

    def requested_files(self) -> list[str]:
        """returns the recording filenames requested since the log was cleared."""
        filenames: list[str] = self._request("GET", "/mock/requests")["filenames"]
        return filenames

    def clear_requests(self) -> None:
        """clears the session's request log."""
        self._request("DELETE", "/mock/requests")

    def delete_session(self) -> None:
        """discards all of the session's state on the dashcam."""
        self._request("DELETE", "/mock/session")
