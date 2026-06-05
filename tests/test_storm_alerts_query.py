"""Tests for storm alerts query service (API-01–05)."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.storm_alerts_query import (
    StormAlertsQueryService,
    confidence_from_item,
    coords_from_s3_key,
    item_to_detection,
)


def test_coords_from_s3_key_regions():
    lat, lon = coords_from_s3_key("uploads/nasa_brasil_sudeste_20260604_1530.png")
    assert lat == pytest.approx(-23.55)
    assert lon == pytest.approx(-46.63)

    lat2, lon2 = coords_from_s3_key("nasa_americas_20260604_1344.png")
    assert lat2 == pytest.approx(-15.0)
    assert lon2 == pytest.approx(-60.0)


def test_confidence_from_detection_count():
    assert confidence_from_item({"detection_count": 0}) == 0.75
    assert confidence_from_item({"detection_count": 10}) == pytest.approx(0.99, abs=0.01)


def test_item_to_detection_shape():
    det = item_to_detection({
        "alert_id": "msg-123",
        "timestamp": "2026-06-04T12:00:00Z",
        "s3_key": "nasa_brasil_20260604_1340.png",
        "detection_count": 3,
    })
    assert det["detection_id"] == "msg-123"
    assert "latitude" in det
    assert "longitude" in det
    assert 0 < det["confidence"] <= 1


@patch("app.services.storm_alerts_query.use_mock_store", return_value=False)
@patch("app.services.storm_alerts_query.boto3")
def test_recent_detections_returns_mapped_items(mock_boto3, _mock_off):
    mock_table = MagicMock()
    mock_boto3.resource.return_value.Table.return_value = mock_table
    mock_table.scan.return_value = {
        "Items": [
            {
                "alert_type": "storm_detection",
                "timestamp": "2026-06-04T15:00:00Z",
                "alert_id": "a1",
                "s3_key": "nasa_brasil_sudeste_x.png",
                "detection_count": 2,
            }
        ],
    }

    svc = StormAlertsQueryService()
    results = svc.recent_detections(hours=24)
    assert len(results) == 1
    assert results[0]["detection_id"] == "a1"
    assert results[0]["confidence"] > 0


@patch("app.services.storm_alerts_query.use_mock_store", return_value=False)
@patch("app.services.storm_alerts_query.boto3")
def test_map_overlay_filters_bbox(mock_boto3, _mock_off):
    mock_table = MagicMock()
    mock_boto3.resource.return_value.Table.return_value = mock_table
    mock_table.scan.return_value = {
        "Items": [
            {
                "alert_type": "storm_detection",
                "timestamp": "2026-06-04T15:00:00Z",
                "alert_id": "a1",
                "s3_key": "nasa_brasil_sudeste_x.png",
                "detection_count": 1,
            },
            {
                "alert_type": "storm_detection",
                "timestamp": "2026-06-04T14:00:00Z",
                "alert_id": "a2",
                "s3_key": "nasa_americas_x.png",
                "detection_count": 1,
            },
        ],
    }

    svc = StormAlertsQueryService()
    # bbox Sudeste BR
    features = svc.map_overlay_features(-26, -48, -22, -44, hours=48)
    assert len(features) == 1
    assert features[0].geometry.coordinates[1] == pytest.approx(-23.55)


@patch("app.services.storm_alerts_query.use_mock_store", return_value=False)
@patch("app.services.storm_alerts_query.boto3")
def test_scan_returns_empty_on_dynamodb_error(mock_boto3, _mock_off):
    from botocore.exceptions import ClientError

    mock_table = MagicMock()
    mock_boto3.resource.return_value.Table.return_value = mock_table
    mock_table.scan.side_effect = ClientError(
        {"Error": {"Code": "ResourceNotFoundException", "Message": "x"}},
        "Scan",
    )

    svc = StormAlertsQueryService()
    assert svc.recent_detections(hours=1) == []
