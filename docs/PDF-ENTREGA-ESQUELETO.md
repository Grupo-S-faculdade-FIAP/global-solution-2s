# PDF de Entrega — Esqueleto GS 2026.1

> **Como usar:** copie cada seção para Word/Google Docs/LaTeX e preencha os campos `[...]`.
> Exporte como **PDF único** para a plataforma FIAP.
> Código sempre em **texto** — nunca screenshot.
> Fonte técnica: `docs/RPI.md` v1.5 · Checklist: `.specs/features/gs-closure/tasks.md`

---

## Capa (página 1)

**Global Solution 2026.1 — FIAP Graduação ON em Inteligência Artificial**

### Integrantes

| Nome completo | E-mail |
|---------------|--------|
| Caroline de Castro Corrêa | castrocaroline11@gmail.com |
| Rodrigo Dias Figueiroa | rdfigueiroa@gmail.com |
| Enzo França Sader | efr4nca03@gmail.com |
| Lucas Hideki Oliveira Koyama | lucaskoyamahhh@gmail.com |
| Tiago Lindgren Curi | shopper.tiago@gmail.com |

**Tutor(a):** Sabrina Otoni  
**Coordenador(a):** Andre Godoi

<!-- Se concorrer ao pódio, descomente a linha abaixo: -->
<!-- **QUERO CONCORRER** -->

**Nome do produto:** [DEFINIR — decisão B3, ex.: GS2 Environmental Intelligence]

**Repositório:** https://github.com/Grupo-S-faculdade-FIAP/global-solution-2s

**Data:** [DD/MM/2026]

---

## 1. Introdução

### 1.1 Contexto — economia espacial e impacto na Terra

A exploração espacial deixou de ser apenas científica e passou a representar uma das maiores oportunidades tecnológicas da atualidade. Satélites monitoram o clima, auxiliam no agronegócio e produzem grandes volumes de dados utilizados por governos, empresas e centros de pesquisa.

A FIAP propõe a Global Solution 2026.1 conectando Inteligência Artificial ao universo da economia espacial. Nossa equipe responde à pergunta:

> **Como a Inteligência Artificial e as tecnologias digitais podem transformar a nova economia espacial e gerar impacto positivo na Terra?**

### 1.2 Problema

[Preencher 1 parágrafo — usar PROJECT.md]

Dados de satélite existem em abundância (NASA GOES, Open-Meteo), mas não são processados, correlacionados com sensores de campo e apresentados de forma integrada e acessível para produtores rurais e gestores de risco. A demora e a fragmentação impedem decisões preventivas ante eventos climáticos extremos.

### 1.3 Proposta de solução

[Preencher 1 parágrafo]

O **GS2** é uma plataforma de inteligência ambiental e agrícola que combina:

- **Visão computacional (YOLOv5)** em imagens de satélite para detectar padrões de nuvens convectivas;
- **Machine Learning** (LightGBM + otimização genética de limiares) para risco agrícola com dados INMET;
- **IoT (ESP32 + DHT22)** para temperatura e umidade em campo;
- **Computação em nuvem AWS** (S3, Lambda, DynamoDB, SNS) com CI/CD via GitHub Actions;
- **Dashboard web** unificado (clima, alertas, mapas, analytics e IoT) em uma única URL.

### 1.4 Objetivos (G1–G5)

| ID | Objetivo | Status |
|----|----------|--------|
| G1 | Detecção YOLO de tempestades em imagens de satélite | Concluído (MVP) — mAP@0.5 56,5%; P=73,5% em conf=0,55 |
| G2 | Previsão de risco agrícola (ML + INMET) | Concluído |
| G3 | Visualização climática em tempo real | Concluído |
| G4 | ESP32 → pipeline cloud | Concluído (MVP) |
| G5 | MVP documentado + vídeo | Este documento + vídeo anexo |

### 1.5 Público-alvo

Pesquisadores, produtores rurais, órgãos de monitoramento ambiental e gestores de risco no território brasileiro (v1).

---

## 2. Desenvolvimento

### 2.1 Arquitetura da solução

**Inserir diagrama** — exportar do mermaid em `docs/RPI.md` §3.1 ou usar ferramenta draw.io.

Fluxo resumido:

```
NASA GOES / S3 upload → YOLOv5 → DynamoDB + SNS
Open-Meteo → FastAPI → Dashboard
ESP32 → POST /iot/readings → DynamoDB → Dashboard
INMET → AgriRiskModel → /risk/forecast → Dashboard
```

### 2.2 Stack tecnológica

| Camada | Tecnologia |
|--------|------------|
| Backend | Python 3.11, FastAPI, Mangum (Lambda) |
| Frontend | Flask + Jinja, ES modules, Chart.js, Leaflet, Windy widget |
| CV | YOLOv5 (PyTorch Hub), OpenCV |
| ML | LightGBM, scikit-learn, DEAP (AG limiares) |
| Cloud | AWS Lambda, S3, DynamoDB, SNS, API Gateway |
| IoT | ESP32, DHT22, Arduino C++ |
| CI/CD | GitHub Actions + OIDC (sem access keys) |
| Testes | pytest (82% cobertura), Playwright E2E |

### 2.3 Integração entre disciplinas

> **Obrigatório para pódio (tarefa P4).** Preencher e manter alinhado com `docs/GUIA-DE-AVALIACAO.md`.

| Disciplina / conceito | Tecnologia aplicada | Módulo no projeto | Responsável |
|----------------------|---------------------|-------------------|-------------|
| Visão computacional | YOLOv5, pipeline NASA v2 | `DetectStormUseCase`, `storm_detector.py` | Lucas |
| Machine Learning | LightGBM, AG (DEAP), ensemble | `agri_risk_model.py`, `risk_assessment.py` | Lucas |
| Análise de dados | Gráficos, heatmap, analytics | `/alerts/*`, dashboard `sections/` | Caroline |
| Computação em nuvem | Lambda serverless, S3 trigger | `docs/DEPLOY-LAMBDA.md`, Lambda Docker | Lucas, Tiago |
| Banco NoSQL | DynamoDB time-series | `storm_alerts_store`, `iot_readings_store` | Lucas |
| IoT / sensores | ESP32 + DHT22 | `src/iot/firmware.cpp`, `/iot/readings` | Rodrigo |
| DevOps / automação | CI/CD OIDC, captura NASA cron | `.github/workflows/`, `capture_nasa_data.py` | Tiago |
| Apresentação | Vídeo + PDF | Este documento | Enzo, equipe |

### 2.4 Módulos implementados

#### 2.4.1 Visão computacional (YOLO)

- 1.602 capturas NASA GOES acumuladas (base v2: 79); dataset augmentado **1.361** train → tiled **3.045** train / **1.033** val;
- Pseudo-rótulos gerados por heurística OpenCV (`detect_storms`, limiar/área) — ver §2.4.5;
- Dataset YOLO v2 com **0 bbox fantasma** (audit gate);
- Pesos: `src/models/weights/best.pt` (~89 MB); produção: `s3://satellite-images-gs2/models/best.pt` (cold start Lambda);
- Inferência local (`stormdetector.py`) e na Lambda via `DetectStormUseCase`;
- Métricas v3 (`storm70-l-tiled`, YOLOv5l): mAP@0.5=**56,5%** (TTA 57,1%); conf=0,55 → P=**73,5%**, R=30,2%, mAP=50,4%.

**Inserir screenshot:** dashboard seção YOLO com detecção (não é código — permitido).

#### 2.4.2 Machine Learning — risco agrícola

- Treino com INMET BDMEP (43,8k registros, 5 estações);
- **Alvo proxy:** `score_continuo_normalizado(temp, umid, precip, vento)` — regra determinística das mesmas features de entrada (ver §2.4.5); R²≈0,95 mede ajuste à regra, não risco agrícola real;
- Limiares otimizados por algoritmo genético → `models/agri_risk_thresholds.json`;
- `RiskAssessmentService` combina clima (Open-Meteo) + CV geo-aware (raio 200 km) + ML com **pesos dinâmicos**;
- Dashboard (`sections/ml.js`) exibe breakdown clima / CV / ML na calculadora de risco;
- Endpoints: `/risk/forecast`, `/ml/predict/agricultural-risk`.

#### 2.4.3 Análise de dados e dashboard

- Analytics: `/alerts/weekly`, `/hourly`, `/daily`, `/heatmap`;
- Dashboard produtor: tema claro/escuro, mapas Leaflet + Windy, seção ML com breakdown;
- Demo: `make demo` → http://127.0.0.1:8000

**Inserir screenshots:** `docs/assets/dashboard-light.png`, `dashboard-dark.png` (tarefa B7).

#### 2.4.4 IoT ESP32

- Firmware: Wi-Fi, DHT22, POST HTTP para API;
- Persistência mock (`data/demo/iot_readings.json`) ou DynamoDB;
- Seção IoT no dashboard com leituras recentes.

#### 2.4.5 Geração de rótulos proxy (honestidade metodológica)

> **Obrigatório para avaliadores que leem o código.** Ambos os modelos treinam com alvos derivados de regras do próprio pipeline — válido para POC, não para validação científica independente.

| Modelo | Como o rótulo é gerado | Código | O que a métrica mede |
|--------|------------------------|--------|----------------------|
| **AgriRiskModel** | Score 0–1 = regra agrometeorológica sobre temp, umidade, precipitação e vento | `agri_risk_model.py` → `score_continuo_normalizado()` | R²≈0,95 = quão bem o regressor **memoriza a regra**, não previsão de safra/perda real |
| **YOLO storm** | Bboxes = regiões de pixels brilhantes acima de limiar/área mínima | `04_nasa_to_yolo.py` → `detect_storms()` | mAP/P = consistência com a **heurística OpenCV**, não anotação humana independente |

**Trade-off consciente:**

- **Pró:** POC integrada e demonstrável em prazo de GS (ensemble geo-aware, dashboard, Lambda serverless);
- **Contra:** métricas altas não implicam validação externa (produtividade agrícola, validação meteorológica humana);
- **Próximo passo (v2):** rótulos humanos para YOLO; alvo de ML com variável externa (ex.: yield FAOSTAT, eventos de perda).

**Frase sugerida para o corpo do PDF:**

> *"Os modelos ML e CV foram treinados com rótulos proxy gerados automaticamente pelo pipeline. O R²≈0,95 do regressor agrícola e a precisão YOLO medem consistência interna com essas regras — não acurácia preditiva em campo."*

#### 2.4.6 AWS e automação

- API Gateway: `https://qqnjq8qsmh.execute-api.us-east-1.amazonaws.com/`
- Pipeline: upload `.jpg` em S3 → Lambda → YOLO → DynamoDB + SNS;
- CI: pytest + 82% cobertura + E2E Playwright; CD na `main`.

**Inserir screenshot:** GitHub Actions job verde (tarefa BEY-03).

### 2.5 Trechos de código principais (TEXTO — não print)

> Copiar do repositório. Máximo ~40 linhas cada. Ajustar numeração ao exportar.

#### Trecho 1 — Pipeline de detecção (Use Case)

**Arquivo:** `src/app/application/cv/detect_storm.py`  
**Papel:** Orquestra download S3 → inferência YOLO → SNS → persistência DynamoDB.

```python
# src/app/application/cv/detect_storm.py — DetectStormUseCase.execute (trecho)
image_local = _TMP / pathlib.Path(key).name
s3 = boto3.client("s3", region_name=settings.AWS_REGION)
s3.download_file(bucket, key, str(image_local))

model_path = _ensure_model()
detections = _run_yolo_inference(image_local, model_path)

if detections:
    alert_id = _deterministic_alert_id(bucket, key)
    saved = self._persist(bucket, key, detections, alert_id)
    duplicate = bool(saved.get("_duplicate"))
    if not duplicate:
        message_id = publish_storm_alert(bucket, key, detections)
    alert_sent = True

return {
    "bucket": bucket,
    "key": key,
    "detections": detections,
    "alert_sent": alert_sent,
    "duplicate": duplicate,
    "sns_message_id": message_id,
}
```

#### Trecho 2 — Ensemble de risco agrícola

**Arquivo:** `src/app/services/risk_assessment.py` (ou `agri_risk_model.py`)  
**Papel:** Combina sinais de clima, CV e ML para score de risco.

```python
# src/app/services/risk_assessment.py — RiskAssessmentService.calculate_risk (trecho)
pesos = _effective_weights(coverage_factor)
score_final = (
    score_clima * pesos["clima"] +
    score_cv    * pesos["cv"] +
    score_ml    * pesos["ml_agricola"]
)
score_final = float(np.clip(score_final, 0.0, 1.0))
categoria   = _categoria(score_final)

detalhes["pesos"] = pesos
detalhes["components"] = {
    "clima": round(score_clima, 3),
    "cv": round(score_cv, 3),
    "ml_agricola": round(score_ml, 3),
}

return RiskScore(
    score=round(score_final, 3),
    category=categoria,
    recommendation=RECOMENDACOES[categoria],
    timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    detalhes=detalhes,
)
```

#### Trecho 3 — Recepção IoT

**Arquivo:** `src/app/routers/iot.py` ou trecho de `src/iot/firmware.cpp`  
**Papel:** ESP32 envia leitura; API persiste e expõe no dashboard.

```python
# src/app/routers/iot.py — POST /iot/readings
@router.post("/readings", status_code=201)
def receive_sensor_reading(
    body: SensorReading,
    repo: IoTReadingRepository = Depends(get_iot_repo),
) -> dict:
    item = repo.save(
        device_id=body.device_id,
        cidade=body.cidade,
        temperatura=body.temperatura,
        umidade=body.umidade,
    )
    return {
        "stored": True,
        "reading_id": item["reading_id"],
        "timestamp": item["timestamp"],
        "storage": "demo" if settings.IOT_USE_MOCK else "dynamodb",
    }
```

#### Trecho 4 (opcional) — Configuração e mock local

**Arquivo:** `src/app/container.py`  
**Papel:** Injeção de dependência — troca DynamoDB real ↔ JSON mock.

```python
# src/app/container.py — injeção mock ↔ DynamoDB
def get_storm_repo() -> StormAlertRepository:
    if settings.DYNAMODB_USE_MOCK:
        from app.infrastructure.persistence.json_storm_store import JsonStormAlertRepository
        return JsonStormAlertRepository()
    from app.infrastructure.aws.dynamodb_storm import DynamoDBStormAlertRepository
    return DynamoDBStormAlertRepository()

def get_iot_repo() -> IoTReadingRepository:
    if settings.IOT_USE_MOCK:
        from app.infrastructure.persistence.json_iot_store import JsonIoTReadingRepository
        return JsonIoTReadingRepository()
    from app.infrastructure.aws.dynamodb_iot import DynamoDBIoTReadingRepository
    return DynamoDBIoTReadingRepository()
```

### 2.6 Decisões técnicas relevantes

| Decisão | Rationale |
|---------|-----------|
| YOLOv5 via PyTorch Hub | Compatível com Lambda; documentação madura |
| Pipeline labels v2 (letterbox + máscara UI) | Elimina bboxes fantasma do v1 |
| DynamoDB + mock JSON | Demo local sem AWS; produção com `DYNAMODB_USE_MOCK=false` |
| Porta única :8000 | FastAPI monta Flask — UX simplificada para avaliador |
| Windy como widget (não REST) | Plano free não libera API REST completa |
| CI/CD OIDC | Sem access keys permanentes no repositório |
| AG (DEAP) para limiares ML | Otimização automática dos thresholds de risco |
| Rótulos proxy (ML + YOLO) | Alvos derivados de regras do pipeline — transparência no §2.4.5; trade-off POC vs validação externa |
| `best.pt` via S3 (gitignored) | Cold start Lambda baixa `models/best.pt`; artefato ~89 MB fora da imagem Docker |

Detalhes: `docs/RPI.md` §5 e `.specs/project/STATE.md`.

### 2.7 Como executar (instruções para o avaliador)

```bash
git clone git@github.com:Grupo-S-faculdade-FIAP/global-solution-2s.git
cd global-solution-2s
make install
cp .env.example .env
make demo
# Abrir http://127.0.0.1:8000
```

Testes: `make test-coverage` (gate 82%).

---

## 3. Resultados Esperados

### 3.1 Resultados técnicos

| Métrica | Valor | Observação |
|---------|-------|------------|
| Testes automatizados | **440** unit/integration + **53** E2E | `make test`, `make test-e2e` |
| Cobertura de código | **82,44%** | Gate no CI (`make test-coverage`) |
| Capturas NASA | 1.602 PNG acumulados | `data/nasa_captures/` (base v2: 79) |
| Dataset YOLO | 1.361 train (base) → 3.045 train tiled / 1.033 val | Augmentação + SAHI; 0 ghost |
| YOLO mAP@0.5 | **56,5%** (TTA 57,1%) | `storm70-l-tiled`; conf=0,55 → P=73,5% |
| ML R² CV | ≈ 0,95 | **Ajuste à regra proxy** — ver §2.4.5; não é acurácia preditiva real |
| INMET registros | 43,8k horários | 5 estações BDMEP |
| Pesos YOLO | ~89 MB | Local + `s3://satellite-images-gs2/models/best.pt` |
| Endpoints API | 20+ rotas REST + BFF `/api/*` | Ver `docs/RPI.md` §4.1 |

### 3.2 Resultados de negócio / impacto

- **Antecipação:** detecção de padrões convectivos em imagens orbitais antes do impacto no solo;
- **Decisão agrícola:** score de risco (seca, geada, produtividade) com dados reais INMET;
- **Campo:** correlação entre satélite, clima e sensores IoT em painel único;
- **Acessibilidade:** POC executável com um comando (`make demo`) para avaliação.

### 3.3 Cobertura da rubrica FIAP

Baseado em `docs/GUIA-DE-AVALIACAO.md`:

| Tema FIAP | Coberto? | Evidência |
|-----------|----------|-----------|
| Monitoramento climático com dados espaciais | Sim | NASA GOES + Open-Meteo + Windy |
| Visão computacional em imagens orbitais | Sim | YOLOv5 + pipeline v2 |
| Redes neurais para previsão clima/agro | Sim | YOLO + LightGBM + ensemble |
| Cloud + dados de satélite | Sim | S3 → Lambda |
| AWS, Lambda, APIs | Sim | API Gateway, DynamoDB, SNS |
| Análise preditiva | Sim | `/risk/forecast`, analytics alertas |
| Detecção/classificação de objetos | Sim | YOLO bounding boxes |
| IoT ESP32 | Sim | firmware + API + dashboard |
| Plataformas cognitivas big data espacial | Sim | Dashboard + BFF + analytics sobre capturas NASA e alertas DynamoDB |
| Serviços cognitivos / APIs cognitivas | Sim | YOLO + AgriRiskModel + ensemble + recomendações via APIs FastAPI na Lambda |

### 3.4 Limitações conhecidas (honestidade técnica)

- **Rótulos proxy (ML + YOLO):** ambos os modelos treinam com alvos derivados de regras/heurísticas do pipeline — R²≈0,95 e mAP/P medem consistência interna, não validação externa (§2.4.5);
- YOLO: trade-off precisão/recall em conf=0,55 (P=73,5%, R≈30%); rótulos proxy (§2.4.5);
- Demo local usa mock DynamoDB por padrão (`DYNAMODB_USE_MOCK=true` no `.env`);
- Cold start Lambda 60–90 s na primeira invocação (download `best.pt` do S3);
- Cobertura geográfica v1: Brasil;
- ESP32 demonstrado via simulação/Wokwi se hardware indisponível na gravação.

---

## 4. Conclusões

### 4.1 Síntese

[Preencher 1 parágrafo]

A GS2 demonstra que é possível conectar dados orbitais, visão computacional, machine learning, sensores IoT e computação serverless em uma POC integrada e executável. A plataforma transforma volumes de dados espaciais em inteligência acionável para o agronegócio e monitoramento ambiental.

### 4.2 Contribuições do grupo

| Integrante | Contribuição principal |
|------------|------------------------|
| Caroline | Dashboard, analytics, gráficos, code review |
| Rodrigo | ESP32, firmware, integração IoT |
| Enzo | Vídeo demonstrativo, comunicação visual |
| Lucas | YOLO, ML, AWS, pipeline NASA, README |
| Tiago | CI/CD, review AWS, infraestrutura |

### 4.3 Trabalho futuro (pós-GS)

- Mais capturas NASA + rótulos humanos (v2);
- DynamoDB real em produção (`mock off`);
- Alertas push/email em tempo real;
- Expansão da camada cognitiva com novos modelos ou fontes de dados espaciais;
- Cobertura América do Sul.

### 4.4 Agradecimentos

FIAP, tutor(a) Sabrina Otoni, coordenador Andre Godoi, APIs abertas (NASA, Open-Meteo, INMET).

---

## Anexos (dentro do mesmo PDF)

### A. Links obrigatórios

| Item | URL |
|------|-----|
| Repositório GitHub | https://github.com/Grupo-S-faculdade-FIAP/global-solution-2s |
| Licença | CC BY 4.0 — ver `LICENSE` na raiz do repositório |
| API produção (health) | https://qqnjq8qsmh.execute-api.us-east-1.amazonaws.com/health |
| **Vídeo demonstrativo (YouTube não listado)** | https://www.youtube.com/watch?v=W67760WVado |
| Wiki AWS (time) | https://github.com/Grupo-S-faculdade-FIAP/global-solution-2s/wiki |

### B. Referências internas

- `docs/RPI.md` — relatório técnico completo
- `docs/DEPLOY-LAMBDA.md` — deploy serverless
- `docs/CI-CD.md` — pipeline GitHub Actions
- `src/iot/README.md` — ESP32
- `.specs/features/gs-closure/tasks.md` — tarefas de entrega

---

## Checklist final antes do upload

- [ ] PDF único (não .zip)
- [ ] Nomes completos na 1ª página
- [ ] "QUERO CONCORRER" (se pódio)
- [ ] Código em texto, não screenshot
- [x] Link do vídeo no final
- [ ] Link do repositório no corpo
- [x] Vídeo ≤ 5 min, YouTube não listado
- [ ] `make demo` testado
