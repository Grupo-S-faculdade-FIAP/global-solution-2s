"""Unit tests for DetectStormUseCase pipeline ordering and idempotency."""

from unittest.mock import MagicMock, patch

import pytest

from app.application.cv.detect_storm import (
    DetectStormUseCase,
    _deterministic_alert_id,
    _exponential_backoff,
)


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def use_case(repo):
    return DetectStormUseCase(repo=repo)


def test_exponential_backoff_sleeps(monkeypatch):
    slept = []

    def fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr("app.application.cv.detect_storm.time.sleep", fake_sleep)
    monkeypatch.setattr("app.application.cv.detect_storm.random.uniform", lambda _a, _b: 0.0)

    _exponential_backoff(0, base_delay=1.0, max_delay=32.0)
    _exponential_backoff(2, base_delay=1.0, max_delay=8.0)

    assert len(slept) == 2
    assert slept[0] == 1.0
    assert slept[1] == 8.0


def test_deterministic_alert_id_stable():
    a = _deterministic_alert_id("bucket-a", "path/img.png")
    b = _deterministic_alert_id("bucket-a", "path/img.png")
    c = _deterministic_alert_id("bucket-b", "path/img.png")
    assert a == b
    assert a != c
    assert a.startswith("storm_")


@patch("app.application.cv.detect_storm._run_yolo_inference")
@patch("app.application.cv.detect_storm._ensure_model")
@patch("app.services.sns_alerts.publish_storm_alert")
@patch("boto3.client")
def test_persist_before_sns(mock_boto, mock_sns, mock_model, mock_yolo, use_case, repo):
    mock_yolo.return_value = [{"class": "storm", "confidence": 0.9}]
    mock_model.return_value = MagicMock()
    repo.save.return_value = {"alert_id": "storm_abc", "s3_key": "img.png"}
    mock_sns.return_value = "msg-123"
    mock_boto.return_value.download_file = MagicMock()

    result = use_case.execute(bucket="bkt", key="img.png")

    repo.save.assert_called_once()
    mock_sns.assert_called_once()
    assert mock_sns.call_args[0][0:2] == ("bkt", "img.png")
    assert result["alert_sent"] is True
    assert result["sns_message_id"] == "msg-123"
    assert result["duplicate"] is False


@patch("app.application.cv.detect_storm._run_yolo_inference")
@patch("app.application.cv.detect_storm._ensure_model")
@patch("app.services.sns_alerts.publish_storm_alert")
@patch("boto3.client")
def test_duplicate_skips_sns(mock_boto, mock_sns, mock_model, mock_yolo, use_case, repo):
    mock_yolo.return_value = [{"class": "storm", "confidence": 0.8}]
    mock_model.return_value = MagicMock()
    repo.save.return_value = {"alert_id": "storm_abc", "_duplicate": True}
    mock_boto.return_value.download_file = MagicMock()

    result = use_case.execute(bucket="bkt", key="img.png")

    mock_sns.assert_not_called()
    assert result["duplicate"] is True
    assert result["sns_message_id"] is None
