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

    # Desactivar efectos de horario
    monkeypatch.setattr("app.services.orchestrator.Orchestrator._handle_business_hours", AsyncMock(return_value=None))

    # FF interactivos activado
    class FFMock:
        async def is_enabled(self, flag: str, default=None) -> bool:
            if flag == "features.interactive_messages":
                return True
            return bool(default)

    async def get_ff_mock():
        return FFMock()

    monkeypatch.setattr("app.services.orchestrator.get_feature_flag_service", get_ff_mock)

    return Orchestrator(pms_adapter, session_manager, lock_service)


@pytest.mark.asyncio
async def test_payment_confirmation_interactive_buttons_es(orch):
    session = {"reservation_pending": True}
    msg = UnifiedMessage(
        message_id="pm1",
        canal="whatsapp",
        user_id="u100",
        timestamp_iso="2025-01-01T00:00:00Z",
        tipo="text",
        texto="pago",
        metadata={"detected_language": "es"},
        tenant_id="tenant1",
    )
    nlp_result = {"intent": {"name": "payment_confirmation", "confidence": 0.9}, "language": "es"}

    resp = await orch._handle_payment_confirmation(nlp_result, session, msg)
    assert resp["response_type"] == "interactive_buttons"
    content = resp["content"]
    assert isinstance(content, dict)
    ids = [b.get("id") for b in content.get("action_buttons", [])]
    assert "transfer_request" in ids and "late_checkin" in ids


@pytest.mark.asyncio
async def test_payment_confirmation_interactive_buttons_en(orch):
    session = {"reservation_pending": True}
    msg = UnifiedMessage(
        message_id="pm2",
        canal="whatsapp",
        user_id="u101",
        timestamp_iso="2025-01-01T00:00:00Z",
        tipo="text",
        texto="payment",
        metadata={"detected_language": "en"},
        tenant_id="tenant2",
    )
    nlp_result = {"intent": {"name": "payment_confirmation", "confidence": 0.9}, "language": "en"}

    resp = await orch._handle_payment_confirmation(nlp_result, session, msg)
    assert resp["response_type"] == "interactive_buttons"
    content = resp["content"]
    assert isinstance(content, dict)
    ids = [b.get("id") for b in content.get("action_buttons", [])]
    assert "transfer_request" in ids and "late_checkin" in ids
