"""
GOES Pipeline — Etapa 7: Augmentação do dataset YOLO para detecção de tempestades
==================================================================================
Lê imagens + labels de data/model-dataset/ (pipeline v2) e gera versões augmentadas
em data/training-dataset-1000/ para ampliar o dataset de treinamento.

Augmentações aplicadas (3 por imagem → total ≈ original × 4):
  1. flip_h      — flip horizontal (bboxes ajustadas)
  2. brightness  — variação aleatória de brilho/contraste (±15%)
  3. rotate10    — rotação aleatória ±10° (bboxes rotacionadas → AABB recalculado)

Execute a partir do root do projeto (global-solutions/):
    python scripts/goes_pipeline/07_augment_dataset.py
    python scripts/goes_pipeline/07_augment_dataset.py --target 500
"""

from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DATASET  = PROJECT_ROOT / "data" / "model-dataset"
DST_DATASET  = PROJECT_ROOT / "data" / "training-dataset-1000"

YOLO_SIZE = 640
RANDOM_SEED = 42


# ── Transformações de imagem ───────────────────────────────────────────────────

def _flip_h(img: np.ndarray) -> np.ndarray:
    return cv2.flip(img, 1)


def _adjust_brightness(img: np.ndarray, alpha: float, beta: int) -> np.ndarray:
    """alpha = contraste (0.85–1.15), beta = brilho (-30..30)."""
    out = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
    return out


def _rotate(img: np.ndarray, angle: float) -> np.ndarray:
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REFLECT)


# ── Transformações de labels YOLO ──────────────────────────────────────────────

def _read_labels(path: Path) -> list[tuple[int, float, float, float, float]]:
    labels = []
    if path.exists():
        for line in path.read_text().splitlines():
            parts = line.strip().split()
            if len(parts) == 5:
                cls, xc, yc, w, h = int(parts[0]), *map(float, parts[1:])
                labels.append((cls, xc, yc, w, h))
    return labels


def _write_labels(path: Path, labels: list[tuple]) -> None:
    lines = [f"{c} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}" for c, xc, yc, w, h in labels]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _labels_flip_h(labels: list[tuple]) -> list[tuple]:
    return [(c, 1.0 - xc, yc, w, h) for c, xc, yc, w, h in labels]


def _bbox_rotate(xc: float, yc: float, bw: float, bh: float, angle_deg: float,
                 img_w: int = YOLO_SIZE, img_h: int = YOLO_SIZE) -> tuple[float, float, float, float]:
    """Rotaciona uma bbox YOLO (normalizada) e retorna nova AABB normalizada."""
    cx, cy = xc * img_w, yc * img_h
    hw, hh = bw * img_w / 2, bh * img_h / 2

    corners = np.array([
        [cx - hw, cy - hh],
        [cx + hw, cy - hh],
        [cx + hw, cy + hh],
        [cx - hw, cy + hh],
    ], dtype=np.float32)

    theta = np.radians(-angle_deg)
    cos_t, sin_t = np.cos(theta), np.sin(theta)
    ox, oy = img_w / 2, img_h / 2

    rotated = np.array([
        [cos_t * (px - ox) - sin_t * (py - oy) + ox,
         sin_t * (px - ox) + cos_t * (py - oy) + oy]
        for px, py in corners
    ])

    x_min, y_min = rotated[:, 0].min(), rotated[:, 1].min()
    x_max, y_max = rotated[:, 0].max(), rotated[:, 1].max()

    new_xc = np.clip((x_min + x_max) / 2 / img_w, 0.0, 1.0)
    new_yc = np.clip((y_min + y_max) / 2 / img_h, 0.0, 1.0)
    new_w  = np.clip((x_max - x_min) / img_w, 0.0, 1.0)
    new_h  = np.clip((y_max - y_min) / img_h, 0.0, 1.0)
    return float(new_xc), float(new_yc), float(new_w), float(new_h)


def _labels_rotate(labels: list[tuple], angle: float) -> list[tuple]:
    result = []
    for c, xc, yc, w, h in labels:
        new_xc, new_yc, new_w, new_h = _bbox_rotate(xc, yc, w, h, angle)
        if new_w > 0.005 and new_h > 0.005:
            result.append((c, new_xc, new_yc, new_w, new_h))
    return result


# ── Geração do dataset augmentado ─────────────────────────────────────────────

def _collect_pairs(src: Path) -> list[tuple[Path, Path]]:
    """Retorna pares (image_path, label_path) de train/ e val/."""
    pairs = []
    for split in ("train", "val"):
        img_dir = src / "images" / split
        lbl_dir = src / "labels" / split
        if not img_dir.exists():
            continue
        for img_path in sorted(img_dir.glob("*.png")):
            lbl_path = lbl_dir / f"{img_path.stem}.txt"
            pairs.append((img_path, lbl_path))
    return pairs


def _split_for_pair(img_path: Path, src: Path) -> str:
    """Determina se a imagem estava em train ou val."""
    return "train" if (src / "images" / "train" / img_path.name).exists() else "val"


def _save(img: np.ndarray, labels: list[tuple],
          dst_img_dir: Path, dst_lbl_dir: Path, stem: str) -> None:
    dst_img_dir.mkdir(parents=True, exist_ok=True)
    dst_lbl_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dst_img_dir / f"{stem}.png"), img)
    _write_labels(dst_lbl_dir / f"{stem}.txt", labels)


def _write_yaml(dst: Path) -> None:
    yaml_path = dst / "storm.yaml"
    yaml_path.write_text(
        f"path: {dst}\n"
        "train: images/train\n"
        "val: images/val\n"
        "nc: 1\n"
        "names:\n"
        "  0: storm\n",
        encoding="utf-8",
    )
    print(f"  yaml → {yaml_path}")


def augment(target: int = 300) -> int:
    rng = random.Random(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    pairs = _collect_pairs(SRC_DATASET)
    if not pairs:
        raise FileNotFoundError(
            f"Nenhuma imagem encontrada em {SRC_DATASET}/images/\n"
            "Rode build_dataset_nasa.command ou 04_nasa_to_yolo.py primeiro."
        )

    n_originals = len(pairs)
    augments_needed = max(0, target - n_originals)
    augments_per_img = max(1, -(-augments_needed // n_originals))  # ceil division

    print(f"\n{'='*60}")
    print(f"  Dataset origem  : {SRC_DATASET}")
    print(f"  Dataset destino : {DST_DATASET}")
    print(f"  Originais       : {n_originals}")
    print(f"  Augmentações/img: {augments_per_img}")
    print(f"  Target          : ≥ {target} imagens")
    print(f"{'='*60}\n")

    # Limpa destino e recria estrutura
    if DST_DATASET.exists():
        shutil.rmtree(DST_DATASET)

    saved = 0

    for img_path, lbl_path in pairs:
        split = _split_for_pair(img_path, SRC_DATASET)
        img_dir = DST_DATASET / "images" / split
        lbl_dir = DST_DATASET / "labels" / split

        img = cv2.imread(str(img_path))
        if img is None:
            print(f"  [ERRO] não leu {img_path.name}")
            continue
        labels = _read_labels(lbl_path)

        # Copia original
        _save(img, labels, img_dir, lbl_dir, img_path.stem)
        saved += 1

        aug_list = []

        # 1. Flip horizontal
        aug_list.append(("fh", _flip_h(img), _labels_flip_h(labels)))

        # 2. Brilho +15%
        alpha_p = rng.uniform(1.08, 1.18)
        beta_p  = rng.randint(10, 25)
        aug_list.append(("bp", _adjust_brightness(img, alpha_p, beta_p), labels))

        # 3. Brilho −15%
        alpha_m = rng.uniform(0.82, 0.92)
        beta_m  = rng.randint(-25, -10)
        aug_list.append(("bm", _adjust_brightness(img, alpha_m, beta_m), labels))

        # 4. Rotação +10°
        angle_p = rng.uniform(8.0, 12.0)
        aug_list.append(("r+", _rotate(img, angle_p), _labels_rotate(labels, angle_p)))

        # 5. Rotação −10°
        angle_m = rng.uniform(-12.0, -8.0)
        aug_list.append(("r-", _rotate(img, angle_m), _labels_rotate(labels, angle_m)))

        for tag, aug_img, aug_labels in aug_list[:augments_per_img]:
            stem = f"{img_path.stem}_aug_{tag}"
            _save(aug_img, aug_labels, img_dir, lbl_dir, stem)
            saved += 1

        icon = "🌩️" if labels else "☀️"
        print(f"  {icon} {img_path.stem} → +{min(augments_per_img, len(aug_list))} aug (total parcial: {saved})")

    _write_yaml(DST_DATASET)

    # Copia também o test split (imagem de referência)
    test_src = SRC_DATASET / "images" / "test"
    if test_src.exists():
        test_dst = DST_DATASET / "images" / "test"
        test_dst.mkdir(parents=True, exist_ok=True)
        for f in test_src.glob("*"):
            shutil.copy2(f, test_dst / f.name)

    print(f"\n{'='*60}")
    print(f"  ✅ Dataset expandido: {saved} imagens")
    print(f"  Destino: {DST_DATASET}")
    print(f"  Próximo passo:")
    print(f"    make train-yolo")
    print(f"{'='*60}\n")
    return saved


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Augmenta dataset YOLO de tempestades (NASA IR C13)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--target", type=int, default=300,
                        help="Número mínimo de imagens no dataset expandido")
    args = parser.parse_args()
    raise SystemExit(0 if augment(target=args.target) >= args.target else 1)
