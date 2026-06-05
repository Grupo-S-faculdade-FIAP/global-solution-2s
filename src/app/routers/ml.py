"""
ML Router — Endpoints de Machine Learning para risco agrícola.
"""

from functools import lru_cache

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from app.services.agri_risk_model import AgriRiskModel
from app.services.risk_assessment import RECOMENDACOES

router = APIRouter()


@lru_cache(maxsize=1)
def _get_agri_model() -> AgriRiskModel:
    """Lazy singleton — evita carregar pickle na importação do módulo."""
    return AgriRiskModel()


class AgriRiskRequest(BaseModel):
    temperatura: float = Field(..., description="Temperatura em °C")
    umidade: float = Field(..., description="Umidade relativa (%)")
    precipitacao: float = Field(0.0, description="Precipitação mm/h")
    vento_kmh: float = Field(0.0, description="Velocidade do vento km/h")


@router.get("/status")
def ml_status():
    """Status do módulo de Machine Learning."""
    return {"module": "machine_learning", "status": "ready"}


@router.post("/predict/agricultural-risk")
def predict_agricultural_risk(body: AgriRiskRequest):
    """
    Prevê nível de risco agrícola por condições meteorológicas.

    Usa Random Forest treinado com histórico Open-Meteo (ou sintético como fallback).
    """
    try:
        resultado = _get_agri_model().predict_detalhado(
            temperatura=body.temperatura,
            umidade=body.umidade,
            precipitacao=body.precipitacao,
            vento_kmh=body.vento_kmh,
        )
        resultado["recomendacao"] = RECOMENDACOES[resultado["classe"]]
        return resultado

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/predict/agricultural-risk")
def predict_agricultural_risk_get(
    temperatura: float = Query(..., description="Temperatura °C"),
    umidade: float = Query(..., description="Umidade relativa %"),
    precipitacao: float = Query(0.0, description="Precipitação mm/h"),
    vento_kmh: float = Query(0.0, description="Vento km/h"),
):
    """Versão GET do endpoint de risco agrícola."""
    try:
        resultado = _get_agri_model().predict_detalhado(
            temperatura=temperatura,
            umidade=umidade,
            precipitacao=precipitacao,
            vento_kmh=vento_kmh,
        )
        resultado["recomendacao"] = RECOMENDACOES[resultado["classe"]]
        return resultado

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/model/info")
def model_info():
    """Informações sobre o modelo de risco agrícola."""
    try:
        from app.services.agri_risk_model import (  # noqa: PLC0415
            DATASET_SOURCE,
            MODEL_PATH,
            MODEL_TYPE,
            SCALER_PATH,
        )
        return {
            "modelo": MODEL_TYPE,
            "classes": ["LOW", "MEDIUM", "HIGH"],
            "features": ["temperatura_c", "umidade_pct", "precipitacao_mm", "vento_kmh"],
            "dataset": DATASET_SOURCE,
            "dataset_label": (
                "INMET BDMEP — 5 estações automáticas (capitais BR)"
                if "inmet" in DATASET_SOURCE
                else "Open-Meteo Archive — 5 cidades BR (90 dias)"
                if "openmeteo" in DATASET_SOURCE
                else "Sintético — limiares EMBRAPA/INMET Brasil"
            ),
            "modelo_salvo": MODEL_PATH.exists(),
            "caminho": str(MODEL_PATH),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
