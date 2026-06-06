"""Publicação e inscrição de alertas de tempestade via Amazon SNS."""

from __future__ import annotations

import logging
import re
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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


def _normalize_email(email: str) -> str:
    """Valida e normaliza e-mail para inscrição SNS."""
    normalized = (email or "").strip().lower()
    if not normalized or not _EMAIL_RE.match(normalized):
        raise ValueError("E-mail inválido")
    return normalized


def subscribe_email(email: str) -> dict[str, Any]:
    """
    Inscreve e-mail no tópico SNS (Protocol=email).

    A AWS envia link de confirmação — o alerta só chega após o usuário confirmar.
    """
    if not sns_is_configured():
        return {
            "success": False,
            "configured": False,
            "error": "SNS não configurado — defina SNS_TOPIC_ARN no ambiente AWS",
        }

    try:
        endpoint = _normalize_email(email)
    except ValueError as exc:
        return {"success": False, "configured": True, "error": str(exc)}

    topic_arn = settings.SNS_TOPIC_ARN.strip()
    try:
        sns = boto3.client("sns", region_name=settings.AWS_REGION)
        response = sns.subscribe(
            TopicArn=topic_arn,
            Protocol="email",
            Endpoint=endpoint,
        )
    except (ClientError, BotoCoreError) as exc:
        logger.error("SNS subscribe failed for %s: %s", endpoint, exc)
        return {
            "success": False,
            "configured": True,
            "error": "Falha ao inscrever e-mail no SNS",
        }

    subscription_arn = response.get("SubscriptionArn", "")
    pending = subscription_arn == "pending confirmation"
    return {
        "success": True,
        "configured": True,
        "email": endpoint,
        "subscription_arn": subscription_arn or None,
        "pending_confirmation": pending,
        "message": (
            "Enviamos um e-mail de confirmação da AWS. "
            "Abra o link \"Confirm subscription\" para ativar os alertas."
        ),
    }


def publish_simulated_alert(lat: float, lon: float, confidence: float) -> str | None:
    """Publica alerta simulado (dashboard) no tópico SNS configurado."""
    if not sns_is_configured():
        logger.info("SNS not configured — skipping simulated publish")
        return None

    subject_base = settings.SNS_ALERT_SUBJECT.strip() or "Rain Alert — Storm Detected"
    subject = f"{subject_base} [Simulated]"
    message = (
        f"Simulated storm alert from dashboard.\n"
        f"Location: {lat:.4f}, {lon:.4f}\n"
        f"Confidence: {confidence:.2%}\n"
        f"Project: {settings.PROJECT_NAME}"
    ).rstrip()
    topic_arn = settings.SNS_TOPIC_ARN.strip()

    try:
        sns = boto3.client("sns", region_name=settings.AWS_REGION)
        response = sns.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message,
        )
    except (ClientError, BotoCoreError) as exc:
        logger.error("SNS simulated publish failed: %s", exc)
        return None

    message_id = response.get("MessageId")
    logger.info("SNS simulated alert published: MessageId=%s", message_id)
    return message_id
