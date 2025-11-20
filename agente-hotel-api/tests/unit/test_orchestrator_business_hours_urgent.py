import pytest

from app.services.orchestrator import Orchestrator
from app.services.session_manager import SessionManager
from app.services.lock_service import LockService
from tests.factories import unified_message, tenant_meta


class _DummyPMS:
    async def check_late_checkout_availability(self, **kwargs):
        return {"available": False}


@pytest.mark.asyncio
async def test_after_hours_urgent_escalation(monkeypatch):
    # Forzar fuera de horario
    monkeypatch.setattr("app.services.orchestrator.is_business_hours", lambda **kwargs: False, raising=False)

    # Orquestador con servicios en memoria
    orch = Orchestrator(_DummyPMS(), SessionManager(), LockService())

    # Mensaje urgente
    msg = unified_message(texto="Es URGENTE, necesito ayuda", tipo="text")

    res = await orch.handle_unified_message(msg)

    assert res["response_type"] == "text"
    # Debe contener template de escalamiento
    assert "derivando" in res["content"].lower() or "escalating" in res["content"].lower()
