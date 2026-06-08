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
import pickle
import random
import time
from typing import TYPE_CHECKING, Any

from app.core.config import settings
from app.core.xray_tracing import xray_traced, xray_subsegment, xray_metadata

if TYPE_CHECKING:
    from app.domain.cv.ports import StormAlertRepository

logger = logging.getLogger(__name__)

_TMP = pathlib.Path("/tmp")
_MODEL_LOCAL = _TMP / "storm_model.pt"
_YOLOV5_SRC = pathlib.Path("/opt/yolov5_src")
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
_LOCAL_WEIGHTS = _PROJECT_ROOT / "models" / "weights" / "best.pt"


def _exponential_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 32.0) -> None:
    """Sleep com exponential backoff + jitter (evita thundering herd).

    Formula: sleep_time = min(base_delay * 2^attempt + random_jitter, max_delay)

    Args:
        attempt: Número da tentativa (começando em 0).
        base_delay: Delay inicial em segundos.
        max_delay: Delay máximo em segundos.
    """
    sleep_time = min(base_delay * (2 ** attempt), max_delay)
    # Adiciona jitter aleatório (0-50% do sleep_time)
    jitter = random.uniform(0, sleep_time * 0.5)
    total_sleep = sleep_time + jitter
    logger.debug("Backoff: sleeping %.2fs (attempt %d)", total_sleep, attempt)
    time.sleep(total_sleep)


def _deterministic_alert_id(bucket: str, key: str) -> str:
    """Idempotência: mesmo objeto S3 → mesmo alert_id em retries."""
    digest = hashlib.sha256(f"{bucket}/{key}".encode()).hexdigest()[:16]
    return f"storm_{digest}"


def _yolov5_repo() -> tuple[str, str]:
    """Lambda usa clone em /opt; dev local usa cache torch.hub."""
    if (_YOLOV5_SRC / "hubconf.py").exists():
        return str(_YOLOV5_SRC), "local"
    return "ultralytics/yolov5", "github"


def _safe_torch_load(path: str, weights_only: bool = False) -> Any:
    """Carrega modelo PyTorch com fallback seguro para pesos desserializáveis.

    Args:
        path: Caminho do arquivo .pt
        weights_only: Se True, apenas pesos serão desserializados (mais seguro).
                     Se False, permite code execution (necessário para YOLO).

    Returns:
        Modelo carregado.

    Raises:
        RuntimeError: Se torch.load falhar mesmo com fallback.
    """
    import torch  # noqa: PLC0415

    try:
        # Tenta com weights_only=False para suportar YOLO checkpoints
        return torch.load(path, weights_only=False)
    except (RuntimeError, pickle.UnpicklingError) as exc:
        logger.warning("Failed to load with weights_only=False: %s. Retrying...", exc)
        try:
            # Fallback: tenta com weights_only=True (apenas pesos)
            return torch.load(path, weights_only=True)
        except Exception as exc2:
            logger.error("Failed to load weights with both strategies: %s, %s", exc, exc2)
            raise RuntimeError(f"Cannot load model from {path}: {exc2}") from exc2


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
    for attempt in range(max_retries):
        try:
            s3 = boto3.client("s3", region_name=settings.AWS_REGION)
            logger.info(
                "Cold start (attempt %d/%d): downloading model from s3://%s/%s",
                attempt + 1, max_retries,
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
            if attempt < max_retries - 1:
                logger.warning(
                    "S3 download failed (attempt %d/%d): %s. Retrying with backoff...",
                    attempt + 1, max_retries, exc,
                )
                _exponential_backoff(attempt, base_delay=1.0, max_delay=8.0)
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

    Carrega modelo com torch.load (weights_only=False para YOLO) e executa
    inferência na imagem fornecida.

    Raises:
        ValueError: Se imagem for inválida.
        RuntimeError: Erros do modelo YOLO.
    """
    import torch  # noqa: PLC0415

    try:
        # YOLOv5 checkpoints need full pickle loading on PyTorch 2.6+.
        _allow_yolo_checkpoint_load(torch)
        torch.hub.set_dir("/tmp/torch_hub")
        repo, source = _yolov5_repo()

        if source == "local":
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
    except Exception as exc:
        logger.error("YOLO inference failed: %s", exc)
        raise


def _allow_yolo_checkpoint_load(torch_module: Any) -> None:
    """PyTorch 2.6+ defaults to weights_only=True; YOLOv5 .pt needs False."""
    original_load = torch_module.load

    if getattr(original_load, "_gs2_yolo_weights_patch", False):
        return

    def load_with_checkpoint_support(*args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("weights_only", False)
        return original_load(*args, **kwargs)

    load_with_checkpoint_support._gs2_yolo_weights_patch = True  # type: ignore[attr-defined]
    torch_module.load = load_with_checkpoint_support


class DetectStormUseCase:
    """Orquestra o pipeline CV: download S3 → YOLO → SNS → persist."""

    def __init__(self, repo: "StormAlertRepository") -> None:
        self._repo = repo

    @xray_traced(name="detect_storm_pipeline")
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
            with xray_subsegment("s3_download_image"):
                s3 = boto3.client("s3", region_name=settings.AWS_REGION)
                logger.info("Downloading image s3://%s/%s", bucket, key)
                xray_metadata("bucket", bucket)
                xray_metadata("key", key)
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        s3.download_file(bucket, key, str(image_local))
                        break
                    except ClientError as exc:
                        if attempt < max_retries - 1:
                            logger.warning(
                                "S3 download failed (attempt %d/%d): %s. Retrying with backoff...",
                                attempt + 1, max_retries, exc,
                            )
                            _exponential_backoff(attempt, base_delay=0.5, max_delay=4.0)
                        else:
                            logger.error(
                                "S3 download failed after %d attempts: %s",
                                max_retries, exc,
                            )
                            raise

            with xray_subsegment("ensure_model"):
                model_path = _ensure_model()

            with xray_subsegment("yolo_inference"):
                detections = _run_yolo_inference(image_local, model_path)
                xray_metadata("detection_count", len(detections))

            alert_sent = False
            message_id = None
            duplicate = False

            if detections:
                logger.info("%d storm detections found — persisting alert", len(detections))
                alert_id = _deterministic_alert_id(bucket, key)

                with xray_subsegment("persist_alert"):
                    saved = self._persist(bucket, key, detections, alert_id)
                    duplicate = bool(saved.get("_duplicate"))
                    xray_metadata("alert_id", alert_id)
                    xray_metadata("duplicate", duplicate)

                if duplicate:
                    logger.info("Alert already stored for s3://%s/%s — skipping SNS", bucket, key)
                else:
                    with xray_subsegment("publish_sns_alert"):
                        message_id = publish_storm_alert(bucket, key, detections)
                        xray_metadata("sns_message_id", message_id)
                alert_sent = True
            else:
                logger.info("No storm detected in %s", key)
                xray_metadata("detection_found", False)

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
