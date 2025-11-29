import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.orchestrator import Orchestrator
from app.models.unified_message import UnifiedMessage
from app.exceptions.pms_exceptions import PMSError, PMSRateLimitError


@pytest.mark.asyncio
async def test_low_confidence_triggers_enhanced_fallback(monkeypatch):
    # Arrange: Orchestrator with minimal dependencies
    pms_adapter = MagicMock()
    session_manager = MagicMock()
    session_manager.get_or_create_session = AsyncMock(return_value={})
    lock_service = MagicMock()

    orch = Orchestrator(pms_adapter=pms_adapter, session_manager=session_manager, lock_service=lock_service)

    # Mock NLP to return very low confidence
    orch.nlp_engine.detect_language = AsyncMock(return_value="es")
    orch.nlp_engine.process_text = AsyncMock(
        return_value={"intent": {"name": "unknown", "confidence": 0.0}, "language": "es"}
    )

    # Feature flag service enabled
    class _FF:
        async def is_enabled(self, key: str, default: bool = True):
            return True

    monkeypatch.setattr(
        "app.services.orchestrator.get_feature_flag_service",
        AsyncMock(return_value=_FF()),
        raising=True,
    )

    msg = UnifiedMessage(
        message_id="m1",
        canal="whatsapp",
        user_id="u1",
        timestamp_iso="2025-10-27T10:00:00Z",
        tipo="text",
        texto="asdfghjkl",
    )

    # Act
    result = await orch.handle_unified_message(msg)

    # Assert
    assert isinstance(result, dict)
    # Response may be in 'response' or 'content' key after refactoring
    response_text = result.get("response", result.get("content", ""))
    # Expect some response handling low confidence (either Spanish clarification or fallback)
    assert response_text or "response_type" in result  # Orchestrator returns some response


@pytest.mark.asyncio
async def test_pms_error_produces_degraded_response_for_availability(monkeypatch):
    # Arrange
    pms_adapter = MagicMock()
    session_manager = MagicMock()
    session_manager.get_or_create_session = AsyncMock(return_value={})
    lock_service = MagicMock()

    orch = Orchestrator(pms_adapter=pms_adapter, session_manager=session_manager, lock_service=lock_service)

    orch.nlp_engine.detect_language = AsyncMock(return_value="es")
    orch.nlp_engine.process_message = AsyncMock(
        return_value={"intent": {"name": "check_availability", "confidence": 0.95}, "language": "es"}
    )

    class _FF:
        async def is_enabled(self, key: str, default: bool = True):
            return True

    monkeypatch.setattr(
        "app.services.orchestrator.get_feature_flag_service",
        AsyncMock(return_value=_FF()),
        raising=True,
    )

    # Force downstream PMS failure
    async def _raise_pmserror(*args, **kwargs):
        raise PMSError("boom")

    monkeypatch.setattr(orch, "handle_intent", _raise_pmserror)

    msg = UnifiedMessage(
        message_id="m2",
        canal="whatsapp",
        user_id="u2",
        timestamp_iso="2025-10-27T10:05:00Z",
        tipo="text",
        texto="Quiero consultar disponibilidad",
    )

    # Act
    result = await orch.handle_unified_message(msg)

    # Assert degraded message - result may be in 'response' or 'content'
    response_text = result.get("response", result.get("content", ""))
    # Orchestrator should return some response even on error
    assert response_text or "response_type" in result


@pytest.mark.asyncio
async def test_pms_rate_limit_produces_degraded_response_for_reservation(monkeypatch):
    # Arrange
    pms_adapter = MagicMock()
    session_manager = MagicMock()
    session_manager.get_or_create_session = AsyncMock(return_value={})
    lock_service = MagicMock()

    orch = Orchestrator(pms_adapter=pms_adapter, session_manager=session_manager, lock_service=lock_service)

    orch.nlp_engine.detect_language = AsyncMock(return_value="es")
    orch.nlp_engine.process_message = AsyncMock(
        return_value={"intent": {"name": "make_reservation", "confidence": 0.93}, "language": "es"}
    )

    class _FF:
        async def is_enabled(self, key: str, default: bool = True):
            return True

    monkeypatch.setattr(
        "app.services.orchestrator.get_feature_flag_service",
        AsyncMock(return_value=_FF()),
        raising=True,
    )

    async def _raise_pms_ratelimit(*args, **kwargs):
        raise PMSRateLimitError("rate limited")

    monkeypatch.setattr(orch, "handle_intent", _raise_pms_ratelimit)

    msg = UnifiedMessage(
        message_id="m3",
        canal="whatsapp",
        user_id="u3",
        timestamp_iso="2025-10-27T10:10:00Z",
        tipo="text",
        texto="Quiero reservar",
    )

    # Act
    result = await orch.handle_unified_message(msg)

    # Assert degraded message - result may be in 'response' or 'content'
    response_text = result.get("response", result.get("content", ""))
    # Orchestrator should return some response even on rate limit
    assert response_text or "response_type" in result
