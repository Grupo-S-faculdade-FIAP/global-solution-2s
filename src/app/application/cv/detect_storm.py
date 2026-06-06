"""Use case: DetectStormUseCase.

Encapsula todo o pipeline de detecção de tempestade:
  1. Download da imagem do S3
  2. Garantir modelo em /tmp (cache entre invocações Lambda)
  3. Inferência YOLO
  4. Se detectado: publicar SNS + persistir alerta
  5. Retornar resultado

Não importa fastapi, flask nem define rotas HTTP.
"""

from __future__ import annotations

import hashlib
import logging
import pathlib
from typing import TYPE_CHECKING, Any

from app.core.config import settings

if TYPE_CHECKING:
    from app.domain.cv.ports import StormAlertRepository

logger = logging.getLogger(__name__)

_TMP = pathlib.Path("/tmp")
_MODEL_LOCAL = _TMP / "storm_model.pt"
_YOLOV5_SRC = pathlib.Path("/opt/yolov5_src")
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
_LOCAL_WEIGHTS = _PROJECT_ROOT / "models" / "weights" / "best.pt"


def _deterministic_alert_id(bucket: str, key: str) -> str:
    """Idempotência: mesmo objeto S3 → mesmo alert_id em retries."""
    digest = hashlib.sha256(f"{bucket}/{key}".encode()).hexdigest()[:16]
    return f"storm_{digest}"


def _yolov5_repo() -> tuple[str, str]:
    """Lambda usa clone em /opt; dev local usa cache torch.hub."""
    if (_YOLOV5_SRC / "hubconf.py").exists():
        return str(_YOLOV5_SRC), "local"
    return "ultralytics/yolov5", "github"


def _allow_yolo_checkpoint_load() -> None:
    """Permite carregar checkpoints YOLOv5 no PyTorch 2.6+ (weights_only padrão=True)."""
    import torch  # noqa: PLC0415

    _orig_load = torch.load

    def _load(*args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("weights_only", False)
        return _orig_load(*args, **kwargs)

    torch.load = _load  # type: ignore[method-assign]


def _ensure_model() -> pathlib.Path:
    """Baixa pesos do S3 na partida fria; reutiliza em Lambda warm."""
    if _MODEL_LOCAL.exists():
        return _MODEL_LOCAL
    if _LOCAL_WEIGHTS.exists():
        logger.info("Using local model weights: %s", _LOCAL_WEIGHTS)
        return _LOCAL_WEIGHTS

    import boto3  # noqa: PLC0415

    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    logger.info(
        "Cold start: downloading model from s3://%s/%s",
        settings.S3_BUCKET_IMAGES,
        settings.YOLO_MODEL_S3_KEY,
    )
    s3.download_file(
        settings.S3_BUCKET_IMAGES,
        settings.YOLO_MODEL_S3_KEY,
        str(_MODEL_LOCAL),
    )
    logger.info("Model downloaded to %s", _MODEL_LOCAL)
    return _MODEL_LOCAL


def _run_yolo_inference(
    image_path: pathlib.Path, model_path: pathlib.Path
) -> list[dict[str, Any]]:
    """Executa inferência YOLO e retorna lista de detecções."""
    import torch  # noqa: PLC0415

    # Checkpoints treinados no Windows usam PosixPath no pickle (stormdetector.py).
    pathlib.PosixPath = pathlib.WindowsPath

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

    results = model(str(image_path))
    detections = []
    for *xyxy, conf, cls in results.pred[0].tolist():
        detections.append({
            "class": results.names[int(cls)],
            "confidence": round(conf, 4),
            "bbox": [round(v, 1) for v in xyxy],
        })
    return detections


class DetectStormUseCase:
    """Orquestra o pipeline CV: download S3 → YOLO → SNS → persist."""

    def __init__(self, repo: "StormAlertRepository") -> None:
        self._repo = repo

    def execute(self, bucket: str, key: str) -> dict[str, Any]:
        """
        Processa uma imagem de satélite armazenada no S3.

        Args:
            bucket: nome do bucket S3
            key: chave do objeto (ex: "screenshots/img.jpg")

        Returns:
            dict com bucket, key, detections, alert_sent, sns_message_id
        """
        import boto3  # noqa: PLC0415
        from app.services.sns_alerts import publish_storm_alert  # noqa: PLC0415

        image_local = _TMP / pathlib.Path(key).name
        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        logger.info("Downloading image s3://%s/%s", bucket, key)
        s3.download_file(bucket, key, str(image_local))

        model_path = _ensure_model()
        detections = _run_yolo_inference(image_local, model_path)

        alert_sent = False
        message_id = None
        duplicate = False

        if detections:
            logger.info("%d storm detections found — persisting alert", len(detections))
            alert_id = _deterministic_alert_id(bucket, key)
            saved = self._persist(bucket, key, detections, alert_id)
            duplicate = bool(saved.get("_duplicate"))
            if duplicate:
                logger.info("Alert already stored for s3://%s/%s — skipping SNS", bucket, key)
            else:
                message_id = publish_storm_alert(bucket, key, detections)
            alert_sent = True
        else:
            logger.info("No storm detected in %s", key)

        return {
            "bucket": bucket,
            "key": key,
            "detections": detections,
            "alert_sent": alert_sent,
            "duplicate": duplicate,
            "sns_message_id": message_id,
        }

    def _persist(
        self,
        bucket: str,
        key: str,
        detections: list[dict[str, Any]],
        alert_id: str,
    ) -> dict[str, Any]:
        confs = [
            d["confidence"]
            for d in detections
            if isinstance(d.get("confidence"), (int, float))
        ]
        max_confidence = max(confs) if confs else None
        return self._repo.save(
            s3_key=key,
            detection_count=len(detections),
            bucket=bucket,
            alert_id=alert_id,
            simulated=False,
            classes=list({d["class"] for d in detections}),
            confidence=max_confidence,
        )
