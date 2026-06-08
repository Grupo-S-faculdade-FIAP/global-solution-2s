#!/usr/bin/env bash
# =============================================================================
# runbook_train.sh — Executa o docs/RUNBOOK-YOLO-70.md passo a passo
#
# Mudança crítica vs rodadas anteriores:
#   --img 1280  (era 640 — MAIOR alavanca para objetos pequenos)
#   yolov5m     (era yolov5l — começar menor, subir se necessário)
#   area=400    (era 150 — remove specks <12px que nunca atingem IoU≥0.5)
#   hyp.smallobj.yaml (era hyp.v3.yaml — calibrado para tiny objects)
#
# Uso:
#   bash scripts/runbook_train.sh
#   bash scripts/runbook_train.sh --skip-download   # se imagens já baixadas
# =============================================================================

set -euo pipefail

WORKDIR="/workspace/global-solutions"
LOG="/workspace/runbook_train.log"
SKIP_DOWNLOAD=false
# YOLOv5 grava em ROOT/runs/ (ROOT=yolov5/) quando --project não é passado
RUNS_TRAIN="yolov5/runs/train"
RUNS_VAL="yolov5/runs/val"

for arg in "$@"; do
  case $arg in --skip-download) SKIP_DOWNLOAD=true ;; esac
done

log()    { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }
banner() { echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n  $*\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"; }

cd "$WORKDIR"

# ── 0. Setup ──────────────────────────────────────────────────────────────────
banner "[0/5] Setup e sanidade"

# Deps de sistema
apt-get update -qq && apt-get install -y -qq git libgl1 libglib2.0-0 2>/dev/null
log "✔ Sistema OK"

# Deps Python
PIP="pip install -q --break-system-packages"
$PIP opencv-python-headless requests numpy tqdm pandas ultralytics gitpython
log "✔ Python deps OK"

# Git pull
git pull 2>&1 | tail -1 | tee -a "$LOG"
log "✔ Repo atualizado"

# Confirmar GPU
python3 -c "import torch; print('CUDA:', torch.cuda.is_available(), torch.cuda.get_device_name(0))" | tee -a "$LOG"

# Garantir YOLOv5 clonado
if [ ! -f "yolov5/train.py" ]; then
  log "Clonando YOLOv5..."
  git clone --depth 1 https://github.com/ultralytics/yolov5 yolov5 2>&1 | tail -2 | tee -a "$LOG"
fi
$PIP -r yolov5/requirements.txt 2>/dev/null || true
log "✔ YOLOv5 OK"

# ── 1. Download dataset (se não existir) ──────────────────────────────────────
if [ "$SKIP_DOWNLOAD" = "false" ]; then
  banner "[1/5] Download NASA GIBS (180 dias × 9 regiões × 3 horários)"
  python scripts/goes_pipeline/00_download_gibs.py \
    --limpar --dias 180 --workers 20 2>&1 | tee -a "$LOG"
  log "✔ Download OK"
else
  NIMGS=$(find data/nasa_captures -name '*.png' 2>/dev/null | wc -l)
  log "⏭  Download pulado — $NIMGS imagens em data/nasa_captures/"
fi

# ── 2. Regenerar labels (area=400, limiar=168) ────────────────────────────────
banner "[2/5] Labels limpas (area=400px², limiar=168)"
log "Regenerando labels em data/model-dataset/ ..."
python scripts/goes_pipeline/04_nasa_to_yolo.py \
  --clean --limiar 168 --area 400 2>&1 | tee -a "$LOG"

# Diagnóstico de tamanhos de bbox
python3 - <<'PY' | tee -a "$LOG"
import glob, statistics as st
IMG=640; s=[]
for sp in ['train','val']:
    for f in glob.glob(f'data/model-dataset/labels/{sp}/*.txt'):
        for l in open(f).read().splitlines():
            if l.strip():
                p=l.split(); s.append(min(float(p[3]),float(p[4]))*IMG)
if not s:
    print("AVISO: nenhuma bbox encontrada!")
else:
    s.sort(); n=len(s)
    print(f"Boxes: {n} | mediana lado px: {s[n//2]:.1f} | <12px: {round(sum(x<12 for x in s)/n*100,1)}%")
PY

log "✔ Labels OK"

# ── 3. Gerar storm.v4.yaml com paths absolutos ────────────────────────────────
banner "[3/5] Gerando storm.v4.yaml"
python3 - <<'PY' | tee -a "$LOG"
from pathlib import Path
root = Path('data/model-dataset').resolve()
n_train = len(list((root/'images'/'train').glob('*.png'))) if (root/'images'/'train').exists() else 0
n_val   = len(list((root/'images'/'val').glob('*.png')))   if (root/'images'/'val').exists() else 0
y = f"""path: {root}
train: images/train
val:   images/val
nc: 1
names:
  0: storm
"""
Path('data/model-dataset/storm.v4.yaml').write_text(y)
print(f"storm.v4.yaml → path: {root}")
print(f"  train: {n_train} imagens | val: {n_val} imagens")
PY
log "✔ storm.v4.yaml gerado"

# ── 4. Treino principal — yolov5m @ 1280 ─────────────────────────────────────
banner "[4/5] Treino yolov5m @ img=1280 (RUNBOOK Passo 3)"
log "Iniciando às $(date '+%H:%M')..."
log "ETA: ~1.5-2h (RTX 5090)  |  Acompanhe: tmux attach -t train"

python yolov5/train.py \
  --weights yolov5m.pt \
  --data    data/model-dataset/storm.v4.yaml \
  --hyp     data/model-dataset/hyp.smallobj.yaml \
  --img 1280 --batch 16 --epochs 200 --cos-lr --patience 60 \
  --name storm-v4-m-1280 --device 0 \
  --exist-ok 2>&1 | tee -a "$LOG"

# ── 5. Resultado ──────────────────────────────────────────────────────────────
banner "[5/5] Resultado"
BEST=$(ls -t "$RUNS_TRAIN"/storm-v4-m-1280/weights/best.pt 2>/dev/null | head -1 || true)

if [ -n "$BEST" ] && [ -f "$BEST" ]; then
  SIZE=$(du -sh "$BEST" | cut -f1)
  log "✅ best.pt: $BEST ($SIZE)"

  # Validação final canônica
  log "Rodando validação final..."
  python yolov5/val.py --weights "$BEST" \
    --data data/model-dataset/storm.v4.yaml \
    --img 1280 --task val --name final_val 2>&1 | tee -a "$LOG"

  # Publicar
  mkdir -p src/models/weights
  cp "$BEST" src/models/weights/best.pt
  log "✅ best.pt publicado em src/models/weights/best.pt"

  log ""
  log "Para baixar no Mac:"
  log "  scp -P 52397 root@157.157.221.30:$WORKDIR/src/models/weights/best.pt ~/Downloads/best.pt"
else
  log "⚠️  best.pt não encontrado — verifique erros acima"
fi

echo "DONE" >> "$LOG"
