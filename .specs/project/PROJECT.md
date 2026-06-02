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

- [ ] **G1** — Detectar tempestades e padrões de nuvens chuvosas em imagens de satélite com YOLO (precisão ≥ 70% no conjunto de validação)
- [ ] **G2** — Prever risco agrícola (seca, geada, produtividade) com modelo ML usando dados climáticos de satélite
- [ ] **G3** — Visualizar dados climáticos em tempo real via Windy API em dashboard web integrado
- [ ] **G4** — Coletar dados de solo/ambiente com ESP32 e enviá-los para pipeline cloud na AWS
- [ ] **G5** — Entregar MVP funcional documentado com vídeo de até 5 min dentro do prazo da GS

---

## Tech Stack

**Core:**
- Language: Python 3.11
- Framework: FastAPI (backend API)
- ML/CV: Ultralytics YOLOv8, scikit-learn, pandas, numpy
- Cloud: AWS (Lambda, S3, API Gateway)
- Database: DynamoDB (alertas + dados IoT time-series) — 100% NoSQL
- Frontend: HTML/JS + Windy API widget + Streamlit (dashboard)
- IoT: ESP32 + MicroPython (sensores de temperatura, umidade, solo)

**Key dependencies:** ultralytics, fastapi, boto3, streamlit, requests

---

## Scope

**MVP (v1) inclui:**
- Pipeline de ingestão e análise de imagens de satélite (INPE/NASA via API ou dataset público)
- Modelo YOLO treinado para detecção de tempestades/padrões de nuvens chuvosas
- Modelo de ML para previsão de risco agrícola (regressão/classificação)
- Dashboard com Windy API (visualização climática em tempo real no mapa)
- Backend FastAPI na AWS (Lambda + API Gateway) conectado ao banco de dados
- ESP32 enviando leituras de sensor para endpoint HTTP (API Gateway → Lambda)
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

How we know the project is successful:

- [ ] [Measurable outcome — e.g., "User can complete X in < 2 minutes"]
- [ ] [Measurable outcome — e.g., "Zero errors in Y scenario"]
- [ ] [Measurable outcome — e.g., "N users can use feature Z simultaneously"]

---

<!-- Size limit: 2,000 tokens (~1,200 words). Keep it concise. -->
