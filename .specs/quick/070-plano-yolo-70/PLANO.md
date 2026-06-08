# Plano para cruzar a meta G1 (≥ 70%)

## ‼️ Antes de tudo: o "70%" NÃO está na rubrica oficial da GS 2026.1

Lendo o enunciado oficial da Global Solution 2026.1: **não existe nenhum limiar de 70%** (nem mAP, nem precisão, nem acurácia) como requisito de nota. O "70%" veio do PROJECT.md/RPI.md interno do grupo — é uma meta auto-imposta, não da FIAP.

O que a rubrica oficial realmente exige para garantir a nota:
- É uma **POC** — "não precisa estar 100% funcional".
- MVP com aplicação prática de ML/visão computacional + análise de dados/nuvem/APIs/dashboard + integração com sensores/ESP32/AWS quando aplicável.
- Vídeo ≤5 min, PDF único (integrantes, intro/desenvolvimento/resultados/conclusões, código em texto), repositório organizado com README.
- Pontos de **pódio** vêm de **amplitude de integração** ("quanto mais implementações reais"), não de um número de acurácia.

**Conclusão:** um YOLO em ~43% mAP, com as limitações documentadas honestamente (labels-heurístico, objeto minúsculo, trade-off vs. pipeline v1 de bbox-fantasma), **já atende a nota**. Subir o modelo é bônus de qualidade/pódio, não pré-requisito. Priorize a documentação honesta e a integração entre disciplinas.

Se ainda quiser melhorar o modelo (recomendado para o pódio), siga abaixo.

---

## Diagnóstico (por que travou em ~43% mAP@0.5)

O treino não está limitado por learning rate nem por "label noise residual" (a leitura do Cursor). Está limitado por três coisas, em ordem de impacto:

1. **Resolução baixa para o tamanho do objeto.** As caixas têm em média **3,8% da imagem** (muitas <1%, ≈5 px em 640). Em `imgsz=640` a cabeça P3 (stride 8) mal resolve esses blobs. → Treinar em **1280** é o maior ganho isolado.
2. **Augmentation encolhe o alvo minúsculo.** `hyp.v3.yaml` usava `mosaic=1.0`, `scale=0.6`, `mixup=0.3`, `copy_paste=0.3`. Mosaico + scale reduzem o objeto pela metade; mixup/copy_paste fabricam blobs que não batem com a label. → Corrigido em `hyp.smallobj.yaml`.
3. **A label É um heurístico determinístico** (`04_nasa_to_yolo.py`: `cv2.threshold(168)` + componentes conectados). A rede tenta reproduzir um detector de brilho por pixel cujas bordas são instáveis frame a frame → teto estrutural de mAP@0.5 com IoU≥0.5.

A oscilação 0.13→0.44→0.18 é variância normal de obj-loss em objeto pequeno, não LR alto. Rodar 300 épocas não cruza 70% sozinho.

---

## ⚠️ Conflito na rubrica — confirme isto primeiro

A meta G1 aparece de duas formas no projeto:

| Fonte | Critério |
|-------|----------|
| `docs/RPI.md` (PROJECT.md) | **"Precisão ≥ 70%"** na validação |
| `docs/YOLO-RETREINO.md` | reinterpretado como **mAP@0.5 ≥ 0.70** |

São métricas com dificuldade oposta. **Precisão** é ponto de operação (sobe com o limiar de confiança). **mAP@0.5** é métrica de curva. Confirme com o professor qual vale — isso decide o esforço.

---

## Track 1 — Precisão ≥ 70% (rápido, se a rubrica for "precisão")

Precisão sobe quando você só conta detecções confiantes. Faça uma varredura de `--conf-thres` no modelo atual e reporte o ponto onde P≥0,70 (padrão em CV: reportar o ponto de operação escolhido).

```bash
cd global-solutions
for c in 0.25 0.40 0.55 0.70 0.80; do
  echo "=== conf $c ==="
  python yolov5/val.py \
    --weights src/models/weights/best.pt \
    --data data/model-dataset/storm.resolved.yaml \
    --img 1280 --conf-thres $c --iou-thres 0.5 --task val
done
```

Pegue o menor `conf` em que `P ≥ 0.70` e documente recall naquele ponto. Provavelmente já passa sem retreinar.

---

## Track 2 — Subir o mAP@0.5 de verdade (RunPod RTX 4090)

Rode o `train.py` direto para ter controle total. **3 mudanças que importam:** `--img 1280`, modelo `yolov5m`, e o novo `hyp.smallobj.yaml`.

```bash
cd global-solutions
python yolov5/train.py \
  --weights yolov5m.pt \
  --data    data/model-dataset/storm.resolved.yaml \
  --hyp     data/model-dataset/hyp.smallobj.yaml \
  --img     1280 \
  --batch   16 \
  --epochs  150 \
  --cos-lr \
  --patience 40 \
  --name storm-detector-v4-1280 \
  --device 0
```

Notas:
- Se faltar VRAM no 1280 com batch 16, use `--batch 8`.
- **Anchors:** o autoanchor do YOLOv5 roda sozinho e vai recalcular âncoras pequenas para esse dataset (confira no log "Best Possible Recall"). Se ficar <0,98, vale testar a cabeça P2 (stride 4): troque `--weights yolov5m.pt` por `--cfg yolov5/models/hub/yolov5-p2.yaml --weights ''`.
- Compare o `best.pt` novo via `val.py` (mesmo comando do Track 1, sem o loop).

---

## Track 3 — Atacar a causa raiz (labels mais estáveis)

Maior teto de longo prazo. As specks de ~5px nunca atingem IoU≥0,5 — são ruído que derruba o mAP. Regenere as labels descartando as menores e fechando mais o blob:

```bash
cd global-solutions
# area_min maior remove specks indetectáveis; mantém storm cells reais
python scripts/goes_pipeline/04_nasa_to_yolo.py --clean --limiar 168 --area 400
```

Depois confira a distribuição (deve subir o tamanho médio das caixas) e retreine com o Track 2. Para o ganho máximo de mAP, revisão manual de uma fração do val set (~50 imagens) ancora a métrica — mas só vale se o prazo permitir.

---

## Ordem recomendada

1. **Confirmar a métrica da rubrica** (precisão vs mAP).
2. Se for precisão → **Track 1** (provavelmente resolve hoje).
3. Se for mAP → **Track 2** (imgsz 1280 + hyp novo) → reavaliar.
4. Se ainda faltar → **Track 3** (labels limpas) + retreino.
