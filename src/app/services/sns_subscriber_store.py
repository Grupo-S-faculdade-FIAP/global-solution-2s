"""Persistência de localização de inscritos SNS (DynamoDB ou JSON local)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.services.sns_rate_limit import is_lambda_runtime, use_mock_store

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORE_PATH = PROJECT_ROOT / "data" / "demo" / "sns_subscribers.json"


def _store_path() -> Path:
    raw = (settings.SNS_SUBSCRIBER_STORE_PATH or "").strip()
    return Path(raw) if raw else DEFAULT_STORE_PATH


def _subscriber_pk(email: str) -> str:
    return f"SUBSCRIBER#{email.strip().lower()}"


def _dynamodb_table():
    dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    return dynamodb.Table(settings.DYNAMODB_TABLE_SNS_RATE_LIMIT)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_store() -> dict[str, Any]:
    path = _store_path()
    if not path.exists():
        return {"subscribers": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("subscribers"), dict):
            return data
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read SNS subscriber store %s: %s", path, exc)
    return {"subscribers": {}}


def _save_store(data: dict[str, Any]) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def save_subscriber_location(email: str, lat: float, lon: float) -> None:
    """Salva lat/lon do inscrito (mock JSON ou DynamoDB)."""
    normalized = email.strip().lower()
    if not normalized:
        return

    record = {
        "email": normalized,
        "lat": float(lat),
        "lon": float(lon),
        "updated_at": _now_iso(),
    }

    if use_mock_store():
        store = _load_store()
        subscribers = store.setdefault("subscribers", {})
        if not isinstance(subscribers, dict):
            subscribers = {}
            store["subscribers"] = subscribers
        subscribers[normalized] = record
        _save_store(store)
        return

    try:
        table = _dynamodb_table()
        table.put_item(
            Item={
                "pk": _subscriber_pk(normalized),
                "email": normalized,
                "lat": record["lat"],
                "lon": record["lon"],
                "updated_at": record["updated_at"],
            }
        )
    except (ClientError, BotoCoreError) as exc:
        logger.error("DynamoDB put_item failed for subscriber %s: %s", normalized, exc)


def get_subscriber_location(email: str) -> dict[str, Any] | None:
    """Retorna dict com lat, lon, updated_at ou None."""
    normalized = email.strip().lower()
    if not normalized:
        return None

    if use_mock_store():
        store = _load_store()
        subscribers = store.get("subscribers", {})
        if not isinstance(subscribers, dict):
            return None
        raw = subscribers.get(normalized)
        return dict(raw) if isinstance(raw, dict) else None

    try:
        table = _dynamodb_table()
        response = table.get_item(Key={"pk": _subscriber_pk(normalized)})
        item = response.get("Item", {})
        if not item:
            return None
        lat = item.get("lat")
        lon = item.get("lon")
        if lat is None or lon is None:
            return None
        return {
            "email": normalized,
            "lat": float(lat),
            "lon": float(lon),
            "updated_at": item.get("updated_at"),
        }
    except (ClientError, BotoCoreError) as exc:
        logger.error("DynamoDB get_item failed for subscriber %s: %s", normalized, exc)
        return None


def list_subscriber_locations() -> list[dict[str, Any]]:
    """Lista todas as localizações salvas (scan mock ou DynamoDB)."""
    if use_mock_store():
        store = _load_store()
        subscribers = store.get("subscribers", {})
        if not isinstance(subscribers, dict):
            return []
        return [dict(v) for v in subscribers.values() if isinstance(v, dict)]

    results: list[dict[str, Any]] = []
    try:
        table = _dynamodb_table()
        scan_kwargs: dict[str, Any] = {
            "FilterExpression": "begins_with(pk, :prefix)",
            "ExpressionAttributeValues": {":prefix": "SUBSCRIBER#"},
        }
        while True:
            response = table.scan(**scan_kwargs)
            for item in response.get("Items", []):
                lat = item.get("lat")
                lon = item.get("lon")
                email = item.get("email") or str(item.get("pk", "")).replace("SUBSCRIBER#", "", 1)
                if lat is None or lon is None or not email:
                    continue
                results.append(
                    {
                        "email": str(email).strip().lower(),
                        "lat": float(lat),
                        "lon": float(lon),
                        "updated_at": item.get("updated_at"),
                    }
                )
            if not response.get("LastEvaluatedKey"):
                break
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
    except (ClientError, BotoCoreError) as exc:
        logger.error("DynamoDB scan failed for subscribers: %s", exc)
    return results


def reset_store_for_tests() -> None:
    """Limpa store local (apenas testes)."""
    path = _store_path()
    if path.exists():
        path.unlink()
