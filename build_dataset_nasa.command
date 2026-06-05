#!/bin/bash
# build_dataset_nasa.command
# Duplo clique para baixar 60 dias de imagens NASA Worldview para o dataset
cd "$(dirname "$0")"

echo ""
echo "================================================"
echo "  Global Solutions — NASA Dataset Builder"
echo "================================================"
echo ""
echo "Vai baixar imagens do NASA Worldview (GOES-East IR C13)"
echo "Regiões: Américas, Brasil, Sudeste BR"
echo "Período: últimos 60 dias (~180 imagens)"
echo "Destino S3: s3://\$S3_BUCKET_IMAGES/nasa-satellite/ (canônico)"
echo "Cache local: data/nasa_captures/ (NASA_KEEP_LOCAL=true durante treino)"
echo ""

# shellcheck source=scripts/activate_venv.sh
source scripts/activate_venv.sh
activate_project_venv "$(pwd)" || true

# Instala playwright se necessário
python3 -c "import playwright" 2>/dev/null || {
    echo "📦 Instalando playwright..."
    pip3 install playwright
}

# Instala Chromium headless se necessário
python3 -m playwright install chromium 2>/dev/null
echo "✓ Chromium OK"
echo ""
echo "🚀 Iniciando download histórico (pode levar 30-60 min)..."
echo ""

# Mantém cópias locais só para o pipeline YOLO abaixo
export NASA_KEEP_LOCAL=true
python3 src/app/cron/capture_nasa_data.py --historico --dias 60

echo ""
echo "================================================"
echo "  Download concluído! Convertendo para YOLO..."
echo "================================================"
echo ""

# --clean: reconstrói train/val só com NASA (pipeline v2: letterbox + UI mask)
python3 scripts/goes_pipeline/04_nasa_to_yolo.py --clean --limiar 175 --area 50

echo ""
echo "Revisão visual dos labels..."
python3 scripts/goes_pipeline/05_review_nasa_labels.py
python3 scripts/goes_pipeline/06_audit_labels.py --strict

echo ""
echo "================================================"
echo "  Dataset NASA pronto em data/model-dataset/"
echo "  Próximo passo: python3 src/yolo_training.py --epochs 50 --batch 8"
echo "================================================"
echo ""

echo ""
echo "================================================"
echo "  Pipeline completo!"
echo "  Modelo salvo em: src/models/weights/best.pt"
echo "================================================"
echo ""
read -p "Pressione Enter para fechar..."
