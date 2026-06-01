from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
def iot_status():
    """Status do módulo IoT."""
    return {"module": "iot", "status": "ready"}


@router.post("/readings")
async def receive_sensor_reading():
    """
    Recebe leitura de sensor do ESP32 e armazena no DynamoDB.
    TODO: implementar persistência.
    """
    return {"stored": False, "message": "not implemented yet"}


@router.get("/readings/latest")
async def get_latest_readings():
    """
    Retorna as leituras mais recentes dos sensores.
    TODO: implementar busca no DynamoDB.
    """
    return {"readings": [], "message": "not implemented yet"}
