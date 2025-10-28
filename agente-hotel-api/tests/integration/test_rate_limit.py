import asyncio
import hashlib
import hmac
import json
import os
from typing import Any, Dict

import pytest
import pytest_asyncio
from httpx import AsyncClient
try:
    # httpx>=0.28
    from httpx import ASGITransport
except Exception:  # pragma: no cover - fallback for older httpx
    ASGITransport = None  # type: ignore

from app.main import app
from app.core.settings import get_settings


class _DummyWhatsAppClient:
    def __init__(self, *args, **kwargs) -> None:  # pragma: no cover - trivial
        pass

    async def send_message(self, *args, **kwargs) -> Dict[str, Any]:  # pragma: no cover - stubbed
        return {"status": "ok"}

    async def send_audio_message(self, *args, **kwargs) -> Dict[str, Any]:  # pragma: no cover - stubbed
        return {"status": "ok"}

    async def send_interactive_message(self, *args, **kwargs) -> Dict[str, Any]:  # pragma: no cover - stubbed
        return {"status": "ok"}

    async def send_image(self, *args, **kwargs) -> Dict[str, Any]:  # pragma: no cover - stubbed
        return {"status": "ok"}

    async def send_location(self, *args, **kwargs) -> Dict[str, Any]:  # pragma: no cover - stubbed
        return {"status": "ok"}

    async def send_reaction(self, *args, **kwargs) -> Dict[str, Any]:  # pragma: no cover - stubbed
        return {"status": "ok"}

    async def close(self) -> None:  # pragma: no cover - stubbed
        return None


@pytest_asyncio.fixture
async def test_client(monkeypatch):
    # Ensure rate limiting is active in tests
    settings = get_settings()
    # Force DEBUG=false for this test session so limiter is enforced
    original_debug = settings.debug
    settings.debug = False

    # Patch WhatsApp client used by webhook to avoid external calls during POST
    import app.services.whatsapp_client as whatsapp_client_mod

    monkeypatch.setattr(whatsapp_client_mod, "WhatsAppMetaClient", _DummyWhatsAppClient)

    transport = ASGITransport(app=app) if ASGITransport else None
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    # Restore debug flag
    settings.debug = original_debug


def _make_whatsapp_signature(secret: str, body: bytes) -> str:
    mac = hmac.new(secret.encode("utf-8"), msg=body, digestmod=hashlib.sha256)
    return mac.hexdigest()


@pytest.mark.asyncio
async def test_rate_limit_whatsapp_get_returns_429_after_limit(test_client):
    settings = get_settings()

    # Build valid verification query so baseline requests succeed until limit hit
    token = settings.whatsapp_verify_token.get_secret_value() if hasattr(settings.whatsapp_verify_token, "get_secret_value") else str(settings.whatsapp_verify_token)
    params = {
        "hub.mode": "subscribe",
        "hub.challenge": "12345",
        "hub.verify_token": token,
    }

    # The GET endpoint is limited at 60/min; send 61 requests
    last_response = None
    for _ in range(61):
        last_response = await test_client.get("/webhooks/whatsapp", params=params)

    assert last_response is not None
    assert last_response.status_code == 429, last_response.text


@pytest.mark.asyncio
async def test_rate_limit_whatsapp_post_returns_429_after_limit(test_client):
    settings = get_settings()

    # Minimal WhatsApp webhook body
    body_dict = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba_id",
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "1234567890",
                                    "id": "wamid.HBgLMjM0NTY3ODkw",
                                    "timestamp": "1699999999",
                                    "type": "text",
                                    "text": {"body": "hola"},
                                }
                            ]
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }
    body_bytes = json.dumps(body_dict).encode("utf-8")

    secret = settings.whatsapp_app_secret.get_secret_value() if hasattr(settings.whatsapp_app_secret, "get_secret_value") else str(settings.whatsapp_app_secret)
    signature = _make_whatsapp_signature(secret, body_bytes)

    headers = {
        "X-Hub-Signature-256": f"sha256={signature}",
        "Content-Type": "application/json",
    }

    # POST endpoint limited at 120/min; send 121 requests
    # This should be fast due to stubbed WhatsApp client and minimal local processing
    last_response = None
    for _ in range(121):
        last_response = await test_client.post("/webhooks/whatsapp", content=body_bytes, headers=headers)

    assert last_response is not None
    assert last_response.status_code == 429, last_response.text
