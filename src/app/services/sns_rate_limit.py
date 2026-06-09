"""Controle de limite diário de alertas SNS por e-mail."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORE_PATH = PROJECT_ROOT / "data" / "demo" / "sns_rate_limits.json"


def is_lambda_runtime() -> bool:
    """True quando executando dentro de AWS Lambda."""
    return bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))


def _aws_available() -> bool:
    try:
        creds = boto3.Session().get_credentials()
        return creds is not None and bool(creds.access_key)
    except (BotoCoreError, ClientError, OSError):
        return False


def use_mock_store() -> bool:
    """True = JSON local; False = DynamoDB (Lambda ou AWS com mock desligado)."""
    if is_lambda_runtime():
        return False
    if settings.DYNAMODB_USE_MOCK:
        return True
    if (settings.SNS_RATE_LIMIT_STORE_PATH or "").strip():
        return True
    if not _aws_available():
        return True
    return False


def _store_path() -> Path:
    raw = (settings.SNS_RATE_LIMIT_STORE_PATH or "").strip()
    return Path(raw) if raw else DEFAULT_STORE_PATH


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _email_day_pk(email: str, day: str | None = None) -> str:
    normalized = email.strip().lower()
    return f"EMAIL#{normalized}#DAY#{day or _today_utc()}"


def _ttl_end_of_day_plus_one() -> int:
    now = datetime.now(timezone.utc)
    end_of_day = datetime(
        now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc
    )
    expires = end_of_day + timedelta(days=1)
    return int(expires.timestamp())


def _dynamodb_table():
    dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    return dynamodb.Table(settings.DYNAMODB_TABLE_SNS_RATE_LIMIT)


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


def _get_daily_alert_count_mock(email: str) -> int:
    normalized = email.strip().lower()
    if not normalized:
        return 0
    store = _load_store()
    day_counts = store.get("counts", {}).get(normalized, {})
    if not isinstance(day_counts, dict):
        return 0
    return int(day_counts.get(_today_utc(), 0))


def _get_daily_alert_count_dynamodb(email: str) -> int:
    normalized = email.strip().lower()
    if not normalized:
        return 0
    try:
        table = _dynamodb_table()
        response = table.get_item(Key={"pk": _email_day_pk(normalized)})
        item = response.get("Item", {})
        return int(item.get("alert_count", 0))
    except (ClientError, BotoCoreError) as exc:
        logger.error("DynamoDB get_item failed for SNS rate limit: %s", exc)
        return 0


def _record_alert_sent_mock(email: str) -> int:
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


def _record_alert_sent_dynamodb(email: str) -> int:
    normalized = email.strip().lower()
    if not normalized:
        return 0
    pk = _email_day_pk(normalized)
    ttl = _ttl_end_of_day_plus_one()
    try:
        table = _dynamodb_table()
        response = table.update_item(
            Key={"pk": pk},
            UpdateExpression="ADD alert_count :inc SET #ttl = :ttl",
            ExpressionAttributeNames={"#ttl": "ttl"},
            ExpressionAttributeValues={":inc": 1, ":ttl": ttl},
            ReturnValues="UPDATED_NEW",
        )
        return int(response.get("Attributes", {}).get("alert_count", 1))
    except (ClientError, BotoCoreError) as exc:
        logger.error("DynamoDB update_item failed for SNS rate limit: %s", exc)
        return 0


def get_daily_alert_count(email: str) -> int:
    """Retorna quantos alertas o e-mail recebeu hoje (UTC)."""
    if use_mock_store():
        return _get_daily_alert_count_mock(email)
    return _get_daily_alert_count_dynamodb(email)


def can_send_alert(email: str) -> bool:
    """True se o e-mail ainda não atingiu o limite diário."""
    limit = max(1, int(settings.SNS_MAX_ALERTS_PER_EMAIL_DAY))
    return get_daily_alert_count(email) < limit


def record_alert_sent(email: str) -> int:
    """Incrementa contador diário e retorna o novo total."""
    if use_mock_store():
        return _record_alert_sent_mock(email)
    return _record_alert_sent_dynamodb(email)


def reset_store_for_tests() -> None:
    """Limpa o store local (apenas testes)."""
    path = _store_path()
    if path.exists():
        path.unlink()
