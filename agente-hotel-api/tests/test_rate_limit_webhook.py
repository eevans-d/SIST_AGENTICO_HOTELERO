import pytest
from httpx import AsyncClient, ASGITransport
from typing import Any, cast

from app.main import app
from app.core.settings import settings
from slowapi import Limiter
from slowapi.util import get_remote_address


@pytest.mark.asyncio
async def test_webhook_get_rate_limited(monkeypatch):
    # Forzar que el decorador de rate limit no se salte en modo debug
    original_debug = settings.debug
    settings.debug = False
    try:
        # Forzar almacenamiento en memoria para el limiter durante esta prueba
        app.state.limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
        transport = ASGITransport(app=cast(Any, app))
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = None
            # Límite configurado: 60/min para GET /webhooks/whatsapp
            for _ in range(61):
                resp = await ac.get("/webhooks/whatsapp")
            assert resp is not None
            assert resp.status_code == 429
    finally:
        settings.debug = original_debug
