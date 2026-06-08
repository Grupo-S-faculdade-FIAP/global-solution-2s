# Cursor Rules — Global Solutions (FIAP GS 2026.1)

Indice das rules do projeto. Fonte espelhada em `CLAUDE.md` e `.github/copilot-instructions.md`.

| Rule | Arquivo | Escopo (`globs`) | `alwaysApply` |
| --- | --- | --- | --- |
| Spec-Driven (TLC) | [tlc-spec-driven.mdc](tlc-spec-driven.mdc) | `**/*` | sim |
| Organizacao de documentos | [document-organization.mdc](document-organization.mdc) | `**/*.md` | nao |
| Dados & ML Python | [data-ml-python.mdc](data-ml-python.mdc) | `**/*.py`, `**/*.ipynb` | nao |
| Clean Architecture & SOLID | [clean-architecture-solid.mdc](clean-architecture-solid.mdc) | `src/app/**/*.py` | nao |

## Quando cada rule carrega

- **Sempre:** `tlc-spec-driven` — fluxo SPECIFY → DESIGN → TASKS → EXECUTE, STATE.md, commits.
- **Markdown:** `document-organization` — destino de docs, indices, PT-BR, sem inventar metricas.
- **Python/ML:** `data-ml-python` — pandas/sklearn/LightGBM/DEAP, versionamento de modelos; **carve-out YOLO G1** (conf=0.55, `storm70-l-tiled`) congelado.
- **Backend FastAPI:** `clean-architecture-solid` — domain/application/infrastructure, ports & adapters, `container.py`.

## Skills complementares

Ver [`.cursor/skills/README.md`](../skills/README.md).
