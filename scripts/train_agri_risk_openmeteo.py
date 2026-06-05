#!/usr/bin/env python3
"""Retreina AgriRiskModel com histórico Open-Meteo (dados reais)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> int:
    from app.services import agri_risk_model  # noqa: PLC0415

    agri_risk_model.treinar_e_salvar(prefer_real=True)
    print(f"\n✅ Modelo salvo: {agri_risk_model.MODEL_PATH}")
    print(f"   Fonte: {agri_risk_model.DATASET_SOURCE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
