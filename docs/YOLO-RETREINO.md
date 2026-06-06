# Retreino YOLOv5 — meta G1 (mAP@0.5 ≥ 70%)

**Projeto:** GS2 — `global-solution-2s`  
**Atualizado:** 2026-06-06  
**Status atual:** mAP@0.5 ≈ 0,14 (labels honestos, dataset pequeno) — abaixo da meta G1

---

## Pipeline canônico

O retreino usa o dataset em `data/model-dataset/` gerado pelo pipeline NASA v2 (`scripts/goes_pipeline/`). Não há scripts paralelos na raiz — use os comandos abaixo.

| Etapa | Comando / script | Saída |
|-------|------------------|-------|
| 1. Captura NASA | `make nasa-capture` | `data/nasa_captures/*.png` |
| 2. Conversão YOLO | `python scripts/goes_pipeline/04_nasa_to_yolo.py` | `data/model-dataset/images/` + `labels/` |
| 3. Revisão manual (opcional) | `python scripts/goes_pipeline/05_review_nasa_labels.py` | UI de revisão |
| 4. Auditoria (gate) | `python scripts/goes_pipeline/06_audit_labels.py --strict` | `data/label_review/audit.json` |
| 5. Treino | `make train-yolo` | `runs/train/` → cópia em `src/models/weights/best.pt` |

Atalho macOS para etapas 1–2: `build_dataset_nasa.command` (duplo clique).

---

## Pré-requisitos

- Python 3.11+ e `.venv/` na raiz (`make install`)
- Repositório `yolov5/` clonado na raiz (gitignored; `src/yolo_training.py` clona automaticamente se ausente)
- GPU recomendada para treino > 40 épocas (CPU funciona, porém lento)
- Capturas NASA suficientes — meta: ampliar além das **79** atuais em `data/nasa_captures/`

---

## Treino

```bash
# Padrão: 40 épocas, recall-focus, gate de labels
make train-yolo

# Opções avançadas (mesmo script)
python src/yolo_training.py --epochs 100 --batch 16 --recall-focus --validate
```

O script `src/yolo_training.py`:

1. Roda **label quality gate** (bloqueia treino se houver bbox fantasma)
2. Gera `data/model-dataset/storm.resolved.yaml` com paths absolutos
3. Invoca `yolov5/train.py`
4. Copia `best.pt` para `src/models/weights/best.pt`

---

## Parâmetros do pipeline de labels (v2)

Definidos em `scripts/goes_pipeline/label_utils.py`:

- Letterbox 640×640
- Máscara de UI NASA
- Limiar de detecção e área mínima calibrados (sem bbox fantasma no canto superior esquerdo)

Regerar dataset após novas capturas:

```bash
python scripts/goes_pipeline/04_nasa_to_yolo.py --clean
python scripts/goes_pipeline/06_audit_labels.py --strict
```

---

## Métricas e meta G1

| Versão | Dataset | mAP@0.5 | Precision | Recall | Observação |
|--------|---------|---------|-----------|--------|------------|
| v1 (corrompido) | 76 bbox fantasma | ~0,55 | ~0,89 | ~0,42 | Artefato de UI, não nuvens |
| v2.0 | 76 bbox honestos | ~0,08 | ~0,003 | ~0,69 | Labels corretos, dataset esparsо |
| v2.1 | 285 bbox | ~0,14 | ~0,27 | ~0,17 | Melhoria parcial |

**Meta PROJECT.md (G1):** mAP@0.5 ≥ **0,70** no conjunto de validação.

Estratégias para atingir a meta (v2 pós-GS):

1. Mais capturas NASA (`make nasa-capture` em loop / regiões variadas)
2. Augmentação no treino (`--recall-focus` já ativo no Makefile)
3. Revisão manual de labels difíceis (`05_review_nasa_labels.py`)
4. Modelo maior (`yolov5m` ou `yolov5l`) com GPU adequada

---

## Validação local

```bash
cd src
python models/stormdetector.py
# Imagem padrão: data/model-dataset/images/test/test-storm.png
```

---

## Deploy dos novos pesos

1. Copiar para S3: `aws s3 cp src/models/weights/best.pt s3://satellite-images-gs2/models/best.pt`
2. Smoke test: `make smoke-aws`
3. Verificar logs CloudWatch da Lambda `gs2-api`

Ver também: [DEPLOY-LAMBDA.md](DEPLOY-LAMBDA.md) · [RPI.md](RPI.md) §4 (CV)
