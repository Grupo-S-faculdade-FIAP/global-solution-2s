"""Extended INMET client/parser tests."""

import io
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.clients.inmet import (
    InmetClient,
    InmetHourlyRecord,
    _parse_br_number,
    _parse_hora,
    parse_bdmep_csv,
)


def test_parse_br_number_handles_null_markers():
    assert _parse_br_number("") is None
    assert _parse_br_number("9999") is None
    assert _parse_br_number("12,5") == pytest.approx(12.5)
    assert _parse_br_number("bad") is None


def test_parse_hora_short_input():
    assert _parse_hora("12") == "00:00"
    assert _parse_hora("1530 UTC") == "15:30"


def test_parse_bdmep_skips_incomplete_rows():
    csv_text = """Data;Hora UTC;PRECIPITAÇÃO TOTAL, HORÁRIO (mm);P1;P2;P3;RAD;TEMPERATURA DO AR - BULBO SECO, HORARIA (°C);T2;T3;T4;T5;T6;U1;U2;UMIDADE RELATIVA DO AR, HORARIA (%);DIR;RAJ;VENTO, VELOCIDADE HORARIA (m/s)
2024/01/01;1200 UTC;1,0;p;p;p;;20,0;t;t;t;t;t;t;t;50;d;r;5,0
2024/01/01;1300 UTC;bad;p;p;p;;20,0;t;t;t;t;t;t;t;50;d;r;5,0
short;row
"""
    records = parse_bdmep_csv(csv_text, station_code="A701", city="SP", uf="SP")
    assert len(records) == 1
    assert records[0].temperatura == pytest.approx(20.0)


def test_inmet_client_list_stations():
    session = MagicMock()
    session.get.return_value = MagicMock(
        json=lambda: [{"CD_ESTACAO": "A701"}],
        raise_for_status=lambda: None,
    )
    client = InmetClient(session=session)
    stations = client.list_stations()
    assert len(stations) == 1


def test_inmet_client_list_stations_invalid_response():
    session = MagicMock()
    session.get.return_value = MagicMock(
        json=lambda: {"error": "x"},
        raise_for_status=lambda: None,
    )
    client = InmetClient(session=session)
    with pytest.raises(ValueError, match="Resposta inesperada"):
        client.list_stations()


def test_fetch_bdmep_year_extracts_matching_csv():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("BR_A701_SP.csv", "Data;Hora\n2024/01/01;1200")
        zf.writestr("OTHER.csv", "ignore")
    session = MagicMock()
    session.get.return_value = MagicMock(
        content=buf.getvalue(),
        raise_for_status=lambda: None,
    )
    client = InmetClient(session=session)
    files = client.fetch_bdmep_year(2024, station_codes=["A701"])
    assert "A701" in files


def test_save_and_load_cache_csv(tmp_path):
    records = [
        InmetHourlyRecord(
            timestamp="2024-01-01T12:00:00",
            station_code="A701",
            city="São Paulo",
            uf="SP",
            temperatura=25.0,
            umidade=60.0,
            precipitacao=1.0,
            vento_kmh=18.0,
        )
    ]
    path = tmp_path / "cache.csv"
    InmetClient.save_cache_csv(path, records)
    loaded = InmetClient.load_cache_csv(path)
    assert loaded[0].temperatura == 25.0


def test_load_cache_csv_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        InmetClient.load_cache_csv(tmp_path / "missing.csv")
