# [PROMPT GA-02] tests/test_orchestrator_metrics.py

import pytest
from httpx import AsyncClient, ASGITransport
from typing import Any, cast
import json
import hmac
import hashlib

from app.main import app
from app.core.settings import settings


@pytest.mark.asyncio
async def test_orchestrator_metrics_exposed():
    # Disparar un flujo de mensaje de texto para generar métricas del orquestador
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
                                    "text": {"body": "Hola"},
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

        # Scrape metrics
        metrics_text = (await ac.get("/metrics")).text

    assert "orchestrator_latency_seconds_bucket" in metrics_text
    assert "orchestrator_messages_total" in metrics_text
    assert "orchestrator_errors_total" in metrics_text
