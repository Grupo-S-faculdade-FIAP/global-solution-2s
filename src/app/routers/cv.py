from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class DetectStormRequest(BaseModel):
    s3_key: str
    bucket: str | None = None


def process_s3_image(bucket: str, key: str) -> dict:
    """
    Processa uma imagem de satélite armazenada no S3 com o modelo YOLO.

    Chamado automaticamente pelo S3 trigger (via main.handler) quando uma
    imagem .jpg é enviada ao bucket, ou manualmente via POST /cv/detect/storm.

    TODO: implementar pipeline completo:
      1. Baixar imagem do S3 via boto3
      2. Rodar inferência YOLO (yolov8_storm.pt)
      3. Se detecção positiva: publicar alerta no SNS e gravar em DynamoDB (tabela alerts)
    """
    return {
        "bucket": bucket,
        "key": key,
        "detections": [],
        "alert_sent": False,
        "message": "not implemented yet",
    }


@router.get("/status")
def cv_status():
    """Status do módulo de Computer Vision."""
    return {"module": "computer_vision", "status": "ready"}


@router.post("/detect/storm")
async def detect_storm(body: DetectStormRequest):
    """
    Dispara o pipeline de detecção de tempestades/nuvens de chuva para uma imagem já
    presente no S3. Use este endpoint para testes manuais; em produção o
    trigger é automático via S3 → Lambda.

    Body:
      - s3_key: caminho do objeto no bucket (ex: "screenshots/img.jpg")
      - bucket: nome do bucket (opcional; usa S3_BUCKET_IMAGES do ambiente se omitido)
    """
    from app.core.config import settings

    bucket = body.bucket or settings.S3_BUCKET_IMAGES
    return process_s3_image(bucket=bucket, key=body.s3_key)
