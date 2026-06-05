"""Fixtures para testes E2E do dashboard (Playwright + servidor uvicorn)."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import Browser, Page, sync_playwright

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(base_url: str, timeout_s: float = 30.0) -> None:
    deadline = time.monotonic() + timeout_s
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{base_url}/health", timeout=2.0)
            if response.status_code == 200:
                return
        except Exception as exc:  # noqa: BLE001 — polling até o servidor subir
            last_error = exc
        time.sleep(0.25)
    raise RuntimeError(f"Servidor E2E não respondeu em {base_url}/health: {last_error}")


@pytest.fixture(scope="session")
def e2e_base_url() -> str:
    """Sobe API + dashboard Flask na mesma porta (como `make demo`)."""
    port = _free_port()
    env = os.environ.copy()
    env.update(
        {
            "MOUNT_DASHBOARD": "true",
            "DYNAMODB_USE_MOCK": "true",
            "IOT_USE_MOCK": "true",
            "DEMO_MODE": "true",
            # HTTP loopback evita deadlock do TestClient sob carga E2E paralela.
            "BFF_INPROCESS": "false",
            "PORT": str(port),
            "PYTHONPATH": str(_SRC),
        }
    )
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=_SRC,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        _wait_for_health(base)
        yield base
    except Exception:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)
        stderr = proc.stderr.read().decode() if proc.stderr else ""
        raise RuntimeError(f"Falha ao iniciar servidor E2E na porta {port}.\n{stderr}") from None
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


@pytest.fixture(scope="session")
def browser() -> Browser:
    with sync_playwright() as playwright:
        chromium = playwright.chromium.launch(headless=True)
        yield chromium
        chromium.close()


@pytest.fixture
def page(browser: Browser, e2e_base_url: str) -> Page:
    context = browser.new_context(locale="pt-BR", timezone_id="America/Sao_Paulo")
    pg = context.new_page()
    pg.set_default_timeout(15_000)
    # networkidle garante Chart.js + Leaflet (CDN) antes do módulo app.js inicializar mapas
    pg.goto(e2e_base_url, wait_until="networkidle")
    pg.wait_for_function(
        "() => typeof L !== 'undefined' && typeof Chart !== 'undefined'",
        timeout=15_000,
    )
    yield pg
    context.close()
