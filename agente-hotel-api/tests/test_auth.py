# [PROMPT GA-02] tests/test_auth.py

import pytest
from fastapi import status
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_admin_endpoint_no_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/admin/dashboard")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_admin_endpoint_with_auth():
    token = create_access_token(data={"sub": "testuser"})
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/admin/dashboard", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the admin dashboard"}
