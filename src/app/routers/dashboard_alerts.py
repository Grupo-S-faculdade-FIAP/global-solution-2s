"""Dashboard API endpoints for SNS alerts monitoring and management."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.core.sns_config import validate_sns_setup, get_topic_arn_from_env
from app.infrastructure.aws.sns_dlq import SNSDLQManager
from app.services import sns_alerts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/status")
async def get_alerts_status() -> dict[str, Any]:
    """Get SNS alerts system status.

    Returns:
        {
            "enabled": bool - SNS is enabled,
            "configured": bool - Topic is configured,
            "topic_arn": str | None - Topic ARN,
            "region": str - AWS region,
            "valid": bool - SNS setup is valid,
            "issues": list[str] - Configuration issues (if any),
            "dlq_available": bool - DLQ is configured,
        }
    """
    status = sns_alerts.sns_status()
    is_valid, issues = validate_sns_setup()

    topic_arn = get_topic_arn_from_env()
    dlq_available = False

    if topic_arn:
        try:
            dlq_manager = SNSDLQManager()
            dlq_url = dlq_manager.get_dlq_url_from_topic(topic_arn)
            dlq_available = dlq_url is not None
        except Exception as exc:
            logger.warning(f"Failed to check DLQ availability: {exc}")

    return {
        **status,
        "valid": is_valid,
        "issues": issues,
        "dlq_available": dlq_available,
    }


@router.get("/metrics")
async def get_alerts_metrics() -> dict[str, Any]:
    """Get CloudWatch metrics for alerts.

    Returns recent metrics:
    - StormAlertsSent
    - StormAlertsFailed
    - AlertsSkipped
    - DLQMessagesReprocessed
    """
    try:
        cloudwatch = __import__("boto3").client("cloudwatch", region_name=settings.AWS_REGION)

        metrics_response = cloudwatch.list_metrics(Namespace="GlobalSolutions")
        metrics = []

        metric_names = [
            "StormAlertsSent",
            "StormAlertsFailed",
            "AlertsSkipped",
            "DLQMessagesReprocessed",
            "DLQReprocessingFailed",
            "DLQPurged",
        ]

        for metric_name in metric_names:
            try:
                stats = cloudwatch.get_metric_statistics(
                    Namespace="GlobalSolutions",
                    MetricName=metric_name,
                    StartTime=__import__("datetime").datetime.utcnow() - __import__("datetime").timedelta(hours=24),
                    EndTime=__import__("datetime").datetime.utcnow(),
                    Period=3600,  # 1 hour
                    Statistics=["Sum", "Average"],
                )

                metric_data = {
                    "name": metric_name,
                    "datapoints": stats.get("Datapoints", []),
                    "unit": "Count",
                }
                metrics.append(metric_data)

            except Exception as exc:
                logger.warning(f"Failed to get metric {metric_name}: {exc}")

        return {
            "namespace": "GlobalSolutions",
            "metrics": metrics,
            "time_range_hours": 24,
        }

    except Exception as exc:
        logger.error(f"Failed to get metrics: {exc}")
        raise HTTPException(status_code=500, detail="Failed to retrieve CloudWatch metrics")


@router.get("/dlq")
async def get_dlq_messages(max_messages: int = Query(10, ge=1, le=10)) -> dict[str, Any]:
    """Get messages from DLQ.

    Query Parameters:
    - max_messages: Maximum messages to retrieve (1-10, default 10)

    Returns:
        {
            "queue_url": str | None,
            "stats": dict - DLQ statistics,
            "messages": list[dict] - DLQ messages,
            "count": int - Number of messages returned,
        }
    """
    topic_arn = get_topic_arn_from_env()
    if not topic_arn:
        raise HTTPException(status_code=400, detail="SNS topic not configured")

    try:
        dlq_manager = SNSDLQManager()
        dlq_url = dlq_manager.get_dlq_url_from_topic(topic_arn)

        if not dlq_url:
            raise HTTPException(status_code=404, detail="DLQ not found for topic")

        stats = dlq_manager.get_dlq_stats()
        messages = dlq_manager.read_messages(max_messages=max_messages)

        # Convert datetime to ISO string for JSON serialization
        for msg in messages:
            if msg.get("Timestamp"):
                msg["Timestamp"] = msg["Timestamp"].isoformat()

        return {
            "queue_url": dlq_url,
            "stats": stats,
            "messages": messages,
            "count": len(messages),
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to get DLQ messages: {exc}")
        raise HTTPException(status_code=500, detail="Failed to retrieve DLQ messages")


@router.post("/retry-dlq")
async def retry_dlq_messages(max_attempts: int = Query(10, ge=1, le=100)) -> dict[str, Any]:
    """Reprocess all messages from DLQ.

    Attempts to republish each failed message. If successful, the message
    is deleted from DLQ. If reprocessing fails, the message remains in DLQ
    for manual investigation.

    Query Parameters:
    - max_attempts: Maximum messages to reprocess (1-100, default 10)

    Returns:
        {
            "total": int - Total messages processed,
            "succeeded": int - Successfully reprocessed,
            "failed": int - Failed reprocessing,
            "details": list[dict] - Per-message results,
        }
    """
    topic_arn = get_topic_arn_from_env()
    if not topic_arn:
        raise HTTPException(status_code=400, detail="SNS topic not configured")

    try:
        dlq_manager = SNSDLQManager()
        dlq_url = dlq_manager.get_dlq_url_from_topic(topic_arn)

        if not dlq_url:
            raise HTTPException(status_code=404, detail="DLQ not found for topic")

        results = dlq_manager.reprocess_all(max_attempts=max_attempts)

        return {
            "total": results["Total"],
            "succeeded": results["Succeeded"],
            "failed": results["Failed"],
            "details": results["Details"],
            "message": f"Reprocessing complete: {results['Succeeded']} succeeded, {results['Failed']} failed",
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to reprocess DLQ messages: {exc}")
        raise HTTPException(status_code=500, detail="Failed to reprocess DLQ messages")


@router.get("/history")
async def get_alerts_history(limit: int = Query(100, ge=1, le=1000)) -> dict[str, Any]:
    """Get recent alert history from CloudWatch Logs.

    Note: This endpoint requires CloudWatch Logs integration.
    Currently returns placeholder data. For production, integrate with
    CloudWatch Logs Insights or DynamoDB alert table.

    Query Parameters:
    - limit: Maximum alerts to return (1-1000, default 100)

    Returns:
        {
            "alerts": list[dict] - Recent alerts,
            "count": int - Number of alerts returned,
            "message": str - Status message,
        }
    """
    # TODO: Implement CloudWatch Logs Insights query or DynamoDB table scan
    # For now, return placeholder

    return {
        "alerts": [],
        "count": 0,
        "message": "Alert history integration pending. Use CloudWatch Logs or DynamoDB integration.",
        "next_steps": [
            "Enable CloudWatch Logs for SNS",
            "Query logs using CloudWatch Logs Insights",
            "Or integrate with DynamoDB alerts table for persistent storage",
        ],
    }


@router.get("/test")
async def test_alert_send(lat: float = Query(-23.5505), lon: float = Query(-46.6333), confidence: float = Query(0.85)) -> dict[str, Any]:
    """Send a test simulated alert to SNS.

    This endpoint allows testing the alert system without manual image upload.

    Query Parameters:
    - lat: Latitude (default: São Paulo)
    - lon: Longitude (default: São Paulo)
    - confidence: Confidence score 0.0-1.0 (default: 0.85)

    Returns:
        {
            "success": bool - Publish succeeded,
            "message_id": str | None - SNS MessageId if successful,
            "message": str - Status message,
        }
    """
    if not sns_alerts.sns_is_configured():
        raise HTTPException(
            status_code=400,
            detail="SNS not configured. Set SNS_TOPIC_ARN environment variable.",
        )

    if not 0.0 <= confidence <= 1.0:
        raise HTTPException(status_code=400, detail="Confidence must be between 0.0 and 1.0")

    try:
        message_id = sns_alerts.publish_simulated_alert(lat, lon, confidence)

        if message_id:
            return {
                "success": True,
                "message_id": message_id,
                "message": f"Test alert sent successfully to SNS topic",
            }
        else:
            return {
                "success": False,
                "message_id": None,
                "message": "Failed to send test alert (check logs for details)",
            }

    except Exception as exc:
        logger.error(f"Failed to send test alert: {exc}")
        raise HTTPException(status_code=500, detail="Failed to send test alert")
