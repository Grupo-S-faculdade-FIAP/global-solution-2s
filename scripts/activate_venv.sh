#!/usr/bin/env bash
# Ativa o venv do projeto (.venv na raiz ou src/.venv legado).
# Uso: source scripts/activate_venv.sh

activate_project_venv() {
  local root="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
  if [ -f "${root}/.venv/bin/activate" ]; then
    # shellcheck source=/dev/null
    source "${root}/.venv/bin/activate"
    echo "✓ venv (.venv) ativado"
    return 0
  fi
  if [ -f "${root}/src/.venv/bin/activate" ]; then
    # shellcheck source=/dev/null
    source "${root}/src/.venv/bin/activate"
    echo "✓ venv (src/.venv) ativado"
    return 0
  fi
  echo "⚠ Nenhum venv encontrado — usando python3 do sistema"
  return 1
}

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  activate_project_venv "$(cd "$(dirname "$0")/.." && pwd)"
fi
