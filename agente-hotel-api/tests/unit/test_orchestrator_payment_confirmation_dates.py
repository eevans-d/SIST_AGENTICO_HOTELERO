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

    # Evitar checks de horario comercial
    monkeypatch.setattr("app.services.orchestrator.Orchestrator._handle_business_hours", AsyncMock(return_value=None))

    return Orchestrator(pms_adapter, session_manager, lock_service)


@pytest.mark.asyncio
async def test_payment_confirmation_dates_formatted_es(orch):
    session = {
        "reservation_pending": True,
        # Usamos valores por defecto (MOCK_CHECKIN_DATE/OUT) para cubrir parseo ISO
    }

    msg = UnifiedMessage(
        message_id="m20",
        canal="whatsapp",
        user_id="u20",
        timestamp_iso="2025-01-01T00:00:00Z",
        tipo="text",
        texto="pago",
        metadata={"detected_language": "es"},
        tenant_id="tenant1",
    )

    nlp_result = {"intent": {"name": "payment_confirmation", "confidence": 0.9}, "language": "es"}

    resp = await orch._handle_payment_confirmation(nlp_result, session, msg)

    assert resp["response_type"] == "text"
    content = resp["content"]
    # ES dd/mm/yyyy: 15/10/2025 y 17/10/2025
    assert "15/10/2025" in content
    assert "17/10/2025" in content


@pytest.mark.asyncio
async def test_payment_confirmation_dates_formatted_en(orch):
    session = {
        "reservation_pending": True,
    }

    msg = UnifiedMessage(
        message_id="m21",
        canal="whatsapp",
        user_id="u21",
        timestamp_iso="2025-01-01T00:00:00Z",
        tipo="text",
        texto="payment",
        metadata={"detected_language": "en"},
        tenant_id="tenant2",
    )

    nlp_result = {"intent": {"name": "payment_confirmation", "confidence": 0.9}, "language": "en"}

    resp = await orch._handle_payment_confirmation(nlp_result, session, msg)

    assert resp["response_type"] == "text"
    content = resp["content"]
    # EN mm/dd/yyyy: 10/15/2025 y 10/17/2025
    assert "10/15/2025" in content
    assert "10/17/2025" in content
