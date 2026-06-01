from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
def cv_status():
    """Status do módulo de Computer Vision."""
    return {"module": "computer_vision", "status": "ready"}


@router.post("/detect/fire")
async def detect_fire():
    """
    Recebe imagem de satélite e retorna detecções de queimadas via YOLOv8.
    TODO: implementar serviço de detecção.
    """
    return {"detections": [], "message": "not implemented yet"}
