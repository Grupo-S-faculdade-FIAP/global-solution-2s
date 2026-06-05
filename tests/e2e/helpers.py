"""Utilitários compartilhados dos testes E2E Playwright."""

from __future__ import annotations

from playwright.sync_api import Page


def wait_dashboard_ready(page: Page, timeout_ms: int = 20_000) -> None:
    """Aguarda bootstrap JS preencher KPIs (dados demo/mock)."""
    page.wait_for_function(
        """() => {
            const el = document.getElementById('kpi-total');
            if (!el) return false;
            const text = (el.textContent || '').trim();
            return text !== '—' && text !== '' && !el.classList.contains('is-loading');
        }""",
        timeout=timeout_ms,
    )


def open_location_advanced(page: Page) -> None:
    page.locator("#location-advanced").evaluate("el => { el.open = true; }")


def ensure_location_bar_expanded(page: Page) -> None:
    """Mapa picker fica oculto quando a barra está recolhida (is-compact)."""
    bar = page.locator("#location-bar")
    classes = bar.get_attribute("class") or ""
    if "is-compact" in classes:
        page.locator("#btn-location-collapse").click()
        bar.wait_for(state="visible")
