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


@pytest.mark.asyncio
async def test_room_options_dates_formatted_by_locale(orch):
    # ES
    msg_es = UnifiedMessage(
        message_id="m3",
        canal="whatsapp",
        user_id="u3",
        timestamp_iso="2025-01-01T00:00:00Z",
        tipo="text",
        texto="habitaciones",
        metadata={"detected_language": "es"},
        tenant_id="tenantC",
    )
    resp_es = await orch._handle_room_options({"intent": {"name": "show_room_options"}}, {}, msg_es)
    body_es = resp_es["content"].get("body_text", "")
    # En ES, dd/mm: la fecha de checkout debe verse como 05/01/2023
    assert "05/01/2023" in body_es

    # EN
    msg_en = UnifiedMessage(
        message_id="m4",
        canal="whatsapp",
        user_id="u4",
        timestamp_iso="2025-01-01T00:00:00Z",
        tipo="text",
        texto="rooms",
        metadata={"detected_language": "en"},
        tenant_id="tenantD",
    )
    resp_en = await orch._handle_room_options({"intent": {"name": "show_room_options"}}, {}, msg_en)
    body_en = resp_en["content"].get("body_text", "")
    # En EN, mm/dd: la fecha de checkout debe verse como 01/05/2023
    assert "01/05/2023" in body_en


@pytest.mark.asyncio
async def test_fallback_localized_message(orch):
    msg_en = UnifiedMessage(
        message_id="m5",
        canal="whatsapp",
        user_id="u5",
        timestamp_iso="2025-01-01T00:00:00Z",
        tipo="text",
        texto="",
        metadata={"detected_language": "en"},
        tenant_id="tenantE",
    )
    resp = await orch._handle_fallback_response(msg_en, respond_with_audio=False)
    assert resp["response_type"] == "text"
    assert "I'm not sure I understood" in resp["content"]
