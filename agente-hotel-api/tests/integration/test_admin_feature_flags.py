import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_feature_flags_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/admin/feature-flags")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_feature_flags_with_auth_returns_defaults():
    token = create_access_token(data={"sub": "testuser"})
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/admin/feature-flags", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "flags" in data
    flags = data["flags"]
    # Debe incluir al menos estos flags por default
    assert "features.interactive_messages" in flags
    assert "tenancy.dynamic.enabled" in flags