import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from mangum import Mangum

from app.core.config import settings
from app.routers import cv, ml, iot, dashboard, data_integration, dashboard_bff, dashboard_ui
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
# BFF /api/* no FastAPI (antes do mount Flask) — formato esperado pelo index.html
app.include_router(dashboard_bff.router)


def _mount_dashboard_ui(application: FastAPI) -> None:
    """
    Dashboard Flask (HTML + rotas /api/* BFF) no mesmo processo que a API.
    Rotas FastAPI registradas acima têm prioridade; o restante vai ao Flask.
    Desative em Lambda com MOUNT_DASHBOARD=false.
    """
    if os.environ.get("MOUNT_DASHBOARD", "true").strip().lower() not in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return
    try:
        from dashboard.app import app as flask_dashboard

        application.mount("/", WSGIMiddleware(flask_dashboard))
        logger.info("Dashboard UI montado em / (porta única)")
    except Exception as exc:
        logger.warning("Dashboard UI não montado: %s", exc)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


def _setup_dashboard(application: FastAPI) -> None:
    """Flask (dev local) ou FastAPI static (Lambda)."""
    mount_flask = os.environ.get("MOUNT_DASHBOARD", "true").strip().lower() in (
        "1", "true", "yes", "on",
    )
    if mount_flask:
        _mount_dashboard_ui(application)
    else:
        dashboard_ui.register(application)


_setup_dashboard(app)


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
