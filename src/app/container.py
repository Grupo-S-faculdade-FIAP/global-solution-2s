"""Container de Dependency Injection.

Factory functions usadas via FastAPI Depends().
A escolha entre adapter mock (JSON) e produção (DynamoDB)
ocorre aqui, com base em settings.DYNAMODB_USE_MOCK.
Nunca coloque lógica de negócio aqui — apenas wiring.
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
    if settings.DYNAMODB_USE_MOCK:
        from app.infrastructure.persistence.json_iot_store import (
            JsonIoTReadingRepository,
        )
        return JsonIoTReadingRepository()

    from app.infrastructure.aws.dynamodb_iot import DynamoDBIoTReadingRepository
    return DynamoDBIoTReadingRepository()
