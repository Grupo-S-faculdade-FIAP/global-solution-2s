# Roadmap

**Project:** Global Solutions — Environmental Intelligence  
**Last updated:** 2026-06-04

---

## v1 — MVP (Entrega GS 2026.1)

**Target:** Prazo FIAP  
**Goal:** POC integrado + vídeo + PDF

| Feature | Prioridade | Status | Notas |
|---------|------------|--------|-------|
| YOLO NASA (90 img, mAP ≥ 0,50) | P1 | ✅ Done | `best.pt`, limiar 200/área 600 |
| RiskAssessment + `/risk/forecast` | P1 | ✅ Done | |
| `/storms/recent` + `/map/overlay` | P1 | ✅ Done | mock JSON até AWS |
| Alertas analytics (weekly/hourly/daily/heatmap) | P1 | ✅ Done | Carol |
| `/dashboard/summary` | P1 | ✅ Done | |
| Dashboard + Windy + YOLO demo | P1 | ✅ Done | `make demo` |
| DynamoDB mock local | P1 | ✅ Done | `DYNAMODB_USE_MOCK` |
| ML risco agrícola (sintético) | P1 | ✅ Done | |
| Backend FastAPI + Lambda scaffold | P1 | 🟡 Partial | deploy manual |
| Captura NASA script | P1 | ✅ Done | EventBridge ⏸ |
| README + estrutura TIAO | P1 | 🟡 Partial | |
| PDF entrega | P1 | ❌ Pending | 👤 |
| Vídeo 5 min | P1 | ❌ Pending | 👤 roteiro em `CHECKLIST_ENTREGA.md` |
| IoT ESP32 | P2 | ❌ Out of scope | Rodrigo |

---

## v2 — Pós-GS

| Feature | Status |
|---------|--------|
| AWS DynamoDB real (mock off) | Planned |
| `/alerts/subscribe` | Planned |
| ML com dados Open-Meteo históricos | Planned |
| Mais imagens Windy (novas capturas) | Planned |

---

## Feature specs

| Feature | Spec |
|---------|------|
| Fechamento GS | `.specs/features/gs-closure/spec.md` |
| Checklist entrega | `.specs/project/CHECKLIST_ENTREGA.md` |
