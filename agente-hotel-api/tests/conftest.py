# [PROMPT 2.10] tests/conftest.py

import pytest_asyncio
from slowapi import Limiter
from slowapi.util import get_remote_address


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
