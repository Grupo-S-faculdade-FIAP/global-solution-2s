"""Router de Computer Vision — thin HTTP layer.

Toda a lógica de pipeline (S3, YOLO, SNS, persist) está em
app.application.cv.detect_storm.DetectStormUseCase.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.application.cv.detect_storm import DetectStormUseCase
from app.container import get_storm_repo
from app.domain.cv.ports import StormAlertRepository
from app.services.nasa_captures import list_nasa_captures, resolve_nasa_image
from app.services.sns_alerts import sns_status
from app.core.config import settings

router = APIRouter()


class DetectStormRequest(BaseModel):
    s3_key: str
    bucket: Optional[str] = None


def _get_use_case(
    repo: StormAlertRepository = Depends(get_storm_repo),
) -> DetectStormUseCase:
    return DetectStormUseCase(repo=repo)


@router.get("/status")
def cv_status() -> dict:
    """Status do módulo de Computer Vision."""
    return {
        "module": "computer_vision",
        "status": "ready",
        "sns": sns_status(),
        "s3_bucket_images": settings.S3_BUCKET_IMAGES,
        "yolo_model_s3_key": settings.YOLO_MODEL_S3_KEY,
    }


@router.get("/nasa/capturas")
def nasa_capturas(limite: int = 12) -> dict:
    """Lista capturas NASA Worldview salvas localmente (data/nasa_captures/)."""
    return list_nasa_captures(limite=max(1, min(limite, 100)))


@router.get("/nasa/imagem/{nome_arquivo}")
def nasa_imagem(
    nome_arquivo: str,
    fonte: str = Query("captures", pattern="^(captures|dataset)$"),
) -> FileResponse:
    """Serve PNG de captura NASA ou do dataset YOLO (demo local)."""
    path = resolve_nasa_image(nome_arquivo, fonte=fonte)
    if path is None:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    return FileResponse(path, media_type="image/png")


@router.post("/detect/storm")
def detect_storm(
    body: DetectStormRequest,
    uc: DetectStormUseCase = Depends(_get_use_case),
) -> dict:
    """
    Dispara o pipeline de detecção de tempestades para uma imagem já presente no S3.

    Body:
      - s3_key: caminho do objeto no bucket (ex: "screenshots/img.jpg")
      - bucket: nome do bucket (opcional; usa S3_BUCKET_IMAGES se omitido)
    """
    bucket = body.bucket or settings.S3_BUCKET_IMAGES
    return uc.execute(bucket=bucket, key=body.s3_key)


def process_s3_image(bucket: str, key: str) -> dict:
    """
    Compatibilidade com chamadas diretas (main.py legado e testes).
    Cria um use case com o repo padrão e executa.
    """
    repo = get_storm_repo()
    return DetectStormUseCase(repo=repo).execute(bucket=bucket, key=key)
