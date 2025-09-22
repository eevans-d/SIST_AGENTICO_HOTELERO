# [PROMPT 2.10] tests/integration/test_orchestrator.py

import pytest
import json
import hmac
import hashlib
from httpx import AsyncClient, ASGITransport
from typing import Any, cast

from app.main import app
from app.core.settings import settings


@pytest.mark.asyncio
async def test_full_availability_flow():
    # Payload mínimo de WhatsApp con mensaje de texto
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "wamid.HBgM...",
                                    "from": "5491100000000",
                                    "timestamp": "1717090000",
                                    "type": "text",
                                    "text": {"body": "Hola, disponibilidad?"},
                                }
                            ],
                            "contacts": [{"wa_id": "5491100000000"}],
                        }
                    }
                ]
            }
        ]
    }

    body = json.dumps(payload).encode()
    app_secret = settings.whatsapp_app_secret.get_secret_value().encode()
    digest = hmac.new(app_secret, body, hashlib.sha256).hexdigest()
    headers = {"X-Hub-Signature-256": f"sha256={digest}"}

    transport = ASGITransport(app=cast(Any, app))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/webhooks/whatsapp", content=body, headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "¿Querés reservar?" in data["response"]
