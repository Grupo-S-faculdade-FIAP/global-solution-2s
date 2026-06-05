"""Tests for Lambda handler routing in app.main."""

from unittest.mock import MagicMock, patch

from app.main import handler, app
from fastapi.testclient import TestClient


def test_lambda_routes_s3_events():
    mock_s3_handler = MagicMock()
    mock_s3_handler.handle.return_value = {"processed": 1, "results": []}

    with patch("app.main._build_s3_handler", return_value=mock_s3_handler):
        event = {
            "Records": [
                {"eventSource": "aws:s3", "s3": {"bucket": {"name": "b"}, "object": {"key": "k"}}}
            ]
        }
        result = handler(event, None)

    assert result["processed"] == 1
    mock_s3_handler.handle.assert_called_once_with(event)


def test_lambda_routes_http_via_mangum():
    with patch("app.main._http_handler") as mock_mangum:
        mock_mangum.return_value = {"statusCode": 200}
        event = {"httpMethod": "GET", "path": "/health"}
        result = handler(event, None)
    assert result["statusCode"] == 200


def test_build_s3_handler_wires_use_case():
    from app.main import _build_s3_handler

    h = _build_s3_handler()
    assert h._uc is not None


def test_dashboard_ui_registered_when_mount_disabled(monkeypatch):
    monkeypatch.setenv("MOUNT_DASHBOARD", "false")
    from importlib import reload
    import app.main as main_mod

    reload(main_mod)
    client = TestClient(main_mod.app)
    response = client.get("/dashboard/status")
    assert response.status_code == 200
