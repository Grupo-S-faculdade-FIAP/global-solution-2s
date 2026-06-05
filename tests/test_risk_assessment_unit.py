"""Unit tests for RiskAssessmentService."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.risk_assessment import (
    RiskAssessmentService,
    _categoria,
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


@patch.object(RiskAssessmentService, "_load_models")
def test_calculate_risk_with_mocked_weather(_mock_load):
    svc = RiskAssessmentService()
    svc.weather_service = MagicMock()
    svc.weather_service.get_current.return_value = SAMPLE_WEATHER
    svc._storm_detector = None
    svc._agri_model = None

    result = svc.calculate_risk(lat=-23.55, lon=-46.63)

    assert 0.0 <= result.score <= 1.0
    assert result.category in ("LOW", "MEDIUM", "HIGH")
    assert result.recommendation
    assert "clima" in result.detalhes


@patch.object(RiskAssessmentService, "_load_models")
def test_calculate_risk_weather_failure_fallback(_mock_load):
    svc = RiskAssessmentService()
    svc.weather_service = MagicMock()
    svc.weather_service.get_current.side_effect = Exception("offline")
    svc._storm_detector = None
    svc._agri_model = None

    result = svc.calculate_risk(lat=0.0, lon=0.0)

    assert result.detalhes["clima"]["erro"] == "offline"
    assert result.score >= 0.0
