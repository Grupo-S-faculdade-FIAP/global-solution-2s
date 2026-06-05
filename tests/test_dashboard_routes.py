"""Tests for dashboard router and UI registration."""

from __future__ import annotations

import os
from importlib import reload
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_dashboard_status() -> None:
    from app.main import app

    client = TestClient(app)
    response = client.get("/dashboard/status")
    assert response.status_code == 200
    assert response.json() == {"module": "dashboard", "status": "ready"}


def test_dashboard_climate_current_success() -> None:
    from app.main import app

    weather = {"temperature": 24.0, "humidity": 70.0}
    with patch("app.routers.dashboard._weather.get_current", return_value=weather):
        response = TestClient(app).get("/dashboard/climate/current?lat=-23.5&lon=-46.6")

    assert response.status_code == 200
    assert response.json() == {"data": weather, "source": "open-meteo"}


def test_dashboard_climate_current_error() -> None:
    from app.main import app

    with patch(
        "app.routers.dashboard._weather.get_current",
        side_effect=RuntimeError("upstream down"),
    ):
        response = TestClient(app).get("/dashboard/climate/current")

    assert response.status_code == 503
    assert "upstream down" in response.json()["detail"]


def test_dashboard_ui_index_when_flask_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOUNT_DASHBOARD", "false")
    import app.main as main_mod

    reload(main_mod)
    response = TestClient(main_mod.app).get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_dashboard_ui_register_missing_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import app.routers.dashboard_ui as dashboard_ui

    missing = tmp_path / "missing-dashboard"
    monkeypatch.setattr(dashboard_ui, "_TEMPLATES_DIR", missing / "templates")
    monkeypatch.setattr(dashboard_ui, "_STATIC_DIR", missing / "static")

    application = FastAPI()
    dashboard_ui.register(application)
    assert not any(r.path == "/" for r in application.routes)


def test_dashboard_ui_register_without_static(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import app.routers.dashboard_ui as dashboard_ui

    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "index.html").write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(dashboard_ui, "_TEMPLATES_DIR", templates)
    monkeypatch.setattr(dashboard_ui, "_STATIC_DIR", tmp_path / "no-static")

    application = FastAPI()
    dashboard_ui.register(application)
    assert any(r.path == "/" for r in application.routes)
    assert not any(getattr(r, "name", "") == "dashboard-static" for r in application.routes)


def test_config_mirrors_aws_credentials_to_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key-id")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

    import app.core.config as config_mod

    reload(config_mod)
    assert os.environ.get("AWS_ACCESS_KEY_ID") == "test-key-id"
    assert os.environ.get("AWS_SECRET_ACCESS_KEY") == "test-secret"
