"""Dashboard HTML + arquivos estáticos via FastAPI (Lambda / produção)."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Dashboard UI"])

_DASHBOARD_ROOT = Path(__file__).resolve().parents[2] / "dashboard"
_TEMPLATES_DIR = _DASHBOARD_ROOT / "templates"
_STATIC_DIR = _DASHBOARD_ROOT / "static"

templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_index(request: Request) -> HTMLResponse:
    """Página principal do dashboard."""
    response = templates.TemplateResponse(
        request,
        "index.html",
        {"demo_mode": settings.DEMO_MODE},
    )
    response.headers["Cache-Control"] = "no-store"
    return response


def register(application) -> None:
    """Monta rotas do dashboard quando Flask não está ativo (ex.: Lambda)."""
    if not _TEMPLATES_DIR.is_dir():
        logger.warning("Dashboard templates não encontrados em %s", _TEMPLATES_DIR)
        return
    application.include_router(router)
    if _STATIC_DIR.is_dir():
        application.mount(
            "/static",
            StaticFiles(directory=str(_STATIC_DIR)),
            name="dashboard-static",
        )
        logger.info("Dashboard UI FastAPI em / (static: %s)", _STATIC_DIR)
    else:
        logger.warning("Dashboard static não encontrado em %s", _STATIC_DIR)
