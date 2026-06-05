"""Tests for weather ingestion Lambda handler.

This Lambda is triggered by CloudWatch Events every 30 minutes.
It fetches weather data from Open-Meteo API and stores in DynamoDB.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.lambdas.ingest_weather import (  # noqa: E402
    lambda_handler,
    WeatherMetricsRepository,
    parse_locations,
)

# Módulo real usado nos patches (sem prefixo src.)
_MODULE = "app.lambdas.ingest_weather"


class TestWeatherIngestLambda:
    """Test weather ingestion Lambda handler."""

    def test_lambda_handler_success(self):
        """Test successful weather ingestion."""
        with patch("app.lambdas.ingest_weather.WeatherService") as mock_service:
            with patch("app.lambdas.ingest_weather.WeatherMetricsRepository") as mock_repo:
                # Mock weather data
                mock_service.return_value.get_current.return_value = {
                    "temperature": 28.5,
                    "humidity": 75,
                    "pressure": 1013.25,
                    "wind_speed": 12.3,
                    "wind_direction": 180,
                    "precipitation": 2.5,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Call handler
                response = lambda_handler({}, None)
                
                # Verify success
                assert response["statusCode"] == 200
                assert "records_stored" in response["body"]
                
    def test_lambda_handler_multiple_locations(self):
        """Test ingestion for multiple locations."""
        with patch("app.lambdas.ingest_weather.WeatherService") as mock_service:
            with patch("app.lambdas.ingest_weather.WeatherMetricsRepository") as mock_repo:
                # Mock weather data
                mock_weather = {
                    "temperature": 25.0,
                    "humidity": 70,
                    "pressure": 1015.0,
                    "wind_speed": 10.0,
                    "wind_direction": 90,
                    "precipitation": 0.0,
                    "timestamp": datetime.now().isoformat()
                }
                mock_service.return_value.get_current.return_value = mock_weather
                
                # Call handler (should process 3+ locations)
                response = lambda_handler({}, None)
                
                assert response["statusCode"] == 200
                assert mock_service.return_value.get_current.call_count >= 3
                
    def test_lambda_handler_stores_in_dynamodb(self):
        """Test that weather data is stored in DynamoDB."""
        with patch("app.lambdas.ingest_weather.WeatherService") as mock_service:
            with patch("app.lambdas.ingest_weather.WeatherMetricsRepository") as mock_repo:
                mock_weather = {
                    "temperature": 28.5,
                    "humidity": 75,
                    "pressure": 1013.25,
                    "wind_speed": 12.3,
                    "wind_direction": 180,
                    "precipitation": 2.5,
                    "timestamp": datetime.now().isoformat()
                }
                mock_service.return_value.get_current.return_value = mock_weather
                
                response = lambda_handler({}, None)
                
                # Verify repository was called
                assert mock_repo.return_value.put_item.called
                
    def test_lambda_handler_graceful_error(self):
        """Test that Lambda handles errors gracefully."""
        with patch("app.lambdas.ingest_weather.WeatherService") as mock_service:
            with patch("app.lambdas.ingest_weather.WeatherMetricsRepository") as mock_repo:
                # Simulate API error
                mock_service.return_value.get_current.side_effect = Exception("API error")
                
                # Handler should not crash, should log error
                response = lambda_handler({}, None)
                
                assert response["statusCode"] == 500 or response["statusCode"] == 207
            
    def test_lambda_handler_returns_valid_response(self):
        """Test that Lambda returns valid AWS Lambda response format."""
        with patch("app.lambdas.ingest_weather.WeatherService") as mock_service:
            with patch("app.lambdas.ingest_weather.WeatherMetricsRepository") as mock_repo:
                mock_service.return_value.get_current.return_value = {
                    "temperature": 20.0,
                    "humidity": 50,
                    "pressure": 1010.0,
                    "wind_speed": 5.0,
                    "wind_direction": 45,
                    "precipitation": 0.0,
                    "timestamp": datetime.now().isoformat()
                }
                
                response = lambda_handler({}, None)
                
                # Verify response structure
                assert "statusCode" in response
                assert "body" in response
                assert isinstance(response["statusCode"], int)
                assert isinstance(response["body"], str)


class TestWeatherMetricsRepository:
    """Test DynamoDB repository for weather metrics."""
    
    @patch("boto3.resource")
    def test_put_item_success(self, mock_boto3):
        """Test storing weather metric in DynamoDB."""
        mock_table = MagicMock()
        mock_boto3.return_value.Table.return_value = mock_table
        
        repo = WeatherMetricsRepository()
        metric = {
            "pk": "2026-06-02T10:00:00#lat-22.89_lon-43.18",
            "sk": "temperature",
            "timestamp": "2026-06-02T10:00:00Z",
            "latitude": -22.89,
            "longitude": -43.18,
            "temperature": 28.5,
            "humidity": 75,
            "pressure": 1013.25,
            "wind_speed": 12.3,
            "wind_direction": 180,
            "precipitation": 2.5,
            "ttl": 1234567890
        }
        
        repo.put_item(metric)
        
        # Verify DynamoDB was called
        assert mock_table.put_item.called
        
    def test_metric_includes_required_fields(self):
        """Test that weather metric has all required fields."""
        from app.lambdas.ingest_weather import format_weather_metric
        
        weather = {
            "temperature": 28.5,
            "humidity": 75,
            "pressure": 1013.25,
            "wind_speed": 12.3,
            "wind_direction": 180,
            "precipitation": 2.5,
            "timestamp": "2026-06-02T10:00:00Z"
        }
        
        metric = format_weather_metric(weather, lat=-22.89, lon=-43.18)
        
        required_fields = {
            "pk", "sk", "timestamp", "latitude", "longitude",
            "temperature", "humidity", "pressure", "wind_speed",
            "wind_direction", "precipitation", "source", "ttl"
        }
        
        assert set(metric.keys()) == required_fields


class TestParseLocations:
    """Test location parsing from settings."""
    
    @patch("app.lambdas.ingest_weather.settings")
    def test_parse_locations_valid(self, mock_settings):
        """Test parsing valid location string."""
        mock_settings.WEATHER_LOCATIONS = "-23.5505,-46.6333,-22.9068,-43.1729"
        
        locations = parse_locations()
        
        assert len(locations) == 2
        assert locations[0] == (-23.5505, -46.6333)
        assert locations[1] == (-22.9068, -43.1729)
        
    @patch("app.lambdas.ingest_weather.settings")
    def test_parse_locations_single(self, mock_settings):
        """Test parsing single location."""
        mock_settings.WEATHER_LOCATIONS = "-23.5505,-46.6333"
        
        locations = parse_locations()
        
        assert len(locations) == 1
        assert locations[0] == (-23.5505, -46.6333)
        
    @patch("app.lambdas.ingest_weather.settings")
    def test_parse_locations_invalid(self, mock_settings):
        """Test that odd number of values raises error."""
        mock_settings.WEATHER_LOCATIONS = "-23.5505,-46.6333,-22.9068"
        
        with pytest.raises(ValueError):
            parse_locations()
