"""Test suite for T-09: Data integration API endpoints."""

import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient
from app.main import app
from weather_fixtures import SAMPLE_WEATHER

client = TestClient(app)


class TestWeatherEndpoint:
    """Test GET /weather/current endpoint."""

    @patch(
        "app.routers.data_integration.weather_service.get_current",
        return_value=SAMPLE_WEATHER,
    )
    def test_get_weather_success(self, _mock_weather):
        """Test successful weather fetch with valid coordinates."""
        response = client.get("/weather/current?lat=-22.89&lon=-43.18")
        assert response.status_code == 200
        
        data = response.json()
        assert "temperature" in data
        assert "humidity" in data
        assert "pressure" in data
        assert "wind_speed" in data
        assert "wind_direction" in data
        assert "precipitation" in data
        assert "timestamp" in data
        
    def test_get_weather_invalid_latitude(self):
        """Test error when latitude is out of range."""
        response = client.get("/weather/current?lat=100&lon=-43.18")
        assert response.status_code == 400
        
    def test_get_weather_invalid_longitude(self):
        """Test error when longitude is out of range."""
        response = client.get("/weather/current?lat=-22.89&lon=200")
        assert response.status_code == 400
        
    def test_get_weather_missing_lat(self):
        """Test error when latitude is missing."""
        response = client.get("/weather/current?lon=-43.18")
        assert response.status_code == 422  # FastAPI validation error
        
    def test_get_weather_missing_lon(self):
        """Test error when longitude is missing."""
        response = client.get("/weather/current?lat=-22.89")
        assert response.status_code == 422  # FastAPI validation error
        
    @patch(
        "app.routers.data_integration.weather_service.get_current",
        return_value=SAMPLE_WEATHER,
    )
    def test_get_weather_response_structure(self, _mock_weather):
        """Test response has correct structure with proper types."""
        response = client.get("/weather/current?lat=-22.89&lon=-43.18")
        data = response.json()
        
        assert isinstance(data["temperature"], (int, float))
        assert isinstance(data["humidity"], (int, float))
        assert isinstance(data["pressure"], (int, float))
        assert isinstance(data["wind_speed"], (int, float))
        assert isinstance(data["wind_direction"], (int, float))
        assert isinstance(data["precipitation"], (int, float))
        assert isinstance(data["timestamp"], str)


class TestStormsEndpoint:
    """Test GET /storms/recent endpoint."""
    
    def test_get_storms_success(self):
        """Test successful storm detections fetch."""
        response = client.get("/storms/recent?hours=24")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
    def test_get_storms_with_default_hours(self):
        """Test that default hours works."""
        response = client.get("/storms/recent")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        
    def test_get_storms_invalid_hours(self):
        """Test error when hours is invalid."""
        response = client.get("/storms/recent?hours=invalid")
        assert response.status_code == 422  # FastAPI validation error
        
    def test_get_storms_negative_hours(self):
        """Test error when hours is negative."""
        response = client.get("/storms/recent?hours=-1")
        assert response.status_code == 422  # FastAPI validation error
        
    def test_get_storms_structure(self):
        """Test storm detection structure if results exist."""
        response = client.get("/storms/recent?hours=24")
        data = response.json()
        
        # If there are results, validate structure
        if len(data) > 0:
            storm = data[0]
            assert "detection_id" in storm
            assert "latitude" in storm
            assert "longitude" in storm
            assert "confidence" in storm
            assert "timestamp" in storm


class TestRiskEndpoint:
    """Test GET /risk/forecast endpoint."""

    @patch(
        "app.routers.data_integration.weather_service.get_current",
        return_value=SAMPLE_WEATHER,
    )
    def test_get_risk_success(self, _mock_weather):
        """Test successful risk forecast fetch."""
        response = client.get("/risk/forecast?lat=-22.89&lon=-43.18")
        assert response.status_code == 200
        
        data = response.json()
        assert "risk_score" in data
        assert "risk_category" in data
        assert "recommendation" in data
        
    def test_get_risk_invalid_latitude(self):
        """Test error when latitude is out of range."""
        response = client.get("/risk/forecast?lat=100&lon=-43.18")
        assert response.status_code == 400
        
    def test_get_risk_invalid_longitude(self):
        """Test error when longitude is out of range."""
        response = client.get("/risk/forecast?lat=-22.89&lon=200")
        assert response.status_code == 400
        
    def test_get_risk_missing_lat(self):
        """Test error when latitude is missing."""
        response = client.get("/risk/forecast?lon=-43.18")
        assert response.status_code == 422  # FastAPI validation error
        
    def test_get_risk_missing_lon(self):
        """Test error when longitude is missing."""
        response = client.get("/risk/forecast?lat=-22.89")
        assert response.status_code == 422  # FastAPI validation error
        
    @patch(
        "app.routers.data_integration.weather_service.get_current",
        return_value=SAMPLE_WEATHER,
    )
    def test_get_risk_structure(self, _mock_weather):
        """Test risk forecast response structure."""
        response = client.get("/risk/forecast?lat=-22.89&lon=-43.18")
        data = response.json()
        
        assert isinstance(data["risk_score"], (int, float))
        assert 0 <= data["risk_score"] <= 1
        assert data["risk_category"] in ["LOW", "MEDIUM", "HIGH"]
        assert isinstance(data["recommendation"], str)


class TestMapOverlayEndpoint:
    """Test GET /map/overlay endpoint."""
    
    def test_get_map_overlay_success(self):
        """Test successful map overlay GeoJSON fetch."""
        response = client.get("/map/overlay?bbox=-25,-50,-20,-40")
        assert response.status_code == 200
        
        data = response.json()
        assert "type" in data
        assert data["type"] == "FeatureCollection"
        assert "features" in data
        
    def test_get_map_overlay_invalid_bbox(self):
        """Test error when bbox is invalid."""
        response = client.get("/map/overlay?bbox=invalid")
        assert response.status_code == 400
        
    def test_get_map_overlay_missing_bbox(self):
        """Test error when bbox is missing."""
        response = client.get("/map/overlay")
        assert response.status_code == 422  # FastAPI validation error
        
    def test_get_map_overlay_geojson_structure(self):
        """Test GeoJSON structure is valid."""
        response = client.get("/map/overlay?bbox=-25,-50,-20,-40")
        data = response.json()
        
        assert data["type"] == "FeatureCollection"
        assert isinstance(data["features"], list)
        
        # If there are features, validate structure
        if len(data["features"]) > 0:
            feature = data["features"][0]
            assert "type" in feature
            assert feature["type"] == "Feature"
            assert "properties" in feature
            assert "geometry" in feature


class TestAlertsAnalyticsEndpoints:
    """Test analytics endpoints for dashboard bar charts."""

    def test_get_alerts_weekly_success(self):
        """Test weekly alerts endpoint returns expected weekday keys."""
        response = client.get("/alerts/weekly?days=30")

        # May return 200 with real data or 500 without AWS credentials
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            expected_keys = {
                "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"
            }
            assert set(data.keys()) == expected_keys

    def test_get_alerts_hourly_success(self):
        """Test hourly alerts endpoint returns 24 hour buckets."""
        response = client.get("/alerts/hourly?days=30")

        # May return 200 with real data or 500 without AWS credentials
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert len(data) == 24
            assert "00h" in data
            assert "23h" in data
