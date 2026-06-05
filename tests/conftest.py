"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_root = Path(__file__).parent.parent
sys.path.insert(0, str(_root / "src"))
sys.path.insert(0, str(_root / "tests"))

from app.clients.openmeteo import OpenMeteoClient  # noqa: E402


@pytest.fixture(autouse=True)
def clear_openmeteo_cache():
    """Avoid cross-test pollution from @lru_cache on OpenMeteoClient.get_current."""
    OpenMeteoClient.get_current.cache_clear()
    yield
    OpenMeteoClient.get_current.cache_clear()
