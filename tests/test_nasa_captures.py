"""Testes do serviço e endpoint de capturas NASA."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import nasa_captures as svc
from app.services.nasa_captures import list_nasa_captures, nasa_captures_dir

client = TestClient(app)


def test_nasa_captures_dir_resolves_to_repo_data() -> None:
    path = nasa_captures_dir()
    assert path.name == "nasa_captures"
    assert path.parent.name == "data"


def test_list_nasa_captures_from_s3() -> None:
    fake_items = [
        {
            "s3_key": "nasa-satellite/2026/06/04/nasa_brasil_20260604_1200.png",
            "arquivo": "nasa_brasil_20260604_1200.png",
            "criado_em": datetime(2026, 6, 4, 12, 0, tzinfo=timezone.utc).isoformat(),
            "tamanho_kb": 512,
            "last_modified": datetime(2026, 6, 4, 12, 0, tzinfo=timezone.utc),
        }
    ]
    with (
        patch.object(svc, "_bucket_configured", return_value=True),
        patch.object(svc, "_list_s3_nasa_objects", return_value=fake_items),
        patch.object(svc, "presigned_nasa_url", return_value="https://s3.example/presigned"),
    ):
        result = list_nasa_captures(limite=5)

    assert result["storage"] == "s3"
    assert result["total"] == 1
    assert result["capturas"][0]["fonte"] == "s3"
    assert result["capturas"][0]["url"] == "https://s3.example/presigned"


def test_list_nasa_captures_local_fallback_when_s3_empty() -> None:
    captures_dir = nasa_captures_dir()
    if not captures_dir.is_dir():
        pytest.skip("data/nasa_captures ausente")

    with patch.object(svc, "_bucket_configured", return_value=True), patch.object(
        svc, "_list_s3_nasa_objects", return_value=[]
    ):
        result = list_nasa_captures(limite=5)

    assert "capturas" in result
    if result["total"] > 0:
        cap = result["capturas"][0]
        assert cap["arquivo"].endswith(".png")
        assert cap["tamanho_kb"] >= 100


def test_s3_has_capture_matches_region_and_date() -> None:
    mock_client = MagicMock()
    mock_client.list_objects_v2.return_value = {
        "Contents": [
            {"Key": "nasa-satellite/2026/06/04/nasa_brasil_20260604_1200.png", "Size": 200_000},
        ]
    }
    with patch.object(svc, "_bucket_configured", return_value=True), patch.object(
        svc, "_s3_client", return_value=mock_client
    ):
        assert svc.s3_has_capture("nasa_brasil", "2026-06-04") is True
        assert svc.s3_has_capture("nasa_americas", "2026-06-04") is False


def test_cv_nasa_capturas_endpoint() -> None:
    with patch(
        "app.routers.cv.list_nasa_captures",
        return_value={
            "total": 2,
            "storage": "s3",
            "capturas": [
                {
                    "arquivo": "nasa_brasil_20260604.png",
                    "url": "https://s3.example/presigned",
                    "fonte": "s3",
                }
            ],
        },
    ):
        response = client.get("/cv/nasa/capturas?limite=5")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["storage"] == "s3"
    assert len(body["capturas"]) == 1


def test_nasa_imagem_rejects_invalid_name() -> None:
    response = client.get("/cv/nasa/imagem/not-a-nasa-file.png")
    assert response.status_code == 404


def test_nasa_imagem_redirects_to_presigned_s3() -> None:
    with (
        patch("app.routers.cv.resolve_nasa_s3_key", return_value="nasa-satellite/x.png"),
        patch("app.routers.cv.presigned_nasa_url", return_value="https://s3.example/presigned"),
    ):
        response = client.get("/cv/nasa/imagem/nasa_brasil_test.png?fonte=s3", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "https://s3.example/presigned"


def test_nasa_imagem_serves_file(tmp_path, monkeypatch) -> None:
    png = tmp_path / "nasa_brasil_test.png"
    png.write_bytes(b"\x89PNG" + b"\0" * 100_000)
    monkeypatch.setattr(
        "app.routers.cv.resolve_nasa_image",
        lambda nome, fonte="captures": png if nome == "nasa_brasil_test.png" else None,
    )
    response = client.get("/cv/nasa/imagem/nasa_brasil_test.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
