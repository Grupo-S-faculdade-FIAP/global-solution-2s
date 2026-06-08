# RUNBOOK — Cruzar mAP@0.5 ≥ 0.70 (storm detector)

> **Para o Cursor:** execute os passos NA ORDEM. Cada passo tem um **critério de aceite**.
> Se um passo falhar no aceite, vá para o item correspondente na **Escada de Fallback** (Seção 6).
> Não pule a Seção 0. Rode tudo a partir da pasta `global-solutions/`.
> Ambiente alvo: GPU NVIDIA (RunPod RTX 4090 ou 5090, 24 GB). CUDA device 0.

> ## ⚡ EXECUÇÃO RÁPIDA (recomendado) — um comando só
> Há um script que roda o **stack completo YOLoV5** de uma vez (limpeza → tiling →
> yolov5l nos tiles → TTA → e, se faltar, ensemble l6+P2+WBF → consolida):
> ```bash
> cd global-solutions && bash RODAR_STACK_70.sh
> ```
> Ele é idempotente e tem corte automático: para assim que o mAP@0.5 ≥ 0.70.
> O dataset fatiado (`data/model-dataset-tiled/`, train 3045 / val 1445 tiles) **já foi
> gerado** localmente; o script regenera no ambiente de GPU por segurança.
> As seções abaixo explicam cada etapa para rodar manualmente / depurar.

---

## 0. Setup e sanidade (obrigatório)

```bash
cd global-solutions

# 0.1 Dependências do YOLOv5 (se ainda não instaladas no pod)
pip install -r yolov5/requirements.txt

# 0.2 Confirmar GPU visível
python -c "import torch; print('CUDA:', torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

**0.3 Gerar um data.yaml com caminho ABSOLUTO correto deste ambiente** (não confie no storm.resolved.yaml, que tem o caminho do Mac):

```bash
python - <<'PY'
from pathlib import Path
root = Path('data/model-dataset').resolve()
y = f"""path: {root}
train: images/train
val: images/val
nc: 1
names:
  0: storm
"""
Path('data/model-dataset/storm.v4.yaml').write_text(y)
print(y)
PY
```

**Critério de aceite 0:** `CUDA: True ...` e o `storm.v4.yaml` impresso com `path:` absoluto válido.

---

## 1. Baseline honesto (medir antes de mexer)

Valida o `best.pt` atual em 640 e em 1280 — só pra registrar o ponto de partida.

```bash
# baseline em 640 (como foi treinado)
python yolov5/val.py --weights src/models/weights/best.pt \
  --data data/model-dataset/storm.v4.yaml --img 640 --task val --name base640

# mesmo peso avaliado em 1280 (mostra ganho só de resolução de inferência)
python yolov5/val.py --weights src/models/weights/best.pt \
  --data data/model-dataset/storm.v4.yaml --img 1280 --task val --name base1280
```

**Critério de aceite 1:** ambos rodam e imprimem `P, R, mAP50, mAP50-95`. Anote os mAP50.

---

## 2. Limpeza de labels (estabiliza o teto de IoU) — JÁ FEITO localmente

> **NOTA:** este passo já foi aplicado no dataset local (`data/model-dataset/labels/`).
> Caixas com lado < 10px (não-localizáveis a IoU≥0.5) foram removidas: **20.019 → 15.962** (-20%).
> Backup em `data/model-dataset/labels_backup_*`. **Re-sincronize o dataset para o
> ambiente de treino antes da Seção 4.** Não rode `--clean` aqui: removeu 86% das caixas
> (área de blob ≠ tamanho de bbox) e o método abaixo é o correto.

Método aplicado (filtro pelo **lado menor** da bbox, que é o que decide o IoU — não pela
área do blob). Para reproduzir/ajustar o limiar:

```bash
# (opcional) backup antes
cp -r data/model-dataset/labels data/model-dataset/labels_backup_$(date +%s)

python - <<'PY'
import glob
from pathlib import Path
IMG=640; THR=10          # lado mínimo em px @640 (10 -> remove ~20%; 12 -> ~40%)
b=a=0
for sp in ['train','val']:
    for f in glob.glob(f'data/model-dataset/labels/{sp}/*.txt'):
        L=[l for l in open(f).read().splitlines() if l.strip()]
        K=[l for l in L if min(float(l.split()[3]),float(l.split()[4]))*IMG>=THR]
        b+=len(L); a+=len(K)
        Path(f).write_text("\n".join(K)+("\n" if K else ""))
print(f"antes={b} depois={a} removidos={b-a} ({(b-a)/b*100:.0f}%)")
PY
```

**Critério de aceite 2:** remoção de ~20% (lado≥10) e nenhuma caixa com lado <10px.
Use `THR=12` para um corte mais forte (~40%) só se o mAP ainda travar.

---

## 3. Treino principal — yolov5m @ 1280 (a maior alavanca)

```bash
python yolov5/train.py \
  --weights yolov5m.pt \
  --data data/model-dataset/storm.v4.yaml \
  --hyp  data/model-dataset/hyp.smallobj.yaml \
  --img 1280 --batch 16 --epochs 200 --cos-lr --patience 60 \
  --name storm-v4-m-1280 --device 0
```

Durante o treino, no log inicial confira o **autoanchor**: a linha `Best Possible Recall (BPR)` deve ficar ≥ 0.98. Se `--batch 16` der **CUDA out of memory**, reduza para `--batch 8` (ou `--batch -1` para auto).

**Critério de aceite 3:** treino termina (ou early-stop por patience) e o resumo final mostra **mAP50 ≥ 0.70** em val.
- Se **≥ 0.70** → pule para a Seção 5 (consolidar).
- Se **0.55–0.70** → Seção 4 (empurrão).
- Se **< 0.55** → Seção 6 (fallback / diagnóstico).

---

## 4. Empurrão — yolov5l @ 1280 (mais capacidade)

Só se o passo 3 ficou entre 0.55 e 0.70.

```bash
python yolov5/train.py \
  --weights yolov5l.pt \
  --data data/model-dataset/storm.v4.yaml \
  --hyp  data/model-dataset/hyp.smallobj.yaml \
  --img 1280 --batch 8 --epochs 250 --cos-lr --patience 60 \
  --name storm-v4-l-1280 --device 0
```

**Critério de aceite 4:** mAP50 ≥ 0.70. Se sim → Seção 5. Se não → Seção 6.

---

## 5. Consolidar (quando mAP50 ≥ 0.70)

```bash
# achar o run vencedor (ajuste o nome se usou o 'l')
BEST=$(ls -t runs/train/storm-v4-*/weights/best.pt | head -1)
echo "Melhor peso: $BEST"

# validação final canônica
python yolov5/val.py --weights "$BEST" \
  --data data/model-dataset/storm.v4.yaml --img 1280 --task val --name final_val

# publicar o peso no caminho usado pelo app
cp "$BEST" src/models/weights/best.pt

# (opcional) varredura de precisão p/ documentar o ponto de operação
for c in 0.25 0.40 0.55; do
  echo "=== conf $c ==="
  python yolov5/val.py --weights src/models/weights/best.pt \
    --data data/model-dataset/storm.v4.yaml --img 1280 --conf-thres $c --task val
done
```

**Entregáveis:** `runs/train/.../results.png` (curvas), `confusion_matrix.png`, `PR_curve.png`, e o `best.pt` copiado.
Atualizar os docs (`docs/RPI.md`, `docs/YOLO-RETREINO.md`, `README.md`) com a nova métrica.

---

## 6. Escada de Fallback (se ainda não cruzou 70%)

Aplique na ordem; reavalie o mAP após cada um.

1. **Cabeça P2 (stride 4)** — dedicada a objeto pequeno:
   ```bash
   python yolov5/train.py --cfg yolov5/models/hub/yolov5-p2.yaml --weights '' \
     --data data/model-dataset/storm.v4.yaml --hyp data/model-dataset/hyp.smallobj.yaml \
     --img 1280 --batch 8 --epochs 250 --cos-lr --patience 60 --name storm-v4-p2 --device 0
   ```
2. **Subir resolução para 1536** (se a VRAM aguentar): `--img 1536 --batch 4`.
3. **Reduzir mosaic a 0.3 e scale a 0.1** no `hyp.smallobj.yaml` (objeto pequeno odeia tiling/zoom-out).
4. **Mais dados:** capturar mais dias/regiões no NASA Worldview, rodar `00_download_gibs.py` → `04_nasa_to_yolo.py` de novo para ampliar o train.
5. **Endurecer labels:** `--area 300` + aumentar morphological close no `label_utils.py` para blobs mais consistentes (val mais "justo").
6. **Diagnóstico se mAP < 0.55 persistir:** abra `runs/train/.../val_batch0_pred.jpg` vs `val_batch0_labels.jpg` e verifique se as predições batem visualmente com as labels — se baterem mas mAP for baixo, o gargalo é IoU/tamanho (volte ao passo 1–2); se não baterem, é capacidade/treino (passos 3–4).

---

## 7. Recursos avançados — TUDO dentro do YOLOv5 (+ complementos que plugam nele)

Mantendo o YOLOv5. Ordenado por impacto neste problema (objeto pequeno + labels determinísticas).

### 7.1 SAHI / tiling — MAIOR alavanca (SAHI tem backend YOLOv5)
Treinar em tiles faz o objeto pequeno ficar grande em relação ao recorte. Pesquisa de
2026 atingiu >0.95 mAP@0.5 com tiling+SAHI.

```bash
# 1) gerar dataset fatiado (320px, 20% overlap) a partir das labels JÁ limpas
python scripts/goes_pipeline/08_tile_dataset.py --tile 320 --overlap 0.2

# 2) treinar nos tiles (320 -> upscale 2x = objeto ~4x maior que no 640 original)
python yolov5/train.py --weights yolov5l.pt \
  --data data/model-dataset-tiled/storm.tiled.yaml \
  --hyp data/model-dataset/hyp.smallobj.yaml \
  --img 640 --batch 16 --epochs 200 --cos-lr --patience 60 \
  --name storm-tiled-l --device 0

# 3) inferência fatiada com SAHI (backend YOLOv5)  ->  pip install sahi
#    from sahi import AutoDetectionModel
#    AutoDetectionModel.from_pretrained(model_type="yolov5", model_path="best.pt", ...)
#    get_sliced_prediction(img, model, slice_height=320, slice_width=320, overlap_*=0.2)
```

### 7.2 TTA nativo do YOLOv5 — grátis, +1–3 mAP
```bash
python yolov5/val.py --weights <best.pt> --data <yaml> --img 1280 --augment --task val
```

### 7.3 Modelos P6 nativos (yolov5l6 / x6) — pré-treino em 1280, cabeça P6 extra
Trocar `yolov5l.pt` por `yolov5l6.pt` (ou `yolov5x6.pt`). Melhor que P5 em upscale.

### 7.4 Arquiteturas YOLOv5 para objeto pequeno (via `--cfg`)
- **P2 head** (stride 4, dedicado a objeto minúsculo): `--cfg yolov5/models/hub/yolov5-p2.yaml --weights ''`
- **BiFPN neck** (fusão de features multi-escala melhor): `--cfg yolov5/models/hub/yolov5-bifpn.yaml`

### 7.5 Ensemble NATIVO do YOLOv5 + WBF
O YOLOv5 funde múltiplos pesos sozinho (classe Ensemble) — basta passar vários `--weights`:
```bash
python yolov5/val.py --weights storm-l.pt storm-p2.pt storm-l6.pt \
  --data <yaml> --img 1280 --augment --task val
```
Para fusão mais forte que o NMS, use **WBF**: `pip install ensemble-boxes` (ver script de avaliação).

### 7.6 Albumentations — complemento auto-integrado ao YOLOv5
Se `albumentations` estiver instalado, o YOLOv5 aplica augmentations extras automaticamente
(blur, CLAHE, etc. em `utils/augmentations.py`). `pip install albumentations` e o treino já usa.
Para nuvem/satélite, CLAHE (contraste local) costuma ajudar.

### 7.7 Flags de treino que ajudam objeto pequeno
- `--multi-scale` — varia o img ±50% durante o treino (robustez de escala).
- `--image-weights` — re-amostra imagens "difíceis" com mais frequência.
- `--rect` — treino retangular (menos padding) se quiser eficiência.

### 7.8 Âncoras customizadas (kmeans) para o regime minúsculo
O autoanchor já roda; se o BPR ficar <0.98, force novas âncoras:
```bash
python -c "from utils.autoanchor import kmean_anchors; kmean_anchors('data/model-dataset/storm.v4.yaml', n=9, img_size=1280, thr=4.0, gen=1000)"
# cole as âncoras no topo do yaml do modelo (campo 'anchors:')
```

### 7.9 Hyperparameter evolution (espremer os últimos pontos — caro)
`python yolov5/train.py ... --evolve 300` (busca genética; rodar overnight).

### Stack recomendado para garantir >70% (100% YOLOv5)
`labels limpas (✓)` → `7.1 tiling + yolov5l` → `7.2 TTA na validação` →
se faltar: `7.4 P2/BiFPN` + `7.5 ensemble+WBF` → último recurso `7.9 evolve`.

---

## Resumo do caminho recomendado

`Setup (0)` → `baseline (1)` → `labels limpas (2)` → `treino m@1280 (3)` →
se faltar: `l@1280 (4)` → se faltar: `P2 / 1536 / +dados (6)` → `consolidar (5)`.

Arquivos já criados para este runbook:
- `data/model-dataset/hyp.smallobj.yaml` (hiperparâmetros tiny-object)
- `data/model-dataset/storm.v4.yaml` (gerado no passo 0.3)
