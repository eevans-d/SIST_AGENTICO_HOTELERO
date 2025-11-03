import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

from app.services.orchestrator import Orchestrator, escalations_total
from app.models.unified_message import UnifiedMessage


@pytest_asyncio.fixture
async def orch():
    # Mocks livianos para dependencias
    pms_adapter = AsyncMock()
    session_manager = AsyncMock()
    lock_service = AsyncMock()
    return Orchestrator(pms_adapter, session_manager, lock_service)


@pytest.mark.asyncio
async def test_urgent_after_hours_escalates_and_records_metric(monkeypatch, orch):
    # Forzar fuera de horario
    monkeypatch.setattr("app.services.orchestrator.is_business_hours", lambda *a, **k: False)

    # Stub alert manager
    from app.services import orchestrator as orch_module
    orch_module.alert_manager.send_alert = AsyncMock()

    # Mensaje con palabra clave de urgencia
    msg = UnifiedMessage(
        message_id="m-urgent-1",
        canal="whatsapp",
        user_id="u123",
        timestamp_iso="2025-01-01T00:00:00Z",
        tipo="text",
        texto="Necesito ayuda URGENTE",
        metadata={},
        tenant_id="tenantA",
    )

    # Ejecutar flujo de business hours
    res = await orch._handle_business_hours({"intent": "unknown"}, {}, msg)

    # Verifica escalamiento
    assert res is not None
    assert res.get("response_type") == "text"
    assert res.get("escalated") is True

    # Verifica métrica de escalamiento
    # Leer el valor directamente del counter etiquetado
    labeled = escalations_total.labels(reason="urgent_after_hours", channel="whatsapp")
    val = labeled._value.get()  # type: ignore[attr-defined]
    assert val == 1.0

    # Verifica que se envió alerta a staff
    orch_module.alert_manager.send_alert.assert_awaited()
