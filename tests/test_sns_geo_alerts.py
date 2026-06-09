"""Tests for SNS geo-targeted email alerts."""

from __future__ import annotations

import pytest

from app.services import sns_alerts, sns_geo, sns_subscriber_store


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
    monkeypatch.setattr(sns_alerts.settings, "SNS_ALERT_RADIUS_KM", 200.0)
    monkeypatch.setattr(sns_alerts, "_put_cloudwatch_metric", lambda *args, **kwargs: None)


@pytest.fixture(autouse=True)
def clear_subscriber_store(monkeypatch, tmp_path):
    from app.services import sns_rate_limit, sns_region_cooldown

    store_file = tmp_path / "sns_subscribers.json"
    rate_file = tmp_path / "sns_rate_limits.json"
    cooldown_file = tmp_path / "sns_region_cooldown.json"
    monkeypatch.setattr(
        sns_subscriber_store.settings,
        "SNS_SUBSCRIBER_STORE_PATH",
        str(store_file),
    )
    monkeypatch.setattr(
        sns_rate_limit.settings,
        "SNS_RATE_LIMIT_STORE_PATH",
        str(rate_file),
    )
    monkeypatch.setattr(sns_rate_limit.settings, "DYNAMODB_USE_MOCK", True)
    monkeypatch.setattr(
        sns_region_cooldown.settings,
        "SNS_REGION_COOLDOWN_STORE_PATH",
        str(cooldown_file),
    )
    sns_subscriber_store.reset_store_for_tests()
    yield
    sns_subscriber_store.reset_store_for_tests()


def test_storm_location_from_s3_key_brasil_sudeste():
    coords = sns_geo.storm_location_from_s3_key("screenshots/brasil_sudeste_20260609_1530.jpg")
    assert coords == (-23.55, -46.63)


def test_storm_location_from_s3_key_unknown():
    assert sns_geo.storm_location_from_s3_key("screenshots/a.jpg") is None


def test_is_within_radius():
    sp_lat, sp_lon = -23.55, -46.63
    near_lat, near_lon = -23.60, -46.70
    far_lat, far_lon = -15.0, -47.0
    assert sns_geo.is_within_radius(sp_lat, sp_lon, near_lat, near_lon, 200.0)
    assert not sns_geo.is_within_radius(sp_lat, sp_lon, far_lat, far_lon, 50.0)


def test_subscribe_allows_resubscribe_after_deleted_subscription(sns_settings, monkeypatch):
    """Deleted SNS subscriptions must not block re-subscribe or location save."""
    captured: dict = {}

    class FakeSNS:
        def subscribe(self, **kwargs):
            captured.update(kwargs)
            return {"SubscriptionArn": "pending confirmation"}

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

    result = sns_alerts.subscribe_email(
        "castrocaroline11@gmail.com",
        lat=-23.55,
        lon=-46.63,
    )
    assert result["success"] is True
    assert result.get("already_subscribed") is not True
    assert result.get("pending_confirmation") is True
    assert result.get("location_saved") is True
    assert captured["Endpoint"] == "castrocaroline11@gmail.com"

    stored = sns_subscriber_store.get_subscriber_location("castrocaroline11@gmail.com")
    assert stored is not None
    assert stored["lat"] == -23.55
    assert stored["lon"] == -46.63


def test_subscribe_saves_location_when_pending_confirmation(sns_settings, monkeypatch):
    class FakeSNS:
        def get_paginator(self, operation_name):
            class Paginator:
                def paginate(self, **kwargs):
                    return [
                        {
                            "Subscriptions": [
                                {
                                    "Protocol": "email",
                                    "Endpoint": "pending@example.com",
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

    result = sns_alerts.subscribe_email("pending@example.com", lat=-23.55, lon=-46.63)
    assert result["success"] is True
    assert result.get("already_subscribed") is True
    assert result.get("location_saved") is True

    stored = sns_subscriber_store.get_subscriber_location("pending@example.com")
    assert stored is not None
    assert stored["lat"] == -23.55
    assert stored["lon"] == -46.63


def test_subscribe_saves_location(sns_settings, monkeypatch):
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

    result = sns_alerts.subscribe_email("geo@example.com", lat=-23.55, lon=-46.63)
    assert result["success"] is True
    assert result.get("location_saved") is True

    stored = sns_subscriber_store.get_subscriber_location("geo@example.com")
    assert stored is not None
    assert stored["lat"] == -23.55
    assert stored["lon"] == -46.63


def test_publish_skips_subscriber_outside_radius(sns_settings, monkeypatch):
    sns_subscriber_store.save_subscriber_location("far@example.com", -15.0, -47.0)

    published: list[str] = []

    class FakeSNS:
        def get_paginator(self, operation_name):
            class Paginator:
                def paginate(self, **kwargs):
                    return [
                        {
                            "Subscriptions": [
                                {
                                    "Protocol": "email",
                                    "Endpoint": "far@example.com",
                                    "SubscriptionArn": "arn:aws:sns:us-east-1:123:sub:far",
                                }
                            ]
                        }
                    ]

            return Paginator()

        def publish(self, **kwargs):
            published.append(kwargs.get("TargetArn", ""))
            return {"MessageId": "msg-far"}

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )

    # Storm near SP — subscriber in Brasília area but outside 50km; use small radius
    monkeypatch.setattr(sns_alerts.settings, "SNS_ALERT_RADIUS_KM", 50.0)
    key = "screenshots/brasil_sudeste_20260609_1530.jpg"
    result = sns_alerts.publish_storm_alert(
        "bucket",
        key,
        [{"class": "storm", "confidence": 0.9}],
    )
    assert result is None
    assert published == []


def test_publish_sends_subscriber_inside_radius(sns_settings, monkeypatch):
    sns_subscriber_store.save_subscriber_location("near@example.com", -23.55, -46.63)

    published: list[str] = []

    class FakeSNS:
        def get_paginator(self, operation_name):
            class Paginator:
                def paginate(self, **kwargs):
                    return [
                        {
                            "Subscriptions": [
                                {
                                    "Protocol": "email",
                                    "Endpoint": "near@example.com",
                                    "SubscriptionArn": "arn:aws:sns:us-east-1:123:sub:near",
                                }
                            ]
                        }
                    ]

            return Paginator()

        def publish(self, **kwargs):
            published.append(kwargs.get("TargetArn", ""))
            return {"MessageId": "msg-near"}

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )

    key = "screenshots/brasil_sudeste_20260609_1530.jpg"
    result = sns_alerts.publish_storm_alert(
        "bucket",
        key,
        [{"class": "storm", "confidence": 0.9}],
    )
    assert result == "msg-near"
    assert len(published) == 1


def test_simulated_alert_geo_filter(sns_settings, monkeypatch):
    sns_subscriber_store.save_subscriber_location("near@example.com", -23.55, -46.63)
    sns_subscriber_store.save_subscriber_location("far@example.com", -15.0, -47.0)

    published_emails: list[str] = []

    class FakeSNS:
        def get_paginator(self, operation_name):
            class Paginator:
                def paginate(self, **kwargs):
                    return [
                        {
                            "Subscriptions": [
                                {
                                    "Protocol": "email",
                                    "Endpoint": "near@example.com",
                                    "SubscriptionArn": "arn:sub:near",
                                },
                                {
                                    "Protocol": "email",
                                    "Endpoint": "far@example.com",
                                    "SubscriptionArn": "arn:sub:far",
                                },
                            ]
                        }
                    ]

            return Paginator()

        def publish(self, **kwargs):
            arn = kwargs.get("TargetArn", "")
            if "near" in arn:
                published_emails.append("near")
            elif "far" in arn:
                published_emails.append("far")
            return {"MessageId": f"msg-{len(published_emails)}"}

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )
    monkeypatch.setattr(sns_alerts.settings, "SNS_ALERT_RADIUS_KM", 50.0)

    message_id = sns_alerts.publish_simulated_alert(-23.55, -46.63, 0.85)
    assert message_id is not None
    assert published_emails == ["near"]


def test_legacy_subscriber_without_coords_skipped(sns_settings, monkeypatch):
    published: list[str] = []

    class FakeSNS:
        def get_paginator(self, operation_name):
            class Paginator:
                def paginate(self, **kwargs):
                    return [
                        {
                            "Subscriptions": [
                                {
                                    "Protocol": "email",
                                    "Endpoint": "legacy@example.com",
                                    "SubscriptionArn": "arn:sub:legacy",
                                }
                            ]
                        }
                    ]

            return Paginator()

        def publish(self, **kwargs):
            published.append(kwargs.get("TargetArn", ""))
            return {"MessageId": "msg-legacy"}

    monkeypatch.setattr(
        sns_alerts.boto3,
        "client",
        lambda service, region_name: FakeSNS(),
    )

    result = sns_alerts.publish_simulated_alert(-23.55, -46.63, 0.9)
    assert result is None
    assert published == []
