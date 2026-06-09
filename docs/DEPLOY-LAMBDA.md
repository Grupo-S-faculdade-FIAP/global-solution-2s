# Deploy da Lambda `gs2-api` — passo a passo

Guia para o time republicar a API na AWS após mudanças no backend.

**Deploy automatizado:** merge na `main` dispara [CI/CD via GitHub Actions](CI-CD.md). Use este guia como fallback manual.

**Referência de infraestrutura:** [AWS-STATE.md](https://github.com/Grupo-S-faculdade-FIAP/global-solution-2s/wiki/AWS%E2%80%90STATE) (ARNs, armadilhas, permissões).

---

## Pré-requisitos

| Ferramenta | Uso |
|------------|-----|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Build e push da imagem |
| [AWS CLI v1/v2](https://docs.aws.amazon.com/cli/) | Login ECR, `update-function-code`, testes |
| Credenciais AWS | Perfil com acesso a ECR + Lambda (`gs2-dev` ou equivalente) |

Região do projeto: **`us-east-1`**.

```powershell
aws configure list   # conferir região e credenciais
```

---

## O que entra (e o que não entra) no deploy

A Lambda roda a **imagem Docker** definida em `src/Dockerfile`. Só o código copiado para a imagem é publicado:

| Entra no deploy | Não entra no deploy |
|-----------------|---------------------|
| `src/app/**` (FastAPI, routers, `main.py`) | `src/app/cron/capture_nasa_data.py` (script local + Playwright — não na imagem Lambda) |
| Dependências de `src/requirements-lambda.txt` + layers do Dockerfile | `src/dashboard/`, notebooks, scripts de treino |
| Handler: `app.main.handler` | Upload manual de `.env` — variáveis vão no console/CLI da Lambda |

Após alterar apenas scripts de captura NASA (`capture_nasa_data.py`) ou treino ML local, **não** é necessário redeploy da Lambda. Após alterar `cv.py`, `risk_assessment.py`, `main.py`, `config.py`, etc., **sim**.

**Artefatos ML (fora da imagem Lambda):** modelos em `models/` na raiz (`agri_risk_*.pkl`, `agri_risk_thresholds.json`) e pesos YOLO em `s3://satellite-images-gs2/models/best.pt` — atualizar S3 após retreino, sem rebuild se só os pesos mudaram.

---

## Redeploy após mudança de código

Execute na pasta **`src/`** do repositório.

### 1. Build da imagem

```powershell
cd src
docker build -t gs2-api:latest .
```

A primeira build pode demorar vários minutos (torch, OpenCV, YOLOv5).

### 2. Tag para o ECR

**Obrigatório após cada build novo.** Sem este passo, o `push` pode enviar uma imagem antiga.

```powershell
docker tag gs2-api:latest 544785076353.dkr.ecr.us-east-1.amazonaws.com/gs2-api:latest
```

### 3. Login no ECR

Uma vez por sessão de terminal:

```powershell
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 544785076353.dkr.ecr.us-east-1.amazonaws.com
```

### 4. Push da imagem

```powershell
docker push 544785076353.dkr.ecr.us-east-1.amazonaws.com/gs2-api:latest
```

O primeiro push é grande (~600 MB); pushes seguintes costumam ser bem mais rápidos (cache de layers).

### 5. Atualizar a função Lambda

```powershell
aws lambda update-function-code `
  --function-name gs2-api `
  --image-uri 544785076353.dkr.ecr.us-east-1.amazonaws.com/gs2-api:latest `
  --region us-east-1
```

### 6. Aguardar status Active

```powershell
aws lambda get-function --function-name gs2-api --region us-east-1 `
  --query "Configuration.{State:State,LastUpdateStatus:LastUpdateStatus,LastModified:LastModified}"
```

Repita até `State` = `Active` e `LastUpdateStatus` = `Successful`.

### 7. Teste de sanidade (HTTP)

```powershell
Invoke-RestMethod -Uri "https://qqnjq8qsmh.execute-api.us-east-1.amazonaws.com/health"
```

Resposta esperada: `status` = `ok`.

### 8. Teste do pipeline S3 → Lambda (opcional)

Na **raiz** do repositório (ajuste o caminho da imagem se necessário):

para enviar uma imagem especifica
```powershell
aws s3 cp data/model-dataset/images/test/test-storm.jpg `
  s3://satellite-images-gs2/screenshots/test-storm.jpg `
  --region us-east-1 `
  --content-type "image/jpeg"
```

ou

para captura NASA local (não dispara Lambda até upload JPG no S3):
```powershell
make nasa-capture-aws
# ou: cd src && python -m app.cron.capture_nasa_data --upload-cv-jpg
```

O trigger do S3 só reage a arquivos **`.jpg`** no bucket. Na primeira invocação (cold start + download do modelo) pode levar **60–90 s**.

Ver logs:

```powershell
aws logs filter-log-events `
  --log-group-name '/aws/lambda/gs2-api' `
  --region us-east-1 `
  --limit 20
```

---

## Permissões IAM — SNS (inscrição + alertas)

A role de execução da Lambda `gs2-api` precisa de **`sns:Publish`**, **`sns:Subscribe`** e **`sns:GetTopicAttributes`** no tópico `rain-alerts`.

Policy de referência: [`docs/iam/lambda-execution-sns-policy.json`](iam/lambda-execution-sns-policy.json)

```powershell
# Anexar inline policy à role da Lambda (ajuste o nome da role se diferente)
aws iam put-role-policy `
  --role-name gs2-lambda-role `
  --policy-name gs2-sns-storm-alerts `
  --policy-document file://docs/iam/lambda-execution-sns-policy.json
```

Sem `sns:Subscribe`, o dashboard retorna erro ao inscrever e-mail. Sem `sns:Publish`, alertas são gravados no DynamoDB mas o e-mail não é enviado.

---

## Permissões IAM — DynamoDB `sns_rate_limits`

Limite diário por e-mail (`SNS_MAX_ALERTS_PER_EMAIL_DAY`) e cooldown regional (`SNS_REGION_COOLDOWN_MINUTES`) persistem na tabela **`sns_rate_limits`** (PK `pk`, TTL em `ttl`).

Policy de referência: [`docs/iam/lambda-execution-dynamodb-sns-rate-limits-policy.json`](iam/lambda-execution-dynamodb-sns-rate-limits-policy.json)

```powershell
aws iam put-role-policy `
  --role-name gs2-lambda-role `
  --policy-name gs2-dynamodb-sns-rate-limits `
  --policy-document file://docs/iam/lambda-execution-dynamodb-sns-rate-limits-policy.json
```

O workflow `.github/workflows/deploy-lambda.yml` cria a tabela automaticamente (se ainda não existir) e habilita TTL. A role do GitHub Actions precisa de `dynamodb:CreateTable` — ver [`docs/iam/github-actions-gs2-deploy-policy.json`](iam/github-actions-gs2-deploy-policy.json).

Sem `dynamodb:GetItem`/`UpdateItem` na Lambda, o limite por pessoa e o cooldown regional **não funcionam** em produção (contadores falham silenciosamente).

---

## Atualizar só variáveis de ambiente (sem rebuild)

Use quando mudou configuração, mas **não** mudou código em `src/app/`:

```powershell
aws lambda update-function-configuration `
  --function-name gs2-api `
  --region us-east-1 `
  --environment "Variables={ENVIRONMENT=production,S3_BUCKET_IMAGES=satellite-images-gs2,DYNAMODB_TABLE_ALERTS=alerts,DYNAMODB_TABLE_SNS_RATE_LIMIT=sns_rate_limits,DYNAMODB_USE_MOCK=false,SNS_TOPIC_ARN=arn:aws:sns:us-east-1:544785076353:rain-alerts,SNS_ENABLED=true,SNS_ALERT_SUBJECT=Rain Alert — Storm Detected,SNS_MAX_ALERTS_PER_EMAIL_DAY=3,SNS_REGION_COOLDOWN_MINUTES=60}"
```

---

## Conferir o que está publicado na AWS

| Objetivo | Comando |
|----------|---------|
| Estado da função | `aws lambda get-function --function-name gs2-api --region us-east-1` |
| Env vars | `aws lambda get-function-configuration --function-name gs2-api --region us-east-1 --query Environment` |
| URI da imagem em uso | `aws lambda get-function --function-name gs2-api --region us-east-1 --query "Code.ImageUri"` |
| Logs recentes | `aws logs filter-log-events --log-group-name '/aws/lambda/gs2-api' --region us-east-1 --limit 20` |

No console AWS: **Lambda → Functions → gs2-api → Code / Monitor**.

---

## Checklist rápido

```
[ ] Código alterado em src/app/ (ou Dockerfile / requirements-lambda.txt)
[ ] docker build -t gs2-api:latest .     (dentro de src/)
[ ] docker tag ... ECR ...:latest        ← não pular
[ ] aws ecr get-login-password + docker login
[ ] docker push ...:latest
[ ] aws lambda update-function-code ...
[ ] State = Active / LastUpdateStatus = Successful
[ ] GET /health OK
[ ] (opcional) upload .jpg no S3 e verificar logs/alertas/DynamoDB/SNS
```

---

## Problemas comuns

| Sintoma | O que verificar |
|---------|-----------------|
| Lambda com código antigo após deploy | Fez `docker tag` depois do `build`? |
| `docker push` negado | Login ECR expirado — repetir passo 3 |
| `AccessDenied` no push/update | Credenciais do `gs2-dev` e policy `gs2-policy` |
| `/health` falha após recriar a Lambda | Permissões API Gateway + `create-deployment` — ver [AWS-STATE.md](https://github.com/Grupo-S-faculdade-FIAP/global-solution-2s/wiki/AWS%E2%80%90STATE) |
| S3 não dispara a Lambda | Objeto deve ser `.jpg`; permissão `lambda:InvokeFunction` do S3 |
| Cold start muito lento | Normal na 1ª execução (~60–90 s); modelo em `s3://satellite-images-gs2/models/best.pt` |

**PowerShell (Windows):** use `;` para encadear comandos, não `&&`. ARNs com `$` em aspas simples (`'...'`).

---

