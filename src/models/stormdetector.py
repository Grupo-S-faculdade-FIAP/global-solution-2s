import pathlib

import cv2
import torch
from pathlib import Path

# Checkpoints treinados no Windows usam PosixPath no pickle.
pathlib.PosixPath = pathlib.WindowsPath

YOLOV5_BRANCH = "v7.0"  # mesma versão usada no treino (Colab) e no Dockerfile/Lambda


def _allow_yolo_checkpoint_load() -> None:
    """PyTorch 2.6+ defaults weights_only=True; YOLOv5 .pt needs weights_only=False."""
    _orig_load = torch.load

    def _load(*args, **kwargs):
        kwargs.setdefault("weights_only", False)
        return _orig_load(*args, **kwargs)

    torch.load = _load  # type: ignore[method-assign]


_allow_yolo_checkpoint_load()

BASE_DIR = Path(__file__).parent
weights_path = str(BASE_DIR / "weights" / "best.pt")
image_path = str(
    BASE_DIR.parent.parent / "data" / "model-dataset" / "images" / "test" / "test-storm.png"
)

model = torch.hub.load(
    f"ultralytics/yolov5:{YOLOV5_BRANCH}",
    "custom",
    weights_path,
    trust_repo=True,
)
model.conf = 0.25

print(f"Weights: {weights_path}")
print(f"Image:   {image_path}")

# Passar o caminho (PIL/RGB), igual no Colab: model('image.png').
# cv2.imread() retorna BGR e o AutoShape do YOLOv5 v7.0 NÃO converte arrays numpy.
results = model(image_path)
print(results)

# OpenCV 4.11+ cannot draw on the read-only array returned by results.render().
frame = cv2.imread(image_path)
if frame is None:
    raise FileNotFoundError(f"Could not load image: {image_path}")

for x1, y1, x2, y2, conf, cls in results.xyxy[0].tolist():
    x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))
    label = f"{results.names[int(cls)]} {conf:.2f}"
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(
        frame,
        label,
        (x1, max(y1 - 10, 0)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 255, 0),
        2,
    )

frame = cv2.resize(frame, (1280, 720))
cv2.imshow("Deteccao", frame)
cv2.waitKey(0)
cv2.destroyAllWindows()
