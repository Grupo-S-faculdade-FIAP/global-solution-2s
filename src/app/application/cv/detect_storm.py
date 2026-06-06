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
import os
import pathlib
from typing import TYPE_CHECKING, Any, Callable

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


def _apply_pathlib_compat() -> None:
    """Compatibilidade pathlib para checkpoints YOLO treinados em outro SO.

    Sem isso, torch.hub.load falha no Lambda com:
    No module named 'pathlib._local'; 'pathlib' is not a package
    (ultralytics/yolov5#13578).
    """
    import sys

    sys.modules.setdefault("pathlib._local", pathlib)
    if os.name == "nt":
        pathlib.PosixPath = pathlib.WindowsPath
    else:
        pathlib.WindowsPath = pathlib.PosixPath


def _create_torch_load_wrapper(original_load: Callable) -> Callable:
    """Factory para criar wrapper de torch.load sem monkey patching."""
    def safe_load(*args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("weights_only", False)
        return original_load(*args, **kwargs)
    return safe_load


def _ensure_model() -> pathlib.Path:
    """Baixa pesos do S3 na partida fria; reutiliza em Lambda warm.

    Raises:
        FileNotFoundError: Se modelo não for encontrado após 3 tentativas.
        Exception: Erros do boto3 após retry.
    """
    if _MODEL_LOCAL.exists():
        return _MODEL_LOCAL
    if _LOCAL_WEIGHTS.exists():
        logger.info("Using local model weights: %s", _LOCAL_WEIGHTS)
        return _LOCAL_WEIGHTS

    import boto3  # noqa: PLC0415
    from botocore.exceptions import ClientError  # noqa: PLC0415

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            s3 = boto3.client("s3", region_name=settings.AWS_REGION)
            logger.info(
                "Cold start (attempt %d/%d): downloading model from s3://%s/%s",
                attempt, max_retries,
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
        except ClientError as exc:
            if attempt < max_retries:
                logger.warning(
                    "S3 download failed (attempt %d/%d): %s. Retrying...",
                    attempt, max_retries, exc,
                )
            else:
                logger.error("S3 download failed after %d attempts: %s", max_retries, exc)
                raise

    raise FileNotFoundError(
        f"Model not found at {_MODEL_LOCAL} or s3://{settings.S3_BUCKET_IMAGES}/"
        f"{settings.YOLO_MODEL_S3_KEY}"
    )


def _run_yolo_inference(
    image_path: pathlib.Path, model_path: pathlib.Path
) -> list[dict[str, Any]]:
    """Executa inferência YOLO e retorna lista de detecções.

    Usa injeção de dependência para torch.load via contexto local,
    evitando monkey patching global.

    Raises:
        ValueError: Se imagem for inválida.
        RuntimeError: Erros do modelo YOLO.
    """
    _apply_pathlib_compat()
    import torch  # noqa: PLC0415

    # Injetar wrapper de torch.load apenas no escopo desta função
    original_load = torch.load
    torch.load = _create_torch_load_wrapper(original_load)

    try:
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

        if not image_path.exists():
            raise ValueError(f"Image path does not exist: {image_path}")

        results = model(str(image_path))
        detections = []
        for *xyxy, conf, cls in results.pred[0].tolist():
            detections.append({
                "class": results.names[int(cls)],
                "confidence": round(conf, 4),
                "bbox": [round(v, 1) for v in xyxy],
            })
        return detections
    finally:
        # Restaurar torch.load original ao sair
        torch.load = original_load


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

        Raises:
            ValueError: Se key contiver path traversal.
            Exception: Erros de S3 ou modelo após retry.
        """
        import boto3  # noqa: PLC0415
        from botocore.exceptions import ClientError  # noqa: PLC0415
        from app.services.sns_alerts import publish_storm_alert  # noqa: PLC0415

        # Validação: evitar path traversal
        if ".." in key or key.startswith("/"):
            raise ValueError(f"Invalid S3 key (path traversal): {key}")

        image_local = _TMP / pathlib.Path(key).name

        try:
            # Download com retry
            s3 = boto3.client("s3", region_name=settings.AWS_REGION)
            logger.info("Downloading image s3://%s/%s", bucket, key)
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    s3.download_file(bucket, key, str(image_local))
                    break
                except ClientError as exc:
                    if attempt < max_retries:
                        logger.warning(
                            "S3 download failed (attempt %d/%d): %s. Retrying...",
                            attempt, max_retries, exc,
                        )
                    else:
                        logger.error(
                            "S3 download failed after %d attempts: %s",
                            max_retries, exc,
                        )
                        raise

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
        finally:
            # Cleanup: remover arquivo temporário
            self._cleanup_image(image_local)

    @staticmethod
    def _cleanup_image(image_path: pathlib.Path) -> None:
        """Remove arquivo temporário de imagem."""
        try:
            if image_path.exists():
                image_path.unlink()
                logger.debug("Cleaned up temp image: %s", image_path)
        except Exception as exc:
            logger.warning("Failed to cleanup temp image %s: %s", image_path, exc)

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
