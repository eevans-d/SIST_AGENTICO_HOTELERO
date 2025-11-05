# [PROMPT 2.10] tests/conftest.py

import warnings
import pytest
import pytest_asyncio
import httpx
# Silenciar DeprecationWarning específico de passlib (crypt será removido en Python 3.13)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="passlib.utils")

from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Any


# Reset Prometheus default registry between tests to avoid duplicated timeseries
@pytest_asyncio.fixture(autouse=True)
async def _reset_prometheus_registry() -> Any:
    try:
        from prometheus_client import REGISTRY, PROCESS_COLLECTOR, PLATFORM_COLLECTOR, GC_COLLECTOR
        # Unregister all custom collectors (keep process/platform/gc)
        for collector in list(getattr(REGISTRY, "_collector_to_names", {}).keys()):
            if collector not in {PROCESS_COLLECTOR, PLATFORM_COLLECTOR, GC_COLLECTOR}:
                try:
                    REGISTRY.unregister(collector)
                except Exception:
                    pass
    except Exception:
        # If prometheus_client not present or API changes, ignore silently
        pass
    yield


# --- Compatibility shim for httpx.AsyncClient(app=..., base_url=...) in newer httpx versions ---
# Some tests use AsyncClient(app=app, base_url="http://test"), which was removed in newer httpx.
# Provide a lightweight subclass that accepts `app` and translates it into an ASGITransport.
try:
    from httpx import ASGITransport  # type: ignore
except Exception:  # pragma: no cover - older httpx
    ASGITransport = None  # type: ignore


class _AsyncClientCompat(httpx.AsyncClient):  # type: ignore[misc]
    def __init__(self, *args, app=None, **kwargs):  # type: ignore[no-untyped-def]
        if app is not None and "transport" not in kwargs:
            try:
                if ASGITransport is not None:
                    kwargs["transport"] = ASGITransport(app=app)
            except Exception:
                # Fallback: leave transport unset
                pass
        super().__init__(*args, **kwargs)


# Apply the shim globally for tests
httpx.AsyncClient = _AsyncClientCompat  # type: ignore[assignment]


@pytest_asyncio.fixture
async def test_app():
    # Lógica para crear una app de prueba con BD temporal
    from app.main import app

    # Usar almacenamiento en memoria para el rate limiter en pruebas
    app.state.limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
    return app


@pytest_asyncio.fixture(autouse=True)
async def _force_memory_rate_limiter():
    """Configura el rate limiter en memoria para todas las pruebas (autouse)."""
    from app.main import app

    app.state.limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
    yield
