# Contexto agrícola brasileiro — FAOSTAT (QCL)

**Gerado em:** 2026-06-05  
**Fonte:** [FAOSTAT — Production: Crops and livestock products (QCL)](https://www.fao.org/faostat/en/#data/QCL)  
**Área:** Brasil (código FAO 21)  

> Uso: seção *Contexto* e *Resultados* do PDF FIAP. Não alimenta o modelo ML em runtime.

## Por que FAOSTAT aqui?

O **INMET** calibra o modelo de risco com medições meteorológicas oficiais. O **FAOSTAT** contextualiza o **impacto econômico-agricultural**: produção, área e rendimento das principais culturas — conectando clima extremo à volatilidade da safra brasileira.

## Tabela resumo (últimos anos)

| Cultura | Ano | Produção (t) | Área colhida (ha) | Rendimento (kg/ha) |
|---------|-----|--------------|-------------------|---------------------|
| _Preencher via `make export-faostat`_ | — | — | — | — |

> API FAO retornou indisponível nesta execução. Consulte manualmente em
> https://www.fao.org/faostat/en/#data/QCL (Brasil, QCL, 2018–2024).

## Insights para o PDF (roteiro)

1. **Clima → decisão no campo:** alertas YOLO + risco ML (INMET) antecipam janelas críticas.
2. **Clima → safra:** eventos como El Niño reduzem rendimento (ex.: soja 2023/24) — FAOSTAT quantifica escala nacional.
3. **Brasil como celeiro:** soja e milho concentram área colhida; variabilidade climática afeta cadeia de exportação.

## Complementos narrativos (sem código)

- **ZARC (MAPA):** zoneamento de risco climático para culturas.
- **CONAB:** acompanhamento de safras brasileiras (complemento nacional ao FAOSTAT).

## Reproduzir

```bash
make export-faostat
```

Se a API FAO retornar erro, consulte manualmente: https://www.fao.org/faostat/en/#data/QCL
