"""Contratos (ports) do bounded context de IoT.

Nenhum import de boto3, fastapi ou flask aqui — domain é puro.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IoTReadingRepository(Protocol):
    """Contrato para persistência de leituras de sensores IoT."""

    def save(
        self,
        *,
        device_id: str,
        cidade: str,
        temperatura: float,
        umidade: float,
        reading_id: str | None = None,
    ) -> dict[str, Any]: ...

    def list_since_hours(self, hours: int) -> list[dict[str, Any]]: ...

    def ensure_seeded(self) -> None: ...
