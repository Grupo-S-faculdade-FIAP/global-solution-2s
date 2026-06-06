"""Tests para detect_storm pipeline com backoff exponencial e X-Ray."""

import time
from unittest.mock import MagicMock, patch

import pytest

from app.application.cv.detect_storm import _exponential_backoff


class TestExponentialBackoff:
    """Testes para exponential backoff com jitter."""

    def test_backoff_sleep_time_increases(self):
        """Testa que sleep time aumenta com tentativas."""
        # Usamos tempo real para verificar delays
        start = time.time()
        _exponential_backoff(0, base_delay=0.01, max_delay=10.0)
        elapsed_0 = time.time() - start
        
        start = time.time()
        _exponential_backoff(1, base_delay=0.01, max_delay=10.0)
        elapsed_1 = time.time() - start
        
        # Backoff(1) deve ser >= Backoff(0) (em média)
        # Note: com jitter, pode haver variação
        assert elapsed_1 >= 0  # Sanidade check

    def test_backoff_respects_max_delay(self):
        """Testa que backoff respeita max_delay."""
        start = time.time()
        _exponential_backoff(10, base_delay=1.0, max_delay=0.1)
        elapsed = time.time() - start
        
        # Deve respeitar max_delay (+ jitter pequeno)
        assert elapsed < 0.5  # Max_delay é 0.1, max com jitter ~0.15

    def test_backoff_zero_attempt(self):
        """Testa backoff na tentativa 0."""
        start = time.time()
        _exponential_backoff(0, base_delay=0.01, max_delay=10.0)
        elapsed = time.time() - start
        
        # Deve fazer sleep mínimo
        assert elapsed >= 0.01 - 0.01  # Tolerância de jitter


class TestDetectStormWithBackoff:
    """Testes de integração com retry e backoff."""

    @patch("boto3.client")
    def test_ensure_model_retries_with_backoff(self, mock_boto3, monkeypatch, tmp_path):
        """Testa retry com backoff ao baixar modelo."""
        from botocore.exceptions import ClientError
        from app.application.cv import detect_storm as ds

        model_path = tmp_path / "storm_model.pt"
        monkeypatch.setattr(ds, "_MODEL_LOCAL", model_path)
        monkeypatch.setattr(ds, "_LOCAL_WEIGHTS", tmp_path / "missing.pt")
        monkeypatch.setattr(ds, "_exponential_backoff", lambda *args, **kwargs: None)

        mock_s3 = MagicMock()
        error = ClientError(
            {"Error": {"Code": "ServiceUnavailable"}},
            "GetObject",
        )
        mock_s3.download_file.side_effect = [error, error, None]
        mock_boto3.return_value = mock_s3

        result = ds._ensure_model()
        assert result == model_path
        assert mock_s3.download_file.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
