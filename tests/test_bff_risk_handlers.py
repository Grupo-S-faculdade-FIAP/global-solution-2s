"""Unit tests for BFF risk handlers."""

from unittest.mock import MagicMock, patch

from app.services.risk_assessment import RiskScore


@patch("dashboard.bff_handlers._get_risk_service")
@patch("dashboard.bff_handlers.use_inprocess_backend", return_value=True)
def test_risk_forecast_returns_detalhes(mock_inprocess, mock_svc):
    from dashboard import bff_handlers as bff

    mock_svc.return_value.calculate_risk.return_value = RiskScore(
        score=0.33,
        category="LOW",
        recommendation="ok",
        timestamp="2026-06-05T12:00:00Z",
        detalhes={
            "components": {"clima": 0.2, "cv": 0.0, "ml_agricola": 0.4},
            "pesos": {"clima": 0.5, "cv": 0.0, "ml_agricola": 0.5},
            "clima": {"score": 0.2},
        },
    )
    data, source, status = bff.risk_forecast(-23.55, -46.63)
    assert status == 200
    assert source == "live"
    assert data["detalhes"]["components"]["clima"] == 0.2


@patch("dashboard.bff_handlers._get_agri_risk_model")
@patch("dashboard.bff_handlers.use_inprocess_backend", return_value=True)
def test_ml_agricultural_risk_inprocess(mock_inprocess, mock_model):
    from dashboard import bff_handlers as bff

    mock_model.return_value.predict_detalhado.return_value = {
        "score": 0.4,
        "classe": "MEDIUM",
        "probabilidades": {"LOW": 0.2, "MEDIUM": 0.7, "HIGH": 0.1},
        "features": {},
        "dataset_source": "inmet",
        "model_type": "sklearn_hgb_regressor",
    }
    data, source, status = bff.ml_agricultural_risk(25, 60, 0, 10)
    assert status == 200
    assert data["classe"] == "MEDIUM"
    assert "recomendacao" in data


def test_detector_status_reflects_availability(monkeypatch):
    from dashboard import bff_handlers as bff

    monkeypatch.setattr(bff, "_storm_detector", object())
    data, source, status = bff.detector_status()
    assert status == 200
    assert data["available"] is True


@patch("dashboard.bff_handlers.backend_get", return_value=(503, {}))
@patch("dashboard.bff_handlers.use_inprocess_backend", return_value=False)
def test_risk_forecast_demo_fallback(mock_inprocess, _mock_get):
    from dashboard import bff_handlers as bff

    data, source, status = bff.risk_forecast(-10.0, -50.0)
    assert status == 200
    assert source == "fallback"
    assert "risk_score" in data
