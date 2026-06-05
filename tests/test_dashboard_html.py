"""Testes do template HTML e assets estáticos do dashboard (sem browser)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_DASHBOARD_ROOT = Path(__file__).resolve().parent.parent / "src" / "dashboard"
_STATIC = _DASHBOARD_ROOT / "static"
_TEMPLATES = _DASHBOARD_ROOT / "templates"


@pytest.fixture
def flask_client():
    from dashboard.app import app

    app.config["TESTING"] = True
    return app.test_client()


def test_index_renders_main_sections(flask_client) -> None:
    response = flask_client.get("/")
    assert response.status_code == 200
    html = response.data.decode()
    assert "Painel da propriedade" in html
    for section_id in (
        "sec-resumo",
        "sec-clima",
        "sec-lavoura",
        "sec-iot",
        "sec-satelite",
        "sec-historico",
        "sec-radar",
    ):
        assert f'id="{section_id}"' in html


def test_index_includes_es_module_entry(flask_client) -> None:
    html = flask_client.get("/").data.decode()
    assert 'type="module"' in html
    assert "/static/js/app.js" in html


def test_index_includes_chart_and_leaflet_cdn(flask_client) -> None:
    html = flask_client.get("/").data.decode()
    assert "chart.js" in html
    assert "leaflet" in html


def test_demo_mode_renders_yolo_dev_actions(flask_client, monkeypatch: pytest.MonkeyPatch) -> None:
    import dashboard.app as dashboard_app

    monkeypatch.setattr(dashboard_app, "DEMO_MODE", True)
    html = flask_client.get("/").data.decode()
    assert 'id="yolo-dev-actions"' in html
    assert 'id="btn-test-detection"' in html


def test_nav_has_all_section_links(flask_client) -> None:
    html = flask_client.get("/").data.decode()
    for href in (
        "#sec-resumo",
        "#sec-clima",
        "#sec-lavoura",
        "#sec-iot",
        "#sec-satelite",
        "#sec-historico",
        "#sec-alertas-mapa",
        "#sec-radar",
    ):
        assert f'href="{href}"' in html


def test_location_bar_controls_present(flask_client) -> None:
    html = flask_client.get("/").data.decode()
    for control_id in (
        "select-city",
        "input-lat",
        "input-lon",
        "btn-apply-location",
        "btn-reset-sp",
        "theme-toggle",
    ):
        assert f'id="{control_id}"' in html


def test_static_css_and_js_exist() -> None:
    assert (_STATIC / "dashboard.css").is_file()
    assert (_STATIC / "css" / "tokens.css").is_file()
    assert (_STATIC / "js" / "app.js").is_file()
    assert (_STATIC / "js" / "bootstrap.js").is_file()


def test_app_js_imports_bootstrap_module() -> None:
    app_js = (_STATIC / "js" / "app.js").read_text(encoding="utf-8")
    assert 'from "./bootstrap.js"' in app_js


def test_flask_serves_static_css(flask_client) -> None:
    response = flask_client.get("/static/dashboard.css")
    assert response.status_code == 200
    assert b":root" in response.data or b"--" in response.data


def test_flask_serves_app_js(flask_client) -> None:
    response = flask_client.get("/static/js/app.js")
    assert response.status_code == 200
    assert b"initDashboard" in response.data


def test_api_dashboard_config_json(flask_client) -> None:
    response = flask_client.get("/api/dashboard/config")
    assert response.status_code == 200
    payload = response.get_json()
    assert "demo_mode" in payload
    assert response.headers.get("X-Data-Source")


def test_api_alerts_summary_demo_data(flask_client) -> None:
    response = flask_client.get("/api/dashboard/summary?days=30")
    assert response.status_code == 200
    payload = response.get_json()
    kpis = payload.get("kpis") or payload
    assert isinstance(kpis.get("total_30d"), (int, float))
    assert kpis["total_30d"] > 0


def test_index_html_lang_pt_br(flask_client) -> None:
    html = flask_client.get("/").data.decode()
    assert re.search(r'<html[^>]+lang="pt-BR"', html)


def test_index_has_chart_canvases(flask_client) -> None:
    html = flask_client.get("/").data.decode()
    for canvas_id in ("trendChart", "weeklyChart", "hourlyChart"):
        assert f'id="{canvas_id}"' in html
    assert 'id="heatmap-table"' in html


def test_index_has_map_containers(flask_client) -> None:
    html = flask_client.get("/").data.decode()
    assert 'id="location-picker-map"' in html
    assert 'id="region-map"' in html
    assert 'id="windy-iframe"' in html


def test_flask_api_weather_endpoint(flask_client) -> None:
    response = flask_client.get("/api/weather/current", query_string={"lat": -23.55, "lon": -46.63})
    assert response.status_code == 200
    data = response.get_json()
    assert "temperature" in data


def test_flask_api_storms_recent(flask_client) -> None:
    response = flask_client.get("/api/storms/recent", query_string={"hours": 24})
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)
