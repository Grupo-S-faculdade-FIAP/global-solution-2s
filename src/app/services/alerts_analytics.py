"""Services for aggregating storm alerts for dashboard analytics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from app.services.storm_alerts_store import list_alerts_since_days


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

# Índice 0=Segunda … 6=Domingo (para heatmap y)
WEEKDAY_EN_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
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
    """Aggregate storm alert records via storm_alerts_store into chart-ready buckets."""

    def _scan_recent_alerts(self, days: int = 30) -> list[dict[str, Any]]:
        return list_alerts_since_days(days)

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

    def daily_alerts(self, days: int = 30) -> dict[str, int]:
        """Contagem por dia (label dd/mm) nos últimos N dias."""
        today = datetime.now(timezone.utc).date()
        buckets: dict[str, int] = {}
        for i in range(days):
            d = today - timedelta(days=(days - 1 - i))
            buckets[d.strftime("%d/%m")] = 0

        for item in self._scan_recent_alerts(days=days):
            date_raw = str(item.get("date", "")).strip()
            if date_raw:
                try:
                    dt = datetime.strptime(date_raw, "%Y-%m-%d").date()
                    key = dt.strftime("%d/%m")
                    if key in buckets:
                        buckets[key] += 1
                    continue
                except ValueError:
                    pass
            ts_raw = str(item.get("timestamp", "")).replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(ts_raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                key = dt.strftime("%d/%m")
                if key in buckets:
                    buckets[key] += 1
            except ValueError:
                continue

        return buckets

    def heatmap_alerts(self, days: int = 30) -> list[dict[str, int]]:
        """Células {x: hora 0-23, y: dia 0-6 Seg-Dom, v: contagem}."""
        grid = [[0 for _ in range(24)] for _ in range(7)]
        for item in self._scan_recent_alerts(days=days):
            hour = _to_int(item.get("hour"), default=-1)
            weekday_raw = str(item.get("weekday", "")).strip().lower()
            day_idx = WEEKDAY_EN_INDEX.get(weekday_raw, -1)
            if 0 <= hour <= 23 and 0 <= day_idx <= 6:
                grid[day_idx][hour] += 1

        cells: list[dict[str, int]] = []
        for y in range(7):
            for x in range(24):
                cells.append({"x": x, "y": y, "v": grid[y][x]})
        return cells

    def summary(self, days: int = 30) -> dict[str, Any]:
        weekly = self.weekly_alerts(days=days)
        hourly = self.hourly_alerts(days=days)
        daily = self.daily_alerts(days=days)
        total = sum(daily.values())
        peak_day = max(weekly, key=weekly.get) if weekly else "—"
        peak_hour = max(hourly, key=hourly.get) if hourly else "—"
        return {
            "total_30d": total,
            "daily_avg": round(total / max(days, 1), 1),
            "peak_day": peak_day,
            "peak_hour": peak_hour,
        }

    def dashboard_summary(self, days: int = 30) -> dict[str, Any]:
        return {
            "alerts_by_weekday": self.weekly_alerts(days=days),
            "alerts_by_hour": self.hourly_alerts(days=days),
            "trend_30_days": self.daily_alerts(days=days),
            "heatmap": self.heatmap_alerts(days=days),
            "kpis": self.summary(days=days),
        }
