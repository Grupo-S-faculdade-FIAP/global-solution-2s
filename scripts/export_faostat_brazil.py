#!/usr/bin/env python3
"""Exporta contexto agrícola Brasil (FAOSTAT QCL) para PDF."""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "data" / "references" / "faostat_brazil_qcl.json"
OUT_MD = ROOT / "docs" / "dados" / "FAOSTAT_BR_contexto.md"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FAO_API = "https://fenixservices.fao.org/faostat/api/v1/en/data/QCL"

CROPS: dict[int, str] = {
    236: "Soja",
    56: "Milho",
    656: "Café verde",
    15: "Trigo",
}

# Fallback OWID (derivado FAOSTAT): produção (t) + rendimento (t/ha)
OWID_CROPS: dict[int, tuple[str, str | None]] = {
    236: ("soybean-production", "soybean-yields"),
    56: ("maize-production", "maize-yields"),
    656: ("coffee-bean-production", "coffee-yields"),
    15: ("wheat-production", "wheat-yields"),
}

SOURCE_LABELS = {
    "faostat_api": "API FAOSTAT (fenixservices.fao.org)",
    "owid_faostat": "Our World in Data (grapher CSV, derivado de FAOSTAT QCL)",
    "cached_json": "cache local (data/references/faostat_brazil_qcl.json)",
}


@dataclass
class CropYearRecord:
    """Registro unificado: API FAOSTAT, OWID ou JSON em cache."""

    crop_code: int
    crop: str
    year: int
    production_t: float | None = None
    area_ha: float | None = None
    yield_kg_ha: float | None = None
    source: str = "unknown"

    def to_dict(self) -> dict:
        out = asdict(self)
        if out["production_t"] is not None:
            out["production_t"] = round(out["production_t"])
        if out["area_ha"] is not None:
            out["area_ha"] = round(out["area_ha"])
        if out["yield_kg_ha"] is not None:
            out["yield_kg_ha"] = round(out["yield_kg_ha"], 1)
        return out

    @classmethod
    def from_dict(cls, data: dict) -> CropYearRecord:
        return cls(
            crop_code=int(data["crop_code"]),
            crop=str(data["crop"]),
            year=int(data["year"]),
            production_t=_optional_float(data.get("production_t")),
            area_ha=_optional_float(data.get("area_ha")),
            yield_kg_ha=_optional_float(data.get("yield_kg_ha")),
            source=str(data.get("source", "cached_json")),
        )


def _optional_float(value) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _derive_area_ha(production_t: float | None, yield_t_ha: float | None) -> float | None:
    if production_t is not None and yield_t_ha and yield_t_ha > 0:
        return round(production_t / yield_t_ha)
    return None


def records_from_json_payload(payload: list[dict]) -> list[CropYearRecord]:
    return [CropYearRecord.from_dict(item) for item in payload]


def records_to_json_payload(records: list[CropYearRecord]) -> list[dict]:
    return [record.to_dict() for record in records]


def infer_data_source(records: list[CropYearRecord]) -> str:
    if not records:
        return "sem dados"
    source = records[0].source
    return SOURCE_LABELS.get(source, f"cache ({source})")


def parse_faostat_api(rows: list[dict], years: list[int]) -> list[CropYearRecord]:
    records: list[CropYearRecord] = []
    for crop_code, crop_name in CROPS.items():
        for year in years:
            record = CropYearRecord(
                crop_code=crop_code,
                crop=crop_name,
                year=year,
                source="faostat_api",
            )
            for row in rows:
                if str(row.get("Item Code")) != str(crop_code):
                    continue
                if str(row.get("Year")) != str(year):
                    continue
                element = str(row.get("Element Code"))
                value = _optional_float(row.get("Value"))
                if value is None:
                    continue
                if element == "5510":
                    record.production_t = value
                elif element == "5312":
                    record.area_ha = value
                elif element == "5412":
                    record.yield_kg_ha = value
            records.append(record)
    return records


def fetch_faostat(years: list[int]) -> list[CropYearRecord]:
    params = {
        "area": 21,
        "element": [5510, 5312, 5412],
        "item": list(CROPS.keys()),
        "year": years,
        "show_codes": "true",
        "null_values": "true",
        "format": "json",
        "output_type": "objects",
    }
    resp = requests.get(FAO_API, params=params, timeout=120)
    resp.raise_for_status()
    payload = resp.json()
    rows = payload.get("data", [])
    if len(rows) < 2:
        raise ValueError("FAOSTAT retornou dados vazios")
    header = rows[0]
    dict_rows = [dict(zip(header, row)) for row in rows[1:]]
    return parse_faostat_api(dict_rows, years)


def _fetch_owid_series(slug: str) -> dict[int, float]:
    url = (
        f"https://ourworldindata.org/grapher/{slug}.csv"
        "?v=1&csvType=full&useColumnShortNames=true"
    )
    resp = requests.get(url, timeout=60, headers={"User-Agent": "global-solutions/1.0"})
    resp.raise_for_status()
    out: dict[int, float] = {}
    for row in csv.DictReader(io.StringIO(resp.text)):
        if row.get("entity") != "Brazil":
            continue
        year = int(float(row["year"]))
        for key, val in row.items():
            if key in ("entity", "code", "year") or not (val or "").strip():
                continue
            try:
                out[year] = float(val)
                break
            except ValueError:
                continue
    return out


def fetch_owid_faostat(years: list[int]) -> list[CropYearRecord]:
    records: list[CropYearRecord] = []
    for crop_code, crop_name in CROPS.items():
        prod_slug, yield_slug = OWID_CROPS[crop_code]
        production = _fetch_owid_series(prod_slug)
        yields = _fetch_owid_series(yield_slug) if yield_slug else {}

        for year in years:
            prod_t = production.get(year)
            yield_t_ha = yields.get(year)
            yield_kg_ha = round(yield_t_ha * 1000, 1) if yield_t_ha is not None else None
            area_ha = _derive_area_ha(prod_t, yield_t_ha)
            records.append(
                CropYearRecord(
                    crop_code=crop_code,
                    crop=crop_name,
                    year=year,
                    production_t=prod_t,
                    area_ha=area_ha,
                    yield_kg_ha=yield_kg_ha,
                    source="owid_faostat",
                )
            )
    return records


def load_records_from_cache(path: Path = OUT_JSON) -> list[CropYearRecord]:
    if not path.exists():
        raise FileNotFoundError(f"Cache ausente: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"JSON inválido (esperada lista): {path}")
    return records_from_json_payload(payload)


def _fmt_num(val) -> str:
    if val is None or val == "":
        return "—"
    try:
        return f"{float(val):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return str(val)


def build_markdown(records: list[CropYearRecord], *, data_source: str) -> str:
    lines = [
        "# Contexto agrícola brasileiro — FAOSTAT (QCL)",
        "",
        f"**Gerado em:** {date.today().isoformat()}  ",
        "**Fonte primária:** [FAOSTAT — Production: Crops and livestock products (QCL)](https://www.fao.org/faostat/en/#data/QCL)  ",
        f"**Proveniência desta exportação:** {data_source}  ",
        "**Área:** Brasil (código FAO 21)  ",
        "",
        "> Uso: seção *Contexto* e *Resultados* do PDF FIAP. Não alimenta o modelo ML em runtime.",
        "",
        "## Por que FAOSTAT aqui?",
        "",
        "O **INMET** calibra o modelo de risco com medições meteorológicas oficiais. O **FAOSTAT** contextualiza o **impacto econômico-agricultural**: produção, área e rendimento das principais culturas — conectando clima extremo à volatilidade da safra brasileira.",
        "",
        "## Tabela resumo (últimos anos)",
        "",
        "| Cultura | Ano | Produção (t) | Área colhida (ha) | Rendimento (kg/ha) |",
        "|---------|-----|--------------|-------------------|---------------------|",
    ]

    if records:
        for record in sorted(records, key=lambda item: (item.crop, -item.year)):
            lines.append(
                f"| {record.crop} | {record.year} | "
                f"{_fmt_num(record.production_t)} | "
                f"{_fmt_num(record.area_ha)} | "
                f"{_fmt_num(record.yield_kg_ha)} |"
            )
    else:
        lines.append("| _sem dados_ | — | — | — | — |")

    lines.extend([
        "",
        "## Insights para o PDF (roteiro)",
        "",
        "1. **Clima → decisão no campo:** alertas YOLO + risco ML (INMET) antecipam janelas críticas.",
        "2. **Clima → safra:** eventos como El Niño reduzem rendimento (ex.: soja 2023/24) — FAOSTAT quantifica escala nacional.",
        "3. **Brasil como celeiro:** soja e milho concentram área colhida; variabilidade climática afeta cadeia de exportação.",
        "",
        "## Complementos narrativos (sem código)",
        "",
        "- **ZARC (MAPA):** zoneamento de risco climático para culturas.",
        "- **CONAB:** acompanhamento de safras brasileiras (complemento nacional ao FAOSTAT).",
        "",
        "## Reproduzir",
        "",
        "```bash",
        "make export-faostat",
        "# offline (sem rede):",
        "python scripts/export_faostat_brazil.py --offline",
        "```",
        "",
    ])
    return "\n".join(lines)


def write_outputs(records: list[CropYearRecord], *, data_source: str) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(records_to_json_payload(records), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    OUT_MD.write_text(build_markdown(records, data_source=data_source), encoding="utf-8")


def fetch_records(years: list[int]) -> tuple[list[CropYearRecord], str]:
    try:
        records = fetch_faostat(years)
        return records, SOURCE_LABELS["faostat_api"]
    except Exception as exc:
        logger.warning("API FAOSTAT indisponível (%s) — usando OWID/FAOSTAT", exc)
        records = fetch_owid_faostat(years)
        return records, SOURCE_LABELS["owid_faostat"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Exporta contexto FAOSTAT Brasil")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Regenera o Markdown a partir de data/references/faostat_brazil_qcl.json (sem rede)",
    )
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=list(range(2018, 2025)),
        help="Anos a exportar (default: 2018–2024)",
    )
    args = parser.parse_args()

    if args.offline:
        try:
            records = load_records_from_cache()
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
            logger.error("%s", exc)
            return 1
        data_source = infer_data_source(records)
        OUT_MD.write_text(build_markdown(records, data_source=data_source), encoding="utf-8")
        print(f"✅ FAOSTAT MD (offline): {OUT_MD} ({data_source})")
        return 0

    records, data_source = fetch_records(args.years)
    write_outputs(records, data_source=data_source)
    print(f"✅ FAOSTAT JSON: {OUT_JSON}")
    print(f"✅ FAOSTAT MD:   {OUT_MD} ({data_source})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
