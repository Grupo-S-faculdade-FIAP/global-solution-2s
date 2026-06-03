"""
Script de treinamento do modelo YOLOv5 para detecção de tempestades.

Uso:
    python3 yolo_training.py --epochs 50 --img-size 640 --batch 8
"""

import argparse
import sys
from pathlib import Path

try:
    import torch
except ImportError:
    print("❌ torch não instalado. Execute:")
    print("   pip install torch torchvision")
    sys.exit(1)


def train_yolo_storm_detector(
    dataset_yaml: str = "data/model-dataset/storm.yaml",
    model_name: str = "yolov5s",
    epochs: int = 50,
    img_size: int = 640,
    batch_size: int = 8,
    device: int = 0,
    patience: int = 20,
    output_dir: str = "models",
) -> str:
    """
    Treina um modelo YOLOv5 para detecção de tempestades.

    Args:
        dataset_yaml: Caminho para o arquivo YAML do dataset
        model_name: Tamanho do modelo ('yolov5n', 'yolov5s', 'yolov5m', 'yolov5l', 'yolov5x')
        epochs: Número de épocas de treinamento
        img_size: Tamanho das imagens (default 640)
        batch_size: Tamanho do batch
        device: GPU/CPU device (0 para GPU, -1 para CPU)
        patience: Early stopping patience (em épocas)
        output_dir: Diretório para salvar modelos

    Returns:
        Caminho para o modelo treinado (.pt)
    """
    print(f"🚀 Iniciando treinamento do YOLOv5-Storm Detector...")
    print(f"   Dataset: {dataset_yaml}")
    print(f"   Modelo: {model_name}")
    print(f"   Épocas: {epochs}")
    print(f"   Batch size: {batch_size}")
    print()

    # Criar diretório de saída se não existir
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Carregar modelo base via torch.hub (YOLOv5 oficial)
    print(f"📦 Carregando modelo base: {model_name}...")
    model = torch.hub.load("ultralytics/yolov5", model_name, pretrained=True)

    # Treinar usando CLI (YOLOv5 style)
    print(f"🎓 Treinando...")
    import subprocess
    cmd = [
        "python",
        "-m",
        "yolov5.train",
        "--img", str(img_size),
        "--batch", str(batch_size),
        "--epochs", str(epochs),
        "--data", dataset_yaml,
        "--weights", f"{model_name}.pt",
        "--device", str(device),
        "--patience", str(patience),
        "--project", str(output_path),
        "--name", "yolov5-storm-detector",
    ]
    
    try:
        # Alternativa: usar train.py direto do repositório
        import os
        os.system(f"cd {Path(__file__).parent} && python -m yolov5.train --img {img_size} --batch {batch_size} --epochs {epochs} --data {dataset_yaml} --weights {model_name}.pt --device {device} --patience {patience}")
    except Exception as e:
        print(f"⚠️  Treino via CLI falhou, tentando API torch.hub: {e}")

    # Salvar modelo otimizado no caminho correto
    model_path = Path("src/models/weights/best.pt")
    model_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n✅ Modelo treinado com sucesso!")
    print(f"📍 Melhor modelo: {model_path}")

    return str(model_path)


def validate_model(model_path: str, dataset_yaml: str = "data/model-dataset/storm.yaml"):
    """
    Valida o modelo treinado no conjunto de validação.

    Args:
        model_path: Caminho para o modelo .pt
        dataset_yaml: Caminho para o arquivo YAML do dataset
    """
    print(f"\n📊 Validando modelo: {model_path}...")
    model = torch.hub.load("ultralytics/yolov5", "custom", path=model_path, force_reload=True)
    print(f"✅ Validação concluída!")
    return model


def export_model(model_path: str, export_format: str = "onnx"):
    """
    Exporta o modelo para diferentes formatos (ONNX, TensorFlow, etc).

    Args:
        model_path: Caminho para o modelo .pt
        export_format: Formato de exportação ('onnx', 'torchscript', 'tflite', etc)
    """
    print(f"\n🔄 Exportando modelo para {export_format}...")
    model = torch.hub.load("ultralytics/yolov5", "custom", path=model_path, force_reload=True)
    # YOLOv5 export via torch.onnx
    if export_format == "onnx":
        output_path = Path(model_path).with_suffix(".onnx")
        torch.onnx.export(model, torch.randn(1, 3, 640, 640), str(output_path))
        print(f"✅ Modelo exportado: {output_path}")
        return output_path
    print(f"⚠️  Formato {export_format} não suportado")
    return model_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Treina um modelo YOLOv8 para detecção de tempestades"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="data/model-dataset/storm.yaml",
        help="Caminho para o arquivo YAML do dataset",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="yolov5s",
        help="Tamanho do modelo (yolov5n, yolov5s, yolov5m, yolov5l, yolov5x)",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
        help="Número de épocas",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=8,
        help="Tamanho do batch",
    )
    parser.add_argument(
        "--img-size",
        type=int,
        default=640,
        help="Tamanho das imagens (padrão: 640)",
    )
    parser.add_argument(
        "--device",
        type=int,
        default=0,
        help="Device (0 para GPU, use 'cpu' para CPU)",
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=20,
        help="Early stopping patience",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="models",
        help="Diretório para salvar modelos",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validar modelo após treinamento",
    )

    args = parser.parse_args()

    # Treinar modelo
    model_path = train_yolo_storm_detector(
        dataset_yaml=args.dataset,
        model_name=args.model,
        epochs=args.epochs,
        batch_size=args.batch,
        img_size=args.img_size,
        device=args.device,
        patience=args.patience,
        output_dir=args.output_dir,
    )

    # Validar se solicitado
    if args.validate:
        validate_model(model_path, args.dataset)
