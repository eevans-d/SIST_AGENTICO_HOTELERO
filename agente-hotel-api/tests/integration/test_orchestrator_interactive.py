import json
import hmac
import hashlib
import pytest
from typing import Any, Dict
from httpx import AsyncClient
from httpx import ASGITransport

from app.main import app
from app.core.settings import settings


class StubFF:
    async def is_enabled(self, flag: str, default: bool | None = None) -> bool:
        if flag == "features.interactive_messages":
            return True
        return bool(default) if default is not None else False


@pytest.mark.asyncio
async def test_availability_interactive_buttons(monkeypatch):
    # Monkeypatch FF service to force interactive mode
    import app.services.feature_flag_service as ff

    async def _get_stub():
        return StubFF()

    monkeypatch.setattr(ff, "get_feature_flag_service", _get_stub, raising=True)
    # Asegurar que el default también quede activado, por si el servicio cae a defaults
    ff.DEFAULT_FLAGS["features.interactive_messages"] = True

    payload: Dict[str, Any] = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "wamid.TEST",
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

    transport = ASGITransport(app=app)  # type: ignore
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/webhooks/whatsapp", content=body, headers=headers)

    assert resp.status_code == 200
    data = resp.json()

    # En modo interactivo, debe devolver tipo interactive_buttons
    assert data.get("response_type") in {"interactive_buttons", "interactive_buttons_with_image"}
    content = data.get("content") or {}

    # Validaciones básicas de la plantilla
    assert "header_text" in content
    assert "body_text" in content
    # Para 'interactive_buttons_with_image' también debe venir image_url opcional
    if data.get("response_type") == "interactive_buttons_with_image":
        assert "image_url" in data
    assert "action_buttons" in content and len(content["action_buttons"]) >= 1

    # El body_text incluye la información de disponibilidad resumida
    assert "Para" in content["body_text"] and "Total" in content["body_text"]
