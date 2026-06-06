"""Tests for SNS DLQ manager."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws

from app.core import sns_config
from app.infrastructure.aws.sns_dlq import SNSDLQManager


@pytest.fixture
def aws_credentials(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def topic_with_dlq(aws_credentials):
    with mock_aws():
        sns = boto3.client("sns", region_name="us-east-1")
        sqs = boto3.client("sqs", region_name="us-east-1")
        topic_arn = sns.create_topic(Name="storm-alerts")["TopicArn"]
        dlq_url = sqs.create_queue(QueueName="storm-alerts-dlq")["QueueUrl"]
        dlq_arn = sns_config._queue_url_to_arn(dlq_url)
        yield topic_arn, dlq_url, dlq_arn


def test_arn_to_sqs_url():
    manager = SNSDLQManager()
    url = manager._arn_to_sqs_url("arn:aws:sqs:us-east-1:123456789012:storm-alerts-dlq")
    assert url == "https://queue.amazonaws.com/123456789012/storm-alerts-dlq"


def test_arn_to_sqs_url_invalid():
    with pytest.raises(ValueError, match="Invalid SQS ARN"):
        SNSDLQManager()._arn_to_sqs_url("arn:aws:s3:us-east-1:123:bucket")


def test_get_dlq_url_from_topic(topic_with_dlq):
    topic_arn, dlq_url, dlq_arn = topic_with_dlq
    manager = SNSDLQManager()
    manager.sns_client.get_topic_attributes = MagicMock(
        return_value={
            "Attributes": {
                "RedrivePolicy": json.dumps({"deadLetterTargetArn": dlq_arn}),
            }
        }
    )
    resolved = manager.get_dlq_url_from_topic(topic_arn)
    assert resolved == manager._arn_to_sqs_url(dlq_arn)


def test_get_dlq_url_missing_redrive_policy(aws_credentials):
    with mock_aws():
        sns = boto3.client("sns", region_name="us-east-1")
        topic_arn = sns.create_topic(Name="no-dlq")["TopicArn"]
        manager = SNSDLQManager()
        assert manager.get_dlq_url_from_topic(topic_arn) is None


def test_read_messages_empty(topic_with_dlq):
    _, dlq_url, _ = topic_with_dlq
    manager = SNSDLQManager()
    manager.set_dlq_url(dlq_url)
    messages = manager.read_messages(max_messages=5)
    assert messages == []


def test_get_dlq_stats_without_url():
    manager = SNSDLQManager()
    assert manager.get_dlq_stats() == {}


def test_get_dlq_stats_with_queue(topic_with_dlq):
    _, dlq_url, _ = topic_with_dlq
    manager = SNSDLQManager()
    manager.set_dlq_url(dlq_url)
    stats = manager.get_dlq_stats()
    assert stats["MessageCount"] == 0
