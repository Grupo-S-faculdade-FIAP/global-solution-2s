# Testing

**Project:** global-solution-2s
**Mapped on:** 2026-06-05

---

## Test Framework

| Layer | Framework | Config |
|-------|-----------|--------|
| API/Lambda integration | pytest | Arquivos em `tests/` |
| App basic checks | pytest | `src/tests/test_main.py` |
| Async support | pytest-asyncio | `src/requirements.txt` |
| HTTP app tests | fastapi.testclient | `tests/test_api_endpoints.py` |

**Comando canônico (CI + local):**

```bash
make test
# equivalente: cd src && PYTHONPATH=. ../.venv/bin/pytest ../tests/ tests/ -q
```

**Resultado atual:** 89 passed (jun/2026)

---

## Gate Check Commands

| Gate Level | Command | When to use |
|------------|---------|-------------|
| **quick** | `make test-api` | Mudanças em endpoints de data integration |
| **storms** | `make test-storms` | Mudanças em storm alerts / analytics |
| **full** | `make test` | Mudanças em routers, services, IoT, lambdas |
| **build** | `cd src && make lint && cd .. && make test` | Entregas finais de fase |

---

## Current Test Coverage (Observed)

| Area | File(s) | Tests | Status |
|------|---------|-------|--------|
| Endpoints weather/storm/risk/map | `tests/test_api_endpoints.py` | 23 | Coberto |
| Storm alerts query | `tests/test_storm_alerts_query.py` | 6 | Coberto |
| Storm alerts store | `tests/test_storm_alerts_store.py` | 4 | Coberto |
| Alerts analytics extended | `tests/test_alerts_analytics_extended.py` | 3 | Coberto |
| IoT readings | `tests/test_iot_readings.py` | 11 | Coberto |
| Weather service | `tests/test_weather_service.py` | 7 | Coberto (chamadas reais Open-Meteo) |
| Lambda ingestão clima | `tests/test_ingest_weather_lambda.py` | 10 | Coberto com mocks |
| SNS alerts | `tests/test_sns_alerts.py` | 6 | Coberto |
| Label utils (YOLO pipeline) | `tests/test_label_utils.py` | 5 | Coberto |
| INMET client | `tests/test_inmet_client.py` | 2 | Coberto |
| FAOSTAT export | `tests/test_export_faostat.py` | 7 | Coberto |
| App health | `src/tests/test_main.py` | 5 | Cobertura básica |

---

## Main Gaps

| Gap | Priority | Why it matters |
|-----|----------|----------------|
| Sem teste E2E real S3 → Lambda → DynamoDB | Alta | Fluxo crítico depende de AWS; `make smoke-aws` é manual |
| Sem testes dedicados para `routers/cv.py` com YOLO real | Média | Inferência mockada; regressão de pesos não detectada |
| `tests/test_weather_service.py` depende de internet | Média | Suite pode falhar offline |
| Sem testes frontend dashboard (JS) | Baixa | UI validada manualmente; sem Jest/Playwright e2e |
| G1 YOLO sem teste de métricas mAP no CI | Média | Meta 70% não enforced automaticamente |

---

## Test Patterns in Use

### Endpoint tests (FastAPI TestClient)

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_weather_success():
    response = client.get("/weather/current?lat=-22.89&lon=-43.18")
    assert response.status_code == 200
```

### Lambda tests with patch

```python
from unittest.mock import patch

@patch("app.lambdas.ingest_weather.WeatherService")
def test_lambda_handler_success(mock_service):
    ...
```

### IoT repository mock

```python
# DYNAMODB_USE_MOCK=true + IOT_USE_MOCK=true (default em testes)
# Store: data/demo/iot_readings.json
```

---

## Coverage Goals (Recommended)

| Type | Target | Current |
|------|--------|---------|
| Critical routers (cv/ml/data/iot) | >= 80% | Parcial (~70%) |
| Services (weather/risk/storm) | >= 75% | Médio |
| Lambda handlers | >= 80% | Médio-alto |
| E2E S3 trigger path | 1 smoke por release | Script manual (`make smoke-aws`) |

---

## Running Tests

```bash
make test                    # suite completa (89)
make test-api                # endpoints API
make test-storms             # storm alerts

# Arquivos individuais
cd src && PYTHONPATH=. ../.venv/bin/pytest ../tests/test_iot_readings.py -v

# Lint
cd src && make lint
```
