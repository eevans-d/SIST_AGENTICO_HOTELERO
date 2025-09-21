import json
import hmac
import hashlib
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.settings import settings


@pytest.mark.asyncio
async def test_whatsapp_webhook_verification_get_success():
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": settings.whatsapp_verify_token.get_secret_value(),
        "hub.challenge": "test-challenge",
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/webhooks/whatsapp", params=params)
    assert resp.status_code == 200
    assert resp.text == "test-challenge"


@pytest.mark.asyncio
async def test_whatsapp_webhook_verification_get_forbidden():
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "bad-token",
        "hub.challenge": "ignored",
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/webhooks/whatsapp", params=params)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_whatsapp_webhook_post_signature_valid():
    body = json.dumps({"entry": []}).encode()
    app_secret = settings.whatsapp_app_secret.get_secret_value().encode()
    digest = hmac.new(app_secret, body, hashlib.sha256).hexdigest()
    headers = {"X-Hub-Signature-256": f"sha256={digest}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/webhooks/whatsapp", content=body, headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_whatsapp_webhook_post_signature_invalid():
    body = json.dumps({"entry": []}).encode()
    headers = {"X-Hub-Signature-256": "sha256=bad"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/webhooks/whatsapp", content=body, headers=headers)
    assert resp.status_code == 401
