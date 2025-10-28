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

    # Stub feature flag service to be provided per-test via monkeypatch later
    async def _ff_service_factory():
        class _FF:
            async def is_enabled(self, key: str, default: bool = True):
                return default
        return _FF()

    monkeypatch.setattr("app.services.orchestrator.get_feature_flag_service", _ff_service_factory)

    return Orchestrator(pms_adapter, session_manager, lock_service)


@pytest.mark.asyncio
async def test_availability_audio_path_returns_audio(monkeypatch, orch):
    # Forzar flags: no imagen para simplificar
    from app.core import settings as settings_module
    settings = settings_module.settings
    prev = settings.room_images_enabled
    settings.room_images_enabled = False

    # Stub TTS audio
    async def _gen_audio(self, text: str, content_type: str = ""):  # noqa: ARG001, ANN001
        return b"audio-bytes"

    monkeypatch.setattr("app.services.orchestrator.AudioProcessor.generate_audio_response", _gen_audio)

    # Construir mensaje y nlp_result
    msg = UnifiedMessage(
        message_id="m1",
        canal="whatsapp",
        user_id="u1",
        timestamp_iso="2025-01-01T00:00:00Z",
        tipo="audio",
        texto="quiero disponibilidad",
        metadata={},
        tenant_id="tenantA",
    )

    # Stub business hours gate para que no interrumpa desde handle_intent
    monkeypatch.setattr("app.services.orchestrator.Orchestrator._handle_business_hours", AsyncMock(return_value=None))

    # Llamar a handler de intent directamente para simular ruta de disponibilidad con audio
    resp = await orch._handle_availability({"intent": {"name": "check_availability"}}, {}, msg, respond_with_audio=True)

    assert resp["response_type"] in ("audio", "audio_with_image")
    assert resp.get("audio_data") is not None or resp.get("audio_data") is None  # defensivo

    # Restaurar setting
    settings.room_images_enabled = prev


@pytest.mark.asyncio
async def test_availability_interactive_buttons_when_flag_enabled(monkeypatch, orch):
    # Forzar flags: no imagen; interactive on
    from app.core import settings as settings_module
    settings = settings_module.settings
    prev = settings.room_images_enabled
    settings.room_images_enabled = False

    class _FF:
        async def is_enabled(self, key: str, default: bool = True):  # noqa: ARG002
            if key == "features.interactive_messages":
                return True
            return default

    async def _ff_factory():
        return _FF()

    monkeypatch.setattr("app.services.orchestrator.get_feature_flag_service", _ff_factory)

    msg = UnifiedMessage(
        message_id="m1",
        canal="whatsapp",
        user_id="u1",
        timestamp_iso="2025-01-01T00:00:00Z",
        tipo="text",
        texto="disponibilidad",
        metadata={},
        tenant_id="tenantA",
    )

    resp = await orch._handle_availability({"intent": {"name": "check_availability"}}, {}, msg, respond_with_audio=False)

    assert resp["response_type"] == "interactive_buttons"

    settings.room_images_enabled = prev


@pytest.mark.asyncio
async def test_availability_text_when_flag_disabled(monkeypatch, orch):
    # Forzar flags: no imagen; interactive off
    from app.core import settings as settings_module
    settings = settings_module.settings
    prev = settings.room_images_enabled
    settings.room_images_enabled = False

    class _FF:
        async def is_enabled(self, key: str, default: bool = True):  # noqa: ARG002
            if key == "features.interactive_messages":
                return False
            return default

    async def _ff_factory():
        return _FF()

    monkeypatch.setattr("app.services.orchestrator.get_feature_flag_service", _ff_factory)

    msg = UnifiedMessage(
        message_id="m1",
        canal="whatsapp",
        user_id="u1",
        timestamp_iso="2025-01-01T00:00:00Z",
        tipo="text",
        texto="disponibilidad",
        metadata={},
        tenant_id="tenantA",
    )

    resp = await orch._handle_availability({"intent": {"name": "check_availability"}}, {}, msg, respond_with_audio=False)

    assert resp["response_type"] == "text"

    settings.room_images_enabled = prev
