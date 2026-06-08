# Treino YOLOv5m no RunPod — Guia Rápido

**Objetivo:** Treinar `yolov5m` em GPU RTX 3090/4090 e obter `best.pt` com mAP próximo de 0.70.

**Tempo total:** ~15 min de setup + ~45 min de treino  
**Custo estimado:** ~$0.50–1 USD (RTX 4090 ~$0.74/hr × 1h)

---

## Passo 1 — Criar conta e adicionar crédito

1. Acesse [https://runpod.io](https://runpod.io) → **Sign Up**
2. Vá em **Billing** → **Add Credits** → adicione ~$10 USD via cartão
3. Pronto

---

## Passo 2 — Criar o Pod (instância GPU)

1. No menu lateral, clique em **Pods** → **+ Deploy**
2. Em **GPU**, selecione:
   - **RTX 4090** (24 GB VRAM) — melhor custo-benefício para treino rápido
   - Evite RTX 3090 (mais lento, mesmo preço)
3. Clique em **Deploy** na opção escolhida
4. Na tela de configuração:
   - **Container Image:** `runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04`
   - **Disk:** 40 GB (Container) + 20 GB (Volume)
   - **Expose ports:** deixe padrão
5. Clique em **Deploy On-Demand**
6. Aguarde status **Running** (~1–3 min)

---

## Passo 3 — Conectar pelo Cursor (recomendado)

1. No painel RunPod → seu Pod → **Connect** → **SSH over exposed TCP**
2. Copie os dados de conexão (IP e porta, ex: `ssh root@123.45.67.89 -p 10022`)
3. No **Cursor**: `Cmd+Shift+P` → **Remote-SSH: Connect to Host…** → **Add New SSH Host**
4. Cole o comando SSH e pressione Enter
5. Selecione **Linux** como sistema operacional do servidor
6. Aguarde conectar — o Cursor vai abrir uma nova janela conectada ao Pod
7. Use o terminal integrado do Cursor (`Ctrl+\``) para rodar os comandos

> **Dica:** Adicione a chave SSH antes para não precisar de senha:
> ```bash
> # No Mac — gera chave se não tiver
> ssh-keygen -t ed25519 -C "runpod"
> # Copie o conteúdo de ~/.ssh/id_ed25519.pub
> # No RunPod → Settings → SSH Public Keys → cole a chave
> ```

---

## Passo 4 — Rodar o script de treino

No terminal do Pod:

```bash
apt-get update -qq && apt-get install -y -qq git libgl1 libglib2.0-0

git clone https://github.com/Grupo-S-faculdade-FIAP/global-solution-2s.git /workspace/global-solutions

cd /workspace/global-solutions

bash scripts/runpod_train.sh
```

O script faz automaticamente (em ~1–2h no total):
1. Instala dependências
2. Baixa **1602 imagens** do NASA GIBS (~4 min)
3. Converte para YOLO + augmenta para **3204 imagens** (~10 min)
4. Treina **yolov5m 100 épocas** com `--device 0` (~5–10h)
5. Salva `best.pt` em `src/models/weights/best.pt`

Para acompanhar o progresso em outra aba do terminal:

```bash
watch -n 30 tail -5 /workspace/global-solutions/runs/train/storm-detector-v2/results.csv
```

---

## Passo 5 — Baixar o best.pt para o Mac

### Via SCP (terminal do Mac):
```bash
# Pegue IP e porta no painel RunPod → Connect → SSH
scp -P 12345 root@xxx.xxx.xxx.xxx:/workspace/global-solutions/src/models/weights/best.pt \
    ~/Desktop/FIAP/global-solutions/src/models/weights/best.pt
```

### Via painel RunPod (sem SSH):
1. No painel do Pod, clique em **Files**
2. Navegue até `/workspace/global-solutions/src/models/weights/`
3. Clique em `best.pt` → **Download**

---

## Passo 6 — Encerrar o Pod

**Importante:** Pare o Pod assim que baixar o `best.pt` para não pagar à toa.

1. No painel → seu Pod → **Stop** (pausa, mantém disco)
2. Ou **Terminate** (deleta tudo, não cobra mais nada)

> Use **Terminate** se já baixou o `best.pt` e não precisa mais do Pod.

---

## Referência de comandos úteis no Pod

```bash
# Ver GPU disponível
nvidia-smi

# Ver progresso ao vivo
tail -f /workspace/global-solutions/runs/train/storm-detector-v2/results.csv

# Treino com modelo maior (opcional)
cd /workspace/global-solutions
python src/yolo_training.py \
  --model yolov5l --epochs 150 --batch 32 \
  --device 0 --patience 50 \
  --cos-lr --recall-focus --validate
```

---

## Métricas esperadas

| Modelo | GPU | Épocas | mAP@0.5 estimado | Duração |
|--------|-----|--------|-----------------|---------|
| yolov5s (atual, CPU) | — | 37 | 0.436 | 11h |
| yolov5m | RTX 4090 | 100 | ~0.55–0.65 | **~45 min** |
| yolov5l | RTX 4090 | 150 | ~0.65–0.75 | **~2h** |

> Para garantir mAP ≥ 0.70, considere `yolov5l` com 150 épocas ou revisar
> manualmente ~50 labels com `python scripts/goes_pipeline/05_review_nasa_labels.py`.
