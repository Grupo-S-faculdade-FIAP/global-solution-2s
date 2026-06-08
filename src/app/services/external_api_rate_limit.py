"""Limite horário de chamadas a APIs externas sem token (Open-Meteo, INMET, etc.).

Em runtime Lambda (AWS_LAMBDA_FUNCTION_NAME) o limite é desabilitado — ingestão
agendada e API em produção não são restringidas. Em dev local (`make demo`) protege
o free tier (~20 req/h por instância).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORE_PATH = PROJECT_ROOT / "data" / "demo" / "external_api_rate_limits.json"
_WINDOW = timedelta(hours=1)


class ExternalApiRateLimitExceeded(Exception):
    """Limite horário de chamadas externas atingido (HTTP 429)."""

    def __init__(self, limit: int, retry_after_sec: int | None = None) -> None:
        self.limit = limit
        self.retry_after_sec = retry_after_sec
        msg = (
            f"Limite de {limit} chamadas externas por hora atingido "
            f"(APIs sem token — Open-Meteo, INMET). Tente novamente em breve."
        )
        super().__init__(msg)


def is_lambda_runtime() -> bool:
    """True quando executando dentro de AWS Lambda."""
    return bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))


def _store_path() -> Path:
    raw = (settings.EXTERNAL_API_RATE_LIMIT_STORE_PATH or "").strip()
    return Path(raw) if raw else DEFAULT_STORE_PATH


def _load_store() -> dict[str, Any]:
    path = _store_path()
    if not path.exists():
        return {"calls": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("calls"), list):
            return data
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read external API rate limit store %s: %s", path, exc)
    return {"calls": []}


def _save_store(data: dict[str, Any]) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _parse_ts(raw: str) -> datetime | None:
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _prune_calls(calls: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    cutoff = now - _WINDOW
    kept: list[dict[str, Any]] = []
    for item in calls:
        if not isinstance(item, dict):
            continue
        ts = _parse_ts(str(item.get("at", "")))
        if ts is not None and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts is not None and ts >= cutoff:
            kept.append(item)
    return kept


def get_hourly_call_count() -> int:
    """Quantidade de chamadas externas na janela móvel de 1 h."""
    now = datetime.now(timezone.utc)
    store = _load_store()
    return len(_prune_calls(store.get("calls", []), now))


def _retry_after_seconds(calls: list[dict[str, Any]], now: datetime, limit: int) -> int:
    if len(calls) < limit:
        return 60
    oldest = min(
        ts
        for item in calls
        if (ts := _parse_ts(str(item.get("at", "")))) is not None
    )
    if oldest.tzinfo is None:
        oldest = oldest.replace(tzinfo=timezone.utc)
    delta = (_WINDOW - (now - oldest)).total_seconds()
    return max(1, int(delta) + 1)


def acquire_external_api_slot(provider: str = "external") -> None:
    """Reserva slot antes de HTTP externo; levanta 429 se limite horário excedido."""
    if is_lambda_runtime():
        return
    if not settings.EXTERNAL_API_RATE_LIMIT_ENABLED:
        return

    limit = max(1, int(settings.EXTERNAL_API_RATE_LIMIT_PER_HOUR))
    now = datetime.now(timezone.utc)
    store = _load_store()
    calls = _prune_calls(store.get("calls", []), now)

    if len(calls) >= limit:
        retry = _retry_after_seconds(calls, now, limit)
        logger.warning(
            "External API rate limit exceeded (%d/%d h) provider=%s retry_after=%ds",
            len(calls),
            limit,
            provider,
            retry,
        )
        raise ExternalApiRateLimitExceeded(limit=limit, retry_after_sec=retry)

    calls.append({"at": now.isoformat(), "provider": provider})
    store["calls"] = calls
    _save_store(store)


def reset_store_for_tests() -> None:
    """Limpa store local (apenas testes)."""
    path = _store_path()
    if path.exists():
        path.unlink()
