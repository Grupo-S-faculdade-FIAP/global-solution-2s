"""Container de Dependency Injection.

Factory functions usadas via FastAPI Depends().
Alertas sempre via DynamoDB (ou JSON local só em CI com DYNAMODB_USE_MOCK).
IoT usa IOT_USE_MOCK para simular ESP32 sem hardware.
"""

from __future__ import annotations

from app.core.config import settings
from app.domain.cv.ports import StormAlertRepository
from app.domain.iot.ports import IoTReadingRepository


def get_storm_repo() -> StormAlertRepository:
    """Retorna o adapter correto para StormAlertRepository."""
    if settings.DYNAMODB_USE_MOCK:
        from app.infrastructure.persistence.json_storm_store import (
            JsonStormAlertRepository,
        )
        return JsonStormAlertRepository()

    from app.infrastructure.aws.dynamodb_storm import DynamoDBStormAlertRepository
    return DynamoDBStormAlertRepository()


def get_iot_repo() -> IoTReadingRepository:
    """Retorna o adapter correto para IoTReadingRepository."""
    if settings.IOT_USE_MOCK:
        from app.infrastructure.persistence.json_iot_store import (
            JsonIoTReadingRepository,
        )
        return JsonIoTReadingRepository()

    from app.infrastructure.aws.dynamodb_iot import DynamoDBIoTReadingRepository
    return DynamoDBIoTReadingRepository()
