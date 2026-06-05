"""Unit tests for AgriRiskModel helpers and prediction."""

import numpy as np
import pytest

from app.services import agri_risk_model as arm


class TestClassificarRisco:
    def test_low_risk_calm_weather(self):
        assert arm._classificar_risco(22.0, 50.0, 0.0, 10.0) == 0

    def test_medium_risk_moderate_rain(self):
        assert arm._classificar_risco(27.0, 70.0, 12.0, 30.0) == 1

    def test_high_risk_heavy_rain_and_wind(self):
        assert arm._classificar_risco(30.0, 90.0, 25.0, 85.0) == 2

    def test_extreme_temperature_adds_risk(self):
        assert arm._classificar_risco(40.0, 50.0, 6.0, 5.0) >= 1


class TestSyntheticData:
    def test_gerar_dados_sinteticos_shape(self):
        X, y = arm._gerar_dados_sinteticos(n=200)
        assert X.shape == (200, 4)
        assert y.shape == (200,)
        assert set(y.tolist()).issubset({0, 1, 2})


class TestAgriRiskModelPredict:
    @pytest.fixture
    def model(self):
        return arm.AgriRiskModel()

    def test_predict_returns_score_between_0_and_1(self, model):
        score = model.predict(28.0, 80.0, 5.0, 20.0)
        assert 0.0 <= score <= 1.0

    def test_predict_detalhado_structure(self, model):
        result = model.predict_detalhado(32.0, 90.0, 15.0, 50.0)
        assert result["classe"] in ("LOW", "MEDIUM", "HIGH")
        assert "probabilidades" in result
        assert "features" in result
        assert "dataset_source" in result
        assert 0.0 <= result["score"] <= 1.0

    def test_treinar_e_salvar_synthetic(self, tmp_path, monkeypatch):
        model_path = tmp_path / "agri_risk_model.pkl"
        scaler_path = tmp_path / "agri_risk_scaler.pkl"
        monkeypatch.setattr(arm, "MODEL_PATH", model_path)
        monkeypatch.setattr(arm, "SCALER_PATH", scaler_path)

        model, scaler = arm.treinar_e_salvar(prefer_real=False)

        assert model_path.exists()
        assert scaler_path.exists()
        X = np.array([[25.0, 60.0, 2.0, 15.0]])
        pred = model.predict(scaler.transform(X))
        assert pred[0] in (0, 1, 2)
