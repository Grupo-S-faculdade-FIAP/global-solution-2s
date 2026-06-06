# State — Persistent Memory

**Project:** GS2 — global-solution-2s
**Last updated:** 2026-06-06 (limpeza repo + docs refresh)

> Este arquivo é a memória persistente do agente entre sessões.
> Sempre carregar no início de cada sessão.
> Atualizar antes de pausar ou encerrar a sessão.

---

## Current Focus

**Active feature:** gs-closure (entrega FIAP — PDF + vídeo)
**Last task completed:** SNS no dashboard — inscrição e-mail + simular alerta publica no tópico (`.specs/features/sns-dashboard/spec.md`)
**Next task:** B0 prazo FIAP → B3 nome → B1 vídeo (Enzo) + B2 PDF (equipe); B7 screenshots opcional
**Blockers:** nenhum
**RPI (status formal):** [docs/RPI.md](../../docs/RPI.md) — v1.7 (2026-06-06)

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
| 2026-06-04 | D-015 | CI/CD via GitHub Actions + OIDC (sem access keys) | Credenciais temporárias; least privilege; deploy auto na main | Lambda gs2-api |
| 2026-06-05 | D-016 | Clean Architecture enxuta: Domain → Application → Infrastructure → Interfaces | Testabilidade; troca mock↔DynamoDB via container.py; sem over-engineering | Toda a API |
| 2026-06-05 | D-017 | BFF shim strategy invertida: dashboard/ é canonical, interfaces/http/bff/ re-exporta | Preserva backward compat com testes que patcham dashboard.bff_backend._fastapi_test_client | BFF |
| 2026-06-05 | D-018 | DetectStormUseCase em application/cv/ — routers/cv.py não importa boto3/torch | Separação clara HTTP vs pipeline; testável sem FastAPI | CV |
| 2026-06-05 | D-019 | Pipeline labels YOLO v2: letterbox 640 + detecção na img de treino + UI mask + audit gate | 74/76 labels eram bbox fantasma (canto sup. esq.); precision alta / recall baixo era artefato posicional | CV / dataset |
| 2026-06-05 | D-020 | Frontend dashboard: ES modules + partials Jinja + CSS tokens | Manutenibilidade; `app.js` entry; `core/` api/state/dom/ui; `maps/`; `sections/` | Dashboard |
| 2026-06-05 | D-021 | `.env` canônico na raiz do repo | `config.py` carrega raiz primeiro; `src/.env.example` é legado | Config / docs |
| 2026-06-05 | D-022 | ML risco v2: regressão contínua + AG nos limiares (não no ensemble) | Score varia por região; `agri_risk_thresholds.json` commitado; CI usa `--skip-ga` | ML / G2 |
| 2026-06-05 | D-023 | Regressor default sklearn HGB; LightGBM só com `AGRI_USE_LIGHTGBM=1` | Evita segfault torch+lightgbm no macOS em pytest/demo | ML |
| 2026-06-05 | D-024 | YOLO lazy load + `RISK_SKIP_YOLO=1` em pytest | BFF e RiskAssessment não carregam torch na importação | CV / testes |
| 2026-06-05 | D-025 | CV geo-aware: alertas 200 km + peso dinâmico no ensemble | Risco muda por localização; sem cobertura satélite → peso CV=0 | Risco / YOLO |
| 2026-06-05 | D-026 | Dashboard: calculadora usa `/api/risk/forecast` (ensemble + breakdown) | Uma narrativa na UI (`ml.js` + `#risk-badge`) | Frontend |

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
- 2026-06-04 — Retreino NASA com `--limiar 200 --area 600` (pipeline v1, **corrompido**): 266 bboxes, 74/76 com bbox fantasma `0.079687 0.176852…`, mAP@0.5 ≈ 0.546, precision ~0.89, recall ~0.42 — modelo aprendeu artefato de UI, não nuvens.
- 2026-06-05 — Pipeline v2 (`scripts/goes_pipeline/label_utils.py`): letterbox 640, detecção na img de treino, máscara UI, `--limiar 185 --area 80`. Dataset: 93 img, 34 com storm, 76 bboxes, 0 ghost, audit PASSED.
- 2026-06-05 — Retreino v2.0 (76 bboxes): P≈0.003, R≈0.688, mAP@0.5≈0.078 — labels honestos, dataset esparsо.
- 2026-06-05 — Dataset v2.1 (limiar 175 / area 50): 285 bboxes, 64 img com storm, 0 ghost. Retreino `storm-detector-v2`: P≈0.27, R≈0.17, mAP@0.5≈0.14 — mAP quase dobrou; ainda abaixo G1 (70%).
- 2026-06-04 — DynamoDB mock: `DYNAMODB_USE_MOCK=true` (default) → `data/demo/storm_alerts.json`; `POST /alerts/simulate`; gráficos e `/storms/recent` usam o mesmo store.
- 2026-06-04 — Dashboard: `DEMO_MODE=true` (default) mantém fallbacks de gráficos; `false` exige FastAPI e oculta botões de dev. Localização em `localStorage` (`dashboard-location`).
- 2026-06-04 — Dashboard: seção **Mapa da região** (Leaflet CDN) consome `/api/map/overlay` com bbox da localização; Windy permanece como **Radar meteorológico**.
- 2026-06-04 — Dois servidores (5000+8000) confundiam usuários e `make demo` falhava se :8000 ocupada (só Flask, BFF quebrado). Solução: `WSGIMiddleware` monta Flask em `/` após rotas FastAPI; URL única `http://127.0.0.1:8000`. Causa KPIs "—": abrir :8000 sem UI ou JS abortado antes do `bootstrapDashboard` (listeners em sliders nulos).
- 2026-06-05 — Location-bar: flex-wrap quebrava alinhamento do mapinha; migrado para CSS Grid + header com badge. Auto-apply no mapa (debounce), toast, nav por âncoras, três mapas renomeados. Refinamento: sticky dinâmico compacto, nav scroll horizontal mobile, Leaflet zoom bottom-right, badge clicável para expandir.
- 2026-06-05 — Gaps técnicos resolvidos: IoT store + router implementados (DynamoDB/mock), confiança YOLO real salva nos alertas, firmware movido para `src/iot/firmware.cpp` apontando para API GS2, seção IoT no dashboard (card leituras + histórico), BFF `/api/iot/*`, 11 testes IoT em `tests/test_iot_readings.py`.
- 2026-06-05 — Arquitetura limpa aplicada em 4 fases: Ports, Adapters, DetectStormUseCase, S3TriggerHandler, container.py, interfaces/http/bff/. Suite atual: **259 testes** (`make test`) + **53 E2E** + cobertura **82%**.
- 2026-06-05 — Documentação desatualizada (Streamlit, IoT stub, CI manual, 84 testes) corrigida em auditoria única; fonte canônica de env: `.env.example` na raiz.
- 2026-06-06 — Limpeza repo: removidos `simular_treino.py`, `treinar_modelo.py`, `setup_and_train.command`, `iot_esp32`, `src/.env.example`, scripts WIP 01–04; guia YOLO consolidado em `docs/YOLO-RETREINO.md`; teste `test_map_overlay_filters_bbox` corrigido (timestamps dinâmicos).
- 2026-06-06 — Limpeza rodada 2: `capture_satellite_data.py` (Windy), `src/Makefile`, `test_api.command`, target `make train-ml`; `build_dataset_agri.command` → `make test-api`.

---

## Deferred Ideas

- ~~Alertas em tempo real por push/email quando YOLO detectar tempestade~~ — SNS e-mail no dashboard (jun/2026); push mobile fora de escopo
- Cobertura de outros países da América do Sul
- App mobile para visualização no campo
- YOLO mAP ≥ 70% (G1) — retreino offline `make train-yolo --recall-focus`; integração geo já no ensemble

---

## Todos

- [ ] Verificar prazo exato de entrega na plataforma FIAP
- [x] Clonar template TIAO-2026
- [x] Criar estrutura de pastas do repositório conforme template
- [x] Criar scaffold FastAPI base (src/)
- [x] Instalar dependências e rodar testes base (`make test` — 259 passed)
- [x] Especificar feature: Data Integration Dashboard
- [x] Implementar T-01 a T-12 (MVP integrado — ver ROADMAP)
- [x] Especificar e implementar módulo IoT (ESP32 + sensores)
- [x] Auditoria e atualização de documentação (specs, README, RPI, codebase docs)
- [x] Limpeza de arquivos desnecessários + docs refresh (06/06)
- [ ] B0: Verificar prazo exato na plataforma FIAP
- [ ] B3: Definir nome do produto (D-001)
- [ ] B1: Vídeo ≤ 5 min — Enzo (`tasks.md`)
- [ ] B2: PDF FIAP — usar `docs/PDF-ENTREGA-ESQUELETO.md`
- [ ] B5–B6: Link vídeo no README + revisão final
- [ ] BEY-05: Merge → `main` + smoke AWS (`make smoke-aws`)

---

## Preferences

- Idioma de trabalho: Português (BR)
- Commits: Conventional Commits em inglês
- `.env` canônico: copiar `.env.example` na **raiz** do repo (não `src/.env.example`)

---

<!-- Archive resolved blockers to HISTORY below if this file grows too long. -->
