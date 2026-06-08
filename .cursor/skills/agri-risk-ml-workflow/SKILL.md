---
name: agri-risk-ml-workflow
description: Workflow para treinar, avaliar, ajustar limiares (AG/DEAP) e versionar o AgriRiskModel e o pipeline de dados (INMET/FAOSTAT) do projeto FIAP Global Solutions. Use quando o usuario pedir para treinar/retreinar o modelo de risco agricola, ajustar thresholds, analisar dataset INMET, avaliar metricas de ML tabular ou revisar o pipeline scikit-learn/LightGBM/DEAP.
---

# Agri Risk ML Workflow

Use esta skill para tarefas de analise de dados e Machine Learning tabular do
modulo de risco agricola (`AgriRiskModel` + `AgriThresholds`). Trabalhe sempre
em cima do codigo existente — `src/app/services/agri_risk_model.py`,
`agri_threshold_ga.py`, `risk_assessment.py` — sem criar pipelines paralelos.

## Quando usar

- Re-treinar/avaliar `AgriRiskModel` com novos dados INMET/FAOSTAT.
- Rodar/ajustar o algoritmo genetico (DEAP) que otimiza `AgriThresholds`.
- Analisar distribuicao de classes, features ou qualidade do cache `training_cache.csv`.
- Revisar/depurar `RiskAssessmentService` (ensemble clima + CV + ML).
- Atualizar artefatos versionados em `models/` (`.pkl`, `agri_risk_thresholds.json`, `_meta.pkl`).

## Workflow

1. **Entenda o estado atual**
   - Leia `models/agri_risk_meta.pkl` / `agri_risk_thresholds.json` e os testes
     `tests/test_agri_risk_model.py`, `tests/test_agri_threshold_ga.py` para
     saber o formato esperado de features, thresholds e metricas — nao assuma.
   - Verifique se existe cache real (`data/weather/inmet/training_cache.csv`)
     ou se o fallback de amostra (`sample_inmet_bdmep.csv`) sera usado.

2. **Prepare/explore os dados (pandas/numpy)**
   - Use `.loc`/`.iloc`, vetorizacao, e documente unidade/fonte de cada feature
     meteorologica (°C, mm, km/h, %).
   - Reporte contagens, faixas e distribuicao de classes alvo (`TARGET_DIST` =
     {0: 0.70, 1: 0.25, 2: 0.05}) antes e depois de qualquer mudanca — isso
     mostra se o dataset ainda reflete a realidade que o AG tenta balancear.

3. **Treino / avaliacao (scikit-learn / LightGBM)**
   - Reaproveite o pipeline `StandardScaler` + regressor +
     `cross_val_score` ja presente. Respeite `_resolve_regressor_backend`
     (variavel `AGRI_USE_LIGHTGBM`; fallback `HistGradientBoostingRegressor`).
   - Fixe seeds (`numpy`, `random`, e do proprio `LGBMRegressor`/`HistGradientBoostingRegressor`).
   - Reporte metricas de validacao cruzada (nao apenas treino) e compare com o
     `agri_risk_meta.pkl` anterior antes de sobrescrever artefatos.

4. **Otimizacao de limiares (AG / DEAP)**
   - Ao rodar/ajustar `agri_threshold_ga.py`: confirme a funcao de fitness,
     numero de geracoes/populacao e seed. Documente o racional de qualquer
     mudanca em `AgriThresholds` ou `TARGET_DIST`.
   - Persista o resultado em `models/agri_risk_thresholds.json` via
     `to_dict`/`asdict` — nao escreva o JSON manualmente.

5. **Versionamento e sincronia de artefatos**
   - Mantenha `agri_risk_model.pkl` + `agri_risk_scaler.pkl` +
     `agri_risk_thresholds.json` + `agri_risk_meta.pkl` coerentes entre si
     (mesma run/seed/feature-set). Um artefato desalinhado quebra
     `RiskAssessmentService` silenciosamente em produção.
   - Para modelos de visao (YOLO `.pt`), use `ModelVersion`
     (`app/core/model_versioning.py`) — checksum SHA256 + metadata — em vez de
     sobrescrever o peso sem registro.

6. **Teste e valide**
   - Rode/atualize os testes relevantes (`pytest tests/test_agri_risk_model.py
     tests/test_agri_threshold_ga.py tests/test_risk_assessment_unit.py -v`).
   - Para mudancas que afetam a API/BFF, rode tambem `test_bff_risk_handlers.py`
     e `test_ml_router.py`.

7. **Documente decisoes, nao apenas numeros**
   - Metricas, distribuicao de classes e thresholds mudam com o dataset —
     registre a decisao de modelagem (por que mudou, com qual dado, qual
     trade-off) em `.specs/` ou no commit, seguindo `document-organization`.
   - Nunca repita metricas antigas de docs sem reverificar no codigo/artefatos atuais.

## Comandos uteis

```bash
# Rodar testes do modulo de risco agricola
pytest tests/test_agri_risk_model.py tests/test_agri_threshold_ga.py tests/test_risk_assessment_unit.py -v

# Forcar backend LightGBM (cuidado: pode haver conflito com torch/YOLO no macOS)
AGRI_USE_LIGHTGBM=1 python -m <script_de_treino>
```

## Referencias

- `src/app/services/agri_risk_model.py`, `agri_threshold_ga.py`, `risk_assessment.py`
- `models/agri_risk_thresholds.json`, `agri_risk_meta.pkl`
- `app/core/model_versioning.py`
- `docs/YOLO-RETREINO.md`, `docs/RUNBOOK-YOLO-70.md` (para o lado de visao computacional)
- Boas praticas de referencia: pandas user guide, scikit-learn pipelines/cross-validation,
  skills de Data Science da Tech Leads Club (agent-skills.techleads.club)
