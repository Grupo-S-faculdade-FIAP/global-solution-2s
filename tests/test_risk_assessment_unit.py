"""Unit tests for RiskAssessmentService."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.risk_assessment import (
    RiskAssessmentService,
    _categoria,
    _effective_weights,
    _haversine_km,
    _score_climatico,
    _score_cv,
    RECOMENDACOES,
)
from weather_fixtures import SAMPLE_WEATHER


def test_categoria_thresholds():
    assert _categoria(0.1) == "LOW"
    assert _categoria(0.5) == "MEDIUM"
    assert _categoria(0.8) == "HIGH"


def test_recomendacoes_cover_all_categories():
    for cat in ("LOW", "MEDIUM", "HIGH"):
        assert cat in RECOMENDACOES


def test_effective_weights_no_coverage():
    pesos = _effective_weights(0.0)
    assert pesos["cv"] == 0.0
    assert abs(pesos["clima"] + pesos["ml_agricola"] - 1.0) < 0.01


def test_effective_weights_full_coverage():
    pesos = _effective_weights(1.0)
    assert pesos["cv"] == 0.4
    assert pesos["clima"] == 0.4
    assert pesos["ml_agricola"] == 0.2


def test_effective_weights_partial_coverage():
    pesos = _effective_weights(0.5)
    assert pesos["cv"] == 0.2
    assert abs(sum(pesos.values()) - 1.0) < 0.01


def test_score_climatico_ranges():
    calm = _score_climatico({
        "precipitation": 0, "wind_speed": 2, "humidity": 50, "temperature": 22,
    })
    stormy = _score_climatico({
        "precipitation": 25, "wind_speed": 25, "humidity": 95, "temperature": 36,
    })
    assert 0.0 <= calm <= 1.0
    assert stormy > calm


def test_haversine_same_point():
    assert _haversine_km(-23.55, -46.63, -23.55, -46.63) == 0.0


@patch.object(RiskAssessmentService, "_load_models")
def test_calculate_risk_cv_exception(_mock_load):
    svc = RiskAssessmentService()
    svc.weather_service = MagicMock()
    svc.weather_service.get_current.return_value = SAMPLE_WEATHER
    svc._storm_detector = None
    svc._storm_detector_tried = True
    svc._storm_query = MagicMock()
    svc._storm_query.recent_detections.side_effect = RuntimeError("cv fail")
    svc._agri_model = None

    with patch("app.services.risk_assessment._score_cv", side_effect=RuntimeError("cv fail")):
        result = svc.calculate_risk(lat=-23.55, lon=-46.63)
    assert result.detalhes["cv"]["erro"] == "cv fail"


@patch.object(RiskAssessmentService, "_load_models")
def test_calculate_risk_ml_failure(_mock_load):
    svc = RiskAssessmentService()
    svc.weather_service = MagicMock()
    svc.weather_service.get_current.return_value = SAMPLE_WEATHER
    svc._storm_detector = None
    svc._storm_detector_tried = True
    svc._storm_query = None
    svc._agri_model = MagicMock()
    svc._agri_model.predict.side_effect = RuntimeError("ml down")

    result = svc.calculate_risk(lat=-23.55, lon=-46.63)
    assert result.detalhes["ml_agricola"]["erro"] == "ml down"


@patch.object(RiskAssessmentService, "_load_models")
def test_calculate_risk_with_ml_and_storm_query(_mock_load):
    svc = RiskAssessmentService()
    svc.weather_service = MagicMock()
    svc.weather_service.get_current.return_value = SAMPLE_WEATHER
    svc._storm_detector = None
    svc._storm_detector_tried = True
    svc._storm_query = MagicMock()
    svc._storm_query.recent_detections.return_value = [
        {
            "detection_id": "a1",
            "latitude": -23.55,
            "longitude": -46.63,
            "confidence": 0.75,
            "s3_key": "nasa_brasil_sudeste.png",
            "timestamp": "2026-06-05T12:00:00Z",
        },
    ]
    mock_ml = MagicMock()
    mock_ml.predict.return_value = 0.35
    svc._agri_model = mock_ml

    result = svc.calculate_risk(lat=-23.55, lon=-46.63)
    assert result.detalhes["cv"]["coverage_factor"] == 1.0
    assert result.detalhes["ml_agricola"]["score"] == 0.35


@patch.object(RiskAssessmentService, "_load_models")
def test_calculate_risk_with_mocked_weather(_mock_load):
    svc = RiskAssessmentService()
    svc.weather_service = MagicMock()
    svc.weather_service.get_current.return_value = SAMPLE_WEATHER
    svc._storm_detector = None
    svc._storm_detector_tried = True
    svc._agri_model = None
    svc._storm_query = None

    result = svc.calculate_risk(lat=-23.55, lon=-46.63)

    assert result.detalhes["cv"]["status"] == "modelo_nao_disponivel"
    assert 0.0 <= result.score <= 1.0
    assert result.category in ("LOW", "MEDIUM", "HIGH")
    assert result.recommendation
    assert "clima" in result.detalhes
    assert "components" in result.detalhes
    assert "pesos" in result.detalhes


@patch.object(RiskAssessmentService, "_load_models")
def test_calculate_risk_weather_failure_fallback(_mock_load):
    svc = RiskAssessmentService()
    svc.weather_service = MagicMock()
    svc.weather_service.get_current.side_effect = Exception("offline")
    svc._storm_detector = None
    svc._agri_model = None
    svc._storm_query = None

    result = svc.calculate_risk(lat=0.0, lon=0.0)

    assert result.detalhes["clima"]["erro"] == "offline"
    assert result.score >= 0.0


def test_get_storm_detector_skipped_with_env(monkeypatch):
    monkeypatch.setenv("RISK_SKIP_YOLO", "1")
    svc = RiskAssessmentService()
    assert svc._get_storm_detector() is None


def test_get_storm_detector_missing_model_file(monkeypatch):
    from pathlib import Path
    from unittest.mock import patch as mock_patch

    monkeypatch.delenv("RISK_SKIP_YOLO", raising=False)
    svc = RiskAssessmentService()
    with mock_patch.object(Path, "exists", return_value=False):
        assert svc._get_storm_detector() is None


def test_nearest_region_image_finds_file():
    from app.services.risk_assessment import _nearest_region_image
    path, dist = _nearest_region_image(-23.55, -46.63)
    if path is not None:
        assert path.suffix == ".png"


def test_score_cv_without_detector_uses_alerts_only():
    storm_query = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
    storm_query.recent_detections.return_value = [
        {
            "detection_id": "x1",
            "latitude": -23.55,
            "longitude": -46.63,
            "confidence": 0.7,
            "s3_key": "nasa_brasil_sudeste.png",
            "timestamp": "2026-06-04T12:00:00Z",
        },
    ]
    score, info, cov = _score_cv(None, -23.55, -46.63, storm_query)
    assert cov == 1.0
    assert score > 0
    assert info["fonte"] == "alertas"


def test_score_cv_with_mock_alerts():
    detector = MagicMock()
    detector.predict.return_value = MagicMock(
        average_confidence=0.5,
        num_detections=2,
        has_storm=True,
    )

    storm_query = MagicMock()
    storm_query.recent_detections.return_value = [
        {
            "detection_id": "sp1",
            "latitude": -23.55,
            "longitude": -46.63,
            "confidence": 0.8,
            "s3_key": "nasa_brasil_sudeste_20260604.png",
            "timestamp": "2026-06-04T12:00:00Z",
        },
        {
            "detection_id": "am1",
            "latitude": -3.1,
            "longitude": -60.0,
            "confidence": 0.9,
            "s3_key": "nasa_brasil_20260604.png",
            "timestamp": "2026-06-04T12:00:00Z",
        },
    ]

    score_sp, info_sp, cov_sp = _score_cv(detector, -23.55, -46.63, storm_query)
    score_am, info_am, cov_am = _score_cv(detector, -3.1, -60.0, storm_query)

    assert cov_sp == 1.0
    assert cov_am == 1.0
    assert info_sp["fonte"] in ("alertas", "imagem")
    assert info_am["fonte"] in ("alertas", "imagem")
    assert score_sp >= 0.0
    assert score_am >= 0.0
