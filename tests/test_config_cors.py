"""Tests for CORS / settings helpers."""

import os

from app.core.config import get_allowed_origins, settings


def test_get_allowed_origins_merges_extra(monkeypatch):
    monkeypatch.setenv("CORS_EXTRA_ORIGINS", "https://a.example.com, https://b.example.com")
    origins = get_allowed_origins()
    assert "https://a.example.com" in origins
    assert "https://b.example.com" in origins
    for base in settings.ALLOWED_ORIGINS:
        assert base in origins


def test_get_allowed_origins_without_extra(monkeypatch):
    monkeypatch.delenv("CORS_EXTRA_ORIGINS", raising=False)
    origins = get_allowed_origins()
    assert origins == list(settings.ALLOWED_ORIGINS)
