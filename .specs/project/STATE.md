# State — Persistent Memory

**Project:** —
**Last updated:** 2026-06-01 (estrutura de repositório ajustada conforme template TIAO-2026)

> Este arquivo é a memória persistente do agente entre sessões.
> Sempre carregar no início de cada sessão.
> Atualizar antes de pausar ou encerrar a sessão.

---

## Current Focus

**Active feature:** estrutura base do projeto
**Last task completed:** scaffold FastAPI criado (main.py, routers, config, requirements, Makefile, tests)
**Next task:** instalar dependências e rodar os testes base; depois especificar feature Computer Vision (YOLO)
**Blockers:** nenhum

---

## Decisions

| Date | ID | Decision | Rationale | Impact |
|------|----|----------|-----------|--------|
| 2026-06-01 | D-001 | Nome do projeto: sem nome definido | Pendente de definição | Nome nos READMEs e PDF |
| 2026-06-01 | D-002 | Arquitetura: FastAPI + AWS Lambda + API Gateway | Cobre disciplina Cloud/AWS; serverless reduz custo; free tier suficiente para POC | Backend inteiro |
| 2026-06-01 | D-003 | Windy API como widget no frontend (não REST) | Plano free do Windy não libera REST API completa; widget free cobre visualização no mapa | Frontend / dashboard |
| 2026-06-01 | D-004 | YOLOv8 (Ultralytics) para detecção de tempestades/nuvens chuvosas | Estado da arte para detecção de objetos; boa documentação; dataset de nuvens do Windy.com | Módulo CV |
| 2026-06-01 | D-005 | Dataset de imagens: screenshots do Windy.com (nuvens chuvosas) | Gratuito; cobre o Brasil; upload manual para S3 dispara o pipeline via trigger | Módulo CV + ML |
| 2026-06-01 | D-006 | Estrutura base: FastAPI com routers por módulo (cv, ml, iot, dashboard) | Separação de responsabilidades; facilita divisão de trabalho entre integrantes | Toda a API |
| 2026-06-01 | D-007 | Config via pydantic-settings + .env | Sem segredos hardcodados; segue boas práticas de segurança | Toda a API |

---

## Blockers

| ID | Description | Status | Resolution |
|----|-------------|--------|------------|
| — | Nenhum blocker ativo | — | — |

---

## Lessons Learned

- 2026-06-01 — Projeto inicializado com spec-driven. Manter cada módulo com seu próprio `spec.md` para facilitar divisão entre integrantes.

---

## Deferred Ideas

- Alertas em tempo real por push/email quando YOLO detectar tempestade
- Cobertura de outros países da América do Sul
- App mobile para visualização no campo

---

## Todos

- [ ] Verificar prazo exato de entrega na plataforma FIAP
- [x] Clonar template TIAO-2026: https://github.com/CaiqueFiap-2026/TEMPLATE-TIAO-2026
- [x] Criar estrutura de pastas do repositório conforme template (README.md, docs/, data/, assets/, Ir Além/)
- [x] Criar scaffold FastAPI base (src/)
- [ ] Instalar dependências e rodar testes base
- [ ] Especificar feature: módulo Computer Vision (YOLO + detecção de tempestades)
- [ ] Especificar feature: módulo Machine Learning (previsão agrícola)
- [ ] Especificar feature: módulo Cloud/Backend (FastAPI + AWS)
- [ ] Especificar feature: módulo Frontend/Dashboard (Windy API + visualizações)
- [ ] Especificar feature: módulo IoT (ESP32 + sensores)

---

## Preferences

- Idioma de trabalho: Português (BR)
- Commits: Conventional Commits em inglês

Good ideas captured during implementation that are out of current scope.

- [YYYY-MM-DD] — [Idea: description] → Candidate for [v2 / backlog / investigate]

---

## Todos

Short-term tasks that don't belong to a specific feature spec.

- [ ] [Todo item]
- [ ] [Todo item]

---

## Preferences

Agent behavior preferences noted during sessions (to avoid repeating tips).

- [YYYY-MM-DD] — [Preference noted]

---

<!-- This file GROWS over time. Archive old resolved blockers to a HISTORY section at the bottom if it gets too long. -->
