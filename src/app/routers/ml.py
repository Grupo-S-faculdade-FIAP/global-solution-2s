from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
def ml_status():
    """Status do módulo de Machine Learning."""
    return {"module": "machine_learning", "status": "ready"}


@router.post("/predict/agricultural-risk")
async def predict_agricultural_risk():
    """
    Recebe dados climáticos e retorna previsão de risco agrícola.
    TODO: implementar modelo de previsão.
    """
    return {"risk_level": None, "message": "not implemented yet"}
