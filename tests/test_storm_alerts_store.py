"""Tests for local mock DynamoDB store."""

import json
from pathlib import Path

import pytest

from app.services import storm_alerts_store as store


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    path = tmp_path / "alerts.json"
    monkeypatch.setattr(store, "DEFAULT_STORE_PATH", path)
    monkeypatch.setattr(store.settings, "DYNAMODB_USE_MOCK", True)
    monkeypatch.setattr(store.settings, "DYNAMODB_MOCK_STORE_PATH", str(path))
    path.write_text("[]", encoding="utf-8")
    return path


def test_use_mock_store_default_true(monkeypatch):
    monkeypatch.setattr(store.settings, "DYNAMODB_USE_MOCK", True)
    assert store.use_mock_store() is True


def test_seed_and_list(isolated_store):
    store.ensure_seeded()
    items = store.list_alerts_since_hours(24 * 30)
    assert len(items) >= 1
    assert items[0]["alert_type"] == "storm_detection"


def test_add_alert_persists(isolated_store):
    store.ensure_seeded()
    before = len(store.list_alerts_since_hours(1))
    store.add_alert_from_coords(-23.55, -46.63, 0.9)
    after = store.list_alerts_since_hours(1)
    assert len(after) == before + 1
    data = json.loads(isolated_store.read_text(encoding="utf-8"))
    assert isinstance(data, list)
