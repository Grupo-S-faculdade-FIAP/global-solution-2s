"""Adapter DynamoDB para alertas de tempestade.

Implementa StormAlertRepository usando boto3 diretamente.
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

_WEEKDAY_EN = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]


def _build_item(
    *,
    s3_key: str,
    detection_count: int,
    bucket: str,
    alert_id: str | None = None,
    timestamp: datetime | None = None,
    simulated: bool = False,
    classes: list[str] | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    now = timestamp or datetime.now(timezone.utc)
    item: dict[str, Any] = {
        "alert_type": "storm_detection",
        "timestamp": now.isoformat().replace("+00:00", "Z"),
        "alert_id": alert_id or f"alert_{uuid.uuid4().hex[:12]}",
        "date": now.strftime("%Y-%m-%d"),
        "hour": now.hour,
        "weekday": _WEEKDAY_EN[now.weekday()],
        "bucket": bucket,
        "s3_key": s3_key,
        "detection_count": detection_count,
        "classes": classes or ["storm"],
        "simulated": simulated,
    }
    if confidence is not None:
        item["confidence"] = round(float(confidence), 4)
    return item


def _table():
    dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    return dynamodb.Table(settings.DYNAMODB_TABLE_ALERTS)


class DynamoDBStormAlertRepository:
    """Adapter de produção — persiste alertas no DynamoDB."""

    def save(
        self,
        *,
        s3_key: str,
        detection_count: int,
        bucket: str,
        alert_id: str | None = None,
        simulated: bool = False,
        classes: list[str] | None = None,
        confidence: float | None = None,
    ) -> dict[str, Any]:
        item = _build_item(
            s3_key=s3_key,
            detection_count=detection_count,
            bucket=bucket,
            alert_id=alert_id,
            simulated=simulated,
            classes=classes,
            confidence=confidence,
        )
        try:
            _table().put_item(Item=item)
            logger.info(
                "Alert saved to DynamoDB %s: %s",
                settings.DYNAMODB_TABLE_ALERTS,
                item.get("alert_id"),
            )
        except (ClientError, BotoCoreError) as exc:
            logger.error("DynamoDB put_item failed: %s", exc)
            raise
        return item

    def list_since_hours(self, hours: int) -> list[dict[str, Any]]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_iso = cutoff.isoformat().replace("+00:00", "Z")
        items: list[dict[str, Any]] = []
        scan_kwargs: dict[str, Any] = {
            "FilterExpression": "alert_type = :atype AND #ts >= :cutoff",
            "ExpressionAttributeNames": {"#ts": "timestamp"},
            "ExpressionAttributeValues": {
                ":atype": "storm_detection",
                ":cutoff": cutoff_iso,
            },
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
            logger.error("DynamoDB scan failed: %s", exc)
            raise
        items.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
        return [i for i in items if self._parse_ts(i) and self._parse_ts(i) >= cutoff]

    def list_since_days(self, days: int) -> list[dict[str, Any]]:
        return self.list_since_hours(days * 24)

    def ensure_seeded(self) -> None:
        pass  # no-op: DynamoDB não precisa de seed

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
