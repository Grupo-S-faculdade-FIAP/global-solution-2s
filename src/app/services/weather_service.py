"""Weather service layer.

Abstracts the Open-Meteo API client for use in routes/lambdas.
"""

from src.app.clients.openmeteo import OpenMeteoClient


class WeatherService:
    """Service for weather operations."""
    
    def __init__(self):
        """Initialize weather service."""
        self.client = OpenMeteoClient()
        
    def get_current(self, lat: float, lon: float) -> dict:
        """Get current weather for a location.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            dict with weather data
            
        Raises:
            ValueError: If coordinates invalid
            Exception: If API call fails
        """
        return self.client.get_current(lat, lon)
