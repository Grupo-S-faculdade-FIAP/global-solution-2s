"""Tests for X-Ray distributed tracing utilities.

Testa decoradores e funções de rastreamento com X-Ray.
"""

import pytest

from app.core.xray_tracing import (
    is_xray_available,
    xray_annotation,
    xray_metadata,
    xray_subsegment,
    xray_traced,
)


def test_xray_available():
    """Testa função is_xray_available()."""
    result = is_xray_available()
    assert isinstance(result, bool)


def test_xray_metadata_noop_when_disabled():
    """Testa que xray_metadata não falha se X-Ray desabilitado."""
    xray_metadata("test_key", "test_value")
    xray_metadata("number", 42)
    xray_metadata("dict", {"a": 1})


def test_xray_annotation_noop_when_disabled():
    """Testa que xray_annotation não falha se X-Ray desabilitado."""
    xray_annotation("test_annotation", "value1")
    xray_annotation("status", "success")


def test_xray_subsegment_context_manager():
    """Testa xray_subsegment como context manager."""
    with xray_subsegment("test_operation"):
        x = 1 + 1
        assert x == 2


def test_xray_traced_decorator():
    """Testa decorador @xray_traced."""

    @xray_traced(name="test_function")
    def add(a, b):
        return a + b

    result = add(2, 3)
    assert result == 5


def test_xray_traced_decorator_with_exception():
    """Testa que decorador não mascara exceções."""

    @xray_traced(name="failing_function")
    def divide(a, b):
        return a / b

    with pytest.raises(ZeroDivisionError):
        divide(10, 0)
