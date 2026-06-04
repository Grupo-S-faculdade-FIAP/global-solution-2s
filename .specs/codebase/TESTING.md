# Testing

**Project:** global-solution-2s
**Mapped on:** 2026-06-04

---

## Test Framework

| Layer | Framework | Config |
|-------|-----------|--------|
| API/Lambda integration | pytest | Arquivos em `tests/` |
| App basic checks | pytest | Arquivos em `src/tests/` |
| Async support | pytest-asyncio | Dependencia em `src/requirements.txt` |
| HTTP app tests | fastapi.testclient | Utilizado em `tests/test_api_endpoints.py` |

---

## Gate Check Commands

| Gate Level | Command | When to use |
|------------|---------|-------------|
| **quick** | `pytest tests/test_api_endpoints.py -v` | Mudancas em endpoints de data integration |
| **full** | `pytest tests/ src/tests/ -v` | Mudancas em routers/services/lambdas |
| **build** | `cd src && make lint && cd .. && pytest tests/ src/tests/ -v` | Entregas finais de fase |

---

## Current Test Coverage (Observed)

| Area | File(s) | Status |
|------|---------|--------|
| Endpoints weather/storm/risk/map | `tests/test_api_endpoints.py` | Coberto (fluxo feliz + validacoes) |
| Weather service | `tests/test_weather_service.py` | Coberto, com chamadas reais e cache |
| Lambda ingestao clima | `tests/test_ingest_weather_lambda.py` | Coberto com mocks boto3/services |
| App health e routers | `src/tests/test_main.py` | Cobertura basica |

---

## Main Gaps

| Gap | Priority | Why it matters |
|-----|----------|----------------|
| Sem testes para `src/app/routers/cv.py` | Alta | Fluxo critico S3 -> YOLO -> SNS -> DynamoDB pode quebrar sem aviso |
| Sem testes para `src/app/routers/ml.py` | Alta | Endpoint de predicao agricola pode retornar erro silencioso |
| Sem testes para `src/app/services/agri_risk_model.py` | Alta | Modelo e serializacao sem garantias de comportamento |
| Sem testes para `src/app/services/storm_detector.py` | Media | Regressao em inferencia local |
| `tests/test_weather_service.py` depende de internet | Media | Suite pode falhar por indisponibilidade externa |
| Routers IoT sao stubs sem testes | Media | Funcionalidade aparece pronta, mas nao esta implementada |

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

@patch("src.app.lambdas.ingest_weather.WeatherService")
def test_lambda_handler_success(mock_service):
    ...
```

---

## Coverage Goals (Recommended)

| Type | Target | Current |
|------|--------|---------|
| Critical routers (cv/ml/data) | >= 80% | Parcial |
| Services (weather/risk/storm) | >= 75% | Baixo a medio |
| Lambda handlers | >= 80% | Medio |
| End-to-end S3 trigger path | 1 smoke test por release | Ausente |

---

## Running Tests

```bash
# Tudo
pytest tests/ src/tests/ -v

# Apenas integracao de API
pytest tests/test_api_endpoints.py -v

# Apenas weather service
pytest tests/test_weather_service.py -v

# Apenas lambda ingestao
pytest tests/test_ingest_weather_lambda.py -v

# Lint
cd src && make lint
```
