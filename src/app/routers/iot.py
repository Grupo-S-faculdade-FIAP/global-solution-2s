"""IoT router — recebe leituras do ESP32 e persiste no DynamoDB (ou mock JSON)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.iot_readings_store import (
    add_reading,
    list_readings_since_hours,
    use_mock_store,
)

router = APIRouter()


class SensorReading(BaseModel):
    device_id: str = Field("esp32_01", description="ID do dispositivo ESP32")
    cidade: str = Field("São Paulo", description="Cidade / localização do sensor")
    temperatura: float = Field(..., ge=-40, le=85, description="Temperatura em °C")
    umidade: float = Field(..., ge=0, le=100, description="Umidade relativa em %")


@router.get("/status")
def iot_status() -> dict:
    return {
        "module": "iot",
        "status": "ready",
        "storage": "mock_json" if use_mock_store() else "dynamodb",
        "table": "iot_readings",
    }


@router.post("/readings", status_code=201)
def receive_sensor_reading(body: SensorReading) -> dict:
    """Recebe leitura de sensor do ESP32 e persiste no DynamoDB (ou mock JSON)."""
    try:
        item = add_reading(
            device_id=body.device_id,
            cidade=body.cidade,
            temperatura=body.temperatura,
            umidade=body.umidade,
        )
        return {
            "stored": True,
            "reading_id": item["reading_id"],
            "timestamp": item["timestamp"],
            "storage": "mock_json" if use_mock_store() else "dynamodb",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar leitura: {exc}") from exc


@router.get("/readings/latest")
def get_latest_readings(hours: int = 24, limit: int = 20) -> dict:
    """Retorna as leituras mais recentes dos sensores (últimas N horas)."""
    if hours < 1 or hours > 720:
        raise HTTPException(status_code=400, detail="hours deve ser entre 1 e 720")
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit deve ser entre 1 e 100")
    try:
        readings = list_readings_since_hours(hours)[:limit]
        return {
            "readings": readings,
            "count": len(readings),
            "hours": hours,
            "storage": "mock_json" if use_mock_store() else "dynamodb",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar leituras: {exc}") from exc
