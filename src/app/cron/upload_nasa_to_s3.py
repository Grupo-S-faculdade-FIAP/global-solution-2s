"""
upload_nasa_to_s3.py — Envia capturas locais (PNG) para S3 real.

Uso:
    cd src && python -m app.cron.upload_nasa_to_s3
    cd src && python -m app.cron.upload_nasa_to_s3 --cv --limit 5
    cd src && python -m app.cron.upload_nasa_to_s3 --file ../data/nasa_captures/nasa_brasil_20260604.png
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from app.core.config import settings
from app.cron.capture_nasa_data import (
    CAPTURES_DIR,
    trigger_cv_pipeline,
    upload_s3,
    upload_s3_cv_jpg,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_DATE_IN_NAME = re.compile(r"(\d{8})_\d{4}")


def _data_from_filename(name: str) -> str:
    m = _DATE_IN_NAME.search(name)
    if m:
        raw = m.group(1)
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return datetime.utcnow().strftime("%Y-%m-%d")


def upload_file(path: Path, *, trigger_cv: bool = False) -> dict:
    data = _data_from_filename(path.name)
    s3_key = upload_s3(path, data)
    cv_key = upload_s3_cv_jpg(path) if trigger_cv else None
    cv_result = None
    if cv_key and settings.S3_BUCKET_IMAGES:
        cv_result = trigger_cv_pipeline(settings.S3_BUCKET_IMAGES, cv_key)
    return {
        "file": str(path),
        "s3_key": s3_key,
        "cv_s3_key": cv_key,
        "cv_result": cv_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload capturas NASA locais para S3")
    parser.add_argument("--file", type=Path, help="Arquivo PNG específico")
    parser.add_argument("--dir", type=Path, default=CAPTURES_DIR, help="Diretório de capturas")
    parser.add_argument("--limit", type=int, default=0, help="Máximo de arquivos (0 = todos)")
    parser.add_argument("--cv", action="store_true", help="Também envia JPG em screenshots/ e roda CV")
    args = parser.parse_args()

    bucket = (settings.S3_BUCKET_IMAGES or "").strip()
    if not bucket:
        logger.error("Configure S3_BUCKET_IMAGES no .env")
        return 1

    if args.file:
        paths = [args.file]
    else:
        paths = sorted(args.dir.glob("*.png"))

    if args.limit > 0:
        paths = paths[: args.limit]

    if not paths:
        logger.warning("Nenhum PNG encontrado em %s", args.dir)
        return 0

    ok = 0
    for path in paths:
        if not path.is_file():
            logger.warning("Ignorando (não existe): %s", path)
            continue
        result = upload_file(path, trigger_cv=args.cv)
        if result["s3_key"]:
            ok += 1
            logger.info("OK %s → %s", path.name, result["s3_key"])
        else:
            logger.error("Falha no upload: %s", path.name)

    logger.info("Concluído: %d/%d uploads para s3://%s/", ok, len(paths), bucket)
    return 0 if ok == len(paths) else 2


if __name__ == "__main__":
    raise SystemExit(main())
