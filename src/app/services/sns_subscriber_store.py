"""Persistência de localização de inscritos SNS (DynamoDB ou JSON local)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
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


def _to_decimal(value: float) -> Decimal:
    return Decimal(str(value))


def _to_float(value: Any) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


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


def _merge_subscriber_record(
    email: str,
    lat: float | None = None,
    lon: float | None = None,
    subscription_arn: str | None = None,
) -> dict[str, Any] | None:
    """Merge new fields into an existing subscriber record (mock or DynamoDB)."""
    normalized = email.strip().lower()
    if not normalized:
        return None

    existing = get_subscriber_record(normalized) or {"email": normalized}
    record: dict[str, Any] = {"email": normalized}

    if lat is not None and lon is not None:
        record["lat"] = float(lat)
        record["lon"] = float(lon)
    elif existing.get("lat") is not None and existing.get("lon") is not None:
        record["lat"] = _to_float(existing["lat"])
        record["lon"] = _to_float(existing["lon"])

    arn = (subscription_arn or existing.get("subscription_arn") or "").strip()
    if arn:
        record["subscription_arn"] = arn

    if "lat" not in record and "subscription_arn" not in record:
        return None

    record["updated_at"] = _now_iso()
    return record


def get_subscriber_record(email: str) -> dict[str, Any] | None:
    """Retorna registro completo do inscrito (lat, lon, subscription_arn) ou None."""
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
        record: dict[str, Any] = {"email": normalized}
        lat = item.get("lat")
        lon = item.get("lon")
        if lat is not None and lon is not None:
            record["lat"] = _to_float(lat)
            record["lon"] = _to_float(lon)
        arn = item.get("subscription_arn")
        if arn:
            record["subscription_arn"] = str(arn).strip()
        if item.get("updated_at"):
            record["updated_at"] = item.get("updated_at")
        return record if len(record) > 1 else None
    except (ClientError, BotoCoreError) as exc:
        logger.error("DynamoDB get_item failed for subscriber %s: %s", normalized, exc)
        return None


def clear_subscription_arn(email: str) -> None:
    """Remove subscription_arn from the subscriber record (keeps lat/lon when present)."""
    normalized = email.strip().lower()
    if not normalized:
        return

    record = get_subscriber_record(normalized)
    if not record or not record.get("subscription_arn"):
        return

    record.pop("subscription_arn", None)
    record["updated_at"] = _now_iso()

    if use_mock_store():
        store = _load_store()
        subscribers = store.setdefault("subscribers", {})
        if not isinstance(subscribers, dict):
            subscribers = {}
            store["subscribers"] = subscribers
        if record.get("lat") is not None and record.get("lon") is not None:
            subscribers[normalized] = record
        else:
            subscribers.pop(normalized, None)
        _save_store(store)
        return

    try:
        table = _dynamodb_table()
        pk = _subscriber_pk(normalized)
        if record.get("lat") is not None and record.get("lon") is not None:
            table.update_item(
                Key={"pk": pk},
                UpdateExpression="REMOVE subscription_arn SET updated_at = :ua",
                ExpressionAttributeValues={":ua": record["updated_at"]},
            )
        else:
            table.delete_item(Key={"pk": pk})
        logger.info("Cleared stale subscription_arn for %s", normalized)
    except (ClientError, BotoCoreError) as exc:
        logger.error("DynamoDB clear subscription_arn failed for %s: %s", normalized, exc)


def save_subscriber_location(
    email: str,
    lat: float | None = None,
    lon: float | None = None,
    subscription_arn: str | None = None,
) -> None:
    """Salva lat/lon e/ou subscription_arn do inscrito (mock JSON ou DynamoDB)."""
    normalized = email.strip().lower()
    if not normalized:
        return

    record = _merge_subscriber_record(
        normalized,
        lat=lat,
        lon=lon,
        subscription_arn=subscription_arn,
    )
    if not record:
        return

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
        item: dict[str, Any] = {
            "pk": _subscriber_pk(normalized),
            "email": normalized,
            "updated_at": record["updated_at"],
        }
        if "lat" in record and "lon" in record:
            item["lat"] = _to_decimal(record["lat"])
            item["lon"] = _to_decimal(record["lon"])
        if record.get("subscription_arn"):
            item["subscription_arn"] = record["subscription_arn"]
        table = _dynamodb_table()
        table.put_item(Item=item)
    except (ClientError, BotoCoreError) as exc:
        logger.error("DynamoDB put_item failed for subscriber %s: %s", normalized, exc)


def get_subscriber_location(email: str) -> dict[str, Any] | None:
    """Retorna dict com lat, lon, updated_at ou None."""
    record = get_subscriber_record(email)
    if not record or record.get("lat") is None or record.get("lon") is None:
        return None
    return {
        "email": record["email"],
        "lat": _to_float(record["lat"]),
        "lon": _to_float(record["lon"]),
        "updated_at": record.get("updated_at"),
        **(
            {"subscription_arn": record["subscription_arn"]}
            if record.get("subscription_arn")
            else {}
        ),
    }


def list_subscribers_with_subscription_arn() -> list[dict[str, Any]]:
    """Lista inscritos com subscription_arn persistido (para merge no publish)."""
    if use_mock_store():
        store = _load_store()
        subscribers = store.get("subscribers", {})
        if not isinstance(subscribers, dict):
            return []
        results: list[dict[str, Any]] = []
        for raw in subscribers.values():
            if not isinstance(raw, dict):
                continue
            arn = (raw.get("subscription_arn") or "").strip()
            email = (raw.get("email") or "").strip().lower()
            if not arn or not email:
                continue
            entry: dict[str, Any] = {"email": email, "subscription_arn": arn}
            if raw.get("lat") is not None and raw.get("lon") is not None:
                entry["lat"] = _to_float(raw["lat"])
                entry["lon"] = _to_float(raw["lon"])
            results.append(entry)
        return results

    results = []
    try:
        table = _dynamodb_table()
        scan_kwargs: dict[str, Any] = {
            "FilterExpression": "begins_with(pk, :prefix) AND attribute_exists(subscription_arn)",
            "ExpressionAttributeValues": {":prefix": "SUBSCRIBER#"},
        }
        while True:
            response = table.scan(**scan_kwargs)
            for item in response.get("Items", []):
                arn = (item.get("subscription_arn") or "").strip()
                email = item.get("email") or str(item.get("pk", "")).replace("SUBSCRIBER#", "", 1)
                email = str(email).strip().lower()
                if not arn or not email:
                    continue
                entry: dict[str, Any] = {"email": email, "subscription_arn": str(arn)}
                lat = item.get("lat")
                lon = item.get("lon")
                if lat is not None and lon is not None:
                    entry["lat"] = _to_float(lat)
                    entry["lon"] = _to_float(lon)
                results.append(entry)
            if not response.get("LastEvaluatedKey"):
                break
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
    except (ClientError, BotoCoreError) as exc:
        logger.error("DynamoDB scan failed for subscribers with ARN: %s", exc)
    return results


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
                entry = {
                    "email": str(email).strip().lower(),
                    "lat": _to_float(lat),
                    "lon": _to_float(lon),
                    "updated_at": item.get("updated_at"),
                }
                arn = item.get("subscription_arn")
                if arn:
                    entry["subscription_arn"] = str(arn).strip()
                results.append(entry)
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
