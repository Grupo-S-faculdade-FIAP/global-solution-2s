#!/usr/bin/env python3
"""Exporta contexto agrícola Brasil (FAOSTAT QCL) para PDF."""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "data" / "references" / "faostat_brazil_qcl.json"
OUT_MD = ROOT / "docs" / "dados" / "FAOSTAT_BR_contexto.md"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FAO_API = "https://fenixservices.fao.org/faostat/api/v1/en/data/QCL"

CROPS = {
    236: "Soja",
    56: "Milho",
    656: "Café verde",
    15: "Trigo",
}

# Fallback OWID (dados derivados de FAOSTAT): produção + rendimento (t/ha)
OWID_CROPS = {
    236: ("soybean-production", "soybean-yields"),
    56: ("maize-production", "maize-yields"),
    656: ("coffee-bean-production", None),
    15: ("wheat-production", "wheat-yields"),
}


def fetch_faostat(years: list[int]) -> list[dict]:
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
    return [dict(zip(header, row)) for row in rows[1:]]


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


def fetch_owid_faostat(years: list[int]) -> list[dict]:
    """Normaliza produção/rendimento OWID → linhas estilo QCL."""
    records: list[dict] = []
    for crop_code, crop_name in CROPS.items():
        prod_slug, yield_slug = OWID_CROPS[crop_code]
        production = _fetch_owid_series(prod_slug)
        yields = _fetch_owid_series(yield_slug) if yield_slug else {}

        for year in years:
            prod_t = production.get(year)
            yield_t_ha = yields.get(year)
            area_ha = None
            yield_kg_ha = None
            if yield_t_ha is not None:
                yield_kg_ha = round(yield_t_ha * 1000, 1)
            if prod_t is not None and yield_t_ha and yield_t_ha > 0:
                area_ha = round(prod_t / yield_t_ha)

            records.append({
                "source": "owid_faostat",
                "crop_code": crop_code,
                "crop": crop_name,
                "year": year,
                "production_t": round(prod_t) if prod_t is not None else None,
                "area_ha": area_ha,
                "yield_kg_ha": yield_kg_ha,
            })
    return records


def _fmt_num(val) -> str:
    if val is None or val == "":
        return "—"
    try:
        return f"{float(val):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return str(val)


def build_markdown(
    rows: list[dict],
    years: list[int],
    *,
    data_source: str,
) -> str:
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

    if rows and rows[0].get("source") == "owid_faostat":
        for rec in sorted(rows, key=lambda r: (r["crop"], -r["year"])):
            lines.append(
                f"| {rec['crop']} | {rec['year']} | "
                f"{_fmt_num(rec.get('production_t'))} | "
                f"{_fmt_num(rec.get('area_ha'))} | "
                f"{_fmt_num(rec.get('yield_kg_ha'))} |"
            )
    elif rows:
        for crop_code, crop_name in CROPS.items():
            for year in sorted(years, reverse=True):
                prod = area = yield_ = "—"
                for row in rows:
                    if str(row.get("Item Code")) != str(crop_code):
                        continue
                    if str(row.get("Year")) != str(year):
                        continue
                    el = str(row.get("Element Code"))
                    val = row.get("Value", "—")
                    if el == "5510":
                        prod = _fmt_num(val)
                    elif el == "5312":
                        area = _fmt_num(val)
                    elif el == "5412":
                        yield_ = _fmt_num(val)
                lines.append(f"| {crop_name} | {year} | {prod} | {area} | {yield_} |")
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
        "```",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    years = list(range(2018, 2025))
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)

    try:
        rows = fetch_faostat(years)
        source = "API FAOSTAT (fenixservices.fao.org)"
        OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("API FAOSTAT indisponível (%s) — usando OWID/FAOSTAT", exc)
        rows = fetch_owid_faostat(years)
        source = "Our World in Data (grapher CSV, derivado de FAOSTAT QCL)"
        OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    OUT_MD.write_text(build_markdown(rows, years, data_source=source), encoding="utf-8")
    print(f"✅ FAOSTAT JSON: {OUT_JSON}")
    print(f"✅ FAOSTAT MD:   {OUT_MD} ({source})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
