---
name: clean-architecture-review
description: Revisa ou implementa codigo no backend FastAPI (src/app) do Global Solutions seguindo Clean Architecture (domain/application/infrastructure/interfaces) e SOLID. Use quando o usuario pedir para adicionar uma feature, criar um adapter/port/use case, revisar violacoes de camada/SOLID, ou refatorar codigo do backend.
---

# Clean Architecture Review

Use esta skill para implementar ou revisar codigo em `src/app` respeitando a
arquitetura em camadas (Ports & Adapters) e os principios SOLID ja estabelecidos
no projeto Global Solutions. Veja a rule `clean-architecture-solid` para o mapa
completo de camadas e exemplos no codigo.

## Quando usar

- Adicionar uma nova fonte de dados, repositorio ou integracao externa.
- Criar um novo caso de uso (use case) ou endpoint.
- Revisar um PR/diff em busca de violacoes de camada ou de SOLID.
- Refatorar codigo que mistura regra de negocio com detalhes de IO/AWS/framework.

## Workflow para adicionar uma feature nova

1. **Identifique a camada correta**
   - Regra de negocio pura → `domain/` (entidade) ou `application/` (use case).
   - Detalhe tecnico (DynamoDB, S3, SNS, JSON, HTTP externo) → `infrastructure/`.
   - Entrada HTTP/Lambda → `interfaces/`, `routers/`, `lambdas/`.

2. **Desenhe o port antes do adapter**
   - Se a feature precisa de uma nova dependencia externa, escreva primeiro o
     contrato em `domain/<modulo>/ports.py` (Protocol/ABC com metodos minimos —
     ISP). Só depois implemente o adapter concreto.

3. **Implemente o adapter em `infrastructure/`**
   - Isole boto3/HTTP/JSON aqui. O adapter deve honrar exatamente o contrato do
     port (mesma assinatura, mesmas excecoes/semantica) — é o que garante LSP e
     permite trocar `JsonXRepository` ↔ `DynamoDBXRepository` via `DYNAMODB_USE_MOCK`.

4. **Registre no `container.py`**
   - Adicione/edite a factory (`get_x_repo`, `get_x_use_case`) decidindo o adapter
     com base em `settings`. Use cases e routers recebem tudo via `Depends(...)`
     — nunca instanciam adapters diretamente (DIP).

5. **Implemente o caso de uso / handler**
   - Caso de uso depende só de ports (abstrações). Router/Lambda traduz
     requisicao ↔ caso de uso, sem regra de negocio.

6. **Teste em camadas**
   - Teste o port com pelo menos dois adapters (mock + `moto` para AWS) —
     comprova substituibilidade (LSP). Siga o padrao de
     `tests/test_dynamodb_adapters.py`, `tests/test_container.py`.
   - Teste o caso de uso com um adapter fake/mock simples — sem AWS real.

## Workflow para revisar codigo existente

Procure por estes "cheiros" de violacao, na ordem:

1. **Import na direção errada** — `domain` importando `infrastructure`/`fastapi`/
   `boto3`; `application` importando adapter concreto em vez de port.
2. **Regra de negocio em `infrastructure`/`routers`** — calculo, decisao de
   classificacao de risco, orquestracao de múltiplas fontes dentro de um
   adapter ou router (deveria estar em `application`/`domain`/`services`).
3. **Instanciamento direto de adapter** — `DynamoDBStormAlertRepository()` dentro
   de um caso de uso/router em vez de receber via `container`/`Depends`.
4. **Port "gordo"** — interface forçando adapters a implementar metodos
   irrelevantes (ISP). Sugira dividir.
5. **Adapter que não cumpre o contrato** — lança excecao diferente, retorna
   formato diferente, ou tem efeito colateral que o port não promete (LSP).
6. **Mudanças que exigem editar o caso de uso para suportar uma nova fonte**
   (deveria bastar um novo adapter — OCP).

Para cada achado: aponte o arquivo/linha, explique qual principio é violado e
proponha a correção minima (geralmente: extrair port, mover lógica, ou registrar
no container) — não proponha reescrever a arquitetura inteira.

## Referencias

- Rule complementar: `.cursor/rules/clean-architecture-solid.mdc`
- `src/app/domain/*/ports.py`, `src/app/application/cv/detect_storm.py`,
  `src/app/infrastructure/`, `src/app/container.py`
- Testes de referência: `tests/test_container.py`, `tests/test_dynamodb_adapters.py`,
  `tests/test_json_storm_store.py`, `tests/test_detect_storm_use_case.py`
