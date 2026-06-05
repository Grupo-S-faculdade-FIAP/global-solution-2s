#!/usr/bin/env python3
"""Baixa BDMEP INMET (ZIP anual) e gera cache de treino ML."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

DEFAULT_CACHE = ROOT / "data" / "weather" / "inmet" / "training_cache.csv"
DEFAULT_SAMPLE = ROOT / "data" / "weather" / "inmet" / "sample_inmet_bdmep.csv"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch INMET BDMEP training cache")
    parser.add_argument("--years", nargs="+", type=int, default=[2024])
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--sample-rows", type=int, default=500)
    args = parser.parse_args()

    from app.clients.inmet import InmetClient  # noqa: PLC0415

    client = InmetClient()
    records = client.load_training_records(years=args.years)
    client.save_cache_csv(args.cache, records)
    print(f"\n✅ Cache INMET: {args.cache} ({len(records)} registros)")

    if args.sample_rows > 0:
        sample = records[: args.sample_rows]
        client.save_cache_csv(args.sample, sample)
        print(f"✅ Amostra CI: {args.sample} ({len(sample)} registros)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
