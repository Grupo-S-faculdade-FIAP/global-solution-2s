"""AWS X-Ray distributed tracing integration.

Instrumenta operações do boto3, requests, e handlers Lambda.
"""

import logging
import os
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Flag para ativar/desativar X-Ray
XRAY_ENABLED = os.environ.get("XRAY_ENABLED", "true").lower() in ("1", "true", "yes", "on")


def init_xray() -> None:
    """Inicializa X-Ray tracing se XRAY_ENABLED=true.

    Instrumenta boto3 e requests automaticamente.
    """
    if not XRAY_ENABLED:
        logger.debug("X-Ray tracing disabled (XRAY_ENABLED=false)")
        return

    try:
        from aws_xray_sdk.core import xray_recorder
        from aws_xray_sdk.core import patch_all

        # Patch boto3 e requests automaticamente
        patch_all()
        xray_recorder.configure(
            context_missing="LOG_ERROR",
            emitter=lambda x: logger.debug("X-Ray segment: %s", x),
        )
        logger.info("X-Ray tracing initialized")
    except ImportError:
        logger.warning(
            "aws-xray-sdk not installed. Install with: pip install aws-xray-sdk"
        )
    except Exception as exc:
        logger.error("Failed to initialize X-Ray: %s", exc)


def add_trace_metadata(key: str, value: Any) -> None:
    """Adiciona metadata de tracing ao segmento X-Ray atual.

    Args:
        key: Nome da chave de metadata.
        value: Valor a ser rastreado.
    """
    if not XRAY_ENABLED:
        return

    try:
        from aws_xray_sdk.core import xray_recorder

        xray_recorder.current_segment().put_metadata(key, value)
    except Exception as exc:
        logger.debug("Failed to add X-Ray metadata %s: %s", key, exc)


def start_subsegment(name: str) -> Any:
    """Inicia subsegmento nomeado para rastreamento de operações específicas.

    Pode ser usado como context manager:
        with start_subsegment("yolo_inference"):
            # operação a ser rastreada

    Args:
        name: Nome do subsegmento.

    Returns:
        Contexto de subsegmento ou None se X-Ray desabilitado.
    """
    if not XRAY_ENABLED:
        # Retorna um dummy context manager
        class DummyContext:
            def __enter__(self) -> "DummyContext":
                return self
            def __exit__(self, *args: Any) -> None:
                pass

        return DummyContext()

    try:
        from aws_xray_sdk.core import xray_recorder

        return xray_recorder.begin_subsegment(name)
    except Exception as exc:
        logger.debug("Failed to start X-Ray subsegment %s: %s", name, exc)
        # Retorna dummy se falhar
        class DummyContext:
            def __enter__(self) -> "DummyContext":
                return self
            def __exit__(self, *args: Any) -> None:
                pass

        return DummyContext()


def wrap_lambda_handler(handler: Callable) -> Callable:
    """Wrapper para instrumentar Lambda handler com X-Ray.

    Args:
        handler: Função handler Lambda (event, context) -> response.

    Returns:
        Handler instrumentado com X-Ray.
    """
    if not XRAY_ENABLED:
        return handler

    try:
        from aws_xray_sdk.core import xray_recorder

        def wrapped_handler(event: dict, context: Any) -> Any:
            xray_recorder.begin_segment(
                name=getattr(context, "function_name", "lambda_handler"),
                namespace="aws",
            )
            try:
                return handler(event, context)
            finally:
                xray_recorder.end_segment()

        return wrapped_handler
    except ImportError:
        logger.warning("X-Ray wrapper not available, returning handler unchanged")
        return handler
