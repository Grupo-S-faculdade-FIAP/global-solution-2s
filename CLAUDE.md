# Global Solutions — Claude Code

Plataforma de inteligência ambiental e agrícola (FIAP GS 2026.1): satélite, YOLO, ML de risco agrícola, dashboard com Windy, IoT ESP32 e backend FastAPI na AWS.

---

## Metodologia — mesma do Cursor

**Fonte canônica:** leia e siga **sempre** `.cursor/rules/tlc-spec-driven.mdc`.

Esse arquivo define o fluxo Spec-Driven (SPECIFY → DESIGN → TASKS → EXECUTE), auto-sizing de escopo, estrutura `.specs/`, princípios de código e frases-gatilho. O time usa as mesmas regras no Cursor; não invente um fluxo paralelo.

Espelho equivalente (GitHub Copilot): `.github/copilot-instructions.md`

---

## Início de sessão

1. Ler `.cursor/rules/tlc-spec-driven.mdc`
2. Ler `.specs/project/STATE.md` — foco atual, blockers, decisões
3. Ler `.specs/project/PROJECT.md` — visão, stack, escopo MVP
4. Se continuar uma feature: ler `spec.md`, `design.md`, `tasks.md` em `.specs/features/[slug]/`

## Fim de sessão

1. Atualizar `.specs/project/STATE.md`
2. Marcar tarefas concluídas em `tasks.md` (se existir)
3. Commitar apenas se o usuário pedir explicitamente

---

## Stack e layout

| Área | Caminho |
|------|---------|
| API FastAPI | `src/app/` |
| Dashboard | `src/dashboard/` |
| Testes | `tests/` |
| Docs | `docs/` (ex.: `RPI.md`, `DEPLOY-LAMBDA.md`) |
| Demo / dados | `data/demo/` |
| Specs | `.specs/` |

**Core:** Python 3.11, FastAPI, YOLOv5, scikit-learn, AWS (Lambda, S3, API Gateway, DynamoDB), Streamlit/HTML dashboard, ESP32.

Documentação de codebase (quando existir): `.specs/codebase/`

---

## Comandos

```bash
# Dependências
make install

# API + dashboard em http://127.0.0.1:8000 (requer best.pt em src/models/weights/)
make demo

# Testes
make test-api
make test-storms
```

Venv esperado: `.venv/` na raiz do repo.

---

## Regras duras

- **Não commitar** sem pedido explícito do usuário
- **Sem secrets** no código — usar `.env` (ver `.env.example`)
- **Não assumir nem inventar** — verificar no código/docs antes de afirmar
- **Escopo mínimo** — tocar só arquivos necessários à tarefa
- Melhorias fora de escopo → registrar em `.specs/project/STATE.md` (deferred ideas)
- Commits: Conventional Commits (`feat`, `fix`, `refactor`, …)

---

## Verificação de conhecimento

```
Código → docs do projeto (.specs/, README, docs/) → docs oficiais → web → declarar incerteza
```

Nunca fabricar APIs, endpoints ou comportamento não confirmado no repositório.
