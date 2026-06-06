import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from mangum import Mangum

from app.core.config import settings, get_allowed_origins
from app.core.tracing import init_xray, wrap_lambda_handler, add_trace_metadata
from app.core.xray_tracing import xray_subsegment
from app.routers import cv, ml, iot, dashboard, data_integration, dashboard_bff, dashboard_ui

logger = logging.getLogger(__name__)

# Importa slowapi para rate limiting (com graceful fallback)
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    _RATE_LIMITER = Limiter(key_func=get_remote_address)
    _RATE_LIMITING_AVAILABLE = True
except ImportError:
    logger.warning("slowapi not installed. Rate limiting disabled.")
    _RATE_LIMITING_AVAILABLE = False
    _RATE_LIMITER = None

# Inicializar X-Ray tracing (se habilitado)
init_xray()

app = FastAPI(
    title="API",
    description="Plataforma de inteligência ambiental e agrícola com dados de satélite e IA.",
    version="0.1.0",
)

# Adiciona rate limiting middleware (se slowapi disponível)
if _RATE_LIMITING_AVAILABLE:
    app.state.limiter = _RATE_LIMITER
    app.add_exception_handler(
        __import__("slowapi.errors").RateLimitExceeded,
        lambda request, exc: {
            "detail": "Rate limit exceeded. Max 100 requests per minute per IP."
        },
    )
    logger.info("Rate limiting enabled (100 req/min per IP)")
else:
    logger.debug("Rate limiting not available (slowapi not installed)")

# CORS dinâmico: mescla ALLOWED_ORIGINS + CORS_EXTRA_ORIGINS do ambiente
cors_origins = get_allowed_origins()
logger.info("CORS enabled for origins: %s", cors_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
    """Cria S3TriggerHandler com injeção de dependências.

    Usa factory do container para criar use case com repositório correto.
    """
    from app.container import get_detect_storm_use_case
    from app.interfaces.events.s3_trigger import S3TriggerHandler

    use_case = get_detect_storm_use_case()
    return S3TriggerHandler(use_case=use_case)


def handler(event: dict, context: object) -> dict:
    """
    Ponto de entrada do Lambda.
    Roteia eventos S3 (upload de imagem) para o S3TriggerHandler,
    e eventos HTTP do API Gateway para o app FastAPI via Mangum.

    Instrumentado com X-Ray distributed tracing.
    """
    records = event.get("Records", [])

    if records and records[0].get("eventSource") == "aws:s3":
        with xray_subsegment("s3_event_handler"):
            add_trace_metadata("event_type", "s3")
            s3_obj = records[0].get("s3", {})
            s3_key = s3_obj.get("object", {}).get("key", "unknown")
            s3_bucket = s3_obj.get("bucket", {}).get("name", "unknown")
            add_trace_metadata("s3_bucket", s3_bucket)
            add_trace_metadata("s3_key", s3_key)
            return _build_s3_handler().handle(event)

    with xray_subsegment("http_event_handler"):
        add_trace_metadata("event_type", "http")
        add_trace_metadata("resource", event.get("resource", "unknown"))
        add_trace_metadata("method", event.get("httpMethod", "unknown"))
        return _http_handler(event, context)
