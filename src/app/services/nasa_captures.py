"""Capturas NASA Worldview (GOES-East IR C13) — S3 canônico, disco local opcional."""

from __future__ import annotations

import logging
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
# PNGs menores que ~100 KB costumam ser falhas de captura (página de erro / placeholder)
_MIN_BYTES = 100_000
_PRESIGNED_EXPIRES = 3600
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


def _nasa_s3_prefix() -> str:
    return (settings.NASA_S3_PREFIX or "nasa-satellite").strip("/") + "/"


def _bucket_configured() -> bool:
    return bool((settings.S3_BUCKET_IMAGES or "").strip())


def _s3_client():
    import boto3

    return boto3.client("s3", region_name=settings.AWS_REGION)


def nasa_image_url(nome: str, fonte: str = "captures", s3_key: str | None = None) -> str:
    if fonte == "s3" and s3_key:
        url = presigned_nasa_url(s3_key)
        if url:
            return url
    return f"/cv/nasa/imagem/{nome}?fonte={fonte}"


def presigned_nasa_url(s3_key: str, expires: int = _PRESIGNED_EXPIRES) -> str | None:
    if not _bucket_configured():
        return None
    try:
        return _s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET_IMAGES, "Key": s3_key},
            ExpiresIn=expires,
        )
    except Exception as exc:
        logger.warning("Presigned URL falhou para %s: %s", s3_key, exc)
        return None


def _list_s3_nasa_objects(max_items: int = 500) -> list[dict[str, Any]]:
    if not _bucket_configured():
        return []

    bucket = settings.S3_BUCKET_IMAGES
    prefix = _nasa_s3_prefix()
    items: list[dict[str, Any]] = []
    token: str | None = None

    try:
        while len(items) < max_items:
            kwargs: dict[str, Any] = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": 1000}
            if token:
                kwargs["ContinuationToken"] = token
            response = _s3_client().list_objects_v2(**kwargs)
            for obj in response.get("Contents", []):
                key = obj.get("Key", "")
                name = Path(key).name
                size = int(obj.get("Size", 0))
                if not name.endswith(".png") or size < _MIN_BYTES:
                    continue
                if not _SAFE_NASA_NAME.match(name):
                    continue
                items.append(
                    {
                        "s3_key": key,
                        "arquivo": name,
                        "criado_em": obj["LastModified"].astimezone(timezone.utc).isoformat(),
                        "tamanho_kb": size // 1024,
                        "last_modified": obj["LastModified"],
                    }
                )
            if not response.get("IsTruncated"):
                break
            token = response.get("NextContinuationToken")
    except Exception as exc:
        logger.warning("Listagem S3 NASA falhou: %s", exc)

    items.sort(key=lambda item: item["last_modified"], reverse=True)
    return items[:max_items]


def s3_has_capture(regiao_nome: str, data: str) -> bool:
    """Verifica se já existe captura da região na data (YYYY-MM-DD) no S3."""
    if not _bucket_configured():
        return False
    try:
        dt = datetime.strptime(data, "%Y-%m-%d")
        prefix = f"{_nasa_s3_prefix()}{dt.year}/{dt.month:02d}/{dt.day:02d}/"
        response = _s3_client().list_objects_v2(
            Bucket=settings.S3_BUCKET_IMAGES,
            Prefix=prefix,
            MaxKeys=200,
        )
        date_token = data.replace("-", "")
        for obj in response.get("Contents", []):
            name = Path(obj.get("Key", "")).name
            if name.startswith(f"{regiao_nome}_") and date_token in name:
                if int(obj.get("Size", 0)) >= _MIN_BYTES:
                    return True
    except Exception as exc:
        logger.debug("s3_has_capture falhou: %s", exc)
    return False


def resolve_nasa_s3_key(nome_arquivo: str) -> str | None:
    if not _SAFE_NASA_NAME.match(nome_arquivo) or not _bucket_configured():
        return None
    prefix = _nasa_s3_prefix()
    try:
        paginator = _s3_client().get_paginator("list_objects_v2")
        for page in paginator.paginate(
            Bucket=settings.S3_BUCKET_IMAGES,
            Prefix=prefix,
        ):
            for obj in page.get("Contents", []):
                if Path(obj.get("Key", "")).name == nome_arquivo:
                    if int(obj.get("Size", 0)) >= _MIN_BYTES:
                        return obj["Key"]
    except Exception as exc:
        logger.warning("resolve_nasa_s3_key falhou: %s", exc)
    return None


def stream_nasa_from_s3(s3_key: str) -> tuple[Any, int]:
    """Retorna (body stream, content_length) do objeto S3."""
    response = _s3_client().get_object(Bucket=settings.S3_BUCKET_IMAGES, Key=s3_key)
    return response["Body"], int(response.get("ContentLength", 0))


def download_nasa_to_temp(nome_arquivo: str) -> Path | None:
    """Baixa captura do S3 para arquivo temporário (inferência ML)."""
    s3_key = resolve_nasa_s3_key(nome_arquivo)
    if not s3_key:
        return None
    try:
        body, _ = stream_nasa_from_s3(s3_key)
        tmp = Path(tempfile.gettempdir()) / nome_arquivo
        tmp.write_bytes(body.read())
        return tmp
    except Exception as exc:
        logger.warning("download_nasa_to_temp falhou: %s", exc)
        return None


def find_latest_s3_by_region(region_key: str) -> str | None:
    """Retorna o nome do arquivo NASA mais recente no S3 para um prefixo de região."""
    matches = [
        item for item in _list_s3_nasa_objects(limite=500)
        if region_key in item["arquivo"]
    ]
    return matches[0]["arquivo"] if matches else None


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
    if fonte == "s3":
        return download_nasa_to_temp(nome_arquivo)
    candidate = nasa_captures_dir() / nome_arquivo
    if candidate.is_file() and candidate.stat().st_size >= _MIN_BYTES:
        return candidate
    if _bucket_configured():
        return download_nasa_to_temp(nome_arquivo)
    return None


def list_nasa_captures(limite: int = 12) -> dict:
    """Retorna metadados das capturas PNG mais recentes (S3 prioritário)."""
    storage = "local"
    arquivos_s3 = _list_s3_nasa_objects() if _bucket_configured() else []

    if arquivos_s3:
        storage = "s3"
        total = len(arquivos_s3)
        capturas = []
        for item in arquivos_s3[:limite]:
            capturas.append(
                {
                    "arquivo": item["arquivo"],
                    "criado_em": item["criado_em"],
                    "tamanho_kb": item["tamanho_kb"],
                    "fonte": "s3",
                    "s3_key": item["s3_key"],
                    "url": nasa_image_url(item["arquivo"], fonte="s3", s3_key=item["s3_key"]),
                }
            )
        return {
            "total": total,
            "capturas": capturas,
            "storage": storage,
            "bucket": settings.S3_BUCKET_IMAGES,
            "prefix": _nasa_s3_prefix().rstrip("/"),
        }

    captures_dir = nasa_captures_dir()
    search_dirs = [captures_dir] if captures_dir.is_dir() else []
    arquivos = _collect_pngs(search_dirs)
    if not arquivos:
        arquivos = _collect_pngs(list(_DATASET_DIRS))
        if arquivos:
            storage = "dataset"

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
        "storage": storage,
        "diretorio": str(captures_dir),
    }
