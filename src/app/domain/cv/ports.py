"""Contratos (ports) do bounded context de Computer Vision / Storms.

Nenhum import de boto3, fastapi ou flask aqui — domain é puro.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StormAlertRepository(Protocol):
    """Contrato para persistência de alertas de tempestade."""

    def save(
        self,
        *,
        s3_key: str,
        detection_count: int,
        bucket: str,
        alert_id: str | None = None,
        simulated: bool = False,
        classes: list[str] | None = None,
        confidence: float | None = None,
    ) -> dict[str, Any]: ...

    def list_since_hours(self, hours: int) -> list[dict[str, Any]]: ...

    def list_since_days(self, days: int) -> list[dict[str, Any]]: ...

    def ensure_seeded(self) -> None: ...
