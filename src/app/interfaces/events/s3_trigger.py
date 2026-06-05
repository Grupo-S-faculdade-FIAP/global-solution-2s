"""Handler para eventos S3 recebidos pelo Lambda.

Responsabilidade única: despachar para DetectStormUseCase.
Não contém lógica de negócio.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.application.cv.detect_storm import DetectStormUseCase

logger = logging.getLogger(__name__)


class S3TriggerHandler:
    """Despacha eventos S3 (ObjectCreated) para o use case de detecção."""

    def __init__(self, use_case: "DetectStormUseCase") -> None:
        self._uc = use_case

    def handle(self, event: dict[str, Any]) -> dict[str, Any]:
        results = []
        for record in event.get("Records", []):
            bucket = record["s3"]["bucket"]["name"]
            key = record["s3"]["object"]["key"]
            logger.info("S3 trigger: s3://%s/%s", bucket, key)
            result = self._uc.execute(bucket=bucket, key=key)
            results.append(result)
        return {"processed": len(results), "results": results}
