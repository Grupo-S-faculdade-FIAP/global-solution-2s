"""Localização canônica da API pública de BFF handlers.

A implementação real está em dashboard/bff_handlers.py para preservar
backward compat com testes que patcham módulos de dashboard.
Este módulo re-exporta tudo para que novos imports usem o caminho canônico.
"""

from dashboard.bff_handlers import (  # noqa: F401
    DEMO_MODE,
    STORM_DETECTOR,
    WEEKLY_ALERTS,
    HOURLY_ALERTS,
    DAILY_TREND,
    HEATMAP,
    SUMMARY,
    dashboard_config,
    alerts_weekly,
    alerts_hourly,
    alerts_daily,
    alerts_heatmap,
    alerts_summary,
    dashboard_summary,
    weather_current,
    risk_forecast,
    storms_recent,
    map_overlay,
    detector_status,
    ml_agricultural_risk,
    nasa_capturas,
    cv_status,
    detect_storm,
    batch_detect_storms,
    simulate_storm_detection,
    iot_latest,
    iot_status,
    detect_storm_sample,
)
