"""SNS setup and configuration helpers."""

from __future__ import annotations

import json
import logging
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


def validate_sns_setup() -> tuple[bool, list[str]]:
    """Validate SNS setup.

    Checks:
    - SNS is enabled
    - Topic ARN is configured
    - Topic exists and is accessible
    - DLQ is configured (if applicable)

    Returns:
        Tuple of (is_valid: bool, issues: list[str]).
        If is_valid is True, issues list will be empty or contain warnings.
    """
    issues = []

    if not settings.SNS_ENABLED:
        return False, ["SNS is disabled in configuration"]

    if not settings.SNS_TOPIC_ARN:
        return False, ["SNS_TOPIC_ARN is not configured"]

    topic_arn = settings.SNS_TOPIC_ARN.strip()

    try:
        sns = boto3.client("sns", region_name=settings.AWS_REGION)
        attrs = sns.get_topic_attributes(TopicArn=topic_arn)

        # Topic exists and is accessible
        logger.info(f"SNS topic {topic_arn} is accessible")

        # Check for RedrivePolicy (DLQ)
        redrive_policy = attrs.get("Attributes", {}).get("RedrivePolicy")
        if not redrive_policy:
            issues.append(f"No RedrivePolicy (DLQ) configured on topic {topic_arn}")
        else:
            try:
                policy_obj = json.loads(redrive_policy)
                dlq_arn = policy_obj.get("deadLetterTargetArn")
                if dlq_arn:
                    logger.info(f"DLQ configured: {dlq_arn}")
                else:
                    issues.append("RedrivePolicy exists but has no deadLetterTargetArn")
            except json.JSONDecodeError:
                issues.append("RedrivePolicy is not valid JSON")

        return len(issues) == 0, issues

    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code == "NotFound":
            return False, [f"SNS topic not found: {topic_arn}"]
        return False, [f"SNS topic access error: {exc}"]

    except BotoCoreError as exc:
        return False, [f"AWS SDK error: {exc}"]


def create_sns_topic(topic_name: str) -> str | None:
    """Create SNS topic if it doesn't exist.

    Args:
        topic_name: Name of the topic (without ARN prefix).

    Returns:
        Topic ARN on success, None on failure.

    Example:
        >>> create_sns_topic("storm-alerts")
        'arn:aws:sns:us-east-1:123456789012:storm-alerts'
    """
    try:
        sns = boto3.client("sns", region_name=settings.AWS_REGION)
        response = sns.create_topic(Name=topic_name)
        topic_arn = response.get("TopicArn")

        logger.info(f"SNS topic created: {topic_arn}")
        return topic_arn

    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code == "TopicLimitExceeded":
            logger.warning(f"Topic creation failed: limit exceeded")
            return None
        logger.error(f"Failed to create SNS topic {topic_name}: {exc}")
        return None

    except BotoCoreError as exc:
        logger.error(f"AWS SDK error creating topic {topic_name}: {exc}")
        return None


def create_sqs_dlq(queue_name: str, attributes: dict[str, str] | None = None) -> str | None:
    """Create SQS DLQ (Dead Letter Queue) if it doesn't exist.

    Args:
        queue_name: Name of the SQS queue.
        attributes: Optional queue attributes (e.g., VisibilityTimeout, MessageRetentionPeriod).

    Returns:
        Queue URL on success, None on failure.

    Example:
        >>> create_sqs_dlq("storm-alerts-dlq")
        'https://queue.amazonaws.com/123456789012/storm-alerts-dlq'
    """
    attrs = attributes or {}

    # Set sensible defaults for DLQ
    if "MessageRetentionPeriod" not in attrs:
        attrs["MessageRetentionPeriod"] = "1209600"  # 14 days

    if "VisibilityTimeout" not in attrs:
        attrs["VisibilityTimeout"] = "300"  # 5 minutes

    try:
        sqs = boto3.client("sqs", region_name=settings.AWS_REGION)
        response = sqs.create_queue(QueueName=queue_name, Attributes=attrs)
        queue_url = response.get("QueueUrl")

        logger.info(f"SQS DLQ created: {queue_url}")
        return queue_url

    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code == "QueueNameExists":
            # Queue already exists, get its URL
            try:
                response = sqs.get_queue_url(QueueName=queue_name)
                queue_url = response.get("QueueUrl")
                logger.info(f"SQS DLQ already exists: {queue_url}")
                return queue_url
            except ClientError:
                pass

        logger.error(f"Failed to create SQS DLQ {queue_name}: {exc}")
        return None

    except BotoCoreError as exc:
        logger.error(f"AWS SDK error creating DLQ {queue_name}: {exc}")
        return None


def bind_dlq_to_topic(topic_arn: str, dlq_arn: str) -> bool:
    """Bind SQS DLQ to SNS topic using RedrivePolicy.

    This allows SNS to send failed messages to the DLQ for later recovery.

    Args:
        topic_arn: ARN of the SNS topic.
        dlq_arn: ARN of the SQS DLQ queue.

    Returns:
        True on success, False on failure.

    Example:
        >>> bind_dlq_to_topic(
        ...     "arn:aws:sns:us-east-1:123456789012:storm-alerts",
        ...     "arn:aws:sqs:us-east-1:123456789012:storm-alerts-dlq"
        ... )
        True
    """
    redrive_policy = {
        "deadLetterTargetArn": dlq_arn,
    }

    try:
        sns = boto3.client("sns", region_name=settings.AWS_REGION)
        sns.set_topic_attributes(
            TopicArn=topic_arn,
            AttributeName="RedrivePolicy",
            AttributeValue=json.dumps(redrive_policy),
        )

        logger.info(f"DLQ {dlq_arn} bound to topic {topic_arn}")
        return True

    except ClientError as exc:
        logger.error(f"Failed to bind DLQ to topic: {exc}")
        return False

    except BotoCoreError as exc:
        logger.error(f"AWS SDK error binding DLQ: {exc}")
        return False


def setup_sns_dlq(topic_name: str = "storm-alerts", dlq_name: str = "storm-alerts-dlq") -> tuple[str | None, str | None]:
    """Complete SNS + DLQ setup in one call.

    Creates SNS topic and SQS DLQ, then binds them together.

    Args:
        topic_name: Name of the SNS topic.
        dlq_name: Name of the SQS DLQ queue.

    Returns:
        Tuple of (topic_arn: str | None, dlq_url: str | None).

    Example:
        >>> topic_arn, dlq_url = setup_sns_dlq()
        >>> print(topic_arn)
        'arn:aws:sns:us-east-1:123456789012:storm-alerts'
    """
    # Create SNS topic
    topic_arn = create_sns_topic(topic_name)
    if not topic_arn:
        logger.error("Failed to create SNS topic")
        return None, None

    # Create SQS DLQ
    dlq_url = create_sqs_dlq(dlq_name)
    if not dlq_url:
        logger.error("Failed to create SQS DLQ")
        return topic_arn, None

    # Get DLQ ARN from URL
    # Parse URL to get queue name and account
    dlq_arn = _queue_url_to_arn(dlq_url)
    if not dlq_arn:
        logger.error("Failed to convert DLQ URL to ARN")
        return topic_arn, dlq_url

    # Bind DLQ to topic
    if not bind_dlq_to_topic(topic_arn, dlq_arn):
        logger.error("Failed to bind DLQ to topic")
        return topic_arn, dlq_url

    logger.info(f"SNS + DLQ setup completed: topic={topic_arn}, dlq={dlq_url}")
    return topic_arn, dlq_url


def _queue_url_to_arn(queue_url: str) -> str | None:
    """Convert SQS queue URL to ARN.

    Args:
        queue_url: SQS queue URL (https://queue.amazonaws.com/account/queue-name).

    Returns:
        Queue ARN, or None if conversion fails.
    """
    try:
        # URL format: https://queue.amazonaws.com/123456789012/queue-name
        parts = queue_url.rstrip("/").split("/")
        if len(parts) < 4:
            return None

        queue_name = parts[-1]
        account = parts[-2]

        # ARN format: arn:aws:sqs:region:account:queue-name
        arn = f"arn:aws:sqs:{settings.AWS_REGION}:{account}:{queue_name}"
        return arn

    except (ValueError, IndexError) as exc:
        logger.error(f"Failed to convert queue URL to ARN: {exc}")
        return None


def get_topic_arn_from_env() -> str | None:
    """Get topic ARN from environment configuration.

    Returns:
        Topic ARN from SNS_TOPIC_ARN setting, or None if not configured.
    """
    return (settings.SNS_TOPIC_ARN or "").strip() or None


def validate_topic_arn(topic_arn: str) -> bool:
    """Validate that a topic ARN is accessible.

    Args:
        topic_arn: ARN to validate.

    Returns:
        True if topic is accessible, False otherwise.
    """
    try:
        sns = boto3.client("sns", region_name=settings.AWS_REGION)
        sns.get_topic_attributes(TopicArn=topic_arn)
        return True

    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code == "NotFound":
            logger.warning(f"SNS topic not found: {topic_arn}")
        else:
            logger.warning(f"Failed to validate topic {topic_arn}: {exc}")
        return False

    except BotoCoreError as exc:
        logger.warning(f"AWS SDK error validating topic: {exc}")
        return False
