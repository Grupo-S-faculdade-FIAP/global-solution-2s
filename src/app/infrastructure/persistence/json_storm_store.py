"""Adapter JSON local para alertas de tempestade (mock / dev).

Implementa StormAlertRepository usando um arquivo JSON em data/demo/.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.infrastructure.persistence.json_io import atomic_write_json

logger = logging.getLogger(__name__)

_WEEKDAY_EN = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_PATH = _PROJECT_ROOT / "data" / "demo" / "storm_alerts.json"


def _store_path() -> Path:
    raw = (settings.DYNAMODB_MOCK_STORE_PATH or "").strip()
    return Path(raw) if raw else _DEFAULT_PATH


def _load_all() -> list[dict[str, Any]]:
    path = _store_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read mock store %s: %s", path, exc)
        return []


def _save_all(items: list[dict[str, Any]]) -> None:
    atomic_write_json(_store_path(), items)


def _find_by_object(
    items: list[dict[str, Any]], bucket: str, s3_key: str
) -> dict[str, Any] | None:
    for item in items:
        if item.get("bucket") == bucket and item.get("s3_key") == s3_key:
            return item
    return None


def _build_item(
    *,
    s3_key: str,
    detection_count: int,
    bucket: str,
    alert_id: str | None = None,
    timestamp: datetime | None = None,
    simulated: bool = False,
    classes: list[str] | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    now = timestamp or datetime.now(timezone.utc)
    item: dict[str, Any] = {
        "alert_type": "storm_detection",
        "timestamp": now.isoformat().replace("+00:00", "Z"),
        "alert_id": alert_id or f"alert_{uuid.uuid4().hex[:12]}",
        "date": now.strftime("%Y-%m-%d"),
        "hour": now.hour,
        "weekday": _WEEKDAY_EN[now.weekday()],
        "bucket": bucket,
        "s3_key": s3_key,
        "detection_count": detection_count,
        "classes": classes or ["storm"],
        "simulated": simulated,
    }
    if confidence is not None:
        item["confidence"] = round(float(confidence), 4)
    return item


def _seed_demo() -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    templates = [
        ("nasa_brasil_sudeste_20260604_1530.png", 4, 14),
        ("nasa_brasil_sudeste_20260604_1351.png", 3, 15),
        ("nasa_brasil_20260604_1534.png", 2, 11),
        ("nasa_americas_20260604_1349.png", 2, 16),
        ("nasa_brasil_sudeste_20260604_1528.png", 5, 15),
        ("nasa_americas_20260604_1536.png", 1, 13),
    ]
    items: list[dict[str, Any]] = []
    for i, (s3_key, count, _hour) in enumerate(templates):
        ts = now - timedelta(days=i % 12, hours=(i * 3) % 8)
        items.append(_build_item(
            s3_key=s3_key,
            detection_count=count,
            bucket="demo-local",
            alert_id=f"demo_{uuid.uuid4().hex[:12]}",
            timestamp=ts,
            simulated=True,
        ))
    return items


def _parse_ts(item: dict[str, Any]) -> datetime | None:
    raw = str(item.get("timestamp", ""))
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


class JsonStormAlertRepository:
    """Adapter de desenvolvimento — persiste alertas em arquivo JSON local."""

    def ensure_seeded(self) -> None:
        path = _store_path()
        if path.exists() and path.stat().st_size > 2:
            return
        _save_all(_seed_demo())
        logger.info("Mock storm_alerts seeded → %s", path)

    def save(
        self,
        *,
        s3_key: str,
        detection_count: int,
        bucket: str,
        alert_id: str | None = None,
        simulated: bool = False,
        classes: list[str] | None = None,
        confidence: float | None = None,
    ) -> dict[str, Any]:
        self.ensure_seeded()
        items = _load_all()
        existing = _find_by_object(items, bucket, s3_key)
        if existing is not None:
            return {**existing, "_duplicate": True}
        item = _build_item(
            s3_key=s3_key,
            detection_count=detection_count,
            bucket=bucket,
            alert_id=alert_id,
            simulated=simulated,
            classes=classes,
            confidence=confidence,
        )
        items.append(item)
        _save_all(items)
        return item

    def list_since_hours(self, hours: int) -> list[dict[str, Any]]:
        self.ensure_seeded()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        out = []
        for item in _load_all():
            dt = _parse_ts(item)
            if dt and dt >= cutoff:
                out.append(item)
        out.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
        return out

    def list_since_days(self, days: int) -> list[dict[str, Any]]:
        return self.list_since_hours(days * 24)
