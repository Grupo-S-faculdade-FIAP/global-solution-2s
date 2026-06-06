"""Pydantic models for request/response validation."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class TestAlertRequest(BaseModel):
    """Request body for POST /alerts/test endpoint."""

    lat: float = Field(
        default=-23.5505,
        ge=-90,
        le=90,
        description="Latitude coordinate (-90 to 90)",
        example=-23.5505,
    )
    lon: float = Field(
        default=-46.6333,
        ge=-180,
        le=180,
        description="Longitude coordinate (-180 to 180)",
        example=-46.6333,
    )
    confidence: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0 to 1.0)",
        example=0.85,
    )

    @field_validator("lat")
    @classmethod
    def validate_lat(cls, v: float) -> float:
        """Validate latitude is within valid range."""
        if not -90 <= v <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator("lon")
    @classmethod
    def validate_lon(cls, v: float) -> float:
        """Validate longitude is within valid range."""
        if not -180 <= v <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Validate confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v


class DLQQueryParams(BaseModel):
    """Query parameters for GET /alerts/dlq endpoint."""

    max_messages: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum messages to retrieve (1-100, default 10)",
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {"max_messages": 10},
        }


class RetryDLQRequest(BaseModel):
    """Request body for POST /alerts/retry-dlq endpoint."""

    max_attempts: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum messages to reprocess (1-100, default 10)",
    )
    message_ids: Optional[list[str]] = Field(
        default=None,
        description="Optional: Specific message IDs to reprocess. If None, reprocesses all.",
    )

    @field_validator("max_attempts")
    @classmethod
    def validate_max_attempts(cls, v: int) -> int:
        """Validate max_attempts is in valid range."""
        if not 1 <= v <= 100:
            raise ValueError("max_attempts must be between 1 and 100")
        return v


class HistoryQueryParams(BaseModel):
    """Query parameters for GET /alerts/history endpoint."""

    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum alerts to return (1-1000, default 100)",
    )
    skip: int = Field(
        default=0,
        ge=0,
        description="Number of alerts to skip (for pagination)",
    )

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        """Validate limit is in valid range."""
        if not 1 <= v <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        return v


class AlertStatusResponse(BaseModel):
    """Response model for GET /alerts/status."""

    enabled: bool = Field(description="SNS is enabled")
    configured: bool = Field(description="Topic is configured")
    topic_arn: Optional[str] = Field(description="Topic ARN (masked if sensitive)")
    region: str = Field(description="AWS region")
    valid: bool = Field(description="SNS setup is valid")
    issues: list[str] = Field(description="Configuration issues if any")
    dlq_available: bool = Field(description="DLQ is configured")


class MetricsResponse(BaseModel):
    """Response model for GET /alerts/metrics."""

    namespace: str = Field(default="GlobalSolutions")
    metrics: list[dict] = Field(description="CloudWatch metrics data")
    time_range_hours: int = Field(default=24)


class DLQStatsResponse(BaseModel):
    """Response model for GET /alerts/dlq."""

    queue_url: Optional[str] = Field(description="DLQ queue URL")
    stats: dict = Field(description="DLQ statistics (message count, etc)")
    messages: list[dict] = Field(description="DLQ messages")
    count: int = Field(description="Number of messages returned")


class RetryDLQResponse(BaseModel):
    """Response model for POST /alerts/retry-dlq."""

    total: int = Field(description="Total messages processed")
    succeeded: int = Field(description="Successfully reprocessed")
    failed: int = Field(description="Failed reprocessing")
    details: list[dict] = Field(description="Per-message results")
    message: str = Field(description="Status message")


class TestAlertResponse(BaseModel):
    """Response model for POST /alerts/test."""

    success: bool = Field(description="Publish succeeded")
    message_id: Optional[str] = Field(description="SNS MessageId if successful")
    message: str = Field(description="Status message")


class HistoryResponse(BaseModel):
    """Response model for GET /alerts/history."""

    alerts: list[dict] = Field(description="Recent alerts")
    count: int = Field(description="Number of alerts returned")
    message: str = Field(description="Status message")
    next_steps: Optional[list[str]] = Field(description="Recommended next steps")
