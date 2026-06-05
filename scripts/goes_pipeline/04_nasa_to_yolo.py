"""
GOES Pipeline — Etapa 4: Converter imagens NASA Worldview para formato YOLO
===========================================================================
Lê screenshots PNG do NASA Worldview (data/nasa_captures/) e gera labels .txt
detectando regiões de convecção profunda (topos frios / pixels brilhantes).

Correções v2 (2026-06):
  - Letterbox 640×640 (mesmo espaço de coordenadas do treino YOLO)
  - Detecção na imagem final de treino (não na resolução original)
  - Máscara de chrome da UI NASA (canto superior esquerdo)
  - Validação de bright_ratio dentro de cada bbox

Execute a partir do root do projeto (global-solutions/):
    python scripts/goes_pipeline/04_nasa_to_yolo.py --clean
    python scripts/goes_pipeline/04_nasa_to_yolo.py --clean --limiar 175 --area 50
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from label_utils import (  # noqa: E402
    DEFAULT_AREA_PX,
    DEFAULT_LIMIAR,
    audit_dataset,
    detect_storms,
    format_audit_summary,
    letterbox_resize,
    save_audit_report,
    write_label_file,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NASA_DIR = PROJECT_ROOT / "data" / "nasa_captures"
DATASET_ROOT = PROJECT_ROOT / "data" / "model-dataset"
IMG_TRAIN = DATASET_ROOT / "images" / "train"
IMG_VAL = DATASET_ROOT / "images" / "val"
LBL_TRAIN = DATASET_ROOT / "labels" / "train"
LBL_VAL = DATASET_ROOT / "labels" / "val"
REVIEW_DIR = PROJECT_ROOT / "data" / "label_review"

for d in [IMG_TRAIN, IMG_VAL, LBL_TRAIN, LBL_VAL]:
    d.mkdir(parents=True, exist_ok=True)


def processar_imagem(
    png_path: Path,
    split: str,
    limiar: int,
    area_min: int,
) -> dict:
    """Converte um PNG NASA para imagem letterbox 640×640 + label YOLO alinhado."""
    img_dir = IMG_TRAIN if split == "train" else IMG_VAL
    lbl_dir = LBL_TRAIN if split == "train" else LBL_VAL

    stem = png_path.stem
    dst_png = img_dir / f"{stem}.png"
    dst_lbl = lbl_dir / f"{stem}.txt"

    img = cv2.imread(str(png_path))
    if img is None:
        return {"arquivo": png_path.name, "status": "erro", "erro": "Não conseguiu ler imagem"}

    img_yolo = letterbox_resize(img)
    cv2.imwrite(str(dst_png), img_yolo)

    bboxes = detect_storms(img_yolo, limiar=limiar, area_min=area_min)
    write_label_file(dst_lbl, bboxes)

    return {
        "arquivo": png_path.name,
        "split": split,
        "n_bboxes": len(bboxes),
        "status": "ok",
    }


def limpar_dataset_nao_nasa() -> int:
    """Remove imagens/labels que não são do pipeline NASA."""
    removidos = 0
    for pasta in (IMG_TRAIN, IMG_VAL, LBL_TRAIN, LBL_VAL):
        for path in list(pasta.glob("*")):
            if not path.is_file():
                continue
            if path.stem.startswith("nasa_"):
                continue
            path.unlink()
            removidos += 1
    return removidos


def limpar_splits_yolo() -> int:
    """Remove todo o conteúdo de train/val antes de reconstruir."""
    removidos = 0
    for pasta in (IMG_TRAIN, IMG_VAL, LBL_TRAIN, LBL_VAL):
        for path in list(pasta.glob("*")):
            if path.is_file():
                path.unlink()
                removidos += 1
    return removidos


def main(
    limiar: int = DEFAULT_LIMIAR,
    area_min: int = DEFAULT_AREA_PX,
    train_frac: float = 0.85,
    clean: bool = False,
    nasa_only: bool = False,
    skip_audit: bool = False,
) -> int:
    if clean:
        n = limpar_splits_yolo()
        print(f"🧹 Dataset limpo: {n} arquivo(s) removido(s) de train/val\n")
    elif nasa_only:
        n = limpar_dataset_nao_nasa()
        if n:
            print(f"🧹 Removidos {n} arquivo(s) não-NASA (Windy/outros)\n")

    arquivos = sorted(NASA_DIR.glob("*.png"))
    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum .png em {NASA_DIR}\n"
            "Rode build_dataset_nasa.command primeiro para baixar as imagens."
        )

    import numpy as np

    np.random.seed(42)
    idx_train = set(
        np.random.choice(
            len(arquivos),
            size=max(1, int(len(arquivos) * train_frac)),
            replace=False,
        )
    )

    print(f"Convertendo {len(arquivos)} imagens NASA → YOLO (pipeline v2)")
    print(f"  Limiar brilho : > {limiar}/255")
    print(f"  Área mínima   : {area_min} px")
    print(f"  Resize        : letterbox {640}×{640}")
    print(f"  UI mask       : topo {12:.0%} + esquerda {18:.0%}")
    print(f"  Split         : {train_frac:.0%} train / {1 - train_frac:.0%} val\n")

    resultados = []
    for i, arq in enumerate(arquivos):
        split = "train" if i in idx_train else "val"
        r = processar_imagem(arq, split, limiar, area_min)
        resultados.append(r)
        icon = "🌩️ " if r.get("n_bboxes", 0) > 0 else "☀️ "
        print(f"  {icon} [{split}] {arq.name} → {r.get('n_bboxes', 0)} bbox(es)")

    n_storm = sum(1 for r in resultados if r.get("n_bboxes", 0) > 0)
    n_clear = len(resultados) - n_storm
    total_boxes = sum(r.get("n_bboxes", 0) for r in resultados)

    print(f"\n{'=' * 55}")
    print(f"  Total imagens   : {len(resultados)}")
    print(f"  Com storm       : {n_storm}")
    print(f"  Sem storm (neg) : {n_clear}")
    print(f"  Total bboxes    : {total_boxes}")
    print(f"\n  Train: {IMG_TRAIN}")
    print(f"  Val  : {IMG_VAL}")

    if not skip_audit:
        print(f"\n{'=' * 55}")
        report = audit_dataset(DATASET_ROOT)
        data = save_audit_report(report, REVIEW_DIR / "audit.json")
        print(format_audit_summary(data))
        if not report.passed:
            print("\n⚠️  Auditoria falhou — revise data/label_review/ antes de treinar.")
            print("    Rode: python scripts/goes_pipeline/05_review_nasa_labels.py")
            return 1

    print("\n✓ Pronto → python src/yolo_training.py --epochs 50 --batch 8")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Converte screenshots NASA Worldview para dataset YOLO (v2)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--limiar", type=int, default=DEFAULT_LIMIAR,
                        help="Limiar de brilho (0-255) para detectar storm")
    parser.add_argument("--area", type=int, default=DEFAULT_AREA_PX,
                        help="Área mínima (px²) para gerar bbox")
    parser.add_argument("--split", type=float, default=0.85,
                        help="Fração para treino (0-1)")
    parser.add_argument("--clean", action="store_true",
                        help="Apaga train/val e reconstrói só a partir de data/nasa_captures/")
    parser.add_argument("--nasa-only", action="store_true",
                        help="Remove arquivos em train/val que não começam com nasa_")
    parser.add_argument("--skip-audit", action="store_true",
                        help="Não rodar auditoria ao final")
    args = parser.parse_args()
    raise SystemExit(
        main(
            limiar=args.limiar,
            area_min=args.area,
            train_frac=args.split,
            clean=args.clean,
            nasa_only=args.nasa_only,
            skip_audit=args.skip_audit,
        )
    )
