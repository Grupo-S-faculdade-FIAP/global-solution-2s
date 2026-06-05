"""Adapter JSON local para leituras IoT (mock / dev).

Implementa IoTReadingRepository usando um arquivo JSON em data/demo/.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_PATH = _PROJECT_ROOT / "data" / "demo" / "iot_readings.json"


def _load_all() -> list[dict[str, Any]]:
    if not _DEFAULT_PATH.exists():
        return []
    try:
        data = json.loads(_DEFAULT_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read iot mock store: %s", exc)
        return []


def _save_all(items: list[dict[str, Any]]) -> None:
    _DEFAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _DEFAULT_PATH.write_text(
        json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8"
    )


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


def _seed_demo() -> list[dict[str, Any]]:
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


def _parse_ts(item: dict[str, Any]) -> datetime | None:
    raw = str(item.get("timestamp", ""))
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


class JsonIoTReadingRepository:
    """Adapter de desenvolvimento — persiste leituras IoT em arquivo JSON local."""

    def ensure_seeded(self) -> None:
        if _DEFAULT_PATH.exists() and _DEFAULT_PATH.stat().st_size > 2:
            return
        _save_all(_seed_demo())
        logger.info("Mock iot_readings seeded → %s", _DEFAULT_PATH)

    def save(
        self,
        *,
        device_id: str,
        cidade: str,
        temperatura: float,
        umidade: float,
        reading_id: str | None = None,
    ) -> dict[str, Any]:
        self.ensure_seeded()
        item = _build_item(
            device_id=device_id,
            cidade=cidade,
            temperatura=temperatura,
            umidade=umidade,
            reading_id=reading_id,
        )
        items = _load_all()
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
