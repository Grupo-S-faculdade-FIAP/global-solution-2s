"""AWS X-Ray distributed tracing decorators and utilities.

Fornece decoradores e funções para instrumentar funções com X-Ray tracing,
com graceful fallback se o SDK não estiver instalado.
"""

import functools
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Flag para saber se X-Ray está disponível
_XRAY_AVAILABLE = False

try:
    from aws_xray_sdk.core import xray_recorder

    _XRAY_AVAILABLE = True
except ImportError:
    logger.debug("aws-xray-sdk not installed. X-Ray tracing disabled.")


def xray_traced(name: Optional[str] = None) -> Callable:
    """Decorador para instrumentar função com X-Ray subsegmento.

    Cria um subsegmento nomeado durante execução, capturando exceções e timing.

    Args:
        name: Nome do subsegmento. Se None, usa __name__ da função.

    Returns:
        Função decorada com rastreamento X-Ray.

    Example:
        @xray_traced(name="yolo_inference")
        def run_inference(image_path):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not _XRAY_AVAILABLE:
                return func(*args, **kwargs)

            segment_name = name or func.__name__
            try:
                with xray_recorder.begin_subsegment(segment_name):
                    return func(*args, **kwargs)
            except Exception as exc:
                xray_recorder.current_subsegment().add_exception(exc)
                raise

        return wrapper

    return decorator


def xray_metadata(key: str, value: Any) -> None:
    """Adiciona metadata ao segmento X-Ray atual.

    Args:
        key: Chave de metadata.
        value: Valor a ser rastreado.
    """
    if not _XRAY_AVAILABLE:
        return

    try:
        segment = xray_recorder.current_segment()
        if segment:
            segment.put_metadata(key, value)
    except Exception as exc:
        logger.debug("Failed to add X-Ray metadata %s: %s", key, exc)


def xray_annotation(key: str, value: str) -> None:
    """Adiciona anotação (indexada) ao segmento X-Ray atual.

    Anotações são indexadas e podem ser consultadas via Insights.

    Args:
        key: Chave de anotação.
        value: Valor string a ser indexado.
    """
    if not _XRAY_AVAILABLE:
        return

    try:
        segment = xray_recorder.current_segment()
        if segment:
            segment.put_annotation(key, value)
    except Exception as exc:
        logger.debug("Failed to add X-Ray annotation %s: %s", key, exc)


def xray_subsegment(name: str) -> Any:
    """Context manager para criar subsegmento X-Ray.

    Uso:
        with xray_subsegment("s3_download"):
            s3.download_file(...)

    Args:
        name: Nome do subsegmento.

    Returns:
        Context manager que cria subsegmento ou dummy se X-Ray desabilitado.
    """
    if not _XRAY_AVAILABLE:

        class DummyContext:
            def __enter__(self) -> "DummyContext":
                return self

            def __exit__(self, *args: Any) -> None:
                pass

        return DummyContext()

    try:
        return xray_recorder.begin_subsegment(name)
    except Exception as exc:
        logger.debug("Failed to create X-Ray subsegment %s: %s", name, exc)

        class DummyContext:
            def __enter__(self) -> "DummyContext":
                return self

            def __exit__(self, *args: Any) -> None:
                pass

        return DummyContext()


def is_xray_available() -> bool:
    """Retorna True se X-Ray SDK está disponível e ativo.

    Returns:
        True se X-Ray está disponível e pode ser usado.
    """
    return _XRAY_AVAILABLE
