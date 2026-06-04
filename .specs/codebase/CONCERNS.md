# Concerns

**Project:** global-solution-2s
**Mapped on:** 2026-06-04

Este documento consolida riscos reais observados no estado atual do codigo.

---

## Fragile Areas

| Area | File(s) | Risk | Why fragile | Mitigation |
|------|---------|:----:|------------|------------|
| Pipeline S3 -> YOLO -> SNS/DynamoDB | `src/app/main.py`, `src/app/routers/cv.py` | High | Fluxo event-driven com multiplas dependencias externas e sem testes dedicados | Criar testes com mocks boto3 + smoke test de trigger |
| Modelo de risco agricola | `src/app/services/agri_risk_model.py`, `src/app/routers/ml.py` | High | Modelo treinado com dados sinteticos e sem suite de validacao robusta | Incluir dataset real + testes de regressao de metricas |
| Integracao de ingestao periodica | `src/app/lambdas/ingest_weather.py` | Medium | Depende de API externa e escrita em DynamoDB | Aumentar observabilidade e retry controlado |
| Deploy serverless | `docs/DEPLOY-LAMBDA.md`, `src/Dockerfile` | Medium | Processo manual com varios passos operacionais | Automatizar com CI/CD |

---

## Technical Debt

| ID | Description | Location | Impact | Priority |
|----|-------------|---------|--------|----------|
| TD-001 | Endpoints IoT ainda retornam "not implemented" | `src/app/routers/iot.py` | Funcionalidade incompleta exposta como pronta | High |
| TD-002 | Endpoints `/storms/recent` e `/map/overlay` retornam dados vazios (TODO) | `src/app/routers/data_integration.py` | Valor de negocio parcial no dashboard/API | High |
| TD-003 | Dependencia de internet em testes de weather service | `tests/test_weather_service.py` | Flakiness em CI e ambientes sem rede | Medium |
| TD-004 | Falta de teste para fluxo CV e modelos | `src/app/routers/cv.py`, `src/app/services/*` | Alto risco de regressao silenciosa | High |
| TD-005 | Sem pipeline CI/CD para build e deploy da Lambda | raiz + docs | Erro operacional e deploy inconsistente | Medium |

---

## Security Concerns

| Concern | Area | Status | Notes |
|---------|------|--------|-------|
| AuthN/AuthZ ausente | API publica | Missing | Endpoints acessiveis sem token |
| Rate limiting ausente | Endpoints HTTP | Missing | Possivel abuso de recursos externos |
| Segredos via env vars | Backend | Partial | Estrutura existe, mas faltam validacoes de ambiente em bootstrap |
| Validacao de payload | Routers | Partial | Boa base com Query/Pydantic, mas falta cobertura em rotas CV/IoT |

---

## Performance & Reliability Concerns

| Concern | Area | Status | Notes |
|---------|------|--------|-------|
| Cold start elevado na Lambda CV | `src/app/routers/cv.py` | Watch | Download de modelo e carga do torch no primeiro ciclo |
| Ausencia de retry/backoff padrao | Integracoes HTTP/AWS | Partial | Erros transientes podem derrubar requests |
| Observabilidade limitada por modulo | API/Lambda | Partial | Logs presentes, mas sem metricas de negocio/latencia |

---

## Priority Action Plan

1. Alta: testar e estabilizar fluxo CV completo (S3 trigger, inferencia, SNS, DynamoDB).
2. Alta: implementar de fato endpoints pendentes de dados (`/storms/recent`, `/map/overlay`, IoT readings).
3. Alta: robustecer avaliacao do modelo de risco agricola com dados nao sinteticos e metas minimas de performance.
4. Media: reduzir fragilidade de testes externos com mocks/fixtures para Open-Meteo.
5. Media: criar pipeline CI/CD para build, lint, teste e deploy da Lambda.

---

## Rules for Tasks Touching Fragile Areas

1. Sempre usar gate **full** apos alteracoes.
2. Alteracao em CV/ML deve incluir ou atualizar testes.
3. Alteracao de deploy deve atualizar `docs/DEPLOY-LAMBDA.md`.
4. Qualquer novo TODO deve entrar em `STATE.md` antes de encerrar sessao.
