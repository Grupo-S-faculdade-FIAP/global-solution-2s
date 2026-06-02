# Roadmap

**Project:** —
**Last updated:** 2026-06-01

---

## Milestones

### v1 — MVP (Entrega GS 2026.1)
**Target:** Prazo da plataforma FIAP
**Goal:** POC funcional com todos os módulos integrados, documentados e demonstrados em vídeo

| Feature | Disciplina | Prioridade | Status | Notas |
|---------|-----------|------------|--------|-------|
| Pipeline de ingestão de imagens de satélite | Python / Automação | P1 | Not started | NASA FIRMS ou INPE via API/dataset |
| Modelo YOLO para detecção de tempestades | Computer Vision / YOLO | P1 | Not started | YOLOv8 fine-tuned em dataset de nuvens chuvosas (Windy.com) |
| Modelo ML de previsão de risco agrícola | Machine Learning | P1 | Not started | Regressão/classificação com dados climáticos |
| Backend FastAPI + endpoints REST | Python / Automação | P1 | Not started | Deploy na AWS Lambda via API Gateway |
| Dashboard com Windy API (frontend) | Análise de Dados / Dashboards | P1 | Not started | Widget Windy + gráficos de dados locais |
| Armazenamento S3 (imagens) + DynamoDB (alertas + IoT) | Banco de Dados | P1 | Not started | 100% NoSQL, sem RDS |
| ESP32 — coleta de sensores e envio para AWS | IoT / ESP32 | P1 | Not started | Temperatura, umidade, solo → HTTP POST para /iot/readings |
| Serviço cognitivo / Rekognition ou Comprehend | APIs / Serviços Cognitivos | P2 | Not started | Classificação auxiliar ou análise de texto |
| README + estrutura do repositório | Documentação | P1 | Not started | Seguir template TIAO-2026 |
| PDF de entrega | Documentação | P1 | Not started | Introdução, Desenvolvimento, Resultados, Conclusão |
| Vídeo demonstrativo (≤ 5 min, YouTube não listado) | Entrega | P1 | Not started | Incluir "QUERO CONCORRER" se for ao pódio |

---

### v2 — Melhorias pós-GS (opcional)
**Target:** Após entrega
**Goal:** Evoluir de POC para produto mais robusto

| Feature | Prioridade | Status | Notas |
|---------|------------|--------|-------|
| Cobertura além do Brasil | P3 | Planned | |
| Alertas em tempo real (push/email) | P3 | Planned | |
| App mobile (React Native) | P3 | Planned | |

---

## Feature Index

Links to individual feature specs as they are created:

| Feature | Spec | Status |
|---------|------|--------|
| [Feature name] | `.specs/features/[slug]/spec.md` | Not started |

---

## Decisions Log

Major direction decisions (quick reference — full detail in STATE.md):

| Date | Decision | Impact |
|------|----------|--------|
| [YYYY-MM-DD] | [Decision made] | [What it affects] |

---

<!-- Update this file whenever feature priorities or milestones change. -->
