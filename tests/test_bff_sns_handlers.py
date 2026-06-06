"""Unit tests for BFF SNS handlers."""

from unittest.mock import patch

import pytest

from app.services import sns_alerts


@patch("dashboard.bff_handlers.use_inprocess_backend", return_value=True)
def test_sns_alerts_status_inprocess(mock_inprocess, sns_settings, monkeypatch):
    from dashboard import bff_handlers as bff

    monkeypatch.setattr(sns_alerts.settings, "SNS_ENABLED", True)
    monkeypatch.setattr(
        sns_alerts.settings,
        "SNS_TOPIC_ARN",
        "arn:aws:sns:us-east-1:123456789012:rain-alerts",
    )

    data, source, status = bff.sns_alerts_status()
    assert status == 200
    assert source == "live"
    assert data["configured"] is True


@patch("dashboard.bff_handlers.backend_get", return_value=(200, {"configured": True, "enabled": True}))
@patch("dashboard.bff_handlers.use_inprocess_backend", return_value=False)
def test_sns_alerts_status_backend_proxy(mock_inprocess, mock_get):
    from dashboard import bff_handlers as bff

    data, source, status = bff.sns_alerts_status()
    assert status == 200
    assert source == "live"
    assert data["configured"] is True
    mock_get.assert_called_once_with("/alerts/sns/status")


@patch("dashboard.bff_handlers.backend_get", return_value=(503, None))
@patch("dashboard.bff_handlers.use_inprocess_backend", return_value=False)
def test_sns_alerts_status_fallback(mock_inprocess, mock_get):
    from dashboard import bff_handlers as bff

    data, source, status = bff.sns_alerts_status()
    assert status == 200
    assert source == "fallback"
    assert data["configured"] is False


def test_sns_subscribe_requires_email():
    from dashboard import bff_handlers as bff

    data, source, status = bff.sns_subscribe({})
    assert status == 400
    assert data["success"] is False
    assert source == "live"


@patch("dashboard.bff_handlers.use_inprocess_backend", return_value=True)
def test_sns_subscribe_inprocess_success(mock_inprocess, sns_settings, monkeypatch):
    from dashboard import bff_handlers as bff

    class FakeSNS:
        def subscribe(self, **kwargs):
            return {"SubscriptionArn": "pending confirmation"}

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )

    data, source, status = bff.sns_subscribe({"email": "avaliador@fiap.com.br"})
    assert status == 200
    assert data["success"] is True
    assert data["pending_confirmation"] is True


@patch("dashboard.bff_handlers.use_inprocess_backend", return_value=True)
def test_sns_subscribe_inprocess_invalid_email(mock_inprocess, sns_settings):
    from dashboard import bff_handlers as bff

    data, source, status = bff.sns_subscribe({"email": "invalid"})
    assert status == 400
    assert data["success"] is False


@patch("dashboard.bff_handlers.backend_post", return_value=(200, {"success": False, "error": "denied"}))
@patch("dashboard.bff_handlers.use_inprocess_backend", return_value=False)
def test_sns_subscribe_backend_failure(mock_inprocess, mock_post):
    from dashboard import bff_handlers as bff

    data, source, status = bff.sns_subscribe({"email": "a@b.com"})
    assert status == 400
    assert data["success"] is False


@patch("dashboard.bff_handlers.backend_post", return_value=(503, "error"))
@patch("dashboard.bff_handlers.use_inprocess_backend", return_value=False)
def test_sns_subscribe_backend_unavailable(mock_inprocess, mock_post):
    from dashboard import bff_handlers as bff

    data, source, status = bff.sns_subscribe({"email": "a@b.com"})
    assert status == 503
    assert data["success"] is False


@patch(
    "dashboard.bff_handlers.backend_post",
    return_value=(
        200,
        {
            "success": True,
            "alert": {"alert_id": "sim_1", "timestamp": "2026-06-06T12:00:00Z"},
            "message": "Alerta simulado registrado",
            "sns_sent": True,
            "sns_message_id": "msg-99",
        },
    ),
)
def test_simulate_storm_detection_includes_sns(mock_post):
    from dashboard import bff_handlers as bff

    data, source, status = bff.simulate_storm_detection({"lat": -23.5, "lon": -46.6})
    assert status == 200
    assert data["sns_sent"] is True
    assert "e-mail SNS enviado" in data["message"]


@pytest.fixture
def sns_settings(monkeypatch):
    monkeypatch.setattr(sns_alerts.settings, "SNS_ENABLED", True)
    monkeypatch.setattr(
        sns_alerts.settings,
        "SNS_TOPIC_ARN",
        "arn:aws:sns:us-east-1:123456789012:rain-alerts",
    )
    monkeypatch.setattr(sns_alerts.settings, "AWS_REGION", "us-east-1")
