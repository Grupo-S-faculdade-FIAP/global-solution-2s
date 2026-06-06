"""Publicação e inscrição de alertas de tempestade via Amazon SNS."""

from __future__ import annotations

import logging
import re
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_transient_error(exc: Exception) -> bool:
    """Check if an error is transient and should be retried.

    Args:
        exc: Exception to evaluate.

    Returns:
        True if error is transient (Throttling, ServiceUnavailable), False otherwise.
    """
    if isinstance(exc, ClientError):
        error_code = exc.response.get("Error", {}).get("Code", "")
        # Transient errors that should be retried
        return error_code in ("Throttling", "ServiceUnavailable", "RequestLimitExceeded")
    return False


def _is_permanent_error(exc: Exception) -> bool:
    """Check if an error is permanent and should not be retried.

    Args:
        exc: Exception to evaluate.

    Returns:
        True if error is permanent (AuthorizationError, InvalidParameter), False otherwise.
    """
    if isinstance(exc, ClientError):
        error_code = exc.response.get("Error", {}).get("Code", "")
        # Permanent errors that should NOT be retried
        return error_code in ("AuthorizationError", "InvalidParameter", "NotFound", "InvalidParameterException")
    return False


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


def _put_cloudwatch_metric(metric_name: str, value: float = 1.0, unit: str = "Count") -> None:
    """Put a metric to CloudWatch.

    Args:
        metric_name: Name of the metric (e.g., "StormAlertsSent").
        value: Metric value. Defaults to 1.
        unit: Unit of measurement. Defaults to "Count".
    """
    try:
        cloudwatch = boto3.client("cloudwatch", region_name=settings.AWS_REGION)
        cloudwatch.put_metric_data(
            Namespace="GlobalSolutions",
            MetricData=[
                {
                    "MetricName": metric_name,
                    "Value": value,
                    "Unit": unit,
                },
            ],
        )
        logger.debug(f"CloudWatch metric recorded: {metric_name}={value} {unit}")
    except (ClientError, BotoCoreError) as exc:
        logger.warning(f"Failed to record CloudWatch metric {metric_name}: {exc}")


@retry(
    retry=retry_if_exception_type(ClientError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    before_sleep=lambda retry_state: logger.warning(
        f"SNS publish retry {retry_state.attempt_number} after error: {retry_state.outcome.exception()}"
    ),
    reraise=True,
)
def _publish_to_sns_with_retry(topic_arn: str, subject: str, message: str) -> str:
    """Publish message to SNS with retry logic.

    Retries on transient errors (Throttling, ServiceUnavailable) with exponential backoff.
    Does NOT retry on permanent errors (AuthorizationError, InvalidParameter).

    Args:
        topic_arn: ARN of SNS topic.
        subject: Email subject.
        message: Email message body.

    Returns:
        MessageId from SNS publish response.

    Raises:
        ClientError: If permanent error or max retries exceeded.
        BotoCoreError: On other AWS SDK errors.
    """
    try:
        sns = boto3.client("sns", region_name=settings.AWS_REGION)
        response = sns.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message,
        )
        return response.get("MessageId", "")
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")

        # Don't retry permanent errors
        if _is_permanent_error(exc):
            logger.error(f"Permanent SNS error (code={error_code}): {exc.response.get('Error', {}).get('Message')}")
            raise

        # Retry transient errors
        if _is_transient_error(exc):
            logger.warning(f"Transient SNS error (code={error_code}), will retry: {exc}")
            raise

        # Other errors: log and raise
        logger.error(f"SNS error (code={error_code}): {exc}")
        raise


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
    """Publish storm alert to SNS topic with retry logic.

    Publishes a storm detection alert to the configured SNS topic.
    Retries automatically on transient errors with exponential backoff.
    Does NOT retry on configuration errors or authorization failures.

    Args:
        bucket: S3 bucket name containing the satellite image.
        key: S3 object key of the satellite image.
        detections: List of YOLO detections (dicts with 'class', 'confidence', etc.).

    Returns:
        MessageId on success, None when skipped or on unrecoverable failure.
    """
    if not detections:
        logger.debug(f"No detections for s3://{bucket}/{key} — skipping alert")
        return None

    if not sns_is_configured():
        logger.info("SNS not configured — skipping publish (set SNS_TOPIC_ARN on Lambda)")
        _put_cloudwatch_metric("AlertsSkipped")
        return None

    topic_arn = settings.SNS_TOPIC_ARN.strip()
    subject, message = _build_storm_message(bucket, key, detections)

    try:
        message_id = _publish_to_sns_with_retry(topic_arn, subject, message)
        _put_cloudwatch_metric("StormAlertsSent")
        logger.info("SNS alert published: MessageId=%s topic=%s s3://%s/%s", message_id, topic_arn, bucket, key)
        return message_id
    except (ClientError, BotoCoreError, RetryError) as exc:
        logger.error("SNS publish failed for s3://%s/%s after retries: %s", bucket, key, exc)
        _put_cloudwatch_metric("StormAlertsFailed")
        return None


def _normalize_email(email: str) -> str:
    """Valida e normaliza e-mail para inscrição SNS."""
    normalized = (email or "").strip().lower()
    if not normalized or not _EMAIL_RE.match(normalized):
        raise ValueError("E-mail inválido")
    return normalized


def subscribe_email(email: str) -> dict[str, Any]:
    """Subscribe email to SNS topic for storm alerts.

    Subscribes an email address to the configured SNS topic using the email protocol.
    AWS sends a confirmation link to the email address; alerts are only delivered
    after the user clicks the confirmation link.

    Args:
        email: Email address to subscribe.

    Returns:
        Dict with subscription result:
            - success: bool - Whether subscription was successful.
            - configured: bool - Whether SNS is configured.
            - error: str (optional) - Error message if subscription failed.
            - email: str (optional) - Normalized email address.
            - subscription_arn: str (optional) - ARN of subscription.
            - pending_confirmation: bool (optional) - Whether awaiting user confirmation.
            - message: str (optional) - User-friendly message.
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
    """Publish simulated alert from dashboard to SNS with retry logic.

    Args:
        lat: Latitude of simulated alert location.
        lon: Longitude of simulated alert location.
        confidence: Confidence score (0.0 to 1.0).

    Returns:
        MessageId on success, None when skipped or on unrecoverable failure.
    """
    if not sns_is_configured():
        logger.info("SNS not configured — skipping simulated publish")
        _put_cloudwatch_metric("AlertsSkipped")
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
        message_id = _publish_to_sns_with_retry(topic_arn, subject, message)
        _put_cloudwatch_metric("StormAlertsSent")
        logger.info("SNS simulated alert published: MessageId=%s lat=%.4f lon=%.4f", message_id, lat, lon)
        return message_id
    except (ClientError, BotoCoreError, RetryError) as exc:
        logger.error("SNS simulated publish failed after retries: %s", exc)
        _put_cloudwatch_metric("StormAlertsFailed")
        return None
