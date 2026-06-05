"""
Auditoria de qualidade dos labels YOLO (NASA pipeline).

Detecta bboxes fantasma, duplicatas globais e distribuição de negativos.
Usado como gate antes do treinamento (yolo_training.py).

Uso (root do projeto):
    python scripts/goes_pipeline/06_audit_labels.py
    python scripts/goes_pipeline/06_audit_labels.py --strict   # exit 1 se falhar
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from label_utils import audit_dataset, format_audit_summary, save_audit_report  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / "data" / "model-dataset"
OUT_JSON = PROJECT_ROOT / "data" / "label_review" / "audit.json"


def main(strict: bool = False) -> int:
    report = audit_dataset(DATASET_ROOT)
    data = save_audit_report(report, OUT_JSON)
    print(format_audit_summary(data))
    print(f"\nRelatório: {OUT_JSON}")

    if strict and not report.passed:
        return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auditoria de labels YOLO NASA")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit code 1 se o quality gate falhar",
    )
    args = parser.parse_args()
    raise SystemExit(main(strict=args.strict))
