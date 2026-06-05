"""
Revisão amostral dos labels NASA auto-gerados (pipeline v2).

Gera overlays em data/label_review/ e relatório JSON com flags de qualidade:
  - bbox_fantasma / bbox_canto_fixo
  - possivel_fn_sem_bbox
  - muitas_bboxes
  - bboxes_muito_pequenas

Uso (root do projeto):
    python scripts/goes_pipeline/05_review_nasa_labels.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from label_utils import (  # noqa: E402
    DEFAULT_AREA_PX,
    DEFAULT_LIMIAR,
    audit_dataset,
    is_ghost_bbox,
    load_bboxes,
    save_audit_report,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / "data" / "model-dataset"
REVIEW_DIR = PROJECT_ROOT / "data" / "label_review"


def _bright_ratio(gray: np.ndarray, limiar: int) -> float:
    return float((gray > limiar).sum()) / gray.size


def _draw_overlay(img: np.ndarray, bboxes: list, title: str) -> np.ndarray:
    out = img.copy()
    h, w = out.shape[:2]
    for xc, yc, bw, bh in bboxes:
        x1 = int((xc - bw / 2) * w)
        y1 = int((yc - bh / 2) * h)
        x2 = int((xc + bw / 2) * w)
        y2 = int((yc + bh / 2) * h)
        color = (0, 0, 255) if is_ghost_bbox(xc, yc, bw, bh) else (0, 255, 0)
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
    cv2.putText(out, title, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
    return out


def revisar(max_amostras: int = 32) -> dict:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    flags: list[dict] = []
    amostras: list[Path] = []

    for split in ("train", "val"):
        img_dir = DATASET_ROOT / "images" / split
        lbl_dir = DATASET_ROOT / "labels" / split
        for img_path in sorted(img_dir.glob("nasa_*.png")):
            lbl_path = lbl_dir / f"{img_path.stem}.txt"
            img = cv2.imread(str(img_path))
            if img is None:
                continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            bright = _bright_ratio(gray, DEFAULT_LIMIAR)
            bboxes = load_bboxes(lbl_path)
            n = len(bboxes)

            motivos: list[str] = []
            if n == 0 and bright > 0.02:
                motivos.append("possivel_fn_sem_bbox")
            if n >= 8:
                motivos.append("muitas_bboxes")
            if n > 0:
                areas = [bb[2] * bb[3] for bb in bboxes]
                if max(areas) < 0.002:
                    motivos.append("bboxes_muito_pequenas")
                if any(is_ghost_bbox(*bb) for bb in bboxes):
                    motivos.append("bbox_fantasma")
                if all(bb[0] < 0.18 and bb[1] < 0.20 for bb in bboxes):
                    motivos.append("bbox_canto_fixo")

            entry = {
                "arquivo": img_path.name,
                "split": split,
                "n_bboxes": n,
                "bright_ratio": round(bright, 4),
                "motivos": motivos,
            }
            if motivos:
                flags.append(entry)
                amostras.append(img_path)

    audit = audit_dataset(DATASET_ROOT)
    save_audit_report(audit, REVIEW_DIR / "audit.json")

    rng = np.random.default_rng(42)
    all_imgs = sorted((DATASET_ROOT / "images" / "train").glob("nasa_*.png"))
    if all_imgs:
        extra_idx = rng.choice(len(all_imgs), size=min(10, len(all_imgs)), replace=False)
        for i in extra_idx:
            p = all_imgs[i]
            if p not in amostras:
                amostras.append(p)

    amostras = amostras[:max_amostras]
    for img_path in amostras:
        split = img_path.parent.name
        lbl_path = DATASET_ROOT / "labels" / split / f"{img_path.stem}.txt"
        img = cv2.imread(str(img_path))
        bboxes = load_bboxes(lbl_path)
        motivos = next((f["motivos"] for f in flags if f["arquivo"] == img_path.name), [])
        tag = ",".join(motivos) if motivos else "amostra"
        title = f"{img_path.name} | {len(bboxes)} bbox | {tag}"
        overlay = _draw_overlay(img, bboxes, title)
        cv2.imwrite(str(REVIEW_DIR / f"{img_path.stem}_review.jpg"), overlay)

    relatorio = {
        "pipeline_version": "v2",
        "limiar_ref": DEFAULT_LIMIAR,
        "area_ref_px": DEFAULT_AREA_PX,
        "audit_passed": audit.passed,
        "audit_failures": audit.failures,
        "total_flags": len(flags),
        "flags": flags,
        "overlays_em": str(REVIEW_DIR),
        "recomendacao": _recomendacao(flags, audit),
    }
    out_json = REVIEW_DIR / "relatorio.json"
    out_json.write_text(
        json.dumps(relatorio, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return relatorio


def _recomendacao(flags: list[dict], audit) -> str:
    ghosts = sum(1 for f in flags if "bbox_fantasma" in f["motivos"])
    canto = sum(1 for f in flags if "bbox_canto_fixo" in f["motivos"])
    fn = sum(1 for f in flags if "possivel_fn_sem_bbox" in f["motivos"])
    many = sum(1 for f in flags if "muitas_bboxes" in f["motivos"])

    if ghosts or canto or not audit.passed:
        return (
            "BLOQUEADO: bboxes fantasma ou quality gate falhou. "
            "Regenere com: python scripts/goes_pipeline/04_nasa_to_yolo.py --clean"
        )
    if fn >= 10 and many < 3:
        return "Considerar --limiar 190 na conversão (muitos FN)."
    if many >= 5:
        return "Considerar --area 800 ou --limiar 205 (ruído / bboxes em excesso)."
    if fn >= 5 and many >= 3:
        return "Revisar overlays manualmente; limiar/área podem variar por região."
    return "Labels aceitáveis para retreino; revisar overlays em data/label_review/."


def main():
    r = revisar()
    print(f"Audit passed : {r['audit_passed']}")
    print(f"Flags        : {r['total_flags']}")
    print(f"Recomendação : {r['recomendacao']}")
    print(f"Overlays     : {r['overlays_em']}")
    print(f"Relatório    : data/label_review/relatorio.json")


if __name__ == "__main__":
    main()
