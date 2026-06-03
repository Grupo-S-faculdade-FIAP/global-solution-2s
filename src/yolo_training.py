"""
Script de treinamento do modelo YOLOv5 para detecção de tempestades.

Pré-requisitos:
    pip install torch torchvision

Uso (a partir do root do projeto — global-solutions/):
    python src/yolo_training.py
    python src/yolo_training.py --epochs 100 --batch 16
    python src/yolo_training.py --validate
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Root do projeto = dois níveis acima deste arquivo (src/yolo_training.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _ensure_yolov5(yolov5_dir: Path) -> Path:
    """
    Garante que o repositório YOLOv5 existe localmente.
    Clona se necessário.
    """
    if yolov5_dir.exists() and (yolov5_dir / "train.py").exists():
        return yolov5_dir

    print("📦 Clonando repositório YOLOv5...")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1",
             "https://github.com/ultralytics/yolov5",
             str(yolov5_dir)],
            check=True,
        )
        subprocess.run(
            [sys.executable, "-m", "pip", "install",
             "-r", str(yolov5_dir / "requirements.txt"),
             "--quiet"],
            check=True,
        )
        print("✅ YOLOv5 clonado com sucesso")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Não foi possível clonar o YOLOv5: {e}\n"
            "Verifique sua conexão ou clone manualmente em 'yolov5/'."
        )
    return yolov5_dir


def train_yolo_storm_detector(
    dataset_yaml: str  = "data/model-dataset/storm.yaml",
    model_name: str    = "yolov5s",
    epochs: int        = 50,
    img_size: int      = 640,
    batch_size: int    = 8,
    device: str        = "cpu",
    patience: int      = 20,
    project_dir: str   = "runs/train",
    run_name: str      = "storm-detector",
) -> Path:
    """
    Treina YOLOv5 para detecção de tempestades.

    Returns:
        Path para o melhor modelo treinado (best.pt)
    """
    yolov5_dir  = PROJECT_ROOT / "yolov5"
    dataset_abs = PROJECT_ROOT / dataset_yaml
    project_abs = PROJECT_ROOT / project_dir

    if not dataset_abs.exists():
        raise FileNotFoundError(f"Dataset YAML não encontrado: {dataset_abs}")

    _ensure_yolov5(yolov5_dir)

    print(f"\n🚀 Iniciando treinamento YOLOv5")
    print(f"   Dataset : {dataset_abs}")
    print(f"   Modelo  : {model_name}")
    print(f"   Épocas  : {epochs} | Batch: {batch_size} | Device: {device}\n")

    cmd = [
        sys.executable,
        str(yolov5_dir / "train.py"),
        "--img",      str(img_size),
        "--batch",    str(batch_size),
        "--epochs",   str(epochs),
        "--data",     str(dataset_abs),
        "--weights",  f"{model_name}.pt",
        "--device",   device,
        "--patience", str(patience),
        "--project",  str(project_abs),
        "--name",     run_name,
        "--exist-ok",
    ]

    result = subprocess.run(cmd, cwd=str(yolov5_dir))
    if result.returncode != 0:
        raise RuntimeError("Treinamento falhou. Verifique a saída acima.")

    best_model = project_abs / run_name / "weights" / "best.pt"

    # Copiar para o caminho padrão do projeto
    dest = PROJECT_ROOT / "src" / "models" / "weights" / "best.pt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if best_model.exists():
        shutil.copy2(str(best_model), str(dest))
        print(f"\n✅ Modelo salvo em: {dest}")
    else:
        print(f"⚠️  best.pt não encontrado em {best_model}")

    return dest


def validate_model(
    model_path: str = "src/models/weights/best.pt",
    dataset_yaml: str = "data/model-dataset/storm.yaml",
):
    """Valida o modelo treinado no conjunto de validação."""
    model_abs  = PROJECT_ROOT / model_path
    dataset_abs = PROJECT_ROOT / dataset_yaml
    yolov5_dir  = PROJECT_ROOT / "yolov5"

    print(f"\n📊 Validando: {model_abs}")
    cmd = [
        sys.executable,
        str(yolov5_dir / "val.py"),
        "--weights", str(model_abs),
        "--data",    str(dataset_abs),
        "--device",  "cpu",
    ]
    subprocess.run(cmd, cwd=str(yolov5_dir), check=True)
    print("✅ Validação concluída")


def export_model(
    model_path: str    = "src/models/weights/best.pt",
    export_format: str = "onnx",
):
    """Exporta o modelo para ONNX ou outros formatos."""
    yolov5_dir = PROJECT_ROOT / "yolov5"
    model_abs  = PROJECT_ROOT / model_path

    print(f"\n🔄 Exportando para {export_format}...")
    cmd = [
        sys.executable,
        str(yolov5_dir / "export.py"),
        "--weights", str(model_abs),
        "--include", export_format,
    ]
    subprocess.run(cmd, cwd=str(yolov5_dir), check=True)
    print("✅ Exportação concluída")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Treina YOLOv5 para detecção de tempestades",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--dataset",  default="data/model-dataset/storm.yaml")
    parser.add_argument("--model",    default="yolov5s",
                        choices=["yolov5n", "yolov5s", "yolov5m", "yolov5l", "yolov5x"])
    parser.add_argument("--epochs",   type=int, default=50)
    parser.add_argument("--batch",    type=int, default=8)
    parser.add_argument("--img-size", type=int, default=640)
    parser.add_argument("--device",   default="cpu",
                        help="'cpu', '0' para GPU 0, '0,1' para multi-GPU")
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--validate", action="store_true",
                        help="Validar modelo após treinamento")
    parser.add_argument("--export",   choices=["onnx", "torchscript", "tflite"],
                        help="Exportar modelo após treinamento")

    args = parser.parse_args()

    model_path = train_yolo_storm_detector(
        dataset_yaml=args.dataset,
        model_name=args.model,
        epochs=args.epochs,
        img_size=args.img_size,
        batch_size=args.batch,
        device=args.device,
        patience=args.patience,
    )

    if args.validate:
        validate_model(str(model_path), args.dataset)

    if args.export:
        export_model(str(model_path), args.export)
