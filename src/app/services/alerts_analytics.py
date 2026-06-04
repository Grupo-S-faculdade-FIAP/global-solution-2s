"""Services for aggregating storm alerts for dashboard analytics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.services.storm_alerts_store import list_alerts_since_days, use_mock_store


WEEKDAYS_PT = [
    "Segunda",
    "Terça",
    "Quarta",
    "Quinta",
    "Sexta",
    "Sábado",
    "Domingo",
]

WEEKDAY_EN_TO_PT = {
    "monday": "Segunda",
    "tuesday": "Terça",
    "wednesday": "Quarta",
    "thursday": "Quinta",
    "friday": "Sexta",
    "saturday": "Sábado",
    "sunday": "Domingo",
}


def _to_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _base_weekly() -> dict[str, int]:
    return {day: 0 for day in WEEKDAYS_PT}


def _base_hourly() -> dict[str, int]:
    return {f"{hour:02d}h": 0 for hour in range(24)}


class AlertAnalyticsService:
    """Aggregate storm alert records from DynamoDB into chart-ready buckets."""

    def __init__(self) -> None:
        self._table = None
        if not use_mock_store():
            self._dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
            self._table = self._dynamodb.Table(settings.DYNAMODB_TABLE_ALERTS)

    def _scan_recent_alerts(self, days: int = 30) -> list[dict[str, Any]]:
        if use_mock_store():
            return list_alerts_since_days(days)

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
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
                page = self._table.scan(**scan_kwargs)
                items.extend(page.get("Items", []))
                last_key = page.get("LastEvaluatedKey")
                if not last_key:
                    break
                scan_kwargs["ExclusiveStartKey"] = last_key
        except (ClientError, BotoCoreError):
            return list_alerts_since_days(days)

        return items

    def weekly_alerts(self, days: int = 30) -> dict[str, int]:
        data = _base_weekly()
        for item in self._scan_recent_alerts(days=days):
            weekday_raw = str(item.get("weekday", "")).strip().lower()
            day_pt = WEEKDAY_EN_TO_PT.get(weekday_raw)
            if day_pt:
                data[day_pt] += 1
        return data

    def hourly_alerts(self, days: int = 30) -> dict[str, int]:
        data = _base_hourly()
        for item in self._scan_recent_alerts(days=days):
            hour = _to_int(item.get("hour"), default=-1)
            if 0 <= hour <= 23:
                data[f"{hour:02d}h"] += 1
        return data
