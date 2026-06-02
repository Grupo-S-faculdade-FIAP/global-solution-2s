"""
Script de treinamento do modelo YOLOv8 para detecção de tempestades.

Uso:
    python3 yolo_training.py --epochs 50 --img-size 640 --batch 8
"""

import argparse
import sys
from pathlib import Path

try:
    from ultralytics import YOLO
except ImportError:
    print("❌ ultralytics não instalado. Execute:")
    print("   pip install ultralytics")
    sys.exit(1)


def train_yolo_storm_detector(
    dataset_yaml: str = "data/model-dataset/storm.yaml",
    model_name: str = "yolov8s",
    epochs: int = 50,
    img_size: int = 640,
    batch_size: int = 8,
    device: int = 0,
    patience: int = 20,
    output_dir: str = "models",
) -> str:
    """
    Treina um modelo YOLOv8 para detecção de tempestades.

    Args:
        dataset_yaml: Caminho para o arquivo YAML do dataset
        model_name: Tamanho do modelo ('yolov8n', 'yolov8s', 'yolov8m', 'yolov8l', 'yolov8x')
        epochs: Número de épocas de treinamento
        img_size: Tamanho das imagens (default 640)
        batch_size: Tamanho do batch
        device: GPU/CPU device (0 para GPU, "cpu" para CPU)
        patience: Early stopping patience (em épocas)
        output_dir: Diretório para salvar modelos

    Returns:
        Caminho para o modelo treinado (.pt)
    """
    print(f"🚀 Iniciando treinamento do YOLOv8-Storm Detector...")
    print(f"   Dataset: {dataset_yaml}")
    print(f"   Modelo: {model_name}")
    print(f"   Épocas: {epochs}")
    print(f"   Batch size: {batch_size}")
    print()

    # Criar diretório de saída se não existir
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Carregar modelo base
    print(f"📦 Carregando modelo base: {model_name}...")
    model = YOLO(f"{model_name}.pt")

    # Treinar
    print(f"🎓 Treinando...")
    results = model.train(
        data=dataset_yaml,
        epochs=epochs,
        imgsz=img_size,
        batch=batch_size,
        device=device,
        patience=patience,
        project=output_dir,
        name="yolov8-storm-detector",
        save=True,
        verbose=True,
        plots=True,  # Gera gráficos de treino
    )

    # Salvar modelo otimizado
    model_path = Path(output_dir) / "yolov8-storm-detector" / "weights" / "best.pt"
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
    model = YOLO(model_path)
    metrics = model.val(data=dataset_yaml)
    print(f"✅ Validação concluída!")
    return metrics


def export_model(model_path: str, export_format: str = "onnx"):
    """
    Exporta o modelo para diferentes formatos (ONNX, TensorFlow, etc).

    Args:
        model_path: Caminho para o modelo .pt
        export_format: Formato de exportação ('onnx', 'torchscript', 'tflite', etc)
    """
    print(f"\n🔄 Exportando modelo para {export_format}...")
    model = YOLO(model_path)
    exported_path = model.export(format=export_format)
    print(f"✅ Modelo exportado: {exported_path}")
    return exported_path


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
        default="yolov8s",
        help="Tamanho do modelo (yolov8n, yolov8s, yolov8m, yolov8l, yolov8x)",
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
