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

## 📜 Descrição

O **GS2** é uma plataforma de monitoramento climático inteligente que combina visão computacional (YOLOv5), computação em nuvem (AWS) e sensores IoT (ESP32) para detectar padrões de nuvens chuvosas em imagens de satélite e gerar alertas de chuva em tempo real.

O projeto endereça a falta de sistemas acessíveis que integrem imagens de satélite, inteligência artificial e sensores de campo para antecipar eventos climáticos com impacto direto na agricultura e no cotidiano — conectando dados orbitais a ações práticas no solo.

**Principais componentes da solução:**

- **Módulo Computer Vision (CV):** pipeline de análise de imagens de satélite (Windy.com) com modelo YOLOv5 treinado para detectar padrões de nuvens chuvosas. As imagens são enviadas manualmente ao S3, que aciona automaticamente o processamento via Lambda;
- **Módulo Cloud/Backend:** API REST construída com FastAPI, hospedada na AWS (Lambda serverless para processamento + SNS para envio de alertas de chuva em tempo real). O fluxo é iniciado pelo upload manual de uma imagem ao bucket S3.
- **Módulo IoT:** ESP32 com sensores de umidade do solo para monitoramento remoto de campo, com dados enviados para a nuvem via HTTP.
- **Módulo Análise de Dados:** armazenamento dos alertas em banco SQL/NoSQL (dia e horário) com visualização em gráficos de barras para identificação de padrões recorrentes de chuva por dia da semana e faixa de horário.

- ## 💡 Módulo IoT – Desenvolvimento por Rodrigo Dias Figueiroa

Este módulo foi desenvolvido para realizar a coleta de dados de temperatura e umidade utilizando o sensor DHT22 conectado ao ESP32.  
Os dados são enviados para a nuvem via API Gateway (AWS Lambda + DynamoDB), integrando o monitoramento de campo ao sistema de alertas climáticos.

### 🔧 Funcionalidades implementadas
- Conexão Wi-Fi automática com verificação de status.
- Leitura de temperatura e umidade via sensor DHT22.
- Consulta à API OpenWeather para obter o clima atual da cidade.
- Envio dos dados para o banco DynamoDB através da API Gateway.
- Exibição dos dados e status no monitor serial.

### 📂 Estrutura do código
O código está localizado em:


A solução foi desenvolvida como projeto Global Solution da Graduação ON em Inteligência Artificial da FIAP.

---

## 📁 Estrutura de pastas

Dentre os arquivos e pastas presentes na raiz do projeto, definem-se:

- **`docs/`**: Documentação textual do projeto — como: brainstorm, diagramas de arquitetura, desenhos de fluxo, prints, storyboard, estratégia de IA, especificações de hardware (ESP32/Wokwi), atas de reunião e decisões técnicas.
  - setup da AWS: https://github.com/Grupo-S-faculdade-FIAP/global-solution-2s/wiki/AWS%E2%80%90STATE
  - **Deploy da Lambda:** [docs/DEPLOY-LAMBDA.md](docs/DEPLOY-LAMBDA.md)
  - **CI/CD (GitHub Actions + OIDC):** [docs/CI-CD.md](docs/CI-CD.md)

- **`src/`**: Todo o código-fonte desenvolvido — API FastAPI (routers de CV, IoT e Dashboard), scripts de treinamento YOLO, notebooks de exploração e análise de dados, código para ESP32 e modelos serializados.

- **`data/`**: Dados utilizados no projeto — amostras de imagens de satélite (Windy.com), datasets de treino/validação do modelo YOLO (imagens rotuladas de nuvens chuvosas) e registros de alertas para análise posterior.

- **`assets/`**: Imagens e recursos estáticos utilizados na documentação (logo FIAP, etc.).

- **`README.md`**: Arquivo que serve como guia e explicação geral sobre o projeto (o mesmo que você está lendo agora).

---

## 📎 Links e Observações

- **Repositório GitHub:** https://github.com/Grupo-S-faculdade-FIAP/global-solution-2s
- **Vídeo de demonstração (5min):** *(link a ser adicionado após gravação)*
- **Dashboard (Streamlit):** *(link a ser adicionado após deploy)* — **demo local:** http://127.0.0.1:8000 (`make demo`; tema claro/escuro na topbar)
- **Dashboard (AWS):** https://qqnjq8qsmh.execute-api.us-east-1.amazonaws.com/ (`MOUNT_DASHBOARD=false` na Lambda)
- **API Backend (AWS):** https://qqnjq8qsmh.execute-api.us-east-1.amazonaws.com

**Decisões técnicas relevantes:**
- YOLOv5 foi escolhido para detecção de padrões de nuvens chuvosas por ser estado da arte em detecção de objetos, com suporte a pipelines customizados de rotulagem e treino.
- AWS Lambda processa as imagens de satélite de forma serverless (acionado por S3 trigger); AWS SNS dispara as notificações de alerta de chuva. O upload manual de screenshots do Windy.com para o S3 inicia todo o pipeline.
- O banco de dados SQL/NoSQL armazena dia e horário de cada alerta, alimentando a análise de padrões de recorrência de chuva.
- Config de segredos via `pydantic-settings` + `.env` — nenhum segredo hard-coded no código.

**Observações gerais:**
- Este projeto foi desenvolvido no contexto da Global Solution da FIAP (Graduação ON em IA)

### Status de Execução (Caroline e Lucas) — 2026-06-04

Evidências objetivas aplicadas no projeto:

- Caroline (Análise de dados):
  - Gráficos de alertas por dia da semana e horário no dashboard agora consomem agregação real via API (`/alerts/weekly` e `/alerts/hourly`) com dados do DynamoDB, mantendo fallback local para demo sem nuvem.
- Lucas (YOLO + pipeline de dados):
  - Captura NASA incremental executada com sucesso (+3 imagens no dia).
  - Conversão NASA -> YOLO executada em 36 imagens.
  - Dataset de treino atualizado para 46 imagens e 46 labels.
  - Retreino smoke (1 época) executado com sucesso e `best.pt` atualizado em `src/models/weights/best.pt`.

Números atuais verificados:

- `data/nasa_captures`: 36 imagens PNG
- `data/model-dataset/images/train`: 46 imagens
- `data/model-dataset/labels/train`: 46 labels

Trilha YOLO NASA (concluída):

1. `data/nasa_captures`: 90 imagens
2. Dataset só NASA (`--limiar 200 --area 600`): mAP@0.5 ≈ **0,55**
3. Endpoints: `GET /storms/recent`, `GET /map/overlay` (DynamoDB `storm_alerts`)

**Demo local (API + dashboard — uma porta):**

```bash
make demo
# Abra http://127.0.0.1:8000
```

**Dashboard produtor:** painel HTML em `/` com tema **claro/escuro** (botão na topbar; preferência salva em `localStorage`). Gráficos, heatmap e mapas Leaflet acompanham o tema. Detalhes e checklist de validação: [docs/RPI.md](docs/RPI.md) §7.2.

**Alertas / DynamoDB (enquanto AWS não estiver pronta):** por padrão `DYNAMODB_USE_MOCK=true` — dados em `data/demo/storm_alerts.json` (seed automático + `POST /alerts/simulate`). Quando a AWS estiver ok: `DYNAMODB_USE_MOCK=false` no `.env`.

Checklist de entrega: `.specs/project/CHECKLIST_ENTREGA.md`

---

## 🔧 Como executar o código

### Pré-requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) ou `pip`
- Pesos do modelo em `src/models/weights/best.pt`
- Imagem de teste em `data/model-dataset/images/test/test-storm.png` (ou ajustar o caminho no script)
- Para a API local: arquivo `.env` (copiar `src/.env.example`)
- Para o teste na AWS: [AWS CLI](https://docs.aws.amazon.com/cli/) configurado (`aws configure`) com credenciais que tenham acesso ao bucket `satellite-images-gs2` e leitura em CloudWatch/DynamoDB

### Instalação

```bash
git clone git@github.com:Grupo-S-faculdade-FIAP/global-solution-2s.git
cd global-solution-2s/src

pip install -r requirements.txt
# ou: make install

cp .env.example .env   # apenas se for subir a API local
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

**5. (Opcional) E-mail SNS** — confirme a inscrição no tópico `rain-alerts`. Sem confirmação, o alerta é gravado no DynamoDB mas o e-mail não chega.

**Sanidade da API na nuvem:**

```bash
curl https://qqnjq8qsmh.execute-api.us-east-1.amazonaws.com/health
```

---
