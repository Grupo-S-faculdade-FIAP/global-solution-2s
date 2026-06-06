"""Tests for SNS configuration helpers."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from app.core import sns_config


@pytest.fixture
def aws_credentials(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


def test_validate_sns_setup_disabled(monkeypatch):
    monkeypatch.setattr(sns_config.settings, "SNS_ENABLED", False)
    valid, issues = sns_config.validate_sns_setup()
    assert valid is False
    assert "disabled" in issues[0].lower()


def test_validate_sns_setup_missing_arn(monkeypatch):
    monkeypatch.setattr(sns_config.settings, "SNS_ENABLED", True)
    monkeypatch.setattr(sns_config.settings, "SNS_TOPIC_ARN", "")
    valid, issues = sns_config.validate_sns_setup()
    assert valid is False
    assert "SNS_TOPIC_ARN" in issues[0]


def test_validate_sns_setup_topic_without_dlq(aws_credentials, monkeypatch):
    with mock_aws():
        monkeypatch.setattr(sns_config.settings, "SNS_ENABLED", True)
        monkeypatch.setattr(sns_config.settings, "AWS_REGION", "us-east-1")
        sns = boto3.client("sns", region_name="us-east-1")
        topic_arn = sns.create_topic(Name="storm-alerts")["TopicArn"]
        monkeypatch.setattr(sns_config.settings, "SNS_TOPIC_ARN", topic_arn)

        valid, issues = sns_config.validate_sns_setup()
        assert valid is False
        assert any("RedrivePolicy" in issue for issue in issues)


def test_validate_sns_setup_with_dlq(aws_credentials, monkeypatch):
    monkeypatch.setattr(sns_config.settings, "SNS_ENABLED", True)
    monkeypatch.setattr(sns_config.settings, "AWS_REGION", "us-east-1")
    monkeypatch.setattr(
        sns_config.settings,
        "SNS_TOPIC_ARN",
        "arn:aws:sns:us-east-1:123456789012:storm-alerts",
    )

    dlq_arn = "arn:aws:sqs:us-east-1:123456789012:storm-alerts-dlq"
    mock_sns = MagicMock()
    mock_sns.get_topic_attributes.return_value = {
        "Attributes": {
            "RedrivePolicy": json.dumps({"deadLetterTargetArn": dlq_arn}),
        }
    }

    with patch("app.core.sns_config.boto3.client", return_value=mock_sns):
        valid, issues = sns_config.validate_sns_setup()

    assert valid is True
    assert issues == []


def test_create_sns_topic_success(aws_credentials):
    with mock_aws():
        arn = sns_config.create_sns_topic("storm-alerts")
        assert arn is not None
        assert arn.endswith(":storm-alerts")


def test_create_sqs_dlq_success(aws_credentials):
    with mock_aws():
        url = sns_config.create_sqs_dlq("storm-alerts-dlq")
        assert url is not None
        assert "storm-alerts-dlq" in url


def test_bind_dlq_to_topic(aws_credentials):
    with mock_aws():
        sns = boto3.client("sns", region_name="us-east-1")
        sqs = boto3.client("sqs", region_name="us-east-1")
        topic_arn = sns.create_topic(Name="alerts")["TopicArn"]
        dlq_url = sqs.create_queue(QueueName="alerts-dlq")["QueueUrl"]
        dlq_arn = sns_config._queue_url_to_arn(dlq_url)

        assert sns_config.bind_dlq_to_topic(topic_arn, dlq_arn) is True


def test_setup_sns_dlq_end_to_end(aws_credentials):
    with mock_aws():
        topic_arn, dlq_url = sns_config.setup_sns_dlq("gs2-alerts", "gs2-alerts-dlq")
        assert topic_arn is not None
        assert dlq_url is not None


def test_get_topic_arn_from_env(monkeypatch):
    monkeypatch.setattr(sns_config.settings, "SNS_TOPIC_ARN", "  arn:aws:sns:us-east-1:1:topic  ")
    assert sns_config.get_topic_arn_from_env() == "arn:aws:sns:us-east-1:1:topic"
    monkeypatch.setattr(sns_config.settings, "SNS_TOPIC_ARN", "")
    assert sns_config.get_topic_arn_from_env() is None


def test_validate_topic_arn_not_found(aws_credentials):
    with mock_aws():
        assert sns_config.validate_topic_arn("arn:aws:sns:us-east-1:123456789012:missing") is False


def test_queue_url_to_arn_invalid():
    assert sns_config._queue_url_to_arn("https://invalid") is None


def test_validate_sns_setup_topic_not_found(monkeypatch):
    monkeypatch.setattr(sns_config.settings, "SNS_ENABLED", True)
    monkeypatch.setattr(sns_config.settings, "SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:1:nope")
    monkeypatch.setattr(sns_config.settings, "AWS_REGION", "us-east-1")

    with mock_aws():
        valid, issues = sns_config.validate_sns_setup()
        assert valid is False
        assert any("not found" in issue.lower() for issue in issues)


def test_create_sns_topic_client_error(monkeypatch):
    mock_client = MagicMock()
    mock_client.create_topic.side_effect = ClientError(
        {"Error": {"Code": "TopicLimitExceeded", "Message": "limit"}},
        "CreateTopic",
    )
    with patch("app.core.sns_config.boto3.client", return_value=mock_client):
        assert sns_config.create_sns_topic("storm-alerts") is None
