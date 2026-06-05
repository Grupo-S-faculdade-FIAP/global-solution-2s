"""Lista capturas locais do NASA Worldview (GOES-East IR C13)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
# PNGs menores que ~100 KB costumam ser falhas de captura (página de erro / placeholder)
_MIN_BYTES = 100_000
_SAFE_NASA_NAME = re.compile(r"^nasa_[a-z0-9_]+\.png$", re.IGNORECASE)
_DATASET_DIRS = (
    _PROJECT_ROOT / "data" / "model-dataset" / "images" / "train",
    _PROJECT_ROOT / "data" / "model-dataset" / "images" / "val",
)


def nasa_captures_dir() -> Path:
    configured = Path(settings.NASA_CAPTURES_DIR)
    if configured.is_absolute():
        return configured
    return _PROJECT_ROOT / configured


def nasa_image_url(nome: str, fonte: str = "captures") -> str:
    return f"/cv/nasa/imagem/{nome}?fonte={fonte}"


def _collect_pngs(directories: list[Path]) -> list[tuple[Path, str]]:
    found: dict[str, tuple[Path, str]] = {}
    for directory in directories:
        if not directory.is_dir():
            continue
        fonte = "dataset" if "model-dataset" in str(directory) else "captures"
        for path in directory.glob("*.png"):
            if not path.is_file() or path.stat().st_size < _MIN_BYTES:
                continue
            if not _SAFE_NASA_NAME.match(path.name):
                continue
            prev = found.get(path.name)
            if prev is None or path.stat().st_mtime > prev[0].stat().st_mtime:
                found[path.name] = (path, fonte)
    items = list(found.values())
    items.sort(key=lambda item: item[0].stat().st_mtime, reverse=True)
    return items


def resolve_nasa_image(nome_arquivo: str, fonte: str = "captures") -> Path | None:
    if not _SAFE_NASA_NAME.match(nome_arquivo):
        return None
    if fonte == "dataset":
        for directory in _DATASET_DIRS:
            candidate = directory / nome_arquivo
            if candidate.is_file() and candidate.stat().st_size >= _MIN_BYTES:
                return candidate
        return None
    candidate = nasa_captures_dir() / nome_arquivo
    if candidate.is_file() and candidate.stat().st_size >= _MIN_BYTES:
        return candidate
    return None


def list_nasa_captures(limite: int = 12) -> dict:
    """Retorna metadados das capturas PNG mais recentes."""
    captures_dir = nasa_captures_dir()
    search_dirs = [captures_dir] if captures_dir.is_dir() else []
    arquivos = _collect_pngs(search_dirs)
    if not arquivos:
        arquivos = _collect_pngs(list(_DATASET_DIRS))

    capturas = []
    for path, fonte in arquivos[:limite]:
        stat = path.stat()
        capturas.append(
            {
                "arquivo": path.name,
                "criado_em": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "tamanho_kb": stat.st_size // 1024,
                "fonte": fonte,
                "url": nasa_image_url(path.name, fonte),
            }
        )

    return {
        "total": len(arquivos),
        "capturas": capturas,
        "diretorio": str(captures_dir),
    }
