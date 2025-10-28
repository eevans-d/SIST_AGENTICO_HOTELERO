# [PROMPT 2.11] tests/integration/test_orchestrator_errors.py

import json
import hmac
import hashlib
import pytest
from httpx import AsyncClient, ASGITransport
from typing import Any, cast

from app.main import app
from app.core.settings import settings
from app.services.orchestrator import Orchestrator
from app.services.nlp_engine import NLPEngine
from app.exceptions.pms_exceptions import PMSError


def _build_signed_headers_and_body(payload: dict) -> tuple[bytes, dict[str, str]]:
    body = json.dumps(payload).encode()
    app_secret = settings.whatsapp_app_secret.get_secret_value().encode()
    digest = hmac.new(app_secret, body, hashlib.sha256).hexdigest()
    headers = {"X-Hub-Signature-256": f"sha256={digest}"}
    return body, headers


@pytest.mark.asyncio
async def test_nlp_service_failure_rule_based_unknown_returns_technical_error(monkeypatch):
    # Patch NLPEngine.process_message to raise an exception simulating NLP outage
    async def _raise_nlp_error(self, text: str, language: str | None = None):  # type: ignore[override]
        raise Exception("NLP down")

    monkeypatch.setattr(NLPEngine, "process_message", _raise_nlp_error)

    # Minimal WhatsApp payload with neutral text (won't match rule-based keywords)
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "wamid.1",
                                    "from": "5491100000000",
                                    "timestamp": "1717090000",
                                    "type": "text",
                                    "text": {"body": "hola asdf qwerty"},
                                }
                            ],
                            "contacts": [{"wa_id": "5491100000000"}],
                        }
                    }
                ]
            }
        ]
    }

    body, headers = _build_signed_headers_and_body(payload)

    transport = ASGITransport(app=cast(Any, app))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/webhooks/whatsapp", content=body, headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    # Should include a textual response with technical error guidance in Spanish
    assert "response" in data
    assert "problemas técnicos" in data["response"]


@pytest.mark.asyncio
async def test_very_low_confidence_triggers_low_confidence_message(monkeypatch):
    # Patch NLPEngine.process_message to return very low confidence
    async def _very_low_conf(self, text: str, language: str | None = None):  # type: ignore[override]
        return {"intent": {"name": "unknown", "confidence": 0.1}, "language": "es"}

    monkeypatch.setattr(NLPEngine, "process_message", _very_low_conf)

    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "wamid.2",
                                    "from": "5491100000001",
                                    "timestamp": "1717090001",
                                    "type": "text",
                                    "text": {"body": "texto ambiguo"},
                                }
                            ],
                            "contacts": [{"wa_id": "5491100000001"}],
                        }
                    }
                ]
            }
        ]
    }

    body, headers = _build_signed_headers_and_body(payload)

    transport = ASGITransport(app=cast(Any, app))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/webhooks/whatsapp", content=body, headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    # Low confidence path returns a clarification message
    assert "response" in data
    assert "No estoy seguro de haber entendido" in data["response"]


@pytest.mark.asyncio
async def test_pms_error_yields_degraded_response_for_availability(monkeypatch):
    # Force intent to check_availability with high confidence so we go through handle_intent
    async def _availability_intent(self, text: str, language: str | None = None):  # type: ignore[override]
        return {"intent": {"name": "check_availability", "confidence": 0.95}, "language": "es"}

    monkeypatch.setattr(NLPEngine, "process_message", _availability_intent)

    # Make orchestrator.handle_intent raise a PMSError to trigger degraded response branch
    async def _raise_pms_error(self, nlp_result, session, message):  # type: ignore[override]
        raise PMSError("PMS down")

    monkeypatch.setattr(Orchestrator, "handle_intent", _raise_pms_error)

    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "wamid.3",
                                    "from": "5491100000002",
                                    "timestamp": "1717090002",
                                    "type": "text",
                                    "text": {"body": "disponibilidad por favor"},
                                }
                            ],
                            "contacts": [{"wa_id": "5491100000002"}],
                        }
                    }
                ]
            }
        ]
    }

    body, headers = _build_signed_headers_and_body(payload)

    transport = ASGITransport(app=cast(Any, app))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/webhooks/whatsapp", content=body, headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    # Degraded message for availability intent
    assert "response" in data
    assert "temporalmente fuera de servicio" in data["response"]
