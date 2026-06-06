"""Model versioning e metadata management.

Mantém registro de versões de modelos, hash de checksum, e metadados.
"""

import hashlib
import json
import logging
import pathlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModelVersion:
    """Informações de versão de um modelo."""

    name: str
    version: str
    checksum: str  # SHA256 do arquivo .pt
    size_bytes: int
    created_at: str  # ISO format
    framework: str  # "yolov5", "pytorch", etc.
    input_size: int  # Tamanho de entrada esperado (ex: 640)
    classes: list[str]  # Classes detectáveis
    metadata: dict[str, Any]  # Metadata customizada (tags, experimento, etc.)

    def to_dict(self) -> dict[str, Any]:
        """Serializa versão para dict."""
        return {
            "name": self.name,
            "version": self.version,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at,
            "framework": self.framework,
            "input_size": self.input_size,
            "classes": self.classes,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelVersion":
        """Desserializa versão de dict."""
        return cls(**data)


class ModelVersionManager:
    """Gerencia versões de modelos e metadados."""

    def __init__(self, registry_path: Optional[pathlib.Path] = None):
        """
        Args:
            registry_path: Path para arquivo JSON de registro de versões.
                Se None, usa ~/.cache/model_versions.json
        """
        if registry_path is None:
            registry_path = (
                pathlib.Path.home() / ".cache" / "model_versions.json"
            )
        self.registry_path = registry_path
        self.versions: dict[str, list[ModelVersion]] = self._load_registry()

    def _load_registry(self) -> dict[str, list[ModelVersion]]:
        """Carrega registro de versões de arquivo."""
        if not self.registry_path.exists():
            logger.debug(
                "Model registry not found at %s, starting fresh",
                self.registry_path,
            )
            return {}

        try:
            with open(self.registry_path) as f:
                data = json.load(f)
            # Converte dict de versões de volta para objetos
            return {
                name: [ModelVersion.from_dict(v) for v in versions]
                for name, versions in data.items()
            }
        except Exception as exc:
            logger.error("Failed to load model registry: %s", exc)
            return {}

    def _save_registry(self) -> None:
        """Salva registro de versões em arquivo."""
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.registry_path, "w") as f:
                json.dump(
                    {
                        name: [v.to_dict() for v in versions]
                        for name, versions in self.versions.items()
                    },
                    f,
                    indent=2,
                )
        except Exception as exc:
            logger.error("Failed to save model registry: %s", exc)

    @staticmethod
    def _compute_checksum(file_path: pathlib.Path) -> str:
        """Computa SHA256 de arquivo."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def register(
        self,
        model_path: pathlib.Path,
        name: str,
        version: str,
        framework: str,
        input_size: int,
        classes: list[str],
        metadata: Optional[dict[str, Any]] = None,
    ) -> ModelVersion:
        """Registra versão de novo modelo.

        Args:
            model_path: Path do arquivo .pt.
            name: Nome do modelo (ex: "storm_detector").
            version: Tag de versão (ex: "1.0.0", "v2-exp-5").
            framework: Framework usado (ex: "yolov5").
            input_size: Tamanho de entrada esperado.
            classes: Lista de classes detectáveis.
            metadata: Dict customizado com info adicional.

        Returns:
            ModelVersion registrada.

        Raises:
            FileNotFoundError: Se model_path não existir.
        """
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        checksum = self._compute_checksum(model_path)
        size_bytes = model_path.stat().st_size
        created_at = datetime.utcnow().isoformat() + "Z"

        model_version = ModelVersion(
            name=name,
            version=version,
            checksum=checksum,
            size_bytes=size_bytes,
            created_at=created_at,
            framework=framework,
            input_size=input_size,
            classes=classes,
            metadata=metadata or {},
        )

        if name not in self.versions:
            self.versions[name] = []
        self.versions[name].append(model_version)
        self._save_registry()

        logger.info(
            "Registered model %s version %s (checksum: %s)",
            name, version, checksum[:12],
        )
        return model_version

    def get_latest(self, model_name: str) -> Optional[ModelVersion]:
        """Retorna versão mais recente de um modelo.

        Args:
            model_name: Nome do modelo.

        Returns:
            ModelVersion mais recente ou None se não existe.
        """
        versions = self.versions.get(model_name, [])
        if not versions:
            return None
        return max(versions, key=lambda v: v.created_at)

    def get_version(self, model_name: str, version: str) -> Optional[ModelVersion]:
        """Retorna versão específica de um modelo.

        Args:
            model_name: Nome do modelo.
            version: Tag de versão.

        Returns:
            ModelVersion ou None se não existe.
        """
        for v in self.versions.get(model_name, []):
            if v.version == version:
                return v
        return None

    def list_versions(self, model_name: str) -> list[ModelVersion]:
        """Lista todas as versões de um modelo."""
        return sorted(
            self.versions.get(model_name, []),
            key=lambda v: v.created_at,
            reverse=True,
        )

    def verify_checksum(
        self,
        file_path: pathlib.Path,
        expected_checksum: str,
    ) -> bool:
        """Verifica integridade de arquivo comparando checksums.

        Args:
            file_path: Path do arquivo.
            expected_checksum: Checksum esperado.

        Returns:
            True se checksums correspondem, False caso contrário.
        """
        actual = self._compute_checksum(file_path)
        match = actual == expected_checksum
        if not match:
            logger.warning(
                "Checksum mismatch for %s: expected %s, got %s",
                file_path, expected_checksum[:12], actual[:12],
            )
        return match
