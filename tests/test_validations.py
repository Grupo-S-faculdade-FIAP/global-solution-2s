"""Tests for input validation utilities.

Testa validators robustos para S3 keys, bucket names, e control characters.
"""

import pytest

from app.utils.validators import (
    contains_control_characters,
    sanitize_s3_key,
    validate_alert_id,
    validate_confidence,
    validate_detection_count,
    validate_s3_bucket_name,
    validate_s3_key,
)


class TestS3BucketValidation:
    """Testes para validação de bucket names."""

    def test_valid_bucket_name(self):
        """Testa bucket name válido."""
        validate_s3_bucket_name("my-bucket-123")
        validate_s3_bucket_name("test")
        validate_s3_bucket_name("a1b2c3")

    def test_invalid_bucket_too_short(self):
        """Testa bucket name muito curto."""
        with pytest.raises(ValueError, match="3-63 chars"):
            validate_s3_bucket_name("ab")

    def test_invalid_bucket_too_long(self):
        """Testa bucket name muito longo."""
        with pytest.raises(ValueError, match="3-63 chars"):
            validate_s3_bucket_name("a" * 64)

    def test_invalid_bucket_uppercase(self):
        """Testa bucket name com maiúsculas (não permitidas)."""
        with pytest.raises(ValueError, match="lowercase"):
            validate_s3_bucket_name("MyBucket")

    def test_invalid_bucket_special_chars(self):
        """Testa bucket name com caracteres especiais."""
        with pytest.raises(ValueError, match="lowercase"):
            validate_s3_bucket_name("my_bucket")
        with pytest.raises(ValueError, match="lowercase"):
            validate_s3_bucket_name("my.bucket")

    def test_invalid_bucket_path_traversal(self):
        """Testa bucket name com path traversal."""
        with pytest.raises(ValueError, match="lowercase|path traversal"):
            validate_s3_bucket_name("../bucket")

    def test_invalid_bucket_starting_with_dash(self):
        """Testa bucket name começando com hífen."""
        with pytest.raises(ValueError, match="lowercase"):
            validate_s3_bucket_name("-bucket")


class TestS3KeyValidation:
    """Testes para validação de S3 keys."""

    def test_valid_key(self):
        """Testa S3 key válida."""
        validate_s3_key("screenshots/image.jpg")
        validate_s3_key("images/2024/storm_001.png")
        validate_s3_key("folder/subfolder/file.bin")

    def test_invalid_empty_key(self):
        """Testa S3 key vazia."""
        with pytest.raises(ValueError, match="empty"):
            validate_s3_key("")

    def test_invalid_key_path_traversal(self):
        """Testa S3 key com path traversal."""
        with pytest.raises(ValueError, match="path traversal"):
            validate_s3_key("../../../etc/passwd")

    def test_invalid_key_leading_slash(self):
        """Testa S3 key com leading slash."""
        with pytest.raises(ValueError, match="leading slash"):
            validate_s3_key("/images/file.jpg")

    def test_invalid_key_newline(self):
        """Testa S3 key com newline."""
        with pytest.raises(ValueError, match="control characters|forbidden"):
            validate_s3_key("image\n.jpg")

    def test_invalid_key_tab(self):
        """Testa S3 key com tab."""
        with pytest.raises(ValueError, match="control characters|forbidden"):
            validate_s3_key("image\t.jpg")

    def test_invalid_key_null_byte(self):
        """Testa S3 key com null byte."""
        with pytest.raises(ValueError, match="forbidden|control"):
            validate_s3_key("image\x00.jpg")


class TestControlCharacterDetection:
    """Testes para detecção de control characters."""

    def test_clean_string(self):
        """Testa string sem control characters."""
        assert not contains_control_characters("normal text")
        assert not contains_control_characters("file_123.jpg")

    def test_string_with_newline(self):
        """Testa string com newline."""
        assert contains_control_characters("text\nmore")

    def test_string_with_null_byte(self):
        """Testa string com null byte."""
        assert contains_control_characters("text\x00more")

    def test_string_with_tab(self):
        """Testa string com tab."""
        assert contains_control_characters("text\tmore")


class TestS3KeySanitization:
    """Testes para sanitização de S3 keys."""

    def test_sanitize_removes_control_chars(self):
        """Testa remoção de control characters."""
        result = sanitize_s3_key("image\n.jpg")
        assert "\n" not in result
        assert "image" in result

    def test_sanitize_removes_path_traversal(self):
        """Testa remoção de path traversal."""
        result = sanitize_s3_key("../images/file.jpg")
        assert ".." not in result
        assert "images" in result

    def test_sanitize_removes_leading_slashes(self):
        """Testa remoção de leading slashes."""
        result = sanitize_s3_key("///images/file.jpg")
        assert not result.startswith("/")

    def test_sanitize_truncates_long_key(self):
        """Testa truncamento de keys longas."""
        long_key = "a" * 2000
        result = sanitize_s3_key(long_key, max_length=100)
        assert len(result) <= 100

    def test_sanitize_empty_raises(self):
        """Testa que sanitização vazia levanta erro."""
        with pytest.raises(ValueError, match="empty"):
            sanitize_s3_key("\x00\x01\x02")  # Apenas control chars


class TestAlertIDValidation:
    """Testes para validação de alert_id."""

    def test_valid_alert_id(self):
        """Testa alert_id válido."""
        validate_alert_id("storm_abc123def4567890")
        validate_alert_id("storm_0000000000000000")
        validate_alert_id("storm_ffffffffffffffff")

    def test_invalid_alert_id_wrong_prefix(self):
        """Testa alert_id com prefixo errado."""
        with pytest.raises(ValueError, match="storm_"):
            validate_alert_id("alert_abc123def456ab")

    def test_invalid_alert_id_wrong_length(self):
        """Testa alert_id com comprimento errado."""
        with pytest.raises(ValueError, match="hex16"):
            validate_alert_id("storm_abc")

    def test_invalid_alert_id_non_hex(self):
        """Testa alert_id com caracteres não-hex."""
        with pytest.raises(ValueError, match="hex16"):
            validate_alert_id("storm_abcxyzdef456ab")


class TestDetectionCountValidation:
    """Testes para validação de detection count."""

    def test_valid_detection_count(self):
        """Testa detection count válido."""
        validate_detection_count(0)
        validate_detection_count(1)
        validate_detection_count(100)
        validate_detection_count(None)

    def test_invalid_detection_count_negative(self):
        """Testa detection count negativo."""
        with pytest.raises(ValueError, match="non-negative"):
            validate_detection_count(-1)

    def test_invalid_detection_count_float(self):
        """Testa detection count float."""
        with pytest.raises(ValueError, match="non-negative"):
            validate_detection_count(1.5)


class TestConfidenceValidation:
    """Testes para validação de confidence score."""

    def test_valid_confidence(self):
        """Testa confidence válido."""
        validate_confidence(0.0)
        validate_confidence(0.5)
        validate_confidence(1.0)
        validate_confidence(None)

    def test_invalid_confidence_too_low(self):
        """Testa confidence menor que 0."""
        with pytest.raises(ValueError, match="0.0-1.0"):
            validate_confidence(-0.1)

    def test_invalid_confidence_too_high(self):
        """Testa confidence maior que 1."""
        with pytest.raises(ValueError, match="0.0-1.0"):
            validate_confidence(1.1)

    def test_invalid_confidence_string(self):
        """Testa confidence como string."""
        with pytest.raises(ValueError, match="0.0-1.0"):
            validate_confidence("0.5")
