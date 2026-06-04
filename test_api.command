#!/bin/bash
# test_api.command — Sobe a API e testa os endpoints principais
cd "$(dirname "$0")"

echo ""
echo "================================================"
echo "  Global Solutions — Teste de Endpoints"
echo "================================================"

# Ativa venv
if [ -f "src/.venv/bin/activate" ]; then
    source src/.venv/bin/activate
fi

# Instala dependências faltantes
cd src
pip install -q scikit-learn fastapi uvicorn pydantic pydantic-settings httpx mangum 2>/dev/null
cd ..

echo ""
echo "🚀 Subindo API em background (porta 8000)..."
cd src
uvicorn app.main:app --port 8000 --host 127.0.0.1 &
API_PID=$!
cd ..

# Aguarda API iniciar
echo "   Aguardando API iniciar..."
sleep 6

echo ""
echo "================================================"
echo "  Testando endpoints"
echo "================================================"
echo ""

BASE="http://127.0.0.1:8000"

run() {
    local desc="$1"
    local url="$2"
    echo "▸ $desc"
    echo "  $url"
    curl -s "$url" | python3 -m json.tool 2>/dev/null | head -20
    echo ""
}

run "Health check" \
    "$BASE/health"

run "Status CV" \
    "$BASE/cv/status"

run "Status ML" \
    "$BASE/ml/status"

run "Risco agrícola — dia seco SP (deve ser LOW)" \
    "$BASE/ml/predict/agricultural-risk?temperatura=28.5&umidade=60&precipitacao=0&vento_kmh=10"

run "Risco agrícola — chuva forte (deve ser MEDIUM)" \
    "$BASE/ml/predict/agricultural-risk?temperatura=30&umidade=92&precipitacao=15&vento_kmh=45"

run "Risco agrícola — tempestade severa (deve ser HIGH)" \
    "$BASE/ml/predict/agricultural-risk?temperatura=34&umidade=95&precipitacao=35&vento_kmh=80"

run "Risk forecast — São Paulo" \
    "$BASE/risk/forecast?lat=-23.55&lon=-46.63"

run "Weather current — São Paulo" \
    "$BASE/weather/current?lat=-23.55&lon=-46.63"

run "Informações do modelo ML" \
    "$BASE/ml/model/info"

echo "================================================"
echo "  Testes concluídos!"
echo "  API rodando em: $BASE"
echo "  Docs:           $BASE/docs"
echo "================================================"
echo ""
echo "Pressione Enter para encerrar a API..."
read
kill $API_PID 2>/dev/null
echo "API encerrada."
