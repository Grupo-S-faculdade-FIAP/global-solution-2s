"""Rotas /api/* do dashboard no FastAPI (prioridade sobre o mount Flask)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

from app.interfaces.http.bff import handlers as bff

router = APIRouter(prefix="/api", tags=["Dashboard BFF"])

_BFF_TIMEOUT_SLOW = 30


def _bff_response(payload: tuple[Any, str, int]) -> JSONResponse:
    data, source, status = payload
    headers = {"X-Data-Source": source, "Cache-Control": "max-age=300, public"}
    if status != 200:
        headers["Cache-Control"] = "no-store"
    return JSONResponse(content=data, status_code=status, headers=headers)


@router.get("/dashboard/config")
def api_dashboard_config() -> JSONResponse:
    data, source, status = bff.dashboard_config()
    return JSONResponse(
        content=data,
        status_code=status,
        headers={"X-Data-Source": source},
    )


@router.get("/alerts/weekly")
def api_alerts_weekly(days: int = Query(30, ge=1, le=365)) -> JSONResponse:
    return _bff_response(bff.alerts_weekly(days))


@router.get("/alerts/hourly")
def api_alerts_hourly(days: int = Query(30, ge=1, le=365)) -> JSONResponse:
    return _bff_response(bff.alerts_hourly(days))


@router.get("/alerts/daily")
def api_alerts_daily(days: int = Query(30, ge=1, le=365)) -> JSONResponse:
    return _bff_response(bff.alerts_daily(days))


@router.get("/alerts/heatmap")
def api_alerts_heatmap(days: int = Query(30, ge=1, le=365)) -> JSONResponse:
    return _bff_response(bff.alerts_heatmap(days))


@router.get("/alerts/summary")
def api_alerts_summary(days: int = Query(30, ge=1, le=365)) -> JSONResponse:
    return _bff_response(bff.alerts_summary(days))


@router.get("/dashboard/summary")
def api_dashboard_summary(days: int = Query(30, ge=1, le=365)) -> JSONResponse:
    return _bff_response(bff.dashboard_summary(days))


@router.get("/weather/current")
def api_weather_current(
    lat: float = Query(-23.55, ge=-90, le=90),
    lon: float = Query(-46.63, ge=-180, le=180),
) -> JSONResponse:
    return _bff_response(bff.weather_current(lat, lon))


@router.get("/risk/forecast")
def api_risk_forecast(
    lat: float = Query(-23.55, ge=-90, le=90),
    lon: float = Query(-46.63, ge=-180, le=180),
) -> JSONResponse:
    return _bff_response(bff.risk_forecast(lat, lon))


@router.get("/storms/recent")
def api_storms_recent(hours: int = Query(24, ge=1, le=720)) -> JSONResponse:
    return _bff_response(bff.storms_recent(hours))


@router.get("/map/overlay")
def api_map_overlay(bbox: str = Query("-25,-50,-20,-40")) -> JSONResponse:
    return _bff_response(bff.map_overlay(bbox))


@router.get("/storms/detector-status")
def api_detector_status() -> JSONResponse:
    data, source, status = bff.detector_status()
    return JSONResponse(content=data, status_code=status, headers={"X-Data-Source": source})


@router.get("/ml/agricultural-risk")
def api_ml_agricultural_risk(
    temperatura: float = Query(25.0),
    umidade: float = Query(60.0),
    precipitacao: float = Query(0.0),
    vento_kmh: float = Query(10.0),
) -> JSONResponse:
    data, _, status = bff.ml_agricultural_risk(
        temperatura, umidade, precipitacao, vento_kmh
    )
    return JSONResponse(content=data, status_code=status)


@router.get("/nasa/capturas")
def api_nasa_capturas(limite: int = Query(12, ge=1, le=100)) -> JSONResponse:
    data, source, status = bff.nasa_capturas(limite)
    return JSONResponse(content=data, status_code=status, headers={"X-Data-Source": source})


@router.get("/cv/status")
def api_cv_status() -> JSONResponse:
    data, _, status = bff.cv_status()
    return JSONResponse(content=data, status_code=status)


@router.post("/storms/detect")
def api_detect_storm(body: dict = Body(default_factory=dict)) -> JSONResponse:
    data, _, status = bff.detect_storm(body)
    return JSONResponse(content=data, status_code=status)


@router.post("/storms/batch-detect")
def api_batch_detect(body: dict = Body(default_factory=dict)) -> JSONResponse:
    data, _, status = bff.batch_detect_storms(body)
    return JSONResponse(content=data, status_code=status)


@router.get("/alerts/sns/status")
def api_sns_status() -> JSONResponse:
    data, source, status = bff.sns_alerts_status()
    return JSONResponse(content=data, status_code=status, headers={"X-Data-Source": source})


@router.post("/alerts/subscribe")
def api_sns_subscribe(body: dict = Body(default_factory=dict)) -> JSONResponse:
    data, source, status = bff.sns_subscribe(body)
    return JSONResponse(content=data, status_code=status, headers={"X-Data-Source": source})


@router.post("/alerts/simulate-detection")
def api_simulate_detection(body: Optional[dict] = Body(default=None)) -> JSONResponse:
    data, _, status = bff.simulate_storm_detection(body or {})
    return JSONResponse(content=data, status_code=status)


@router.post("/storms/detect-sample")
def api_detect_sample() -> JSONResponse:
    data, _, status = bff.detect_storm_sample()
    return JSONResponse(content=data, status_code=status)


@router.get("/iot/status")
def api_iot_status() -> JSONResponse:
    data, _, status = bff.iot_status()
    return JSONResponse(content=data, status_code=status)


@router.get("/iot/readings/latest")
def api_iot_readings_latest(hours: int = Query(24, ge=1, le=720)) -> JSONResponse:
    data, source, status = bff.iot_latest(hours)
    headers = {"X-Data-Source": source}
    return JSONResponse(content=data, status_code=status, headers=headers)
