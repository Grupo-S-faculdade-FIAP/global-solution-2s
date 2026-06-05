#!/usr/bin/env python3
"""
Pipeline agrícola unificado: INMET BDMEP → FAOSTAT → treino AgriRiskModel.

Usado por make build-agri, build_dataset_agri.command e CI/deploy.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
MODELS_DIR = ROOT / "models"
INMET_SAMPLE = ROOT / "data" / "weather" / "inmet" / "sample_inmet_bdmep.csv"
REQUIRED_MODELS = (
    "agri_risk_model.pkl",
    "agri_risk_scaler.pkl",
    "agri_risk_meta.pkl",
    "agri_risk_thresholds.json",
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _run(cmd: list[str], desc: str) -> int:
    logger.info("→ %s", desc)
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    if result.returncode != 0:
        logger.error("Falhou: %s (exit %d)", desc, result.returncode)
    return result.returncode


def verify_models() -> bool:
    missing = [name for name in REQUIRED_MODELS if not (MODELS_DIR / name).exists()]
    if missing:
        logger.error("Modelos ausentes em %s: %s", MODELS_DIR, ", ".join(missing))
        return False
    logger.info("✓ Modelos OK em %s", MODELS_DIR)
    return True


def _read_dataset_source() -> str:
    import pickle

    meta_path = MODELS_DIR / "agri_risk_meta.pkl"
    if not meta_path.exists():
        return "unknown"
    with open(meta_path, "rb") as handle:
        return pickle.load(handle).get("dataset_source", "unknown")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pipeline agrícola: INMET + FAOSTAT + AgriRiskModel",
    )
    parser.add_argument("--years", nargs="+", type=int, default=[2024])
    parser.add_argument("--skip-fetch", action="store_true", help="Não baixa INMET BDMEP")
    parser.add_argument("--skip-faostat", action="store_true", help="Não exporta FAOSTAT")
    parser.add_argument("--skip-train", action="store_true", help="Não retreina o modelo")
    parser.add_argument(
        "--skip-ga",
        action="store_true",
        help="Não executa AG nos limiares (CI usa agri_risk_thresholds.json commitado)",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Modo CI: usa sample INMET commitado (sem download ZIP ~98 MB)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Apenas verifica se models/*.pkl existem (deploy)",
    )
    args = parser.parse_args()

    if args.verify_only:
        return 0 if verify_models() else 1

    python = sys.executable

    if not args.skip_fetch:
        if args.ci:
            if not INMET_SAMPLE.exists():
                logger.error("Sample INMET ausente: %s", INMET_SAMPLE)
                return 1
            logger.info("CI: treino usará sample INMET (%s)", INMET_SAMPLE.name)
        else:
            year_args = [str(y) for y in args.years]
            rc = _run(
                [python, str(SCRIPTS / "fetch_inmet_bdmep.py"), "--years", *year_args],
                f"INMET BDMEP ({', '.join(year_args)})",
            )
            if rc != 0:
                return rc

    if not args.skip_faostat:
        rc = _run(
            [python, str(SCRIPTS / "export_faostat_brazil.py")],
            "FAOSTAT contexto Brasil",
        )
        if rc != 0:
            return rc

    if not args.skip_ga and not args.skip_train:
        ga_cmd = [
            python,
            str(SCRIPTS / "optimize_agri_thresholds.py"),
            "--generations", "8" if args.ci else "15",
            "--population", "20" if args.ci else "40",
            "--sample", "500" if args.ci else "3000",
        ]
        rc = _run(ga_cmd, "AG limiares AgriRiskModel")
        if rc != 0:
            return rc
    elif args.skip_ga:
        logger.info("GA ignorado — usando agri_risk_thresholds.json existente")

    if not args.skip_train:
        rc = _run(
            [python, str(SCRIPTS / "train_agri_risk_openmeteo.py")],
            "Treino AgriRiskModel",
        )
        if rc != 0:
            return rc

    if not verify_models():
        return 1

    source = _read_dataset_source()
    logger.info("Pipeline concluído — dataset_source=%s", source)
    print(f"\n✅ Pipeline agrícola OK — fonte: {source}")
    print(f"   Modelos: {MODELS_DIR}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
