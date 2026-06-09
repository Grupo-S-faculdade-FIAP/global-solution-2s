"""Cooldown regional de alertas SNS (evita spam por região no cron NASA)."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.services.sns_rate_limit import is_lambda_runtime


def _aws_available() -> bool:
    try:
        creds = boto3.Session().get_credentials()
        return creds is not None and bool(creds.access_key)
    except (BotoCoreError, ClientError, OSError):
        return False

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORE_PATH = PROJECT_ROOT / "data" / "demo" / "sns_region_cooldown.json"

# Ex.: brasil_sudeste_20260609_1530.jpg → região brasil_sudeste
_REGION_SUFFIX_RE = re.compile(r"_\d{8}_\d{4}(?:\.[^.]+)?$")


def use_mock_store() -> bool:
    """True = JSON local; False = DynamoDB (Lambda ou AWS com mock desligado)."""
    if is_lambda_runtime():
        return False
    if settings.DYNAMODB_USE_MOCK:
        return True
    if (settings.SNS_REGION_COOLDOWN_STORE_PATH or "").strip():
        return True
    if not _aws_available():
        return True
    return False


def _store_path() -> Path:
    raw = (settings.SNS_REGION_COOLDOWN_STORE_PATH or "").strip()
    return Path(raw) if raw else DEFAULT_STORE_PATH


def extract_region_from_s3_key(key: str) -> str | None:
    """Extrai região do nome do arquivo S3 (parte antes de _YYYYMMDD_HHMM)."""
    basename = key.rsplit("/", 1)[-1].strip()
    if not basename:
        return None
    match = _REGION_SUFFIX_RE.search(basename)
    if not match:
        return None
    region = basename[: match.start()].strip("_")
    return region or None


def _cooldown_delta() -> timedelta:
    minutes = max(1, int(settings.SNS_REGION_COOLDOWN_MINUTES))
    return timedelta(minutes=minutes)


def _region_pk(region: str) -> str:
    return f"REGION#{region.strip().lower()}"


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _dynamodb_table():
    dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    return dynamodb.Table(settings.DYNAMODB_TABLE_SNS_RATE_LIMIT)


def _load_store() -> dict[str, Any]:
    path = _store_path()
    if not path.exists():
        return {"regions": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("regions"), dict):
            return data
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read SNS region cooldown store %s: %s", path, exc)
    return {"regions": {}}


def _save_store(data: dict[str, Any]) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _get_last_alert_mock(region: str) -> datetime | None:
    store = _load_store()
    regions = store.get("regions", {})
    if not isinstance(regions, dict):
        return None
    raw = regions.get(region.strip().lower())
    if not isinstance(raw, str):
        return None
    return _parse_timestamp(raw)


def _get_last_alert_dynamodb(region: str) -> datetime | None:
    try:
        table = _dynamodb_table()
        response = table.get_item(Key={"pk": _region_pk(region)})
        item = response.get("Item", {})
        raw = item.get("last_alert_at")
        if not isinstance(raw, str):
            return None
        return _parse_timestamp(raw)
    except (ClientError, BotoCoreError) as exc:
        logger.error("DynamoDB get_item failed for region cooldown: %s", exc)
        return None


def can_send_region_alert(region: str) -> bool:
    """True se a região não está em cooldown desde o último alerta SNS."""
    normalized = region.strip().lower()
    if not normalized:
        return True
    last_alert = (
        _get_last_alert_mock(normalized)
        if use_mock_store()
        else _get_last_alert_dynamodb(normalized)
    )
    if last_alert is None:
        return True
    elapsed = datetime.now(timezone.utc) - last_alert
    return elapsed >= _cooldown_delta()


def record_region_alert(region: str) -> None:
    """Registra timestamp do último alerta SNS enviado para a região."""
    normalized = region.strip().lower()
    if not normalized:
        return
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat().replace("+00:00", "Z")
    if use_mock_store():
        store = _load_store()
        regions = store.setdefault("regions", {})
        if not isinstance(regions, dict):
            regions = {}
            store["regions"] = regions
        regions[normalized] = now_iso
        _save_store(store)
        return

    ttl = int((now + _cooldown_delta() + timedelta(days=1)).timestamp())
    try:
        table = _dynamodb_table()
        table.update_item(
            Key={"pk": _region_pk(normalized)},
            UpdateExpression="SET last_alert_at = :ts, #ttl = :ttl",
            ExpressionAttributeNames={"#ttl": "ttl"},
            ExpressionAttributeValues={":ts": now_iso, ":ttl": ttl},
        )
    except (ClientError, BotoCoreError) as exc:
        logger.error("DynamoDB update_item failed for region cooldown: %s", exc)


def reset_store_for_tests() -> None:
    """Limpa o store local (apenas testes)."""
    path = _store_path()
    if path.exists():
        path.unlink()
