"""Publicação e inscrição de alertas de tempestade via Amazon SNS."""

from __future__ import annotations

import logging
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

# RFC-compliant email validation
try:
    from email_validator import validate_email, EmailNotValidError
    _EMAIL_VALIDATOR_AVAILABLE = True
except ImportError:
    _EMAIL_VALIDATOR_AVAILABLE = False
    EmailNotValidError = ValueError

from app.core.config import settings
from app.services.sns_geo import is_within_radius, storm_location_from_s3_key
from app.services.sns_rate_limit import can_send_alert, record_alert_sent
from app.services.sns_region_cooldown import (
    can_send_region_alert,
    extract_region_from_s3_key,
    record_region_alert,
)
from app.services.sns_subscriber_store import get_subscriber_location, save_subscriber_location

logger = logging.getLogger(__name__)


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
    status: dict[str, Any] = {
        "enabled": settings.SNS_ENABLED,
        "configured": sns_is_configured(),
        "topic_arn": topic or None,
        "region": settings.AWS_REGION,
        "max_subscribers": settings.SNS_MAX_SUBSCRIBERS,
        "max_alerts_per_email_day": settings.SNS_MAX_ALERTS_PER_EMAIL_DAY,
        "region_cooldown_minutes": settings.SNS_REGION_COOLDOWN_MINUTES,
        "alert_radius_km": settings.SNS_ALERT_RADIUS_KM,
        "geo_filtering_enabled": True,
    }
    if sns_is_configured():
        status["subscriber_count"] = _count_email_subscriptions(topic)
    return status


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


@retry(
    retry=retry_if_exception_type(ClientError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    before_sleep=lambda retry_state: logger.warning(
        f"SNS subscription publish retry {retry_state.attempt_number} after error: "
        f"{retry_state.outcome.exception()}"
    ),
    reraise=True,
)
def _publish_to_subscription_with_retry(
    subscription_arn: str,
    subject: str,
    message: str,
) -> str:
    """Publish message to a single SNS email subscription with retry logic."""
    try:
        sns = boto3.client("sns", region_name=settings.AWS_REGION)
        response = sns.publish(
            TargetArn=subscription_arn,
            Subject=subject,
            Message=message,
        )
        return response.get("MessageId", "")
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        if _is_permanent_error(exc):
            logger.error(
                "Permanent SNS subscription error (code=%s): %s",
                error_code,
                exc.response.get("Error", {}).get("Message"),
            )
            raise
        if _is_transient_error(exc):
            logger.warning(f"Transient SNS subscription error (code={error_code}), will retry: {exc}")
            raise
        logger.error(f"SNS subscription error (code={error_code}): {exc}")
        raise


def _list_email_subscriptions(topic_arn: str) -> list[dict[str, Any]]:
    """Lista inscrições de e-mail no tópico SNS (confirmadas e pendentes)."""
    subscriptions: list[dict[str, Any]] = []
    try:
        sns = boto3.client("sns", region_name=settings.AWS_REGION)
        paginator = sns.get_paginator("list_subscriptions_by_topic")
        for page in paginator.paginate(TopicArn=topic_arn):
            for sub in page.get("Subscriptions", []):
                if sub.get("Protocol") != "email":
                    continue
                endpoint = (sub.get("Endpoint") or "").strip().lower()
                if not endpoint:
                    continue
                subscription_arn = sub.get("SubscriptionArn", "")
                confirmed = bool(subscription_arn and subscription_arn != "pending confirmation")
                subscriptions.append(
                    {
                        "email": endpoint,
                        "subscription_arn": subscription_arn if confirmed else None,
                        "confirmed": confirmed,
                        "pending_confirmation": subscription_arn == "pending confirmation",
                    }
                )
    except (ClientError, BotoCoreError, AttributeError) as exc:
        logger.warning("Failed to list SNS email subscriptions: %s", exc)
    return subscriptions


def _count_email_subscriptions(topic_arn: str) -> int:
    """Conta inscrições de e-mail ativas (pendentes + confirmadas)."""
    return len(_list_email_subscriptions(topic_arn))


def _email_is_subscribed(topic_arn: str, email: str) -> bool:
    endpoint = email.strip().lower()
    return any(sub["email"] == endpoint for sub in _list_email_subscriptions(topic_arn))


def _subscriber_eligible_for_geo_alert(
    email: str,
    storm_lat: float | None,
    storm_lon: float | None,
) -> bool:
    """True se o inscrito deve receber alerta (geo + coords salvas)."""
    if storm_lat is None or storm_lon is None:
        return True

    location = get_subscriber_location(email)
    if not location:
        logger.info(
            "SNS alert skipped for %s — sem localização salva; reinscreva com o mapa do dashboard",
            email,
        )
        return False

    sub_lat = float(location["lat"])
    sub_lon = float(location["lon"])
    if not is_within_radius(sub_lat, sub_lon, storm_lat, storm_lon):
        logger.info(
            "SNS alert skipped for %s — fora do raio de %.0f km (sub %.4f,%.4f storm %.4f,%.4f)",
            email,
            settings.SNS_ALERT_RADIUS_KM,
            sub_lat,
            sub_lon,
            storm_lat,
            storm_lon,
        )
        return False
    return True


def _publish_alert_message(
    subject: str,
    message: str,
    storm_lat: float | None = None,
    storm_lon: float | None = None,
) -> str | None:
    """Publica alerta respeitando limite diário por e-mail e filtro geográfico.

    Com inscritos confirmados, envia individualmente por subscription ARN.
    Sem inscritos confirmados, publica no tópico (compatível com testes e tópico vazio).
    """
    topic_arn = settings.SNS_TOPIC_ARN.strip()
    confirmed = [
        sub for sub in _list_email_subscriptions(topic_arn) if sub.get("confirmed")
    ]

    if not confirmed:
        logger.warning(
            "SNS topic publish without confirmed subscribers — per-email rate limit not enforced"
        )
        message_id = _publish_to_sns_with_retry(topic_arn, subject, message)
        if message_id:
            _put_cloudwatch_metric("StormAlertsSent")
        return message_id or None

    sent_ids: list[str] = []
    skipped = 0
    for sub in confirmed:
        email = sub["email"]
        subscription_arn = sub.get("subscription_arn")
        if not subscription_arn:
            continue
        if not _subscriber_eligible_for_geo_alert(email, storm_lat, storm_lon):
            skipped += 1
            continue
        if not can_send_alert(email):
            skipped += 1
            logger.info(
                "SNS alert skipped for %s — daily limit of %d reached",
                email,
                settings.SNS_MAX_ALERTS_PER_EMAIL_DAY,
            )
            continue
        try:
            message_id = _publish_to_subscription_with_retry(
                subscription_arn,
                subject,
                message,
            )
        except (ClientError, BotoCoreError, RetryError) as exc:
            logger.error("SNS publish failed for %s: %s", email, exc)
            continue
        if message_id:
            record_alert_sent(email)
            sent_ids.append(message_id)

    if not sent_ids:
        if skipped:
            _put_cloudwatch_metric("AlertsSkipped")
        return None

    _put_cloudwatch_metric("StormAlertsSent", value=float(len(sent_ids)))
    return sent_ids[0]


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

    region = extract_region_from_s3_key(key)
    if region and not can_send_region_alert(region):
        logger.info(
            "SNS alert skipped for region %s — cooldown of %d minutes active",
            region,
            settings.SNS_REGION_COOLDOWN_MINUTES,
        )
        _put_cloudwatch_metric("AlertsSkipped")
        return None

    subject, message = _build_storm_message(bucket, key, detections)
    storm_coords = storm_location_from_s3_key(key)
    storm_lat, storm_lon = storm_coords if storm_coords else (None, None)

    try:
        message_id = _publish_alert_message(
            subject,
            message,
            storm_lat=storm_lat,
            storm_lon=storm_lon,
        )
        if message_id:
            if region:
                record_region_alert(region)
            logger.info(
                "SNS alert published: MessageId=%s s3://%s/%s",
                message_id,
                bucket,
                key,
            )
            return message_id
        logger.info("SNS alert not sent for s3://%s/%s (no eligible subscribers)", bucket, key)
        return None
    except (ClientError, BotoCoreError, RetryError) as exc:
        logger.error("SNS publish failed for s3://%s/%s after retries: %s", bucket, key, exc)
        _put_cloudwatch_metric("StormAlertsFailed")
        return None


def _normalize_email(email: str) -> str:
    """Valida e normaliza e-mail para inscrição SNS.

    Uses RFC-compliant email validation via email_validator library.
    Accepts valid formats including subaddressing (user+tag@example.com).

    Args:
        email: Email address to validate and normalize.

    Returns:
        Normalized email address (lowercase).

    Raises:
        ValueError: If email is invalid.
    """
    if not email or not isinstance(email, str):
        raise ValueError("E-mail inválido: email deve ser uma string não-vazia")

    email_clean = email.strip()

    if not email_clean:
        raise ValueError("E-mail inválido: email não pode estar vazio")

    if not _EMAIL_VALIDATOR_AVAILABLE:
        logger.warning("email_validator not installed, falling back to basic validation")
        # Fallback: basic validation
        if "@" not in email_clean or "." not in email_clean.split("@")[-1]:
            raise ValueError("E-mail inválido: formato não reconhecido")
        return email_clean.lower()

    try:
        # Validate and normalize using email_validator
        # check_deliverability=False to avoid DNS lookups in tests
        email_obj = validate_email(email_clean, check_deliverability=False)
        return email_obj.normalized.lower()
    except EmailNotValidError as exc:
        raise ValueError(f"E-mail inválido: {str(exc)}")


def _validate_subscriber_coords(lat: float | None, lon: float | None) -> tuple[float, float] | None:
    if lat is None and lon is None:
        return None
    if lat is None or lon is None:
        raise ValueError("Informe latitude e longitude juntas para alertas por região")
    if not (-35.0 <= lat <= 5.0):
        raise ValueError("Latitude inválida para o Brasil (use entre -35 e 5)")
    if not (-75.0 <= lon <= -30.0):
        raise ValueError("Longitude inválida para o Brasil (use entre -75 e -30)")
    return float(lat), float(lon)


def subscribe_email(
    email: str,
    lat: float | None = None,
    lon: float | None = None,
) -> dict[str, Any]:
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
        coords = _validate_subscriber_coords(lat, lon)
    except ValueError as exc:
        return {"success": False, "configured": True, "error": str(exc)}

    topic_arn = settings.SNS_TOPIC_ARN.strip()
    max_subscribers = max(1, int(settings.SNS_MAX_SUBSCRIBERS))

    if _email_is_subscribed(topic_arn, endpoint):
        if coords:
            save_subscriber_location(endpoint, coords[0], coords[1])
        return {
            "success": True,
            "configured": True,
            "email": endpoint,
            "already_subscribed": True,
            "location_saved": coords is not None,
            "message": "Este e-mail já está inscrito (ou aguardando confirmação da AWS).",
        }

    if _count_email_subscriptions(topic_arn) >= max_subscribers:
        return {
            "success": False,
            "configured": True,
            "error": (
                f"Limite de {max_subscribers} e-mails atingido. "
                "Não é possível cadastrar novos inscritos neste ambiente."
            ),
            "subscriber_limit_reached": True,
        }

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
    if coords:
        save_subscriber_location(endpoint, coords[0], coords[1])
    return {
        "success": True,
        "configured": True,
        "email": endpoint,
        "subscription_arn": subscription_arn or None,
        "pending_confirmation": pending,
        "location_saved": coords is not None,
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
    try:
        message_id = _publish_alert_message(
            subject,
            message,
            storm_lat=lat,
            storm_lon=lon,
        )
        if message_id:
            logger.info(
                "SNS simulated alert published: MessageId=%s lat=%.4f lon=%.4f",
                message_id,
                lat,
                lon,
            )
            return message_id
        logger.info("SNS simulated alert not sent lat=%.4f lon=%.4f (no eligible subscribers)", lat, lon)
        return None
    except (ClientError, BotoCoreError, RetryError) as exc:
        logger.error("SNS simulated publish failed after retries: %s", exc)
        _put_cloudwatch_metric("StormAlertsFailed")
        return None
