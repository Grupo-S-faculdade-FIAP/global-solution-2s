"""Tests for DynamoDB repository adapters (mocked boto3)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from app.infrastructure.aws.dynamodb_iot import DynamoDBIoTReadingRepository
from app.infrastructure.aws.dynamodb_storm import DynamoDBStormAlertRepository


def _recent_item(ts: str | None = None) -> dict:
    now = ts or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "alert_type": "storm_detection",
        "timestamp": now,
        "alert_id": "alert_test",
        "s3_key": "img.png",
        "detection_count": 2,
        "bucket": "b",
    }


@patch("app.infrastructure.aws.dynamodb_storm.boto3")
def test_storm_save_puts_item(mock_boto3):
    mock_table = MagicMock()
    mock_boto3.resource.return_value.Table.return_value = mock_table
    repo = DynamoDBStormAlertRepository()

    item = repo.save(
        s3_key="storm.png",
        detection_count=4,
        bucket="gs-bucket",
        confidence=0.88,
    )

    assert item["detection_count"] == 4
    assert item["confidence"] == 0.88
    mock_table.put_item.assert_called_once()


@patch("app.infrastructure.aws.dynamodb_storm.boto3")
def test_storm_save_raises_on_dynamodb_error(mock_boto3):
    mock_table = MagicMock()
    mock_table.put_item.side_effect = ClientError(
        {"Error": {"Code": "500", "Message": "fail"}}, "PutItem"
    )
    mock_boto3.resource.return_value.Table.return_value = mock_table
    repo = DynamoDBStormAlertRepository()

    with pytest.raises(ClientError):
        repo.save(s3_key="x.png", detection_count=1, bucket="b")


@patch("app.infrastructure.aws.dynamodb_storm.boto3")
def test_storm_list_since_hours_scans_paginated(mock_boto3):
    mock_table = MagicMock()
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    mock_table.scan.side_effect = [
        {"Items": [_recent_item(ts)], "LastEvaluatedKey": {"k": "1"}},
        {"Items": [], "LastEvaluatedKey": None},
    ]
    mock_boto3.resource.return_value.Table.return_value = mock_table
    repo = DynamoDBStormAlertRepository()

    items = repo.list_since_hours(24)

    assert len(items) == 1
    assert mock_table.scan.call_count == 2


@patch("app.infrastructure.aws.dynamodb_storm.boto3")
def test_storm_list_since_days(mock_boto3):
    mock_table = MagicMock()
    mock_table.scan.return_value = {"Items": []}
    mock_boto3.resource.return_value.Table.return_value = mock_table
    repo = DynamoDBStormAlertRepository()

    assert repo.list_since_days(3) == []
    repo.ensure_seeded()  # no-op


@patch("app.infrastructure.aws.dynamodb_storm.boto3")
def test_storm_parse_ts_invalid(mock_boto3):
    mock_boto3.resource.return_value.Table.return_value = MagicMock()
    repo = DynamoDBStormAlertRepository()
    assert repo._parse_ts({"timestamp": "bad"}) is None


@patch("app.infrastructure.aws.dynamodb_iot.boto3")
def test_iot_save_puts_item(mock_boto3):
    mock_table = MagicMock()
    mock_boto3.resource.return_value.Table.return_value = mock_table
    repo = DynamoDBIoTReadingRepository()

    item = repo.save(
        device_id="esp32-01",
        cidade="São Paulo",
        temperatura=28.5,
        umidade=72.0,
    )

    assert item["device_id"] == "esp32-01"
    assert item["temperatura"] == 28.5
    mock_table.put_item.assert_called_once()


@patch("app.infrastructure.aws.dynamodb_iot.boto3")
def test_iot_list_since_hours(mock_boto3):
    mock_table = MagicMock()
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    mock_table.scan.return_value = {
        "Items": [{"timestamp": ts, "reading_id": "r1", "temperatura": 25.0}]
    }
    mock_boto3.resource.return_value.Table.return_value = mock_table
    repo = DynamoDBIoTReadingRepository()

    items = repo.list_since_hours(12)

    assert len(items) == 1
    repo.ensure_seeded()


@patch("app.infrastructure.aws.dynamodb_iot.boto3")
def test_iot_scan_raises(mock_boto3):
    mock_table = MagicMock()
    mock_table.scan.side_effect = ClientError(
        {"Error": {"Code": "500", "Message": "fail"}}, "Scan"
    )
    mock_boto3.resource.return_value.Table.return_value = mock_table
    repo = DynamoDBIoTReadingRepository()

    with pytest.raises(ClientError):
        repo.list_since_hours(1)
