import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

from app.services.orchestrator import Orchestrator
import app.services.orchestrator as orchestrator_module
from app.models.unified_message import UnifiedMessage


@pytest_asyncio.fixture
async def orch(monkeypatch):
    pms_adapter = AsyncMock()
    session_manager = AsyncMock()
    lock_service = AsyncMock()

    # Evitar checks de horario comercial
    monkeypatch.setattr("app.services.orchestrator.Orchestrator._handle_business_hours", AsyncMock(return_value=None))

    # Forzar feature flag de interactivos a True
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
async def test_info_intent_returns_interactive_buttons_en(orch):
    msg = UnifiedMessage(
        message_id="m10",
        canal="whatsapp",
        user_id="u10",
        timestamp_iso="2025-01-01T00:00:00Z",
        tipo="text",
        texto="amenities info",
        metadata={"detected_language": "en"},
        tenant_id="tenantZ",
    )

    nlp_result = {"intent": {"name": "hotel_amenities", "confidence": 0.9}, "language": "en"}
    session = {}

    # Asegurar que el parche del FF está activo
    ff = await orchestrator_module.get_feature_flag_service()
    assert await ff.is_enabled("features.interactive_messages") is True

    # Comprobar acceso al template interactivo directamente
    orch.template_service.set_language("en")
    direct_buttons = orch.template_service.get_interactive_buttons("info_menu")
    assert direct_buttons, "Template interactivo 'info_menu' debe existir"

    resp = await orch._handle_info_intent(nlp_result, session, msg)

    assert resp["response_type"] == "interactive_buttons"
    content = resp["content"]
    assert isinstance(content, dict)
    assert "action_buttons" in content and isinstance(content["action_buttons"], list)
    # Debe incluir el botón de amenities
    ids = [b.get("id") for b in content["action_buttons"]]
    assert "hotel_amenities" in ids


@pytest.mark.asyncio
async def test_info_intent_returns_interactive_buttons_es(orch):
    msg = UnifiedMessage(
        message_id="m11",
        canal="whatsapp",
        user_id="u11",
        timestamp_iso="2025-01-01T00:00:00Z",
        tipo="text",
        texto="información de check-in",
        metadata={"detected_language": "es"},
        tenant_id="tenantY",
    )

    nlp_result = {"intent": {"name": "check_in_info", "confidence": 0.9}, "language": "es"}
    session = {}

    # Asegurar que el parche del FF está activo
    ff = await orchestrator_module.get_feature_flag_service()
    assert await ff.is_enabled("features.interactive_messages") is True

    orch.template_service.set_language("es")
    direct_buttons = orch.template_service.get_interactive_buttons("info_menu")
    assert direct_buttons, "Template interactivo 'info_menu' debe existir"

    resp = await orch._handle_info_intent(nlp_result, session, msg)

    assert resp["response_type"] == "interactive_buttons"
    content = resp["content"]
    assert isinstance(content, dict)
    assert "action_buttons" in content and isinstance(content["action_buttons"], list)
    # Debe incluir el botón de check-in
    ids = [b.get("id") for b in content["action_buttons"]]
    assert "check_in_info" in ids
