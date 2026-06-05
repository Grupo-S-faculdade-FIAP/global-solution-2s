"""
AgriRiskModel — Modelo de risco agrícola por condições meteorológicas.

Classificador Random Forest treinado preferencialmente com histórico INMET BDMEP
(dados oficiais), depois Open-Meteo Archive e fallback sintético.

Classes: 0=LOW, 1=MEDIUM, 2=HIGH
"""

from __future__ import annotations

import logging
import pickle
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = Path(__file__).resolve().parents[3] / "models" / "agri_risk_model.pkl"
_DEFAULT_SCALER = Path(__file__).resolve().parents[3] / "models" / "agri_risk_scaler.pkl"

DATASET_SOURCE: str = "unknown"

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

LABEL_MAP = {0: 0.15, 1: 0.55, 2: 0.85}


def _classificar_risco(
    temperatura: float,
    umidade: float,
    precipitacao: float,
    vento_kmh: float,
) -> int:
    score = 0.0
    if precipitacao >= 20:
        score += 3.0
    elif precipitacao >= 10:
        score += 2.0
    elif precipitacao >= 5:
        score += 1.0
    elif precipitacao >= 1:
        score += 0.4
    if vento_kmh >= 80:
        score += 2.5
    elif vento_kmh >= 60:
        score += 1.5
    elif vento_kmh >= 40:
        score += 0.8
    if umidade > 85 and temperatura > 28:
        score += 1.5
    elif umidade > 75 and temperatura > 26:
        score += 0.8
    if temperatura >= 38 or temperatura <= 8:
        score += 1.0
    if score >= 4.0:
        return 2
    if score >= 1.5:
        return 1
    return 0


def _gerar_dados_sinteticos(n: int = 5000) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(42)
    temp = rng.uniform(10, 42, n)
    umid = rng.uniform(20, 100, n)
    precip = rng.exponential(3, n)
    vento = rng.exponential(15, n)
    labels = np.array([
        _classificar_risco(temp[i], umid[i], precip[i], vento[i])
        for i in range(n)
    ], dtype=int)
    return np.column_stack([temp, umid, precip, vento]), labels


def _records_to_xy(records) -> tuple[np.ndarray, np.ndarray]:
    rows: list[list[float]] = []
    labels: list[int] = []
    for rec in records:
        rows.append(rec.as_features())
        labels.append(_classificar_risco(
            rec.temperatura, rec.umidade, rec.precipitacao, rec.vento_kmh,
        ))
    if len(rows) < 100:
        raise ValueError(f"Poucos registros INMET: {len(rows)}")
    return np.array(rows, dtype=float), np.array(labels, dtype=int)


def _carregar_dados_inmet() -> tuple[np.ndarray, np.ndarray]:
    from app.clients.inmet import InmetClient  # noqa: PLC0415

    for path in (_INMET_CACHE, _INMET_SAMPLE):
        if path.exists():
            records = InmetClient.load_cache_csv(path)
            logger.info("INMET cache: %s (%d registros)", path.name, len(records))
            return _records_to_xy(records)
    raise FileNotFoundError(
        "Cache INMET ausente. Execute: make build-agri ou build_dataset_agri.command"
    )


def _carregar_dados_openmeteo(days: int = 90) -> tuple[np.ndarray, np.ndarray]:
    from app.clients.openmeteo import OpenMeteoClient  # noqa: PLC0415

    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days)
    client = OpenMeteoClient()
    rows: list[list[float]] = []
    labels: list[int] = []

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
            labels.append(_classificar_risco(
                rec["temperature"], rec["humidity"],
                rec["precipitation"], rec["wind_speed_kmh"],
            ))

    if len(rows) < 100:
        raise ValueError(f"Open-Meteo retornou poucos registros: {len(rows)}")
    return np.array(rows, dtype=float), np.array(labels, dtype=int)


def _save_meta() -> None:
    meta_path = MODEL_PATH.parent / "agri_risk_meta.pkl"
    with open(meta_path, "wb") as f:
        pickle.dump({"dataset_source": DATASET_SOURCE}, f)


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


def treinar_e_salvar(prefer_real: bool = True) -> tuple[RandomForestClassifier, StandardScaler]:
    global DATASET_SOURCE  # noqa: PLW0603
    logger.info("Treinando AgriRiskModel...")
    X, y, source = _build_training_data(prefer_real=prefer_real)
    DATASET_SOURCE = source

    scaler = StandardScaler()
    X_sc = scaler.fit_transform(X)
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        min_samples_leaf=5,
        class_weight="balanced",
        n_jobs=-1,
        random_state=42,
    )
    model.fit(X_sc, y)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

    scores = cross_val_score(model, X_sc, y, cv=5, scoring="accuracy")
    logger.info(
        "AgriRiskModel treinado — fonte=%s, acurácia CV: %.3f ± %.3f",
        DATASET_SOURCE, scores.mean(), scores.std(),
    )
    _save_meta()
    return model, scaler


class AgriRiskModel:
    def __init__(self):
        global DATASET_SOURCE  # noqa: PLW0603
        meta_path = MODEL_PATH.parent / "agri_risk_meta.pkl"
        if MODEL_PATH.exists() and SCALER_PATH.exists():
            with open(MODEL_PATH, "rb") as f:
                self._model = pickle.load(f)
            with open(SCALER_PATH, "rb") as f:
                self._scaler = pickle.load(f)
            if meta_path.exists():
                with open(meta_path, "rb") as f:
                    DATASET_SOURCE = pickle.load(f).get("dataset_source", "loaded_from_disk")
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
        classe = int(self._model.predict(X_sc)[0])
        proba = self._model.predict_proba(X_sc)[0]

        # Índice local do predict_proba pode diferir do rótulo original se o modelo
        # não viu todas as classes no treino (classes_ pode ser [0, 1] sem o 2)
        known_classes = list(getattr(self._model, "classes_", [0, 1, 2]))
        local_idx = known_classes.index(classe) if classe in known_classes else 0
        local_idx = min(local_idx, len(proba) - 1)

        score_base = LABEL_MAP.get(classe, 0.55)
        confianca = float(proba[local_idx])
        return float(np.clip(score_base * confianca + score_base * (1 - confianca) * 0.8, 0.0, 1.0))

    def predict_detalhado(
        self,
        temperatura: float,
        umidade: float,
        precipitacao: float,
        vento_kmh: float,
    ) -> dict:
        X = np.array([[temperatura, umidade, precipitacao, vento_kmh]])
        X_sc = self._scaler.transform(X)
        classe = int(self._model.predict(X_sc)[0])
        proba = self._model.predict_proba(X_sc)[0]

        # classes_ indica quais classes o modelo conhece (pode ter < 3 se dados de treino
        # não cobriram todas as classes — ex.: apenas [0, 1] sem nenhum HIGH no histórico)
        known_classes = list(getattr(self._model, "classes_", [0, 1, 2]))
        class_names = ["LOW", "MEDIUM", "HIGH"]
        probas: dict[str, float] = {name: 0.0 for name in class_names}
        for i, cls_idx in enumerate(known_classes):
            if cls_idx < len(class_names):
                probas[class_names[cls_idx]] = round(float(proba[i]), 3)

        # Garante que classe está dentro dos limites
        classe_name = class_names[classe] if classe < len(class_names) else "MEDIUM"

        return {
            "score": round(self.predict(temperatura, umidade, precipitacao, vento_kmh), 3),
            "classe": classe_name,
            "probabilidades": probas,
            "features": {
                "temperatura_c": temperatura,
                "umidade_pct": umidade,
                "precipitacao_mm": precipitacao,
                "vento_kmh": vento_kmh,
            },
            "dataset_source": DATASET_SOURCE,
        }
