# State — Persistent Memory

**Project:** GS2 — global-solution-2s
**Last updated:** 2026-06-09 (SNS geo-targeted alerts)

> Este arquivo é a memória persistente do agente entre sessões.
> Sempre carregar no início de cada sessão.
> Atualizar antes de pausar ou encerrar a sessão.

---

## Current Focus

**Active feature:** gs-closure (entrega FIAP — PDF)
**Last task completed:** B1 vídeo (Enzo) + B5 link no README — https://www.youtube.com/watch?v=W67760WVado
**Next task:** B0 prazo FIAP → B3 nome → B2 PDF (equipe); B7 screenshots opcional
**Blockers:** nenhum
**Branch status:** `chore/dataset-gitignore-yolo-stack` — commit `afbf61c` pushed (`refactor: apply cursor rules practices (non-yolo)`)
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
| 2026-06-08 | D-027 | YOLO ponto operacional conf=0,55 (P=73,5%, R=30,2%, mAP@0.5=50,4% val) | Sweep val tiled; conf=0,55 equilibra P/R para demo; sem limiar numérico na rubrica FIAP | CV / inferência |
| 2026-06-08 | D-028 | Pesos canônicos: `storm70-l-tiled` (YOLOv5l) em `src/models/weights/best.pt` | mAP@0.5=56,5% (TTA 57,1%); treinos l6/p2 cancelados (Option A) | CV / deploy |
| 2026-06-08 | D-029 | Rules/skills Cursor versionadas em `.cursor/` com índices README | 4 rules + 3 skills; carve-out YOLO G1 em `data-ml-python.mdc`; refs em CLAUDE.md e copilot-instructions | Agentes / docs |
| 2026-06-08 | D-030 | Rótulos proxy documentados (ML + YOLO) | Alvos circulares — R²/mAP medem consistência interna, não validação externa; transparência no PDF §2.4.5 | PDF B2, RPI §8.2 |
| 2026-06-09 | D-031 | SNS rate limit + cooldown regional em DynamoDB (`sns_rate_limits`) | JSON local não persiste em Lambda; PK `EMAIL#…#DAY#…` e `REGION#…`; cooldown 60 min por região NASA | SNS / Lambda |
| 2026-06-09 | D-032 | SNS alertas geo-targeted (raio 200 km) | Inscrição salva lat/lon do dashboard; publish filtra por `SNS_ALERT_RADIUS_KM`; legados sem coords não recebem (re-inscrição) | SNS / dashboard |

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
- 2026-06-05 — Dataset v2.1 (limiar 175 / area 50): 285 bboxes, 64 img com storm, 0 ghost. Retreino `storm-detector-v2`: P≈0.27, R≈0.17, mAP@0.5≈0.14 — baseline antes do retreino GPU tiled.
- 2026-06-08 — Retreino GPU RunPod `storm70-l-tiled` (YOLOv5l, dataset tiled): mAP@0.5=0.565 (TTA 0.571). Sweep conf: 0.25→P=54.2%; 0.40→66.3%; **0.55→73.5%**; 0.70→84.6%; 0.85→90.9%. Conf operacional 0.55. Treinos l6/p2 cancelados (Option A). `best.pt` SCP local (~89 MB).
- 2026-06-04 — DynamoDB mock: `DYNAMODB_USE_MOCK=true` (default) → `data/demo/storm_alerts.json`; `POST /alerts/simulate`; gráficos e `/storms/recent` usam o mesmo store.
- 2026-06-04 — Dashboard: `DEMO_MODE=true` (default) mantém fallbacks de gráficos; `false` exige FastAPI e oculta botões de dev. Localização em `localStorage` (`dashboard-location`).
- 2026-06-04 — Dashboard: seção **Mapa da região** (Leaflet CDN) consome `/api/map/overlay` com bbox da localização; Windy permanece como **Radar meteorológico**.
- 2026-06-04 — Dois servidores (5000+8000) confundiam usuários e `make demo` falhava se :8000 ocupada (só Flask, BFF quebrado). Solução: `WSGIMiddleware` monta Flask em `/` após rotas FastAPI; URL única `http://127.0.0.1:8000`. Causa KPIs "—": abrir :8000 sem UI ou JS abortado antes do `bootstrapDashboard` (listeners em sliders nulos).
- 2026-06-05 — Location-bar: flex-wrap quebrava alinhamento do mapinha; migrado para CSS Grid + header com badge. Auto-apply no mapa (debounce), toast, nav por âncoras, três mapas renomeados. Refinamento: sticky dinâmico compacto, nav scroll horizontal mobile, Leaflet zoom bottom-right, badge clicável para expandir.
- 2026-06-05 — Gaps técnicos resolvidos: IoT store + router implementados (DynamoDB/mock), confiança YOLO real salva nos alertas, firmware movido para `src/iot/firmware.cpp` apontando para API GS2, seção IoT no dashboard (card leituras + histórico), BFF `/api/iot/*`, 11 testes IoT em `tests/test_iot_readings.py`.
- 2026-06-05 — Arquitetura limpa aplicada em 4 fases: Ports, Adapters, DetectStormUseCase, S3TriggerHandler, container.py, interfaces/http/bff/. Suite atual: **440 testes** (`make test`) + **53 E2E** + cobertura **~82%**.
- 2026-06-05 — Documentação desatualizada (Streamlit, IoT stub, CI manual, 84 testes) corrigida em auditoria única; fonte canônica de env: `.env.example` na raiz.
- 2026-06-06 — Limpeza repo: removidos `simular_treino.py`, `treinar_modelo.py`, `setup_and_train.command`, `iot_esp32`, `src/.env.example`, scripts WIP 01–04; guia YOLO consolidado em `docs/YOLO-RETREINO.md`; teste `test_map_overlay_filters_bbox` corrigido (timestamps dinâmicos).
- 2026-06-06 — Limpeza rodada 2: `capture_satellite_data.py` (Windy), `src/Makefile`, `test_api.command`, target `make train-ml`; `build_dataset_agri.command` → `make test-api`.
- 2026-06-06 — Limpeza rodada 3 (concluída): removidos 5 MDs “Critical Fixes” da raiz (artefatos de sessão; cobertura nos testes); `CORS_EXTRA_ORIGINS` e `XRAY_ENABLED` documentados em `.env.example`; mensagem corrigida em `build_dataset_nasa.command`; métricas atualizadas em `GUIA-DE-AVALIACAO.md`; `LIMPEZA_REPO.md` arquivado (plano executado); `.coverage` no `.gitignore`.
- 2026-06-06 — SNS dashboard implementado: inscrição e-mail via `/api/alerts/subscribe`, status via `/api/alerts/sns/status`, simular alerta publica no SNS; rate limit em `sns_rate_limit.py`; 16 testes SNS; `sections/sns.js` no dashboard.
- 2026-06-06 — Limpeza docs rodada 4 (concluída): removidos `IMPLEMENTACOES_2025_06_06.md`, `SNS_IMPLEMENTATION_SUMMARY.md`, `QUICK_START.md` (artefatos com referências a módulos fictícios); `INTEGRATIONS.md` atualizado com seção SNS e rate limit env vars; contagem de testes corrigida para **440** em todos os docs; 7 feature specs marcadas como Arquivadas; `ROADMAP.md` e `CHECKLIST_ENTREGA.md` atualizados.
- 2026-06-08 — Limpeza docs rodada 5: runbook/plano saíram da raiz; `data/training-dataset-1000/` e `data/model-dataset-tiled/` mantidos (augmentação/treino ativos); único `labels_backup_*` mantido; regra `.cursor/rules/document-organization.mdc` referenciada em `CLAUDE.md`.
- 2026-06-08 — Rollout rules/skills: commit de `clean-architecture-solid`, `data-ml-python`, skills `agri-risk-ml-workflow` e `clean-architecture-review`; índices `.cursor/rules/README.md` e `.cursor/skills/README.md`; carve-out YOLO G1 (conf=0.55, storm70-l-tiled) em `data-ml-python.mdc` — sem alterar pesos, config ou scripts de treino.
- 2026-06-08 — Auditoria rules (non-YOLO): AgriRiskModel/GA já usam `logging`; prints restantes são CLI (`capture_nasa_data`, `yolo_training`, `goes_pipeline`) — fora de paths de produção API; métricas 0,14/84/259 testes só em changelog histórico RPI (OK).
- 2026-06-08 — Rótulos proxy (ML + YOLO): alvos circulares documentados em RPI §8.2 e PDF §2.4.5; R²≈0,95 mede ajuste à regra, não predição externa; S3 `best.pt` 88,6 MiB confirmado; contagens dataset atualizadas (1.361 base → 3.045 tiled train).

---

## Deferred Ideas

- `detect_storm.py`: boto3 lazy em `_download_model_from_s3` (application) — extrair adapter S3 + port se refatorar CV
- `dashboard_alerts.py` `/metrics`: `__import__("boto3")` inline — extrair `CloudWatchMetricsAdapter` em `infrastructure/aws/`
- Scripts CLI NASA/YOLO (`capture_nasa_data.py`, `goes_pipeline/`): `print` aceitável para operador; migrar para `logging` só se unificar runbooks

- ~~Alertas em tempo real por push/email quando YOLO detectar tempestade~~ — SNS e-mail no dashboard (jun/2026); push mobile fora de escopo
- Cobertura de outros países da América do Sul
- App mobile para visualização no campo
- Retreino YOLO com mais capturas NASA e rótulos revisados (v2)
- ~~Republicar `best.pt` (~89 MB YOLOv5l) na Lambda S3~~ — confirmado 88,6 MiB em `s3://satellite-images-gs2/models/best.pt` (08/06/2026)

---

## Todos

- [ ] Verificar prazo exato de entrega na plataforma FIAP
- [x] Clonar template TIAO-2026
- [x] Criar estrutura de pastas do repositório conforme template
- [x] Criar scaffold FastAPI base (src/)
- [x] Instalar dependências e rodar testes base (`make test` — 440 passed)
- [x] Especificar feature: Data Integration Dashboard
- [x] Implementar T-01 a T-12 (MVP integrado — ver ROADMAP)
- [x] Especificar e implementar módulo IoT (ESP32 + sensores)
- [x] Auditoria e atualização de documentação (specs, README, RPI, codebase docs)
- [x] Limpeza de arquivos desnecessários + docs refresh (06/06)
- [x] Limpeza docs rodada 3 — Critical Fixes MDs, .env.example, build_dataset_nasa.command (06/06)
- [x] SNS no dashboard — inscrição e-mail, rate limit, 16 testes (06/06)
- [x] Limpeza docs rodada 4 — artefatos SNS, contagem 440 testes, features arquivadas (06/06)
- [x] Limpeza docs rodada 5 — runbook/plano, índices GPU, pastas vazias (08/06)
- [x] Aplicar práticas rules Cursor (non-YOLO): DI SNS DLQ, docs G1, STATE deferred (08/06)
- [x] Corrigir falhas pytest SNS alerts (`/alerts/metrics`, lowercase email, detector status) (08/06)
- [ ] B0: Verificar prazo exato na plataforma FIAP
- [ ] B3: Definir nome do produto (D-001)
- [x] B1: Vídeo ≤ 5 min — Enzo — https://www.youtube.com/watch?v=W67760WVado
- [ ] B2: PDF FIAP — usar `docs/PDF-ENTREGA-ESQUELETO.md`
- [x] B5–B6: Link vídeo no README + revisão final
- [ ] BEY-05: Merge → `main` + smoke AWS (`make smoke-aws`)

---

## Preferences

- Idioma de trabalho: Português (BR)
- Commits: Conventional Commits em inglês
- `.env` canônico: copiar `.env.example` na **raiz** do repo (não `src/.env.example`)

---

<!-- Archive resolved blockers to HISTORY below if this file grows too long. -->
