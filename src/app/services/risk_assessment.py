"""
RiskAssessmentService — Avaliação de risco agrícola por tempestade.

Combina três fontes de dados para calcular um score de risco (0–1):
  1. Dados meteorológicos (Open-Meteo via WeatherService)
  2. Detecção de tempestade por CV (YOLO via StormDetector, se modelo disponível)
  3. Modelo ML de risco agrícola (AgriRiskModel)

Score final:
  0.0 – 0.39  → LOW    (condições estáveis)
  0.4 – 0.69  → MEDIUM (atenção — monitorar)
  0.7 – 1.0   → HIGH   (risco elevado — agir)
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

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


class RiskAssessmentService:
    """
    Avaliação de risco agrícola combinando clima + CV + ML.
    """

    def __init__(self):
        from app.services.weather_service import WeatherService
        self.weather_service = WeatherService()
        self._storm_detector = None
        self._agri_model     = None
        self._load_models()

    def _load_models(self):
        """Carrega StormDetector e AgriRiskModel se disponíveis."""
        try:
            from app.services.storm_detector import StormDetector
            model_path = Path(__file__).resolve().parents[2] / "models" / "weights" / "best.pt"
            if model_path.exists():
                self._storm_detector = StormDetector(
                    model_path=str(model_path),
                    confidence_threshold=0.25,
                )
                logger.info("✅ StormDetector carregado")
            else:
                logger.warning("⚠️  Modelo YOLO não encontrado — CV desativado")
        except Exception as e:
            logger.warning("StormDetector não disponível: %s", e)

        try:
            from app.services.agri_risk_model import AgriRiskModel
            self._agri_model = AgriRiskModel()
            logger.info("✅ AgriRiskModel carregado")
        except Exception as e:
            logger.warning("AgriRiskModel não disponível: %s", e)

    def calculate_risk(self, lat: float, lon: float) -> RiskScore:
        """
        Calcula score de risco para uma localização.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            RiskScore com score, categoria e recomendação
        """
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

        # ── 2. Score de detecção CV (YOLO) ──────────────────────────────────
        score_cv = 0.0
        if self._storm_detector:
            try:
                score_cv, cv_info = _score_cv(self._storm_detector)
                detalhes["cv"] = {"score": round(score_cv, 3), **cv_info}
            except Exception as e:
                logger.warning("Falha CV: %s", e)
                detalhes["cv"] = {"score": 0.0, "erro": str(e)}
        else:
            detalhes["cv"] = {"score": 0.0, "status": "modelo_nao_disponivel"}

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

        # ── Score final ponderado ───────────────────────────────────────────
        # Clima: 40% | CV: 40% | ML: 20%
        score_final = (
            score_clima * 0.40 +
            score_cv    * 0.40 +
            score_ml    * 0.20
        )
        score_final = float(np.clip(score_final, 0.0, 1.0))
        categoria   = _categoria(score_final)

        detalhes["pesos"] = {"clima": 0.40, "cv": 0.40, "ml_agricola": 0.20}

        return RiskScore(
            score=round(score_final, 3),
            category=categoria,
            recommendation=RECOMENDACOES[categoria],
            timestamp=datetime.now(timezone.utc).isoformat() + "Z",
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
    peso_total = 0.0

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
    score += s_p * 0.40; peso_total += 0.40

    # Vento (peso 25%)
    if vento >= 80:    s_v = 1.0
    elif vento >= 60:  s_v = 0.8
    elif vento >= 40:  s_v = 0.5
    elif vento >= 20:  s_v = 0.2
    else:              s_v = 0.0
    score += s_v * 0.25; peso_total += 0.25

    # Umidade (peso 20%) — alta umidade + calor favorece convecção
    s_u = max(0.0, (umid - 60) / 40)  # 0 em 60%, 1 em 100%
    if temp > 28: s_u = min(1.0, s_u * 1.3)
    score += s_u * 0.20; peso_total += 0.20

    # Temperatura extrema (peso 15%)
    if temp >= 35 or temp <= 10: s_t = 0.7
    elif temp >= 32:             s_t = 0.3
    else:                        s_t = 0.0
    score += s_t * 0.15; peso_total += 0.15  # noqa: F841 (peso_total == 1.0 por construção)

    # peso_total é sempre 1.0 (0.40 + 0.25 + 0.20 + 0.15), divisão desnecessária
    return float(np.clip(score, 0.0, 1.0))


def _score_cv(detector) -> tuple[float, dict]:
    """
    Tenta detectar storm na imagem de teste mais recente disponível.
    Retorna (score 0-1, info dict).
    """
    from pathlib import Path

    # Procura imagem de teste mais recente
    pastas = [
        Path(__file__).resolve().parents[4] / "data" / "nasa_captures",
        Path(__file__).resolve().parents[4] / "data" / "model-dataset" / "images" / "test",
    ]
    imagem = None
    for pasta in pastas:
        if pasta.exists():
            pngs = sorted(pasta.glob("*.png"), reverse=True)
            if pngs:
                imagem = pngs[0]
                break

    if not imagem:
        return 0.0, {"status": "sem_imagem_disponivel"}

    resultado = detector.predict(str(imagem))
    score_cv  = min(1.0, resultado.average_confidence + 0.3 * resultado.num_detections)

    return score_cv, {
        "imagem":           imagem.name,
        "num_deteccoes":    resultado.num_detections,
        "conf_media":       round(resultado.average_confidence, 3),
        "tempestade":       resultado.has_storm,
    }
