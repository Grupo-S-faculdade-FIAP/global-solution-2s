"""Tests for JsonStormAlertRepository."""

from datetime import datetime, timedelta, timezone

import pytest

from app.infrastructure.persistence import json_storm_store as store


@pytest.fixture
def repo(tmp_path, monkeypatch):
    path = tmp_path / "storm_alerts.json"
    monkeypatch.setattr(store.settings, "DYNAMODB_MOCK_STORE_PATH", str(path))
    return store.JsonStormAlertRepository()


def test_ensure_seeded_creates_demo_data(repo):
    repo.ensure_seeded()
    items = store._load_all()
    assert len(items) >= 6
    assert items[0]["alert_type"] == "storm_detection"


def test_save_appends_item(repo):
    item = repo.save(
        s3_key="test.png",
        detection_count=3,
        bucket="test-bucket",
        confidence=0.9,
        simulated=True,
    )
    assert item["s3_key"] == "test.png"
    assert item["confidence"] == 0.9
    assert len(store._load_all()) >= 7


def test_save_is_idempotent_for_same_s3_object(repo):
    first = repo.save(
        s3_key="dup.png",
        detection_count=2,
        bucket="test-bucket",
        simulated=True,
    )
    second = repo.save(
        s3_key="dup.png",
        detection_count=99,
        bucket="test-bucket",
        simulated=True,
    )
    assert second["_duplicate"] is True
    assert second["detection_count"] == first["detection_count"]
    assert len([i for i in store._load_all() if i.get("s3_key") == "dup.png"]) == 1


def test_list_since_hours_filters_old_records(repo, tmp_path, monkeypatch):
    old_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat().replace(
        "+00:00", "Z"
    )
    recent_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    path = tmp_path / "storm_alerts.json"
    path.write_text(
        f'[{{"alert_type":"storm_detection","timestamp":"{old_ts}","s3_key":"old.png"}},'
        f'{{"alert_type":"storm_detection","timestamp":"{recent_ts}","s3_key":"new.png"}}]',
        encoding="utf-8",
    )
    monkeypatch.setattr(store.settings, "DYNAMODB_MOCK_STORE_PATH", str(path))
    repo2 = store.JsonStormAlertRepository()

    recent = repo2.list_since_hours(24)

    assert len(recent) == 1
    assert recent[0]["s3_key"] == "new.png"


def test_list_since_days_delegates_to_hours(repo):
    repo.ensure_seeded()
    days_result = repo.list_since_days(7)
    hours_result = repo.list_since_hours(7 * 24)
    assert days_result == hours_result


def test_load_all_handles_corrupt_json(tmp_path, monkeypatch):
    path = tmp_path / "bad.json"
    path.write_text("not-json", encoding="utf-8")
    monkeypatch.setattr(store.settings, "DYNAMODB_MOCK_STORE_PATH", str(path))
    assert store._load_all() == []


def test_parse_ts_invalid_returns_none():
    assert store._parse_ts({"timestamp": "invalid"}) is None
    assert store._parse_ts({}) is None
