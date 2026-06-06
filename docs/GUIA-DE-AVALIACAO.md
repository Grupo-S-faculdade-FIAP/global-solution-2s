## Como usar o guia

Nosso grupo copiou as seções **"A solução poderá abordar temas como"** e **"O que esperamos da resposta"** da GS 2026.1 e marcou cada item coberto pela solução, com responsável e evidência no repositório.

> **Cognição / “serviços cognitivos”:** a camada cognitiva é composta pelos **modelos próprios** (YOLOv5, LightGBM, ensemble de risco, AG de limiares) e pelas **APIs REST** que expõem inferência e recomendações — executados na **AWS Lambda** junto ao pipeline serverless.

---

## A solução poderá abordar temas como

- [x] Sistemas inteligentes de monitoramento climático utilizando dados espaciais;
  - **Evidência:** capturas NASA GOES, Open-Meteo, Windy, mapas Leaflet — Lucas / Carol
- [x] Aplicações de visão computacional para análise de imagens orbitais;
  - **Evidência:** YOLOv5 + `DetectStormUseCase` + pipeline NASA v2 — Lucas
- [x] Soluções com redes neurais para previsão de eventos, clima ou produção agrícola;
  - **Evidência:** YOLO (detecção) + `AgriRiskModel` LightGBM + `/risk/forecast` — Lucas
- [x] Plataformas cognitivas para análise de grandes volumes de dados espaciais;
  - **Evidência:** dashboard + BFF `/api/*` + analytics (`/alerts/*`) + persistência DynamoDB sobre capturas e alertas — Carol / Lucas
- [x] Sistemas autônomos e sensores inteligentes para ambientes extremos;
  - **Evidência:** ESP32 + DHT22 com telemetria remota (`POST /iot/readings`) — Rodrigo *(MVP campo; não é robô autônomo)*
- [x] Aplicações em nuvem integradas a dados de satélite;
  - **Evidência:** S3 → Lambda → YOLO → DynamoDB/SNS — Lucas / Tiago
- [x] Soluções com AWS, Lambda, APIs e serviços cognitivos;
  - **Evidência:** Lambda serverless executa inferência YOLO e ML; APIs FastAPI expõem predição e recomendações cognitivas — Lucas / Tiago
- [x] Plataformas de recomendação e análise preditiva;
  - **Evidência:** `RiskAssessmentService` (ensemble clima + CV + ML) + textos de recomendação LOW/MEDIUM/HIGH — Lucas
- [x] Sistemas de detecção, classificação e segmentação de objetos;
  - **Evidência:** YOLO bounding boxes em nuvens convectivas — Lucas
- [x] Aplicações de IoT e ESP32 para monitoramento remoto;
  - **Evidência:** `src/iot/firmware.cpp`, seção IoT no dashboard — Rodrigo
- [x] Soluções sustentáveis e inteligentes inspiradas na exploração espacial;
  - **Evidência:** reuso de dados orbitais (NASA) para decisão agrícola e prevenção no solo — equipe

---

## O que esperamos da resposta

- [x] Aplicabilidade e clareza na resolução do problema proposto;
  - **Lucas** — README.md (`README.md`, `docs/RPI.md`)
  - **Enzo** — vídeo de 5 minutos *(pendente gravação)*
- [x] Uso criativo e coerente de *Inteligência Artificial*, *computação em nuvem* e *análise de dados*;
  - **Lucas** — *IA:* YOLO para padrões de nuvens chuvosas em imagens de satélite (NASA GOES)
  - **Lucas / Tiago** — *Cloud:* AWS Lambda, S3 trigger, SNS, DynamoDB
  - **Caroline** — *Análise de dados:* gráficos de alertas por dia da semana, hora, heatmap e tendência 30 dias
- [x] Demonstração de habilidades técnicas desenvolvidas ao longo do curso;
  - **Evidência:** `make demo`, ~220+ testes, CI 82% cobertura, E2E Playwright — Tiago / equipe
- [x] Integração entre *Machine Learning*, *visão computacional*, *sensores*, automação ou aplicações cognitivas;
  - **Lucas** — *ML:* treino YOLO + `AgriRiskModel` + ensemble em `RiskAssessmentService`
  - **Lucas** — *Visão computacional:* inferência YOLO local e na Lambda
  - **Rodrigo** — *Sensores:* ESP32 + DHT22 → API → dashboard
  - **Lucas / Caroline** — *Aplicações cognitivas:* APIs de predição, recomendação e analytics integradas ao dashboard
- [x] Aplicação prática de conceitos vistos em aula (redes neurais, YOLO, pipelines, AWS, serverless, ESP32, APIs cognitivas, SQL/NoSQL, análise em tempo real);
  - **Lucas** — *YOLO:* treino + `best.pt` + inferência no dashboard
  - **Lucas** — *Pipeline de dados:* captura NASA, rotulagem v2, treino
  - **Lucas / Tiago** — *AWS serverless:* S3 → Lambda → DynamoDB + SNS
  - **Rodrigo** — *ESP32:* firmware e integração HTTP
  - **Lucas** — *NoSQL:* DynamoDB (alertas + IoT) e mock JSON local
  - **Lucas / Caroline** — *APIs cognitivas:* `/risk/forecast`, `/ml/predict/agricultural-risk`, `/cv/detect/storm`, recomendações textuais
  - **Lucas** — *Serviços cognitivos:* camada de IA própria (YOLO + ML + AG limiares) hospedada na AWS
  - **Caroline** — *Análise em tempo real:* dashboard consome BFF `/api/*` com clima, alertas e risco
- [x] Planejamento e documentação organizada da solução;
  - **Lucas** — README, `docs/RPI.md`, `docs/PDF-ENTREGA-ESQUELETO.md`, `.specs/`
- [ ] Comunicação visual clara e apresentação estruturada;
  - **Enzo** — vídeo de 5 minutos *(pendente)*
- [x] Trabalho colaborativo e interdisciplinar.

### Integrantes

| Integrante | Contribuição principal |
|------------|------------------------|
| **Enzo França Sader** | Vídeo demonstrativo (≤ 5 min) |
| **Caroline de Castro Corrêa** | Dashboard, analytics, gráficos, code review |
| **Rodrigo Dias Figueiroa** | ESP32, firmware, integração IoT |
| **Lucas Hideki Oliveira Koyama** | YOLO, pipeline NASA, ML, AWS, README |
| **Tiago Lindgren Curi** | CI/CD OIDC, review AWS, infraestrutura |

---

## Testar alertas por e-mail (SNS) — pelo dashboard

1. Abra `make demo` → http://127.0.0.1:8000 (ou a URL da API na AWS).
2. Role até a seção **Alertas por e-mail (AWS SNS)** (atalho na nav: **E-mail SNS**).
3. Se o badge mostrar **SNS ativo**, informe seu e-mail e clique em **Receber alertas por e-mail**.
4. Abra a caixa de entrada e clique em **Confirm subscription** no e-mail da Amazon SNS.
5. Na seção **Detecção de tempestades**, clique em **Simular alerta** — o alerta aparece no dashboard e um e-mail é enviado aos inscritos confirmados.

> **Ambiente local sem AWS:** o badge mostra **SNS indisponível**; a simulação de alerta no dashboard continua funcionando, mas o e-mail só é enviado com `SNS_TOPIC_ARN` configurado na Lambda.

Especificação: `.specs/features/sns-dashboard/spec.md`
