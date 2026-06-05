"""Cobertura E2E das rotas BFF /api/* (HTTP contra servidor local)."""

from __future__ import annotations

import pytest
import httpx

pytestmark = pytest.mark.e2e

_LAT, _LON = -23.55, -46.63


@pytest.fixture
def api(e2e_base_url: str) -> httpx.Client:
    with httpx.Client(base_url=e2e_base_url, timeout=15.0) as client:
        yield client


def test_bff_dashboard_summary(api: httpx.Client) -> None:
    response = api.get("/api/dashboard/summary", params={"days": 30})
    assert response.status_code == 200
    payload = response.json()
    kpis = payload.get("kpis") or payload
    assert kpis["total_30d"] > 0
    assert "trend_30_days" in payload or "alerts_by_weekday" in payload
    assert response.headers.get("x-data-source")
    assert "max-age" in response.headers.get("cache-control", "").lower()


@pytest.mark.parametrize(
    "path",
    [
        "/api/alerts/weekly?days=7",
        "/api/alerts/hourly?days=14",
        "/api/alerts/daily?days=30",
        "/api/alerts/heatmap?days=30",
        "/api/alerts/summary?days=30",
    ],
)
def test_bff_alerts_endpoints(api: httpx.Client, path: str) -> None:
    response = api.get(path)
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, (dict, list))
    assert response.headers.get("x-data-source")


def test_bff_weather_current(api: httpx.Client) -> None:
    response = api.get("/api/weather/current", params={"lat": _LAT, "lon": _LON})
    assert response.status_code == 200
    data = response.json()
    assert "temperature" in data
    assert "humidity" in data


def test_bff_risk_forecast(api: httpx.Client) -> None:
    response = api.get("/api/risk/forecast", params={"lat": _LAT, "lon": _LON})
    assert response.status_code == 200
    data = response.json()
    assert "risk_score" in data or "risk_category" in data


def test_bff_storms_recent(api: httpx.Client) -> None:
    response = api.get("/api/storms/recent", params={"hours": 168})
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_bff_storms_detector_status(api: httpx.Client) -> None:
    response = api.get("/api/storms/detector-status")
    assert response.status_code == 200
    data = response.json()
    assert "available" in data or "model_exists" in data


def test_bff_iot_readings_latest(api: httpx.Client) -> None:
    response = api.get("/api/iot/readings/latest", params={"hours": 24})
    assert response.status_code == 200
    data = response.json()
    assert "readings" in data
    assert isinstance(data["readings"], list)


def test_bff_iot_status(api: httpx.Client) -> None:
    response = api.get("/api/iot/status")
    assert response.status_code == 200


def test_bff_nasa_capturas(api: httpx.Client) -> None:
    response = api.get("/api/nasa/capturas", params={"limite": 6})
    assert response.status_code == 200
    data = response.json()
    assert "capturas" in data
    assert "total" in data


def test_bff_ml_agricultural_risk(api: httpx.Client) -> None:
    response = api.get(
        "/api/ml/agricultural-risk",
        params={
            "temperatura": 25,
            "umidade": 60,
            "precipitacao": 0,
            "vento_kmh": 10,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "classe" in data or "risco" in data or "score" in data


def test_bff_map_overlay(api: httpx.Client) -> None:
    response = api.get("/api/map/overlay", params={"bbox": "-25,-50,-20,-40"})
    assert response.status_code == 200
    data = response.json()
    assert "markers" in data or "alerts" in data or isinstance(data, dict)


def test_bff_cv_status(api: httpx.Client) -> None:
    response = api.get("/api/cv/status")
    assert response.status_code == 200


def test_bff_simulate_storm_detection(api: httpx.Client) -> None:
    response = api.post(
        "/api/alerts/simulate-detection",
        json={"confidence": 0.88, "lat": _LAT, "lon": _LON},
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    alert = data.get("alert") or {}
    assert alert.get("confidence") == pytest.approx(0.88, abs=0.01)
