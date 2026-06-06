# Deployment Guide - Critical Fixes

Instruções para deployd as 11 correções críticas em produção com segurança.

---

## Pre-Deployment Checklist

- [ ] Todos os testes passam: `pytest tests/ -v`
- [ ] Linter passou: `pylint src/` ou `ruff check src/`
- [ ] Código foi revisado por outro dev
- [ ] Variáveis de ambiente documentadas
- [ ] Backup do banco de dados/config atual feito
- [ ] Rollback plan definido

---

## Environment Variables (Adicionar ao Lambda/EC2/ECS)

### Segurança AWS

```bash
# NÃO ADICIONE MAIS:
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...

# Em vez disso, atribua IAM role ao Lambda execution:
# - Ir em Lambda → Configuration → Execution role
# - Usar role com policy:
#   {
#     "Version": "2012-10-17",
#     "Statement": [{
#       "Effect": "Allow",
#       "Action": [
#         "s3:GetObject",
#         "dynamodb:PutItem",
#         "dynamodb:Query",
#         "dynamodb:Scan",
#         "sns:Publish",
#         "xray:PutTraceSegments",
#         "xray:PutTelemetryRecords"
#       ],
#       "Resource": "*"
#     }]
#   }
```

### CORS Dinâmico

```bash
# Em desenvolvimento (localhost):
# CORS_EXTRA_ORIGINS não precisa (usa defaults)

# Em staging:
export CORS_EXTRA_ORIGINS="https://staging-dashboard.example.com"

# Em produção:
export CORS_EXTRA_ORIGINS="https://dashboard.example.com,https://api.example.com"
```

### Distributed Tracing

```bash
# Habilitar X-Ray tracing em Lambda:
export XRAY_ENABLED=true

# Se não quiser X-Ray (reduz latência um pouco):
export XRAY_ENABLED=false  # padrão
```

### Model Versioning

```bash
# Diretório de cache de versões de modelos (opcional):
export MODEL_VERSION_REGISTRY="/tmp/model_versions.json"
# Se não definido, usa ~/.cache/model_versions.json (localmente)
# Em Lambda, /tmp é efêmero mas suficiente
```

---

## Deployment Steps

### 1. Local Testing

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install moto pytest  # para testes

# Rodular testes da correção
pytest tests/test_aws_with_moto.py -v
pytest tests/test_model_versioning.py -v
pytest tests/test_xray_tracing.py -v

# Teste manual de path traversal
python -c "
from app.application.cv.detect_storm import DetectStormUseCase
from app.infrastructure.aws.dynamodb_storm import DynamoDBStormAlertRepository
import pytest

repo = DynamoDBStormAlertRepository()
use_case = DetectStormUseCase(repo=repo)

try:
    use_case.execute(bucket='bkt', key='../../../etc/passwd')
    print('❌ FAIL: Deveria ter lançado ValueError')
except ValueError as e:
    print(f'✅ PASS: Path traversal bloqueado - {e}')
"

# Teste CORS dinâmico
python -c "
import os
from app.core.config import get_allowed_origins

# Padrão
origins = get_allowed_origins()
print(f'Padrão CORS: {origins}')

# Extra
os.environ['CORS_EXTRA_ORIGINS'] = 'https://example.com'
origins = get_allowed_origins()
print(f'Com extra: {origins}')
print('✅ CORS dinâmico funciona')
"
```

### 2. Staging Deployment

```bash
# Deploy com testes em staging
git add .
git commit -m "feat: fix 11 critical issues (security, tracing, versioning)"
git push origin main  # ou branch de feature

# Se using CloudFormation:
aws cloudformation update-stack \
  --stack-name global-solutions-staging \
  --template-body file://cfn-template.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# Ou se using Lambda console:
# 1. Upload arquivo ZIP com novo código
# 2. Configure env variables: XRAY_ENABLED=true, CORS_EXTRA_ORIGINS=...
# 3. Run smoke tests

# Fumigar testes
curl -X POST https://staging-api.example.com/health
# Esperado: {"status": "ok"}

# Teste X-Ray
# Ir em CloudWatch → X-Ray → Service Map
# Verificar que segmentos aparecem
```

### 3. Production Deployment

```bash
# Code review aprovado
# Testes em staging passaram

# Deploy com canary (recomendado para Lambda)
# Usar SAM ou Lambda Alias para traffic shift

# Opção 1: SAM
sam deploy \
  --stack-name global-solutions-prod \
  --template-file template.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# Opção 2: Terraform (se using)
terraform apply -target=aws_lambda_function.detect_storm -auto-approve

# Opção 3: Serverless framework
serverless deploy --stage production
```

---

## Monitoring Post-Deployment

### CloudWatch Logs

```bash
# Monitor errors em tempo real
aws logs tail /aws/lambda/detect_storm --follow

# Buscar por "ERROR" ou "retry"
aws logs filter-log-events \
  --log-group-name /aws/lambda/detect_storm \
  --filter-pattern "[time, request_id, level=ERROR*, ...]"
```

### X-Ray Service Map

```
CloudWatch → X-Ray → Service Map
- Verificar latência de S3 downloads
- Verificar latência de YOLO inference
- Verificar latência de DynamoDB writes
- Alertar se latência > 5 segundos
```

### Alerts

Configurar CloudWatch Alarms:

```bash
# 1. Lambda Errors
aws cloudwatch put-metric-alarm \
  --alarm-name detect-storm-errors \
  --alarm-description "Alert if Lambda errors > 1% in 5 min" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:xxx:alerts

# 2. Lambda Duration (timeout prevention)
aws cloudwatch put-metric-alarm \
  --alarm-name detect-storm-duration \
  --alarm-description "Alert if Lambda duration > 30 seconds" \
  --metric-name Duration \
  --namespace AWS/Lambda \
  --statistic Maximum \
  --period 300 \
  --threshold 30000 \  # em milisegundos
  --comparison-operator GreaterThanThreshold

# 3. DynamoDB Throttling
aws cloudwatch put-metric-alarm \
  --alarm-name dynamodb-throttle \
  --alarm-description "Alert if DynamoDB is throttling" \
  --metric-name ConsumedWriteCapacityUnits \
  --namespace AWS/DynamoDB \
  --statistic Sum \
  --period 60 \
  --threshold 1000 \
  --comparison-operator GreaterThanThreshold
```

---

## Rollback Plan

Se algo der errado em produção:

### Quick Rollback (< 1 minuto)

```bash
# Lambda Alias (recomendado)
# Se deployment anterior em Alias:Live

# Repoint LIVE alias para versão anterior
aws lambda update-alias \
  --function-name detect_storm \
  --name Live \
  --routing-config AdditionalVersionWeight=0 \
  --function-version <previous-version>

# Ou, redeploy versão anterior
git revert HEAD --no-edit
git push origin main
# Redeploy...
```

### Root Cause Analysis

```bash
# 1. Verificar logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/detect_storm \
  --start-time $(date -d '5 minutes ago' +%s)000

# 2. Verificar X-Ray traces
aws xray get-service-graph --start-time <timestamp>

# 3. Verificar métricas
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=detect_storm \
  --start-time <timestamp> \
  --end-time <now> \
  --period 60 \
  --statistics Sum
```

---

## Validação Post-Deployment

### Teste de Idempotência

```bash
# Upload mesma imagem 3x
curl -X POST https://api.example.com/cv/detect \
  -F "image=@storm.jpg" \
  -H "X-Dedup-ID: storm_abc123"

curl -X POST https://api.example.com/cv/detect \
  -F "image=@storm.jpg" \
  -H "X-Dedup-ID: storm_abc123"

curl -X POST https://api.example.com/cv/detect \
  -F "image=@storm.jpg" \
  -H "X-Dedup-ID: storm_abc123"

# Esperado: 3 sucessos, mas apenas 1 SNS enviado (dedup)
```

### Teste de Path Traversal

```bash
# Deve ser rejeitado
curl -X POST https://api.example.com/cv/detect \
  -H "X-S3-Key: ../../../etc/passwd" \
  -F "image=@test.jpg"

# Esperado: 400 Bad Request ou 403 Forbidden com mensagem de validação
```

### Teste de CORS

```bash
# De domínio extra
curl -X OPTIONS https://api.example.com/cv/detect \
  -H "Origin: https://example.com" \
  -H "Access-Control-Request-Method: POST" \
  -i | grep "Access-Control-Allow-Origin"

# Esperado: Access-Control-Allow-Origin: https://example.com
```

---

## Database Migrations (se necessário)

Se modar schema de DynamoDB:

```bash
# 1. Criar nova tabela com novo schema
aws dynamodb create-table \
  --table-name storm_detections_v2 \
  --attribute-definitions \
    AttributeName=alert_id,AttributeType=S \
    AttributeName=timestamp,AttributeType=S \
  --key-schema \
    AttributeName=alert_id,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

# 2. Migrar dados (background job)
python scripts/migrate_dynamodb_v1_to_v2.py \
  --source storm_detections \
  --target storm_detections_v2

# 3. Update código para usar nova tabela
# Atualizar src/app/core/config.py: DYNAMODB_TABLE_ALERTS = "storm_detections_v2"

# 4. Testar com nova tabela
pytest tests/test_aws_with_moto.py -v

# 5. Deploy com nova tabela
# (Lambda continua lendo da antiga até validar)

# 6. Depois de validar, deletar tabela antiga
aws dynamodb delete-table --table-name storm_detections
```

---

## Performance Optimization (após deploy)

### Monitor latências

```bash
# Buscar 99th percentile de duração
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=detect_storm \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --end-time $(date +%s)000 \
  --period 60 \
  --statistics Maximum,Average

# Se > 30s, aumentar timeout ou memory
aws lambda update-function-configuration \
  --function-name detect_storm \
  --memory-size 1024 \  # aumentar se CPU-bound (YOLO)
  --timeout 60
```

### Lambda Layers (para dependencies)

Se código crescer:

```bash
# Criar layer com dependências
pip install -r requirements.txt -t python/
zip -r dependencies-layer.zip python/

# Upload layer
aws lambda publish-layer-version \
  --layer-name global-solutions-deps \
  --zip-file fileb://dependencies-layer.zip \
  --compatible-runtimes python3.11

# Add ao Lambda
aws lambda update-function-configuration \
  --function-name detect_storm \
  --layers arn:aws:lambda:us-east-1:xxx:layer:global-solutions-deps:1
```

---

## Success Criteria

Deploy é considerado bem-sucedido se:

- [ ] Todos os testes em production passam
- [ ] Sem novos erros em CloudWatch logs (5 min)
- [ ] Latência P99 < 10 segundos
- [ ] Deduplicação funcionando (alertas não duplicados)
- [ ] CORS dinâmico respondendo corretamente
- [ ] X-Ray traces aparecendo em Service Map
- [ ] SNS alerts sendo entregues normalmente
- [ ] Model versions registradas corretamente

---

## Troubleshooting

### "AccessDenied" ao acessar S3

```
Solução: Verificar IAM role do Lambda
aws lambda get-function-concurrency --function-name detect_storm
aws iam get-role --role-name lambda-execution-role
# Garantir que policy inclui: s3:GetObject, s3:PutObject
```

### "ConditionalCheckFailedException" em DynamoDB

```
Solução: Normal! Significa alerta duplicado foi rejeitado
- Verificar logs se é para mesma imagem (esperado)
- Se for para imagens diferentes, bug em _deterministic_alert_id()
```

### X-Ray traces não aparecem

```
Solução:
1. Verificar XRAY_ENABLED=true
2. Verificar IAM role tem xray:PutTraceSegments
3. Instalar aws-xray-sdk: pip install aws-xray-sdk
4. Verificar region correto em CloudWatch X-Ray
```

### Cleanup de /tmp falhando

```
Solução:
- Isso é apenas warning, não quebra pipeline
- Se acontecer muito, aumentar memory de Lambda
- /tmp é limpado automaticamente entre invocações
```

---

## Documentation Updates

Após deploy, atualizar:

- [ ] README.md com variáveis de ambiente novas
- [ ] Architecture diagram com X-Ray
- [ ] API documentation com exemplos de CORS
- [ ] Runbook de oncall com troubleshooting
- [ ] CHANGELOG com versão e timestamp

---

## Sign-off

Deploy realizado e validado:

- [ ] **Deploy Date**: _______________
- [ ] **Deployed by**: _______________
- [ ] **Validated by**: _______________
- [ ] **Rollback tested**: Yes / No
- [ ] **All monitoring alerts active**: Yes / No

---

✅ Deployment Guide Complete! 🚀
