# Roadmap

**Project:** Global Solutions — Environmental Intelligence (GS2)
**Last updated:** 2026-06-05

---

## v1 — MVP (Entrega GS 2026.1)

**Target:** Prazo FIAP  
**Goal:** POC integrado + vídeo + PDF

| Feature | Prioridade | Status | Notas |
|---------|------------|--------|-------|
| YOLO NASA pipeline v2 (labels honestos, 0 ghost) | P1 | ✅ Done | 93 capturas, 79 train; mAP@0.5 ≈ 0,14 — abaixo G1 (70%) |
| RiskAssessment + `/risk/forecast` + INMET/FAOSTAT | P1 | ✅ Done | `AgriRiskModel`, `make build-agri` |
| `/storms/recent` + `/map/overlay` | P1 | ✅ Done | mock JSON + DynamoDB via DI |
| Alertas analytics (weekly/hourly/daily/heatmap) | P1 | ✅ Done | Carol |
| BFF `/api/*` + dashboard ES modules | P1 | ✅ Done | `make demo`, tema claro/escuro |
| DynamoDB mock local | P1 | ✅ Done | `DYNAMODB_USE_MOCK` |
| IoT ESP32 (API + firmware + dashboard) | P1 | ✅ Done | Rodrigo — `src/iot/`, 11 testes |
| Clean Architecture (Ports & Adapters) | P1 | ✅ Done | Domain → Application → Infrastructure → Interfaces |
| CI/CD GitHub Actions + OIDC | P1 | ✅ Done | `docs/CI-CD.md` |
| Backend FastAPI + Lambda deploy | P1 | 🟡 Partial | CD na main; smoke manual pendente |
| Captura NASA script | P1 | ✅ Done | EventBridge ⏸ AWS |
| ML risco v2 (ensemble geo + AG limiares) | P1 | ✅ Done | `risk-pipeline-v2`, `ml.js` |
| E2E Playwright + cobertura 82% | P1 | ✅ Done | `make test-e2e`, CI job `e2e-dashboard` |
| Docs alinhados ao código (docs-refresh) | P1 | ✅ Done | fases 0–3; cobertura 82,44% verificada |
| README + estrutura TIAO | P1 | 🟡 Partial | DOC-1: NASA, ML, 259 testes; falta screenshot |
| PDF entrega | P1 | ❌ Pending | 👤 esqueleto em `docs/PDF-ENTREGA-ESQUELETO.md` |
| Vídeo 5 min | P1 | ❌ Pending | 👤 roteiro em `CHECKLIST_ENTREGA.md` |

---

## v2 — Pós-GS

| Feature | Status |
|---------|--------|
| YOLO mAP ≥ 70% (G1) | Planned |
| AWS DynamoDB real em produção (mock off) | Planned |
| `/alerts/subscribe` | Planned |
| Mais imagens Windy (novas capturas rotuladas) | Planned |
| Telemetria IoT contínua (múltiplos dispositivos) | Planned |

---

## Feature specs

| Feature | Spec | Status |
|---------|------|--------|
| Fechamento GS | `gs-closure/spec.md` | Mostly complete |
| Docs refresh | `docs-refresh/spec.md` | Done |
| ML risco v2 | `risk-pipeline-v2/spec.md` | Done |
| Refatoração arquitetura | `architecture-refactor/spec.md` | Done |
| Dashboard produtor | `dashboard-producer-ready/spec.md` | Done |
| Qualidade labels YOLO | `yolo-label-quality/spec.md` | Done |
| INMET + FAOSTAT | `agri-inmet-faostat/spec.md` | Done |
| Checklist entrega | `.specs/project/CHECKLIST_ENTREGA.md` | Ativo |
