"""Unit tests for AgriRiskModel helpers and prediction."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.services import agri_risk_model as arm
from app.services.agri_threshold_ga import AgriThresholds, score_continuo_normalizado


class TestClassificarRisco:
    def test_low_risk_calm_weather(self):
        assert arm._classificar_risco(22.0, 50.0, 0.0, 10.0) == 0

    def test_medium_risk_moderate_rain(self):
        assert arm._classificar_risco(27.0, 70.0, 12.0, 30.0) == 1

    def test_high_risk_heavy_rain_and_wind(self):
        assert arm._classificar_risco(30.0, 90.0, 25.0, 85.0) == 2

    def test_extreme_temperature_adds_risk(self):
        assert arm._classificar_risco(40.0, 50.0, 6.0, 5.0) >= 1


class TestScoreContinuo:
    def test_scores_differ_by_inputs(self):
        th = AgriThresholds()
        s1 = score_continuo_normalizado(22.0, 50.0, 0.0, 10.0, th)
        s2 = score_continuo_normalizado(30.0, 90.0, 25.0, 85.0, th)
        assert s1 != s2


class TestRecordsToXy:
    def test_records_to_xy_raises_when_too_few(self):
        with pytest.raises(ValueError, match="Poucos registros"):
            arm._records_to_xy([])


class TestOpenMeteoLoader:
    @patch("app.clients.openmeteo.OpenMeteoClient")
    def test_carregar_dados_openmeteo(self, mock_client_cls):
        record = {
            "temperature": 28.0,
            "humidity": 70,
            "precipitation": 2.0,
            "wind_speed_kmh": 15.0,
        }
        mock_client_cls.return_value.get_historical_hourly.return_value = [record] * 120
        X, y = arm._carregar_dados_openmeteo(days=1)
        assert X.shape[0] == 600  # 5 cities * 120
        assert np.all((y >= 0) & (y <= 1))


class TestBuildTrainingData:
    def test_build_training_data_falls_back_to_synthetic(self, monkeypatch):
        monkeypatch.setattr(arm, "_carregar_dados_inmet", lambda: (_ for _ in ()).throw(FileNotFoundError()))
        monkeypatch.setattr(arm, "_carregar_dados_openmeteo", lambda: (_ for _ in ()).throw(ValueError("x")))
        X, y, src = arm._build_training_data(prefer_real=True)
        assert src == "synthetic_embrapa_inmet"
        assert len(X) == 8000


class TestSyntheticData:
    def test_gerar_dados_sinteticos_shape(self):
        X, y = arm._gerar_dados_sinteticos(n=200)
        assert X.shape == (200, 4)
        assert y.shape == (200,)
        assert np.all((y >= 0) & (y <= 1))


class TestAgriRiskModelPredict:
    @pytest.fixture
    def model(self):
        return arm.AgriRiskModel()

    def test_predict_returns_score_between_0_and_1(self, model):
        score = model.predict(28.0, 80.0, 5.0, 20.0)
        assert 0.0 <= score <= 1.0

    def test_predict_scores_vary(self, model):
        s_calm = model.predict(22.0, 50.0, 0.0, 10.0)
        s_storm = model.predict(32.0, 90.0, 15.0, 50.0)
        assert s_calm != s_storm or s_storm > s_calm

    def test_predict_detalhado_structure(self, model):
        result = model.predict_detalhado(32.0, 90.0, 15.0, 50.0)
        assert result["classe"] in ("LOW", "MEDIUM", "HIGH")
        assert "probabilidades" in result
        assert "features" in result
        assert "dataset_source" in result
        assert "model_type" in result
        assert 0.0 <= result["score"] <= 1.0

    def test_get_thresholds_returns_dataclass(self):
        th = arm.get_thresholds()
        assert hasattr(th, "precip_t4")

    def test_legacy_classifier_predict_path(self):
        model = arm.AgriRiskModel.__new__(arm.AgriRiskModel)
        mock_clf = MagicMock()
        mock_clf.predict.return_value = [0]
        mock_clf.predict_proba.return_value = [[0.9, 0.1]]
        mock_clf.classes_ = [0, 1]
        mock_scaler = MagicMock()
        mock_scaler.transform.return_value = [[0, 0, 0, 0]]
        model._model = mock_clf
        model._scaler = mock_scaler
        model._thresholds = arm.get_thresholds()
        score = model.predict(25.0, 60.0, 0.0, 10.0)
        assert 0.0 <= score <= 1.0

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
        assert 0.0 <= float(pred[0]) <= 1.0
