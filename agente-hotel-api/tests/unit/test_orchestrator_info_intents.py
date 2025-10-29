import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

from app.services.orchestrator import Orchestrator
from app.models.unified_message import UnifiedMessage


@pytest_asyncio.fixture
async def orch(monkeypatch):
    pms_adapter = AsyncMock()
    session_manager = AsyncMock()
    lock_service = AsyncMock()

    # No interfiere con business hours check
    monkeypatch.setattr("app.services.orchestrator.Orchestrator._handle_business_hours", AsyncMock(return_value=None))

    return Orchestrator(pms_adapter, session_manager, lock_service)


@pytest.mark.asyncio
async def test_pricing_info_intent_text_response(orch):
    msg = UnifiedMessage(
        message_id="m1",
        canal="whatsapp",
        user_id="u1",
        timestamp_iso="2025-01-01T00:00:00Z",
        tipo="text",
        texto="precios",
        metadata={"detected_language": "es"},
        tenant_id="tenantA",
    )

    nlp_result = {"intent": {"name": "pricing_info", "confidence": 0.8}, "language": "es"}
    session = {}

    resp = await orch.handle_intent(nlp_result, session, msg)

    assert resp["response_type"] == "text"
    assert isinstance(resp["content"], str) and len(resp["content"]) > 0


@pytest.mark.asyncio
async def test_escalation_fallback_human_needed(monkeypatch, orch):
    # Evitar envío real de alertas
    monkeypatch.setattr("app.services.orchestrator.alert_manager.send_alert", AsyncMock(return_value=None))

    msg = UnifiedMessage(
        message_id="m2",
        canal="whatsapp",
        user_id="u2",
        timestamp_iso="2025-01-01T00:00:00Z",
        tipo="text",
        texto="",
        metadata={"detected_language": "es"},
        tenant_id="tenantB",
    )

    session = {"history": []}

    # Forzar reason nlp_failure
    resp = await orch._escalate_to_staff(message=msg, reason="nlp_failure", intent="unknown", session_data=session)

    assert resp["response_type"] == "text"
    assert isinstance(resp["content"], str) and len(resp["content"]) > 0
