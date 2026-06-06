"""
Otimização de limiares de risco agrícola via Algoritmo Genético (DEAP).

Evolui parâmetros de _classificar_risco / score_contínuo para balancear classes
e maximizar consistência no cache INMET.
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
try:
    from lightgbm import LGBMRegressor as _FitnessRegressor
except (OSError, ImportError):
    from sklearn.ensemble import HistGradientBoostingRegressor as _FitnessRegressor

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_THRESHOLDS_PATH = _PROJECT_ROOT / "models" / "agri_risk_thresholds.json"
_INMET_CACHE = _PROJECT_ROOT / "data" / "weather" / "inmet" / "training_cache.csv"
_INMET_SAMPLE = _PROJECT_ROOT / "data" / "weather" / "inmet" / "sample_inmet_bdmep.csv"

TARGET_DIST = {0: 0.70, 1: 0.25, 2: 0.05}
MAX_RULE_SCORE = 6.0


@dataclass
class AgriThresholds:
    precip_t4: float = 20.0
    precip_t3: float = 10.0
    precip_t2: float = 5.0
    precip_t1: float = 1.0
    wind_t3: float = 80.0
    wind_t2: float = 60.0
    wind_t1: float = 40.0
    humidity_high: float = 85.0
    temp_convective: float = 28.0
    humidity_mid: float = 75.0
    temp_convective_mid: float = 26.0
    temp_extreme_high: float = 38.0
    temp_extreme_low: float = 8.0
    cutoff_high: float = 4.0
    cutoff_medium: float = 1.5
    w_precip_t4: float = 3.0
    w_precip_t3: float = 2.0
    w_precip_t2: float = 1.0
    w_precip_t1: float = 0.4
    w_wind_t3: float = 2.5
    w_wind_t2: float = 1.5
    w_wind_t1: float = 0.8
    w_humidity_high: float = 1.5
    w_humidity_mid: float = 0.8
    w_temp_extreme: float = 1.0


def load_thresholds(path: Path | None = None) -> AgriThresholds:
    p = path or DEFAULT_THRESHOLDS_PATH
    if not p.exists():
        return AgriThresholds()
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return AgriThresholds(**{k: v for k, v in data.items() if k in AgriThresholds.__dataclass_fields__})


def save_thresholds(thresholds: AgriThresholds, path: Path | None = None) -> Path:
    p = path or DEFAULT_THRESHOLDS_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(asdict(thresholds), f, indent=2)
    return p


def rule_raw_score(
    temperatura: float,
    umidade: float,
    precipitacao: float,
    vento_kmh: float,
    th: AgriThresholds | None = None,
) -> float:
    """Score bruto 0–MAX_RULE_SCORE a partir das regras parametrizadas."""
    t = th or AgriThresholds()
    score = 0.0
    if precipitacao >= t.precip_t4:
        score += t.w_precip_t4
    elif precipitacao >= t.precip_t3:
        score += t.w_precip_t3
    elif precipitacao >= t.precip_t2:
        score += t.w_precip_t2
    elif precipitacao >= t.precip_t1:
        score += t.w_precip_t1
    if vento_kmh >= t.wind_t3:
        score += t.w_wind_t3
    elif vento_kmh >= t.wind_t2:
        score += t.w_wind_t2
    elif vento_kmh >= t.wind_t1:
        score += t.w_wind_t1
    if umidade > t.humidity_high and temperatura > t.temp_convective:
        score += t.w_humidity_high
    elif umidade > t.humidity_mid and temperatura > t.temp_convective_mid:
        score += t.w_humidity_mid
    if temperatura >= t.temp_extreme_high or temperatura <= t.temp_extreme_low:
        score += t.w_temp_extreme
    return score


def classificar_com_thresholds(
    temperatura: float,
    umidade: float,
    precipitacao: float,
    vento_kmh: float,
    th: AgriThresholds,
) -> int:
    score = rule_raw_score(temperatura, umidade, precipitacao, vento_kmh, th)
    if score >= th.cutoff_high:
        return 2
    if score >= th.cutoff_medium:
        return 1
    return 0


def score_continuo_normalizado(
    temperatura: float,
    umidade: float,
    precipitacao: float,
    vento_kmh: float,
    th: AgriThresholds | None = None,
) -> float:
    raw = rule_raw_score(temperatura, umidade, precipitacao, vento_kmh, th)
    return float(np.clip(raw / MAX_RULE_SCORE, 0.0, 1.0))


def classe_from_score(score: float) -> str:
    if score >= 0.7:
        return "HIGH"
    if score >= 0.4:
        return "MEDIUM"
    return "LOW"


def estimate_probas(score: float, th: AgriThresholds | None = None) -> dict[str, float]:
    """Probabilidades suaves a partir da distância aos cutoffs normalizados."""
    t = th or load_thresholds()
    low_cut = t.cutoff_medium / MAX_RULE_SCORE
    high_cut = t.cutoff_high / MAX_RULE_SCORE
    p_high = float(np.clip((score - high_cut) / max(0.01, 1.0 - high_cut), 0.0, 1.0))
    p_low = float(np.clip((low_cut - score) / max(0.01, low_cut), 0.0, 1.0))
    p_med = float(np.clip(1.0 - p_high - p_low, 0.0, 1.0))
    total = p_low + p_med + p_high or 1.0
    return {
        "LOW": round(p_low / total, 3),
        "MEDIUM": round(p_med / total, 3),
        "HIGH": round(p_high / total, 3),
    }


def _load_xy_from_csv() -> tuple[np.ndarray, np.ndarray]:
    from app.clients.inmet import InmetClient  # noqa: PLC0415

    for path in (_INMET_CACHE, _INMET_SAMPLE):
        if path.exists():
            records = InmetClient.load_cache_csv(path)
            rows = [r.as_features() for r in records]
            if len(rows) < 50:
                continue
            return np.array(rows, dtype=float), records
    raise FileNotFoundError("Cache INMET ausente para GA")


def _genes_to_thresholds(genes: list[float]) -> AgriThresholds:
    g = genes
    return AgriThresholds(
        precip_t4=max(g[0], g[1] + 0.5),
        precip_t3=max(g[1], g[2] + 0.5),
        precip_t2=max(g[2], g[3] + 0.1),
        precip_t1=max(0.1, g[3]),
        wind_t3=max(g[4], g[5] + 1),
        wind_t2=max(g[5], g[6] + 1),
        wind_t1=max(10.0, g[6]),
        humidity_high=min(99.0, max(70.0, g[7])),
        temp_convective=min(40.0, max(20.0, g[8])),
        humidity_mid=min(95.0, max(60.0, g[9])),
        temp_convective_mid=min(38.0, max(18.0, g[10])),
        temp_extreme_high=min(45.0, max(32.0, g[11])),
        temp_extreme_low=min(15.0, max(0.0, g[12])),
        cutoff_high=max(g[14] + 0.5, g[13]),
        cutoff_medium=max(0.5, g[13]),
        w_precip_t4=max(1.0, g[15]),
        w_precip_t3=max(0.5, g[16]),
        w_precip_t2=max(0.2, g[17]),
        w_precip_t1=max(0.1, g[18]),
        w_wind_t3=max(1.0, g[19]),
        w_wind_t2=max(0.5, g[20]),
        w_wind_t1=max(0.2, g[21]),
        w_humidity_high=max(0.5, g[22]),
        w_humidity_mid=max(0.2, g[23]),
        w_temp_extreme=max(0.2, g[24]),
    )


def _balance_penalty(labels: np.ndarray) -> float:
    n = len(labels)
    if n == 0:
        return 1.0
    dist = {c: float(np.sum(labels == c)) / n for c in (0, 1, 2)}
    return sum(abs(dist[c] - TARGET_DIST[c]) for c in TARGET_DIST)


def evaluate_thresholds(th: AgriThresholds, X: np.ndarray, records) -> float:
    labels = np.array([
        classificar_com_thresholds(r.temperatura, r.umidade, r.precipitacao, r.vento_kmh, th)
        for r in records
    ], dtype=int)
    y_cont = np.array([
        score_continuo_normalizado(r.temperatura, r.umidade, r.precipitacao, r.vento_kmh, th)
        for r in records
    ], dtype=float)

    balance = _balance_penalty(labels)
    # Proxy de qualidade: regressão rápida preve score contínuo
    scaler = StandardScaler()
    X_sc = scaler.fit_transform(X)
    try:
        model = _FitnessRegressor(
            n_estimators=50,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            verbose=-1,
        )
    except TypeError:
        model = _FitnessRegressor(max_iter=50, max_depth=6, learning_rate=0.1, random_state=42)
    try:
        cv_r2 = cross_val_score(model, X_sc, y_cont, cv=3, scoring="r2").mean()
    except ValueError:
        cv_r2 = 0.0

    # Fitness: menor penalidade de balance + maior R2
    return float(-balance + 0.5 * max(cv_r2, 0.0))


def optimize_thresholds(
    generations: int = 15,
    population: int = 40,
    seed: int = 42,
    sample_size: int = 3000,
) -> AgriThresholds:
    """Executa AG e retorna melhores limiares (requer pacote `deap` — só offline/CI)."""
    from deap import algorithms, base, creator, tools  # noqa: PLC0415

    random.seed(seed)
    np.random.seed(seed)

    X, records = _load_xy_from_csv()
    if len(records) > sample_size:
        idx = np.random.default_rng(seed).choice(len(records), sample_size, replace=False)
        records = [records[i] for i in idx]
        X = X[idx]

    default_th = AgriThresholds()
    baseline = evaluate_thresholds(default_th, X, records)
    logger.info("Fitness baseline (default thresholds): %.4f", baseline)

    if hasattr(creator, "FitnessMax"):
        del creator.FitnessMax
    if hasattr(creator, "Individual"):
        del creator.Individual

    creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    creator.create("Individual", list, fitness=creator.FitnessMax)

    toolbox = base.Toolbox()

    bounds = [
        (8, 35), (4, 20), (2, 12), (0.1, 3),      # precip
        (50, 100), (35, 80), (15, 60),             # wind
        (75, 95), (24, 34), (65, 85), (22, 30),   # humidity/temp
        (34, 42), (0, 12),                         # temp extreme
        (0.8, 3.0), (2.5, 5.5),                    # cutoffs medium/high
        (2, 4), (1, 3), (0.5, 2), (0.2, 1),       # w_precip
        (1.5, 3.5), (1, 2.5), (0.4, 1.5),          # w_wind
        (0.8, 2.5), (0.4, 1.5), (0.3, 1.5),        # w_humidity, w_temp
    ]

    def _random_gene(lo: float, hi: float) -> float:
        return random.uniform(lo, hi)

    toolbox.register("attr_float", _random_gene, 0, 1)
    toolbox.register(
        "individual",
        tools.initIterate,
        creator.Individual,
        lambda: [_random_gene(lo, hi) for lo, hi in bounds],
    )
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    def _eval(individual: list[float]) -> tuple[float]:
        th = _genes_to_thresholds(individual)
        return (evaluate_thresholds(th, X, records),)

    toolbox.register("evaluate", _eval)
    toolbox.register("mate", tools.cxBlend, alpha=0.4)
    toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=0.15, indpb=0.2)
    toolbox.register("select", tools.selTournament, tournsize=3)

    pop = toolbox.population(n=population)
    hof = tools.HallOfFame(1)
    algorithms.eaSimple(
        pop, toolbox, cxpb=0.6, mutpb=0.3, ngen=generations, halloffame=hof, verbose=False,
    )

    best = _genes_to_thresholds(list(hof[0]))
    best_fitness = evaluate_thresholds(best, X, records)
    logger.info("Fitness GA: %.4f (baseline %.4f)", best_fitness, baseline)

    if best_fitness < baseline:
        logger.warning("GA não superou baseline — mantendo limiares default")
        return default_th
    return best
