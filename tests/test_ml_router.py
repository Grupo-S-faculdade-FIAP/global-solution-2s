"""Tests for ML router endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ml_status():
    response = client.get("/ml/status")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_predict_agricultural_risk_post():
    response = client.post(
        "/ml/predict/agricultural-risk",
        json={
            "temperatura": 32.0,
            "umidade": 90.0,
            "precipitacao": 15.0,
            "vento_kmh": 50.0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["classe"] in ("LOW", "MEDIUM", "HIGH")
    assert "recomendacao" in data
    assert "probabilidades" in data


def test_predict_agricultural_risk_get():
    response = client.get(
        "/ml/predict/agricultural-risk"
        "?temperatura=22&umidade=55&precipitacao=0&vento_kmh=10"
    )
    assert response.status_code == 200
    assert "score" in response.json()


def test_model_info():
    response = client.get("/ml/model/info")
    assert response.status_code == 200
    data = response.json()
    assert data["modelo"] in ("lgbm_regressor", "sklearn_hgb_regressor", "regressor")
    assert "dataset" in data
    assert "features" in data
