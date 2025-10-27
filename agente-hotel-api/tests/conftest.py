# [PROMPT 2.10] tests/conftest.py

import pytest_asyncio
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
