"""Armazenamento de alertas — DynamoDB (produção) ou JSON local (mock)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORE_PATH = PROJECT_ROOT / "data" / "demo" / "storm_alerts.json"

WEEKDAY_EN = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]


def use_mock_store() -> bool:
    """True = JSON local; False = DynamoDB AWS (requer credenciais válidas)."""
    return bool(settings.DYNAMODB_USE_MOCK)


def _store_path() -> Path:
    raw = (settings.DYNAMODB_MOCK_STORE_PATH or "").strip()
    return Path(raw) if raw else DEFAULT_STORE_PATH


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_all() -> list[dict[str, Any]]:
    path = _store_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read mock store %s: %s", path, exc)
    return []


def _save_all(items: list[dict[str, Any]]) -> None:
    path = _store_path()
    _ensure_dir(path)
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


def _seed_demo_alerts() -> list[dict[str, Any]]:
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
    for i, (s3_key, count, hour) in enumerate(templates):
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


def _build_item(
    *,
    s3_key: str,
    detection_count: int,
    bucket: str,
    alert_id: str | None = None,
    timestamp: datetime | None = None,
    simulated: bool = False,
    classes: list[str] | None = None,
) -> dict[str, Any]:
    now = timestamp or datetime.now(timezone.utc)
    return {
        "alert_type": "storm_detection",
        "timestamp": now.isoformat().replace("+00:00", "Z"),
        "alert_id": alert_id or f"alert_{uuid.uuid4().hex[:12]}",
        "date": now.strftime("%Y-%m-%d"),
        "hour": now.hour,
        "weekday": WEEKDAY_EN[now.weekday()],
        "bucket": bucket,
        "s3_key": s3_key,
        "detection_count": detection_count,
        "classes": classes or ["storm"],
        "simulated": simulated,
    }


def _dynamodb_table():
    dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    return dynamodb.Table(settings.DYNAMODB_TABLE_ALERTS)


def _put_dynamodb(item: dict[str, Any]) -> dict[str, Any]:
    table = _dynamodb_table()
    table.put_item(Item=item)
    logger.info("Alert saved to DynamoDB table %s: %s", settings.DYNAMODB_TABLE_ALERTS, item.get("alert_id"))
    return item


def _scan_dynamodb_since(cutoff: datetime) -> list[dict[str, Any]]:
    """Lista alertas storm_detection com timestamp >= cutoff (UTC)."""
    cutoff_iso = cutoff.isoformat().replace("+00:00", "Z")
    table = _dynamodb_table()
    items: list[dict[str, Any]] = []
    scan_kwargs: dict[str, Any] = {
        "FilterExpression": "alert_type = :atype AND #ts >= :cutoff",
        "ExpressionAttributeNames": {"#ts": "timestamp"},
        "ExpressionAttributeValues": {
            ":atype": "storm_detection",
            ":cutoff": cutoff_iso,
        },
    }
    try:
        while True:
            page = table.scan(**scan_kwargs)
            items.extend(page.get("Items", []))
            last_key = page.get("LastEvaluatedKey")
            if not last_key:
                break
            scan_kwargs["ExclusiveStartKey"] = last_key
    except (ClientError, BotoCoreError) as exc:
        logger.error("DynamoDB scan failed: %s", exc)
        raise
    items.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
    return items


def _parse_alert_timestamp(item: dict[str, Any]) -> datetime | None:
    ts_raw = str(item.get("timestamp", ""))
    if not ts_raw:
        return None
    ts = ts_raw.replace("Z", "+00:00") if ts_raw.endswith("Z") else ts_raw
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def ensure_seeded() -> None:
    """Cria arquivo de demo na primeira execução (somente mock)."""
    if not use_mock_store():
        return
    path = _store_path()
    if path.exists() and path.stat().st_size > 2:
        return
    items = _seed_demo_alerts()
    _save_all(items)
    logger.info("Mock storm_alerts seeded: %d items → %s", len(items), path)


def list_alerts_since_hours(hours: int) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    if use_mock_store():
        ensure_seeded()
        source = _load_all()
    else:
        source = _scan_dynamodb_since(cutoff)

    out: list[dict[str, Any]] = []
    for item in source:
        dt = _parse_alert_timestamp(item)
        if dt is None or dt < cutoff:
            continue
        out.append(item)
    out.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
    return out


def list_alerts_since_days(days: int) -> list[dict[str, Any]]:
    return list_alerts_since_hours(days * 24)


def add_alert(
    *,
    s3_key: str = "nasa_brasil_sudeste_simulated.png",
    detection_count: int = 2,
    bucket: str | None = None,
    alert_id: str | None = None,
    simulated: bool = True,
    classes: list[str] | None = None,
) -> dict[str, Any]:
    bucket_name = bucket or settings.S3_BUCKET_IMAGES
    item = _build_item(
        s3_key=s3_key,
        detection_count=detection_count,
        bucket=bucket_name,
        alert_id=alert_id,
        simulated=simulated,
        classes=classes,
    )

    if use_mock_store():
        ensure_seeded()
        items = _load_all()
        items.append(item)
        _save_all(items)
        return item

    try:
        return _put_dynamodb(item)
    except (ClientError, BotoCoreError) as exc:
        logger.error("DynamoDB put_item failed: %s", exc)
        raise


def add_alert_from_coords(
    lat: float,
    lon: float,
    confidence: float = 0.85,
) -> dict[str, Any]:
    """Registra alerta a partir de lat/lon (dashboard simulate)."""
    if lon < -50:
        s3_key = "nasa_brasil_sudeste_simulated.png"
    elif lon < -55:
        s3_key = "nasa_brasil_simulated.png"
    else:
        s3_key = "nasa_americas_simulated.png"
    count = max(1, int((confidence - 0.5) / 0.08))
    return add_alert(
        s3_key=s3_key,
        detection_count=count,
        simulated=True,
    )
