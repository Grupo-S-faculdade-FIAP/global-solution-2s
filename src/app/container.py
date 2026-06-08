"""Container de Dependency Injection.

Factory functions para injetar dependências em use cases e routers.
Suporta múltiplos adapters (DynamoDB, JSON mock) via settings.

Uso em FastAPI:
    @router.get("/alert")
    def my_endpoint(repo: StormAlertRepository = Depends(get_storm_repo)):
        ...

Uso em testes:
    repo = get_storm_repo()  # Retorna adapter configurado
    use_case = get_detect_storm_use_case()  # Usa repo injetado
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    from app.application.cv.detect_storm import DetectStormUseCase
    from app.domain.cv.ports import StormAlertRepository
    from app.domain.iot.ports import IoTReadingRepository
    from app.infrastructure.aws.sns_dlq import SNSDLQManager

logger = logging.getLogger(__name__)


def get_storm_repo() -> "StormAlertRepository":
    """Factory para StormAlertRepository (via settings).

    Retorna:
    - JsonStormAlertRepository se DYNAMODB_USE_MOCK=true (CI/testes)
    - DynamoDBStormAlertRepository senão (produção)

    Returns:
        Adapter configurado para persistência de alertas de tempestade.
    """
    if settings.DYNAMODB_USE_MOCK:
        from app.infrastructure.persistence.json_storm_store import (
            JsonStormAlertRepository,
        )

        logger.debug("Using JsonStormAlertRepository (mock mode)")
        return JsonStormAlertRepository()

    from app.infrastructure.aws.dynamodb_storm import DynamoDBStormAlertRepository

    logger.debug("Using DynamoDBStormAlertRepository (production mode)")
    return DynamoDBStormAlertRepository()


def get_iot_repo() -> "IoTReadingRepository":
    """Factory para IoTReadingRepository (via settings).

    Retorna:
    - JsonIoTReadingRepository se IOT_USE_MOCK=true (simula ESP32)
    - DynamoDBIoTReadingRepository senão (AWS real)

    Returns:
        Adapter configurado para leituras IoT.
    """
    if settings.IOT_USE_MOCK:
        from app.infrastructure.persistence.json_iot_store import (
            JsonIoTReadingRepository,
        )

        logger.debug("Using JsonIoTReadingRepository (mock mode)")
        return JsonIoTReadingRepository()

    from app.infrastructure.aws.dynamodb_iot import DynamoDBIoTReadingRepository

    logger.debug("Using DynamoDBIoTReadingRepository (production mode)")
    return DynamoDBIoTReadingRepository()


def get_detect_storm_use_case() -> "DetectStormUseCase":
    """Factory para DetectStormUseCase com repositório injetado.

    Cria instance de DetectStormUseCase com o adapter StormAlertRepository
    correto baseado em settings.

    Returns:
        Use case de detecção de tempestades totalmente configurado.

    Example:
        use_case = get_detect_storm_use_case()
        result = use_case.execute(bucket="images", key="storm.jpg")
    """
    from app.application.cv.detect_storm import DetectStormUseCase

    repo = get_storm_repo()
    logger.debug("Created DetectStormUseCase with %s", repo.__class__.__name__)
    return DetectStormUseCase(repo=repo)


def get_sns_dlq_manager() -> "SNSDLQManager":
    """Factory para SNSDLQManager (adapter AWS SNS/SQS DLQ).

    Returns:
        Adapter configurado para leitura e reprocessamento de mensagens DLQ.
    """
    from app.infrastructure.aws.sns_dlq import SNSDLQManager

    logger.debug("Created SNSDLQManager")
    return SNSDLQManager()
