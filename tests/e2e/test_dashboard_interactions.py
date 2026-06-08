"""Interações de usuário no dashboard (Playwright)."""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

from e2e.helpers import open_location_advanced, wait_dashboard_ready

pytestmark = pytest.mark.e2e


def test_simulate_storm_alert_updates_ui(page: Page) -> None:
    wait_dashboard_ready(page)
    page.locator("#btn-test-detection").click()
    expect(page.locator("#test-status")).to_contain_text(
        re.compile(r"Alerta registrado|registrado", re.I),
        timeout=20_000,
    )
    expect(page.locator("#yolo-last-detection")).not_to_have_text("—")
    expect(page.locator("#yolo-avg-confidence")).to_contain_text("%")


def test_reset_location_to_sao_paulo(page: Page) -> None:
    wait_dashboard_ready(page)
    page.locator("#select-city option[value='rj']").wait_for(state="attached")
    page.select_option("#select-city", "rj")
    page.wait_for_function(
        "() => document.getElementById('location-city-name')?.textContent?.includes('Rio')",
        timeout=10_000,
    )
    page.locator("#btn-reset-sp").click()
    expect(page.locator("#location-city-name")).to_contain_text("São Paulo", timeout=10_000)


def test_apply_coordinates_from_advanced_fields(page: Page) -> None:
    wait_dashboard_ready(page)
    open_location_advanced(page)
    page.fill("#input-lat", "-15.8267")
    page.fill("#input-lon", "-47.9218")
    page.locator("#btn-apply-location").click()
    expect(page.locator("#location-city-name")).to_contain_text("Brasília", timeout=15_000)
    expect(page.locator("#weather-temp")).not_to_have_text("—", timeout=15_000)


def test_invalid_coordinates_shows_error_toast(page: Page) -> None:
    wait_dashboard_ready(page)
    open_location_advanced(page)
    page.fill("#input-lat", "999")
    page.fill("#input-lon", "-46.63")
    page.locator("#btn-apply-location").click()
    expect(page.locator(".toast-error")).to_be_visible(timeout=5_000)
    expect(page.locator(".toast-error")).to_contain_text("inválid", ignore_case=True)


def test_location_bar_collapse_toggle(page: Page) -> None:
    wait_dashboard_ready(page)
    bar = page.locator("#location-bar")
    collapse_btn = page.locator("#btn-location-collapse")
    collapse_btn.click()
    expect(bar).to_have_class(re.compile(r"is-compact"))
    expect(collapse_btn).to_have_attribute("aria-expanded", "false")
    collapse_btn.click()
    expect(bar).not_to_have_class(re.compile(r"is-compact"))


def test_theme_persists_after_reload(page: Page) -> None:
    wait_dashboard_ready(page)
    page.locator("#theme-toggle").click()
    theme_after_toggle = page.evaluate(
        "() => document.documentElement.getAttribute('data-theme')"
    )
    assert theme_after_toggle in ("light", "dark")
    stored = page.evaluate("() => localStorage.getItem('dashboard-theme')")
    assert stored == theme_after_toggle

    page.reload(wait_until="domcontentloaded")
    wait_dashboard_ready(page)
    theme_after_reload = page.evaluate(
        "() => document.documentElement.getAttribute('data-theme')"
    )
    assert theme_after_reload == theme_after_toggle


def test_nav_highlights_active_section_on_scroll(page: Page) -> None:
    wait_dashboard_ready(page)
    page.locator('a.page-nav-link[href="#sec-clima"]').click()
    expect(page.locator("#sec-clima")).to_be_in_viewport()
    page.wait_for_function(
        """() => document.querySelector('a.page-nav-link[href="#sec-clima"]')
            ?.classList.contains('is-active')""",
        timeout=10_000,
    )


@pytest.mark.parametrize(
    "href,section_id",
    [
        ("#sec-resumo", "sec-resumo"),
        ("#sec-clima", "sec-clima"),
        ("#sec-lavoura", "sec-lavoura"),
        ("#sec-satelite", "sec-satelite"),
        ("#sec-sns", "sec-sns"),
        ("#sec-historico", "sec-historico"),
        ("#sec-alertas-mapa", "sec-alertas-mapa"),
        ("#sec-radar", "sec-radar"),
        ("#sec-sobre", "sec-sobre"),
    ],
)
def test_nav_links_scroll_to_sections(page: Page, href: str, section_id: str) -> None:
    wait_dashboard_ready(page)
    page.locator(f'a.page-nav-link[href="{href}"]').click()
    expect(page.locator(f"#{section_id}")).to_be_in_viewport()


def test_sns_section_visible(page: Page) -> None:
    wait_dashboard_ready(page)
    expect(page.locator("#sec-sns")).to_be_visible()
    expect(page.locator("#sns-email")).to_be_visible()
    expect(page.locator("#sns-status-badge")).not_to_have_text("Verificando…", timeout=15_000)


def test_footer_storage_hint_updates(page: Page) -> None:
    wait_dashboard_ready(page)
    hint = page.locator("#footer-storage-hint")
    expect(hint).not_to_be_empty()
    text = hint.inner_text()
    assert text and text != "—"
