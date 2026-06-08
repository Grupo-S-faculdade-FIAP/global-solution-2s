"""
GOES Pipeline — Etapa 8: Tiling (SAHI-style) do dataset para objeto pequeno
============================================================================
Fatia cada imagem 640x640 em tiles sobrepostos e remapeia as labels YOLO.
Treinar nos tiles faz o objeto pequeno ficar GRANDE em relação ao tile —
a técnica de maior impacto para detecção de objeto pequeno em satélite.

Saída: data/model-dataset-tiled/{images,labels}/{train,val}

Uso:
    python scripts/goes_pipeline/08_tile_dataset.py --tile 320 --overlap 0.2
    # depois treine apontando para o storm.tiled.yaml gerado, com --img 640
    # (tile 320 -> upscale 2x no treino = objeto ~4x maior que no original 640)

Na INFERÊNCIA use SAHI (pip install sahi) com slice_height=slice_width=320,
overlap=0.2 e fundo das predições por NMS/Greedy — ver Seção 7 de docs/RUNBOOK-YOLO-70.md.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import cv2

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "model-dataset"
DST = ROOT / "data" / "model-dataset-tiled"


def yolo_to_xyxy(line, W, H):
    c, xc, yc, w, h = line.split()
    xc, yc, w, h = float(xc) * W, float(yc) * H, float(w) * W, float(h) * H
    return c, xc - w / 2, yc - h / 2, xc + w / 2, yc + h / 2


def tile_split(split, tile, overlap, min_visi):
    src_img = SRC / "images" / split
    src_lbl = SRC / "labels" / split
    di = DST / "images" / split
    dl = DST / "labels" / split
    di.mkdir(parents=True, exist_ok=True)
    dl.mkdir(parents=True, exist_ok=True)

    step = int(tile * (1 - overlap))
    n_img = n_box = 0
    for ip in sorted(src_img.glob("*.png")):
        img = cv2.imread(str(ip))
        if img is None:
            continue
        H, W = img.shape[:2]
        lp = src_lbl / f"{ip.stem}.txt"
        boxes = []
        if lp.exists():
            for l in lp.read_text().splitlines():
                if l.strip():
                    boxes.append(yolo_to_xyxy(l, W, H))

        ys = list(range(0, max(1, H - tile + 1), step)) or [0]
        xs = list(range(0, max(1, W - tile + 1), step)) or [0]
        if ys[-1] != H - tile:
            ys.append(max(0, H - tile))
        if xs[-1] != W - tile:
            xs.append(max(0, W - tile))

        for ty in ys:
            for tx in xs:
                tile_boxes = []
                for c, x0, y0, x1, y1 in boxes:
                    ix0, iy0 = max(x0, tx), max(y0, ty)
                    ix1, iy1 = min(x1, tx + tile), min(y1, ty + tile)
                    iw, ih = ix1 - ix0, iy1 - iy0
                    if iw <= 0 or ih <= 0:
                        continue
                    area_box = (x1 - x0) * (y1 - y0)
                    if area_box <= 0 or (iw * ih) / area_box < min_visi:
                        continue  # caixa cortada demais pela borda do tile
                    cx = (ix0 + ix1) / 2 - tx
                    cy = (iy0 + iy1) / 2 - ty
                    tile_boxes.append(f"{c} {cx/tile:.6f} {cy/tile:.6f} {iw/tile:.6f} {ih/tile:.6f}")
                # só salva tile com pelo menos 1 caixa (evita explodir negativos)
                if not tile_boxes:
                    continue
                crop = img[ty:ty + tile, tx:tx + tile]
                name = f"{ip.stem}_t{tx}_{ty}"
                cv2.imwrite(str(di / f"{name}.png"), crop)
                (dl / f"{name}.txt").write_text("\n".join(tile_boxes) + "\n")
                n_img += 1
                n_box += len(tile_boxes)
    print(f"[{split}] tiles={n_img} boxes={n_box}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tile", type=int, default=320)
    ap.add_argument("--overlap", type=float, default=0.2)
    ap.add_argument("--min-visi", type=float, default=0.3,
                    help="fração mínima da caixa visível no tile para mantê-la")
    a = ap.parse_args()
    for split in ["train", "val"]:
        tile_split(split, a.tile, a.overlap, a.min_visi)

    root = DST.resolve()
    (DST / "storm.tiled.yaml").write_text(
        f"path: {root}\ntrain: images/train\nval: images/val\nnc: 1\nnames:\n  0: storm\n")
    print(f"\nOK -> {DST}\nyaml -> {DST/'storm.tiled.yaml'}")


if __name__ == "__main__":
    main()
