# Structure

**Project:** global-solution-2s
**Mapped on:** 2026-06-04

---

## Directory Tree

```text
global-solutions/
├── .github/
├── .specs/
│   ├── project/
│   ├── features/
│   ├── codebase/
│   └── quick/
├── assets/                     # logos e midia de documentacao
├── data/
│   ├── goes_raw/               # dados satelitais brutos
│   ├── model-dataset/          # dataset YOLO (images/labels)
│   ├── nasa_captures/          # capturas para pipeline
│   └── test_results/
├── docs/                       # guias de deploy, avaliacao, entrega
├── runs/train/storm-detector/  # artefatos de treino YOLO
├── scripts/goes_pipeline/      # scripts de transformacao dataset
├── src/
│   ├── app/                    # backend FastAPI por dominio
│   │   ├── clients/
│   │   ├── core/
│   │   ├── cron/
│   │   ├── lambdas/
│   │   ├── models/
│   │   ├── routers/
│   │   └── services/
│   ├── dashboard/              # app Flask de visualizacao
│   ├── models/                 # wrappers e weights locais
│   ├── tests/                  # testes locais do pacote src
│   ├── requirements*.txt
│   ├── Makefile
│   └── yolo_training.py
├── tests/                      # testes de integracao API/Lambda
└── yolov5/                     # codigo-base YOLOv5
```

---

## Key Files

| File | Purpose |
|------|---------|
| `README.md` | Contexto geral do projeto e execucao |
| `docs/DEPLOY-LAMBDA.md` | Procedimento de deploy na AWS |
| `src/app/main.py` | App FastAPI + roteamento Lambda HTTP/S3 |
| `src/app/core/config.py` | Variaveis de ambiente e defaults |
| `src/app/routers/cv.py` | Pipeline de inferencia YOLO + SNS + DynamoDB |
| `src/app/routers/data_integration.py` | Endpoints weather/storm/risk/map |
| `src/app/lambdas/ingest_weather.py` | Ingestao periodica Open-Meteo -> DynamoDB |
| `src/models/stormdetector.py` | Inferencia local de referencia YOLO |
| `src/Makefile` | Comandos de install/run/test/lint |
| `data/model-dataset/storm.yaml` | Config do dataset YOLO |

---

## Ownership by Area

| Area | Directory | Main Concern |
|------|-----------|--------------|
| API backend | `src/app/` | Endpoints e orquestracao de fluxos |
| ML/CV artifacts | `src/models/`, `runs/`, `data/model-dataset/` | Treino e inferencia YOLO |
| Dashboard | `src/dashboard/` | Visualizacao operacional |
| Data engineering | `scripts/goes_pipeline/` | Preparacao de dataset |
| Tests | `tests/` e `src/tests/` | Validacao funcional e regressao |
| Operational docs | `docs/` | Deploy e guias de entrega |

---

## Test File Location Strategy

| Test type | Location |
|-----------|---------|
| API integration tests | `tests/test_api_endpoints.py` |
| Service tests | `tests/test_weather_service.py` |
| Lambda tests | `tests/test_ingest_weather_lambda.py` |
| Basic app tests | `src/tests/test_main.py` |

Observacao: ainda nao ha padrao de co-locacao por modulo (por ex. `src/app/routers/*_test.py`).
