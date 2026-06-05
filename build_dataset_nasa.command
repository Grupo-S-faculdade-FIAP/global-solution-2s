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
echo "Destino: data/nasa_captures/"
echo ""

# Ativa venv se existir
if [ -f "src/.venv/bin/activate" ]; then
    source src/.venv/bin/activate
    echo "✓ venv ativado"
fi

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

python3 src/app/cron/capture_nasa_data.py --historico --dias 60

echo ""
echo "================================================"
echo "  Download concluído! Convertendo para YOLO..."
echo "================================================"
echo ""

# --clean: reconstrói train/val só com NASA (ignora screenshots Windy antigos)
python3 scripts/goes_pipeline/04_nasa_to_yolo.py --clean

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
