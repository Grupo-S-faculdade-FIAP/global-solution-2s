"""Adapter DynamoDB para leituras IoT.

Implementa IoTReadingRepository usando boto3.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


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


def _table():
    dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    return dynamodb.Table(settings.DYNAMODB_IOT_TABLE)


class DynamoDBIoTReadingRepository:
    """Adapter de produção — persiste leituras IoT no DynamoDB."""

    def save(
        self,
        *,
        device_id: str,
        cidade: str,
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
        try:
            _table().put_item(Item=item)
            logger.info(
                "IoT reading saved to DynamoDB %s: %s",
                settings.DYNAMODB_IOT_TABLE,
                item.get("reading_id"),
            )
        except (ClientError, BotoCoreError) as exc:
            logger.error("DynamoDB put_item (iot) failed: %s", exc)
            raise
        return item

    def list_since_hours(self, hours: int) -> list[dict[str, Any]]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_iso = cutoff.isoformat().replace("+00:00", "Z")
        items: list[dict[str, Any]] = []
        scan_kwargs: dict[str, Any] = {
            "FilterExpression": "#ts >= :cutoff",
            "ExpressionAttributeNames": {"#ts": "timestamp"},
            "ExpressionAttributeValues": {":cutoff": cutoff_iso},
        }
        try:
            while True:
                page = _table().scan(**scan_kwargs)
                items.extend(page.get("Items", []))
                last_key = page.get("LastEvaluatedKey")
                if not last_key:
                    break
                scan_kwargs["ExclusiveStartKey"] = last_key
        except (ClientError, BotoCoreError) as exc:
            logger.error("DynamoDB scan (iot) failed: %s", exc)
            raise
        items.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
        cutoff_dt = cutoff
        return [i for i in items if self._parse_ts(i) and self._parse_ts(i) >= cutoff_dt]

    def ensure_seeded(self) -> None:
        pass  # no-op para DynamoDB

    @staticmethod
    def _parse_ts(item: dict[str, Any]) -> datetime | None:
        raw = str(item.get("timestamp", ""))
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
