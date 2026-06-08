"""Shared pytest fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Evita carregar torch/YOLO durante pytest (segfault macOS com ML no mesmo processo)
os.environ.setdefault("RISK_SKIP_YOLO", "1")

_root = Path(__file__).parent.parent
sys.path.insert(0, str(_root / "src"))
sys.path.insert(0, str(_root / "tests"))

from app.clients.openmeteo import clear_openmeteo_cache  # noqa: E402
from app.services.external_api_rate_limit import reset_store_for_tests  # noqa: E402


@pytest.fixture(autouse=True)
def external_api_rate_limit_isolated(tmp_path, monkeypatch):
    """Store isolado por teste — evita 429 cruzado entre testes Open-Meteo/INMET."""
    store = tmp_path / "external_api_rate_limits.json"
    monkeypatch.setenv("EXTERNAL_API_RATE_LIMIT_STORE_PATH", str(store))
    from app.core.config import settings

    monkeypatch.setattr(settings, "EXTERNAL_API_RATE_LIMIT_STORE_PATH", str(store))
    reset_store_for_tests()
    yield
    reset_store_for_tests()


@pytest.fixture(autouse=True)
def clear_openmeteo_cache_fixture():
    """Evita poluição entre testes do cache Open-Meteo."""
    clear_openmeteo_cache()
    yield
    clear_openmeteo_cache()
