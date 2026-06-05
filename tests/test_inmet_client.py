"""Tests for INMET BDMEP parser and cache."""

from pathlib import Path

import pytest

from app.clients.inmet import InmetClient, parse_bdmep_csv

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "weather" / "inmet" / "sample_inmet_bdmep.csv"


def test_parse_bdmep_minimal():
    csv_text = """REGIAO:;SE
UF:;SP
ESTACAO:;SAO PAULO - MIRANTE
CODIGO (WMO):;A701
LATITUDE:;-23,49
LONGITUDE:;-46,62
ALTITUDE:;785
DATA DE FUNDACAO:;25/07/06
Data;Hora UTC;PRECIPITAÇÃO TOTAL, HORÁRIO (mm);P1;P2;P3;RAD;TEMPERATURA DO AR - BULBO SECO, HORARIA (°C);T2;T3;T4;T5;T6;U1;U2;UMIDADE RELATIVA DO AR, HORARIA (%);DIR;RAJ;VENTO, VELOCIDADE HORARIA (m/s)
2024/01/01;1200 UTC;5,2;p;p;p;;32,1;t;t;t;t;t;t;t;88;d;r;12,5
"""
    records = parse_bdmep_csv(csv_text, station_code="A701", city="São Paulo", uf="SP")
    assert len(records) == 1
    assert records[0].temperatura == pytest.approx(32.1)
    assert records[0].umidade == 88
    assert records[0].precipitacao == pytest.approx(5.2)
    assert records[0].vento_kmh == pytest.approx(45.0)


def test_load_sample_cache_if_present():
    if not SAMPLE.exists():
        pytest.skip("sample_inmet_bdmep.csv ausente — rode make fetch-inmet")
    records = InmetClient.load_cache_csv(SAMPLE)
    assert len(records) >= 10
    feats = records[0].as_features()
    assert len(feats) == 4
