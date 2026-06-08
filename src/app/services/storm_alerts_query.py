"""Query storm alerts from DynamoDB for /storms/recent and /map/overlay."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from app.models.schemas import GeoJSONFeature, GeoJSONGeometry, GeoJSONProperties
from app.services.storm_alerts_store import list_alerts_since_hours, use_mock_store

logger = logging.getLogger(__name__)

# Centro aproximado por prefixo do arquivo NASA (s3_key ou nome)
REGION_COORDS: dict[str, tuple[float, float]] = {
    "nasa_americas": (-15.0, -60.0),
    "nasa_brasil_sudeste": (-23.55, -46.63),
    "nasa_nordeste": (-8.5, -39.5),
    "nasa_norte": (-3.5, -60.0),
    "nasa_sul": (-29.5, -52.0),
    "nasa_centro_oeste": (-15.8, -54.0),
    "nasa_leste_litoral": (-12.5, -38.5),
    "nasa_oeste": (-9.0, -67.0),
    "nasa_brasil": (-14.5, -52.0),
}


def _to_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_ts(value: str) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _region_key(s3_key: str) -> str:
    name = s3_key.lower()
    if "nasa_brasil_sudeste" in name or "brasil_sudeste" in name:
        return "nasa_brasil_sudeste"
    if "nasa_centro_oeste" in name or "centro_oeste" in name:
        return "nasa_centro_oeste"
    if "nasa_leste_litoral" in name or "leste_litoral" in name:
        return "nasa_leste_litoral"
    if "nasa_nordeste" in name or "nordeste" in name:
        return "nasa_nordeste"
    if "nasa_norte" in name or "norte" in name:
        return "nasa_norte"
    if "nasa_sul" in name or "_sul" in name:
        return "nasa_sul"
    if "nasa_oeste" in name or "_oeste" in name:
        return "nasa_oeste"
    if "nasa_brasil" in name or "brasil" in name:
        return "nasa_brasil"
    if "nasa_americas" in name or "americas" in name:
        return "nasa_americas"
    return "nasa_brasil"


def coords_from_s3_key(s3_key: str) -> tuple[float, float]:
    """Latitude, longitude inferidas pelo nome da captura."""
    key = _region_key(s3_key or "")
    lat, lon = REGION_COORDS.get(key, (-14.0, -51.0))
    return lat, lon


def confidence_from_item(item: dict[str, Any]) -> float:
    """Estima confiança quando o pipeline não gravou score YOLO."""
    count = _to_int(item.get("detection_count"), 0)
    if count <= 0:
        return 0.75
    return min(0.99, 0.50 + 0.08 * count)


def item_to_detection(item: dict[str, Any]) -> dict[str, Any]:
    s3_key = str(item.get("s3_key", ""))
    lat, lon = coords_from_s3_key(s3_key)
    ts = str(item.get("timestamp", ""))
    alert_id = str(item.get("alert_id") or item.get("timestamp") or "unknown")
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", alert_id)[:64]
    return {
        "detection_id": safe_id,
        "latitude": lat,
        "longitude": lon,
        "confidence": round(confidence_from_item(item), 4),
        "timestamp": ts,
        "s3_key": s3_key,
        "detection_count": _to_int(item.get("detection_count"), 0),
    }


def _point_in_bbox(lat: float, lon: float, south: float, west: float, north: float, east: float) -> bool:
    return south <= lat <= north and west <= lon <= east


class StormAlertsQueryService:
    """Lê alertas CV via storm_alerts_store (mock JSON ou DynamoDB)."""

    def _scan_storm_alerts(self, hours: int = 24) -> list[dict[str, Any]]:
        logger.debug("storm_alerts: store=%s", "mock" if use_mock_store() else "dynamodb")
        return list_alerts_since_hours(hours)

    def recent_detections(self, hours: int = 24) -> list[dict[str, Any]]:
        return [item_to_detection(item) for item in self._scan_storm_alerts(hours=hours)]

    def map_overlay_features(
        self,
        south: float,
        west: float,
        north: float,
        east: float,
        hours: int = 168,
    ) -> list[GeoJSONFeature]:
        features: list[GeoJSONFeature] = []
        for item in self._scan_storm_alerts(hours=hours):
            det = item_to_detection(item)
            lat, lon = det["latitude"], det["longitude"]
            if not _point_in_bbox(lat, lon, south, west, north, east):
                continue
            features.append(
                GeoJSONFeature(
                    properties=GeoJSONProperties(
                        type="storm",
                        intensity=det["confidence"],
                        timestamp=det["timestamp"],
                    ),
                    geometry=GeoJSONGeometry(
                        type="Point",
                        coordinates=[lon, lat],
                    ),
                )
            )
        return features
