import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from mangum import Mangum

from app.core.config import settings
from app.routers import cv, ml, iot, dashboard, data_integration, dashboard_bff, dashboard_ui

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
app.include_router(dashboard_bff.router)


def _mount_dashboard_ui(application: FastAPI) -> None:
    """
    Dashboard Flask no mesmo processo que a API.
    Rotas FastAPI registradas acima têm prioridade; o restante vai ao Flask.
    Desative em Lambda com MOUNT_DASHBOARD=false.
    """
    if os.environ.get("MOUNT_DASHBOARD", "true").strip().lower() not in (
        "1", "true", "yes", "on",
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
    mount_flask = os.environ.get("MOUNT_DASHBOARD", "true").strip().lower() in (
        "1", "true", "yes", "on",
    )
    if mount_flask:
        _mount_dashboard_ui(application)
    else:
        dashboard_ui.register(application)


_setup_dashboard(app)

_http_handler = Mangum(app)


def _build_s3_handler():
    """Cria S3TriggerHandler com o use case e repositório corretos."""
    from app.application.cv.detect_storm import DetectStormUseCase
    from app.container import get_storm_repo
    from app.interfaces.events.s3_trigger import S3TriggerHandler

    repo = get_storm_repo()
    use_case = DetectStormUseCase(repo=repo)
    return S3TriggerHandler(use_case=use_case)


def handler(event: dict, context: object) -> dict:
    """
    Ponto de entrada do Lambda.
    Roteia eventos S3 (upload de imagem) para o S3TriggerHandler,
    e eventos HTTP do API Gateway para o app FastAPI via Mangum.
    """
    records = event.get("Records", [])
    if records and records[0].get("eventSource") == "aws:s3":
        return _build_s3_handler().handle(event)
    return _http_handler(event, context)
