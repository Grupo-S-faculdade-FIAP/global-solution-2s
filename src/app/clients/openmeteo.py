"""Open-Meteo API Client.

Reference: https://open-meteo.com/en/docs
"""

import requests
from functools import lru_cache

from app.core.config import settings


class OpenMeteoClient:
    """Client for Open-Meteo free weather API.
    
    - No API key required
    - No rate limiting for POC
    - Global coverage
    - Hourly + forecast data
    """
    
    # Hourly data fields to request
    HOURLY_FIELDS = [
        "temperature_2m",
        "relative_humidity_2m",
        "pressure_msl",
        "wind_speed_10m",
        "wind_direction_10m",
        "precipitation",
        "weather_code"
    ]
    
    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

    def __init__(self):
        """Initialize Open-Meteo client."""
        self.base_url = settings.OPENMETEO_API_URL
        self.archive_url = self.ARCHIVE_URL
        self.timezone = settings.OPENMETEO_TIMEZONE
        self.session = requests.Session()
        self.session.timeout = 30
        
    def _validate_coordinates(self, lat: float, lon: float) -> None:
        """Validate latitude and longitude.
        
        Args:
            lat: Latitude (-90 to 90)
            lon: Longitude (-180 to 180)
            
        Raises:
            ValueError: If coordinates are invalid
        """
        if not -90 <= lat <= 90:
            raise ValueError(f"Invalid latitude: {lat}. Must be between -90 and 90")
        if not -180 <= lon <= 180:
            raise ValueError(f"Invalid longitude: {lon}. Must be between -180 and 180")
    
    @lru_cache(maxsize=128)
    def get_current(self, lat: float, lon: float) -> dict:
        """Get current weather for location.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            dict with keys:
                - temperature: °C
                - humidity: %
                - pressure: hPa
                - wind_speed: m/s
                - wind_direction: degrees (0-360)
                - precipitation: mm
                - timestamp: ISO 8601 string
                
        Raises:
            ValueError: If coordinates invalid
            Exception: If API call fails
        """
        self._validate_coordinates(lat, lon)
        
        # Query API for current + 1h forecast (to get hourly current)
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(self.HOURLY_FIELDS),
            "timezone": self.timezone
        }
        
        try:
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch weather data: {str(e)}")
        
        data = response.json()
        
        # Extract current (index 0 = current hour)
        hourly = data["hourly"]
        
        # Get current values (latest index)
        current_index = 0  # First hour in response is current
        
        return {
            "temperature": float(hourly["temperature_2m"][current_index]),
            "humidity": int(hourly["relative_humidity_2m"][current_index]),
            "pressure": float(hourly["pressure_msl"][current_index]),
            "wind_speed": float(hourly["wind_speed_10m"][current_index]),
            "wind_direction": int(hourly["wind_direction_10m"][current_index]),
            "precipitation": float(hourly["precipitation"][current_index]),
            "timestamp": hourly["time"][current_index],
        }

    def get_historical_hourly(
        self,
        lat: float,
        lon: float,
        start_date: str,
        end_date: str,
    ) -> list[dict]:
        """Fetch hourly historical weather from Open-Meteo Archive API."""
        self._validate_coordinates(lat, lon)
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ",".join(self.HOURLY_FIELDS),
            "timezone": self.timezone,
        }
        try:
            response = self.session.get(self.archive_url, params=params, timeout=60)
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
