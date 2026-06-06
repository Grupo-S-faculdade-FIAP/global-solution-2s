"""Tests for SNS storm alert publishing."""

from __future__ import annotations

import pytest

from app.services import sns_alerts


@pytest.fixture
def sns_settings(monkeypatch):
    monkeypatch.setattr(sns_alerts.settings, "SNS_ENABLED", True)
    monkeypatch.setattr(
        sns_alerts.settings,
        "SNS_TOPIC_ARN",
        "arn:aws:sns:us-east-1:123456789012:rain-alerts",
    )
    monkeypatch.setattr(sns_alerts.settings, "SNS_ALERT_SUBJECT", "Rain Alert — Storm Detected")
    monkeypatch.setattr(sns_alerts.settings, "AWS_REGION", "us-east-1")
    monkeypatch.setattr(sns_alerts, "_put_cloudwatch_metric", lambda *args, **kwargs: None)


def test_sns_is_configured_requires_topic_and_enabled(monkeypatch):
    monkeypatch.setattr(sns_alerts.settings, "SNS_ENABLED", True)
    monkeypatch.setattr(sns_alerts.settings, "SNS_TOPIC_ARN", "")
    assert sns_alerts.sns_is_configured() is False

    monkeypatch.setattr(
        sns_alerts.settings,
        "SNS_TOPIC_ARN",
        "arn:aws:sns:us-east-1:123456789012:rain-alerts",
    )
    assert sns_alerts.sns_is_configured() is True

    monkeypatch.setattr(sns_alerts.settings, "SNS_ENABLED", False)
    assert sns_alerts.sns_is_configured() is False


def test_publish_skips_when_not_configured(monkeypatch):
    monkeypatch.setattr(sns_alerts.settings, "SNS_ENABLED", False)
    result = sns_alerts.publish_storm_alert(
        "bucket",
        "img.jpg",
        [{"class": "storm", "confidence": 0.9}],
    )
    assert result is None


def test_publish_skips_empty_detections(sns_settings):
    assert sns_alerts.publish_storm_alert("bucket", "img.jpg", []) is None


def test_publish_storm_alert_success(sns_settings, monkeypatch):
    captured: dict = {}

    class FakeSNS:
        def publish(self, **kwargs):
            captured.update(kwargs)
            return {"MessageId": "msg-123"}

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )

    detections = [
        {"class": "storm", "confidence": 0.91},
        {"class": "storm", "confidence": 0.82},
    ]
    message_id = sns_alerts.publish_storm_alert("satellite-images-gs2", "screenshots/a.jpg", detections)

    assert message_id == "msg-123"
    assert captured["TopicArn"] == sns_alerts.settings.SNS_TOPIC_ARN
    assert captured["Subject"] == "Rain Alert — Storm Detected"
    assert "s3://satellite-images-gs2/screenshots/a.jpg" in captured["Message"]
    assert "Max confidence: 91.00%" in captured["Message"]
    assert "Detections: 2" in captured["Message"]


def test_publish_storm_alert_handles_client_error(sns_settings, monkeypatch):
    from botocore.exceptions import ClientError

    class FakeSNS:
        def publish(self, **kwargs):
            raise ClientError(
                {"Error": {"Code": "AuthorizationError", "Message": "denied"}},
                "Publish",
            )

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )

    result = sns_alerts.publish_storm_alert(
        "bucket",
        "img.jpg",
        [{"class": "storm", "confidence": 0.5}],
    )
    assert result is None


def test_sns_status_redacts_empty_topic(monkeypatch):
    monkeypatch.setattr(sns_alerts.settings, "SNS_ENABLED", True)
    monkeypatch.setattr(sns_alerts.settings, "SNS_TOPIC_ARN", "")
    status = sns_alerts.sns_status()
    assert status["configured"] is False
    assert status["topic_arn"] is None


def test_subscribe_email_requires_configuration(monkeypatch):
    monkeypatch.setattr(sns_alerts.settings, "SNS_ENABLED", False)
    result = sns_alerts.subscribe_email("test@example.com")
    assert result["success"] is False
    assert result["configured"] is False


def test_subscribe_email_rejects_invalid(sns_settings):
    result = sns_alerts.subscribe_email("not-an-email")
    assert result["success"] is False
    assert "inválido" in result["error"].lower()


def test_subscribe_email_success(sns_settings, monkeypatch):
    captured: dict = {}

    class FakeSNS:
        def subscribe(self, **kwargs):
            captured.update(kwargs)
            return {"SubscriptionArn": "pending confirmation"}

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )

    result = sns_alerts.subscribe_email("Avaliador@FIAP.com")
    assert result["success"] is True
    assert result["pending_confirmation"] is True
    assert result["email"] == "avaliador@fiap.com"
    assert captured["Protocol"] == "email"
    assert captured["Endpoint"] == "avaliador@fiap.com"


def test_publish_simulated_alert_success(sns_settings, monkeypatch):
    captured: dict = {}

    class FakeSNS:
        def publish(self, **kwargs):
            captured.update(kwargs)
            return {"MessageId": "sim-msg-1"}

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )

    message_id = sns_alerts.publish_simulated_alert(-23.55, -46.63, 0.85)
    assert message_id == "sim-msg-1"
    assert "[Simulated]" in captured["Subject"]
    assert "-23.5500" in captured["Message"]
    assert "85.00%" in captured["Message"]


def test_publish_simulated_alert_skips_when_not_configured(monkeypatch):
    monkeypatch.setattr(sns_alerts.settings, "SNS_ENABLED", False)
    assert sns_alerts.publish_simulated_alert(0.0, 0.0, 0.5) is None


def test_subscribe_email_handles_client_error(sns_settings, monkeypatch):
    from botocore.exceptions import ClientError

    class FakeSNS:
        def subscribe(self, **kwargs):
            raise ClientError(
                {"Error": {"Code": "AuthorizationError", "Message": "denied"}},
                "Subscribe",
            )

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )

    result = sns_alerts.subscribe_email("test@example.com")
    assert result["success"] is False
    assert "Falha" in result["error"]


def test_publish_simulated_alert_handles_client_error(sns_settings, monkeypatch):
    from botocore.exceptions import ClientError

    class FakeSNS:
        def publish(self, **kwargs):
            raise ClientError(
                {"Error": {"Code": "AuthorizationError", "Message": "denied"}},
                "Publish",
            )

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )

    assert sns_alerts.publish_simulated_alert(-23.55, -46.63, 0.9) is None


def test_subscribe_email_rejects_when_subscriber_limit_reached(sns_settings, monkeypatch):
    monkeypatch.setattr(sns_alerts.settings, "SNS_MAX_SUBSCRIBERS", 2)

    class FakeSNS:
        def subscribe(self, **kwargs):
            return {"SubscriptionArn": "pending confirmation"}

        def get_paginator(self, operation_name):
            class Paginator:
                def paginate(self, **kwargs):
                    return [
                        {
                            "Subscriptions": [
                                {"Protocol": "email", "Endpoint": "a@b.com", "SubscriptionArn": "pending confirmation"},
                                {"Protocol": "email", "Endpoint": "c@d.com", "SubscriptionArn": "arn:sub:2"},
                            ]
                        }
                    ]

            return Paginator()

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )

    result = sns_alerts.subscribe_email("new@example.com")
    assert result["success"] is False
    assert result.get("subscriber_limit_reached") is True
    assert "20" not in result["error"]  # limit is 2 in test
    assert "2" in result["error"]


def test_subscribe_email_already_subscribed(sns_settings, monkeypatch):
    class FakeSNS:
        def get_paginator(self, operation_name):
            class Paginator:
                def paginate(self, **kwargs):
                    return [
                        {
                            "Subscriptions": [
                                {
                                    "Protocol": "email",
                                    "Endpoint": "user@example.com",
                                    "SubscriptionArn": "pending confirmation",
                                }
                            ]
                        }
                    ]

            return Paginator()

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )

    result = sns_alerts.subscribe_email("user@example.com")
    assert result["success"] is True
    assert result.get("already_subscribed") is True


def test_publish_respects_per_email_daily_limit(sns_settings, monkeypatch, tmp_path):
    from app.services import sns_rate_limit

    store_file = tmp_path / "sns_rate_limits.json"
    monkeypatch.setattr(sns_rate_limit.settings, "SNS_RATE_LIMIT_STORE_PATH", str(store_file))
    monkeypatch.setattr(sns_rate_limit.settings, "SNS_MAX_ALERTS_PER_EMAIL_DAY", 3)
    monkeypatch.setattr(sns_alerts.settings, "SNS_MAX_ALERTS_PER_EMAIL_DAY", 3)

    published_targets: list[str] = []

    class FakeSNS:
        def get_paginator(self, operation_name):
            class Paginator:
                def paginate(self, **kwargs):
                    return [
                        {
                            "Subscriptions": [
                                {
                                    "Protocol": "email",
                                    "Endpoint": "user@example.com",
                                    "SubscriptionArn": "arn:aws:sns:us-east-1:123:sub:user",
                                }
                            ]
                        }
                    ]

            return Paginator()

        def publish(self, **kwargs):
            if "TargetArn" in kwargs:
                published_targets.append(kwargs["TargetArn"])
            return {"MessageId": f"msg-{len(published_targets)}"}

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )

    detections = [{"class": "storm", "confidence": 0.9}]
    for _ in range(3):
        assert sns_alerts.publish_storm_alert("bucket", "img.jpg", detections) is not None

    assert len(published_targets) == 3
    assert sns_alerts.publish_storm_alert("bucket", "img.jpg", detections) is None
    assert len(published_targets) == 3
