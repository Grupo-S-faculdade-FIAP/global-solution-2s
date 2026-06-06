# Integrações — Global Solutions

**Atualizado:** 2026-06-06

## Dashboard BFF (`/api/*`)

O frontend consome exclusivamente rotas `/api/*` servidas pelo BFF. A implementação canônica está em [`dashboard/bff_handlers.py`](../../src/dashboard/bff_handlers.py) (decisão D-017); [`interfaces/http/bff/handlers.py`](../../src/app/interfaces/http/bff/handlers.py) re-exporta para a camada Interfaces. Rotas espelhadas em Flask ([`app.py`](../../src/dashboard/app.py)) e FastAPI ([`routers/dashboard_bff.py`](../../src/app/routers/dashboard_bff.py)).

Contratos JS: [`core/api/endpoints.js`](../../src/dashboard/static/js/core/api/endpoints.js).

Header de resposta: **`X-Data-Source`** — `live` (DynamoDB/backend real), `demo` (JSON local), ou ausente em erro.

### Endpoints consumidos pelo dashboard

| Domínio | Método | Path | Query / Body | Uso |
|---------|--------|------|--------------|-----|
| dashboard | GET | `/api/dashboard/config` | — | `demo_mode`, storage, defaults |
| alerts | GET | `/api/alerts/summary` | `days` (opc.) | KPIs |
| alerts | GET | `/api/alerts/daily` | `days` (opc.) | gráfico tendência |
| alerts | GET | `/api/alerts/weekly` | `days` (opc.) | gráfico semanal |
| alerts | GET | `/api/alerts/hourly` | `days` (opc.) | gráfico horário |
| alerts | GET | `/api/alerts/heatmap` | `days` (opc.) | heatmap 7×24 |
| alerts | POST | `/api/alerts/simulate-detection` | `{ confidence, lat, lon }` | simular alerta YOLO |
| weather | GET | `/api/weather/current` | `lat`, `lon` | clima atual |
| risk | GET | `/api/risk/forecast` | `lat`, `lon` | ensemble clima + CV geo + ML (breakdown em `detalhes`) |
| storms | GET | `/api/storms/detector-status` | — | status YOLO |
| storms | GET | `/api/storms/recent` | `hours` | lista alertas recentes |
| storms | POST | `/api/storms/detect-sample` | — | inferência em imagem demo |
| map | GET | `/api/map/overlay` | `bbox` (s,w,n,e) | GeoJSON alertas no mapa |
| ml | GET | `/api/ml/agricultural-risk` | `temperatura`, `umidade`, `precipitacao`, `vento_kmh` | calculadora ML |
| iot | GET | `/api/iot/readings/latest` | `hours` | leituras ESP32 |
| nasa | GET | `/api/nasa/capturas` | `limite` | galeria de capturas |

### Modos de operação

| Variável | Default | Efeito no BFF |
|----------|---------|---------------|
| `DEMO_MODE` | `true` | fallbacks JSON quando backend indisponível |
| `DYNAMODB_USE_MOCK` | `true` | alertas/IoT em `data/demo/*.json` |
| `BFF_INPROCESS` | `false` (dev) | BFF chama FastAPI via TestClient em vez de HTTP |

### INMET BDMEP + pipeline ML agrícola

| Etapa | Script / serviço | Saída |
|-------|------------------|-------|
| Download estações | `scripts/fetch_inmet_bdmep.py` | `data/weather/inmet/training_cache.csv` |
| Treino + AG limiares | `scripts/build_agri_pipeline.py` | `models/agri_risk_*.pkl`, `agri_risk_thresholds.json` |
| Otimização GA (offline) | `scripts/optimize_agri_thresholds.py` | limiares em `agri_threshold_ga.py` |
| Inferência runtime | `AgriRiskModel` + `RiskAssessmentService` | `/risk/forecast`, `/api/risk/forecast` |

CI usa `make build-agri-ci` (`--skip-ga`) para validar artefatos sem rodar DEAP.

### NASA GOES (captura + CV)

| Etapa | Comando / módulo | Destino |
|-------|------------------|---------|
| Captura Playwright | `make nasa-capture` | `data/nasa_captures/` (79 PNG) |
| Conversão YOLO v2 | `scripts/goes_pipeline/04_nasa_to_yolo.py` | `data/model-dataset/` |
| Auditoria labels | `scripts/goes_pipeline/06_audit_labels.py --strict` | gate antes do treino |
| Retreino YOLO | `make train-yolo` → `src/yolo_training.py` | `src/models/weights/best.pt` |
| Upload S3 + Lambda | `make nasa-capture-aws` / `upload-s3` | S3 → `DetectStormUseCase` |
| Cron GitHub Actions | `.github/workflows/nasa-capture.yml` | captura a cada 6 h (UTC) |

Guia completo: [docs/YOLO-RETREINO.md](../../docs/YOLO-RETREINO.md)

### Windy (terceiro)

- Widget Windy embarcado em `maps/windy.js` — **não** passa pelo BFF
- API REST Windy não usada (plano free); apenas widget interativo

### Localização (client-side)

- `localStorage` key `dashboard-location`: `{ lat, lon }`
- `localStorage` key `dashboard-theme`: `dark` | `light`
- Evento `location:changed` dispara recarga de weather, risk, map overlay e Windy
