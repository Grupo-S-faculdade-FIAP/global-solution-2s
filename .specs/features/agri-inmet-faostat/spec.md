# Feature: Dados reais agrícolas — INMET + FAOSTAT

**Slug:** `agri-inmet-faostat`  
**Data:** 2026-06-05  
**Status:** Em execução

## Problema

O módulo agrícola (G2) precisa de credibilidade na avaliação FIAP: modelo treinado com fonte oficial brasileira (INMET) e narrativa de impacto na produção (FAOSTAT) no PDF.

## Solução

| Fonte | Onde entra | Escopo código |
|-------|------------|---------------|
| **INMET BDMEP** | Treino `AgriRiskModel` | Sim — cliente + cache + retreino |
| **FAOSTAT QCL** | PDF / `docs/dados/` | Não obrigatório no runtime — script + markdown |

## Requisitos

### P1 — INMET (código)

| ID | User story | Aceite |
|----|------------|--------|
| **AGRI-01** | Como desenvolvedor, quero ingerir BDMEP das 5 estações das capitais | WHEN `make fetch-inmet` THEN gera `data/weather/inmet/training_cache.csv` com ≥20k registros horários |
| **AGRI-02** | Como API, quero modelo treinado com INMET | WHEN `make train-ml-inmet` THEN `DATASET_SOURCE=inmet_bdmep_brazil_5stations` e meta salva |
| **AGRI-03** | Como avaliador, quero ver fonte no endpoint | WHEN `GET /ml/model/info` THEN `dataset` cita INMET se aplicável |
| **AGRI-04** | Como CI, quero testes sem download | WHEN pytest THEN usa `sample_inmet_bdmep.csv` fixture |

### P2 — FAOSTAT (PDF)

| ID | User story | Aceite |
|----|------------|--------|
| **AGRI-05** | Como autor do PDF, quero contexto agrícola BR | WHEN `docs/dados/FAOSTAT_BR_contexto.md` existir THEN contém tabela soja/milho/café + fonte FAO |
| **AGRI-06** | Como time, quero script reprodutível | WHEN `make export-faostat` THEN tenta API FAO e grava JSON + atualiza markdown |

## Rótulos (MVP)

Features: temperatura, umidade, precipitação, vento (INMET horário).  
Labels: regras agrometeorológicas INMET/EMBRAPA (`_classificar_risco`) — documentado no PDF como proxy, não perda de safra observada.

## Fora do escopo

- Integrar yield FAOSTAT como feature do Random Forest v1
- App mobile / ERP agrícola
