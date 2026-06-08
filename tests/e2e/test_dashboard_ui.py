"""Testes E2E do dashboard com Playwright (browser real + API local)."""

from __future__ import annotations

import re

import httpx
import pytest
from playwright.sync_api import Page, expect

from e2e.helpers import wait_dashboard_ready

pytestmark = pytest.mark.e2e


def test_home_page_structure(page: Page) -> None:
    expect(page.locator(".topbar-brand")).to_contain_text("Global Solutions")
    expect(page.locator(".page-nav")).to_be_visible()
    for section_id in (
        "sec-resumo",
        "sec-clima",
        "sec-lavoura",
        "sec-iot",
        "sec-satelite",
        "sec-historico",
        "sec-radar",
        "sec-sobre",
    ):
        expect(page.locator(f"#{section_id}")).to_be_attached()


def test_static_assets_load(page: Page, e2e_base_url: str) -> None:
    for path in (
        "/static/dashboard.css",
        "/static/js/app.js",
        "/static/css/tokens.css",
    ):
        response = page.request.get(f"{e2e_base_url}{path}")
        assert response.status == 200, path
        assert response.headers.get("content-type", "").startswith(("text/", "application/javascript"))


def test_bootstrap_populates_kpis_and_chip(page: Page) -> None:
    wait_dashboard_ready(page)
    kpi_total = page.locator("#kpi-total")
    expect(kpi_total).not_to_have_text("—")
    expect(kpi_total).not_to_have_class("is-loading")

    chip = page.locator("#data-source-chip")
    expect(chip).not_to_have_text("Carregando…")
    expect(page.locator("#data-source-updated")).to_contain_text("Atualizado:")


def test_weather_and_risk_sections_load(page: Page) -> None:
    wait_dashboard_ready(page)
    for element_id in ("weather-temp", "weather-humidity", "risk-badge", "ml-score"):
        el = page.locator(f"#{element_id}")
        expect(el).not_to_have_text("—", timeout=20_000)
        expect(el).not_to_have_class("is-loading")


def test_iot_section_loads(page: Page) -> None:
    wait_dashboard_ready(page)
    expect(page.locator("#iot-temp")).not_to_have_text("—", timeout=20_000)
    expect(page.locator("#iot-umid")).not_to_have_text("—")
    expect(page.locator("#iot-status-badge")).not_to_be_empty()


def test_nav_anchor_scrolls_to_section(page: Page) -> None:
    wait_dashboard_ready(page)
    page.locator('a.page-nav-link[href="#sec-iot"]').click()
    expect(page.locator("#sec-iot")).to_be_in_viewport()


def test_theme_toggle_switches_mode(page: Page) -> None:
    wait_dashboard_ready(page)
    toggle = page.locator("#theme-toggle")
    initial = toggle.get_attribute("aria-pressed")
    toggle.click()
    expect(toggle).not_to_have_attribute("aria-pressed", initial or "")
    label = page.locator("#theme-mode-label")
    expect(label).to_have_text(re.compile(r"Claro|Escuro"))


def test_location_city_change_updates_badge(page: Page) -> None:
    wait_dashboard_ready(page)
    page.locator("#select-city option[value='rj']").wait_for(state="attached", timeout=10_000)
    page.select_option("#select-city", "rj")
    page.wait_for_function(
        """() => {
            const name = document.getElementById('location-city-name');
            return name && name.textContent.includes('Rio de Janeiro');
        }""",
        timeout=10_000,
    )
    expect(page.locator("#location-city-name")).to_contain_text("Rio de Janeiro")


def test_demo_yolo_actions_visible(page: Page) -> None:
    wait_dashboard_ready(page)
    expect(page.locator("#yolo-dev-actions")).to_be_visible()
    expect(page.locator("#btn-test-detection")).to_be_enabled()


def test_bff_config_endpoint(e2e_base_url: str) -> None:
    response = httpx.get(f"{e2e_base_url}/api/dashboard/config", timeout=10.0)
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("demo_mode") is True
    assert response.headers.get("x-data-source")


def test_health_endpoint(e2e_base_url: str) -> None:
    response = httpx.get(f"{e2e_base_url}/health", timeout=10.0)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
