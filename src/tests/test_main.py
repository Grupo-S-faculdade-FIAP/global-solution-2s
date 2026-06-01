from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_cv_status():
    response = client.get("/cv/status")
    assert response.status_code == 200


def test_ml_status():
    response = client.get("/ml/status")
    assert response.status_code == 200


def test_iot_status():
    response = client.get("/iot/status")
    assert response.status_code == 200


def test_dashboard_status():
    response = client.get("/dashboard/status")
    assert response.status_code == 200
