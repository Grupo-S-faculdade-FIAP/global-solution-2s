# Contexto agrícola brasileiro — FAOSTAT (QCL)

**Gerado em:** 2026-06-05  
**Fonte primária:** [FAOSTAT — Production: Crops and livestock products (QCL)](https://www.fao.org/faostat/en/#data/QCL)  
**Proveniência desta exportação:** Our World in Data (grapher CSV, derivado de FAOSTAT QCL)  
**Área:** Brasil (código FAO 21)  

> Uso: seção *Contexto* e *Resultados* do PDF FIAP. Não alimenta o modelo ML em runtime.

## Por que FAOSTAT aqui?

O **INMET** calibra o modelo de risco com medições meteorológicas oficiais. O **FAOSTAT** contextualiza o **impacto econômico-agricultural**: produção, área e rendimento das principais culturas — conectando clima extremo à volatilidade da safra brasileira.

## Tabela resumo (últimos anos)

| Cultura | Ano | Produção (t) | Área colhida (ha) | Rendimento (kg/ha) |
|---------|-----|--------------|-------------------|---------------------|
| Café verde | 2024 | 3.387.724 | 1.943.951 | 1.743 |
| Café verde | 2023 | 3.348.510 | 1.905.269 | 1.758 |
| Café verde | 2022 | 3.179.341 | 1.867.345 | 1.703 |
| Café verde | 2021 | 2.985.581 | 1.832.544 | 1.629 |
| Café verde | 2020 | 3.705.719 | 1.898.422 | 1.952 |
| Café verde | 2019 | 3.011.745 | 1.825.300 | 1.650 |
| Café verde | 2018 | 3.552.729 | 1.863.971 | 1.906 |
| Milho | 2024 | 114.953.304 | 21.186.813 | 5.426 |
| Milho | 2023 | 131.949.710 | 22.315.189 | 5.913 |
| Milho | 2022 | 109.741.960 | 21.066.546 | 5.209 |
| Milho | 2021 | 88.272.110 | 18.984.472 | 4.650 |
| Milho | 2020 | 103.990.936 | 18.259.080 | 5.695 |
| Milho | 2019 | 101.126.410 | 17.515.919 | 5.773 |
| Milho | 2018 | 82.366.530 | 16.126.269 | 5.108 |
| Soja | 2024 | 144.473.760 | 45.906.946 | 3.147 |
| Soja | 2023 | 152.144.240 | 44.417.784 | 3.425 |
| Soja | 2022 | 121.290.104 | 41.051.273 | 2.955 |
| Soja | 2021 | 134.799.180 | 39.126.661 | 3.445 |
| Soja | 2020 | 121.820.950 | 37.191.559 | 3.276 |
| Soja | 2019 | 114.316.830 | 35.895.635 | 3.185 |
| Soja | 2018 | 117.912.450 | 34.778.328 | 3.390 |
| Trigo | 2024 | 7.633.178 | 2.921.567 | 2.613 |
| Trigo | 2023 | 7.730.188 | 3.330.255 | 2.321 |
| Trigo | 2022 | 10.343.182 | 3.167.120 | 3.266 |
| Trigo | 2021 | 7.878.413 | 2.752.669 | 2.862 |
| Trigo | 2020 | 6.344.079 | 2.432.639 | 2.608 |
| Trigo | 2019 | 5.590.815 | 2.103.550 | 2.658 |
| Trigo | 2018 | 5.469.236 | 2.080.190 | 2.629 |

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
# offline (sem rede):
python scripts/export_faostat_brazil.py --offline
```
