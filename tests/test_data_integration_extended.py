"""Extended tests for data_integration router (mocked dependencies)."""

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from weather_fixtures import SAMPLE_WEATHER

client = TestClient(app)


@patch(
    "app.routers.data_integration.alert_analytics_service.weekly_alerts",
    return_value={
        "Segunda": 1, "Terça": 2, "Quarta": 0, "Quinta": 3,
        "Sexta": 1, "Sábado": 0, "Domingo": 2,
    },
)
def test_alerts_weekly_mocked(_mock):
    response = client.get("/alerts/weekly?days=30")
    assert response.status_code == 200
    assert response.json()["Segunda"] == 1


@patch(
    "app.routers.data_integration.alert_analytics_service.hourly_alerts",
    return_value={f"{h:02d}h": h for h in range(24)},
)
def test_alerts_hourly_mocked(_mock):
    response = client.get("/alerts/hourly?days=7")
    assert response.status_code == 200
    assert len(response.json()) == 24


@patch(
    "app.routers.data_integration.alert_analytics_service.daily_alerts",
    return_value={"2026-06-01": 3, "2026-06-02": 1},
)
def test_alerts_daily(_mock):
    response = client.get("/alerts/daily?days=30")
    assert response.status_code == 200
    assert "2026-06-01" in response.json()


@patch(
    "app.routers.data_integration.alert_analytics_service.heatmap_alerts",
    return_value=[{"weekday": "Monday", "hour": 10, "count": 2}],
)
def test_alerts_heatmap(_mock):
    response = client.get("/alerts/heatmap?days=30")
    assert response.status_code == 200
    assert response.json()[0]["count"] == 2


@patch(
    "app.routers.data_integration.alert_analytics_service.summary",
    return_value={"total": 10, "avg_per_day": 1.2},
)
def test_alerts_summary(_mock):
    response = client.get("/alerts/summary?days=30")
    assert response.status_code == 200
    assert response.json()["total"] == 10


@patch(
    "app.routers.data_integration.alert_analytics_service.dashboard_summary",
    return_value={"kpis": {"total": 5}, "heatmap": []},
)
def test_dashboard_summary(_mock):
    response = client.get("/dashboard/summary?days=30")
    assert response.status_code == 200
    assert "kpis" in response.json()


@patch(
    "app.routers.data_integration._get_risk_service",
)
@patch(
    "app.routers.data_integration.weather_service.get_current",
    return_value=SAMPLE_WEATHER,
)
def test_risk_forecast_includes_detalhes(_mock_weather, mock_risk_svc):
    from app.services.risk_assessment import RiskScore

    mock_risk_svc.return_value.calculate_risk.return_value = RiskScore(
        score=0.42,
        category="MEDIUM",
        recommendation="test",
        timestamp="2026-06-05T12:00:00Z",
        detalhes={
            "components": {"clima": 0.3, "cv": 0.1, "ml_agricola": 0.5},
            "pesos": {"clima": 0.5, "cv": 0.0, "ml_agricola": 0.5},
        },
    )
    response = client.get("/risk/forecast?lat=-22.89&lon=-43.18")
    assert response.status_code == 200
    data = response.json()
    assert data["detalhes"]["components"]["ml_agricola"] == 0.5


@patch(
    "app.routers.data_integration.add_alert_from_coords",
    return_value={"alert_id": "sim_1", "confidence": 0.85},
)
def test_simulate_alert(_mock):
    response = client.post(
        "/alerts/simulate",
        json={"lat": -23.55, "lon": -46.63, "confidence": 0.85},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_alerts_storage_status():
    response = client.get("/alerts/status")
    assert response.status_code == 200
    assert response.json()["store"] == "dynamodb"


@patch(
    "app.routers.data_integration.weather_service.get_current",
    side_effect=Exception("API down"),
)
def test_weather_endpoint_500_on_service_error(_mock):
    response = client.get("/weather/current?lat=-22.89&lon=-43.18")
    assert response.status_code == 500
    assert "API down" in response.json()["detail"]


def test_map_overlay_invalid_bbox_order():
    response = client.get("/map/overlay?bbox=-20,-40,-25,-50")
    assert response.status_code == 400


@patch(
    "app.routers.data_integration.storm_alerts_service.map_overlay_features",
    side_effect=Exception("db error"),
)
def test_map_overlay_500(_mock):
    response = client.get("/map/overlay?bbox=-25,-50,-20,-40")
    assert response.status_code == 500


@patch(
    "app.routers.data_integration.storm_alerts_service.recent_detections",
    side_effect=Exception("scan failed"),
)
def test_storms_recent_500(_mock):
    response = client.get("/storms/recent?hours=24")
    assert response.status_code == 500
