"""Armazenamento local de alertas quando DynamoDB ainda não está disponível."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORE_PATH = PROJECT_ROOT / "data" / "demo" / "storm_alerts.json"

WEEKDAY_EN = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]


def use_mock_store() -> bool:
    """True = não chama AWS; usa JSON local + seed de demo."""
    if settings.DYNAMODB_USE_MOCK:
        return True
    key = (settings.AWS_ACCESS_KEY_ID or "").strip()
    if not key or key.startswith("your_"):
        return True
    return False


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
    """Gera alertas plausíveis para gráficos e mapa (últimos ~14 dias)."""
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
        weekday = WEEKDAY_EN[ts.weekday()]
        items.append({
            "alert_type": "storm_detection",
            "timestamp": ts.isoformat().replace("+00:00", "Z"),
            "alert_id": f"demo_{uuid.uuid4().hex[:12]}",
            "date": ts.strftime("%Y-%m-%d"),
            "hour": hour,
            "weekday": weekday,
            "bucket": "demo-local",
            "s3_key": s3_key,
            "detection_count": count,
            "classes": ["storm"],
            "simulated": True,
        })
    return items


def ensure_seeded() -> None:
    """Cria arquivo de demo na primeira execução."""
    path = _store_path()
    if path.exists() and path.stat().st_size > 2:
        return
    items = _seed_demo_alerts()
    _save_all(items)
    logger.info("Mock storm_alerts seeded: %d items → %s", len(items), path)


def list_alerts_since_hours(hours: int) -> list[dict[str, Any]]:
    ensure_seeded()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    out: list[dict[str, Any]] = []
    for item in _load_all():
        ts_raw = str(item.get("timestamp", ""))
        ts = ts_raw.replace("Z", "+00:00") if ts_raw.endswith("Z") else ts_raw
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if dt >= cutoff:
            out.append(item)
    out.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
    return out


def list_alerts_since_days(days: int) -> list[dict[str, Any]]:
    return list_alerts_since_hours(days * 24)


def add_alert(
    *,
    s3_key: str = "nasa_brasil_sudeste_simulated.png",
    detection_count: int = 2,
    bucket: str = "demo-local",
    alert_id: str | None = None,
) -> dict[str, Any]:
    ensure_seeded()
    now = datetime.now(timezone.utc)
    item = {
        "alert_type": "storm_detection",
        "timestamp": now.isoformat().replace("+00:00", "Z"),
        "alert_id": alert_id or f"sim_{uuid.uuid4().hex[:12]}",
        "date": now.strftime("%Y-%m-%d"),
        "hour": now.hour,
        "weekday": WEEKDAY_EN[now.weekday()],
        "bucket": bucket,
        "s3_key": s3_key,
        "detection_count": detection_count,
        "classes": ["storm"],
        "simulated": True,
    }
    items = _load_all()
    items.append(item)
    _save_all(items)
    return item


def add_alert_from_coords(
    lat: float,
    lon: float,
    confidence: float = 0.85,
) -> dict[str, Any]:
    """Simula alerta a partir de lat/lon (dashboard)."""
    if lon < -50:
        s3_key = "nasa_brasil_sudeste_simulated.png"
    elif lon < -55:
        s3_key = "nasa_brasil_simulated.png"
    else:
        s3_key = "nasa_americas_simulated.png"
    count = max(1, int((confidence - 0.5) / 0.08))
    return add_alert(s3_key=s3_key, detection_count=count)
