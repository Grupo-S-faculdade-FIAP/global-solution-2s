# Stack

**Project:** global-solution-2s
**Mapped on:** 2026-06-04

---

## Runtime & Language

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| Language | Python | 3.11+ | Backend, ML, automations |
| Runtime API | ASGI (Uvicorn) | 0.32.1 | Execucao local |
| Runtime serverless | AWS Lambda + Mangum | Mangum 0.19.0 | Adaptador FastAPI para Lambda |
| Package manager | pip | n/a | Instalacao por requirements.txt |

---

## Frameworks & Libraries

| Category | Library | Version | Purpose |
|----------|---------|---------|---------|
| Web framework | FastAPI | 0.115.5 | API REST principal |
| Validation/config | Pydantic + pydantic-settings | 2.10.3 / 2.6.1 | Schemas e variaveis de ambiente |
| Server | Uvicorn | 0.32.1 | Servidor local de desenvolvimento |
| Cloud SDK | boto3 | 1.35.74 | S3, SNS e DynamoDB |
| Computer Vision | torch + torchvision | >=2.2.0 / >=0.17.0 | Inferencia YOLOv5 |
| Image processing | opencv-python-headless + Pillow | 4.10.0.84 / 11.0.0 | Leitura e preprocessamento de imagem |
| ML tabular | scikit-learn + numpy + pandas | 1.5.2 / 1.26.4 / 2.2.3 | Modelo de risco agricola |
| HTTP client | httpx + requests | 0.28.0 / 2.32.3 | Integracoes externas |
| Dashboard | Flask | 3.1.1 | Interface local de visualizacao |
| Browser automation | Playwright | 1.49.0 | Captura automatica de imagens |
| Testing | pytest + pytest-asyncio | 8.3.3 / 0.24.0 | Suite de testes |
| Lint | Ruff | n/a | Qualidade de codigo |

---

## Database

| Type | Technology | Version | Notes |
|------|-----------|---------|-------|
| Primary DB | AWS DynamoDB | managed | Tabelas weather_metrics, storm_detections, risk_predictions, iot_readings |
| Alerts DB | AWS DynamoDB | managed | Tabela storm_alerts (pipeline CV) |
| Cache | In-memory (LRU via Python) | stdlib | Cache local no service de clima |

---

## Infrastructure

| Layer | Technology | Notes |
|-------|-----------|-------|
| Hosting API | AWS Lambda + API Gateway | Execucao serverless de endpoints |
| Storage | AWS S3 | Buckets para imagens, modelos e saida |
| Notifications | AWS SNS | Alertas de deteccao de tempestade |
| Logs | AWS CloudWatch | Observabilidade da Lambda |
| Container | Docker | Build da imagem da Lambda |
| CI/CD | Manual (AWS CLI + Docker) | Ainda sem pipeline automatizado |

---

## External Integrations

| Service | SDK/Client | Purpose |
|---------|-----------|---------|
| Open-Meteo API | requests/httpx | Dados meteorologicos atuais |
| Windy.com | Playwright (captura) | Fonte visual para screenshots de nuvens |
| NASA/GOES datasets | Scripts Python | Conversao para dataset YOLO |
| AWS S3 | boto3 | Trigger e armazenamento de artefatos |
| AWS SNS | boto3 | Notificacoes de chuva |
| AWS DynamoDB | boto3 | Persistencia de metricas e alertas |

---

## Key Dev Scripts

```bash
# Instalar dependencias
cd src && pip install -r requirements.txt

# Rodar API local
cd src && make run

# Rodar dashboard local
cd src && make run-dashboard

# Executar testes
pytest tests/ -v

# Lint
cd src && make lint

# Treinar YOLO local
python src/yolo_training.py --epochs 50 --batch 8 --device cpu
```
