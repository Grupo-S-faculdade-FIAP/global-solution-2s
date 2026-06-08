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
PROJECT_ROOT    = Path(__file__).resolve().parent.parent
_BASE_DATASET   = PROJECT_ROOT / "data" / "model-dataset"
_AUG_DATASET    = PROJECT_ROOT / "data" / "training-dataset-1000"
_GOES_PIPELINE  = PROJECT_ROOT / "scripts" / "goes_pipeline"

# Usa dataset augmentado se existir e tiver imagens de treino
DATASET_ROOT = (
    _AUG_DATASET
    if (_AUG_DATASET / "images" / "train").exists()
    and any((_AUG_DATASET / "images" / "train").iterdir())
    else _BASE_DATASET
)


def _run_label_quality_gate() -> None:
    """Bloqueia treino se labels tiverem bboxes fantasma ou distribuição inválida."""
    if str(_GOES_PIPELINE) not in sys.path:
        sys.path.insert(0, str(_GOES_PIPELINE))
    from label_utils import audit_dataset, format_audit_summary, save_audit_report  # noqa: E402

    # Quality gate sempre roda sobre o dataset base (sem augmentação)
    report = audit_dataset(_BASE_DATASET)
    out = PROJECT_ROOT / "data" / "label_review" / "audit.json"
    data = save_audit_report(report, out)
    print(format_audit_summary(data))
    if not report.passed:
        raise RuntimeError(
            "Label quality gate FAILED — corrija o dataset antes de treinar.\n"
            "  python scripts/goes_pipeline/04_nasa_to_yolo.py --clean\n"
            "  python scripts/goes_pipeline/06_audit_labels.py --strict\n"
            f"  Relatório: {out}"
        )
    print("✅ Label quality gate passed\n")


def _resolved_dataset_yaml(dataset_yaml: str) -> Path:
    """Gera YAML com path absoluto para o YOLOv5 (cwd=yolov5/)."""
    resolved = DATASET_ROOT / "storm.resolved.yaml"
    resolved.write_text(
        f"path: {DATASET_ROOT}\n"
        "train: images/train\n"
        "val: images/val\n"
        "nc: 1\n"
        "names:\n"
        "  0: storm\n",
        encoding="utf-8",
    )
    print(f"📂 Dataset: {DATASET_ROOT}")
    return resolved


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
            [
                sys.executable, "-m", "pip", "install",
                "gitpython",
                "-r", str(yolov5_dir / "requirements.txt"),
                "--quiet",
                "--break-system-packages",
            ],
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
    run_name: str      = "storm-detector-v2",
    recall_focus: bool = False,
    cos_lr: bool       = False,
    skip_quality_gate: bool = False,
) -> Path:
    """
    Treina YOLOv5 para detecção de tempestades.

    Returns:
        Path para o melhor modelo treinado (best.pt)
    """
    yolov5_dir  = PROJECT_ROOT / "yolov5"
    dataset_abs = _resolved_dataset_yaml(dataset_yaml)
    project_abs = PROJECT_ROOT / project_dir

    if not DATASET_ROOT.exists():
        raise FileNotFoundError(f"Dataset dir não encontrado: {DATASET_ROOT}")

    if not skip_quality_gate:
        _run_label_quality_gate()

    _ensure_yolov5(yolov5_dir)

    print(f"\n🚀 Iniciando treinamento YOLOv5")
    print(f"   Dataset : {dataset_abs}")
    print(f"   Modelo  : {model_name}")
    print(f"   Épocas  : {epochs} | Batch: {batch_size} | Device: {device}\n")

    # Prioridade: hyp.v3.yaml > hyp.recall.yaml (ambos em data/model-dataset/)
    hyp_v3_path = PROJECT_ROOT / "data" / "model-dataset" / "hyp.v3.yaml"
    hyp_recall_path = DATASET_ROOT / "hyp.recall.yaml"
    hyp_path = hyp_v3_path if hyp_v3_path.exists() else hyp_recall_path

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
    if recall_focus and hyp_path.exists():
        cmd.extend(["--hyp", str(hyp_path)])
        hyp_label = "v3" if hyp_path == hyp_v3_path else "recall-focus"
        print(f"   Hyp     : {hyp_path} ({hyp_label})")
    if cos_lr:
        cmd.append("--cos-lr")
        print(f"   LR      : cosine decay")

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
    device: str = "cpu",
):
    """Valida o modelo treinado no conjunto de validação."""
    model_abs  = PROJECT_ROOT / model_path
    dataset_abs = _resolved_dataset_yaml(dataset_yaml)
    yolov5_dir  = PROJECT_ROOT / "yolov5"

    print(f"\n📊 Validando: {model_abs}")
    cmd = [
        sys.executable,
        str(yolov5_dir / "val.py"),
        "--weights", str(model_abs),
        "--data",    str(dataset_abs),
        "--device",  device,
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
    parser.add_argument("--validate-only", action="store_true",
                        help="Somente validar best.pt existente (sem treinar)")
    parser.add_argument("--recall-focus", action="store_true",
                        help="Usar hyp.recall.yaml (viés para recall)")
    parser.add_argument("--cos-lr", action="store_true",
                        help="Cosine LR decay (melhor convergência)")
    parser.add_argument("--skip-quality-gate", action="store_true",
                        help="Pular auditoria de labels (não recomendado)")
    parser.add_argument("--export",   choices=["onnx", "torchscript", "tflite"],
                        help="Exportar modelo após treinamento")

    args = parser.parse_args()

    if args.validate_only:
        validate_model("src/models/weights/best.pt", args.dataset, device=args.device)
        raise SystemExit(0)

    model_path = train_yolo_storm_detector(
        dataset_yaml=args.dataset,
        model_name=args.model,
        epochs=args.epochs,
        img_size=args.img_size,
        batch_size=args.batch,
        device=args.device,
        patience=args.patience,
        recall_focus=args.recall_focus,
        cos_lr=args.cos_lr,
        skip_quality_gate=args.skip_quality_gate,
    )

    if args.validate:
        validate_model(str(model_path), args.dataset, device=args.device)

    if args.export:
        export_model(str(model_path), args.export)
