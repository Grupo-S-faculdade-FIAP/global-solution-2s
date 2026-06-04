"""Tests for weather service (Open-Meteo API integration)."""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.services.weather_service import WeatherService  # noqa: E402


class TestWeatherService:
    """Test WeatherService.get_current() method."""

    def test_get_current_weather_success(self):
        """Test successful weather data retrieval."""
        service = WeatherService()
        
        # Query a real location (São Paulo)
        weather = service.get_current(lat=-23.5505, lon=-46.6333)
        
        # Verify required fields exist
        assert weather is not None
        assert "temperature" in weather
        assert "humidity" in weather
        assert "pressure" in weather
        assert "wind_speed" in weather
        assert "wind_direction" in weather
        assert "precipitation" in weather
        assert "timestamp" in weather
        
    def test_get_current_weather_values_in_range(self):
        """Test that weather values are in sensible ranges."""
        service = WeatherService()
        weather = service.get_current(lat=-23.5505, lon=-46.6333)
        
        # Temperature: -50 to +60 Celsius (reasonable global range)
        assert -50 < weather["temperature"] < 60, f"Temp out of range: {weather['temperature']}"
        
        # Humidity: 0-100%
        assert 0 <= weather["humidity"] <= 100, f"Humidity out of range: {weather['humidity']}"
        
        # Pressure: 870-1085 hPa (reasonable range)
        assert 870 < weather["pressure"] < 1085, f"Pressure out of range: {weather['pressure']}"
        
        # Wind speed: 0-40 m/s (reasonable for POC)
        assert 0 <= weather["wind_speed"] <= 40, f"Wind speed out of range: {weather['wind_speed']}"
        
        # Wind direction: 0-360 degrees
        assert 0 <= weather["wind_direction"] <= 360, f"Wind direction out of range: {weather['wind_direction']}"
        
        # Precipitation: 0-100 mm (reasonable hourly)
        assert 0 <= weather["precipitation"] <= 100, f"Precipitation out of range: {weather['precipitation']}"
        
    def test_get_current_weather_invalid_latitude(self):
        """Test that invalid latitude raises error."""
        service = WeatherService()
        
        with pytest.raises(ValueError, match="latitude"):
            service.get_current(lat=100, lon=0)  # Invalid lat
            
        with pytest.raises(ValueError, match="latitude"):
            service.get_current(lat=-100, lon=0)  # Invalid lat
            
    def test_get_current_weather_invalid_longitude(self):
        """Test that invalid longitude raises error."""
        service = WeatherService()
        
        with pytest.raises(ValueError, match="longitude"):
            service.get_current(lat=0, lon=200)  # Invalid lon
            
        with pytest.raises(ValueError, match="longitude"):
            service.get_current(lat=0, lon=-200)  # Invalid lon
            
    def test_get_current_weather_caching(self):
        """Test that consecutive calls use cache."""
        service = WeatherService()
        
        # First call
        weather1 = service.get_current(lat=-23.5505, lon=-46.6333)
        
        # Second call (should be cached)
        weather2 = service.get_current(lat=-23.5505, lon=-46.6333)
        
        # Results should be identical (from cache)
        assert weather1 == weather2
        
    def test_get_current_weather_different_locations(self):
        """Test that different locations return different data."""
        service = WeatherService()
        
        # Rio de Janeiro
        weather_rio = service.get_current(lat=-22.9068, lon=-43.1729)
        
        # São Paulo
        weather_sp = service.get_current(lat=-23.5505, lon=-46.6333)
        
        # Brazília
        weather_bsb = service.get_current(lat=-15.8267, lon=-47.8711)
        
        # Results should be different (different locations)
        # At least one of temperature/humidity should differ
        assert (weather_rio["temperature"] != weather_sp["temperature"] or 
                weather_rio["humidity"] != weather_sp["humidity"])
        
    def test_get_current_weather_response_structure(self):
        """Test that response has correct structure."""
        service = WeatherService()
        weather = service.get_current(lat=-23.5505, lon=-46.6333)
        
        # Check all expected keys
        expected_keys = {
            "temperature",
            "humidity", 
            "pressure",
            "wind_speed",
            "wind_direction",
            "precipitation",
            "timestamp"
        }
        assert set(weather.keys()) == expected_keys, f"Unexpected keys: {set(weather.keys())}"
        

