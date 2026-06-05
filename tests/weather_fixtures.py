"""Shared weather test data and helpers."""

from __future__ import annotations

from unittest.mock import MagicMock


SAMPLE_WEATHER = {
    "temperature": 25.5,
    "humidity": 70,
    "pressure": 1013.2,
    "wind_speed": 5.2,
    "wind_direction": 180,
    "precipitation": 0.0,
    "timestamp": "2026-06-05T12:00",
}

SAMPLE_WEATHER_RIO = {
    "temperature": 30.1,
    "humidity": 82,
    "pressure": 1010.0,
    "wind_speed": 8.0,
    "wind_direction": 90,
    "precipitation": 2.5,
    "timestamp": "2026-06-05T12:00",
}

OPENMETEO_HOURLY_JSON = {
    "hourly": {
        "time": ["2026-06-05T12:00", "2026-06-05T13:00"],
        "temperature_2m": [25.5, 26.0],
        "relative_humidity_2m": [70, 68],
        "pressure_msl": [1013.2, 1012.8],
        "wind_speed_10m": [5.2, 5.5],
        "wind_direction_10m": [180, 175],
        "precipitation": [0.0, 0.5],
        "weather_code": [0, 1],
    }
}


def make_mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Build a requests.Response-like mock."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    if status_code >= 400:
        from requests.exceptions import HTTPError

        mock.raise_for_status.side_effect = HTTPError(
            f"{status_code} Error", response=mock
        )
    else:
        mock.raise_for_status.return_value = None
    return mock
