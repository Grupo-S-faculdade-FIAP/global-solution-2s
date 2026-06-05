"""Chamadas ao backend FastAPI para o BFF do dashboard (sem HTTP loopback na porta única)."""

from __future__ import annotations

import json
import os
from typing import Any, Optional

import requests

_BFF_TIMEOUT_DEFAULT = 5
_fastapi_test_client: Any = None


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name, "true" if default else "false").strip().lower()
    return raw in ("1", "true", "yes", "on")


def use_inprocess_backend() -> bool:
    """
    Lambda: sempre in-process (não há loopback HTTP local).
    Dev uvicorn: só se BFF_INPROCESS=true (evita deadlock em worker threads).
    """
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return True
    raw = os.environ.get("BFF_INPROCESS", "true").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    return raw in ("1", "true", "yes", "on")


def fastapi_base_url() -> str:
    port = os.environ.get("PORT", "8000")
    return os.environ.get("FASTAPI_BASE_URL", f"http://127.0.0.1:{port}").rstrip("/")


def _get_test_client():
    global _fastapi_test_client
    if _fastapi_test_client is None:
        from starlette.testclient import TestClient

        from app.main import app as fastapi_app

        _fastapi_test_client = TestClient(fastapi_app)
    return _fastapi_test_client


def _parse_body(response: Any) -> Any:
    ct = (response.headers.get("content-type") or "").lower()
    if "application/json" in ct:
        return response.json()
    return response.text


def backend_get(
    path: str,
    params: Optional[dict] = None,
    timeout: int = _BFF_TIMEOUT_DEFAULT,
) -> tuple[int, Any]:
    """GET no backend (path sem prefixo /api, ex.: /alerts/summary)."""
    params = params or {}
    if use_inprocess_backend():
        try:
            response = _get_test_client().get(path, params=params)
            return response.status_code, _parse_body(response)
        except Exception:
            return 503, {"error": "Inprocess backend error"}

    try:
        response = requests.get(
            f"{fastapi_base_url()}{path}",
            params=params,
            timeout=timeout,
        )
        if "application/json" in (response.headers.get("content-type") or "").lower():
            return response.status_code, response.json()
        return response.status_code, response.text
    except requests.exceptions.RequestException:
        return 503, {"error": "Backend offline"}


def backend_post(
    path: str,
    json_body: Optional[dict] = None,
    timeout: int = _BFF_TIMEOUT_DEFAULT,
) -> tuple[int, Any]:
    """POST no backend."""
    if use_inprocess_backend():
        try:
            response = _get_test_client().post(path, json=json_body or {})
            return response.status_code, _parse_body(response)
        except Exception:
            return 503, {"error": "Inprocess backend error"}

    try:
        response = requests.post(
            f"{fastapi_base_url()}{path}",
            json=json_body or {},
            timeout=timeout,
        )
        if "application/json" in (response.headers.get("content-type") or "").lower():
            return response.status_code, response.json()
        return response.status_code, response.text
    except requests.exceptions.RequestException:
        return 503, {"error": "Backend offline"}
