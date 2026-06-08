"""Tests for dashboard_alerts router."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def sns_enabled(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "SNS_ENABLED", True)
    monkeypatch.setattr(settings, "SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:rain-alerts")
    monkeypatch.setattr(settings, "AWS_REGION", "us-east-1")


def test_alerts_status_endpoint(sns_enabled):
    with patch("app.routers.dashboard_alerts.validate_sns_setup", return_value=(False, ["No DLQ"])):
        with patch("app.routers.dashboard_alerts.get_topic_arn_from_env", return_value="arn:aws:sns:us-east-1:1:t"):
            with patch("app.container.get_sns_dlq_manager") as mock_factory:
                mock_factory.return_value.get_dlq_url_from_topic.return_value = None
                response = client.get("/alerts/status")

    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert data["configured"] is True
    assert data["valid"] is False
    assert data["dlq_available"] is False


def test_alerts_history_placeholder():
    response = client.get("/alerts/history?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert isinstance(data["alerts"], list)


def test_alerts_test_not_configured(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "SNS_ENABLED", False)
    monkeypatch.setattr(settings, "SNS_TOPIC_ARN", "")
    response = client.post("/alerts/test", json={"confidence": 0.85})
    assert response.status_code == 400


def test_alerts_test_invalid_confidence(sns_enabled):
    response = client.post("/alerts/test", json={"confidence": 2.0})
    assert response.status_code == 422


def test_alerts_test_success(sns_enabled):
    with patch("app.routers.dashboard_alerts.sns_alerts.publish_simulated_alert", return_value="msg-1"):
        response = client.post("/alerts/test", json={"confidence": 0.85})
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["message_id"] == "msg-1"


def test_alerts_dlq_not_configured(monkeypatch):
    with patch("app.routers.dashboard_alerts.get_topic_arn_from_env", return_value=None):
        response = client.get("/alerts/dlq")
    assert response.status_code == 400


def test_alerts_metrics_endpoint(sns_enabled):
    mock_cw = MagicMock()
    mock_cw.list_metrics.return_value = {"Metrics": [{"MetricName": "StormAlertsSent"}]}
    mock_cw.get_metric_statistics.return_value = {"Datapoints": [{"Sum": 1.0}]}

    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "boto3":
            mod = MagicMock()
            mod.client.return_value = mock_cw
            return mod
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        response = client.get("/alerts/metrics")

    assert response.status_code == 200
    assert response.json()["namespace"] == "GlobalSolutions"
