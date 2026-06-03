# 🤖 Guia de Treinamento e Uso do Modelo YOLO para Detecção de Tempestades

Este guia descreve como treinar e usar um modelo **YOLOv5** para detectar padrões de nuvens chuvosas/tempestades em imagens de satélite.

---

## 📋 Requisitos

### Dependências Python
```bash
# YOLOv5 via torch.hub
pip install torch torchvision opencv-python numpy

# Ou instale tudo com:
pip install -r src/requirements.txt
```

### Dataset
O dataset já está disponível em `data/model-dataset/` com:
- **Classes:** `storm` (nuvens chuvosas)
- **Formato:** YOLO (imagens em `images/` e labels em `labels/`)
- **Splits:** `train/`, `val/`, `test/`

---

## 🚀 Passo 1: Treinar o Modelo

### Opção 1: Via script Python
```bash
cd /Users/caroline/Desktop/FIAP/global-solutions

# Treino básico (50 épocas, modelo YOLOv5 small)
python3 src/yolo_training.py --epochs 50 --batch 8

# Treino avançado com validação
python3 src/yolo_training.py \
  --epochs 100 \
  --batch 16 \
  --model yolov5m \
  --img-size 640 \
  --device 0 \
  --validate
```

### Opção 2: Via Notebook (Google Colab - recomendado para GPU)

```python
import torch

# Carregar modelo base
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

# Treinar usando CLI
import os
os.system('python -m yolov5.train --img 640 --batch 16 --epochs 100 --data data/model-dataset/storm.yaml --weights yolov5s.pt --device 0')
```

### Saída do treinamento

```
✅ Modelo treinado com sucesso!
📍 Melhor modelo: src/models/weights/best.pt
```

**O modelo será salvo em:** `src/models/weights/best.pt`

---

## 📊 Passo 2: Validar o Modelo

```bash
python3 src/yolo_training.py --validate
```

Isso gera:
- Gráficos de Loss (treino vs validação)
- Matriz de confusão
- Curva PR (Precision-Recall)
- Exemplos de predições

---

## 🔍 Passo 3: Usar o Modelo no Dashboard

### 3.1. Colocar o modelo no local correto

```bash
# O modelo deve estar em:
src/models/weights/best.pt
```

### 3.2. Reiniciar o servidor Flask

```bash
cd /Users/caroline/Desktop/FIAP/global-solutions/src
python3 -m flask --app dashboard.app run --port 5000
```

O detector será carregado automaticamente e aparecerá no dashboard com status **✅ Operacional**.

### 3.3. Usar os endpoints

#### Detectar tempestades em uma imagem

```bash
curl -X POST http://localhost:5000/api/storms/detect \
  -H "Content-Type: application/json" \
  -d '{"image_url": "path/to/image.jpg"}'
```

**Resposta:**
```json
{
  "success": true,
  "num_detections": 2,
  "detections": [
    {
      "x": 320.5,
      "y": 240.2,
      "width": 100,
      "height": 80,
      "confidence": 0.87,
      "class_name": "storm"
    }
  ],
  "has_storm": true,
  "average_confidence": 0.87,
  "timestamp": "2026-06-02T17:30:00.123456"
}
```

#### Detectar em múltiplas imagens

```bash
curl -X POST http://localhost:5000/api/storms/batch-detect \
  -H "Content-Type: application/json" \
  -d '{
    "image_urls": [
      "path/to/image1.jpg",
      "path/to/image2.jpg",
      "path/to/image3.jpg"
    ]
  }'
```

#### Simular uma detecção (para testes)

```bash
curl -X POST http://localhost:5000/api/alerts/simulate-detection \
  -H "Content-Type: application/json" \
  -d '{"confidence": 0.85}'
```

---

## 📈 Monitorar Treinamento

Após o treinamento, os gráficos estarão em:
```
models/yolov5-storm-detector/results.csv
models/yolov5-storm-detector/plots/
  ├── confusion_matrix.png
  ├── pr_curve.png
  ├── results.png
  └── ...
```

### Visualizar resultados

```python
import matplotlib.pyplot as plt
from PIL import Image

# Abrir matriz de confusão
img = Image.open("models/yolov5-storm-detector/plots/confusion_matrix.png")
plt.imshow(img)
plt.axis('off')
plt.show()
```

---

## 🎯 Otimizações e Melhorias

### Aumentar precisão

1. **Mais dados de treinamento**
   - Coletar mais screenshots do Windy.com
   - Usar data augmentation (rotação, zoom, ruído)

2. **Ajustar hiperparâmetros**
   ```python
   model.train(
       epochs=200,           # Mais épocas
       batch=32,            # Batch maior (com GPU forte)
       imgsz=1280,          # Resolução maior
       device=0,            # GPU
       patience=50,         # Early stopping mais paciente
   )
   ```

3. **Usar modelo maior**
   ```bash
  python3 yolo_training.py --model yolov5l
   ```

### Reduzir tamanho do modelo (para Lambda)

```bash
# Exportar para ONNX (menor, mais rápido)
python3 yolo_training.py --export onnx

# Ou TensorFlow Lite (mobilidade)
python3 yolo_training.py --export tflite
```

---

## ⚠️ Troubleshooting

### ❌ "torch not found"
```bash
pip install torch torchvision
```

### ❌ "Dataset path not found"
Verificar se `data/model-dataset/storm.yaml` está acessível e aponta para caminhos corretos.

### ❌ "CUDA not available"
```bash
# Usar CPU (mais lento)
python3 yolo_training.py --device cpu

# Ou instalar PyTorch com suporte CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### ❌ "Out of memory"
Reduzir batch size:
```bash
python3 yolo_training.py --batch 4
```

---

## 📚 Referências

- **Documentação YOLOv5:** https://github.com/ultralytics/yolov5
- **Windy.com API:** https://www.windy.com/
- **Formato YOLO Dataset:** https://roboflow.com/formats/yolo-darknet-txt

---

## 📋 Checklist de Conclusão

- [ ] Dataset preparado em `data/model-dataset/`
- [ ] Dependências instaladas (`pip install torch torchvision`)
- [ ] Modelo treinado: `models/yolov5-storm-detector/weights/best.pt`
- [ ] Validação concluída com métricas aceitáveis
- [ ] Dashboard Flask rodando e detectando com sucesso
- [ ] Testes manuais dos endpoints funcionando
- [ ] Imagens de teste com bounding boxes salvos
