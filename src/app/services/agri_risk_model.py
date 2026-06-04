"""
AgriRiskModel — Modelo de risco agrícola por condições meteorológicas.

Classificador Random Forest treinado com dados sintéticos baseados em
limiares agrometeorológicos do Brasil (EMBRAPA / INMET).

Classes: 0=LOW, 1=MEDIUM, 2=HIGH
"""

import logging
import pickle
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

MODEL_PATH  = Path(__file__).resolve().parents[3] / "models" / "agri_risk_model.pkl"
SCALER_PATH = Path(__file__).resolve().parents[3] / "models" / "agri_risk_scaler.pkl"

# Garante que o diretório existe
MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

LABEL_MAP = {0: 0.15, 1: 0.55, 2: 0.85}   # classe → score central


def _gerar_dados_sinteticos(n: int = 5000) -> tuple[np.ndarray, np.ndarray]:
    """
    Gera dataset sintético baseado em limiares agrometeorológicos brasileiros.

    Features: [temperatura, umidade, precipitacao, vento_kmh]
    Label:    0=LOW | 1=MEDIUM | 2=HIGH
    """
    rng = np.random.default_rng(42)

    temp   = rng.uniform(10, 42, n)
    umid   = rng.uniform(20, 100, n)
    precip = rng.exponential(3, n)       # maioria próxima de 0, cauda longa
    vento  = rng.exponential(15, n)

    labels = np.zeros(n, dtype=int)

    for i in range(n):
        score = 0.0

        # Precipitação (maior peso)
        if precip[i] >= 20:    score += 3.0
        elif precip[i] >= 10:  score += 2.0
        elif precip[i] >= 5:   score += 1.0
        elif precip[i] >= 1:   score += 0.4

        # Vento
        if vento[i] >= 80:     score += 2.5
        elif vento[i] >= 60:   score += 1.5
        elif vento[i] >= 40:   score += 0.8

        # Umidade + temperatura (convecção)
        if umid[i] > 85 and temp[i] > 28:  score += 1.5
        elif umid[i] > 75 and temp[i] > 26: score += 0.8

        # Temperatura extrema
        if temp[i] >= 38 or temp[i] <= 8:   score += 1.0

        if score >= 4.0:   labels[i] = 2   # HIGH
        elif score >= 1.5: labels[i] = 1   # MEDIUM
        else:              labels[i] = 0   # LOW

    X = np.column_stack([temp, umid, precip, vento])
    return X, labels


def treinar_e_salvar():
    """Treina o modelo e salva em disco."""
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Treinando AgriRiskModel...")
    X, y = _gerar_dados_sinteticos(n=8000)

    scaler = StandardScaler()
    X_sc   = scaler.fit_transform(X)

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        min_samples_leaf=5,
        class_weight="balanced",
        n_jobs=-1,
        random_state=42,
    )
    model.fit(X_sc, y)

    with open(MODEL_PATH,  "wb") as f: pickle.dump(model,  f)
    with open(SCALER_PATH, "wb") as f: pickle.dump(scaler, f)

    # Log de acurácia rápida
    from sklearn.model_selection import cross_val_score
    scores = cross_val_score(model, X_sc, y, cv=5, scoring="accuracy")
    logger.info("AgriRiskModel treinado — acurácia CV: %.3f ± %.3f", scores.mean(), scores.std())
    return model, scaler


class AgriRiskModel:
    """
    Wrapper de inferência para o modelo de risco agrícola.
    Treina automaticamente se o arquivo .pkl não existir.
    """

    def __init__(self):
        if MODEL_PATH.exists() and SCALER_PATH.exists():
            with open(MODEL_PATH,  "rb") as f: self._model  = pickle.load(f)
            with open(SCALER_PATH, "rb") as f: self._scaler = pickle.load(f)
            logger.info("AgriRiskModel carregado de %s", MODEL_PATH)
        else:
            logger.info("Modelo não encontrado — treinando agora...")
            self._model, self._scaler = treinar_e_salvar()

    def predict(
        self,
        temperatura: float,
        umidade: float,
        precipitacao: float,
        vento_kmh: float,
    ) -> float:
        """
        Retorna score de risco 0–1.

        Args:
            temperatura:  °C
            umidade:      % (0-100)
            precipitacao: mm/h
            vento_kmh:    km/h

        Returns:
            float 0-1 representando nível de risco
        """
        X = np.array([[temperatura, umidade, precipitacao, vento_kmh]])
        X_sc = self._scaler.transform(X)

        classe = int(self._model.predict(X_sc)[0])
        proba  = self._model.predict_proba(X_sc)[0]

        # Score = posição central da classe + ajuste pela probabilidade
        score_base  = LABEL_MAP[classe]
        confianca   = float(proba[classe])
        score_final = score_base * confianca + score_base * (1 - confianca) * 0.8

        return float(np.clip(score_final, 0.0, 1.0))

    def predict_detalhado(
        self,
        temperatura: float,
        umidade: float,
        precipitacao: float,
        vento_kmh: float,
    ) -> dict:
        """Retorna predição com probabilidades por classe."""
        X    = np.array([[temperatura, umidade, precipitacao, vento_kmh]])
        X_sc = self._scaler.transform(X)

        classe = int(self._model.predict(X_sc)[0])
        proba  = self._model.predict_proba(X_sc)[0]
        score  = self.predict(temperatura, umidade, precipitacao, vento_kmh)

        return {
            "score":       round(score, 3),
            "classe":      ["LOW", "MEDIUM", "HIGH"][classe],
            "probabilidades": {
                "LOW":    round(float(proba[0]), 3),
                "MEDIUM": round(float(proba[1]), 3),
                "HIGH":   round(float(proba[2]), 3),
            },
            "features": {
                "temperatura_c":  temperatura,
                "umidade_pct":    umidade,
                "precipitacao_mm": precipitacao,
                "vento_kmh":      vento_kmh,
            },
        }
