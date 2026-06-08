"""Lógica compartilhada das rotas /api/* (FastAPI BFF + Flask)."""

from __future__ import annotations

import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from dashboard.bff_backend import backend_get, backend_post, use_inprocess_backend

_BFF_TIMEOUT = 5
_BFF_TIMEOUT_SLOW = 30


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name, "true" if default else "false").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _demo_mode() -> bool:
    try:
        from app.core.config import settings
        return bool(settings.DEMO_MODE)
    except ImportError:
        return _env_bool("DEMO_MODE", default=True)


def _is_demo() -> bool:
    """Avalia DEMO_MODE em tempo de execução (não cached) para refletir monkeypatch em testes."""
    return _demo_mode()


DEMO_MODE = _demo_mode()
DEFAULT_WEATHER_LAT = -23.55
DEFAULT_WEATHER_LON = -46.63

random.seed(42)

WEEKLY_ALERTS = {
    "Segunda": 5,
    "Terça": 12,
    "Quarta": 8,
    "Quinta": 15,
    "Sexta": 10,
    "Sábado": 4,
    "Domingo": 3,
}

HOURLY_ALERTS = {
    "00h": 1, "01h": 0, "02h": 1, "03h": 0, "04h": 0,
    "05h": 1, "06h": 2, "07h": 3, "08h": 4, "09h": 5,
    "10h": 4, "11h": 6, "12h": 7, "13h": 9, "14h": 14,
    "15h": 16, "16h": 13, "17h": 10, "18h": 8, "19h": 6,
    "20h": 5, "21h": 4, "22h": 3, "23h": 2,
}

_base_date = datetime(2026, 5, 3)
_weekday_mult = [0.6, 1.2, 0.9, 1.5, 1.1, 0.5, 0.4]
DAILY_TREND: dict[str, int] = {}
for _i in range(30):
    _day = _base_date + timedelta(days=_i)
    _base_val = 10 * _weekday_mult[_day.weekday()]
    DAILY_TREND[_day.strftime("%d/%m")] = max(0, round(random.gauss(_base_val, 2), 0))

_hour_vals = list(HOURLY_ALERTS.values())
HEATMAP: list[dict[str, int]] = []
for _d in range(7):
    for _h in range(24):
        _val = max(0, int(round(_hour_vals[_h] * _weekday_mult[_d] + random.gauss(0, 0.4))))
        HEATMAP.append({"x": _h, "y": _d, "v": _val})

_total = int(sum(DAILY_TREND.values()))
SUMMARY = {
    "total_30d": _total,
    "daily_avg": round(_total / 30, 1),
    "peak_day": max(WEEKLY_ALERTS, key=WEEKLY_ALERTS.get),
    "peak_hour": max(HOURLY_ALERTS, key=HOURLY_ALERTS.get),
}

def _demo_weather(lat: float, lon: float) -> dict[str, Any]:
    """Fallback demo que varia com lat/lon para a UI refletir troca de região."""
    seed = int(abs(lat * 100) + abs(lon * 100)) % 1000
    return {
        "temperature": round(18.0 + (seed % 14) + abs(lat) % 6 * 0.4, 1),
        "humidity": round(52.0 + (seed % 38), 1),
        "pressure": round(1008.0 + (seed % 12), 1),
        "wind_speed": round(1.8 + (seed % 50) / 10.0, 1),
        "wind_direction": float((seed * 37) % 360),
        "precipitation": round((seed % 30) / 10.0, 1),
        "timestamp": datetime.now().isoformat(),
    }


def _demo_risk(lat: float, lon: float) -> dict[str, Any]:
    seed = int(abs(lat * 100) + abs(lon * 100)) % 1000
    score = round(0.15 + (seed % 70) / 100.0, 2)
    if score >= 0.65:
        category = "HIGH"
        rec = "Demonstração: risco elevado para a região selecionada."
    elif score >= 0.4:
        category = "MEDIUM"
        rec = "Demonstração: atenção moderada — monitore a previsão."
    else:
        category = "LOW"
        rec = "Demonstração: condições estáveis na região selecionada."
    return {
        "risk_score": score,
        "risk_category": category,
        "recommendation": rec,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEMO_STORMS_PATH = _PROJECT_ROOT / "data" / "demo" / "storm_alerts.json"

# Lazy — evita carregar torch/YOLO na importação do módulo (conflito com LightGBM em testes)
_storm_detector = None
_storm_detector_loaded = False
STORM_DETECTOR = None  # legado; use _get_storm_detector()

_weather_service = None
_risk_service = None
_storm_query_service = None
_agri_risk_model = None


def _skip_yolo_load() -> bool:
    """pytest/E2E: evita importar torch no subprocesso uvicorn."""
    return os.environ.get("RISK_SKIP_YOLO", "").strip().lower() in ("1", "true", "yes", "on")


def _get_storm_detector():
    """Carrega StormDetector sob demanda (singleton)."""
    global _storm_detector, _storm_detector_loaded, STORM_DETECTOR
    if _storm_detector_loaded:
        return _storm_detector
    _storm_detector_loaded = True
    if _skip_yolo_load():
        return None
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from app.core.config import settings
        from app.services.storm_detector import StormDetector

        _src_root = Path(__file__).resolve().parent.parent
        yolo_path = _src_root / "models" / "weights" / "best.pt"
        if yolo_path.exists():
            _storm_detector = StormDetector(
                model_path=yolo_path,
                confidence_threshold=settings.YOLO_CONFIDENCE_THRESHOLD,
                device="cpu",
            )
            STORM_DETECTOR = _storm_detector
    except Exception:
        _storm_detector = None
    return _storm_detector


def _get_weather_service():
    global _weather_service
    if _weather_service is None:
        from app.services.weather_service import WeatherService

        _weather_service = WeatherService()
    return _weather_service


def _get_risk_service():
    global _risk_service
    if _risk_service is None:
        from app.services.risk_assessment import RiskAssessmentService

        _risk_service = RiskAssessmentService()
    return _risk_service


def _get_storm_query_service():
    global _storm_query_service
    if _storm_query_service is None:
        from app.services.storm_alerts_query import StormAlertsQueryService

        _storm_query_service = StormAlertsQueryService()
    return _storm_query_service


def _get_agri_risk_model():
    global _agri_risk_model
    if _agri_risk_model is None:
        from app.services.agri_risk_model import AgriRiskModel

        _agri_risk_model = AgriRiskModel()
    return _agri_risk_model


def _parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    parts = [float(x) for x in bbox.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox must have 4 values")
    return parts[0], parts[1], parts[2], parts[3]


def _ok(data: Any, source: str = "live") -> tuple[Any, str, int]:
    return data, source, 200


def _err(message: str, status: int = 503) -> tuple[Any, str, int]:
    return {"error": message}, "unavailable", status


def _proxy_get(
    path: str,
    params: Optional[dict] = None,
    fallback: Any = None,
    timeout: int = _BFF_TIMEOUT,
) -> tuple[Any, str, int]:
    status, body = backend_get(path, params=params, timeout=timeout)
    if status == 200 and isinstance(body, (dict, list)):
        return _ok(body, "live")
    if not DEMO_MODE or fallback is None:
        return _err("Backend offline", 503)
    return _ok(fallback, "demo")


def _demo_storms_recent(hours: int = 24) -> list[dict[str, Any]]:
    if not _DEMO_STORMS_PATH.exists():
        return []
    try:
        items = json.loads(_DEMO_STORMS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(items, list):
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    out: list[dict[str, Any]] = []
    for item in items:
        ts_raw = item.get("timestamp")
        if not ts_raw:
            continue
        try:
            ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts < cutoff:
            continue
        out.append({
            "detection_id": item.get("alert_id", ""),
            "confidence": 0.82,
            "latitude": item.get("latitude", DEFAULT_WEATHER_LAT),
            "longitude": item.get("longitude", DEFAULT_WEATHER_LON),
            "timestamp": ts_raw,
            "detection_count": item.get("detection_count", 1),
            "s3_key": item.get("s3_key", ""),
        })
    return out


def dashboard_config() -> tuple[Any, str, int]:
    return _ok({
        "demo_mode": DEMO_MODE,
        "storage": "dynamodb",
        "default_lat": DEFAULT_WEATHER_LAT,
        "default_lon": DEFAULT_WEATHER_LON,
    }, "live")


def alerts_weekly(days: int = 30) -> tuple[Any, str, int]:
    return _proxy_get("/alerts/weekly", {"days": days}, fallback=WEEKLY_ALERTS)


def alerts_hourly(days: int = 30) -> tuple[Any, str, int]:
    return _proxy_get("/alerts/hourly", {"days": days}, fallback=HOURLY_ALERTS)


def alerts_daily(days: int = 30) -> tuple[Any, str, int]:
    return _proxy_get("/alerts/daily", {"days": days}, fallback=DAILY_TREND)


def alerts_heatmap(days: int = 30) -> tuple[Any, str, int]:
    return _proxy_get("/alerts/heatmap", {"days": days}, fallback=HEATMAP)


def alerts_summary(days: int = 30) -> tuple[Any, str, int]:
    return _proxy_get("/alerts/summary", {"days": days}, fallback=SUMMARY)


def dashboard_summary(days: int = 30) -> tuple[Any, str, int]:
    fallback = {
        "alerts_by_weekday": WEEKLY_ALERTS,
        "alerts_by_hour": HOURLY_ALERTS,
        "trend_30_days": DAILY_TREND,
        "heatmap": HEATMAP,
        "kpis": SUMMARY,
    }
    return _proxy_get("/dashboard/summary", {"days": days}, fallback=fallback)


def weather_current(lat: float, lon: float) -> tuple[Any, str, int]:
    if use_inprocess_backend():
        try:
            data = _get_weather_service().get_current(lat, lon)
            return _ok(
                {
                    "temperature": data["temperature"],
                    "humidity": data["humidity"],
                    "pressure": data["pressure"],
                    "wind_speed": data["wind_speed"],
                    "wind_direction": data["wind_direction"],
                    "precipitation": data["precipitation"],
                    "timestamp": data["timestamp"],
                },
                "live",
            )
        except Exception:
            pass
    status, body = backend_get(
        "/weather/current", params={"lat": lat, "lon": lon}, timeout=_BFF_TIMEOUT
    )
    if status == 200 and isinstance(body, dict):
        return _ok(body, "live")
    return _ok(_demo_weather(lat, lon), "fallback")


def risk_forecast(lat: float, lon: float) -> tuple[Any, str, int]:
    if use_inprocess_backend():
        try:
            result = _get_risk_service().calculate_risk(lat, lon)
            return _ok(
                {
                    "risk_score": result.score,
                    "risk_category": result.category,
                    "recommendation": result.recommendation,
                    "timestamp": result.timestamp,
                    "detalhes": result.detalhes,
                },
                "live",
            )
        except Exception:
            pass
    status, body = backend_get(
        "/risk/forecast",
        params={"lat": lat, "lon": lon},
        timeout=_BFF_TIMEOUT_SLOW,
    )
    if status == 200 and isinstance(body, dict):
        return _ok(body, "live")
    return _ok(_demo_risk(lat, lon), "fallback")


def _geojson_features_to_dicts(features: list[Any]) -> list[dict[str, Any]]:
    """Serializa GeoJSONFeature (Pydantic) para dict — JSONResponse não aceita modelos."""
    out: list[dict[str, Any]] = []
    for feature in features:
        if hasattr(feature, "model_dump"):
            out.append(feature.model_dump())
        elif hasattr(feature, "dict"):
            out.append(feature.dict())
        elif isinstance(feature, dict):
            out.append(feature)
    return out


def map_overlay(bbox: str) -> tuple[Any, str, int]:
    if use_inprocess_backend():
        try:
            south, west, north, east = _parse_bbox(bbox)
            if south <= north and west <= east:
                features = _get_storm_query_service().map_overlay_features(
                    south, west, north, east, hours=24 * 7
                )
                return _ok(
                    {
                        "type": "FeatureCollection",
                        "features": _geojson_features_to_dicts(features),
                    },
                    "live",
                )
        except Exception:
            pass
    status, body = backend_get("/map/overlay", params={"bbox": bbox})
    if status == 200 and isinstance(body, dict):
        return _ok(body, "live")
    return _ok({"type": "FeatureCollection", "features": []}, "fallback")


def storms_recent(hours: int = 24) -> tuple[Any, str, int]:
    status, body = backend_get("/storms/recent", params={"hours": hours})
    if status == 200 and isinstance(body, list):
        return _ok(body, "live")
    if DEMO_MODE:
        return _ok(_demo_storms_recent(hours), "demo")
    return _err("Failed to fetch storm data", status if status != 200 else 503)


def detector_status() -> tuple[Any, str, int]:
    from app.core.config import settings

    model_path = Path(__file__).resolve().parent.parent / "models" / "weights" / "best.pt"
    return _ok({
        "available": _storm_detector is not None,
        "model_exists": model_path.exists(),
        "confidence_threshold": settings.YOLO_CONFIDENCE_THRESHOLD,
        "model_path": str(model_path),
    }, "live")


def ml_agricultural_risk(
    temperatura: float,
    umidade: float,
    precipitacao: float,
    vento_kmh: float,
) -> tuple[Any, str, int]:
    if use_inprocess_backend():
        try:
            from app.services.risk_assessment import RECOMENDACOES

            result = _get_agri_risk_model().predict_detalhado(
                temperatura=temperatura,
                umidade=umidade,
                precipitacao=precipitacao,
                vento_kmh=vento_kmh,
            )
            result["recomendacao"] = RECOMENDACOES[result["classe"]]
            return _ok(result, "live")
        except Exception:
            pass
    status, body = backend_get(
        "/ml/predict/agricultural-risk",
        params={
            "temperatura": temperatura,
            "umidade": umidade,
            "precipitacao": precipitacao,
            "vento_kmh": vento_kmh,
        },
        timeout=10,
    )
    if status == 200 and isinstance(body, dict):
        return _ok(body, "live")
    return _err("Backend error", status if status != 200 else 503)


def nasa_capturas(limite: int = 12) -> tuple[Any, str, int]:
    status, body = backend_get("/cv/nasa/capturas", params={"limite": limite})
    if status == 200 and isinstance(body, dict):
        return _ok(body, "live")
    return _ok({"total": 0, "capturas": []}, "live")


def cv_status() -> tuple[Any, str, int]:
    status, body = backend_get("/cv/status")
    if status == 200 and isinstance(body, dict):
        return _ok(body, "live")
    return _ok({"status": "unavailable"}, "live")


def detect_storm(body: dict) -> tuple[Any, str, int]:
    detector = _get_storm_detector()
    if not detector:
        return {
            "success": False,
            "error": "Storm Detector não está disponível. Treine o modelo primeiro.",
            "message": "Modelo YOLO não encontrado",
        }, "live", 503

    image_url = body.get("image_url")
    if not image_url:
        return {"success": False, "error": "Campo obrigatório 'image_url' não fornecido"}, "live", 400

    try:
        result = detector.predict(image_url)
        return _ok({
            "success": True,
            "num_detections": result.num_detections,
            "detections": [
                {
                    "x": d.x,
                    "y": d.y,
                    "width": d.width,
                    "height": d.height,
                    "confidence": d.confidence,
                    "class_name": d.class_name,
                }
                for d in result.detections
            ],
            "has_storm": result.has_storm,
            "average_confidence": result.average_confidence,
            "timestamp": result.timestamp,
            "message": (
                f"Detectadas {result.num_detections} tempestades"
                if result.has_storm
                else "Nenhuma tempestade detectada"
            ),
        }, "live")
    except Exception as exc:
        return {"success": False, "error": str(exc)}, "live", 500


def batch_detect_storms(body: dict) -> tuple[Any, str, int]:
    detector = _get_storm_detector()
    if not detector:
        return {"success": False, "error": "Storm Detector não disponível"}, "live", 503

    image_urls = body.get("image_urls", [])
    if not image_urls:
        return {"success": False, "error": "Campo obrigatório 'image_urls' não fornecido"}, "live", 400

    try:
        results = detector.predict_batch(image_urls)
        return _ok({
            "success": True,
            "total_images": len(results),
            "total_detections": sum(r.num_detections for r in results),
            "images_with_storm": sum(1 for r in results if r.has_storm),
            "results": [
                {
                    "image_path": r.image_path,
                    "num_detections": r.num_detections,
                    "has_storm": r.has_storm,
                    "average_confidence": r.average_confidence,
                    "timestamp": r.timestamp,
                }
                for r in results
            ],
        }, "live")
    except Exception as exc:
        return {"success": False, "error": str(exc)}, "live", 500


def sns_alerts_status() -> tuple[Any, str, int]:
    if use_inprocess_backend():
        try:
            from app.services.sns_alerts import sns_status as _sns_status

            return _ok(_sns_status(), "live")
        except Exception:
            pass
    status, body = backend_get("/alerts/sns/status")
    if status == 200 and isinstance(body, dict):
        return _ok(body, "live")
    return _ok(
        {"enabled": False, "configured": False, "topic_arn": None, "region": None},
        "fallback",
    )


def sns_subscribe(body: dict) -> tuple[Any, str, int]:
    email = (body.get("email") or "").strip()
    if not email:
        return {"success": False, "error": "E-mail obrigatório"}, "live", 400

    if use_inprocess_backend():
        try:
            from app.services.sns_alerts import subscribe_email

            result = subscribe_email(email)
            code = 200 if result.get("success") else 400
            return result, "live", code
        except Exception as exc:
            return {"success": False, "error": str(exc)}, "live", 500

    status, payload = backend_post("/alerts/subscribe", json_body={"email": email})
    if isinstance(payload, dict):
        return payload, "live", status if status != 200 else (200 if payload.get("success") else 400)
    return {"success": False, "error": "Falha ao inscrever e-mail"}, "unavailable", 503


def simulate_storm_detection(body: dict) -> tuple[Any, str, int]:
    confidence = body.get("confidence", 0.85)
    lat = body.get("lat", -23.55)
    lon = body.get("lon", -46.63)

    status, payload = backend_post(
        "/alerts/simulate",
        json_body={"confidence": confidence, "lat": lat, "lon": lon},
    )
    if status == 200 and isinstance(payload, dict):
        stored = payload.get("alert", {})
        sns_sent = bool(payload.get("sns_sent"))
        base_message = payload.get("message", "Alerta simulado registrado")
        if sns_sent:
            base_message += " — e-mail SNS enviado aos inscritos confirmados."
        elif payload.get("sns_message_id") is None and payload.get("sns_sent") is False:
            pass  # SNS não configurado — mensagem base
        return _ok({
            "success": True,
            "alert": {
                "id": stored.get("alert_id"),
                "type": "storm_detection",
                "confidence": confidence,
                "latitude": lat,
                "longitude": lon,
                "timestamp": stored.get("timestamp"),
                "message": payload.get("message", "Alerta simulado"),
                "simulated": True,
            },
            "message": base_message,
            "sns_sent": sns_sent,
            "sns_message_id": payload.get("sns_message_id"),
        }, "live")

    alert = {
        "id": f"alert_{datetime.now().timestamp()}",
        "type": "storm_detection",
        "confidence": confidence,
        "latitude": lat,
        "longitude": lon,
        "timestamp": datetime.now().isoformat(),
        "message": f"Tempestade detectada com confiança {confidence:.1%}",
        "simulated": True,
    }
    return _ok({
        "success": True,
        "alert": alert,
        "message": "Alerta simulado (API offline — não persistido)",
    }, "demo")


_DEMO_IOT_PATH = _PROJECT_ROOT / "data" / "demo" / "iot_readings.json"


def _demo_iot_readings() -> list[dict[str, Any]]:
    """Fallback demo quando a API está offline."""
    if _DEMO_IOT_PATH.exists():
        try:
            data = json.loads(_DEMO_IOT_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data[:10]
        except (json.JSONDecodeError, OSError):
            pass
    now = datetime.now(timezone.utc)
    return [
        {
            "reading_id": "demo_001",
            "device_id": "esp32_01",
            "cidade": "São Paulo",
            "temperatura": 24.5,
            "umidade": 68.0,
            "timestamp": now.isoformat().replace("+00:00", "Z"),
        }
    ]


def iot_latest(hours: int = 24) -> tuple[Any, str, int]:
    """Leituras IoT — demo ESP32 enquanto hardware não estiver conectado."""
    try:
        from app.core.config import settings as app_settings
        iot_mock = bool(app_settings.IOT_USE_MOCK)
    except ImportError:
        iot_mock = _env_bool("IOT_USE_MOCK", default=True)

    if not iot_mock:
        status, body = backend_get("/iot/readings/latest", params={"hours": hours})
        if status == 200 and isinstance(body, dict):
            return _ok(body, "live")
    readings = _demo_iot_readings()
    return _ok({"readings": readings, "count": len(readings), "storage": "demo"}, "demo")


def iot_status() -> tuple[Any, str, int]:
    try:
        from app.core.config import settings as app_settings
        iot_mock = bool(app_settings.IOT_USE_MOCK)
    except ImportError:
        iot_mock = _env_bool("IOT_USE_MOCK", default=True)

    if not iot_mock:
        status, body = backend_get("/iot/status")
        if status == 200 and isinstance(body, dict):
            return _ok(body, "live")
    return _ok(
        {"module": "iot", "status": "demo", "storage": "demo", "note": "ESP32 simulado (MVP)"},
        "demo",
    )


def _default_nasa_sample_path() -> Path | None:
    root = Path(__file__).resolve().parent.parent.parent
    candidates = sorted((root / "data" / "model-dataset" / "images" / "val").glob("nasa_*.png"))
    for path in candidates:
        lbl = root / "data" / "model-dataset" / "labels" / "val" / f"{path.stem}.txt"
        if lbl.exists() and lbl.stat().st_size > 0:
            return path
    return candidates[0] if candidates else None


def detect_storm_sample() -> tuple[Any, str, int]:
    detector = _get_storm_detector()
    if not detector:
        return {"success": False, "error": "Storm Detector não disponível"}, "live", 503

    sample = _default_nasa_sample_path()
    if not sample or not sample.exists():
        return {
            "success": False,
            "error": "Nenhuma imagem NASA de amostra em data/model-dataset/images/val/",
        }, "live", 404

    try:
        result = detector.predict(str(sample.resolve()))
        return _ok({
            "success": True,
            "sample_image": str(sample.name),
            "num_detections": result.num_detections,
            "has_storm": result.has_storm,
            "average_confidence": result.average_confidence,
            "timestamp": result.timestamp,
            "detections": [
                {"confidence": d.confidence, "class_name": d.class_name}
                for d in result.detections
            ],
            "message": (
                f"{result.num_detections} detecção(ões) em {sample.name}"
                if result.has_storm
                else f"Nenhuma tempestade em {sample.name}"
            ),
        }, "live")
    except Exception as exc:
        return {"success": False, "error": str(exc)}, "live", 500
