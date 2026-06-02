import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from app.core.config import settings
from app.routers import cv, ml, iot, dashboard, data_integration
from app.routers.cv import process_s3_image

logger = logging.getLogger(__name__)

app = FastAPI(
    title="API",
    description="Plataforma de inteligência ambiental e agrícola com dados de satélite e IA.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cv.router, prefix="/cv", tags=["Computer Vision"])
app.include_router(ml.router, prefix="/ml", tags=["Machine Learning"])
app.include_router(iot.router, prefix="/iot", tags=["IoT"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(data_integration.router, prefix="", tags=["Data Integration"])


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


_http_handler = Mangum(app)


def _handle_s3_trigger(event: dict, context: object) -> dict:
    """Processa eventos de trigger do S3 — chamado quando uma imagem é enviada ao bucket."""
    results = []
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        logger.info("S3 trigger recebido: s3://%s/%s", bucket, key)
        result = process_s3_image(bucket=bucket, key=key)
        results.append(result)
    return {"processed": len(results), "results": results}


def handler(event: dict, context: object) -> dict:
    """
    Ponto de entrada do Lambda.
    Roteia eventos S3 (upload de imagem) para o pipeline de CV,
    e eventos HTTP do API Gateway para o app FastAPI via Mangum.
    """
    records = event.get("Records", [])
    if records and records[0].get("eventSource") == "aws:s3":
        return _handle_s3_trigger(event, context)
    return _http_handler(event, context)
