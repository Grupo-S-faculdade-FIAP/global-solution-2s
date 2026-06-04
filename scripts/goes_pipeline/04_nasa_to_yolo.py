"""
GOES Pipeline — Etapa 4: Converter imagens NASA Worldview para formato YOLO
===========================================================================
Lê os screenshots PNG do NASA Worldview (data/nasa_captures/) e gera
labels .txt automáticos detectando regiões de convecção profunda.

No NASA Worldview GOES-East IR C13:
  - Pixels brancos/muito claros = nuvem com topo muito frio = tempestade
  - Pixels cinza médio = nuvem baixa/média
  - Pixels escuros = céu limpo / superfície quente

O detector identifica manchas brancas brilhantes e gera bboxes YOLO.

Execute a partir do root do projeto (global-solutions/):
    python scripts/goes_pipeline/04_nasa_to_yolo.py
    python scripts/goes_pipeline/04_nasa_to_yolo.py --limiar 210 --area 300
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NASA_DIR     = PROJECT_ROOT / "data" / "nasa_captures"
IMG_TRAIN    = PROJECT_ROOT / "data" / "model-dataset" / "images" / "train"
IMG_VAL      = PROJECT_ROOT / "data" / "model-dataset" / "images" / "val"
LBL_TRAIN    = PROJECT_ROOT / "data" / "model-dataset" / "labels" / "train"
LBL_VAL      = PROJECT_ROOT / "data" / "model-dataset" / "labels" / "val"

for d in [IMG_TRAIN, IMG_VAL, LBL_TRAIN, LBL_VAL]:
    d.mkdir(parents=True, exist_ok=True)

# Limiar de brilho: pixels acima disso são considerados topo frio (storm)
# NASA IR C13: branco brilhante (>210/255) = nuvem convectiva
DEFAULT_LIMIAR  = 210
DEFAULT_AREA_PX = 400   # área mínima em pixels para gerar bbox


def detectar_storms_nasa(img_bgr: np.ndarray, limiar: int, area_min: int) -> list[dict]:
    """
    Detecta regiões de storm em screenshot do NASA Worldview.

    Estratégia:
      1. Converte para grayscale
      2. Mascara pixels muito brilhantes (> limiar) — topos frios
      3. Remove ruído com morfologia
      4. Rotula regiões conectadas e gera bboxes YOLO normalizadas

    Returns:
        Lista de dicts com x_c, y_c, w, h (0-1)
    """
    H, W = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Máscara: pixels muito brancos = topo de nuvem convectiva frio
    _, mascara = cv2.threshold(gray, limiar, 255, cv2.THRESH_BINARY)

    # Remove ruído pequeno com erosão/dilatação
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN,  kernel, iterations=2)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel, iterations=3)

    # Rotula regiões conectadas
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mascara, connectivity=8)

    bboxes = []
    for i in range(1, n_labels):  # 0 = background
        area = stats[i, cv2.CC_STAT_AREA]
        if area < area_min:
            continue

        x0 = stats[i, cv2.CC_STAT_LEFT]
        y0 = stats[i, cv2.CC_STAT_TOP]
        bw = stats[i, cv2.CC_STAT_WIDTH]
        bh = stats[i, cv2.CC_STAT_HEIGHT]

        # Normaliza para YOLO
        x_c = (x0 + bw / 2) / W
        y_c = (y0 + bh / 2) / H
        w_n = bw / W
        h_n = bh / H

        # Descarta bboxes que cobrem quase a imagem toda (artefatos de UI)
        if w_n > 0.90 or h_n > 0.90:
            continue

        bboxes.append({"x_c": x_c, "y_c": y_c, "w": w_n, "h": h_n, "area": area})

    return bboxes


def processar_imagem(png_path: Path, split: str, limiar: int, area_min: int) -> dict:
    """Converte um PNG NASA para imagem 640×640 + label YOLO."""
    img_dir = IMG_TRAIN if split == "train" else IMG_VAL
    lbl_dir = LBL_TRAIN if split == "train" else LBL_VAL

    stem     = png_path.stem
    dst_png  = img_dir / f"{stem}.png"
    dst_lbl  = lbl_dir / f"{stem}.txt"

    img = cv2.imread(str(png_path))
    if img is None:
        return {"arquivo": png_path.name, "status": "erro", "erro": "Não conseguiu ler imagem"}

    # Redimensiona para padrão YOLOv5 (640×640)
    img_640 = cv2.resize(img, (640, 640), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(dst_png), img_640)

    # Detecta storms na imagem original (resolução maior = mais preciso)
    bboxes = detectar_storms_nasa(img, limiar, area_min)

    with open(dst_lbl, "w") as f:
        for bb in bboxes:
            f.write(f"0 {bb['x_c']:.6f} {bb['y_c']:.6f} {bb['w']:.6f} {bb['h']:.6f}\n")

    return {
        "arquivo":  png_path.name,
        "split":    split,
        "n_bboxes": len(bboxes),
        "status":   "ok",
    }


def main(limiar: int = DEFAULT_LIMIAR, area_min: int = DEFAULT_AREA_PX,
         train_frac: float = 0.85):

    arquivos = sorted(NASA_DIR.glob("*.png"))

    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum .png em {NASA_DIR}\n"
            "Rode build_dataset_nasa.command primeiro para baixar as imagens."
        )

    np.random.seed(42)
    idx_train = set(np.random.choice(
        len(arquivos),
        size=max(1, int(len(arquivos) * train_frac)),
        replace=False,
    ))

    print(f"Convertendo {len(arquivos)} imagens NASA → YOLO")
    print(f"  Limiar brilho: > {limiar}/255 = storm")
    print(f"  Área mínima  : {area_min} px")
    print(f"  Split        : {train_frac:.0%} train / {1-train_frac:.0%} val\n")

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

    print(f"\n{'='*55}")
    print(f"  Total imagens   : {len(resultados)}")
    print(f"  Com storm       : {n_storm}")
    print(f"  Sem storm (neg) : {n_clear}")
    print(f"  Total bboxes    : {total_boxes}")
    print(f"\n  Train: {IMG_TRAIN}")
    print(f"  Val  : {IMG_VAL}")
    print("\n✓ Pronto → rode src/yolo_training.py para retreinar o modelo")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Converte screenshots NASA Worldview para dataset YOLO",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--limiar",  type=int,   default=DEFAULT_LIMIAR,
                        help="Limiar de brilho (0-255) para detectar storm")
    parser.add_argument("--area",    type=int,   default=DEFAULT_AREA_PX,
                        help="Área mínima (px²) para gerar bbox")
    parser.add_argument("--split",   type=float, default=0.85,
                        help="Fração para treino (0-1)")
    args = parser.parse_args()
    main(limiar=args.limiar, area_min=args.area, train_frac=args.split)
