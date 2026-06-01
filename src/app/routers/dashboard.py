from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
def dashboard_status():
    """Status do módulo de Dashboard."""
    return {"module": "dashboard", "status": "ready"}


@router.get("/climate/current")
async def get_current_climate():
    """
    Retorna dados climáticos atuais para exibição no dashboard.
    TODO: integrar com NASA FIRMS e dados de sensores.
    """
    return {"data": None, "message": "not implemented yet"}
