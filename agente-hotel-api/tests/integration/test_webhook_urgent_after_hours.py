import hmac
import hashlib
import json
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
from prometheus_client import REGISTRY
from app.services.orchestrator import escalations_total

from app.main import app


@pytest_asyncio.fixture
async def client(monkeypatch):
    # Forzar fuera de horario en orquestador
    monkeypatch.setattr("app.services.orchestrator.is_business_hours", lambda *a, **k: False)
    # Stub alert manager
    from app.services import orchestrator as orch_module
    orch_module.alert_manager.send_alert = AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _sign(body: bytes) -> str:
    # Usar app secret actual de settings
    from app.core.settings import settings
    secret = settings.whatsapp_app_secret.get_secret_value().encode()
    digest = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


@pytest.mark.asyncio
async def test_webhook_urgent_after_hours_triggers_escalation(client):
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "m1",
                                    "from": "15551234567",
                                    "timestamp": "1700000000",
                                    "type": "text",
                                    "text": {"body": "Necesito disponibilidad URGENTE"},
                                }
                            ],
                            "contacts": [{"wa_id": "15551234567"}],
                        }
                    }
                ]
            }
        ]
    }
    body = json.dumps(payload).encode()
    sig = _sign(body)

    r = await client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
    )

    assert r.status_code == 200
    data = r.json()
    # El router con response_type=text retorna {status: ok, response: str}
    assert data["status"] == "ok"
    assert isinstance(data.get("response"), str) and len(data["response"]) > 0

    # Métrica de escalamiento
    # Leer el valor directamente del counter etiquetado
    labeled = escalations_total.labels(reason="urgent_after_hours", channel="whatsapp")
    val = labeled._value.get()  # type: ignore[attr-defined]
    assert val == 1.0
