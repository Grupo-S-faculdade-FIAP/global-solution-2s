#!/usr/bin/env bash
# =============================================================================
# runpod_train.sh — Pipeline completo de treino YOLOv5l na instância RunPod
#
# Uso (dentro da instância, como root):
#   bash runpod_train.sh
#   bash runpod_train.sh --model yolov5m --epochs 100  # opcional
#
# Acompanhar ao vivo (do Mac):
#   ssh runpod "tmux attach -t train"
#
# Requisitos da instância:
#   - PyTorch >= 2.0 com CUDA  (ex: pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime)
#   - GPU >= 16GB VRAM (RTX 3090 / 4090 recomendado)
#   - ~20 GB de disco livre
# =============================================================================

set -euo pipefail

MODEL="${MODEL:-yolov5l}"
EPOCHS="${EPOCHS:-300}"
BATCH="${BATCH:-32}"
PATIENCE="${PATIENCE:-150}"
REPO="https://github.com/Grupo-S-faculdade-FIAP/global-solution-2s.git"
WORKDIR="/workspace/global-solutions"
LOG="/workspace/train.log"

# ── Flags opcionais via argumento ─────────────────────────────────────────────
for arg in "$@"; do
  case $arg in
    --model=*)    MODEL="${arg#*=}" ;;
    --epochs=*)   EPOCHS="${arg#*=}" ;;
    --batch=*)    BATCH="${arg#*=}" ;;
  esac
done

# Função de log com timestamp
log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }
banner() {
  echo "" | tee -a "$LOG"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"
  echo "  $*" | tee -a "$LOG"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"
}

banner "GS2 — RunPod Training Pipeline  |  $(date '+%Y-%m-%d %H:%M')"
log "Modelo: $MODEL  |  Épocas: $EPOCHS  |  Batch: $BATCH  |  Patience: $PATIENCE"
log "Repo  : $REPO"
log "Log   : $LOG"

# ── 1. Dependências de sistema ─────────────────────────────────────────────
banner "[1/6] Dependências de sistema"
apt-get update -qq && apt-get install -y -qq git curl libgl1 libglib2.0-0 pv
log "✔ Sistema OK"

# ── 2. Clone do repositório ────────────────────────────────────────────────
banner "[2/6] Clonando repositório"
if [ -d "$WORKDIR" ]; then
  log "Diretório já existe — git pull..."
  cd "$WORKDIR" && git pull | tee -a "$LOG"
else
  git clone "$REPO" "$WORKDIR" | tee -a "$LOG"
  cd "$WORKDIR"
fi
cd "$WORKDIR"
log "✔ Repo OK  ($(git log -1 --format='%h %s'))"

# ── 3. Dependências Python ─────────────────────────────────────────────────
banner "[3/6] Instalando dependências Python"
PIP="pip install -q --break-system-packages"
$PIP opencv-python-headless requests numpy tqdm pandas ultralytics
$PIP fastapi uvicorn pydantic pydantic-settings boto3 httpx scikit-learn joblib || true
log "✔ Python deps OK"

# ── 4. Download do dataset NASA GIBS ──────────────────────────────────────
banner "[4/6] Construindo dataset"
log "→ Download NASA GIBS (180 dias × 9 regiões × 3 horários)..."
python scripts/goes_pipeline/00_download_gibs.py \
  --limpar --dias 180 --workers 20 2>&1 | tee -a "$LOG"

log "→ Convertendo para labels YOLO (v3.1: limiar 168, area 150px²)..."
python scripts/goes_pipeline/04_nasa_to_yolo.py \
  --clean --limiar 168 --area 150 2>&1 | tee -a "$LOG"

log "→ Augmentando dataset (target=500)..."
python scripts/goes_pipeline/07_augment_dataset.py --target 500 2>&1 | tee -a "$LOG"

NIMGS=$(find data/ -name "*.jpg" -o -name "*.png" 2>/dev/null | wc -l)
log "✔ Dataset pronto — $NIMGS imagens encontradas"

# ── 5. Treino YOLOv5 ──────────────────────────────────────────────────────
banner "[5/6] Treino YOLOv5 — $MODEL  (CUDA device 0)"
log "Iniciando treino às $(date '+%H:%M')..."
log "ETA estimado: ~3-5 h (RTX 4090, 300 épocas)  |  Acompanhe: ssh runpod \"tmux attach -t train\""

python src/yolo_training.py \
  --model    "$MODEL"     \
  --epochs   "$EPOCHS"    \
  --batch    "$BATCH"     \
  --device   0            \
  --patience "$PATIENCE"  \
  --recall-focus          \
  --cos-lr                \
  --validate 2>&1 | tee -a "$LOG"

# ── 6. Resultado ──────────────────────────────────────────────────────────
banner "[6/6] Pipeline concluído  —  $(date '+%Y-%m-%d %H:%M')"
BEST="$WORKDIR/src/models/weights/best.pt"

if [ -f "$BEST" ]; then
  SIZE=$(du -sh "$BEST" | cut -f1)
  log "✅ best.pt salvo: $BEST  ($SIZE)"
  log ""
  log "Para baixar no Mac:"
  log "  scp -P 17989 root@213.173.107.78:$BEST ~/Downloads/best.pt"
else
  log "⚠️  best.pt não encontrado — verifique erros acima"
fi
