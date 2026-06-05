"""
AgriRiskModel — Modelo de risco agrícola por condições meteorológicas.

Regressor LightGBM treinado com histórico INMET BDMEP; limiares otimizados por AG.
Score contínuo 0–1 derivado de regras agrometeorológicas parametrizadas.
"""

from __future__ import annotations

import logging
import pickle
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import os

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler

_REGRESSOR_BACKEND = "sklearn_hgb"


def _resolve_regressor_backend() -> str:
    """LightGBM só quando explicitamente pedido — evita segfault com torch/YOLO no macOS."""
    if os.environ.get("AGRI_USE_LIGHTGBM", "").strip().lower() in ("1", "true", "yes"):
        try:
            from lightgbm import LGBMRegressor  # noqa: PLC0415
            return "lightgbm"
        except (OSError, ImportError):
            pass
    return "sklearn_hgb"

from app.services.agri_threshold_ga import (
    AgriThresholds,
    classificar_com_thresholds,
    classe_from_score,
    estimate_probas,
    load_thresholds,
    score_continuo_normalizado,
)

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = Path(__file__).resolve().parents[3] / "models" / "agri_risk_model.pkl"
_DEFAULT_SCALER = Path(__file__).resolve().parents[3] / "models" / "agri_risk_scaler.pkl"

DATASET_SOURCE: str = "unknown"
MODEL_TYPE: str = "regressor"

_INMET_CACHE = Path(__file__).resolve().parents[3] / "data" / "weather" / "inmet" / "training_cache.csv"
_INMET_SAMPLE = Path(__file__).resolve().parents[3] / "data" / "weather" / "inmet" / "sample_inmet_bdmep.csv"

_BRAZIL_LOCATIONS: list[tuple[float, float, str]] = [
    (-23.5505, -46.6333, "São Paulo"),
    (-22.9068, -43.1729, "Rio de Janeiro"),
    (-15.8267, -47.8711, "Brasília"),
    (-30.0346, -51.2177, "Porto Alegre"),
    (-9.9794, -49.8623, "Belém"),
]


def _resolve_model_paths() -> tuple[Path, Path]:
    here = Path(__file__).resolve()
    for base in (here.parents[2], here.parents[3]):
        model = base / "models" / "agri_risk_model.pkl"
        scaler = base / "models" / "agri_risk_scaler.pkl"
        if model.exists() and scaler.exists():
            return model, scaler
    return _DEFAULT_MODEL, _DEFAULT_SCALER


MODEL_PATH, SCALER_PATH = _resolve_model_paths()
MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_thresholds() -> AgriThresholds:
    return load_thresholds()


def _classificar_risco(
    temperatura: float,
    umidade: float,
    precipitacao: float,
    vento_kmh: float,
    th: AgriThresholds | None = None,
) -> int:
    return classificar_com_thresholds(
        temperatura, umidade, precipitacao, vento_kmh, th or get_thresholds(),
    )


def _gerar_dados_sinteticos(n: int = 5000) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(42)
    th = get_thresholds()
    temp = rng.uniform(10, 42, n)
    umid = rng.uniform(20, 100, n)
    precip = rng.exponential(3, n)
    vento = rng.exponential(15, n)
    y = np.array([
        score_continuo_normalizado(temp[i], umid[i], precip[i], vento[i], th)
        for i in range(n)
    ], dtype=float)
    return np.column_stack([temp, umid, precip, vento]), y


def _records_to_xy(records, th: AgriThresholds | None = None) -> tuple[np.ndarray, np.ndarray]:
    t = th or get_thresholds()
    rows: list[list[float]] = []
    targets: list[float] = []
    for rec in records:
        rows.append(rec.as_features())
        targets.append(
            score_continuo_normalizado(
                rec.temperatura, rec.umidade, rec.precipitacao, rec.vento_kmh, t,
            )
        )
    if len(rows) < 100:
        raise ValueError(f"Poucos registros INMET: {len(rows)}")
    return np.array(rows, dtype=float), np.array(targets, dtype=float)


def _carregar_dados_inmet() -> tuple[np.ndarray, np.ndarray]:
    from app.clients.inmet import InmetClient  # noqa: PLC0415

    th = get_thresholds()
    for path in (_INMET_CACHE, _INMET_SAMPLE):
        if path.exists():
            records = InmetClient.load_cache_csv(path)
            logger.info("INMET cache: %s (%d registros)", path.name, len(records))
            return _records_to_xy(records, th)
    raise FileNotFoundError(
        "Cache INMET ausente. Execute: make build-agri ou build_dataset_agri.command"
    )


def _carregar_dados_openmeteo(days: int = 90) -> tuple[np.ndarray, np.ndarray]:
    from app.clients.openmeteo import OpenMeteoClient  # noqa: PLC0415

    th = get_thresholds()
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days)
    client = OpenMeteoClient()
    rows: list[list[float]] = []
    targets: list[float] = []

    for lat, lon, city in _BRAZIL_LOCATIONS:
        logger.info("Open-Meteo archive: %s (%.2f, %.2f)", city, lat, lon)
        records = client.get_historical_hourly(
            lat, lon,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
        )
        for rec in records:
            rows.append([
                rec["temperature"],
                rec["humidity"],
                rec["precipitation"],
                rec["wind_speed_kmh"],
            ])
            targets.append(
                score_continuo_normalizado(
                    rec["temperature"], rec["humidity"],
                    rec["precipitation"], rec["wind_speed_kmh"], th,
                )
            )

    if len(rows) < 100:
        raise ValueError(f"Open-Meteo retornou poucos registros: {len(rows)}")
    return np.array(rows, dtype=float), np.array(targets, dtype=float)


def _save_meta(extra: dict[str, Any] | None = None) -> None:
    meta_path = MODEL_PATH.parent / "agri_risk_meta.pkl"
    payload = {
        "dataset_source": DATASET_SOURCE,
        "model_type": MODEL_TYPE,
        "thresholds_source": str(MODEL_PATH.parent / "agri_risk_thresholds.json"),
    }
    if extra:
        payload.update(extra)
    with open(meta_path, "wb") as f:
        pickle.dump(payload, f)


def _build_training_data(prefer_real: bool = True) -> tuple[np.ndarray, np.ndarray, str]:
    global DATASET_SOURCE  # noqa: PLW0603
    if prefer_real:
        for loader, source in (
            (_carregar_dados_inmet, "inmet_bdmep_brazil_5stations"),
            (_carregar_dados_openmeteo, "openmeteo_archive_brazil_5cities"),
        ):
            try:
                X, y = loader()
                DATASET_SOURCE = source
                return X, y, DATASET_SOURCE
            except Exception as exc:
                logger.warning("%s indisponível: %s", source, exc)
    X, y = _gerar_dados_sinteticos(n=8000)
    DATASET_SOURCE = "synthetic_embrapa_inmet"
    return X, y, DATASET_SOURCE


def _build_regressor():
    global MODEL_TYPE, _REGRESSOR_BACKEND  # noqa: PLW0603
    backend = _resolve_regressor_backend()
    _REGRESSOR_BACKEND = backend
    if backend == "lightgbm":
        from lightgbm import LGBMRegressor  # noqa: PLC0415
        MODEL_TYPE = "lgbm_regressor"
        return LGBMRegressor(
            n_estimators=200,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbose=-1,
        )
    MODEL_TYPE = "sklearn_hgb_regressor"
    return HistGradientBoostingRegressor(
        max_iter=200,
        max_depth=8,
        learning_rate=0.05,
        random_state=42,
    )


def treinar_e_salvar(prefer_real: bool = True) -> tuple[Any, StandardScaler]:
    global DATASET_SOURCE  # noqa: PLW0603
    backend = _resolve_regressor_backend()
    logger.info("Treinando AgriRiskModel (%s)...", backend)
    X, y, source = _build_training_data(prefer_real=prefer_real)
    DATASET_SOURCE = source

    scaler = StandardScaler()
    X_sc = scaler.fit_transform(X)
    model = _build_regressor()
    model.fit(X_sc, y)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

    scores = cross_val_score(model, X_sc, y, cv=5, scoring="r2")
    logger.info(
        "AgriRiskModel treinado — fonte=%s, R2 CV: %.3f ± %.3f",
        DATASET_SOURCE, scores.mean(), scores.std(),
    )
    _save_meta({"cv_r2_mean": float(scores.mean())})
    return model, scaler


class AgriRiskModel:
    def __init__(self):
        global DATASET_SOURCE, MODEL_TYPE  # noqa: PLW0603
        self._thresholds = get_thresholds()
        meta_path = MODEL_PATH.parent / "agri_risk_meta.pkl"
        if MODEL_PATH.exists() and SCALER_PATH.exists():
            with open(MODEL_PATH, "rb") as f:
                self._model = pickle.load(f)
            with open(SCALER_PATH, "rb") as f:
                self._scaler = pickle.load(f)
            if meta_path.exists():
                with open(meta_path, "rb") as f:
                    meta = pickle.load(f)
                    DATASET_SOURCE = meta.get("dataset_source", "loaded_from_disk")
                    MODEL_TYPE = meta.get("model_type", "unknown")
            else:
                DATASET_SOURCE = "loaded_from_disk"
            logger.info("AgriRiskModel carregado de %s", MODEL_PATH)
        else:
            self._model, self._scaler = treinar_e_salvar(prefer_real=True)

    def predict(
        self,
        temperatura: float,
        umidade: float,
        precipitacao: float,
        vento_kmh: float,
    ) -> float:
        X = np.array([[temperatura, umidade, precipitacao, vento_kmh]])
        X_sc = self._scaler.transform(X)
        if hasattr(self._model, "predict_proba"):
            # Legado RandomForestClassifier
            classe = int(self._model.predict(X_sc)[0])
            proba = self._model.predict_proba(X_sc)[0]
            known = list(getattr(self._model, "classes_", [0, 1, 2]))
            idx = known.index(classe) if classe in known else 0
            idx = min(idx, len(proba) - 1)
            base = {0: 0.15, 1: 0.55, 2: 0.85}.get(classe, 0.55)
            conf = float(proba[idx])
            return float(np.clip(base * conf + base * (1 - conf) * 0.8, 0.0, 1.0))
        raw = float(self._model.predict(X_sc)[0])
        return float(np.clip(raw, 0.0, 1.0))

    def predict_detalhado(
        self,
        temperatura: float,
        umidade: float,
        precipitacao: float,
        vento_kmh: float,
    ) -> dict:
        score = round(self.predict(temperatura, umidade, precipitacao, vento_kmh), 3)
        classe_name = classe_from_score(score)
        probas = estimate_probas(score, self._thresholds)
        return {
            "score": score,
            "classe": classe_name,
            "probabilidades": probas,
            "features": {
                "temperatura_c": temperatura,
                "umidade_pct": umidade,
                "precipitacao_mm": precipitacao,
                "vento_kmh": vento_kmh,
            },
            "dataset_source": DATASET_SOURCE,
            "model_type": MODEL_TYPE,
        }
