# Stack

**Project:** global-solution-2s
**Mapped on:** 2026-06-06

---

## Runtime & Language

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| Language | Python | 3.11+ | Backend, ML, automations |
| Runtime API | ASGI (Uvicorn) | 0.32.1 | Execução local (`make demo`) |
| Runtime serverless | AWS Lambda + Mangum | Mangum 0.19.0 | Adaptador FastAPI para Lambda |
| Package manager | pip | n/a | `make install` → `src/requirements.txt` |
| Virtualenv | `.venv/` | na raiz | Esperado pelo Makefile |

---

## Frameworks & Libraries

| Category | Library | Version | Purpose |
|----------|---------|---------|---------|
| Web framework | FastAPI | 0.115.5 | API REST principal |
| Dashboard UI | Flask | 3.1.1 | HTML/Jinja montado em `/` via WSGI |
| Validation/config | Pydantic + pydantic-settings | 2.10.3 / 2.6.1 | Schemas e variáveis de ambiente |
| Server | Uvicorn | 0.32.1 | Servidor local de desenvolvimento |
| Cloud SDK | boto3 | 1.35.74 | S3, SNS e DynamoDB |
| Computer Vision | torch + torchvision | >=2.2.0 / >=0.17.0 | Inferência YOLOv5 |
| Image processing | opencv-python-headless + Pillow | 4.10.0.84 / 11.0.0 | Leitura e preprocessamento de imagem |
| ML tabular | scikit-learn + numpy + pandas | 1.5.2 / 1.26.4 / 2.2.3 | Modelo de risco agrícola |
| HTTP client | httpx + requests | 0.28.0 / 2.32.3 | Integrações externas |
| Frontend (dashboard) | Chart.js + Leaflet + Windy widget | CDN | Gráficos, mapas, radar |
| Browser automation | Playwright | 1.49.0 | Captura NASA Worldview |
| Testing | pytest + pytest-cov + playwright | 8.3.3+ | 440 testes (`make test`) + 53 E2E |
| Lint | Ruff | n/a | `cd src && make lint` |

---

## Database

| Type | Technology | Version | Notes |
|------|-----------|---------|-------|
| Alerts | AWS DynamoDB | managed | Tabela `alerts` / `storm_alerts` (pipeline CV) |
| IoT | AWS DynamoDB | managed | Tabela `iot_readings` |
| Weather / risk | AWS DynamoDB | managed | `weather_metrics`, `storm_detections`, `risk_predictions` |
| Mock local | JSON files | — | `data/demo/storm_alerts.json`, `iot_readings.json` quando mock=true |
| Cache | In-memory (LRU) | stdlib | Cache local no service de clima |

---

## Infrastructure

| Layer | Technology | Notes |
|-------|-----------|-------|
| Hosting API | AWS Lambda + API Gateway | `gs2-api` — Docker image |
| Storage | AWS S3 | `satellite-images-gs2` — imagens e modelos |
| Notifications | AWS SNS | Alertas de detecção de tempestade |
| Logs | AWS CloudWatch | Observabilidade da Lambda |
| Container | Docker | Build da imagem da Lambda (`src/Dockerfile`) |
| CI/CD | GitHub Actions + OIDC | `.github/workflows/ci.yml`, `deploy-lambda.yml` — ver `docs/CI-CD.md` |

---

## External Integrations

| Service | SDK/Client | Purpose |
|---------|-----------|---------|
| Open-Meteo API | httpx/requests | Dados meteorológicos atuais |
| INMET BDMEP | scripts + client | Treino ML risco agrícola |
| FAOSTAT | scripts | Contexto agrícola Brasil |
| Windy.com | Widget JS + Playwright (captura) | Radar no dashboard; screenshots NASA |
| NASA/GOES | Playwright + scripts | Captura e conversão dataset YOLO |
| AWS S3 / SNS / DynamoDB | boto3 | Pipeline serverless |

---

## Key Dev Scripts

```bash
# Raiz do repo — comandos principais
make install          # pip install -r src/requirements.txt
make demo             # API + dashboard em http://127.0.0.1:8000
make test             # 440 testes (mesmo comando do CI)
make test-coverage    # gate 82%
make test-e2e         # Playwright dashboard
make test-api
make test-storms
make build-agri       # pipeline INMET + FAOSTAT + ML
make train-yolo       # retreino YOLO local
make smoke-aws        # smoke E2E na AWS

# Config: copiar .env.example → .env na RAIZ do repo
```
