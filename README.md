# FIAP - Faculdade de Informática e Administração Paulista

<p align="center">
<a href="https://www.fiap.com.br/">
  <img src="assets/logo-fiap.png" 
       alt="FIAP - Faculdade de Informática e Administração Paulista" 
       width="40%">
</a>
</p>

<br>

# global-solution-2s

## Grupo GS2

## 👨‍🎓 Integrantes:
- <a href="https://github.com/carolineccorrea">Caroline de Castro Corrêa</a>
- <a href="https://github.com/figueiroa-fiap">Rodrigo Dias Figueiroa</a>
- <a href="https://github.com/EnzF">Enzo França Sader</a>
- <a href="https://github.com/lucasKoyama">Lucas Hideki Oliveira Koyama</a>
- <a href="https://github.com/kyber-me">Tiago Lindgren Curi</a>

## 👩‍🏫 Professores:
### Tutor(a)
- <a href="https://github.com/SabrinaOtoni">Sabrina Otoni</a>
### Coordenador(a)
- <a href="https://www.linkedin.com/in/andregodoichiovato/">Andre Godoi</a>

---

## 📋 Licença

Este projeto está licenciado sob [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE) — mesmo modelo do [template FIAP TIAO-2026](https://github.com/CaiqueFiap-2026/TEMPLATE-TIAO-2026).

---

## 📜 Descrição

O **GS2** é uma plataforma de inteligência ambiental e agrícola que combina visão computacional (YOLOv5), machine learning, computação em nuvem (AWS) e sensores IoT (ESP32) para detectar padrões de nuvens convectivas em imagens de satélite, prever risco agrícola e gerar alertas acionáveis.

O projeto endereça a falta de sistemas acessíveis que integrem imagens orbitais, IA e sensores de campo para antecipar eventos climáticos com impacto direto na agricultura — conectando dados espaciais a decisões no solo.

**Principais componentes da solução:**

- **Módulo Computer Vision (CV):** captura **NASA GOES** (Playwright), rotulagem pipeline v2 e modelo **YOLOv5** (`best.pt`) para detectar nuvens convectivas. Upload `.jpg` no S3 dispara inferência na **Lambda** (`DetectStormUseCase`);
- **Módulo ML / Risco agrícola:** `AgriRiskModel` treinado com **INMET BDMEP** + contexto FAOSTAT; limiares otimizados por algoritmo genético (DEAP); **RiskAssessmentService** combina clima (Open-Meteo), sinal CV geo-localizado e ML em `/risk/forecast`;
- **Módulo Cloud/Backend:** API **FastAPI** + BFF `/api/*`, deploy **AWS Lambda** (Mangum), **DynamoDB**, **SNS** para alertas, **API Gateway**;
- **Módulo IoT:** **ESP32** + sensor **DHT22** (temperatura e umidade do ar) com envio HTTP para `POST /iot/readings` e exibição no dashboard;
- **Módulo Análise de Dados / Dashboard:** analytics de alertas (`/alerts/weekly`, heatmap, tendência), mapas **Leaflet**, radar **Windy** (widget), tema claro/escuro, seção ML com breakdown do ensemble.

### Módulo IoT — Rodrigo Dias Figueiroa

Coleta de temperatura e umidade via sensor **DHT22** no ESP32, com envio para a API GS2 (`POST /iot/readings`) e persistência em DynamoDB (ou mock local).

**Funcionalidades:** Wi-Fi automático, leitura DHT22, envio HTTP para API Gateway/Lambda, exibição no dashboard (seção IoT).

**Código e documentação:** [`src/iot/firmware.cpp`](src/iot/firmware.cpp) · [`src/iot/README.md`](src/iot/README.md)

---

## 📁 Estrutura de pastas

Dentre os arquivos e pastas presentes na raiz do projeto, definem-se:

- **`docs/`**: Documentação do projeto — índice em [docs/README.md](docs/README.md).
  - **Status técnico (RPI):** [docs/RPI.md](docs/RPI.md)
  - **Rubrica FIAP:** [docs/GUIA-DE-AVALIACAO.md](docs/GUIA-DE-AVALIACAO.md)
  - **Deploy Lambda:** [docs/DEPLOY-LAMBDA.md](docs/DEPLOY-LAMBDA.md)
  - **CI/CD (GitHub Actions + OIDC):** [docs/CI-CD.md](docs/CI-CD.md)
  - **Retreino YOLO / runbook GPU:** [docs/YOLO-RETREINO.md](docs/YOLO-RETREINO.md) · [docs/RUNBOOK-YOLO-70.md](docs/RUNBOOK-YOLO-70.md)
  - **Wiki AWS:** https://github.com/Grupo-S-faculdade-FIAP/global-solution-2s/wiki/AWS%E2%80%90STATE

- **`src/`**: Código-fonte — API FastAPI (Clean Architecture), dashboard Flask/HTML, firmware ESP32 (`src/iot/`), modelos YOLO (`src/models/`) e treino (`src/yolo_training.py`).

- **`scripts/`**: Pipelines operacionais — `goes_pipeline/` (NASA → YOLO), INMET/FAOSTAT (`build_agri_pipeline.py`), smoke AWS (`smoke_aws_e2e.py`).

- **`data/`**: Capturas NASA (`nasa_captures/`), dataset YOLO (`model-dataset/`), dados demo (`demo/`), cache INMET (`weather/inmet/`).

- **`assets/`**: Imagens e recursos estáticos utilizados na documentação (logo FIAP, etc.).

- **`README.md`**: Arquivo que serve como guia e explicação geral sobre o projeto (o mesmo que você está lendo agora).

---

## 📎 Links e Observações

- **Repositório GitHub:** https://github.com/Grupo-S-faculdade-FIAP/global-solution-2s
- **Vídeo de demonstração (5min):** *(link a ser adicionado após gravação)*
- **Dashboard (HTML/JS):** demo local em http://127.0.0.1:8000 (`make demo`; tema claro/escuro na topbar) · produção AWS abaixo
- **Dashboard (AWS):** https://qqnjq8qsmh.execute-api.us-east-1.amazonaws.com/ (`MOUNT_DASHBOARD=false` na Lambda)
- **API Backend (AWS):** https://qqnjq8qsmh.execute-api.us-east-1.amazonaws.com

**Decisões técnicas relevantes:**
- YOLOv5 para detecção de nuvens convectivas; dataset NASA GOES com pipeline de labels v2 (0 bbox fantasma).
- AWS Lambda processa imagens de satélite (S3 trigger → YOLO → DynamoDB + SNS). Windy é apenas **widget de radar** no frontend (plano free, sem REST API).
- Ensemble de risco: pesos dinâmicos clima + CV (raio 200 km) + ML; limiares em `models/agri_risk_thresholds.json`.
- O banco de dados **DynamoDB** (NoSQL) armazena alertas e leituras IoT, alimentando gráficos e mapas no dashboard.
- Config de segredos via `pydantic-settings` + `.env` — nenhum segredo hard-coded no código.

**Observações gerais:**
- Este projeto foi desenvolvido no contexto da Global Solution da FIAP (Graduação ON em IA)

### Status do projeto — 2026-06-06

| Área | Evidência |
|------|-----------|
| Testes unit/integration | **440 passed** (`make test`) |
| Cobertura CI | **~82%** (`make test-coverage`) |
| Testes E2E Playwright | **53** (`make test-e2e`) |
| Capturas NASA | 79 PNG em `data/nasa_captures` |
| Dataset YOLO train | 79 imagens + 79 labels (`data/model-dataset/`) |
| Pipeline labels | v2 — letterbox 640, 0 bbox fantasma; mAP@0.5 ≈ 0,14 (abaixo meta G1 70%) |
| Retreino YOLO | `make train-yolo` + [docs/YOLO-RETREINO.md](docs/YOLO-RETREINO.md) · runbook GPU: [docs/RUNBOOK-YOLO-70.md](docs/RUNBOOK-YOLO-70.md) |
| ML risco | INMET + AG limiares + ensemble geo-aware — `make build-agri` |
| IoT | ESP32 DHT22 + API + dashboard + 11 testes — firmware em `src/iot/firmware.cpp` |
| CI/CD | GitHub Actions + OIDC — [docs/CI-CD.md](docs/CI-CD.md) |
| Arquitetura | Clean Architecture — [docs/RPI.md](docs/RPI.md) |

**Demo local (API + dashboard — uma porta):**

```bash
make demo
# Abra http://127.0.0.1:8000
```

**Dashboard produtor:** painel HTML em `/` com tema **claro/escuro** (botão na topbar; preferência salva em `localStorage`). Gráficos, heatmap e mapas Leaflet acompanham o tema. Detalhes e checklist de validação: [docs/RPI.md](docs/RPI.md) §7.2.

**Alertas / DynamoDB:** alertas persistem na tabela AWS `alerts`. **IoT ESP32:** simulado por padrão (`IOT_USE_MOCK=true` no `.env`); defina `IOT_USE_MOCK=false` quando o hardware estiver enviando para DynamoDB `iot_readings`.

Documentação: [docs/README.md](docs/README.md) · Checklist: `.specs/project/CHECKLIST_ENTREGA.md` · PDF: [docs/PDF-ENTREGA-ESQUELETO.md](docs/PDF-ENTREGA-ESQUELETO.md)

### Comandos úteis

| Comando | Descrição |
|---------|-----------|
| `make install` | Dependências Python |
| `make demo` | API + dashboard em http://127.0.0.1:8000 |
| `make test` | 440 testes (excl. E2E) |
| `make test-coverage` | Testes + gate cobertura 82% |
| `make test-e2e` | 53 testes Playwright no dashboard |
| `make build-agri` | Pipeline INMET + treino ML risco |
| `make train-yolo` | Retreino YOLO (`--recall-focus`) |
| `make smoke-aws` | Smoke S3 → Lambda → DynamoDB |
| `make nasa-capture` | Captura NASA Worldview (Playwright) |

---

## 🔧 Como executar o código

### Pré-requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) ou `pip`
- Pesos do modelo em `src/models/weights/best.pt`
- Imagem de teste em `data/model-dataset/images/test/test-storm.png` (ou ajustar o caminho no script)
- Para a API local: copiar `.env.example` → `.env` na **raiz** do repositório
- Para o teste na AWS: [AWS CLI](https://docs.aws.amazon.com/cli/) configurado (`aws configure`) com credenciais que tenham acesso ao bucket `satellite-images-gs2` e leitura em CloudWatch/DynamoDB

### Instalação

```bash
git clone git@github.com:Grupo-S-faculdade-FIAP/global-solution-2s.git
cd global-solution-2s

make install
# ou: cd src && pip install -r requirements.txt

cp .env.example .env   # raiz do repo — ajustar se necessário
```

---

### 1. Detecção local (YOLOv5)

Script de referência: `src/models/stormdetector.py`. Carrega `best.pt`, roda inferência na imagem de teste e abre uma janela com as detecções.

**Dependências mínimas** (se não quiser instalar o `requirements.txt` completo):

```bash
pip install torch torchvision opencv-python numpy
```

> Use `opencv-python` (com GUI), não `opencv-python-headless`, para que `cv2.imshow` funcione no seu SO.

**Executar** (a partir de `src/`):

```bash
cd src
python models/stormdetector.py
```

O script usa por padrão:

| Item | Caminho |
|------|---------|
| Pesos | `src/models/weights/best.pt` |
| Imagem | `data/model-dataset/images/test/test-storm.png` |
| Confiança | `0.035` (mesmo valor usado na Lambda) |

Na primeira execução o PyTorch Hub baixa o repositório `ultralytics/yolov5` (requer internet). Saída esperada: lista de detecções no terminal e janela **Deteccao** com bounding boxes.

**Windows:** o script já aplica o patch `pathlib.PosixPath = pathlib.WindowsPath` para carregar checkpoints treinados no Windows.

---

**Produção (API Gateway):** `https://qqnjq8qsmh.execute-api.us-east-1.amazonaws.com/health`

---

### 3. Teste end-to-end na AWS (S3 → Lambda → SNS + DynamoDB)

Fluxo: upload de um `.jpg` no bucket dispara a Lambda `gs2-api`, que baixa a imagem e o modelo (`models/best.pt` no S3), roda o mesmo pipeline de CV e, se houver detecções, grava em DynamoDB e publica no SNS.

**Pré-requisito na AWS:** pesos em `s3://satellite-images-gs2/models/best.pt`.

**1. Enviar imagem de teste** (na raiz do repositório):

```bash
aws s3 cp data/model-dataset/images/test/test-storm.png \
  s3://satellite-images-gs2/screenshots/test-storm.jpg \
  --region us-east-1 \
  --content-type "image/jpeg"
```

O trigger do S3 só reage a arquivos **`.jpg`** no bucket — por isso o destino usa extensão `.jpg` mesmo sendo um PNG local.

**2. Aguardar o processamento** — na primeira execução (cold start + download do modelo) pode levar **~60–90 s**. Invocações seguintes no mesmo container são bem mais rápidas.

**3. Verificar logs** (PowerShell: use aspas simples no nome do log group):

```bash
aws logs describe-log-streams \
  --log-group-name '/aws/lambda/gs2-api' \
  --region us-east-1 \
  --order-by LastEventTime \
  --descending \
  --max-items 1

# Troque LOG_STREAM pelo valor retornado em logStreamName
aws logs filter-log-events \
  --log-group-name '/aws/lambda/gs2-api' \
  --log-stream-names 'LOG_STREAM' \
  --region us-east-1 \
  --filter-pattern 'ERROR'

aws logs filter-log-events \
  --log-group-name '/aws/lambda/gs2-api' \
  --log-stream-names 'LOG_STREAM' \
  --region us-east-1 \
  --filter-pattern 'REPORT'
```

Ausência de `ERROR` e linha `REPORT` com duração em dezenas de segundos indicam sucesso.

**4. Verificar alerta no DynamoDB:**

```bash
aws dynamodb scan \
  --table-name alerts \
  --region us-east-1 \
  --limit 5
```

Procure um item com `s3_key` = `screenshots/test-storm.jpg`, `alert_type` = `storm_detection` e `detection_count` > 0.

**5. E-mail SNS (pelo dashboard)** — na seção **Alertas por e-mail (AWS SNS)**, inscreva o e-mail e confirme o link enviado pela AWS. Depois use **Simular alerta** para receber o e-mail de teste. Ver `docs/GUIA-DE-AVALIACAO.md`.

**Sanidade da API na nuvem:**

```bash
curl https://qqnjq8qsmh.execute-api.us-east-1.amazonaws.com/health
```

---
