#!/usr/bin/env python3
"""Captura NASA GOES-East IR C13 e publica no S3 operacional.

Padrao:
- PNG em s3://$S3_BUCKET_IMAGES/nasa-satellite/YYYY/MM/DD/
- JPG em s3://$S3_BUCKET_IMAGES/screenshots/ para disparar Lambda YOLO
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.core.config import settings  # noqa: E402
from app.cron.capture_nasa_data import REGION_SETS, capturar_todas, selecionar_regioes  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Captura NASA Worldview GOES-East IR C13 e sobe para S3.",
    )
    parser.add_argument("--data", default=None, help="Data YYYY-MM-DD (default: hoje UTC)")
    parser.add_argument(
        "--region-set",
        default="brasil-operacional",
        choices=sorted(REGION_SETS),
        help="Conjunto de regiões para capturar",
    )
    parser.add_argument(
        "--regions",
        default=None,
        help="Lista CSV de regiões específicas (sobrescreve --region-set)",
    )
    parser.add_argument(
        "--no-cv-jpg",
        action="store_true",
        help="Nao enviar JPG em screenshots/ (sem trigger da Lambda YOLO)",
    )
    args = parser.parse_args()

    bucket = (settings.S3_BUCKET_IMAGES or "").strip()
    if not bucket:
        print("ERRO: configure S3_BUCKET_IMAGES no ambiente/.env", file=sys.stderr)
        return 1

    regioes = selecionar_regioes(region_set=args.region_set, regions=args.regions)
    resultados = capturar_todas(
        data=args.data,
        upload_cv_jpg=not args.no_cv_jpg,
        trigger_cv_local=False,
        regioes=regioes,
    )

    ok = [item for item in resultados if item.get("status") == "ok"]
    falhas = [item for item in resultados if item.get("status") != "ok"]

    resumo = {
        "bucket": bucket,
        "png_prefix": settings.NASA_S3_PREFIX,
        "cv_jpg_prefix": None if args.no_cv_jpg else settings.NASA_CV_S3_PREFIX,
        "region_set": args.region_set,
        "regions": [item["regiao"] for item in resultados],
        "capturas_ok": len(ok),
        "capturas_falha": len(falhas),
        "png_s3_keys": [item.get("s3_key") for item in ok if item.get("s3_key")],
        "cv_jpg_s3_keys": [item.get("cv_s3_key") for item in ok if item.get("cv_s3_key")],
    }

    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    return 0 if not falhas else 2


if __name__ == "__main__":
    raise SystemExit(main())
