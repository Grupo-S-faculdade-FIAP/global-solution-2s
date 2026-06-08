"""
RiskAssessmentService — Avaliação de risco agrícola por tempestade.

Combina três fontes de dados para calcular um score de risco (0–1):
  1. Dados meteorológicos (Open-Meteo via WeatherService)
  2. Detecção de tempestade por CV (YOLO via StormDetector, geo-localizado)
  3. Modelo ML de risco agrícola (AgriRiskModel)

Score final:
  0.0 – 0.39  → LOW    (condições estáveis)
  0.4 – 0.69  → MEDIUM (atenção — monitorar)
  0.7 – 1.0   → HIGH   (risco elevado — agir)
"""

import logging
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

W_CLIMA_BASE = 0.40
W_CV_BASE = 0.40
W_ML_BASE = 0.20
CV_RADIUS_KM = 200.0
CV_DECAY_KM = 150.0

# ── Recomendações por categoria ────────────────────────────────────────────────
RECOMENDACOES = {
    "LOW": (
        "Condições estáveis. Operações agrícolas podem prosseguir normalmente. "
        "Monitore previsão para as próximas 24h."
    ),
    "MEDIUM": (
        "Atenção: condições meteorológicas adversas possíveis. "
        "Adie irrigação e aplicação de defensivos. Proteja estufas e colheitas sensíveis."
    ),
    "HIGH": (
        "RISCO ELEVADO: Tempestade detectada na região. "
        "Interrompa operações de campo imediatamente. "
        "Abrigue trabalhadores e equipamentos. Acione protocolos de emergência."
    ),
}


@dataclass
class RiskScore:
    score: float               # 0.0 – 1.0
    category: str              # LOW / MEDIUM / HIGH
    recommendation: str
    timestamp: str
    detalhes: dict             # componentes individuais do score


def _categoria(score: float) -> str:
    if score >= 0.7:
        return "HIGH"
    if score >= 0.4:
        return "MEDIUM"
    return "LOW"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _effective_weights(coverage_factor: float) -> dict[str, float]:
    """Redistribui peso do CV quando não há cobertura regional."""
    w_cv = W_CV_BASE * coverage_factor
    remainder = 1.0 - w_cv
    base_other = W_CLIMA_BASE + W_ML_BASE
    if base_other <= 0:
        return {"clima": 0.5, "cv": w_cv, "ml_agricola": 0.5}
    w_clima = remainder * (W_CLIMA_BASE / base_other)
    w_ml = remainder * (W_ML_BASE / base_other)
    return {
        "clima": round(w_clima, 3),
        "cv": round(w_cv, 3),
        "ml_agricola": round(w_ml, 3),
    }


class RiskAssessmentService:
    """
    Avaliação de risco agrícola combinando clima + CV + ML.
    """

    def __init__(self):
        from app.services.weather_service import WeatherService
        self.weather_service = WeatherService()
        self._storm_detector = None
        self._storm_detector_tried = False
        self._agri_model     = None
        self._storm_query    = None
        self._models_loaded  = False

    def _ensure_models(self) -> None:
        if not self._models_loaded:
            self._load_models()
            self._models_loaded = True

    def _get_storm_detector(self):
        """Carrega YOLO sob demanda (evita torch na importação do serviço)."""
        if self._storm_detector_tried:
            return self._storm_detector
        self._storm_detector_tried = True
        if os.environ.get("RISK_SKIP_YOLO", "").strip().lower() in ("1", "true", "yes"):
            return None
        try:
            from app.services.storm_detector import StormDetector
            model_path = Path(__file__).resolve().parents[2] / "models" / "weights" / "best.pt"
            if model_path.exists():
                self._storm_detector = StormDetector(
                    model_path=str(model_path),
                    confidence_threshold=settings.YOLO_CONFIDENCE_THRESHOLD,
                )
                logger.info("✅ StormDetector carregado")
            else:
                logger.warning("⚠️  Modelo YOLO não encontrado — CV desativado")
        except Exception as e:
            logger.warning("StormDetector não disponível: %s", e)
        return self._storm_detector

    def _load_models(self):
        """Carrega AgriRiskModel e query de alertas (YOLO é lazy)."""
        try:
            from app.services.agri_risk_model import AgriRiskModel
            self._agri_model = AgriRiskModel()
            logger.info("✅ AgriRiskModel carregado")
        except Exception as e:
            logger.warning("AgriRiskModel não disponível: %s", e)

        try:
            from app.services.storm_alerts_query import StormAlertsQueryService
            self._storm_query = StormAlertsQueryService()
        except Exception as e:
            logger.warning("StormAlertsQueryService não disponível: %s", e)

    def calculate_risk(self, lat: float, lon: float) -> RiskScore:
        """
        Calcula score de risco para uma localização.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            RiskScore com score, categoria e recomendação
        """
        self._ensure_models()
        detalhes: dict = {}

        # ── 1. Score climático ──────────────────────────────────────────────
        score_clima = 0.0
        try:
            clima = self.weather_service.get_current(lat, lon)
            score_clima = _score_climatico(clima)
            detalhes["clima"] = {
                "score":        round(score_clima, 3),
                "temperatura":  clima.get("temperature"),
                "umidade":      clima.get("humidity"),
                "precipitacao": clima.get("precipitation"),
                "vento_kmh":    round((clima.get("wind_speed") or 0) * 3.6, 1),
            }
        except Exception as e:
            logger.warning("Falha ao obter clima: %s", e)
            score_clima = 0.2  # fallback conservador
            detalhes["clima"] = {"score": score_clima, "erro": str(e)}

        # ── 2. Score de detecção CV (YOLO) geo-aware ────────────────────────
        score_cv = 0.0
        coverage_factor = 0.0
        detector = self._get_storm_detector()
        if detector or self._storm_query:
            try:
                score_cv, cv_info, coverage_factor = _score_cv(
                    detector, lat, lon, self._storm_query,
                )
                detalhes["cv"] = {
                    "score": round(score_cv, 3),
                    "coverage_factor": coverage_factor,
                    **cv_info,
                }
            except Exception as e:
                logger.warning("Falha CV: %s", e)
                detalhes["cv"] = {"score": 0.0, "coverage_factor": 0.0, "erro": str(e)}
        else:
            detalhes["cv"] = {"score": 0.0, "coverage_factor": 0.0, "status": "modelo_nao_disponivel"}

        # ── 3. Score ML agrícola ────────────────────────────────────────────
        score_ml = 0.0
        if self._agri_model and "clima" in detalhes and "erro" not in detalhes["clima"]:
            try:
                clima_data = detalhes["clima"]
                score_ml = self._agri_model.predict(
                    temperatura=clima_data.get("temperatura", 25.0),
                    umidade=clima_data.get("umidade", 60.0),
                    precipitacao=clima_data.get("precipitacao", 0.0),
                    vento_kmh=clima_data.get("vento_kmh", 10.0),
                )
                detalhes["ml_agricola"] = {"score": round(score_ml, 3)}
            except Exception as e:
                logger.warning("Falha ML: %s", e)
                detalhes["ml_agricola"] = {"score": 0.0, "erro": str(e)}
        else:
            detalhes["ml_agricola"] = {"score": 0.0, "status": "nao_disponivel"}

        # ── Score final ponderado (pesos dinâmicos por cobertura CV) ───────
        pesos = _effective_weights(coverage_factor)
        score_final = (
            score_clima * pesos["clima"] +
            score_cv    * pesos["cv"] +
            score_ml    * pesos["ml_agricola"]
        )
        score_final = float(np.clip(score_final, 0.0, 1.0))
        categoria   = _categoria(score_final)

        detalhes["pesos"] = pesos
        detalhes["pesos_base"] = {
            "clima": W_CLIMA_BASE,
            "cv": W_CV_BASE,
            "ml_agricola": W_ML_BASE,
        }
        detalhes["components"] = {
            "clima": round(score_clima, 3),
            "cv": round(score_cv, 3),
            "ml_agricola": round(score_ml, 3),
        }

        return RiskScore(
            score=round(score_final, 3),
            category=categoria,
            recommendation=RECOMENDACOES[categoria],
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            detalhes=detalhes,
        )


# ── Funções auxiliares de score ────────────────────────────────────────────────

def _score_climatico(clima: dict) -> float:
    """
    Score 0-1 baseado em variáveis meteorológicas.

    Regras baseadas em limiares agrometeorológicos brasileiros:
      - Precipitação > 20 mm/h → alto risco
      - Vento > 60 km/h → alto risco
      - Umidade > 90% + temp > 28°C → convecção favorável
    """
    score = 0.0

    precip = clima.get("precipitation") or 0.0
    vento  = (clima.get("wind_speed") or 0.0) * 3.6  # m/s → km/h
    umid   = clima.get("humidity") or 50.0
    temp   = clima.get("temperature") or 25.0

    # Precipitação (peso 40%)
    if precip >= 20:   s_p = 1.0
    elif precip >= 10: s_p = 0.8
    elif precip >= 5:  s_p = 0.5
    elif precip >= 1:  s_p = 0.2
    else:              s_p = 0.0
    score += s_p * 0.40

    # Vento (peso 25%)
    if vento >= 80:    s_v = 1.0
    elif vento >= 60:  s_v = 0.8
    elif vento >= 40:  s_v = 0.5
    elif vento >= 20:  s_v = 0.2
    else:              s_v = 0.0
    score += s_v * 0.25

    # Umidade (peso 20%) — alta umidade + calor favorece convecção
    s_u = max(0.0, (umid - 60) / 40)  # 0 em 60%, 1 em 100%
    if temp > 28: s_u = min(1.0, s_u * 1.3)
    score += s_u * 0.20

    # Temperatura extrema (peso 15%)
    if temp >= 35 or temp <= 10: s_t = 0.7
    elif temp >= 32:             s_t = 0.3
    else:                        s_t = 0.0
    score += s_t * 0.15

    return float(np.clip(score, 0.0, 1.0))


def _nearest_region_image(lat: float, lon: float) -> tuple[Optional[Path], float]:
    """Encontra captura NASA mais próxima da localização (S3 ou disco)."""
    from app.services.nasa_captures import download_nasa_to_temp, find_latest_s3_by_region
    from app.services.storm_alerts_query import REGION_COORDS

    project_root = Path(__file__).resolve().parents[4]
    pastas = [
        project_root / "data" / "nasa_captures",
        project_root / "data" / "model-dataset" / "images" / "test",
        project_root / "data" / "model-dataset" / "images" / "train",
    ]

    best_path: Optional[Path] = None
    best_dist = float("inf")

    for region_key, (rlat, rlon) in REGION_COORDS.items():
        dist = _haversine_km(lat, lon, rlat, rlon)
        if dist < best_dist:
            for pasta in pastas:
                if not pasta.exists():
                    continue
                matches = sorted(pasta.glob(f"*{region_key}*.png"), reverse=True)
                if matches:
                    best_dist = dist
                    best_path = matches[0]
                    break
            if best_path is None:
                s3_name = find_latest_s3_by_region(region_key)
                if s3_name:
                    tmp = download_nasa_to_temp(s3_name)
                    if tmp:
                        best_dist = dist
                        best_path = tmp

    if best_path is None:
        for pasta in pastas:
            if pasta.exists():
                pngs = sorted(pasta.glob("*.png"), reverse=True)
                if pngs:
                    return pngs[0], float("inf")
        s3_name = find_latest_s3_by_region("nasa_")
        if s3_name:
            tmp = download_nasa_to_temp(s3_name)
            if tmp:
                return tmp, float("inf")
    return best_path, best_dist


def _score_cv(detector, lat: float, lon: float, storm_query=None) -> tuple[float, dict, float]:
    """
    Score CV geo-localizado: alertas recentes + inferência em captura regional.
    Retorna (score 0-1, info dict, coverage_factor).
    """
    best_score = 0.0
    best_dist = float("inf")
    info: dict = {"fonte": "nenhuma"}
    coverage_factor = 0.0

    # 1. Alertas YOLO recentes com coordenadas
    if storm_query is not None:
        try:
            for det in storm_query.recent_detections(hours=48):
                dlat, dlon = det["latitude"], det["longitude"]
                dist = _haversine_km(lat, lon, dlat, dlon)
                if dist <= CV_RADIUS_KM:
                    conf = float(det.get("confidence", 0.5))
                    decay = math.exp(-dist / CV_DECAY_KM)
                    candidate = conf * decay
                    if candidate > best_score:
                        best_score = candidate
                        best_dist = dist
                        info = {
                            "fonte": "alertas",
                            "detection_id": det.get("detection_id"),
                            "distancia_km": round(dist, 1),
                            "confianca": round(conf, 3),
                            "s3_key": det.get("s3_key", ""),
                        }
                        coverage_factor = 1.0
        except Exception as e:
            logger.debug("Alertas CV indisponíveis: %s", e)

    # 2. Inferência em captura NASA da região mais próxima (requer YOLO)
    skip_infer = os.environ.get("RISK_SKIP_YOLO", "").strip().lower() in ("1", "true", "yes")
    imagem, img_dist = None, float("inf")
    try:
        imagem, img_dist = _nearest_region_image(lat, lon)
    except Exception as e:
        logger.debug("Captura regional indisponível: %s", e)
    if detector and not skip_infer and imagem and imagem.exists():
        try:
            resultado = detector.predict(str(imagem))
            raw = min(1.0, resultado.average_confidence + 0.3 * resultado.num_detections)
            if img_dist <= CV_RADIUS_KM:
                decay = math.exp(-img_dist / CV_DECAY_KM)
                candidate = raw * decay
                if candidate > best_score:
                    best_score = candidate
                    best_dist = img_dist
                    info = {
                        "fonte": "imagem",
                        "imagem": imagem.name,
                        "num_deteccoes": resultado.num_detections,
                        "conf_media": round(resultado.average_confidence, 3),
                        "tempestade": resultado.has_storm,
                        "distancia_km": round(img_dist, 1) if img_dist != float("inf") else None,
                    }
                    coverage_factor = 1.0
            elif best_score == 0.0:
                info = {
                    "fonte": "imagem_distante",
                    "imagem": imagem.name,
                    "distancia_km": round(img_dist, 1) if img_dist != float("inf") else None,
                    "status": "fora_do_raio",
                }
        except Exception as e:
            logger.debug("Inferência CV falhou: %s", e)

    if best_score == 0.0 and info.get("fonte") == "nenhuma":
        info = {"status": "sem_cobertura_regional", "distancia_km": None}

    return float(np.clip(best_score, 0.0, 1.0)), info, coverage_factor
