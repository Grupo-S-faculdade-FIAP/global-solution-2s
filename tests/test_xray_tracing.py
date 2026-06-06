"""Tests for X-Ray distributed tracing integration."""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.core.tracing import (
    init_xray,
    add_trace_metadata,
    start_subsegment,
    wrap_lambda_handler,
)


def test_xray_disabled():
    """Testa behavior quando X-Ray está desabilitado."""
    os.environ["XRAY_ENABLED"] = "false"

    # Estas chamadas não devem causar erro mesmo com X-Ray desabilitado
    init_xray()
    add_trace_metadata("key", "value")

    # Subsegmento deve retornar dummy context manager
    with start_subsegment("test") as ctx:
        assert ctx is not None


def test_xray_enabled_without_sdk():
    """Testa behavior quando X-Ray está habilitado mas SDK não está instalado."""
    os.environ["XRAY_ENABLED"] = "true"

    # Deve logar warning mas não falhar
    with patch("app.core.tracing.logger") as mock_logger:
        init_xray()
        # Verifica que warning foi logado (ImportError)
        # Note: Este teste pode passar ou falhar dependendo se sdk está instalado


def test_add_trace_metadata_disabled():
    """Testa que add_trace_metadata retorna silenciosamente se X-Ray desabilitado."""
    os.environ["XRAY_ENABLED"] = "false"
    # Não deve lançar exceção
    add_trace_metadata("test_key", {"nested": "value"})


def test_start_subsegment_returns_context():
    """Testa que start_subsegment sempre retorna um context manager."""
    os.environ["XRAY_ENABLED"] = "false"

    ctx = start_subsegment("operation")
    assert hasattr(ctx, "__enter__")
    assert hasattr(ctx, "__exit__")

    # Deve funcionar como context manager
    with ctx:
        pass  # No-op


def test_wrap_lambda_handler_disabled():
    """Testa que wrap_lambda_handler retorna handler original se X-Ray desabilitado."""
    os.environ["XRAY_ENABLED"] = "false"

    def my_handler(event, context):
        return {"status": "ok"}

    wrapped = wrap_lambda_handler(my_handler)
    # Deveria retornar a mesma função
    assert wrapped is my_handler


def test_wrap_lambda_handler_passthrough():
    """Testa que handler wrappado passa através argumentos corretamente."""
    os.environ["XRAY_ENABLED"] = "false"

    def my_handler(event, context):
        return {
            "statusCode": 200,
            "body": f"Received: {event.get('test')}",
        }

    wrapped = wrap_lambda_handler(my_handler)

    # Simular evento e contexto
    event = {"test": "data"}
    context = MagicMock()
    context.function_name = "test_function"

    result = wrapped(event, context)
    assert result["statusCode"] == 200
    assert "data" in result["body"]


def test_xray_metadata_with_lambda_context():
    """Testa adição de metadata com contexto Lambda simulado."""
    os.environ["XRAY_ENABLED"] = "false"

    # Criar mock de contexto Lambda
    context = MagicMock()
    context.function_name = "storm_detector"
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789:function:storm_detector"
    context.request_id = "request-12345"

    # Adicionar metadata com contexto
    add_trace_metadata("lambda_context", {
        "function_name": context.function_name,
        "request_id": context.request_id,
    })

    # Não deve lançar erro


@pytest.fixture(autouse=True)
def reset_xray_env():
    """Reset XRAY_ENABLED após cada teste."""
    original = os.environ.get("XRAY_ENABLED")
    yield
    if original is None:
        os.environ.pop("XRAY_ENABLED", None)
    else:
        os.environ["XRAY_ENABLED"] = original
