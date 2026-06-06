"""Unit tests for NASA captures service helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services import nasa_captures


def test_nasa_captures_dir_relative(monkeypatch):
    monkeypatch.setattr(nasa_captures.settings, "NASA_CAPTURES_DIR", "data/nasa_captures")
    path = nasa_captures.nasa_captures_dir()
    assert path.name == "nasa_captures"
    assert "data" in str(path)


def test_nasa_captures_dir_absolute(tmp_path, monkeypatch):
    monkeypatch.setattr(nasa_captures.settings, "NASA_CAPTURES_DIR", str(tmp_path))
    assert nasa_captures.nasa_captures_dir() == tmp_path


def test_nasa_image_url_local_fallback():
    url = nasa_captures.nasa_image_url("nasa_test.png", fonte="captures")
    assert url == "/cv/nasa/imagem/nasa_test.png?fonte=captures"


def test_presigned_nasa_url_no_bucket(monkeypatch):
    monkeypatch.setattr(nasa_captures.settings, "S3_BUCKET_IMAGES", "")
    assert nasa_captures.presigned_nasa_url("nasa-satellite/nasa_test.png") is None


def test_presigned_nasa_url_success(monkeypatch):
    monkeypatch.setattr(nasa_captures.settings, "S3_BUCKET_IMAGES", "satellite-images-gs2")
    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.return_value = "https://signed.example/nasa.png"
    with patch.object(nasa_captures, "_s3_client", return_value=mock_s3):
        url = nasa_captures.presigned_nasa_url("nasa-satellite/nasa_test.png")
    assert url == "https://signed.example/nasa.png"


def test_list_s3_nasa_objects_filters_small_files(monkeypatch):
    monkeypatch.setattr(nasa_captures.settings, "S3_BUCKET_IMAGES", "bucket")
    monkeypatch.setattr(nasa_captures.settings, "NASA_S3_PREFIX", "nasa-satellite")

    from datetime import datetime, timezone

    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {
        "Contents": [
            {
                "Key": "nasa-satellite/nasa_valid_001.png",
                "Size": 200_000,
                "LastModified": datetime.now(timezone.utc),
            },
            {
                "Key": "nasa-satellite/tiny.png",
                "Size": 500,
                "LastModified": datetime.now(timezone.utc),
            },
        ]
    }
    with patch.object(nasa_captures, "_s3_client", return_value=mock_s3):
        items = nasa_captures._list_s3_nasa_objects(max_items=10)

    assert len(items) == 1
    assert items[0]["arquivo"] == "nasa_valid_001.png"


def test_list_nasa_captures_empty(monkeypatch):
    monkeypatch.setattr(nasa_captures, "_bucket_configured", lambda: False)
    monkeypatch.setattr(nasa_captures, "_collect_pngs", lambda directories: [])
    result = nasa_captures.list_nasa_captures(limite=5)
    assert result["total"] == 0
    assert result["capturas"] == []
