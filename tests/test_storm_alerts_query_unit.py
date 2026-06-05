"""Unit tests for storm_alerts_query helpers."""

from decimal import Decimal

import pytest

from app.services.storm_alerts_query import (
    StormAlertsQueryService,
    _parse_ts,
    _region_key,
    _to_int,
    confidence_from_item,
    coords_from_s3_key,
    item_to_detection,
)


def test_to_int_with_decimal():
    assert _to_int(Decimal("3")) == 3
    assert _to_int(None, default=5) == 5
    assert _to_int("bad", default=1) == 1


def test_parse_ts_formats():
    assert _parse_ts("2026-06-05T12:00:00Z") is not None
    assert _parse_ts("") is None
    assert _parse_ts("invalid") is None


def test_region_key_and_coords():
    assert _region_key("nasa_brasil_sudeste_01.png") == "nasa_brasil_sudeste"
    lat, lon = coords_from_s3_key("nasa_americas_2026.png")
    assert lat == -15.0
    assert lon == -60.0


def test_confidence_from_item():
    assert confidence_from_item({"detection_count": 0}) == 0.75
    assert confidence_from_item({"detection_count": 10}) == pytest.approx(0.99, abs=0.01)


def test_item_to_detection_structure():
    det = item_to_detection({
        "s3_key": "nasa_brasil_sudeste_x.png",
        "detection_count": 3,
        "timestamp": "2026-06-05T12:00:00Z",
        "alert_id": "alert/1",
    })
    assert det["detection_id"] == "alert_1"
    assert det["confidence"] > 0.5
    assert "latitude" in det


def test_map_overlay_filters_bbox(monkeypatch):
    svc = StormAlertsQueryService()
    monkeypatch.setattr(
        svc,
        "_scan_storm_alerts",
        lambda hours=24: [{
            "s3_key": "nasa_brasil_sudeste_x.png",
            "detection_count": 2,
            "timestamp": "2026-06-05T12:00:00Z",
            "alert_id": "a1",
        }],
    )
    features = svc.map_overlay_features(-90, -180, 90, 180, hours=24)
    assert len(features) == 1
    assert features[0].geometry.type == "Point"
