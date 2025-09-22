import json
import hmac
import hashlib
import pytest
from httpx import AsyncClient, ASGITransport
from typing import Any, cast

from app.main import app
from app.core.settings import settings


@pytest.mark.asyncio
async def test_whatsapp_webhook_verification_get_success():
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": settings.whatsapp_verify_token.get_secret_value(),
        "hub.challenge": "test-challenge",
    }
    transport = ASGITransport(app=cast(Any, app))
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
    transport = ASGITransport(app=cast(Any, app))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/webhooks/whatsapp", params=params)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_whatsapp_webhook_post_signature_valid():
    body = json.dumps({"entry": []}).encode()
    app_secret = settings.whatsapp_app_secret.get_secret_value().encode()
    digest = hmac.new(app_secret, body, hashlib.sha256).hexdigest()
    headers = {"X-Hub-Signature-256": f"sha256={digest}"}

    transport = ASGITransport(app=cast(Any, app))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/webhooks/whatsapp", content=body, headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_whatsapp_webhook_post_signature_invalid():
    body = json.dumps({"entry": []}).encode()
    headers = {"X-Hub-Signature-256": "sha256=bad"}

    transport = ASGITransport(app=cast(Any, app))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/webhooks/whatsapp", content=body, headers=headers)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_whatsapp_webhook_post_unsupported_media_type():
    # Firma válida pero content-type no JSON debe dar 415
    body = b"not-json"
    app_secret = settings.whatsapp_app_secret.get_secret_value().encode()
    digest = hmac.new(app_secret, body, hashlib.sha256).hexdigest()
    headers = {"X-Hub-Signature-256": f"sha256={digest}", "Content-Type": "text/plain"}

    transport = ASGITransport(app=cast(Any, app))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/webhooks/whatsapp", content=body, headers=headers)
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_whatsapp_webhook_post_payload_too_large():
    # Payload >1MB debe dar 413 incluso con firma válida
    body = b"a" * 1_000_001
    app_secret = settings.whatsapp_app_secret.get_secret_value().encode()
    digest = hmac.new(app_secret, body, hashlib.sha256).hexdigest()
    headers = {"X-Hub-Signature-256": f"sha256={digest}", "Content-Type": "application/json"}

    transport = ASGITransport(app=cast(Any, app))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/webhooks/whatsapp", content=body, headers=headers)
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_whatsapp_webhook_post_invalid_json():
    # Content-Type correcto pero JSON inválido debe dar 400
    body = b"{"  # malformed
    app_secret = settings.whatsapp_app_secret.get_secret_value().encode()
    digest = hmac.new(app_secret, body, hashlib.sha256).hexdigest()
    headers = {"X-Hub-Signature-256": f"sha256={digest}", "Content-Type": "application/json"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/webhooks/whatsapp", content=body, headers=headers)
    assert resp.status_code == 400
