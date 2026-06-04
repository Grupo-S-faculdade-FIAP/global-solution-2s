"""
ML Router — Endpoints de Machine Learning para risco agrícola.
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter()


class AgriRiskRequest(BaseModel):
    temperatura: float = Query(..., description="Temperatura em °C")
    umidade: float     = Query(..., description="Umidade relativa (%)")
    precipitacao: float = Query(0.0, description="Precipitação mm/h")
    vento_kmh: float   = Query(0.0, description="Velocidade do vento km/h")


@router.get("/status")
def ml_status():
    """Status do módulo de Machine Learning."""
    return {"module": "machine_learning", "status": "ready"}


@router.post("/predict/agricultural-risk")
def predict_agricultural_risk(body: AgriRiskRequest):
    """
    Prevê nível de risco agrícola por condições meteorológicas.

    Usa Random Forest treinado com dados agrometeorológicos brasileiros (EMBRAPA/INMET).

    Body:
      - temperatura:   °C (ex: 28.5)
      - umidade:       % (ex: 85.0)
      - precipitacao:  mm/h (ex: 12.0)
      - vento_kmh:     km/h (ex: 45.0)

    Returns:
      - score:  0–1 (quanto maior, maior o risco)
      - classe: LOW / MEDIUM / HIGH
      - probabilidades: por classe
      - recomendacao: ação sugerida
    """
    try:
        from app.services.agri_risk_model import AgriRiskModel
        from app.services.risk_assessment import RECOMENDACOES

        model = AgriRiskModel()
        resultado = model.predict_detalhado(
            temperatura=body.temperatura,
            umidade=body.umidade,
            precipitacao=body.precipitacao,
            vento_kmh=body.vento_kmh,
        )
        resultado["recomendacao"] = RECOMENDACOES[resultado["classe"]]
        return resultado

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predict/agricultural-risk")
def predict_agricultural_risk_get(
    temperatura: float = Query(..., description="Temperatura °C"),
    umidade: float     = Query(..., description="Umidade relativa %"),
    precipitacao: float = Query(0.0, description="Precipitação mm/h"),
    vento_kmh: float   = Query(0.0, description="Vento km/h"),
):
    """
    Versão GET do endpoint de risco agrícola (facilita testes via browser/curl).

    Exemplo:
        GET /ml/predict/agricultural-risk?temperatura=32&umidade=90&precipitacao=15&vento_kmh=50
    """
    try:
        from app.services.agri_risk_model import AgriRiskModel
        from app.services.risk_assessment import RECOMENDACOES

        model = AgriRiskModel()
        resultado = model.predict_detalhado(
            temperatura=temperatura,
            umidade=umidade,
            precipitacao=precipitacao,
            vento_kmh=vento_kmh,
        )
        resultado["recomendacao"] = RECOMENDACOES[resultado["classe"]]
        return resultado

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model/info")
def model_info():
    """Informações sobre o modelo de risco agrícola."""
    try:
        from app.services.agri_risk_model import MODEL_PATH, SCALER_PATH
        return {
            "modelo": "RandomForestClassifier",
            "classes": ["LOW", "MEDIUM", "HIGH"],
            "features": ["temperatura_c", "umidade_pct", "precipitacao_mm", "vento_kmh"],
            "dataset": "Sintético — limiares EMBRAPA/INMET Brasil",
            "modelo_salvo": MODEL_PATH.exists(),
            "caminho": str(MODEL_PATH),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
