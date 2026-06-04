# Integrations

**Project:** global-solution-2s
**Mapped on:** 2026-06-04

---

## External Services

| Service | SDK / Client | Auth Method | Purpose | Docs |
|---------|-------------|-------------|---------|------|
| Open-Meteo | requests/httpx | Sem API key | Dados meteorologicos atuais por coordenada | https://open-meteo.com/ |
| AWS S3 | boto3 | IAM credentials | Armazenar imagens/modelos e trigger de pipeline CV | https://docs.aws.amazon.com/s3/ |
| AWS SNS | boto3 | IAM credentials | Notificacoes de alerta de chuva | https://docs.aws.amazon.com/sns/ |
| AWS DynamoDB | boto3 | IAM credentials | Persistencia de metricas, leituras e alertas | https://docs.aws.amazon.com/dynamodb/ |
| AWS Lambda/API Gateway | Mangum + boto3 | IAM credentials | Execucao serverless da API e handlers | https://docs.aws.amazon.com/lambda/ |
| Windy.com (captura) | Playwright | Nao aplicavel | Fonte de screenshots para dataset/processamento | https://www.windy.com/ |

---

## Internal APIs

| API | Base URL (env var) | Auth | Notes |
|-----|-------------------|------|-------|
| FastAPI local | `http://localhost:8000` | Sem auth | Consumida por testes e dashboard local |
| FastAPI cloud | URL API Gateway | Sem auth | Endpoint publico de POC |

---

## Event-driven Integrations

| Provider | Trigger | Flow | Validation |
|----------|---------|------|------------|
| S3 | `ObjectCreated` em `.jpg` | S3 -> Lambda handler -> YOLO -> SNS + DynamoDB | Validacao de extensao e logs |
| CloudWatch | Schedule (30 min) | Event -> ingest_weather.lambda_handler -> Open-Meteo -> DynamoDB | Tratamento de excecao no handler |

---

## Environment Variables

Variaveis observadas em `src/app/core/config.py`:

| Variable | Required | Description |
|----------|:--------:|-------------|
| `ENVIRONMENT` | Sim | Ambiente (`development/staging/production`) |
| `AWS_REGION` | Sim | Regiao AWS |
| `AWS_ACCESS_KEY_ID` | Sim (fora AWS managed) | Credencial IAM |
| `AWS_SECRET_ACCESS_KEY` | Sim (fora AWS managed) | Credencial IAM |
| `S3_BUCKET_MODELS` | Sim | Bucket de modelos |
| `S3_BUCKET_IMAGES` | Sim | Bucket de imagens de entrada |
| `S3_BUCKET_OUTPUTS` | Sim | Bucket de saidas |
| `DYNAMODB_WEATHER_TABLE` | Sim | Tabela de metricas meteorologicas |
| `DYNAMODB_STORM_TABLE` | Sim | Tabela de deteccoes de tempestade |
| `DYNAMODB_RISK_TABLE` | Sim | Tabela de previsoes de risco |
| `DYNAMODB_IOT_TABLE` | Sim | Tabela de leituras IoT |
| `DYNAMODB_TABLE_ALERTS` | Sim | Tabela de alertas do pipeline CV |
| `SNS_TOPIC_ARN` | Sim (pipeline CV) | Topico de notificacao de alertas |
| `OPENMETEO_API_URL` | Nao | URL base da API Open-Meteo |
| `WEATHER_LOCATIONS` | Sim (lambda ingest) | Lista lat/lon para coleta periodica |
| `YOLO_MODEL_S3_KEY` | Sim | Chave do modelo no S3 |
| `YOLO_CONFIDENCE_THRESHOLD` | Nao | Limiar de confianca |

---

## Integration Patterns

### AWS client by settings

```python
s3 = boto3.client("s3", region_name=settings.AWS_REGION)
```

### External call wrapped at endpoint boundary

```python
try:
    weather_data = weather_service.get_current(lat, lon)
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error fetching weather data: {str(e)}")
```

---

## Current Integration Gaps

- Sem autenticacao/autorizacao para endpoints publicos.
- Sem rate limiting para chamadas externas.
- Fluxo IoT ainda em stub (`/iot/readings` nao persiste).
- Deploy da Lambda ainda manual (sem pipeline CI/CD).
