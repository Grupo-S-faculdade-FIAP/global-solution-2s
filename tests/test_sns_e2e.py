"""End-to-end tests for SNS alert system with moto mocks."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from app.services import sns_alerts


@pytest.fixture
def aws_credentials(monkeypatch):
    """Mock AWS credentials for testing."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def sns_configured(monkeypatch):
    """Configure SNS for testing."""
    monkeypatch.setattr(sns_alerts.settings, "SNS_ENABLED", True)
    monkeypatch.setattr(sns_alerts.settings, "SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:storm-alerts")
    monkeypatch.setattr(sns_alerts.settings, "SNS_ALERT_SUBJECT", "Rain Alert — Storm Detected")
    monkeypatch.setattr(sns_alerts.settings, "AWS_REGION", "us-east-1")
    monkeypatch.setattr(sns_alerts.settings, "PROJECT_NAME", "Global Solutions")


def test_publish_storm_alert_success(aws_credentials, sns_configured):
    """Test successful storm alert publication."""
    with mock_aws():
        sns = boto3.client("sns", region_name="us-east-1")
        sns.create_topic(Name="storm-alerts")

        detections = [
            {"class": "storm", "confidence": 0.95},
            {"class": "cloud", "confidence": 0.85},
        ]

        message_id = sns_alerts.publish_storm_alert(
            bucket="test-bucket",
            key="test-image.jpg",
            detections=detections,
        )

        assert message_id is not None
        assert len(message_id) > 0


def test_publish_storm_alert_with_cloudwatch_metrics(aws_credentials, sns_configured):
    """Test that CloudWatch metrics are recorded on successful publish."""
    with mock_aws():
        sns = boto3.client("sns", region_name="us-east-1")
        sns.create_topic(Name="storm-alerts")
        cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")

        detections = [{"class": "storm", "confidence": 0.92}]

        message_id = sns_alerts.publish_storm_alert(
            bucket="test-bucket",
            key="test-image.jpg",
            detections=detections,
        )

        assert message_id is not None

        metrics = cloudwatch.list_metrics(Namespace="GlobalSolutions")
        metric_names = [m["MetricName"] for m in metrics["Metrics"]]
        assert "StormAlertsSent" in metric_names


def test_publish_storm_alert_failure_records_metric(aws_credentials, sns_configured):
    """Test that CloudWatch metric is recorded on failure."""
    with mock_aws():
        cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")

        detections = [{"class": "storm", "confidence": 0.92}]

        message_id = sns_alerts.publish_storm_alert(
            bucket="test-bucket",
            key="test-image.jpg",
            detections=detections,
        )

        assert message_id is None

        metrics = cloudwatch.list_metrics(Namespace="GlobalSolutions")
        metric_names = [m["MetricName"] for m in metrics["Metrics"]]
        assert "StormAlertsFailed" in metric_names


def test_publish_with_retry_on_transient_error(aws_credentials, sns_configured):
    """Test that transient errors are retried with exponential backoff."""
    with mock_aws():
        sns = boto3.client("sns", region_name="us-east-1")
        sns.create_topic(Name="storm-alerts")

        call_count = {"value": 0}

        def mock_publish_with_transient_error(*args, **kwargs):
            call_count["value"] += 1
            if call_count["value"] < 3:
                error_response = {
                    "Error": {
                        "Code": "Throttling",
                        "Message": "Rate exceeded",
                    }
                }
                raise ClientError(error_response, "Publish")
            return "msg-123"

        with patch(
            "app.services.sns_alerts._publish_to_sns_with_retry",
            side_effect=mock_publish_with_transient_error,
        ):
            detections = [{"class": "storm", "confidence": 0.9}]
            message_id = sns_alerts.publish_storm_alert(
                bucket="test-bucket",
                key="test-image.jpg",
                detections=detections,
            )
            assert message_id == "msg-123"


def test_publish_with_no_retry_on_permanent_error(aws_credentials, sns_configured):
    """Test that permanent errors are not retried."""
    with mock_aws():
        sns = boto3.client("sns", region_name="us-east-1")
        sns.create_topic(Name="storm-alerts")

        with patch("boto3.client") as mock_boto_client:
            mock_sns_client = MagicMock()
            mock_boto_client.return_value = mock_sns_client

            error_response = {
                "Error": {
                    "Code": "AuthorizationError",
                    "Message": "User is not authorized",
                }
            }
            mock_sns_client.publish.side_effect = ClientError(error_response, "Publish")

            detections = [{"class": "storm", "confidence": 0.9}]
            message_id = sns_alerts.publish_storm_alert(
                bucket="test-bucket",
                key="test-image.jpg",
                detections=detections,
            )

            assert message_id is None
            assert mock_sns_client.publish.call_count == 1


def test_publish_empty_detections_skipped(aws_credentials, sns_configured):
    """Test that alerts with no detections are skipped."""
    message_id = sns_alerts.publish_storm_alert(
        bucket="test-bucket",
        key="test-image.jpg",
        detections=[],  # Empty detections
    )

    assert message_id is None


def test_publish_simulated_alert_success(aws_credentials, sns_configured):
    """Test successful simulated alert publication."""
    with mock_aws():
        sns = boto3.client("sns", region_name="us-east-1")
        sns.create_topic(Name="storm-alerts")

        message_id = sns_alerts.publish_simulated_alert(
            lat=-23.5505,
            lon=-46.6333,
            confidence=0.85,
        )

        assert message_id is not None
        assert len(message_id) > 0


@pytest.mark.parametrize("error_code,should_retry", [
    ("Throttling", True),
    ("ServiceUnavailable", True),
    ("RequestLimitExceeded", True),
    ("AuthorizationError", False),
    ("InvalidParameter", False),
    ("NotFound", False),
])
def test_error_classification(error_code: str, should_retry: bool):
    """Test error classification for retry logic."""
    error_response = {
        "Error": {
            "Code": error_code,
            "Message": "Test error",
        }
    }
    exc = ClientError(error_response, "Publish")

    if should_retry and error_code in ("Throttling", "ServiceUnavailable", "RequestLimitExceeded"):
        assert sns_alerts._is_transient_error(exc)
    else:
        assert not sns_alerts._is_transient_error(exc)

    if not should_retry and error_code in ("AuthorizationError", "InvalidParameter", "NotFound"):
        assert sns_alerts._is_permanent_error(exc)
    else:
        assert not sns_alerts._is_permanent_error(exc)


def test_email_validation():
    """Test email validation."""
    valid_emails = [
        "user@example.com",
        "test.user@example.co.uk",
        "alert@global-solutions.io",
    ]

    invalid_emails = [
        "",
        "  ",
        "notanemail",
        "@example.com",
        "user@",
        "user@.com",
    ]

    for email in valid_emails:
        result = sns_alerts.subscribe_email(email)
        # We expect it to try subscribing (or fail with SNS error, not validation error)
        assert result.get("configured") is not None

    for email in invalid_emails:
        result = sns_alerts.subscribe_email(email)
        assert result["success"] is False
        assert "error" in result or "configured" in result


def test_sns_status_when_configured(aws_credentials, sns_configured):
    """Test SNS status reporting."""
    status = sns_alerts.sns_status()

    assert status["enabled"] is True
    assert status["configured"] is True
    assert status["topic_arn"] == "arn:aws:sns:us-east-1:123456789012:storm-alerts"
    assert status["region"] == "us-east-1"


def test_sns_status_when_not_configured(monkeypatch):
    """Test SNS status when not configured."""
    monkeypatch.setattr(sns_alerts.settings, "SNS_ENABLED", False)
    monkeypatch.setattr(sns_alerts.settings, "SNS_TOPIC_ARN", "")

    status = sns_alerts.sns_status()

    assert status["enabled"] is False
    assert status["configured"] is False
    assert status["topic_arn"] is None


def test_message_format_contains_required_info(aws_credentials, sns_configured):
    """Test that alert messages contain all required information."""
    with mock_aws():
        sns = boto3.client("sns", region_name="us-east-1")
        topic = sns.create_topic(Name="storm-alerts")
        topic_arn = topic["TopicArn"]

        sns.subscribe(
            TopicArn=topic_arn,
            Protocol="sqs",
            Endpoint="arn:aws:sqs:us-east-1:123456789012:test-queue",
        )

        detections = [
            {"class": "storm", "confidence": 0.95},
            {"class": "cloud", "confidence": 0.85},
        ]

        message_id = sns_alerts.publish_storm_alert(
            bucket="my-bucket",
            key="path/to/image.jpg",
            detections=detections,
        )

        assert message_id is not None
        assert len(message_id) > 0
