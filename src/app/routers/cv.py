import logging
import os
import pathlib
from typing import Optional

import boto3
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.services.storm_alerts_store import add_alert


logger = logging.getLogger(__name__)
router = APIRouter()


class DetectStormRequest(BaseModel):
    s3_key: str
    bucket: Optional[str] = None

# /tmp persists across warm Lambda invocations — model is only downloaded once per container.
_TMP = pathlib.Path("/tmp")
_MODEL_LOCAL = _TMP / "storm_model.pt"


def _ensure_model() -> pathlib.Path:
    """Download model weights from S3 to /tmp on cold start; reuse on warm start."""
    if _MODEL_LOCAL.exists():
        return _MODEL_LOCAL
    if _LOCAL_WEIGHTS.exists():
        logger.info("Using local model weights: %s", _LOCAL_WEIGHTS)
        return _LOCAL_WEIGHTS

    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    logger.info(
        "Cold start: downloading model from s3://%s/%s",
        settings.S3_BUCKET_IMAGES,
        settings.YOLO_MODEL_S3_KEY,
    )
    s3.download_file(settings.S3_BUCKET_IMAGES, settings.YOLO_MODEL_S3_KEY, str(_MODEL_LOCAL))
    logger.info("Model downloaded to %s", _MODEL_LOCAL)
    return _MODEL_LOCAL


_YOLOV5_SRC = pathlib.Path("/opt/yolov5_src")
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
_LOCAL_WEIGHTS = _PROJECT_ROOT / "models" / "weights" / "best.pt"


def _yolov5_repo() -> tuple[str, str]:
    """Lambda usa clone em /opt; dev local usa cache torch.hub (ultralytics/yolov5)."""
    if (_YOLOV5_SRC / "hubconf.py").exists():
        return str(_YOLOV5_SRC), "local"
    return "ultralytics/yolov5", "github"


def _allow_yolo_checkpoint_load() -> None:
    """
    YOLOv5 .pt files are full pickle checkpoints. PyTorch 2.6+ defaults
    torch.load(..., weights_only=True), which rejects DetectionModel.
    Local stormdetector.py works on older torch; Lambda ships 2.6+cpu.
    """
    import torch  # noqa: PLC0415

    _orig_load = torch.load

    def _load(*args, **kwargs):
        kwargs.setdefault("weights_only", False)
        return _orig_load(*args, **kwargs)

    torch.load = _load  # type: ignore[method-assign]


def _run_yolo_inference(image_path: pathlib.Path, model_path: pathlib.Path) -> list[dict]:
    """
    Inference using the same pattern as src/models/stormdetector.py (the local reference impl).
    Lambda: torch.hub.load from /opt/yolov5_src. Dev: ultralytics/yolov5 from hub cache.
    """
    import torch  # noqa: PLC0415

    _allow_yolo_checkpoint_load()
    repo, source = _yolov5_repo()
    if source == "local":
        torch.hub.set_dir("/tmp/torch_hub")
        model = torch.hub.load(
            repo,
            "custom",
            path=str(model_path),
            source="local",
            force_reload=False,
            verbose=False,
        )
    else:
        model = torch.hub.load(
            repo,
            "custom",
            path=str(model_path),
            force_reload=False,
            verbose=False,
        )
    model.conf = settings.YOLO_CONFIDENCE_THRESHOLD
    model.iou = settings.YOLO_IOU_THRESHOLD

    # Pass file path (PIL/RGB). cv2.imread() is BGR; YOLOv5 v7 AutoShape does not convert numpy BGR.
    results = model(str(image_path))

    detections = []
    for *xyxy, conf, cls in results.pred[0].tolist():
        detections.append({
            "class": results.names[int(cls)],
            "confidence": round(conf, 4),
            "bbox": [round(v, 1) for v in xyxy],
        })
    return detections


def _publish_alert(bucket: str, key: str, detections: list[dict]) -> str | None:
    """Publishes a rain-alert message to SNS and returns the MessageId."""
    topic = (settings.SNS_TOPIC_ARN or "").strip()
    if not topic:
        logger.info("SNS_TOPIC_ARN not set — skipping SNS publish")
        return None

    sns = boto3.client("sns", region_name=settings.AWS_REGION)
    classes_found = ", ".join({d["class"] for d in detections})
    message = (
        f"Storm detected in satellite image.\n"
        f"Source: s3://{bucket}/{key}\n"
        f"Classes: {classes_found}\n"
        f"Detections: {len(detections)}"
    )
    response = sns.publish(
        TopicArn=topic,
        Subject="Rain Alert — Storm Detected",
        Message=message,
    )
    return response["MessageId"]


def _persist_cv_alert(bucket: str, key: str, detections: list[dict], message_id: str | None) -> None:
    """Persiste alerta via storm_alerts_store (mock JSON ou DynamoDB AWS)."""
    add_alert(
        s3_key=key,
        detection_count=len(detections),
        bucket=bucket,
        alert_id=message_id,
        simulated=False,
        classes=list({d["class"] for d in detections}),
    )


def process_s3_image(bucket: str, key: str) -> dict:
    """
    Full CV pipeline for a satellite image stored in S3.

    Called automatically by the S3 trigger (via main.handler) on .jpg upload,
    or manually via POST /cv/detect/storm.

    Steps:
      1. Download image from S3 to /tmp
      2. Ensure model weights are cached in /tmp (cold-start download from S3)
      3. Run YOLOv5 inference
      4. If storm detected: publish SNS alert + persist record in DynamoDB
    """
    image_local = _TMP / pathlib.Path(key).name
    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    logger.info("Downloading image s3://%s/%s", bucket, key)
    s3.download_file(bucket, key, str(image_local))

    model_path = _ensure_model()
    detections = _run_yolo_inference(image_local, model_path)

    alert_sent = False
    message_id = None
    if detections:
        logger.info("%d storm detections found — sending alert", len(detections))
        message_id = _publish_alert(bucket, key, detections)
        _persist_cv_alert(bucket, key, detections, message_id)
        alert_sent = True
    else:
        logger.info("No storm detected in %s", key)

    return {
        "bucket": bucket,
        "key": key,
        "detections": detections,
        "alert_sent": alert_sent,
        "sns_message_id": message_id,
    }


@router.get("/status")
def cv_status():
    """Status do módulo de Computer Vision."""
    return {"module": "computer_vision", "status": "ready"}


@router.post("/detect/storm")
async def detect_storm(body: DetectStormRequest):
    """
    Dispara o pipeline de detecção de tempestades/nuvens de chuva para uma imagem já
    presente no S3. Use este endpoint para testes manuais; em produção o
    trigger é automático via S3 → Lambda.

    Body:
      - s3_key: caminho do objeto no bucket (ex: "screenshots/img.jpg")
      - bucket: nome do bucket (opcional; usa S3_BUCKET_IMAGES do ambiente se omitido)
    """
    bucket = body.bucket or settings.S3_BUCKET_IMAGES
    return process_s3_image(bucket=bucket, key=body.s3_key)
