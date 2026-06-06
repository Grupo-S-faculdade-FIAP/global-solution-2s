"""Tests for app.routers.dashboard_bff — rotas /api/*."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_OK = ({"ok": True}, "demo", 200)
_ERR = ({"error": "unavailable"}, "demo", 503)


@pytest.mark.parametrize(
    "path,mock_target",
    [
        ("/api/alerts/weekly?days=7", "alerts_weekly"),
        ("/api/alerts/hourly?days=14", "alerts_hourly"),
        ("/api/alerts/daily?days=30", "alerts_daily"),
        ("/api/alerts/heatmap?days=30", "alerts_heatmap"),
        ("/api/alerts/summary?days=30", "alerts_summary"),
        ("/api/dashboard/summary?days=30", "dashboard_summary"),
        ("/api/weather/current?lat=-23.5&lon=-46.6", "weather_current"),
        ("/api/risk/forecast?lat=-23.5&lon=-46.6", "risk_forecast"),
        ("/api/storms/recent?hours=12", "storms_recent"),
        ("/api/map/overlay?bbox=-25,-50,-20,-40", "map_overlay"),
    ],
)
def test_bff_map_overlay_serializes_geojson() -> None:
    """Regressão: GeoJSONFeature (Pydantic) deve serializar em /api/map/overlay."""
    with patch(
        "dashboard.bff_handlers.use_inprocess_backend",
        return_value=True,
    ), patch(
        "dashboard.bff_handlers._get_storm_query_service",
    ) as mock_svc:
        from app.models.schemas import GeoJSONFeature, GeoJSONGeometry, GeoJSONProperties

        mock_svc.return_value.map_overlay_features.return_value = [
            GeoJSONFeature(
                properties=GeoJSONProperties(
                    type="storm",
                    intensity=0.82,
                    timestamp="2026-06-06T12:00:00Z",
                ),
                geometry=GeoJSONGeometry(type="Point", coordinates=[-46.63, -23.55]),
            )
        ]
        response = client.get("/api/map/overlay?bbox=-25,-50,-20,-40")

    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 1
    assert data["features"][0]["geometry"]["coordinates"] == [-46.63, -23.55]


def test_bff_get_routes_success(path: str, mock_target: str) -> None:
    with patch(f"app.routers.dashboard_bff.bff.{mock_target}", return_value=_OK) as mocked:
        response = client.get(path)

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert response.headers["X-Data-Source"] == "demo"
    assert response.headers["Cache-Control"] == "max-age=300, public"
    mocked.assert_called_once()


def test_bff_get_routes_error_cache_control() -> None:
    with patch("app.routers.dashboard_bff.bff.alerts_weekly", return_value=_ERR):
        response = client.get("/api/alerts/weekly")

    assert response.status_code == 503
    assert response.headers["Cache-Control"] == "no-store"


def test_api_dashboard_config() -> None:
    payload = ({"demo_mode": True}, "config", 200)
    with patch("app.routers.dashboard_bff.bff.dashboard_config", return_value=payload):
        response = client.get("/api/dashboard/config")

    assert response.status_code == 200
    assert response.json() == {"demo_mode": True}
    assert response.headers["X-Data-Source"] == "config"


def test_api_detector_status() -> None:
    payload = ({"ready": True}, "detector", 200)
    with patch("app.routers.dashboard_bff.bff.detector_status", return_value=payload):
        response = client.get("/api/storms/detector-status")

    assert response.status_code == 200
    assert response.headers["X-Data-Source"] == "detector"


def test_api_ml_agricultural_risk() -> None:
    with patch(
        "app.routers.dashboard_bff.bff.ml_agricultural_risk",
        return_value=({"risk": "LOW"}, "ml", 200),
    ):
        response = client.get(
            "/api/ml/agricultural-risk?temperatura=25&umidade=60&precipitacao=0&vento_kmh=10"
        )

    assert response.status_code == 200
    assert response.json() == {"risk": "LOW"}


def test_api_nasa_capturas() -> None:
    with patch(
        "app.routers.dashboard_bff.bff.nasa_capturas",
        return_value=([{"id": 1}], "nasa", 200),
    ):
        response = client.get("/api/nasa/capturas?limite=5")

    assert response.status_code == 200
    assert response.headers["X-Data-Source"] == "nasa"


def test_api_cv_status() -> None:
    with patch("app.routers.dashboard_bff.bff.cv_status", return_value=({"loaded": True}, "cv", 200)):
        response = client.get("/api/cv/status")

    assert response.status_code == 200
    assert response.json() == {"loaded": True}


@pytest.mark.parametrize(
    "path,mock_target,method,body",
    [
        ("/api/storms/detect", "detect_storm", "post", {"image_url": "s3://x"}),
        ("/api/storms/batch-detect", "batch_detect_storms", "post", {"keys": []}),
        ("/api/alerts/simulate-detection", "simulate_storm_detection", "post", {"lat": -23.5}),
        ("/api/storms/detect-sample", "detect_storm_sample", "post", None),
    ],
)
def test_bff_post_routes(path: str, mock_target: str, method: str, body: dict | None) -> None:
    with patch(
        f"app.routers.dashboard_bff.bff.{mock_target}",
        return_value=({"done": True}, "demo", 200),
    ) as mocked:
        if body is None:
            response = client.post(path)
            mocked.assert_called_once()
        else:
            response = client.post(path, json=body)
            mocked.assert_called_once()

    assert response.status_code == 200
    assert response.json() == {"done": True}


def test_api_simulate_detection_empty_body() -> None:
    with patch(
        "app.routers.dashboard_bff.bff.simulate_storm_detection",
        return_value=({"simulated": True}, "demo", 200),
    ) as mocked:
        response = client.post("/api/alerts/simulate-detection")

    assert response.status_code == 200
    mocked.assert_called_once_with({})
