"""Armazenamento de leituras IoT — DynamoDB (produção) ou JSON local (demo ESP32)."""

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
DEFAULT_STORE_PATH = PROJECT_ROOT / "data" / "demo" / "iot_readings.json"


def use_mock_store() -> bool:
    return bool(settings.IOT_USE_MOCK)


def _store_path() -> Path:
    return DEFAULT_STORE_PATH


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
        logger.warning("Could not read iot mock store %s: %s", path, exc)
    return []


def _save_all(items: list[dict[str, Any]]) -> None:
    path = _store_path()
    _ensure_dir(path)
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


def _seed_demo_readings() -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    templates = [
        ("esp32_01", "São Paulo", 24.5, 68.0),
        ("esp32_01", "São Paulo", 25.1, 65.3),
        ("esp32_01", "São Paulo", 26.3, 61.0),
        ("esp32_02", "Campinas", 22.8, 72.5),
        ("esp32_02", "Campinas", 23.4, 70.1),
    ]
    items: list[dict[str, Any]] = []
    for i, (device_id, cidade, temp, umid) in enumerate(templates):
        ts = now - timedelta(minutes=i * 15)
        items.append(_build_item(
            device_id=device_id,
            cidade=cidade,
            temperatura=temp,
            umidade=umid,
            timestamp=ts,
        ))
    return items


def _build_item(
    *,
    device_id: str,
    cidade: str,
    temperatura: float,
    umidade: float,
    timestamp: datetime | None = None,
    reading_id: str | None = None,
) -> dict[str, Any]:
    now = timestamp or datetime.now(timezone.utc)
    return {
        "reading_id": reading_id or f"iot_{uuid.uuid4().hex[:12]}",
        "device_id": device_id,
        "cidade": cidade,
        "temperatura": round(temperatura, 2),
        "umidade": round(umidade, 2),
        "timestamp": now.isoformat().replace("+00:00", "Z"),
        "date": now.strftime("%Y-%m-%d"),
        "hour": now.hour,
    }


def _dynamodb_table():
    dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    return dynamodb.Table(settings.DYNAMODB_IOT_TABLE)


def _put_dynamodb(item: dict[str, Any]) -> dict[str, Any]:
    table = _dynamodb_table()
    table.put_item(Item=item)
    logger.info(
        "IoT reading saved to DynamoDB table %s: %s",
        settings.DYNAMODB_IOT_TABLE,
        item.get("reading_id"),
    )
    return item


def _scan_dynamodb_since(cutoff: datetime) -> list[dict[str, Any]]:
    cutoff_iso = cutoff.isoformat().replace("+00:00", "Z")
    table = _dynamodb_table()
    items: list[dict[str, Any]] = []
    scan_kwargs: dict[str, Any] = {
        "FilterExpression": "#ts >= :cutoff",
        "ExpressionAttributeNames": {"#ts": "timestamp"},
        "ExpressionAttributeValues": {":cutoff": cutoff_iso},
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
        logger.error("DynamoDB scan (iot) failed: %s", exc)
        raise
    items.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
    return items


def ensure_seeded() -> None:
    if not use_mock_store():
        return
    path = _store_path()
    if path.exists() and path.stat().st_size > 2:
        return
    items = _seed_demo_readings()
    _save_all(items)
    logger.info("Mock iot_readings seeded: %d items → %s", len(items), path)


def list_readings_since_hours(hours: int) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    if use_mock_store():
        ensure_seeded()
        source = _load_all()
    else:
        source = _scan_dynamodb_since(cutoff)

    out: list[dict[str, Any]] = []
    for item in source:
        ts_raw = str(item.get("timestamp", ""))
        if not ts_raw:
            continue
        ts_str = ts_raw.replace("Z", "+00:00") if ts_raw.endswith("Z") else ts_raw
        try:
            dt = datetime.fromisoformat(ts_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if dt < cutoff:
            continue
        out.append(item)
    out.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
    return out


def add_reading(
    *,
    device_id: str = "esp32_01",
    cidade: str = "São Paulo",
    temperatura: float,
    umidade: float,
    reading_id: str | None = None,
) -> dict[str, Any]:
    item = _build_item(
        device_id=device_id,
        cidade=cidade,
        temperatura=temperatura,
        umidade=umidade,
        reading_id=reading_id,
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
        logger.error("DynamoDB put_item (iot) failed: %s", exc)
        raise
