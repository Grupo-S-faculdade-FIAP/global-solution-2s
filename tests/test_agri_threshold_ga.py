"""Tests for GA threshold optimization module."""

import json

import numpy as np
import pytest

from app.services import agri_threshold_ga as ga


class TestAgriThresholds:
    def test_default_thresholds_classify_low(self):
        th = ga.AgriThresholds()
        assert ga.classificar_com_thresholds(22.0, 50.0, 0.0, 10.0, th) == 0

    def test_default_thresholds_classify_medium(self):
        th = ga.AgriThresholds()
        assert ga.classificar_com_thresholds(27.0, 70.0, 12.0, 30.0, th) == 1

    def test_default_thresholds_classify_high(self):
        th = ga.AgriThresholds()
        assert ga.classificar_com_thresholds(30.0, 90.0, 25.0, 85.0, th) == 2

    def test_score_continuo_varies(self):
        th = ga.AgriThresholds()
        s1 = ga.score_continuo_normalizado(22.0, 50.0, 0.0, 10.0, th)
        s2 = ga.score_continuo_normalizado(30.0, 90.0, 25.0, 85.0, th)
        assert s1 < s2
        assert 0.0 <= s1 <= 1.0

    def test_save_and_load_roundtrip(self, tmp_path):
        th = ga.AgriThresholds(precip_t3=9.5, cutoff_medium=1.2)
        path = ga.save_thresholds(th, tmp_path / "th.json")
        loaded = ga.load_thresholds(path)
        assert loaded.precip_t3 == 9.5
        assert loaded.cutoff_medium == 1.2

    def test_estimate_probas_sum_to_one(self):
        probas = ga.estimate_probas(0.5)
        assert abs(sum(probas.values()) - 1.0) < 0.01

    def test_evaluate_thresholds_returns_float(self):
        from app.clients.inmet import InmetClient

        sample = ga._INMET_SAMPLE
        if not sample.exists():
            pytest.skip("sample INMET ausente")
        records = InmetClient.load_cache_csv(sample)
        X = np.array([r.as_features() for r in records[:200]])
        records = records[:200]
        fitness = ga.evaluate_thresholds(ga.AgriThresholds(), X, records)
        assert isinstance(fitness, float)

    def test_genes_to_thresholds_ordered(self):
        genes = [20, 10, 5, 1, 80, 60, 40, 85, 28, 75, 26, 38, 8, 1.5, 4,
                 3, 2, 1, 0.4, 2.5, 1.5, 0.8, 1.5, 0.8, 1.0]
        th = ga._genes_to_thresholds(genes)
        assert th.precip_t4 >= th.precip_t3 >= th.precip_t2 >= th.precip_t1
        assert th.cutoff_high >= th.cutoff_medium

    def test_classe_from_score(self):
        assert ga.classe_from_score(0.1) == "LOW"
        assert ga.classe_from_score(0.5) == "MEDIUM"
        assert ga.classe_from_score(0.8) == "HIGH"

    def test_load_thresholds_missing_file(self, tmp_path):
        loaded = ga.load_thresholds(tmp_path / "missing.json")
        assert loaded.precip_t4 == 20.0

    def test_rule_raw_score_increases_with_rain(self):
        th = ga.AgriThresholds()
        low = ga.rule_raw_score(20, 50, 0, 10, th)
        high = ga.rule_raw_score(20, 50, 25, 10, th)
        assert high > low

    def test_balance_penalty_empty(self):
        import numpy as np
        assert ga._balance_penalty(np.array([])) == 1.0

    def test_optimize_thresholds_mini(self):
        if not ga._INMET_SAMPLE.exists():
            pytest.skip("sample INMET ausente")
        result = ga.optimize_thresholds(generations=2, population=6, sample_size=80)
        assert isinstance(result, ga.AgriThresholds)
