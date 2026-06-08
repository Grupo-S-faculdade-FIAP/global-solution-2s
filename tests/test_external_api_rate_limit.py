"""Testes do rate limit de APIs externas (Open-Meteo, INMET) — 100% coverage."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services import external_api_rate_limit as rl


@pytest.fixture
def rate_limit_store(tmp_path, monkeypatch):
    store = tmp_path / "external_api_rate_limits.json"
    monkeypatch.setattr(settings, "EXTERNAL_API_RATE_LIMIT_STORE_PATH", str(store))
    monkeypatch.setattr(settings, "EXTERNAL_API_RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "EXTERNAL_API_RATE_LIMIT_PER_HOUR", 3)
    rl.reset_store_for_tests()
    yield store
    rl.reset_store_for_tests()


# ─── Exception & runtime ───────────────────────────────────────────────────────


def test_external_api_rate_limit_exceeded_message():
    exc = rl.ExternalApiRateLimitExceeded(limit=20, retry_after_sec=120)
    assert exc.limit == 20
    assert exc.retry_after_sec == 120
    assert "20 chamadas externas" in str(exc)


def test_is_lambda_runtime_true(monkeypatch):
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "gs2-api")
    assert rl.is_lambda_runtime() is True


def test_is_lambda_runtime_false(monkeypatch):
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    assert rl.is_lambda_runtime() is False


def test_lambda_runtime_bypasses_limit(monkeypatch, rate_limit_store):
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "gs2-api")
    for _ in range(10):
        rl.acquire_external_api_slot("open-meteo")
    assert rl.get_hourly_call_count() == 0


def test_disabled_via_settings(monkeypatch, rate_limit_store):
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    monkeypatch.setattr(settings, "EXTERNAL_API_RATE_LIMIT_ENABLED", False)
    for _ in range(10):
        rl.acquire_external_api_slot("open-meteo")
    assert rl.get_hourly_call_count() == 0


# ─── Store I/O ─────────────────────────────────────────────────────────────────


def test_store_path_default_when_empty(monkeypatch):
    monkeypatch.setattr(settings, "EXTERNAL_API_RATE_LIMIT_STORE_PATH", "")
    assert rl._store_path() == rl.DEFAULT_STORE_PATH


def test_store_path_custom(monkeypatch, tmp_path):
    custom = tmp_path / "custom.json"
    monkeypatch.setattr(settings, "EXTERNAL_API_RATE_LIMIT_STORE_PATH", str(custom))
    assert rl._store_path() == custom


def test_load_store_missing_file(rate_limit_store):
    assert rl._load_store() == {"calls": []}


def test_load_store_invalid_json(rate_limit_store):
    rate_limit_store.write_text("{not json", encoding="utf-8")
    assert rl._load_store() == {"calls": []}


def test_load_store_os_error(monkeypatch, rate_limit_store):
    monkeypatch.setattr(
        rl.Path,
        "read_text",
        lambda *_a, **_k: (_ for _ in ()).throw(OSError("denied")),
    )
    assert rl._load_store() == {"calls": []}


def test_load_store_invalid_structure(rate_limit_store):
    rate_limit_store.write_text('{"calls": "not-a-list"}', encoding="utf-8")
    assert rl._load_store() == {"calls": []}

    rate_limit_store.write_text('["not", "a", "dict"]', encoding="utf-8")
    assert rl._load_store() == {"calls": []}


def test_save_store_creates_parent(tmp_path, monkeypatch):
    nested = tmp_path / "nested" / "store.json"
    monkeypatch.setattr(settings, "EXTERNAL_API_RATE_LIMIT_STORE_PATH", str(nested))
    rl._save_store({"calls": []})
    assert nested.exists()
    assert json.loads(nested.read_text(encoding="utf-8")) == {"calls": []}


def test_reset_store_for_tests_no_file(tmp_path, monkeypatch):
    missing = tmp_path / "missing.json"
    monkeypatch.setattr(settings, "EXTERNAL_API_RATE_LIMIT_STORE_PATH", str(missing))
    rl.reset_store_for_tests()  # não deve falhar


# ─── Parsing & pruning ─────────────────────────────────────────────────────────


def test_parse_ts_invalid():
    assert rl._parse_ts("not-a-date") is None


def test_prune_calls_skips_non_dict_and_invalid_ts():
    now = datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc)
    calls = [
        "bad",
        {"at": "invalid"},
        {"at": (now - timedelta(minutes=30)).isoformat()},
    ]
    pruned = rl._prune_calls(calls, now)
    assert len(pruned) == 1


def test_prune_calls_naive_datetime_gets_utc():
    now = datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc)
    naive_recent = (now - timedelta(minutes=10)).replace(tzinfo=None).isoformat()
    pruned = rl._prune_calls([{"at": naive_recent}], now)
    assert len(pruned) == 1


def test_prunes_calls_outside_window(monkeypatch, rate_limit_store):
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    rate_limit_store.write_text(
        json.dumps({"calls": [{"at": old, "provider": "open-meteo"}]}),
        encoding="utf-8",
    )
    assert rl.get_hourly_call_count() == 0
    rl.acquire_external_api_slot("open-meteo")
    assert rl.get_hourly_call_count() == 1


# ─── acquire / retry ───────────────────────────────────────────────────────────


def test_acquire_records_calls_when_not_lambda(monkeypatch, rate_limit_store):
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    rl.acquire_external_api_slot("open-meteo")
    rl.acquire_external_api_slot("inmet")
    assert rl.get_hourly_call_count() == 2


def test_raises_when_limit_exceeded(monkeypatch, rate_limit_store):
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    for _ in range(3):
        rl.acquire_external_api_slot("open-meteo")
    with pytest.raises(rl.ExternalApiRateLimitExceeded) as exc_info:
        rl.acquire_external_api_slot("open-meteo")
    assert exc_info.value.limit == 3
    assert exc_info.value.retry_after_sec is not None


def test_retry_after_seconds_under_limit():
    now = datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc)
    assert rl._retry_after_seconds([], now, limit=3) == 60


def test_retry_after_seconds_naive_oldest():
    now = datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc)
    naive = (now - timedelta(minutes=30)).replace(tzinfo=None).isoformat()
    calls = [{"at": naive, "provider": "x"}]
    retry = rl._retry_after_seconds(calls, now, limit=1)
    assert 1 <= retry <= 3600


def test_limit_minimum_one(monkeypatch, rate_limit_store):
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    monkeypatch.setattr(settings, "EXTERNAL_API_RATE_LIMIT_PER_HOUR", 0)
    rl.acquire_external_api_slot("open-meteo")
    assert rl.get_hourly_call_count() == 1


# ─── HTTP integration ──────────────────────────────────────────────────────────


@patch("app.clients.openmeteo.requests.get")
def test_weather_endpoint_returns_429(mock_get, monkeypatch, rate_limit_store):
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    mock_get.return_value.json.return_value = {
        "hourly": {
            "temperature_2m": [22.0],
            "relative_humidity_2m": [60],
            "pressure_msl": [1013.0],
            "wind_speed_10m": [5.0],
            "wind_direction_10m": [180],
            "precipitation": [0.0],
            "time": ["2026-06-08T12:00"],
        }
    }
    mock_get.return_value.raise_for_status = lambda: None

    client = TestClient(app)
    for i in range(3):
        r = client.get("/weather/current", params={"lat": -23.5 + i * 0.01, "lon": -46.6})
        assert r.status_code == 200, r.text

    r429 = client.get("/weather/current", params={"lat": -22.0, "lon": -43.0})
    assert r429.status_code == 429
    assert "Limite de 3 chamadas externas" in r429.json()["detail"]
    assert "Retry-After" in r429.headers


@pytest.mark.asyncio
async def test_main_exception_handler_without_retry_after():
    """Handler FastAPI cobre exc.retry_after_sec is None (sem header Retry-After)."""
    from app.main import external_api_rate_limit_handler

    exc = rl.ExternalApiRateLimitExceeded(limit=3, retry_after_sec=None)
    response = await external_api_rate_limit_handler(None, exc)
    assert response.status_code == 429
    assert "Retry-After" not in response.headers
    assert response.body  # JSONResponse populated
