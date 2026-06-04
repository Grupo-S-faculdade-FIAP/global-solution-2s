"""Tests for extended alert analytics (daily, heatmap, summary)."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.alerts_analytics import AlertAnalyticsService


@pytest.fixture
def svc(monkeypatch):
    monkeypatch.setattr(
        "app.services.alerts_analytics.use_mock_store",
        lambda: True,
    )
    return AlertAnalyticsService()


@patch.object(AlertAnalyticsService, "_scan_recent_alerts")
def test_daily_alerts_counts_by_date(mock_scan, svc):
    mock_scan.return_value = [
        {"date": "2026-06-01", "hour": 14, "weekday": "Monday"},
        {"date": "2026-06-01", "hour": 15, "weekday": "Monday"},
        {"timestamp": "2026-06-02T10:00:00Z", "hour": 10, "weekday": "Tuesday"},
    ]
    data = svc.daily_alerts(days=30)
    assert isinstance(data, dict)
    assert sum(data.values()) >= 2


@patch.object(AlertAnalyticsService, "_scan_recent_alerts")
def test_heatmap_structure(mock_scan, svc):
    mock_scan.return_value = [
        {"hour": 14, "weekday": "Thursday"},
        {"hour": 14, "weekday": "Thursday"},
    ]
    cells = svc.heatmap_alerts(days=7)
    assert len(cells) == 7 * 24
    thu_14 = next(c for c in cells if c["x"] == 14 and c["y"] == 3)
    assert thu_14["v"] == 2


@patch.object(AlertAnalyticsService, "_scan_recent_alerts")
def test_dashboard_summary_keys(mock_scan, svc):
    mock_scan.return_value = [{"hour": 15, "weekday": "Friday", "date": "2026-06-04"}]
    out = svc.dashboard_summary(days=30)
    assert "alerts_by_weekday" in out
    assert "trend_30_days" in out
    assert "heatmap" in out
    assert "kpis" in out
