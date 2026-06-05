#!/usr/bin/env python3
"""Otimiza limiares de risco agrícola via Algoritmo Genético."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="AG para limiares AgriRiskModel")
    parser.add_argument("--generations", type=int, default=15)
    parser.add_argument("--population", type=int, default=40)
    parser.add_argument("--sample", type=int, default=3000)
    parser.add_argument("--output", type=str, default="")
    args = parser.parse_args()

    from app.services.agri_threshold_ga import (  # noqa: PLC0415
        DEFAULT_THRESHOLDS_PATH,
        optimize_thresholds,
        save_thresholds,
    )

    out = Path(args.output) if args.output else DEFAULT_THRESHOLDS_PATH
    best = optimize_thresholds(
        generations=args.generations,
        population=args.population,
        sample_size=args.sample,
    )
    path = save_thresholds(best, out)
    print(f"\n✅ Limiares salvos: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
