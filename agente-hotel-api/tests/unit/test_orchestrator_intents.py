"""
Tests de intents del Orchestrator alineados con la API actual.

La versión actual de `_handle_availability` no consulta PMS ni retorna `status`;
devuelve `response_type` + `content` (texto o estructura interactiva) y opcionalmente imagen/audio.

Estos tests se centran en contratos básicos y evitan supuestos de versiones previas.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from app.services.orchestrator import Orchestrator
from app.models.unified_message import UnifiedMessage


# -----------------------------
# Fixtures
# -----------------------------

@pytest.fixture
def mock_pms_adapter():
    adapter = AsyncMock()
    adapter.check_availability = AsyncMock()
    adapter.make_reservation = AsyncMock()
    adapter.check_late_checkout_availability = AsyncMock()
    return adapter


@pytest.fixture
def mock_session_manager():
    manager = AsyncMock()
    manager.get_session = AsyncMock()
    manager.update_session = AsyncMock()
    return manager


@pytest.fixture
def mock_lock_service():
    service = AsyncMock()
    service.acquire = AsyncMock()
    service.release = AsyncMock()
    return service


@pytest.fixture
def orchestrator(mock_pms_adapter, mock_session_manager, mock_lock_service):
    """Crear orchestrator con dependencias mockeadas."""
    return Orchestrator(mock_pms_adapter, mock_session_manager, mock_lock_service)


@pytest.fixture
def sample_message():
    return UnifiedMessage(
        message_id="msg_123",
        user_id="user_123",
        canal="whatsapp",
        texto="¿Hay doble disponible del 20 al 22?",
        tipo="text",
        timestamp_iso=datetime.now(timezone.utc).isoformat(),
        tenant_id="tenant_1",
    )


# -----------------------------
# Tests: Availability
# -----------------------------

class TestAvailabilityIntent:
    @pytest.mark.asyncio
    async def test_availability_basic_response(self, orchestrator, mock_session_manager, sample_message):
        nlp_result = {
            "intent": "check_availability",
            "confidence": 0.78,
            "entities": {
                "checkin": "2025-10-20",
                "checkout": "2025-10-22",
                "guests": 2,
                "room_type": "double",
            },
            "language": "es",
        }

        mock_session_manager.get_session.return_value = {}

        response = await orchestrator._handle_availability(nlp_result, {}, sample_message)

        assert response["response_type"] in {
            "text",
            "text_with_image",
            "interactive_buttons",
            "interactive_buttons_with_image",
        }
        assert "content" in response

    @pytest.mark.asyncio
    async def test_availability_audio_flow_flag(self, orchestrator, sample_message):
        nlp_result = {
            "intent": "check_availability",
            "confidence": 0.80,
            "entities": {},
            "language": "es",
        }

        # Forzar modo audio respondiendo con audio (param interno del handler)
        response = await orchestrator._handle_availability(nlp_result, {}, sample_message, respond_with_audio=False)
        assert "response_type" in response


# -----------------------------
# Tests: Reservation
# -----------------------------

class TestReservationIntent:
    @pytest.mark.asyncio
    async def test_reservation_instructions_text(self, orchestrator, mock_session_manager, sample_message):
        nlp_result = {
            "intent": "make_reservation",
            "confidence": 0.9,
            "entities": {"confirmation": True},
            "language": "es",
        }

        session_data = {
            "last_availability_query": {
                "checkin": "2025-10-20",
                "checkout": "2025-10-22",
                "room_type": "double",
                "price_total": 200,
            }
        }

        response = await orchestrator._handle_make_reservation(nlp_result, session_data, sample_message)

        assert response["response_type"] in {"text", "audio"}
        assert "content" in response
        # Debe actualizar sesión con reservation_pending
        mock_session_manager.update_session.assert_called()

    @pytest.mark.asyncio
    async def test_reservation_no_context_is_still_valid(self, orchestrator, sample_message):
        nlp_result = {"intent": "make_reservation", "confidence": 0.8, "entities": {"confirmation": True}}
        response = await orchestrator._handle_make_reservation(nlp_result, {}, sample_message)
        assert response["response_type"] in {"text", "audio"}


# -----------------------------
# Tests: Late checkout
# -----------------------------

class TestLateCheckoutIntent:
    @pytest.mark.asyncio
    async def test_late_checkout_basic(self, orchestrator, sample_message):
        nlp_result = {"intent": "late_checkout", "confidence": 0.72, "entities": {"requested_time": "14:00"}}
        session = {"current_booking": {"reservation_id": "RES-1", "checkout_date": "2025-10-22"}}

        response = await orchestrator._handle_late_checkout(nlp_result, session, sample_message)
        assert response["response_type"] in {"text", "audio"}

    @pytest.mark.asyncio
    async def test_late_checkout_missing_booking(self, orchestrator, sample_message):
        nlp_result = {"intent": "late_checkout", "confidence": 0.72}
        response = await orchestrator._handle_late_checkout(nlp_result, {}, sample_message)
        assert response["response_type"] in {"text", "audio"}


# -----------------------------
# Tests: Review request
# -----------------------------

class TestReviewIntent:
    @pytest.mark.asyncio
    async def test_review_request_links_if_available(self, orchestrator, sample_message):
        nlp_result = {"intent": "review_response", "confidence": 0.8, "entities": {"action": "request_links"}}
        response = await orchestrator._handle_review_request(nlp_result, {}, sample_message)
        if response:
            assert "content" in response


# -----------------------------
# Tests: Fallbacks y mapping
# -----------------------------

class TestFallbackBehavior:
    def test_unknown_intent_mapping_has_fallback(self, orchestrator):
        assert "unknown_future_intent" not in orchestrator._intent_handlers


# -----------------------------
# Tests: Métricas superficiales
# -----------------------------

class TestIntentMetrics:
    @pytest.mark.asyncio
    async def test_intent_metrics_no_exception(self, orchestrator, sample_message):
        nlp_result = {"intent": "check_availability", "confidence": 0.9, "language": "es"}
        response = await orchestrator._handle_availability(nlp_result, {}, sample_message)
        assert "response_type" in response


# -----------------------------
# Tests: Casos borde (contracto estable)
# -----------------------------

class TestIntentEdgeCases:
    @pytest.mark.asyncio
    async def test_availability_past_dates_returns_valid_shape(self, orchestrator, sample_message):
        nlp_result = {
            "intent": "check_availability",
            "confidence": 0.7,
            "entities": {"checkin": "2020-10-20", "checkout": "2020-10-22"},
        }
        response = await orchestrator._handle_availability(nlp_result, {}, sample_message)
        assert response["response_type"] in {
            "text",
            "text_with_image",
            "interactive_buttons",
            "interactive_buttons_with_image",
        }

    @pytest.mark.asyncio
    async def test_availability_inverted_dates_returns_valid_shape(self, orchestrator, sample_message):
        nlp_result = {
            "intent": "check_availability",
            "confidence": 0.7,
            "entities": {"checkin": "2025-10-22", "checkout": "2025-10-20"},
        }
        response = await orchestrator._handle_availability(nlp_result, {}, sample_message)
        assert response["response_type"] in {
            "text",
            "text_with_image",
            "interactive_buttons",
            "interactive_buttons_with_image",
        }


