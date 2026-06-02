"""Open-Meteo API Client.

Reference: https://open-meteo.com/en/docs
"""

import requests
from datetime import datetime
from functools import lru_cache


class OpenMeteoClient:
    """Client for Open-Meteo free weather API.
    
    - No API key required
    - No rate limiting for POC
    - Global coverage
    - Hourly + forecast data
    """
    
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    
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
    
    def __init__(self):
        """Initialize Open-Meteo client."""
        self.session = requests.Session()
        self.session.timeout = 10  # 10s timeout
        
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
            "timezone": "auto"  # Automatic timezone detection
        }
        
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
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
            "timestamp": datetime.now().isoformat()
        }
