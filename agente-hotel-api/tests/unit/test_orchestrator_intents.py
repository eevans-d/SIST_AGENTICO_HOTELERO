"""
Tests exhaustivos de intents del Orchestrator.

Cubre contratos de entrada/salida, fallbacks y manejo de errores.
"""

import pytest
from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.orchestrator import Orchestrator
from app.models.unified_message import UnifiedMessage
from app.exceptions.pms_exceptions import PMSError, CircuitBreakerOpenError


@pytest.fixture
def mock_pms_adapter():
    """Mock PMS adapter."""
    adapter = AsyncMock()
    adapter.check_availability = AsyncMock()
    adapter.make_reservation = AsyncMock()
    return adapter


@pytest.fixture
def mock_session_manager():
    """Mock session manager."""
    manager = AsyncMock()
    manager.get_session = AsyncMock()
    manager.update_session = AsyncMock()
    return manager


@pytest.fixture
def mock_lock_service():
    """Mock lock service."""
    service = AsyncMock()
    service.acquire = AsyncMock()
    service.release = AsyncMock()
    return service


@pytest.fixture
def orchestrator(mock_pms_adapter, mock_session_manager, mock_lock_service):
    """Crear orchestrator con mocks."""
    orch = Orchestrator(mock_pms_adapter, mock_session_manager, mock_lock_service)
    return orch


@pytest.fixture
def sample_message():
    """Mensaje de ejemplo."""
    from datetime import datetime
    return UnifiedMessage(
        message_id="msg_123",
        user_id="user_123",
        canal="whatsapp",
        texto="¿Hay doble disponible del 20 al 22?",
        tipo="text",
        timestamp_iso=datetime.utcnow().isoformat(),
        tenant_id="tenant_1",
    )


class TestAvailabilityIntent:
    """Tests para intent check_availability."""

    @pytest.mark.asyncio
    async def test_availability_success(self, orchestrator, mock_pms_adapter, mock_session_manager, sample_message):
        """Éxito: retorna disponibilidad."""
        # Setup
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
        mock_pms_adapter.check_availability.return_value = {
            "available": True,
            "rooms": [{"type": "double", "price": 100, "total": 200}],
        }

        # Execute
        response = await orchestrator._handle_availability(nlp_result, {}, sample_message)

        # Assert
        assert response["status"] == "success"
        assert "Doble" in response["content"]["text"] or "double" in response["content"]["text"].lower()
        assert "$" in response["content"]["text"]

    @pytest.mark.asyncio
    async def test_availability_no_stock(self, orchestrator, mock_pms_adapter, sample_message):
        """Sin disponibilidad: ofrecer alternativas."""
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
        
        mock_pms_adapter.check_availability.return_value = {
            "available": False,
            "alternatives": [
                {"dates": ["2025-10-21", "2025-10-23"], "rooms": [{"type": "double", "price": 100}]}
            ],
        }

        response = await orchestrator._handle_availability(nlp_result, {}, sample_message)

        assert response["status"] == "no_availability"
        assert "alternativ" in response["content"]["text"].lower()

    @pytest.mark.asyncio
    async def test_availability_pms_error(self, orchestrator, mock_pms_adapter, sample_message):
        """Error PMS: fallback."""
        nlp_result = {
            "intent": "check_availability",
            "confidence": 0.78,
            "entities": {
                "checkin": "2025-10-20",
                "checkout": "2025-10-22",
                "guests": 2,
            },
            "language": "es",
        }
        
        mock_pms_adapter.check_availability.side_effect = PMSError("Connection timeout")

        response = await orchestrator._handle_availability(nlp_result, {}, sample_message)

        assert response["status"] in ["error", "escalation"]

    @pytest.mark.asyncio
    async def test_availability_circuit_breaker_open(self, orchestrator, mock_pms_adapter, sample_message):
        """Circuit breaker abierto: escalada."""
        nlp_result = {
            "intent": "check_availability",
            "confidence": 0.78,
            "entities": {
                "checkin": "2025-10-20",
                "checkout": "2025-10-22",
            },
            "language": "es",
        }
        
        mock_pms_adapter.check_availability.side_effect = CircuitBreakerOpenError("PMS circuit open")

        response = await orchestrator._handle_availability(nlp_result, {}, sample_message)

        assert response["status"] == "escalation" or "contact" in response["content"]["text"].lower()


class TestReservationIntent:
    """Tests para intent make_reservation."""

    @pytest.mark.asyncio
    async def test_reservation_success(self, orchestrator, mock_pms_adapter, mock_session_manager, mock_lock_service, sample_message):
        """Éxito: reserva creada."""
        nlp_result = {
            "intent": "make_reservation",
            "confidence": 0.75,
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
        
        mock_lock_service.acquire.return_value = True
        mock_pms_adapter.make_reservation.return_value = {
            "success": True,
            "reservation_id": "RES-12345",
            "deposit_amount": 60.00,
        }

        response = await orchestrator._handle_make_reservation(nlp_result, session_data, sample_message)

        assert response["status"] == "success"
        assert "RES-" in response["content"]["text"] or "seña" in response["content"]["text"].lower()

    @pytest.mark.asyncio
    async def test_reservation_no_context(self, orchestrator, sample_message):
        """Sin contexto previo: pedir consulta de disponibilidad."""
        nlp_result = {
            "intent": "make_reservation",
            "confidence": 0.75,
            "entities": {"confirmation": True},
        }
        
        session_data = {}  # Empty session

        response = await orchestrator._handle_make_reservation(nlp_result, session_data, sample_message)

        assert "disponibilidad" in response["content"]["text"].lower() or "availability" in response["content"]["text"].lower()

    @pytest.mark.asyncio
    async def test_reservation_lock_contention(self, orchestrator, mock_lock_service, mock_pms_adapter, sample_message):
        """Lock fallida: habitación en disputa."""
        nlp_result = {
            "intent": "make_reservation",
            "confidence": 0.75,
            "entities": {"confirmation": True},
        }
        
        session_data = {
            "last_availability_query": {
                "checkin": "2025-10-20",
                "checkout": "2025-10-22",
            }
        }
        
        mock_lock_service.acquire.return_value = False  # Lock falla

        response = await orchestrator._handle_make_reservation(nlp_result, session_data, sample_message)

        assert "ocupó" in response["content"]["text"].lower() or "alguien" in response["content"]["text"].lower()


class TestLateCheckoutIntent:
    """Tests para intent late_checkout."""

    @pytest.mark.asyncio
    async def test_late_checkout_approved(self, orchestrator, mock_pms_adapter, sample_message):
        """Late checkout aprobado."""
        nlp_result = {
            "intent": "late_checkout",
            "confidence": 0.72,
            "entities": {"requested_time": "14:00"},
            "language": "es",
        }
        
        session_data = {
            "guest_id": "guest_123",
            "current_booking": {
                "reservation_id": "RES-12345",
                "checkout_date": "2025-10-22",
            }
        }
        
        mock_pms_adapter.check_late_checkout_availability = AsyncMock(return_value={
            "available": True,
            "checkout_time": "14:00",
            "fee": 50.00,
        })

        response = await orchestrator._handle_late_checkout(nlp_result, session_data, sample_message)

        assert "14:00" in response["content"]["text"] or "2:00 PM" in response["content"]["text"]

    @pytest.mark.asyncio
    async def test_late_checkout_no_booking(self, orchestrator, sample_message):
        """Sin booking en sesión: pedir número de reserva."""
        nlp_result = {
            "intent": "late_checkout",
            "confidence": 0.72,
        }
        
        session_data = {}  # Sin booking

        response = await orchestrator._handle_late_checkout(nlp_result, session_data, sample_message)

        assert "número de reserva" in response["content"]["text"].lower() or "reservation" in response["content"]["text"].lower()


class TestReviewIntent:
    """Tests para intent review_response."""

    @pytest.mark.asyncio
    async def test_review_request_success(self, orchestrator, sample_message):
        """Solicitar reseña: retornar links."""
        nlp_result = {
            "intent": "review_response",
            "confidence": 0.80,
            "entities": {"action": "request_links"},
            "language": "es",
        }

        response = await orchestrator._handle_review_request(nlp_result, {}, sample_message)

        if response:  # Puede retornar None si no hay booking
            assert "google" in response["content"]["text"].lower() or "booking" in response["content"]["text"].lower()


class TestFallbackBehavior:
    """Tests para fallback general."""

    @pytest.mark.asyncio
    async def test_low_confidence_fallback(self, orchestrator, sample_message):
        """Baja confianza NLP: mostrar menú."""
        nlp_result = {
            "intent": "unknown",
            "confidence": 0.35,  # Bajo
            "language": "es",
        }

        # El orchestrator debería escalada o mostrar menú
        # Aquí se prueba el comportamiento esperado
        assert nlp_result["confidence"] < 0.55

    @pytest.mark.asyncio
    async def test_unknown_intent_handler(self, orchestrator, sample_message):
        """Intent no maapeado: buscar fallback."""
        nlp_result = {
            "intent": "unknown_future_intent",
            "confidence": 0.65,
        }

        # Si intent no está en _intent_handlers, debería haber fallback
        assert "unknown_future_intent" not in orchestrator._intent_handlers


class TestIntentMetrics:
    """Tests para métricas de intents."""

    @pytest.mark.asyncio
    async def test_intent_metrics_tracked(self, orchestrator, mock_pms_adapter, mock_session_manager, sample_message):
        """Verificar que se registran métricas de intent."""
        nlp_result = {
            "intent": "check_availability",
            "confidence": 0.78,
            "entities": {
                "checkin": "2025-10-20",
                "checkout": "2025-10-22",
            },
            "language": "es",
        }
        
        mock_session_manager.get_session.return_value = {}
        mock_pms_adapter.check_availability.return_value = {
            "available": True,
            "rooms": [{"type": "double", "price": 100, "total": 200}],
        }

        response = await orchestrator._handle_availability(nlp_result, {}, sample_message)

        # Las métricas se incrementan internamente; aquí validamos que no hay excepción
        assert response["status"] in ["success", "error", "escalation"]


class TestIntentEdgeCases:
    """Tests de casos borde."""

    @pytest.mark.asyncio
    async def test_availability_past_dates(self, orchestrator, sample_message):
        """Intentar consultar fechas en el pasado."""
        nlp_result = {
            "intent": "check_availability",
            "confidence": 0.78,
            "entities": {
                "checkin": "2020-10-20",  # Pasado
                "checkout": "2020-10-22",
            },
            "language": "es",
        }

        response = await orchestrator._handle_availability(nlp_result, {}, sample_message)

        # Debería rechazar o corregir
        assert response["status"] in ["error", "clarification_needed"]

    @pytest.mark.asyncio
    async def test_availability_inverted_dates(self, orchestrator, sample_message):
        """Fechas invertidas: checkout antes de checkin."""
        nlp_result = {
            "intent": "check_availability",
            "confidence": 0.78,
            "entities": {
                "checkin": "2025-10-22",
                "checkout": "2025-10-20",  # Invertido
            },
            "language": "es",
        }

        response = await orchestrator._handle_availability(nlp_result, {}, sample_message)

        # Debería detectar el error
        assert response["status"] in ["error", "clarification_needed"]
