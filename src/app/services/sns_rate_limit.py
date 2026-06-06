"""Controle de limite diário de alertas SNS por e-mail."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORE_PATH = PROJECT_ROOT / "data" / "demo" / "sns_rate_limits.json"


def _store_path() -> Path:
    raw = (settings.SNS_RATE_LIMIT_STORE_PATH or "").strip()
    return Path(raw) if raw else DEFAULT_STORE_PATH


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_store() -> dict[str, Any]:
    path = _store_path()
    if not path.exists():
        return {"counts": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("counts"), dict):
            return data
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read SNS rate limit store %s: %s", path, exc)
    return {"counts": {}}


def _save_store(data: dict[str, Any]) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def get_daily_alert_count(email: str) -> int:
    """Retorna quantos alertas o e-mail recebeu hoje (UTC)."""
    normalized = email.strip().lower()
    if not normalized:
        return 0
    store = _load_store()
    day_counts = store.get("counts", {}).get(normalized, {})
    if not isinstance(day_counts, dict):
        return 0
    return int(day_counts.get(_today_utc(), 0))


def can_send_alert(email: str) -> bool:
    """True se o e-mail ainda não atingiu o limite diário."""
    limit = max(1, int(settings.SNS_MAX_ALERTS_PER_EMAIL_DAY))
    return get_daily_alert_count(email) < limit


def record_alert_sent(email: str) -> int:
    """Incrementa contador diário e retorna o novo total."""
    normalized = email.strip().lower()
    if not normalized:
        return 0
    store = _load_store()
    counts = store.setdefault("counts", {})
    day_counts = counts.setdefault(normalized, {})
    if not isinstance(day_counts, dict):
        day_counts = {}
        counts[normalized] = day_counts
    today = _today_utc()
    day_counts[today] = int(day_counts.get(today, 0)) + 1
    _save_store(store)
    return int(day_counts[today])


def reset_store_for_tests() -> None:
    """Limpa o store local (apenas testes)."""
    path = _store_path()
    if path.exists():
        path.unlink()
