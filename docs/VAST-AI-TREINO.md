# Treino YOLOv5m no Vast.ai — Guia Rápido

**Objetivo:** Treinar `yolov5m` em GPU RTX 3090/4090 por ~R$15 e obter `best.pt` com mAP ≥ 0.70.

**Tempo total:** ~30 min de setup + 8–12h de treino  
**Custo:** ~$3–5 USD (RTX 3090 ~$0.25/hr × 12h)

---

## Passo 1 — Criar conta no Vast.ai

1. Acesse [https://vast.ai](https://vast.ai) e crie uma conta
2. Vá em **Billing** → adicione crédito mínimo (~$5 USD via cartão)
3. Pronto — não precisa de nada mais

---

## Passo 2 — Alugar a instância

1. Vá em **Search** (aba de GPUs disponíveis)
2. Filtros recomendados:
   - **GPU:** RTX 3090 ou RTX 4090
   - **VRAM:** ≥ 20 GB
   - **Disk:** ≥ 30 GB
   - **Image:** `pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime`
3. Ordene por **Price/hr** (mais barato primeiro)
4. Clique em **Rent** na instância escolhida
5. Em **On-start script**, deixe em branco
6. Confirme e aguarde status **Running** (~1–2 min)

---

## Passo 3 — Conectar via SSH no Mac

Na página da instância, clique em **Connect** para ver o comando SSH. Vai ser algo como:

```bash
ssh -p 12345 root@123.456.789.0
```

Cole no terminal do seu Mac e pressione Enter.

---

## Passo 4 — Rodar o script de treino

Dentro da instância, execute:

```bash
curl -fsSL https://raw.githubusercontent.com/Grupo-S-faculdade-FIAP/global-solution-2s/main/scripts/vast_train.sh | bash
```

Ou manualmente:

```bash
git clone https://github.com/Grupo-S-faculdade-FIAP/global-solution-2s.git /workspace/global-solutions
cd /workspace/global-solutions
bash scripts/vast_train.sh
```

O script faz automaticamente:
- Instala dependências
- Baixa 1602 imagens do NASA GIBS (~4 min)
- Converte para YOLO + augmentação (~5 min)
- Treina `yolov5m` 100 épocas com `--device 0` (~8–12h)
- Salva `best.pt` em `src/models/weights/best.pt`

Para acompanhar o progresso (em outra janela SSH):

```bash
tail -f /workspace/global-solutions/runs/train/storm-detector-v2/results.csv
```

---

## Passo 5 — Baixar o best.pt para o Mac

Quando o treino terminar, no **terminal do seu Mac** (não na instância):

```bash
# Substitua porta e IP pelo seu (visível no painel Vast.ai)
scp -P 12345 root@123.456.789.0:/workspace/global-solutions/src/models/weights/best.pt \
    ~/Desktop/FIAP/global-solutions/src/models/weights/best.pt
```

---

## Passo 6 — Desligar a instância

**Importante:** Desligue assim que o `best.pt` estiver baixado para não pagar à toa.

1. No painel Vast.ai → sua instância → **Destroy**
2. Confirme

---

## Referência rápida de comandos

```bash
# Dentro da instância — ver GPU disponível
nvidia-smi

# Ver progresso do treino em tempo real
tail -f /workspace/global-solutions/runs/train/storm-detector-v2/results.csv

# Treino personalizado (opcional)
cd /workspace/global-solutions
python src/yolo_training.py --model yolov5l --epochs 150 --batch 32 --device 0 --patience 50 --recall-focus --validate
```

---

## Métricas esperadas

| Modelo | Épocas | mAP@0.5 esperado |
|--------|--------|-----------------|
| yolov5s (atual, CPU) | 37 | 0.436 |
| yolov5m (Vast.ai T4) | 100 | ~0.55–0.65 |
| yolov5m (Vast.ai 3090) | 100 | ~0.60–0.70 |
| yolov5l (Vast.ai 3090) | 150 | ~0.65–0.75 |

> **Nota:** mAP acima de 0.70 depende também da qualidade das labels automáticas.
> Para garantir 0.70+, considere revisar manualmente ~50 labels com
> `python scripts/goes_pipeline/05_review_nasa_labels.py` antes do treino.
