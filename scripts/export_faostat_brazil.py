#!/usr/bin/env python3
"""Exporta contexto agrícola Brasil (FAOSTAT QCL) para PDF."""

from __future__ import annotations

import json
import logging
import sys
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "data" / "references" / "faostat_brazil_qcl.json"
OUT_MD = ROOT / "docs" / "dados" / "FAOSTAT_BR_contexto.md"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FAO_API = "https://fenixservices.fao.org/faostat/api/v1/en/data/QCL"

# Brasil=21; Element: 5510 produção t, 5312 área ha, 5412 yield kg/ha
CROPS = {
    236: "Soja",
    56: "Milho",
    656: "Café verde",
    15: "Trigo",
}
ELEMENTS = {
    5510: "Produção (t)",
    5312: "Área colhida (ha)",
    5412: "Rendimento (kg/ha)",
}


def fetch_faostat(years: list[int]) -> list[dict]:
    params = {
        "area": 21,
        "element": list(ELEMENTS.keys()),
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


def build_markdown(rows: list[dict], years: list[int]) -> str:
    lines = [
        "# Contexto agrícola brasileiro — FAOSTAT (QCL)",
        "",
        f"**Gerado em:** {date.today().isoformat()}  ",
        "**Fonte:** [FAOSTAT — Production: Crops and livestock products (QCL)](https://www.fao.org/faostat/en/#data/QCL)  ",
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

    if not rows:
        lines.extend([
            "| _Preencher via `make export-faostat`_ | — | — | — | — |",
            "",
            "> API FAO retornou indisponível nesta execução. Consulte manualmente em",
            "> https://www.fao.org/faostat/en/#data/QCL (Brasil, QCL, 2018–2024).",
        ])
    else:
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
                        prod = val
                    elif el == "5312":
                        area = val
                    elif el == "5412":
                        yield_ = val
                lines.append(f"| {crop_name} | {year} | {prod} | {area} | {yield_} |")

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
        "Se a API FAO retornar erro, consulte manualmente: https://www.fao.org/faostat/en/#data/QCL",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    years = list(range(2018, 2025))
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)

    try:
        rows = fetch_faostat(years)
        OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        OUT_MD.write_text(build_markdown(rows, years), encoding="utf-8")
        print(f"✅ FAOSTAT JSON: {OUT_JSON}")
        print(f"✅ FAOSTAT MD:   {OUT_MD}")
        return 0
    except Exception as exc:
        logger.warning("API FAOSTAT indisponível (%s) — gravando template em %s", exc, OUT_MD)
        OUT_MD.write_text(build_markdown([], years), encoding="utf-8")
        print(f"⚠️  FAOSTAT API offline — template em {OUT_MD}")
        print("   Reexecute: make export-faostat")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
