# Projeto

**Vision:** Plataforma de inteligência ambiental e agrícola que combina dados de satélite, visão computacional e sensores IoT para monitorar clima, detectar tempestades/padrões de nuvens chuvosas e prever riscos agrícolas — conectando a economia espacial ao impacto direto na Terra.
**For:** Pesquisadores, produtores rurais, órgãos de monitoramento ambiental e gestores de risco.
**Solves:** A fragmentação e a demora no acesso a inteligência ambiental acionável — hoje dados de satélite existem mas não são processados, analisados e visualizados de forma integrada e acessível.

---

## Equipe

| Nome | E-mail |
|------|--------|
| Caroline de Castro Corrêa | castrocaroline11@gmail.com |
| Rodrigo Dias Figueiroa | rdfigueiroa@gmail.com |
| Enzo França Sader | efr4nca03@gmail.com |
| Lucas Hideki Oliveira Koyama | lucaskoyamahhh@gmail.com |
| Tiago Lindgren Curi | shopper.tiago@gmail.com |

---

## Goals

- [x] **G1** — Detectar tempestades e padrões de nuvens chuvosas em imagens de satélite com YOLO (POC funcional: treino, inferência local e Lambda) — métricas val: mAP@0.5=56,5%, P=73,5% em conf=0,55
- [x] **G2** — Prever risco agrícola com ML + clima — `AgriRiskModel` (INMET BDMEP), AG limiares (DEAP), `RiskAssessmentService` ensemble geo-aware, `/risk/forecast`
- [x] **G3** — Visualizar dados climáticos em tempo real via Windy widget + Open-Meteo em dashboard web integrado
- [x] **G4** — Coletar dados de ambiente em campo com ESP32 (DHT22) e enviar ao pipeline cloud (`POST /iot/readings`, mock + DynamoDB)
- [ ] **G5** — Entregar MVP funcional documentado com vídeo de até 5 min dentro do prazo da GS — **parcial:** código ~95%; vídeo publicado; PDF pendente

---

## Tech Stack

**Core:**
- Language: Python 3.11
- Framework: FastAPI (backend API) + Flask (dashboard UI montado via WSGI)
- ML/CV: YOLOv5 (PyTorch Hub), scikit-learn, LightGBM (opcional), DEAP (AG limiares), pandas, numpy
- Cloud: AWS (Lambda, S3, API Gateway, DynamoDB, SNS)
- Database: DynamoDB (alertas + dados IoT time-series) — 100% NoSQL
- Frontend: HTML/JS (ES modules) + Windy widget + Leaflet + Chart.js
- IoT: ESP32 + Arduino (DHT22 — firmware em `src/iot/firmware.cpp`)
- Testes: pytest (440), Playwright E2E (53), cobertura CI ≥ 82%

**Key dependencies:** torch, torchvision, fastapi, flask, boto3, httpx, requests, pydantic-settings

---

## Scope

**MVP (v1) inclui:**
- Pipeline de ingestão e análise de imagens de satélite (NASA GOES via captura Playwright)
- Modelo YOLO treinado para detecção de tempestades/padrões de nuvens chuvosas
- Modelo de ML para previsão de risco agrícola (INMET + FAOSTAT + ensemble)
- Dashboard HTML com Windy widget, mapas Leaflet e gráficos Chart.js
- Backend FastAPI na AWS (Lambda + API Gateway) conectado ao DynamoDB
- ESP32 (DHT22) enviando leituras para endpoint HTTP (API Gateway → Lambda)
- CI/CD GitHub Actions + OIDC (sem access keys)
- README completo + PDF de entrega + vídeo demonstrativo

**Explicitamente fora do escopo:**
- App mobile nativo
- Integração com sistemas ERP agrícolas
- Cobertura de dados além do território brasileiro (v1)
- Modelo em produção com SLA real (é uma POC)
---

## Constraints

- Timeline: Prazo da plataforma FIAP (GS 2026.1) — entregar antes do fechamento
- Technical: Tier gratuito da AWS (Lambda, S3, DynamoDB free tier); Windy API free plan
- Resources: 5 integrantes, trabalho paralelo por módulo
- Compliance: Código não pode ser plágio; vídeo como "não listado" no YouTube

---

## Success Criteria

- [x] Avaliador consegue rodar demo integrada com `make demo` em uma única URL (http://127.0.0.1:8000)
- [x] Suite de testes passa (`make test` — 440 testes; cobertura **~82%**, jun/2026)
- [x] Dashboard exibe clima, alertas, risco agrícola (ensemble), mapas e seção IoT com fallback demo documentado
- [x] Vídeo ≤ 5 min no YouTube (não listado) — https://www.youtube.com/watch?v=W67760WVado
- [ ] PDF estruturado entregue na plataforma FIAP
- [x] G1 YOLO: detecção integrada ao pipeline (modelo treinado, demo e Lambda — D-027/D-028)

---

<!-- Size limit: 2,000 tokens (~1,120 words). Keep it concise. -->
