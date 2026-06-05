# Structure

**Project:** global-solution-2s
**Mapped on:** 2026-06-05

---

## Directory Tree

```text
global-solutions/
├── .github/workflows/          # CI (pytest) + CD (Lambda OIDC)
├── .specs/                     # Spec-driven docs (project, features, codebase)
├── assets/                     # logos e mídia de documentação
├── data/
│   ├── demo/                   # JSON mock (storm_alerts, iot_readings)
│   ├── goes_raw/               # dados satelitais brutos
│   ├── model-dataset/          # dataset YOLO (images/labels)
│   ├── nasa_captures/          # 93 capturas PNG (jun/2026)
│   └── test_results/
├── docs/                       # RPI, deploy, CI/CD, guias FIAP
├── scripts/                    # pipeline agrícola, smoke AWS, goes_pipeline
├── src/
│   ├── app/                    # backend FastAPI (Clean Architecture)
│   │   ├── application/        # use cases (DetectStormUseCase, …)
│   │   ├── clients/            # Open-Meteo, INMET
│   │   ├── container.py        # DI factory (mock ↔ DynamoDB)
│   │   ├── core/               # config, logging
│   │   ├── cron/               # captura NASA, upload S3
│   │   ├── domain/             # Ports (Protocols)
│   │   ├── infrastructure/     # adapters AWS + JSON
│   │   ├── interfaces/         # HTTP BFF, Lambda events
│   │   ├── lambdas/            # ingest_weather
│   │   ├── models/             # Pydantic schemas
│   │   ├── routers/            # endpoints HTTP
│   │   └── services/           # weather, agri risk, storm detector
│   ├── dashboard/              # Flask UI + static/js (ES modules)
│   ├── iot/                    # firmware.cpp + README
│   ├── models/                 # stormdetector.py + weights/best.pt
│   ├── tests/                  # test_main.py
│   ├── requirements*.txt
│   ├── Dockerfile              # imagem Lambda
│   └── yolo_training.py
├── tests/                      # suite principal (259 testes + e2e/)
├── yolov5/                     # código-base YOLOv5
├── .env.example                # config canônica (copiar → .env)
├── Makefile                    # install, demo, test, build-agri, …
└── README.md
```

---

## Key Files

| File | Purpose |
|------|---------|
| `README.md` | Contexto geral, execução, links AWS |
| `docs/RPI.md` | Relatório de progresso FIAP (status formal) |
| `docs/DEPLOY-LAMBDA.md` | Deploy manual Lambda |
| `docs/CI-CD.md` | GitHub Actions + OIDC |
| `src/app/main.py` | FastAPI + Mangum + WSGI dashboard |
| `src/app/core/config.py` | Settings (.env raiz + src/.env) |
| `src/app/container.py` | DI: mock JSON ↔ DynamoDB |
| `src/app/application/cv/detect_storm.py` | Use case YOLO + SNS + persist |
| `src/app/interfaces/events/s3_trigger.py` | Handler S3 → use case |
| `src/dashboard/static/js/app.js` | Entry dashboard ES modules |
| `src/dashboard/bff_handlers.py` | Lógica BFF canônica (`/api/*`) |
| `src/iot/firmware.cpp` | Firmware ESP32 → POST /iot/readings |
| `Makefile` | Comandos raiz (demo, test, build-agri) |
| `data/model-dataset/storm.yaml` | Config dataset YOLO |

---

## Ownership by Area

| Area | Directory | Main Concern |
|------|-----------|--------------|
| API backend | `src/app/` | Endpoints, use cases, DI |
| ML/CV | `src/models/`, `data/model-dataset/`, `scripts/goes_pipeline/` | Treino e inferência YOLO |
| Dashboard | `src/dashboard/` | UI HTML/JS + BFF handlers |
| IoT | `src/iot/` | Firmware ESP32 |
| Data / ML agrícola | `scripts/`, `docs/dados/` | INMET, FAOSTAT, treino |
| Tests | `tests/`, `tests/e2e/`, `src/tests/` | 259 pytest + 53 E2E |
| Ops docs | `docs/`, `.specs/` | Deploy, RPI, specs |

---

## Test File Location Strategy

| Test type | Location |
|-----------|----------|
| API integration | `tests/test_api_endpoints.py` |
| Storm alerts / analytics | `tests/test_storm_*.py`, `tests/test_alerts_analytics_extended.py` |
| IoT | `tests/test_iot_readings.py` |
| Weather / Lambda | `tests/test_weather_service.py`, `tests/test_ingest_weather_lambda.py` |
| ML / dados | `tests/test_inmet_client.py`, `tests/test_export_faostat.py` |
| CV pipeline | `tests/test_label_utils.py`, `tests/test_sns_alerts.py` |
| App health | `src/tests/test_main.py` |

Observação: testes co-localizados por módulo em `src/app/**/_test.py` ainda não adotados — suite centralizada em `tests/`.
