"""mock dashcam session configuration helpers"""

import requests


def set_legacy_api(
    mock_dashcam_url: str, scenario_token: str, legacy_api: bool
) -> None:
    """configures whether the mock dashcam session behaves as a legacy camera or V1.009+."""
    url = f"{mock_dashcam_url}/mock/legacy-api"
    headers = {"X-Affinity-Key": scenario_token}
    data = {"legacy_api": legacy_api}

    response = requests.post(url, json=data, headers=headers, timeout=10)
    response.raise_for_status()
