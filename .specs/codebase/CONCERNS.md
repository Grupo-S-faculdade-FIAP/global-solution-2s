# Concerns

**Project:** global-solution-2s
**Mapped on:** 2026-06-06

Este documento consolida riscos reais observados no estado atual do código.

---

## Fragile Areas

| Area | File(s) | Risk | Why fragile | Mitigation |
|------|---------|:----:|------------|------------|
| Pipeline S3 → YOLO → SNS/DynamoDB | `interfaces/events/s3_trigger.py`, `application/cv/detect_storm.py` | High | Fluxo event-driven; cold start pesado; smoke AWS manual | `make smoke-aws`; testes SNS mockados |
| Modelo YOLO — POC integrado | `src/models/weights/best.pt`, pipeline v2 | Low | mAP@0.5 56,5%; rótulos proxy | Mais capturas NASA; rótulos humanos (v2) |
| Modelo de risco agrícola + ensemble | `agri_risk_model.py`, `risk_assessment.py` | Medium | INMET/FAOSTAT; pesos CV dependem de alertas regionais | `make verify-agri-models`; `make build-agri-ci` |
| torch + LightGBM no macOS | `agri_risk_model.py` | Medium | Segfault em pytest se ambos carregados | Default sklearn HGB; `AGRI_USE_LIGHTGBM=1` só treino |
| Integração ingestão periódica | `lambdas/ingest_weather.py` | Medium | API externa + DynamoDB | Testes com mocks; retry em prod |
| Deploy serverless | `docs/DEPLOY-LAMBDA.md`, CI/CD | Low | CD automatizado na main; path filter pode pular dashboard | Documentar `MOUNT_DASHBOARD=false` na Lambda |

---

## Technical Debt

| ID | Description | Location | Impact | Priority | Status |
|----|-------------|---------|--------|----------|--------|
| TD-001 | Endpoints IoT retornavam stub | `routers/iot.py` | — | — | **Resolvido** (jun/2026) |
| TD-002 | `/storms/recent` e `/map/overlay` vazios | `routers/data_integration.py` | — | — | **Resolvido** — store mock + DynamoDB |
| TD-003 | Testes weather dependem de internet | `tests/test_weather_service.py` | Flakiness offline | Medium | Aberto |
| TD-004 | Falta teste E2E S3 trigger real | AWS pipeline | Regressão silenciosa | High | Aberto — smoke manual |
| TD-005 | CI/CD inexistente | raiz | — | — | **Resolvido** — GitHub Actions OIDC |
| TD-006 | BFF shim duplicado (dashboard/ + interfaces/) | `bff_handlers.py` | Confusão de camada canônica | Low | Aberto — decisão D-017 |
| TD-007 | `src/.env.example` legado vs `.env.example` raiz | config | Docs inconsistentes | Low | **Resolvido** — `src/.env.example` removido (06/06) |
| TD-008 | YOLO — dataset pequeno / rótulos proxy | CV pipeline | Qualidade métrica | Medium | Aberto — mais capturas NASA |
| TD-009 | Documentação multi-arquivo | `docs/`, `.specs/`, README | Drift métricas/texto | Medium | **Resolvido** (jun/2026) — `docs-refresh` fases 0–3 |

---

## Security Concerns

| Concern | Area | Status | Notes |
|---------|------|--------|-------|
| AuthN/AuthZ ausente | API pública | Missing | Endpoints acessíveis sem token (POC) |
| Rate limiting ausente | Endpoints HTTP | Missing | Possível abuso de recursos externos |
| Segredos via env vars | Backend | Partial | `.env` na raiz; nunca commitar credenciais |
| Validacao de payload | Routers | Partial | Pydantic em rotas principais; CV upload validado |

---

## Performance & Reliability Concerns

| Concern | Area | Status | Notes |
|---------|------|--------|-------|
| Cold start elevado na Lambda CV | YOLO + torch | Watch | ~60–90s primeira invocação |
| Ausencia de retry/backoff padrao | Integrações HTTP/AWS | Partial | Erros transientes podem derrubar requests |
| Observabilidade limitada por modulo | API/Lambda | Partial | CloudWatch logs; sem métricas de negócio |

---

## Priority Action Plan

1. **Alta:** Smoke AWS E2E antes da entrega (`make smoke-aws`).
2. **Alta:** PDF + vídeo FIAP (ação humana).
3. **Alta:** Decidir se retreina YOLO antes da entrega ou documenta G1 como v2.
4. **Média:** Mockar Open-Meteo nos testes de weather para CI offline.
5. **Baixa:** Consolidar BFF em uma única camada (pós-GS).

---

## Rules for Tasks Touching Fragile Areas

1. Sempre usar gate **full** (`make test`) após alterações.
2. Alteração em CV/ML deve incluir ou atualizar testes.
3. Alteração de deploy deve atualizar `docs/DEPLOY-LAMBDA.md` e/ou `docs/CI-CD.md`.
4. Qualquer novo TODO deve entrar em `STATE.md` antes de encerrar sessão.
