import pytest
from httpx import AsyncClient, ASGITransport

# Validamos que el middleware de seguridad inyecta headers clave y no cachea endpoints críticos.

@pytest.mark.asyncio
async def test_security_headers_present(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/health/live")
    h = resp.headers
    for header in [
        "X-Content-Type-Options",
        "X-Frame-Options",
        "X-XSS-Protection",
        "Content-Security-Policy",
        "Referrer-Policy",
        "Permissions-Policy",
    ]:
        assert header in h, f"Header faltante: {header}"
    assert h.get("Cache-Control") == "no-store"

@pytest.mark.asyncio
async def test_cache_control_non_get(test_app):
    # Endpoint admin (si existe) o health para simular POST; usaremos /health/live (permitirá 405 pero headers se añaden en respuesta)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/health/live")
    # Aunque sea 405, el middleware ejecuta y añade headers
    assert resp.status_code in (200, 404, 405)
    assert resp.headers.get("Cache-Control") == "no-store"

@pytest.mark.asyncio
async def test_csp_contains_self(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/metrics")
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
