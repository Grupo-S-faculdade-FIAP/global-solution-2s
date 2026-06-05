"""Publicação de alertas de tempestade via Amazon SNS."""

from __future__ import annotations

import logging
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


def sns_is_configured() -> bool:
    """True quando SNS está habilitado e SNS_TOPIC_ARN está definido."""
    if not settings.SNS_ENABLED:
        return False
    return bool((settings.SNS_TOPIC_ARN or "").strip())


def sns_status() -> dict[str, Any]:
    """Resumo da configuração SNS (sem expor segredos)."""
    topic = (settings.SNS_TOPIC_ARN or "").strip()
    return {
        "enabled": settings.SNS_ENABLED,
        "configured": sns_is_configured(),
        "topic_arn": topic or None,
        "region": settings.AWS_REGION,
    }


def _build_storm_message(bucket: str, key: str, detections: list[dict[str, Any]]) -> tuple[str, str]:
    classes_found = ", ".join(sorted({str(d.get("class", "unknown")) for d in detections}))
    confidences = [
        float(d["confidence"])
        for d in detections
        if isinstance(d.get("confidence"), (int, float))
    ]
    max_conf = max(confidences) if confidences else None
    conf_line = f"Max confidence: {max_conf:.2%}\n" if max_conf is not None else ""

    subject = settings.SNS_ALERT_SUBJECT.strip() or "Rain Alert — Storm Detected"
    message = (
        f"Storm detected in satellite image.\n"
        f"Source: s3://{bucket}/{key}\n"
        f"Classes: {classes_found}\n"
        f"Detections: {len(detections)}\n"
        f"{conf_line}"
        f"Project: {settings.PROJECT_NAME}"
    ).rstrip()
    return subject, message


def publish_storm_alert(
    bucket: str,
    key: str,
    detections: list[dict[str, Any]],
) -> str | None:
    """
    Publica alerta de tempestade no tópico SNS configurado.

    Returns MessageId on success, None when skipped or on recoverable failure.
    """
    if not detections:
        return None

    if not sns_is_configured():
        logger.info("SNS not configured — skipping publish (set SNS_TOPIC_ARN on Lambda)")
        return None

    topic_arn = settings.SNS_TOPIC_ARN.strip()
    subject, message = _build_storm_message(bucket, key, detections)

    try:
        sns = boto3.client("sns", region_name=settings.AWS_REGION)
        response = sns.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message,
        )
    except (ClientError, BotoCoreError) as exc:
        logger.error("SNS publish failed for s3://%s/%s: %s", bucket, key, exc)
        return None

    message_id = response.get("MessageId")
    logger.info("SNS alert published: MessageId=%s topic=%s", message_id, topic_arn)
    return message_id
