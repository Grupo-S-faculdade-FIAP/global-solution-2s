"""Testes do serviço e endpoint de capturas NASA."""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.nasa_captures import list_nasa_captures, nasa_captures_dir

client = TestClient(app)


def test_nasa_captures_dir_resolves_to_repo_data() -> None:
    path = nasa_captures_dir()
    assert path.name == "nasa_captures"
    assert path.parent.name == "data"


def test_list_nasa_captures_returns_recent_files() -> None:
    captures_dir = nasa_captures_dir()
    if not captures_dir.is_dir():
        pytest.skip("data/nasa_captures ausente")

    result = list_nasa_captures(limite=5)
    assert "total" in result
    assert "capturas" in result
    if result["total"] > 0:
        cap = result["capturas"][0]
        assert "arquivo" in cap
        assert cap["arquivo"].endswith(".png")
        assert cap["tamanho_kb"] >= 100


def test_cv_nasa_capturas_endpoint() -> None:
    with patch(
        "app.routers.cv.list_nasa_captures",
        return_value={
            "total": 2,
            "capturas": [{"arquivo": "nasa_brasil_20260604.png", "url": "/cv/nasa/imagem/nasa_brasil_20260604.png"}],
        },
    ):
        response = client.get("/cv/nasa/capturas?limite=5")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["capturas"]) == 1


def test_nasa_imagem_rejects_invalid_name() -> None:
    response = client.get("/cv/nasa/imagem/not-a-nasa-file.png")
    assert response.status_code == 404


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
