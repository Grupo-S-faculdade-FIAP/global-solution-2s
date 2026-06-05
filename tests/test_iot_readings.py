"""Tests for IoT readings store and endpoints."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.services import iot_readings_store as store


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    path = tmp_path / "iot_readings.json"
    monkeypatch.setattr(store, "DEFAULT_STORE_PATH", path)
    monkeypatch.setattr(store.settings, "DYNAMODB_USE_MOCK", True)
    path.write_text("[]", encoding="utf-8")
    return path


# ── Unit: store ──────────────────────────────────────────────────────────────

def test_use_mock_store_flag(monkeypatch):
    monkeypatch.setattr(store.settings, "DYNAMODB_USE_MOCK", True)
    assert store.use_mock_store() is True
    monkeypatch.setattr(store.settings, "DYNAMODB_USE_MOCK", False)
    assert store.use_mock_store() is False


def test_seed_creates_entries(isolated_store):
    store.ensure_seeded()
    items = store.list_readings_since_hours(24)
    assert len(items) >= 1
    r = items[0]
    assert "device_id" in r
    assert "temperatura" in r
    assert "umidade" in r
    assert "timestamp" in r


def test_add_reading_persists(isolated_store):
    store.ensure_seeded()
    before = len(store.list_readings_since_hours(1))
    store.add_reading(
        device_id="esp32_test",
        cidade="Campinas",
        temperatura=22.5,
        umidade=75.0,
    )
    after = store.list_readings_since_hours(1)
    assert len(after) == before + 1
    latest = after[0]
    assert latest["device_id"] == "esp32_test"
    assert latest["temperatura"] == 22.5
    assert latest["umidade"] == 75.0


def test_reading_schema(isolated_store):
    item = store.add_reading(
        device_id="esp32_01",
        cidade="São Paulo",
        temperatura=25.0,
        umidade=60.0,
    )
    assert "reading_id" in item
    assert item["reading_id"].startswith("iot_")
    assert "timestamp" in item
    assert item["timestamp"].endswith("Z")
    assert item["date"] is not None
    assert isinstance(item["hour"], int)


def test_list_respects_time_window(isolated_store):
    from datetime import datetime, timedelta, timezone

    old_ts = (datetime.now(timezone.utc) - timedelta(hours=50)).isoformat().replace("+00:00", "Z")
    old_item = {
        "reading_id": "old_001",
        "device_id": "esp32_01",
        "cidade": "SP",
        "temperatura": 20.0,
        "umidade": 60.0,
        "timestamp": old_ts,
        "date": "2020-01-01",
        "hour": 0,
    }
    path = store._store_path()
    path.write_text(json.dumps([old_item]), encoding="utf-8")

    recent = store.list_readings_since_hours(24)
    assert len(recent) == 0

    older = store.list_readings_since_hours(72)
    assert any(r["reading_id"] == "old_001" for r in older)


# ── Integration: API endpoints ───────────────────────────────────────────────

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DEFAULT_STORE_PATH", tmp_path / "iot.json")
    monkeypatch.setattr(store.settings, "DYNAMODB_USE_MOCK", True)
    (tmp_path / "iot.json").write_text("[]", encoding="utf-8")

    from app.main import app
    return TestClient(app)


def test_iot_status_endpoint(client):
    resp = client.get("/iot/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["module"] == "iot"
    assert data["status"] == "ready"
    assert "storage" in data


def test_post_reading_returns_201(client):
    payload = {
        "device_id": "esp32_01",
        "cidade": "Campinas",
        "temperatura": 23.4,
        "umidade": 70.0,
    }
    resp = client.post("/iot/readings", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["stored"] is True
    assert "reading_id" in data
    assert "timestamp" in data


def test_post_reading_validation(client):
    resp = client.post("/iot/readings", json={"temperatura": 200, "umidade": 50})
    assert resp.status_code == 422


def test_get_latest_readings(client):
    client.post("/iot/readings", json={
        "device_id": "esp32_02",
        "cidade": "Brasília",
        "temperatura": 30.0,
        "umidade": 45.0,
    })
    resp = client.get("/iot/readings/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert "readings" in data
    assert "count" in data
    assert data["count"] >= 1


def test_get_latest_respects_limit(client):
    for i in range(5):
        client.post("/iot/readings", json={
            "device_id": f"esp32_0{i}",
            "cidade": "SP",
            "temperatura": 20.0 + i,
            "umidade": 60.0,
        })
    resp = client.get("/iot/readings/latest?limit=3")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["readings"]) <= 3


def test_bff_iot_routes(tmp_path, monkeypatch):
    """BFF /api/iot/* routes — rota em modo in-process para evitar HTTP externo."""
    import os
    path = tmp_path / "iot_bff.json"
    monkeypatch.setattr(store, "DEFAULT_STORE_PATH", path)
    monkeypatch.setattr(store.settings, "DYNAMODB_USE_MOCK", True)
    path.write_text("[]", encoding="utf-8")
    monkeypatch.setenv("BFF_INPROCESS", "true")

    # Reseta o singleton do test client para captar o novo ambiente
    import dashboard.bff_backend as bff_be
    monkeypatch.setattr(bff_be, "_fastapi_test_client", None)

    from app.main import app
    from fastapi.testclient import TestClient

    tc = TestClient(app)

    resp = tc.get("/api/iot/status")
    assert resp.status_code == 200

    tc.post("/iot/readings", json={
        "device_id": "esp32_bff",
        "cidade": "SP",
        "temperatura": 22.0,
        "umidade": 65.0,
    })

    resp2 = tc.get("/api/iot/readings/latest")
    assert resp2.status_code == 200
    data = resp2.json()
    assert "readings" in data
