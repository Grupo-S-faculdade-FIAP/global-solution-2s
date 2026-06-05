#!/bin/bash
# build_dataset_agri.command
# Duplo clique: baixa INMET BDMEP, exporta FAOSTAT e retreina AgriRiskModel
set -e
cd "$(dirname "$0")"
ROOT="$(pwd)"

echo ""
echo "================================================"
echo "  Global Solutions — Pipeline Agrícola"
echo "================================================"
echo ""
echo "Etapas:"
echo "  1. INMET BDMEP (estações SP, RJ, DF, POA, Belém)"
echo "  2. FAOSTAT Brasil (contexto para PDF)"
echo "  3. Treino AgriRiskModel → models/"
echo ""

# shellcheck source=scripts/activate_venv.sh
source scripts/activate_venv.sh
activate_project_venv "$ROOT" || true

echo ""
echo "🚀 Iniciando pipeline (INMET pode levar alguns minutos)..."
echo ""

python3 scripts/build_agri_pipeline.py --years 2024

echo ""
echo "================================================"
echo "  Pipeline agrícola concluído!"
echo "  Modelos: models/agri_risk_*.pkl"
echo "  FAOSTAT: docs/dados/FAOSTAT_BR_contexto.md"
echo "  Próximo: make demo  ou  test_api.command"
echo "================================================"
echo ""
read -p "Pressione Enter para fechar..."
