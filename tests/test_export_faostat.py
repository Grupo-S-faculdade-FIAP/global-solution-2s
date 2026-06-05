"""Testes do exportador FAOSTAT (sem rede)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from export_faostat_brazil import (  # noqa: E402
    CropYearRecord,
    OWID_CROPS,
    build_markdown,
    infer_data_source,
    load_records_from_cache,
    parse_faostat_api,
    records_from_json_payload,
)

CACHE = ROOT / "data" / "references" / "faostat_brazil_qcl.json"


def test_crop_year_record_roundtrip():
    record = CropYearRecord(
        crop_code=656,
        crop="Café verde",
        year=2024,
        production_t=3387724.2,
        area_ha=2100000.6,
        yield_kg_ha=1613.2,
        source="owid_faostat",
    )
    restored = CropYearRecord.from_dict(record.to_dict())
    assert restored.crop_code == 656
    assert restored.production_t == 3387724
    assert restored.area_ha == 2100001
    assert restored.yield_kg_ha == 1613.2


def test_parse_faostat_api_unifies_elements():
    rows = [
        {"Item Code": "236", "Year": "2023", "Element Code": "5510", "Value": "152144240"},
        {"Item Code": "236", "Year": "2023", "Element Code": "5312", "Value": "44417784"},
        {"Item Code": "236", "Year": "2023", "Element Code": "5412", "Value": "3425.3"},
    ]
    records = parse_faostat_api(rows, years=[2023])
    assert len(records) == 4  # 4 culturas × 1 ano
    soja = next(r for r in records if r.crop_code == 236)
    assert soja.production_t == 152144240.0
    assert soja.area_ha == 44417784.0
    assert soja.yield_kg_ha == 3425.3
    assert soja.source == "faostat_api"


def test_coffee_has_owid_yield_slug():
    assert OWID_CROPS[656] == ("coffee-bean-production", "coffee-yields")


def test_build_markdown_from_records():
    records = [
        CropYearRecord(656, "Café verde", 2024, 3387724, 2100000, 1613, "owid_faostat"),
    ]
    md = build_markdown(records, data_source="test")
    assert "Café verde | 2024" in md
    assert "3.387.724" in md
    assert "2.100.000" in md
    assert "1.613" in md
    assert "--offline" in md


def test_infer_data_source():
    records = [CropYearRecord(236, "Soja", 2024, source="owid_faostat")]
    assert "Our World in Data" in infer_data_source(records)


@pytest.mark.skipif(not CACHE.exists(), reason="cache FAOSTAT não presente")
def test_load_records_from_cache():
    records = load_records_from_cache(CACHE)
    assert len(records) >= 28
    coffee_2024 = next(
        r for r in records if r.crop_code == 656 and r.year == 2024
    )
    assert coffee_2024.production_t is not None


@pytest.mark.skipif(not CACHE.exists(), reason="cache FAOSTAT não presente")
def test_legacy_json_payload_parses():
    payload = json.loads(CACHE.read_text(encoding="utf-8"))
    records = records_from_json_payload(payload)
    assert all(isinstance(r, CropYearRecord) for r in records)
