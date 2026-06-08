"""Gráficos, mapas Leaflet e radar Windy (Playwright)."""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

from e2e.helpers import ensure_location_bar_expanded, wait_dashboard_ready

pytestmark = pytest.mark.e2e


def test_charts_render_after_bootstrap(page: Page) -> None:
    wait_dashboard_ready(page)
    for canvas_id in ("trendChart", "weeklyChart", "hourlyChart"):
        canvas = page.locator(f"#{canvas_id}")
        expect(canvas).to_be_attached()
        page.wait_for_function(
            f"""() => {{
                const c = document.getElementById('{canvas_id}');
                return c && c.offsetWidth > 0 && c.offsetHeight > 0;
            }}""",
            timeout=10_000,
        )


def test_heatmap_table_populated(page: Page) -> None:
    wait_dashboard_ready(page)
    rows = page.locator("#heatmap-table tbody tr")
    expect(rows.first).to_be_attached(timeout=10_000)
    assert rows.count() >= 7


def test_yolo_section_status_loaded(page: Page) -> None:
    wait_dashboard_ready(page)
    status = page.locator("#yolo-status")
    expect(status).not_to_have_text("Verificando...", timeout=15_000)
    expect(status).not_to_have_text("")


def test_storms_recent_list_rendered(page: Page) -> None:
    wait_dashboard_ready(page)
    el = page.locator("#storms-recent-list")
    expect(el).not_to_have_text("Carregando alertas recentes…", timeout=15_000)
    expect(page.locator("#yolo-last-detection")).not_to_have_text("—")


def test_nasa_gallery_meta_updated(page: Page) -> None:
    wait_dashboard_ready(page)
    meta = page.locator("#nasa-total")
    expect(meta).not_to_have_text("—", timeout=15_000)
    expect(meta).to_contain_text(re.compile(r"imagens|Nenhuma", re.I))


def test_ml_section_probabilities(page: Page) -> None:
    wait_dashboard_ready(page)
    expect(page.locator("#ml-probas")).not_to_have_text("—", timeout=15_000)
    expect(page.locator("#ml-classe")).not_to_have_text("—")


def test_location_picker_leaflet_map(page: Page) -> None:
    wait_dashboard_ready(page)
    ensure_location_bar_expanded(page)
    page.locator("#location-picker-map").scroll_into_view_if_needed()
    page.wait_for_function(
        "() => document.getElementById('location-picker-map')?.classList.contains('leaflet-container')",
        timeout=25_000,
    )
    expect(page.locator("#location-picker-map.leaflet-container")).to_be_attached()
    expect(page.locator("#location-picker-map .leaflet-tile-pane")).to_be_attached()


def test_region_map_leaflet_initializes(page: Page) -> None:
    wait_dashboard_ready(page)
    coords = page.locator("#region-map-coords")
    status = page.locator("#region-alert-badge")
    expect(coords).not_to_have_text("—", timeout=10_000)
    expect(status).not_to_have_text("Verificando…", timeout=15_000)
    page.locator(".region-map-wrap").scroll_into_view_if_needed()
    page.wait_for_function(
        """() => document.getElementById('region-map')?.classList.contains('leaflet-container')
            || !!document.querySelector('#region-map-empty:not([hidden])')""",
        timeout=25_000,
    )
    expect(page.locator("#region-map.leaflet-container")).to_be_attached()


def test_windy_iframe_lazy_loads_on_scroll(page: Page) -> None:
    wait_dashboard_ready(page)
    page.locator("#sec-radar").scroll_into_view_if_needed()
    page.wait_for_function(
        """() => {
            const iframe = document.getElementById('windy-iframe');
            return iframe && iframe.src && iframe.src.includes('windy.com');
        }""",
        timeout=20_000,
    )
    iframe = page.locator("#windy-iframe")
    expect(iframe).to_have_attribute("src", re.compile(r"windy\.com"))


def test_iot_history_table_when_multiple_readings(page: Page) -> None:
    wait_dashboard_ready(page)
    page.wait_for_function(
        """() => {
            const wrap = document.getElementById('iot-history-wrap');
            const body = document.getElementById('iot-history-body');
            if (!wrap || !body) return false;
            return !wrap.hidden && body.querySelectorAll('tr').length >= 1;
        }""",
        timeout=15_000,
    )
    rows = page.locator("#iot-history-body tr")
    assert rows.count() >= 1
