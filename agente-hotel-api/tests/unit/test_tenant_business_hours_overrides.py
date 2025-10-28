import pytest
from unittest.mock import AsyncMock

from app.services.orchestrator import Orchestrator
from app.models.unified_message import UnifiedMessage


@pytest.mark.asyncio
async def test_orchestrator_passes_tenant_overrides_to_business_hours(monkeypatch):
    # Arrange orchestrator with light mocks
    pms_adapter = AsyncMock()
    session_manager = AsyncMock()
    lock_service = AsyncMock()
    orch = Orchestrator(pms_adapter, session_manager, lock_service)

    # Tenant metadata overrides
    overrides = {
        "business_hours_start": 10,
        "business_hours_end": 18,
        "business_hours_timezone": "America/Argentina/Buenos_Aires",
    }

    # Stub tenant meta resolver
    from app.services import dynamic_tenant_service as dts_module
    monkeypatch.setattr(dts_module.dynamic_tenant_service, "get_tenant_meta", lambda tid: overrides)

    # Capture params passed to is_business_hours
    captured = {}

    def _stub_is_business_hours(*, current_time=None, start_hour=None, end_hour=None, timezone=None):
        captured["start_hour"] = start_hour
        captured["end_hour"] = end_hour
        captured["timezone"] = timezone
        return False  # force after-hours path

    # Patch utils functions
    monkeypatch.setattr("app.services.orchestrator.is_business_hours", _stub_is_business_hours)
    monkeypatch.setattr(
    "app.services.orchestrator.get_next_business_open_time",
        lambda *args, **kwargs: kwargs.get("start_hour") or overrides["business_hours_start"],
    )
    monkeypatch.setattr(
    "app.services.orchestrator.format_business_hours",
        lambda *args, **kwargs: f"{overrides['business_hours_start']}:00 - {overrides['business_hours_end']}:00",
    )

    # Build message with tenant
    msg = UnifiedMessage(
        message_id="m1",
        canal="whatsapp",
        user_id="u1",
        timestamp_iso="2025-01-01T00:00:00Z",
        tipo="text",
        texto="consulta",
        metadata={},
        tenant_id="tenantA",
    )

    # Act: call just the business-hours gate method through a minimal flow
    result = await orch._handle_business_hours({"intent": "unknown"}, {}, msg)

    # Assert: overrides were forwarded to util
    assert captured.get("start_hour") == overrides["business_hours_start"]
    assert captured.get("end_hour") == overrides["business_hours_end"]
    assert captured.get("timezone") == overrides["business_hours_timezone"]
    assert result is not None
