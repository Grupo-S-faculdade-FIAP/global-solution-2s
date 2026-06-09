# SNS Geo-Targeted Email Alerts

**Status:** Implementado  
**Prioridade:** P1 MVP  
**Atualizado:** 2026-06-09

## Problema

Inscritos no tópico SNS recebiam todos os alertas de tempestade (broadcast), independente da localização definida no dashboard.

## Solução

Persistir lat/lon na inscrição e filtrar publicação por raio (default 200 km, alinhado ao CV/risco).

## Requisitos

### SNS-GEO-01 — Persistir coordenadas na inscrição (P1)

**WHEN** o usuário inscreve e-mail com `lat` e `lon` válidos  
**THEN** o sistema SHALL salvar as coordenadas associadas ao e-mail normalizado  
**AND** SHALL retornar sucesso da inscrição SNS como antes.

### SNS-GEO-02 — Filtrar alertas automáticos por região (P1)

**WHEN** uma tempestade é detectada e o S3 key contém região NASA reconhecida  
**THEN** o sistema SHALL derivar o centro da região (bbox NASA)  
**AND** SHALL enviar e-mail apenas a inscritos confirmados dentro de `SNS_ALERT_RADIUS_KM`  
**AND** SHALL aplicar rate limit e cooldown regional apenas para envios efetivos.

### SNS-GEO-03 — Filtrar alertas simulados (P1)

**WHEN** o dashboard publica alerta simulado com `lat`/`lon`  
**THEN** o sistema SHALL filtrar inscritos pelo mesmo raio geográfico.

### SNS-GEO-04 — Inscritos legados sem coordenadas (P1)

**WHEN** um inscrito confirmado não tem lat/lon salvo  
**THEN** o sistema SHALL **não** enviar alerta geo-filtrado  
**AND** SHALL registrar log informando re-inscrição com localização no mapa.

### SNS-GEO-05 — Configuração e status (P2)

**WHEN** `GET /alerts/sns/status`  
**THEN** a resposta SHALL incluir `alert_radius_km` e `geo_filtering_enabled: true`.

### SNS-GEO-06 — Validação de coordenadas Brasil (P1)

**WHEN** lat/lon são enviados na inscrição  
**THEN** lat SHALL estar em [-35, 5] e lon em [-75, -30] (faixa operacional Brasil).

## Configuração

| Variável | Default | Descrição |
|----------|---------|-----------|
| `SNS_ALERT_RADIUS_KM` | `200.0` | Raio de alerta em km |
| `DYNAMODB_TABLE_SNS_RATE_LIMIT` | `sns_rate_limits` | Tabela compartilhada (PK `SUBSCRIBER#email`) |

## Fora de escopo

- Push mobile
- Múltiplas localizações por inscrito
- Re-subscribe automático de legados
