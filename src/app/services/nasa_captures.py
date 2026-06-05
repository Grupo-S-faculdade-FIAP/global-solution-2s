"""Lista capturas locais do NASA Worldview (GOES-East IR C13)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
# PNGs menores que ~100 KB costumam ser falhas de captura (página de erro / placeholder)
_MIN_BYTES = 100_000


def nasa_captures_dir() -> Path:
    configured = Path(settings.NASA_CAPTURES_DIR)
    if configured.is_absolute():
        return configured
    return _PROJECT_ROOT / configured


def list_nasa_captures(limite: int = 12) -> dict:
    """Retorna metadados das capturas PNG mais recentes em data/nasa_captures/."""
    captures_dir = nasa_captures_dir()
    if not captures_dir.is_dir():
        return {"total": 0, "capturas": [], "diretorio": str(captures_dir)}

    arquivos = [
        p
        for p in captures_dir.glob("*.png")
        if p.is_file() and p.stat().st_size >= _MIN_BYTES
    ]
    arquivos.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    capturas = []
    for path in arquivos[:limite]:
        stat = path.stat()
        capturas.append(
            {
                "arquivo": path.name,
                "criado_em": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "tamanho_kb": stat.st_size // 1024,
            }
        )

    return {
        "total": len(arquivos),
        "capturas": capturas,
        "diretorio": str(captures_dir),
    }
