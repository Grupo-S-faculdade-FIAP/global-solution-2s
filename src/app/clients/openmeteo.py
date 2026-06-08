"""Open-Meteo API Client.

Reference: https://open-meteo.com/en/docs
"""

from __future__ import annotations

from functools import lru_cache

import requests

from app.core.config import settings
from app.services.external_api_rate_limit import acquire_external_api_slot

DEFAULT_TIMEOUT_SEC = 10
ARCHIVE_TIMEOUT_SEC = 60

# Hourly data fields to request
_HOURLY_FIELDS = [
    "temperature_2m",
    "relative_humidity_2m",
    "pressure_msl",
    "wind_speed_10m",
    "wind_direction_10m",
    "precipitation",
    "weather_code",
]


def _validate_coordinates(lat: float, lon: float) -> None:
    if not -90 <= lat <= 90:
        raise ValueError(f"Invalid latitude: {lat}. Must be between -90 and 90")
    if not -180 <= lon <= 180:
        raise ValueError(f"Invalid longitude: {lon}. Must be between -180 and 180")


@lru_cache(maxsize=128)
def _get_current_cached(lat: float, lon: float, base_url: str, timezone: str) -> dict:
    """Fetch current weather (module-level cache — não ignora config por instância)."""
    _validate_coordinates(lat, lon)
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(_HOURLY_FIELDS),
        "timezone": timezone,
    }
    try:
        acquire_external_api_slot("open-meteo")
        response = requests.get(base_url, params=params, timeout=DEFAULT_TIMEOUT_SEC)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch weather data: {str(e)}") from e

    hourly = response.json()["hourly"]
    current_index = 0
    return {
        "temperature": float(hourly["temperature_2m"][current_index]),
        "humidity": int(hourly["relative_humidity_2m"][current_index]),
        "pressure": float(hourly["pressure_msl"][current_index]),
        "wind_speed": float(hourly["wind_speed_10m"][current_index]),
        "wind_direction": int(hourly["wind_direction_10m"][current_index]),
        "precipitation": float(hourly["precipitation"][current_index]),
        "timestamp": hourly["time"][current_index],
    }


class OpenMeteoClient:
    """Client for Open-Meteo free weather API."""

    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

    def __init__(self):
        self.base_url = settings.OPENMETEO_API_URL
        self.archive_url = self.ARCHIVE_URL
        self.timezone = settings.OPENMETEO_TIMEZONE
        self.session = requests.Session()

    def get_current(self, lat: float, lon: float) -> dict:
        return _get_current_cached(lat, lon, self.base_url, self.timezone)

    def get_historical_hourly(
        self,
        lat: float,
        lon: float,
        start_date: str,
        end_date: str,
    ) -> list[dict]:
        _validate_coordinates(lat, lon)
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ",".join(_HOURLY_FIELDS),
            "timezone": self.timezone,
        }
        try:
            acquire_external_api_slot("open-meteo-archive")
            response = self.session.get(
                self.archive_url, params=params, timeout=ARCHIVE_TIMEOUT_SEC
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch historical weather: {e}") from e

        hourly = response.json().get("hourly", {})
        times = hourly.get("time", [])
        records: list[dict] = []
        for i, ts in enumerate(times):
            wind_ms = float(hourly["wind_speed_10m"][i] or 0)
            records.append({
                "timestamp": ts,
                "temperature": float(hourly["temperature_2m"][i]),
                "humidity": int(hourly["relative_humidity_2m"][i]),
                "precipitation": float(hourly["precipitation"][i] or 0),
                "wind_speed_kmh": round(wind_ms * 3.6, 2),
                "latitude": lat,
                "longitude": lon,
            })
        return records


def clear_openmeteo_cache() -> None:
    _get_current_cached.cache_clear()
