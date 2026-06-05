"""Tests for weather service (Open-Meteo API integration)."""

import pytest
from unittest.mock import patch, MagicMock

from app.clients.openmeteo import OpenMeteoClient
from app.services.weather_service import WeatherService
from weather_fixtures import (
    SAMPLE_WEATHER,
    SAMPLE_WEATHER_RIO,
    OPENMETEO_HOURLY_JSON,
    make_mock_response,
)


class TestWeatherService:
    """Test WeatherService.get_current() method."""

    def test_get_current_weather_success(self):
        """Test successful weather data retrieval with mocked API."""
        with patch.object(
            OpenMeteoClient, "get_current", return_value=SAMPLE_WEATHER
        ):
            service = WeatherService()
            weather = service.get_current(lat=-23.5505, lon=-46.6333)

        assert weather is not None
        assert weather["temperature"] == 25.5
        assert weather["humidity"] == 70
        assert "pressure" in weather
        assert "wind_speed" in weather
        assert "wind_direction" in weather
        assert "precipitation" in weather
        assert "timestamp" in weather

    def test_get_current_weather_values_in_range(self):
        """Test that weather values are in sensible ranges."""
        with patch.object(
            OpenMeteoClient, "get_current", return_value=SAMPLE_WEATHER
        ):
            service = WeatherService()
            weather = service.get_current(lat=-23.5505, lon=-46.6333)

        assert -50 < weather["temperature"] < 60
        assert 0 <= weather["humidity"] <= 100
        assert 870 < weather["pressure"] < 1085
        assert 0 <= weather["wind_speed"] <= 40
        assert 0 <= weather["wind_direction"] <= 360
        assert 0 <= weather["precipitation"] <= 100

    def test_get_current_weather_invalid_latitude(self):
        """Test that invalid latitude raises error."""
        service = WeatherService()

        with pytest.raises(ValueError, match="latitude"):
            service.get_current(lat=100, lon=0)

        with pytest.raises(ValueError, match="latitude"):
            service.get_current(lat=-100, lon=0)

    def test_get_current_weather_invalid_longitude(self):
        """Test that invalid longitude raises error."""
        service = WeatherService()

        with pytest.raises(ValueError, match="longitude"):
            service.get_current(lat=0, lon=200)

        with pytest.raises(ValueError, match="longitude"):
            service.get_current(lat=0, lon=-200)

    def test_get_current_weather_caching(self):
        """Test that consecutive calls use cache on the client."""
        client = OpenMeteoClient()
        mock_session = MagicMock()
        mock_session.get.return_value = make_mock_response(OPENMETEO_HOURLY_JSON)
        client.session = mock_session

        weather1 = client.get_current(lat=-23.5505, lon=-46.6333)
        weather2 = client.get_current(lat=-23.5505, lon=-46.6333)

        assert weather1 == weather2
        assert mock_session.get.call_count == 1

    def test_get_current_weather_different_locations(self):
        """Test that different locations trigger separate API calls."""
        client = OpenMeteoClient()
        mock_session = MagicMock()
        mock_session.get.side_effect = [
            make_mock_response(OPENMETEO_HOURLY_JSON),
            make_mock_response({
                "hourly": {
                    **OPENMETEO_HOURLY_JSON["hourly"],
                    "temperature_2m": [30.1, 30.5],
                    "relative_humidity_2m": [82, 80],
                }
            }),
        ]
        client.session = mock_session

        weather_rio = client.get_current(lat=-22.9068, lon=-43.1729)
        weather_sp = client.get_current(lat=-23.5505, lon=-46.6333)

        assert weather_rio["temperature"] != weather_sp["temperature"]
        assert mock_session.get.call_count == 2

    def test_get_current_weather_response_structure(self):
        """Test that response has correct structure."""
        with patch.object(
            OpenMeteoClient, "get_current", return_value=SAMPLE_WEATHER_RIO
        ):
            service = WeatherService()
            weather = service.get_current(lat=-23.5505, lon=-46.6333)

        expected_keys = {
            "temperature",
            "humidity",
            "pressure",
            "wind_speed",
            "wind_direction",
            "precipitation",
            "timestamp",
        }
        assert set(weather.keys()) == expected_keys
