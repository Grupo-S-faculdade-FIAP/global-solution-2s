"""Input validation utilities for S3 keys, bucket names, and control characters.

Fornece validadores robustos para dados de entrada, evitando injection attacks.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Expressão regular para validar bucket names S3
_S3_BUCKET_PATTERN = re.compile(r"^[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]$")

# Expressão regular para validar S3 keys (sem path traversal, sem control chars)
_S3_KEY_PATTERN = re.compile(r"^[^\x00-\x1f\x7f]*$")

# Caracteres de controle ASCII
_CONTROL_CHARS = set(chr(i) for i in range(32)) | {chr(127)}


def validate_s3_bucket_name(bucket: str) -> None:
    """Valida nome de bucket S3."""
    if not bucket or len(bucket) < 3 or len(bucket) > 63:
        raise ValueError(
            f"Invalid S3 bucket name (must be 3-63 chars): {bucket}"
        )

    if not _S3_BUCKET_PATTERN.match(bucket):
        raise ValueError(
            f"Invalid S3 bucket name (must be lowercase alphanumeric + dash): {bucket}"
        )

    if ".." in bucket or bucket.startswith("/"):
        raise ValueError(f"Invalid S3 bucket name (path traversal): {bucket}")


def validate_s3_key(key: str) -> None:
    """Valida chave S3 (object key)."""
    if not key:
        raise ValueError("S3 key cannot be empty")

    if ".." in key:
        raise ValueError(f"Invalid S3 key (path traversal): {key}")

    if key.startswith("/"):
        raise ValueError(f"Invalid S3 key (leading slash): {key}")

    if not _S3_KEY_PATTERN.match(key):
        raise ValueError(
            f"Invalid S3 key (contains control characters): {repr(key)}"
        )

    if any(c in key for c in "\n\r\t\x00"):
        raise ValueError(f"Invalid S3 key (contains forbidden chars): {repr(key)}")


def contains_control_characters(text: str) -> bool:
    """Verifica se string contém control characters."""
    return any(c in _CONTROL_CHARS for c in text)


def sanitize_s3_key(key: str, max_length: int = 1024) -> str:
    """Remove control characters de S3 key."""
    sanitized = "".join(c for c in key if c not in _CONTROL_CHARS)
    sanitized = sanitized.replace("..", "")
    sanitized = sanitized.lstrip("/")
    
    if len(sanitized) > max_length:
        logger.warning(
            "S3 key truncated from %d to %d chars", len(sanitized), max_length
        )
        sanitized = sanitized[:max_length]

    if not sanitized:
        raise ValueError("S3 key becomes empty after sanitization")

    return sanitized


def validate_alert_id(alert_id: str) -> None:
    """Valida formato de alert_id."""
    if not alert_id or len(alert_id) < 6:
        raise ValueError(f"Invalid alert_id (too short): {alert_id}")

    if not re.match(r"^storm_[a-f0-9]{16}$", alert_id):
        raise ValueError(
            f"Invalid alert_id (must match storm_[hex16]): {alert_id}"
        )


def validate_detection_count(count: Optional[int]) -> None:
    """Valida detections count."""
    if count is not None:
        if not isinstance(count, int) or count < 0:
            raise ValueError(f"Invalid detection_count (must be non-negative int): {count}")


def validate_confidence(confidence: Optional[float]) -> None:
    """Valida confidence score (0.0 - 1.0)."""
    if confidence is not None:
        if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
            raise ValueError(
                f"Invalid confidence (must be float 0.0-1.0): {confidence}"
            )
