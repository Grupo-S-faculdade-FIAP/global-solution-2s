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
    assert captured.get("ReturnSubscriptionArn") is True


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

        def get_subscription_attributes(self, **kwargs):
            return {"Attributes": {"PendingConfirmation": "false"}}

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


def test_list_email_subscriptions_ignores_deleted(sns_settings, monkeypatch, tmp_path):
    from app.services import sns_subscriber_store

    monkeypatch.setattr(
        sns_subscriber_store.settings,
        "SNS_SUBSCRIBER_STORE_PATH",
        str(tmp_path / "sns_subscribers.json"),
    )
    sns_subscriber_store.reset_store_for_tests()

    class FakeSNS:
        def get_paginator(self, operation_name):
            class Paginator:
                def paginate(self, **kwargs):
                    return [
                        {
                            "Subscriptions": [
                                {
                                    "Protocol": "email",
                                    "Endpoint": "deleted@example.com",
                                    "SubscriptionArn": "Deleted",
                                },
                                {
                                    "Protocol": "email",
                                    "Endpoint": "active@example.com",
                                    "SubscriptionArn": "arn:aws:sns:us-east-1:123:sub:active",
                                },
                            ]
                        }
                    ]

            return Paginator()

        def get_subscription_attributes(self, **kwargs):
            return {"Attributes": {"PendingConfirmation": "false"}}

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )
    monkeypatch.setattr(sns_alerts, "list_subscribers_with_subscription_arn", lambda: [])

    subs = sns_alerts._list_email_subscriptions(sns_alerts.settings.SNS_TOPIC_ARN)
    emails = {sub["email"] for sub in subs}
    assert emails == {"active@example.com"}
    assert sns_alerts._email_is_subscribed(sns_alerts.settings.SNS_TOPIC_ARN, "deleted@example.com") is False
    assert sns_alerts._email_is_subscribed(sns_alerts.settings.SNS_TOPIC_ARN, "active@example.com") is True


def test_subscribe_email_deleted_only_calls_subscribe_with_return_arn(sns_settings, monkeypatch):
    """Deleted-only list entry must still call subscribe with ReturnSubscriptionArn."""
    captured: dict = {}
    pending_arn = "arn:aws:sns:us-east-1:123456789012:rain-alerts:pending-sub"

    class FakeSNS:
        def subscribe(self, **kwargs):
            captured.update(kwargs)
            return {"SubscriptionArn": pending_arn}

        def get_subscription_attributes(self, **kwargs):
            return {"Attributes": {"PendingConfirmation": "true"}}

        def get_paginator(self, operation_name):
            class Paginator:
                def paginate(self, **kwargs):
                    return [
                        {
                            "Subscriptions": [
                                {
                                    "Protocol": "email",
                                    "Endpoint": "deleted@example.com",
                                    "SubscriptionArn": "Deleted",
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

    result = sns_alerts.subscribe_email("deleted@example.com")
    assert result["success"] is True
    assert result.get("already_subscribed") is not True
    assert result["pending_confirmation"] is True
    assert result["subscription_arn"] == pending_arn
    assert captured.get("ReturnSubscriptionArn") is True
    assert captured["Endpoint"] == "deleted@example.com"


def test_subscribe_email_warns_on_deleted_tombstone(sns_settings, monkeypatch):
    """Deleted-only tombstone must return Portuguese warning with alias hint."""
    captured: dict = {}
    pending_arn = "arn:aws:sns:us-east-1:123456789012:rain-alerts:pending-sub"

    class FakeSNS:
        def subscribe(self, **kwargs):
            captured.update(kwargs)
            return {"SubscriptionArn": pending_arn}

        def get_subscription_attributes(self, **kwargs):
            return {"Attributes": {"PendingConfirmation": "true"}}

        def get_paginator(self, operation_name):
            class Paginator:
                def paginate(self, **kwargs):
                    return [
                        {
                            "Subscriptions": [
                                {
                                    "Protocol": "email",
                                    "Endpoint": "castrocaroline11@gmail.com",
                                    "SubscriptionArn": "Deleted",
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

    result = sns_alerts.subscribe_email("castrocaroline11@gmail.com")
    assert result["success"] is True
    assert "warning" in result
    assert "tombstone" in result["warning"].lower()
    assert "castrocaroline11+gs2@gmail.com" in result["warning"]
    assert "48" in result["warning"]


def test_subscribe_email_no_warning_without_tombstone(sns_settings, monkeypatch):
    class FakeSNS:
        def subscribe(self, **kwargs):
            return {"SubscriptionArn": "pending confirmation"}

        def get_paginator(self, operation_name):
            class Paginator:
                def paginate(self, **kwargs):
                    return [{"Subscriptions": []}]

            return Paginator()

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )

    result = sns_alerts.subscribe_email("fresh@example.com")
    assert result["success"] is True
    assert "warning" not in result


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

        def get_subscription_attributes(self, **kwargs):
            return {"Attributes": {"PendingConfirmation": "false"}}

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


def test_extract_region_from_s3_key():
    from app.services.sns_region_cooldown import extract_region_from_s3_key

    assert extract_region_from_s3_key("screenshots/brasil_sudeste_20260609_1530.jpg") == "brasil_sudeste"
    assert extract_region_from_s3_key("nasa_brasil_20260604_1534.png") == "nasa_brasil"
    assert extract_region_from_s3_key("screenshots/a.jpg") is None


def test_region_cooldown_blocks_second_alert(sns_settings, monkeypatch, tmp_path):
    from app.services import sns_region_cooldown

    store_file = tmp_path / "sns_region_cooldown.json"
    monkeypatch.setattr(
        sns_region_cooldown.settings,
        "SNS_REGION_COOLDOWN_STORE_PATH",
        str(store_file),
    )
    monkeypatch.setattr(sns_region_cooldown.settings, "SNS_REGION_COOLDOWN_MINUTES", 60)

    metrics: list[str] = []
    monkeypatch.setattr(
        sns_alerts,
        "_put_cloudwatch_metric",
        lambda name, *args, **kwargs: metrics.append(name),
    )

    class FakeSNS:
        def publish(self, **kwargs):
            return {"MessageId": "msg-cooldown-1"}

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )

    detections = [{"class": "storm", "confidence": 0.9}]
    key = "screenshots/brasil_sudeste_20260609_1530.jpg"

    assert sns_alerts.publish_storm_alert("bucket", key, detections) == "msg-cooldown-1"
    assert sns_alerts.publish_storm_alert("bucket", key, detections) is None
    assert metrics.count("AlertsSkipped") == 1


def test_dynamodb_rate_limit_increment(sns_settings, monkeypatch):
    from app.services import sns_rate_limit

    monkeypatch.setattr(sns_rate_limit, "use_mock_store", lambda: False)

    stored: dict = {}

    class FakeTable:
        def get_item(self, Key):
            item = stored.get(Key["pk"])
            return {"Item": item} if item else {}

        def update_item(self, Key, UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues, ReturnValues):
            pk = Key["pk"]
            item = stored.setdefault(pk, {"pk": pk, "alert_count": 0})
            item["alert_count"] = int(item.get("alert_count", 0)) + int(
                ExpressionAttributeValues[":inc"]
            )
            item["ttl"] = ExpressionAttributeValues[":ttl"]
            return {"Attributes": {"alert_count": item["alert_count"]}}

    class FakeDynamo:
        def Table(self, name):
            return FakeTable()

    monkeypatch.setattr(sns_rate_limit.boto3, "resource", lambda service, region_name: FakeDynamo())
    monkeypatch.setattr(sns_rate_limit.settings, "SNS_MAX_ALERTS_PER_EMAIL_DAY", 3)

    assert sns_rate_limit.get_daily_alert_count("user@example.com") == 0
    assert sns_rate_limit.can_send_alert("user@example.com") is True
    assert sns_rate_limit.record_alert_sent("user@example.com") == 1
    assert sns_rate_limit.get_daily_alert_count("user@example.com") == 1
    assert sns_rate_limit.record_alert_sent("user@example.com") == 2
    assert sns_rate_limit.can_send_alert("user@example.com") is True
    assert sns_rate_limit.record_alert_sent("user@example.com") == 3
    assert sns_rate_limit.can_send_alert("user@example.com") is False


def test_tombstone_merge_skips_stale_dynamodb_arn(sns_settings, monkeypatch, tmp_path):
    from app.services import sns_subscriber_store

    monkeypatch.setattr(
        sns_subscriber_store.settings,
        "SNS_SUBSCRIBER_STORE_PATH",
        str(tmp_path / "sns_subscribers.json"),
    )
    sns_subscriber_store.reset_store_for_tests()

    stale_arn = "arn:aws:sns:us-east-1:123456789012:rain-alerts:stale-sub"
    sns_subscriber_store.save_subscriber_location(
        "stale@example.com",
        lat=-23.55,
        lon=-46.63,
        subscription_arn=stale_arn,
    )

    class FakeSNS:
        def get_paginator(self, operation_name):
            class Paginator:
                def paginate(self, **kwargs):
                    return [
                        {
                            "Subscriptions": [
                                {
                                    "Protocol": "email",
                                    "Endpoint": "stale@example.com",
                                    "SubscriptionArn": "Deleted",
                                }
                            ]
                        }
                    ]

            return Paginator()

        def get_subscription_attributes(self, **kwargs):
            from botocore.exceptions import ClientError

            raise ClientError(
                {"Error": {"Code": "NotFound", "Message": "Subscription does not exist"}},
                "GetSubscriptionAttributes",
            )

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )

    subs = sns_alerts._list_email_subscriptions(sns_alerts.settings.SNS_TOPIC_ARN)
    assert subs == []

    record = sns_subscriber_store.get_subscriber_record("stale@example.com")
    assert record is not None
    assert "subscription_arn" not in record
    assert record["lat"] == pytest.approx(-23.55)


def test_subscription_arn_publishable_ignores_false_auth_when_not_pending(
    sns_settings, monkeypatch,
):
    """Tombstone ARNs may show PendingConfirmation=false and ConfirmationWasAuthenticated=false."""
    stale_arn = "arn:aws:sns:us-east-1:123456789012:rain-alerts:tombstone-sub"

    class FakeSNS:
        def get_subscription_attributes(self, **kwargs):
            return {
                "Attributes": {
                    "PendingConfirmation": "false",
                    "ConfirmationWasAuthenticated": "false",
                    "SubscriptionArn": stale_arn,
                }
            }

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )

    assert sns_alerts._subscription_arn_is_publishable(
        FakeSNS(),
        stale_arn,
        email="tombstone@example.com",
        clear_on_stale=False,
    )


def test_tombstone_merge_includes_false_auth_confirmed_arn(sns_settings, monkeypatch, tmp_path):
    from app.services import sns_subscriber_store

    monkeypatch.setattr(
        sns_subscriber_store.settings,
        "SNS_SUBSCRIBER_STORE_PATH",
        str(tmp_path / "sns_subscribers.json"),
    )
    sns_subscriber_store.reset_store_for_tests()

    tombstone_arn = "arn:aws:sns:us-east-1:123456789012:rain-alerts:tombstone-sub"
    sns_subscriber_store.save_subscriber_location(
        "tombstone@example.com",
        lat=-23.55,
        lon=-46.63,
        subscription_arn=tombstone_arn,
    )

    class FakeSNS:
        def get_paginator(self, operation_name):
            class Paginator:
                def paginate(self, **kwargs):
                    return [
                        {
                            "Subscriptions": [
                                {
                                    "Protocol": "email",
                                    "Endpoint": "tombstone@example.com",
                                    "SubscriptionArn": "Deleted",
                                }
                            ]
                        }
                    ]

            return Paginator()

        def get_subscription_attributes(self, **kwargs):
            return {
                "Attributes": {
                    "PendingConfirmation": "false",
                    "ConfirmationWasAuthenticated": "false",
                    "SubscriptionArn": tombstone_arn,
                }
            }

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )

    subs = sns_alerts._list_email_subscriptions(sns_alerts.settings.SNS_TOPIC_ARN)
    assert len(subs) == 1
    assert subs[0]["email"] == "tombstone@example.com"
    assert subs[0]["confirmed"] is True
    assert subs[0]["subscription_arn"] == tombstone_arn


def test_publish_clears_stale_arn_on_invalid_parameter(sns_settings, monkeypatch, tmp_path):
    from app.services import sns_subscriber_store

    monkeypatch.setattr(
        sns_subscriber_store.settings,
        "SNS_SUBSCRIBER_STORE_PATH",
        str(tmp_path / "sns_subscribers.json"),
    )
    sns_subscriber_store.reset_store_for_tests()

    stale_arn = "arn:aws:sns:us-east-1:123456789012:rain-alerts:invalid-sub"
    sns_subscriber_store.save_subscriber_location(
        "invalid@example.com",
        lat=-23.55,
        lon=-46.63,
        subscription_arn=stale_arn,
    )

    new_arn = "arn:aws:sns:us-east-1:123456789012:rain-alerts:recovered-sub"
    subscribe_calls: list[dict] = []

    class FakeSNS:
        def get_paginator(self, operation_name):
            class Paginator:
                def paginate(self, **kwargs):
                    return [
                        {
                            "Subscriptions": [
                                {
                                    "Protocol": "email",
                                    "Endpoint": "invalid@example.com",
                                    "SubscriptionArn": stale_arn,
                                }
                            ]
                        }
                    ]

            return Paginator()

        def get_subscription_attributes(self, **kwargs):
            return {
                "Attributes": {
                    "PendingConfirmation": "false",
                    "ConfirmationWasAuthenticated": "false",
                    "SubscriptionArn": stale_arn,
                }
            }

        def publish(self, **kwargs):
            from botocore.exceptions import ClientError

            raise ClientError(
                {
                    "Error": {
                        "Code": "InvalidParameter",
                        "Message": f"TargetArn {kwargs['TargetArn']} is not valid to publish to",
                    }
                },
                "Publish",
            )

        def subscribe(self, **kwargs):
            subscribe_calls.append(kwargs)
            return {"SubscriptionArn": new_arn}

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )

    result = sns_alerts.publish_simulated_alert(-23.55, -46.63, 0.85)
    assert result is None
    assert len(subscribe_calls) == 1
    assert subscribe_calls[0]["ReturnSubscriptionArn"] is True
    assert subscribe_calls[0]["Endpoint"] == "invalid@example.com"

    record = sns_subscriber_store.get_subscriber_record("invalid@example.com")
    assert record is not None
    assert record["subscription_arn"] == new_arn
    assert record["lat"] == pytest.approx(-23.55)


def test_subscribe_persists_pending_arn(sns_settings, monkeypatch, tmp_path):
    from app.services import sns_subscriber_store

    monkeypatch.setattr(
        sns_subscriber_store.settings,
        "SNS_SUBSCRIBER_STORE_PATH",
        str(tmp_path / "sns_subscribers.json"),
    )
    sns_subscriber_store.reset_store_for_tests()

    pending_arn = "arn:aws:sns:us-east-1:123456789012:rain-alerts:pending-sub"

    class FakeSNS:
        def subscribe(self, **kwargs):
            return {"SubscriptionArn": pending_arn}

        def get_subscription_attributes(self, **kwargs):
            return {"Attributes": {"PendingConfirmation": "true"}}

        def get_paginator(self, operation_name):
            class Paginator:
                def paginate(self, **kwargs):
                    return [{"Subscriptions": []}]

            return Paginator()

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )

    result = sns_alerts.subscribe_email("pending-arn@example.com", lat=-23.55, lon=-46.63)
    assert result["success"] is True
    assert result["subscription_arn"] == pending_arn
    assert result["pending_confirmation"] is True

    record = sns_subscriber_store.get_subscriber_record("pending-arn@example.com")
    assert record is not None
    assert record["subscription_arn"] == pending_arn
    assert record["lat"] == pytest.approx(-23.55)
