"""Tests for model versioning and metadata management."""

import tempfile
from pathlib import Path

import pytest

from app.core.model_versioning import ModelVersion, ModelVersionManager


@pytest.fixture
def temp_registry():
    """Cria registro temporário de versões."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "versions.json"
        yield ModelVersionManager(registry_path=registry_path)


def test_model_version_serialization():
    """Testa serialização/desserialização de ModelVersion."""
    version = ModelVersion(
        name="storm_detector",
        version="1.0.0",
        checksum="abc123" * 5 + "ab",  # 32 chars
        size_bytes=123456,
        created_at="2024-06-06T10:00:00Z",
        framework="yolov5",
        input_size=640,
        classes=["storm", "cloud"],
        metadata={"experiment": "v1-baseline"},
    )

    data = version.to_dict()
    restored = ModelVersion.from_dict(data)

    assert restored.name == "storm_detector"
    assert restored.version == "1.0.0"
    assert restored.checksum == version.checksum
    assert restored.framework == "yolov5"
    assert restored.classes == ["storm", "cloud"]
    assert restored.metadata["experiment"] == "v1-baseline"


def test_register_model(temp_registry):
    """Testa registro de novo modelo."""
    # Criar arquivo fake
    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
        tmp.write(b"fake model weights" * 1000)
        model_path = Path(tmp.name)

    try:
        registered = temp_registry.register(
            model_path=model_path,
            name="storm_detector",
            version="1.0.0",
            framework="yolov5",
            input_size=640,
            classes=["storm", "cloud"],
            metadata={"training_epochs": 100},
        )

        assert registered.name == "storm_detector"
        assert registered.version == "1.0.0"
        assert registered.size_bytes > 0
        assert registered.checksum != ""
        assert len(registered.checksum) == 64  # SHA256 em hex
        assert registered.framework == "yolov5"
    finally:
        model_path.unlink()


def test_get_latest_version(temp_registry):
    """Testa obtenção de versão mais recente."""
    # Criar dois arquivos
    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp1:
        tmp1.write(b"model v1" * 100)
        path1 = Path(tmp1.name)

    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp2:
        tmp2.write(b"model v2" * 100)
        path2 = Path(tmp2.name)

    try:
        # Registrar múltiplas versões
        v1 = temp_registry.register(
            model_path=path1,
            name="detector",
            version="1.0.0",
            framework="yolov5",
            input_size=640,
            classes=["storm"],
        )

        v2 = temp_registry.register(
            model_path=path2,
            name="detector",
            version="2.0.0",
            framework="yolov5",
            input_size=640,
            classes=["storm"],
        )

        latest = temp_registry.get_latest("detector")
        assert latest is not None
        assert latest.version == "2.0.0"
    finally:
        path1.unlink()
        path2.unlink()


def test_get_specific_version(temp_registry):
    """Testa obtenção de versão específica."""
    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
        tmp.write(b"model" * 100)
        model_path = Path(tmp.name)

    try:
        temp_registry.register(
            model_path=model_path,
            name="detector",
            version="1.5.0",
            framework="yolov5",
            input_size=640,
            classes=["storm"],
        )

        found = temp_registry.get_version("detector", "1.5.0")
        assert found is not None
        assert found.version == "1.5.0"

        not_found = temp_registry.get_version("detector", "99.0.0")
        assert not_found is None
    finally:
        model_path.unlink()


def test_list_versions(temp_registry):
    """Testa listagem de versões."""
    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
        tmp.write(b"model" * 100)
        model_path = Path(tmp.name)

    try:
        for i in range(3):
            temp_registry.register(
                model_path=model_path,
                name="detector",
                version=f"1.{i}.0",
                framework="yolov5",
                input_size=640,
                classes=["storm"],
            )

        versions = temp_registry.list_versions("detector")
        assert len(versions) == 3
        # Ordenadas por mais recente primeiro
        assert versions[0].created_at >= versions[1].created_at
    finally:
        model_path.unlink()


def test_verify_checksum(temp_registry):
    """Testa verificação de integridade."""
    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
        tmp.write(b"model content")
        model_path = Path(tmp.name)

    try:
        version = temp_registry.register(
            model_path=model_path,
            name="detector",
            version="1.0.0",
            framework="yolov5",
            input_size=640,
            classes=["storm"],
        )

        # Checksum correto
        assert temp_registry.verify_checksum(model_path, version.checksum) is True

        # Checksum incorreto
        assert temp_registry.verify_checksum(model_path, "wrong_checksum") is False
    finally:
        model_path.unlink()


def test_register_nonexistent_file(temp_registry):
    """Testa rejeição de arquivo inexistente."""
    with pytest.raises(FileNotFoundError):
        temp_registry.register(
            model_path=Path("/nonexistent/path/model.pt"),
            name="detector",
            version="1.0.0",
            framework="yolov5",
            input_size=640,
            classes=["storm"],
        )


def test_registry_persistence(temp_registry):
    """Testa persistência de registro em arquivo."""
    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
        tmp.write(b"model" * 100)
        model_path = Path(tmp.name)

    try:
        # Registrar versão
        temp_registry.register(
            model_path=model_path,
            name="detector",
            version="1.0.0",
            framework="yolov5",
            input_size=640,
            classes=["storm"],
            metadata={"experiment": "baseline"},
        )

        # Criar novo manager apontando para mesmo arquivo
        new_manager = ModelVersionManager(registry_path=temp_registry.registry_path)

        # Verificar que versão foi persistida
        found = new_manager.get_version("detector", "1.0.0")
        assert found is not None
        assert found.metadata["experiment"] == "baseline"
    finally:
        model_path.unlink()
