"""Localização canônica da API pública de BFF backend.

A implementação real está em dashboard/bff_backend.py para preservar
backward compat com testes que patcham dashboard.bff_backend._fastapi_test_client.
Este módulo re-exporta tudo para que novos imports usem o caminho canônico.
"""

from dashboard.bff_backend import (  # noqa: F401
    backend_get,
    backend_post,
    use_inprocess_backend,
    fastapi_base_url,
)
