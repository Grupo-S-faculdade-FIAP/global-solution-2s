#!/bin/bash
# setup_and_train.command
# Configura TODO o projeto global-solutions e treina os modelos
# Duplo clique para executar

set -e
cd "$(dirname "$0")"
ROOT="$(pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✓ $1${NC}"; }
warn() { echo -e "${YELLOW}  ⚠ $1${NC}"; }
info() { echo -e "${BLUE}  → $1${NC}"; }
fail() { echo -e "${RED}  ✗ $1${NC}"; }

echo ""
echo "================================================"
echo "  Global Solutions — Setup & Train"
echo "================================================"
echo ""

# ── 1. Python ──────────────────────────────────────────────────────────────
info "Verificando Python..."
PY=$(python3 --version 2>&1)
ok "$PY"

# ── 2. Venv ────────────────────────────────────────────────────────────────
info "Configurando ambiente virtual..."
if [ ! -f "src/.venv/bin/activate" ]; then
    python3 -m venv src/.venv
    ok "venv criado"
fi
source src/.venv/bin/activate
ok "venv ativado"

# ── 3. Dependências ────────────────────────────────────────────────────────
echo ""
info "Instalando dependências (pode levar alguns minutos)..."
pip install -q --upgrade pip

pip install -q \
    fastapi==0.115.5 \
    "uvicorn[standard]==0.32.1" \
    pydantic==2.10.3 \
    pydantic-settings==2.6.1 \
    python-multipart==0.0.12 \
    boto3==1.35.74 \
    mangum==0.19.0 \
    "torch>=2.2.0" \
    "torchvision>=0.17.0" \
    opencv-python-headless \
    Pillow \
    scikit-learn==1.5.2 \
    pandas==2.2.3 \
    "numpy>=1.26.4" \
    joblib==1.4.2 \
    httpx==0.28.0 \
    requests==2.32.3 \
    flask==3.1.1 \
    playwright==1.49.0 \
    pytest==8.3.3 \
    pytest-asyncio==0.24.0 \
    scipy

ok "Dependências instaladas"

# Instala Chromium para Playwright
info "Instalando Chromium (Playwright)..."
python3 -m playwright install chromium 2>/dev/null
ok "Chromium instalado"

# ── 4. .env local ─────────────────────────────────────────────────────────
echo ""
info "Configurando .env local..."
if [ ! -f ".env" ]; then
cat > .env << 'ENVEOF'
PROJECT_NAME=Global Solutions
ENVIRONMENT=development
DEBUG=True

# AWS (deixe em branco para rodar localmente sem AWS)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
S3_BUCKET_IMAGES=
S3_BUCKET_MODELS=

# DynamoDB (não usado localmente)
DYNAMODB_WEATHER_TABLE=weather_metrics
DYNAMODB_STORM_TABLE=storm_detections
DYNAMODB_TABLE_ALERTS=storm_alerts

# YOLO
YOLO_MODEL_S3_KEY=models/yolov5s-storm-best.pt
YOLO_CONFIDENCE_THRESHOLD=0.25

# NASA
NASA_CAPTURE_ENABLED=True
NASA_CAPTURES_DIR=data/nasa_captures
NASA_HISTORICO_DIAS=30
ENVEOF
    ok ".env criado com defaults locais"
else
    ok ".env já existe — mantido"
fi

# ── 5. Pipeline agrícola (INMET + FAOSTAT + ML) ───────────────────────────
echo ""
info "Pipeline agrícola (INMET BDMEP + FAOSTAT + AgriRiskModel)..."
if [ -f "data/weather/inmet/training_cache.csv" ]; then
    ok "Cache INMET já existe — retreino sem novo download"
    python3 scripts/build_agri_pipeline.py --skip-fetch
else
    warn "Cache INMET ausente — baixando BDMEP 2024 (pode levar alguns minutos)"
    python3 scripts/build_agri_pipeline.py --years 2024
fi
ok "AgriRiskModel treinado → models/agri_risk_*.pkl"

# ── 6. Dataset NASA ────────────────────────────────────────────────────────
echo ""
echo "================================================"
echo "  Dataset NASA Worldview"
echo "================================================"

NASA_COUNT=$(ls data/nasa_captures/*.png 2>/dev/null | wc -l | tr -d ' ')
if [ "$NASA_COUNT" -gt 10 ]; then
    ok "Dataset NASA já existe ($NASA_COUNT imagens) — pulando download"
else
    warn "Nenhuma imagem NASA encontrada"
    info "Baixando 30 dias de histórico NASA Worldview..."
    info "(isso pode levar 20-40 minutos)"
    echo ""
    cd src
    python3 app/cron/capture_nasa_data.py --historico --dias 30
    cd "$ROOT"
fi

# ── 7. Converter NASA → YOLO ──────────────────────────────────────────────
NASA_COUNT=$(ls data/nasa_captures/*.png 2>/dev/null | wc -l | tr -d ' ')
if [ "$NASA_COUNT" -gt 0 ]; then
    echo ""
    info "Convertendo $NASA_COUNT imagens NASA para formato YOLO..."
    python3 scripts/goes_pipeline/04_nasa_to_yolo.py
    ok "Dataset YOLO atualizado"
else
    warn "Sem imagens NASA — usando apenas dataset existente"
fi

# ── 8. Verificar dataset ───────────────────────────────────────────────────
echo ""
info "Verificando dataset..."
TRAIN=$(ls data/model-dataset/images/train/*.png 2>/dev/null | wc -l | tr -d ' ')
VAL=$(ls data/model-dataset/images/val/*.png 2>/dev/null | wc -l | tr -d ' ')
ok "Train: $TRAIN imagens | Val: $VAL imagens"

if [ "$TRAIN" -lt 5 ]; then
    fail "Dataset muito pequeno ($TRAIN imagens). Execute build_dataset_nasa.command primeiro."
    read -p "Pressione Enter para sair..."
    exit 1
fi

# ── 9. Treinar YOLO ────────────────────────────────────────────────────────
echo ""
echo "================================================"
echo "  Treinando YOLOv5 — Storm Detector"
echo "================================================"
echo ""
info "Dataset: $TRAIN train + $VAL val imagens"
info "Épocas:  50 | Batch: 8 | Device: CPU"
echo ""

python3 src/yolo_training.py --epochs 50 --batch 8 --device cpu

ok "Modelo YOLO treinado → src/models/weights/best.pt"

# ── 10. Smoke test ─────────────────────────────────────────────────────────
echo ""
echo "================================================"
echo "  Smoke test dos serviços"
echo "================================================"
echo ""

cd src
python3 - << 'PYEOF'
import sys
sys.path.insert(0, '.')

print("Testando AgriRiskModel...")
from app.services.agri_risk_model import AgriRiskModel
m = AgriRiskModel()
casos = [
    ("Dia seco SP",        28.5, 60,  0,   10),
    ("Chuva moderada",     30.0, 85,  8,   30),
    ("Tempestade severa",  34.0, 95, 35,   80),
]
for nome, t, u, p, v in casos:
    r = m.predict_detalhado(t, u, p, v)
    print(f"  {nome:<22} → {r['classe']:6}  score={r['score']:.3f}")

print("\nTestando StormDetector...")
from pathlib import Path
model_path = Path("models/weights/best.pt")
if model_path.exists():
    from app.services.storm_detector import StormDetector
    det = StormDetector(str(model_path), confidence_threshold=0.25)
    test_img = Path("../data/model-dataset/images/test/test-storm.png")
    if test_img.exists():
        result = det.predict(str(test_img))
        print(f"  test-storm.png → {result.num_detections} detecções | conf={result.average_confidence:.3f}")
    else:
        print("  (imagem de teste não encontrada — pulando)")
else:
    print("  (modelo YOLO não encontrado — rode o treinamento acima)")
PYEOF
cd "$ROOT"

# ── 11. Resumo final ───────────────────────────────────────────────────────
echo ""
echo "================================================"
echo "  Setup completo!"
echo "================================================"
echo ""
echo "  Modelos treinados:"
ls -lh src/models/weights/best.pt 2>/dev/null && echo "    ✓ YOLO best.pt" || echo "    ✗ YOLO (falhou)"
ls -lh models/agri_risk_model.pkl 2>/dev/null && echo "    ✓ AgriRiskModel.pkl" || echo "    ✗ AgriRisk (falhou)"
echo ""
echo "  Para iniciar a API:"
echo "    cd src && uvicorn app.main:app --port 8000 --reload"
echo ""
echo "  Docs: http://localhost:8000/docs"
echo "================================================"
echo ""
read -p "Pressione Enter para fechar..."
