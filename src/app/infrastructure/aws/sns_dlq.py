"""SNS Dead Letter Queue (DLQ) management and message recovery."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


class SNSDLQManager:
    """Manage SNS Dead Letter Queue (DLQ) for failed alert messages.

    Handles reading, processing, and recovering messages from SQS DLQ
    connected to SNS topic. Includes X-Ray tracing integration.
    """

    def __init__(self, region: str | None = None):
        """Initialize DLQ manager.

        Args:
            region: AWS region. Defaults to settings.AWS_REGION.
        """
        self.region = region or settings.AWS_REGION
        self.sqs_client = boto3.client("sqs", region_name=self.region)
        self.sns_client = boto3.client("sns", region_name=self.region)
        self.cloudwatch_client = boto3.client("cloudwatch", region_name=self.region)
        self.dlq_url: str | None = None

    def set_dlq_url(self, dlq_url: str) -> None:
        """Set the DLQ URL (SQS queue).

        Args:
            dlq_url: Full SQS queue URL for the DLQ.
        """
        self.dlq_url = dlq_url
        logger.info(f"DLQ URL set to: {dlq_url}")

    def get_dlq_url_from_topic(self, topic_arn: str) -> str | None:
        """Get DLQ URL by looking up topic attributes.

        Queries SNS topic attributes to find the RedrivePolicy
        which contains the DLQ URL.

        Args:
            topic_arn: ARN of the SNS topic.

        Returns:
            DLQ URL if found, None otherwise.
        """
        try:
            attrs = self.sns_client.get_topic_attributes(TopicArn=topic_arn)
            redrive_policy_str = attrs.get("Attributes", {}).get("RedrivePolicy", "")

            if not redrive_policy_str:
                logger.warning(f"No RedrivePolicy found on topic {topic_arn}")
                return None

            redrive_policy = json.loads(redrive_policy_str)
            dlq_arn = redrive_policy.get("deadLetterTargetArn")

            if not dlq_arn:
                logger.warning(f"No deadLetterTargetArn in RedrivePolicy for {topic_arn}")
                return None

            # Convert DLQ ARN to URL
            dlq_url = self._arn_to_sqs_url(dlq_arn)
            self.set_dlq_url(dlq_url)
            return dlq_url

        except (ClientError, BotoCoreError, json.JSONDecodeError) as exc:
            logger.error(f"Failed to get DLQ URL from topic {topic_arn}: {exc}")
            return None

    def _arn_to_sqs_url(self, queue_arn: str) -> str:
        """Convert SQS queue ARN to URL.

        Args:
            queue_arn: SQS queue ARN (arn:aws:sqs:region:account:queue-name).

        Returns:
            SQS queue URL (https://queue.amazonaws.com/account/queue-name).

        Raises:
            ValueError: If ARN format is invalid.
        """
        parts = queue_arn.split(":")
        if len(parts) < 6 or parts[2] != "sqs":
            raise ValueError(f"Invalid SQS ARN format: {queue_arn}")

        region = parts[3]
        account = parts[4]
        queue_name = parts[5]

        return f"https://queue.amazonaws.com/{account}/{queue_name}"

    def read_messages(self, max_messages: int = 10, wait_time: int = 0) -> list[dict[str, Any]]:
        """Read messages from DLQ.

        Args:
            max_messages: Maximum number of messages to read (1-10). Defaults to 10.
            wait_time: Long polling wait time in seconds (0-20). Defaults to 0.

        Returns:
            List of message dicts with format:
            {
                "MessageId": str,
                "Body": str (JSON),
                "ReceiptHandle": str,
                "Attributes": dict,
                "Timestamp": datetime,
                "ApproximateAge": int (seconds),
            }
        """
        if not self.dlq_url:
            logger.error("DLQ URL not set. Call set_dlq_url() or get_dlq_url_from_topic() first.")
            return []

        max_messages = min(max(1, max_messages), 10)

        try:
            response = self.sqs_client.receive_message(
                QueueUrl=self.dlq_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time,
                AttributeNames=["All"],
                MessageAttributeNames=["All"],
            )

            messages = response.get("Messages", [])
            formatted_messages = []

            for msg in messages:
                try:
                    body = json.loads(msg.get("Body", "{}"))
                except json.JSONDecodeError:
                    body = {"raw": msg.get("Body")}

                sent_timestamp = int(msg.get("Attributes", {}).get("SentTimestamp", 0))
                timestamp = datetime.fromtimestamp(sent_timestamp / 1000.0) if sent_timestamp else None
                approximate_age = int(msg.get("Attributes", {}).get("ApproximateReceiveCount", 0))

                formatted_messages.append({
                    "MessageId": msg.get("MessageId"),
                    "Body": body,
                    "ReceiptHandle": msg.get("ReceiptHandle"),
                    "Attributes": msg.get("Attributes", {}),
                    "Timestamp": timestamp,
                    "ApproximateAge": approximate_age,
                })

            logger.info(f"Read {len(formatted_messages)} messages from DLQ")
            return formatted_messages

        except (ClientError, BotoCoreError) as exc:
            logger.error(f"Failed to read DLQ messages: {exc}")
            return []

    def get_dlq_stats(self) -> dict[str, Any]:
        """Get DLQ statistics.

        Returns:
            Dict with DLQ statistics:
            {
                "MessageCount": int,
                "ApproximateNumberOfMessages": int,
                "ApproximateNumberOfMessagesNotVisible": int,
                "VisibilityTimeout": int,
                "LastModifiedTimestamp": datetime,
            }
        """
        if not self.dlq_url:
            logger.error("DLQ URL not set")
            return {}

        try:
            response = self.sqs_client.get_queue_attributes(
                QueueUrl=self.dlq_url,
                AttributeNames=["All"],
            )

            attrs = response.get("Attributes", {})
            last_modified = int(attrs.get("LastModifiedTimestamp", 0))

            return {
                "MessageCount": int(attrs.get("ApproximateNumberOfMessages", 0)),
                "ApproximateNumberOfMessagesNotVisible": int(attrs.get("ApproximateNumberOfMessagesNotVisible", 0)),
                "VisibilityTimeout": int(attrs.get("VisibilityTimeout", 0)),
                "CreatedTimestamp": datetime.fromtimestamp(int(attrs.get("CreatedTimestamp", 0))),
                "LastModifiedTimestamp": datetime.fromtimestamp(last_modified),
                "ApproximateNumberOfMessagesDelayed": int(attrs.get("ApproximateNumberOfMessagesDelayed", 0)),
            }

        except (ClientError, BotoCoreError) as exc:
            logger.error(f"Failed to get DLQ stats: {exc}")
            return {}

    def delete_message(self, receipt_handle: str) -> bool:
        """Delete a message from DLQ (after successful reprocessing).

        Args:
            receipt_handle: Receipt handle of the message to delete.

        Returns:
            True if deleted successfully, False otherwise.
        """
        if not self.dlq_url:
            logger.error("DLQ URL not set")
            return False

        try:
            self.sqs_client.delete_message(
                QueueUrl=self.dlq_url,
                ReceiptHandle=receipt_handle,
            )
            logger.info(f"Deleted message from DLQ: {receipt_handle[:20]}...")
            return True

        except (ClientError, BotoCoreError) as exc:
            logger.error(f"Failed to delete message from DLQ: {exc}")
            return False

    def reprocess_message(self, message: dict[str, Any]) -> tuple[bool, str | None]:
        """Reprocess a failed message from DLQ.

        Attempts to republish the message to SNS topic. If successful,
        deletes the message from DLQ. If it fails again, the message
        stays in DLQ for manual investigation.

        Args:
            message: Message dict from read_messages().

        Returns:
            Tuple of (success: bool, message_id: str | None).
        """
        if not isinstance(message.get("Body"), dict):
            logger.error(f"Invalid message body format: {message.get('Body')}")
            return False, None

        body = message["Body"]
        topic_arn = settings.SNS_TOPIC_ARN

        if not topic_arn:
            logger.error("SNS_TOPIC_ARN not configured")
            return False, None

        try:
            subject = body.get("Subject", "Reprocessed Storm Alert")
            message_text = body.get("Message", "")

            response = self.sns_client.publish(
                TopicArn=topic_arn,
                Subject=subject,
                Message=message_text,
            )

            message_id = response.get("MessageId")
            logger.info(f"Reprocessed message to SNS: {message_id}")

            # Delete from DLQ only after successful reprocessing
            receipt_handle = message.get("ReceiptHandle")
            if receipt_handle:
                self.delete_message(receipt_handle)

            self._put_cloudwatch_metric("DLQMessagesReprocessed")
            return True, message_id

        except (ClientError, BotoCoreError) as exc:
            logger.error(f"Failed to reprocess message from DLQ: {exc}")
            self._put_cloudwatch_metric("DLQReprocessingFailed")
            return False, None

    def reprocess_all(self, max_attempts: int = 10) -> dict[str, Any]:
        """Reprocess all messages in DLQ.

        Args:
            max_attempts: Maximum messages to reprocess in this call. Defaults to 10.

        Returns:
            Dict with results:
            {
                "Total": int,
                "Succeeded": int,
                "Failed": int,
                "Details": list[dict],
            }
        """
        messages = self.read_messages(max_messages=max_attempts)
        results = {
            "Total": len(messages),
            "Succeeded": 0,
            "Failed": 0,
            "Details": [],
        }

        for msg in messages:
            success, message_id = self.reprocess_message(msg)
            if success:
                results["Succeeded"] += 1
                results["Details"].append({
                    "MessageId": msg.get("MessageId"),
                    "Reprocessed": True,
                    "NewMessageId": message_id,
                })
            else:
                results["Failed"] += 1
                results["Details"].append({
                    "MessageId": msg.get("MessageId"),
                    "Reprocessed": False,
                    "Error": "Reprocessing failed",
                })

        logger.info(f"Reprocess batch completed: {results['Succeeded']} succeeded, {results['Failed']} failed")
        return results

    def purge_dlq(self) -> bool:
        """Purge all messages from DLQ (destructive operation).

        WARNING: This deletes all messages in the DLQ without recovery!
        Use with caution.

        Returns:
            True if purged successfully, False otherwise.
        """
        if not self.dlq_url:
            logger.error("DLQ URL not set")
            return False

        try:
            self.sqs_client.purge_queue(QueueUrl=self.dlq_url)
            logger.warning("DLQ purged - all messages deleted")
            self._put_cloudwatch_metric("DLQPurged")
            return True

        except (ClientError, BotoCoreError) as exc:
            logger.error(f"Failed to purge DLQ: {exc}")
            return False

    def _put_cloudwatch_metric(self, metric_name: str, value: float = 1.0) -> None:
        """Put a metric to CloudWatch.

        Args:
            metric_name: Name of the metric.
            value: Metric value. Defaults to 1.
        """
        try:
            self.cloudwatch_client.put_metric_data(
                Namespace="GlobalSolutions",
                MetricData=[
                    {
                        "MetricName": metric_name,
                        "Value": value,
                        "Unit": "Count",
                    },
                ],
            )
        except (ClientError, BotoCoreError) as exc:
            logger.warning(f"Failed to record CloudWatch metric {metric_name}: {exc}")
