#!/usr/bin/env bash
# =============================================================================
# RODAR_STACK_70.sh  —  Pipeline YOLOv5 completo para cruzar mAP@0.5 >= 0.70
# Storm detector (objeto pequeno, satélite NASA). Tudo em YOLOv5 + complementos.
#
# Como rodar (no ambiente com GPU — RunPod/Vast 4090/5090):
#     cd global-solutions
#     bash RODAR_STACK_70.sh
#
# Pré-requisitos: dataset em data/model-dataset/ com as LABELS JÁ LIMPAS
# (lado >= 10px). Se ainda não limpou, este script limpa no passo 1.
# =============================================================================
set -euo pipefail

cd "$(dirname "$0")"
META=0.70
IMG=1280
DEV=0

echo "==========================================================="
echo " STACK >70%  |  $(date '+%F %H:%M')  |  device=$DEV"
echo "==========================================================="

# --- 0. Setup --------------------------------------------------------------
PIP="pip install -q --break-system-packages"
if [ ! -f yolov5/train.py ]; then
  git clone --depth 1 https://github.com/ultralytics/yolov5 yolov5
fi
$PIP -r yolov5/requirements.txt
$PIP albumentations ensemble-boxes sahi 2>/dev/null || true
python -c "import torch;assert torch.cuda.is_available();print('GPU:',torch.cuda.get_device_name(0))"

# data.yaml com caminho absoluto deste ambiente
python - <<'PY'
from pathlib import Path
r=Path('data/model-dataset').resolve()
Path('data/model-dataset/storm.v4.yaml').write_text(
 f"path: {r}\ntrain: images/train\nval: images/val\nnc: 1\nnames:\n  0: storm\n")
print("storm.v4.yaml OK ->", r)
PY

# --- 1. Limpeza de labels (idempotente: remove lado <10px) ------------------
echo "--- [1] Limpando labels (lado >= 10px) ---"
python - <<'PY'
import glob
from pathlib import Path
IMG=640; THR=10; b=a=0
for sp in ['train','val']:
    for f in glob.glob(f'data/model-dataset/labels/{sp}/*.txt'):
        L=[l for l in open(f).read().splitlines() if l.strip()]
        K=[l for l in L if min(float(l.split()[3]),float(l.split()[4]))*IMG>=THR]
        b+=len(L); a+=len(K)
        Path(f).write_text("\n".join(K)+("\n" if K else ""))
print(f"labels: antes={b} depois={a} removidos={b-a} ({(b-a)/max(b,1)*100:.0f}%)")
PY

# --- 2. Tiling SAHI (gera data/model-dataset-tiled/) ------------------------
echo "--- [2] Gerando dataset fatiado (tiles 320 / overlap 0.2) ---"
python scripts/goes_pipeline/08_tile_dataset.py --tile 320 --overlap 0.2
TILED_YAML="data/model-dataset-tiled/storm.tiled.yaml"

# helper: extrai mAP@0.5 do results.csv de um run
read_map () { python - "$1" <<'PY'
import sys,csv
rows=list(csv.DictReader(open(sys.argv[1])))
g=lambda r,k:[float(r[c]) for c in r if k in c][0]
print(f"{max(g(r,'metrics/mAP_0.5') for r in rows):.4f}")
PY
}
ok () { python -c "import sys;sys.exit(0 if float('$1')>=$META else 1)"; }

# --- 3. Treino principal: yolov5l @ tiles (maior alavanca) ------------------
echo "--- [3] Treino yolov5l nos tiles ---"
python yolov5/train.py --weights yolov5l.pt \
  --data "$TILED_YAML" --hyp data/model-dataset/hyp.smallobj.yaml \
  --img 640 --batch 16 --epochs 200 --cos-lr --patience 60 \
  --multi-scale --name storm70-l-tiled --device $DEV

BEST="runs/train/storm70-l-tiled/weights/best.pt"
MAP=$(read_map runs/train/storm70-l-tiled/results.csv)
echo ">> mAP@0.5 (treino tiles) = $MAP"

# --- 4. Validação com TTA (de graça, +1-3 mAP) ------------------------------
echo "--- [4] Validação com TTA ---"
python yolov5/val.py --weights "$BEST" --data "$TILED_YAML" \
  --img 640 --augment --task val --name storm70-tta

# --- 5. Se faltar: ensemble (l-tiled + P6 + P2) -----------------------------
if ok "$MAP"; then
  echo "✅ META ATINGIDA no passo 3 (mAP=$MAP). Pulando ensemble."
else
  echo "--- [5] Abaixo de $META (mAP=$MAP). Treinando modelos extras p/ ensemble ---"
  # P6 nativo 1280
  python yolov5/train.py --weights yolov5l6.pt \
    --data "$TILED_YAML" --hyp data/model-dataset/hyp.smallobj.yaml \
    --img 640 --batch 8 --epochs 200 --cos-lr --patience 60 \
    --name storm70-l6-tiled --device $DEV
  # cabeça P2 (stride 4)
  python yolov5/train.py --cfg yolov5/models/hub/yolov5-p2.yaml --weights '' \
    --data "$TILED_YAML" --hyp data/model-dataset/hyp.smallobj.yaml \
    --img 640 --batch 8 --epochs 200 --cos-lr --patience 60 \
    --name storm70-p2-tiled --device $DEV

  echo "--- [5b] Ensemble nativo YOLOv5 (vários --weights) + TTA ---"
  python yolov5/val.py \
    --weights runs/train/storm70-l-tiled/weights/best.pt \
              runs/train/storm70-l6-tiled/weights/best.pt \
              runs/train/storm70-p2-tiled/weights/best.pt \
    --data "$TILED_YAML" --img 640 --augment --task val --name storm70-ensemble
fi

# --- 6. Consolidar ----------------------------------------------------------
echo "--- [6] Consolidando melhor peso ---"
BESTPT=$(ls -t runs/train/storm70-*/weights/best.pt | head -1)
cp "$BESTPT" src/models/weights/best.pt
echo "best.pt publicado -> src/models/weights/best.pt  (de $BESTPT)"
echo "Curvas/relatórios em: runs/train/storm70-*/  e  runs/val/storm70-*/"
echo "==========================================================="
echo " FIM. Verifique o mAP@0.5 final nos logs acima."
echo "==========================================================="
