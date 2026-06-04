# State — Persistent Memory

**Project:** —
**Last updated:** 2026-06-01 (estrutura de repositório ajustada conforme template TIAO-2026)

> Este arquivo é a memória persistente do agente entre sessões.
> Sempre carregar no início de cada sessão.
> Atualizar antes de pausar ou encerrar a sessão.

---

## Current Focus

**Active feature:** gs-closure
**Last task completed:** ✅ Fases 1–2 spec + dashboard + `/storms/recent` + `/map/overlay` (2026-06-04)
**Next task:** Fase 3 — smoke AWS + deploy best.pt na Lambda; Fase 4 — vídeo/README
**Blockers:** nenhum

---

## Decisions

| Date | ID | Decision | Rationale | Impact |
|------|----|----------|-----------|--------|
| 2026-06-01 | D-001 | Nome do projeto: sem nome definido | Pendente de definição | Nome nos READMEs e PDF |
| 2026-06-01 | D-002 | Arquitetura: FastAPI + AWS Lambda + API Gateway | Cobre disciplina Cloud/AWS; serverless reduz custo; free tier suficiente para POC | Backend inteiro |
| 2026-06-01 | D-003 | Windy API como widget no frontend (não REST) | Plano free do Windy não libera REST API completa; widget free cobre visualização no mapa | Frontend / dashboard |
| 2026-06-01 | D-004 | YOLOv5 (PyTorch Hub) para detecção de tempestades/nuvens chuvosas | Compatível com Lambda atual; boa documentação; dataset de nuvens do Windy.com | Módulo CV |
| 2026-06-01 | D-005 | Dataset de imagens: screenshots do Windy.com (nuvens chuvosas) | Gratuito; cobre o Brasil; upload manual para S3 dispara o pipeline via trigger | Módulo CV + ML |
| 2026-06-01 | D-006 | Estrutura base: FastAPI com routers por módulo (cv, ml, iot, dashboard) | Separação de responsabilidades; facilita divisão de trabalho entre integrantes | Toda a API |
| 2026-06-01 | D-007 | Config via pydantic-settings + .env | Sem segredos hardcodados; segue boas práticas de segurança | Toda a API |
| 2026-06-02 | D-008 | Open-Meteo API (100% free, sem API key) | Não requer autenticação; cobertura global; open-source | Data Ingestion |
| 2026-06-02 | D-009 | DynamoDB com 3 tabelas (time-series otimizada) | Serverless; TTL automático; queries rápidas por timestamp | Database |
| 2026-06-02 | D-010 | Lambda para YOLO (vs SageMaker) | Custo menor; modelo v8s ~25MB; reutiliza código FastAPI | CV Pipeline |
| 2026-06-02 | D-011 | Correlação ML simples (não deep learning) | Reduz complexidade; mais interpretável para MVP | ML Module |
| 2026-06-02 | D-012 | Windy API widget (não REST) | Free tier + widget interativo; widget é suficiente | Dashboard |
| 2026-06-02 | D-013 | T-11/T-12 revisadas para usar Flask dashboard existente | Reutilizar codebase; não recriar do zero | Frontend |
| 2026-06-02 | D-014 | Centralizar variáveis de ambiente em .env (pydantic-settings) | Sem hardcoding; fácil deployment; team-friendly | Toda a API |

---

## Blockers

| ID | Description | Status | Resolution |
|----|-------------|--------|------------|
| — | Nenhum blocker ativo | — | — |

---

## Lessons Learned

- 2026-06-01 — Projeto inicializado com spec-driven. Manter cada módulo com seu próprio `spec.md` para facilitar divisão entre integrantes.
- 2026-06-04 — Os docs de `.specs/codebase/` estavam como template genérico; manter mapeamento real evita decisões baseadas em suposição.
- 2026-06-04 — Treino YOLO: usar só NASA por ora; screenshots Windy antigos fora do dataset; futuras capturas Windy podem entrar depois com rótulo revisado.
- 2026-06-04 — Retreino NASA com `--limiar 200 --area 600`: 266 bboxes, mAP@0.5 ≈ 0.546 (época 46), precision ~0.89, recall ~0.42. Modelo em `src/models/weights/best.pt`.
- 2026-06-04 — DynamoDB mock: `DYNAMODB_USE_MOCK=true` (default) → `data/demo/storm_alerts.json`; `POST /alerts/simulate`; gráficos e `/storms/recent` usam o mesmo store.

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
- [x] Especificar feature: Data Integration Dashboard (YOLO + Open-Meteo + Dashboard)
- [ ] **NEXT:** Implementar T-01 a T-03 (Setup DynamoDB, S3, FastAPI)
- [ ] **NEXT:** Implementar T-04 a T-05 (YOLO inference pipeline)
- [ ] **NEXT:** Implementar T-06 a T-07 (Weather ingestion)
- [ ] **NEXT:** Implementar T-08 (ML risk prediction)
- [ ] **NEXT:** Implementar T-09 a T-10 (API endpoints)
- [ ] **NEXT:** Implementar T-11 a T-12 (Dashboard + deployment)
- [ ] Especificar feature: módulo IoT (ESP32 + sensores) — se tempo permitir

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
