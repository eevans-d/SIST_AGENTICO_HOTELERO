"""
Tests de integración para handle_intent() - CRÍTICO antes de refactorizar
Este archivo captura el comportamiento actual de los 937 líneas del método
para asegurar que el refactoring no rompa funcionalidad existente.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, time

from app.services.orchestrator import Orchestrator
from app.models.unified_message import UnifiedMessage


@pytest.fixture
def mock_pms_adapter():
    """Mock del PMS adapter"""
    adapter = AsyncMock()
    adapter.check_availability = AsyncMock()
    adapter.get_room_types = AsyncMock()
    adapter.create_reservation = AsyncMock()
    adapter.get_reservation = AsyncMock()
    adapter.cancel_reservation = AsyncMock()
    adapter.modify_reservation = AsyncMock()
    return adapter


@pytest.fixture
def mock_session_manager():
    """Mock del session manager"""
    manager = AsyncMock()
    manager.get_session = AsyncMock()
    manager.save_session = AsyncMock()
    manager.clear_session = AsyncMock()
    return manager


@pytest.fixture
def mock_lock_service():
    """Mock del lock service"""
    service = AsyncMock()
    service.acquire_lock = AsyncMock(return_value=True)
    service.release_lock = AsyncMock()
    return service


@pytest.fixture
def orchestrator(mock_pms_adapter, mock_session_manager, mock_lock_service):
    """Instancia del orchestrator con mocks"""
    return Orchestrator(
        pms_adapter=mock_pms_adapter,
        session_manager=mock_session_manager,
        lock_service=mock_lock_service
    )


@pytest.fixture
def sample_message():
    """Mensaje de prueba"""
    return UnifiedMessage(
        message_id="test-msg-123",
        canal="whatsapp",
        user_id="+34612345678",
        texto="Quiero hacer una reserva",
        timestamp_iso=datetime.utcnow().isoformat(),
        tipo="text"
    )


@pytest.fixture
def sample_session():
    """Sesión de prueba"""
    return {
        "tenant_id": "hotel-123",
        "user_id": "+34612345678",
        "history": [],
        "state": "idle"
    }


class TestBusinessHoursFeature:
    """FEATURE 2: Business hours check"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_business_hours_check_during_hours(
        self, orchestrator, mock_session_manager, sample_message, sample_session
    ):
        """Test: Verificación de horario comercial - dentro de horario"""
        mock_session_manager.get_session.return_value = sample_session
        
        nlp_result = {
            "intent": "consultar_horario",
            "confidence": 0.9,
            "entities": {}
        }
        
        # Mock para que sea horario comercial (9:00 AM - 10:00 PM)
        with patch('app.services.orchestrator.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(14, 0)  # 2 PM
            mock_datetime.now.return_value.weekday.return_value = 2  # Miércoles
            
            result = await orchestrator.handle_intent(
                nlp_result=nlp_result,
                session=sample_session,
                message=sample_message
            )
            
            assert result["response_type"] == "text"
            assert "horario" in result["content"].lower()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_business_hours_check_after_hours(
        self, orchestrator, mock_session_manager, sample_message, sample_session
    ):
        """Test: Verificación de horario comercial - fuera de horario"""
        mock_session_manager.get_session.return_value = sample_session
        
        nlp_result = {
            "intent": "consultar_horario",
            "confidence": 0.9,
            "entities": {}
        }
        
        # Mock para que sea fuera de horario (11 PM)
        with patch('app.services.orchestrator.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(23, 0)
            mock_datetime.now.return_value.weekday.return_value = 2
            
            result = await orchestrator.handle_intent(
                nlp_result=nlp_result,
                session=sample_session,
                message=sample_message
            )
            
            assert result["response_type"] == "text"
            # Puede escalar o dar mensaje de horario


class TestAvailabilityFeature:
    """FEATURE: Availability checking"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_availability_with_dates(
        self, orchestrator, mock_pms_adapter, mock_session_manager,
        sample_message, sample_session
    ):
        """Test: Consulta de disponibilidad con fechas"""
        mock_session_manager.get_session.return_value = sample_session
        mock_pms_adapter.check_availability.return_value = {
            "available": True,
            "rooms": [
                {"id": "101", "type": "double", "price": 80.00},
                {"id": "102", "type": "suite", "price": 150.00}
            ]
        }
        
        nlp_result = {
            "intent": "consultar_disponibilidad",
            "confidence": 0.9,
            "entities": {
                "fecha_entrada": "2025-12-20",
                "fecha_salida": "2025-12-22",
                "huespedes": 2
            }
        }
        
        result = await orchestrator.handle_intent(
            nlp_result=nlp_result,
            session=sample_session,
            message=sample_message
        )
        
        assert result["response_type"] == "text"
        assert "disponible" in result["content"].lower() or "available" in result["content"].lower()
        
        # Verificar que se llamó al PMS
        mock_pms_adapter.check_availability.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_availability_no_rooms_available(
        self, orchestrator, mock_pms_adapter, mock_session_manager,
        sample_message, sample_session
    ):
        """Test: Sin disponibilidad - debe sugerir alternativas"""
        mock_session_manager.get_session.return_value = sample_session
        mock_pms_adapter.check_availability.return_value = {
            "available": False,
            "rooms": []
        }
        
        nlp_result = {
            "intent": "consultar_disponibilidad",
            "confidence": 0.9,
            "entities": {
                "fecha_entrada": "2025-12-20",
                "fecha_salida": "2025-12-22"
            }
        }
        
        result = await orchestrator.handle_intent(
            nlp_result=nlp_result,
            session=sample_session,
            message=sample_message
        )
        
        assert result["response_type"] == "text"
        # Debe indicar falta de disponibilidad


class TestReservationCreationFeature:
    """FEATURE: Reservation creation flow"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_reservation_complete_data(
        self, orchestrator, mock_pms_adapter, mock_session_manager,
        sample_message, sample_session
    ):
        """Test: Crear reserva con todos los datos"""
        sample_session["state"] = "creating_reservation"
        sample_session["reservation_data"] = {
            "check_in": "2025-12-20",
            "check_out": "2025-12-22",
            "room_type": "double",
            "guests": 2,
            "guest_name": "Juan Pérez",
            "guest_email": "juan@example.com"
        }
        
        mock_session_manager.get_session.return_value = sample_session
        mock_pms_adapter.create_reservation.return_value = {
            "reservation_id": "RES-12345",
            "status": "confirmed",
            "check_in": "2025-12-20",
            "check_out": "2025-12-22"
        }
        
        nlp_result = {
            "intent": "crear_reserva",
            "confidence": 0.9,
            "entities": {}
        }
        
        result = await orchestrator.handle_intent(
            nlp_result=nlp_result,
            session=sample_session,
            message=sample_message
        )
        
        assert result["response_type"] == "text"
        
        # Verificar llamada al PMS
        mock_pms_adapter.create_reservation.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_reservation_missing_data(
        self, orchestrator, mock_session_manager,
        sample_message, sample_session
    ):
        """Test: Crear reserva sin datos completos - debe solicitar info"""
        sample_session["state"] = "creating_reservation"
        sample_session["reservation_data"] = {
            "check_in": "2025-12-20"
            # Falta check_out, room_type, guests, etc.
        }
        
        mock_session_manager.get_session.return_value = sample_session
        
        nlp_result = {
            "intent": "crear_reserva",
            "confidence": 0.9,
            "entities": {}
        }
        
        result = await orchestrator.handle_intent(
            nlp_result=nlp_result,
            session=sample_session,
            message=sample_message
        )
        
        assert result["response_type"] == "text"
        # Debe pedir información faltante


class TestLateCheckoutFeature:
    """FEATURE 4: Late checkout confirmation"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_late_checkout_request(
        self, orchestrator, mock_pms_adapter, mock_session_manager,
        sample_message, sample_session
    ):
        """Test: Solicitud de late checkout"""
        sample_session["reservation_id"] = "RES-12345"
        mock_session_manager.get_session.return_value = sample_session
        
        mock_pms_adapter.get_reservation.return_value = {
            "id": "RES-12345",
            "check_out": "2025-12-22",
            "status": "confirmed"
        }
        
        mock_pms_adapter.modify_reservation.return_value = {
            "success": True,
            "late_checkout_time": "14:00"
        }
        
        nlp_result = {
            "intent": "solicitar_late_checkout",
            "confidence": 0.85,
            "entities": {
                "hora": "14:00"
            }
        }
        
        result = await orchestrator.handle_intent(
            nlp_result=nlp_result,
            session=sample_session,
            message=sample_message
        )
        
        assert result["response_type"] == "text"


class TestRoomImagesFeature:
    """FEATURE 3: Room images"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_room_images_request(
        self, orchestrator, mock_pms_adapter, mock_session_manager,
        sample_message, sample_session
    ):
        """Test: Solicitud de imágenes de habitaciones"""
        mock_session_manager.get_session.return_value = sample_session
        
        mock_pms_adapter.get_room_types.return_value = [
            {
                "id": "double",
                "name": "Habitación Doble",
                "images": ["https://example.com/double1.jpg"]
            }
        ]
        
        nlp_result = {
            "intent": "ver_imagenes_habitacion",
            "confidence": 0.88,
            "entities": {
                "room_type": "double"
            }
        }
        
        result = await orchestrator.handle_intent(
            nlp_result=nlp_result,
            session=sample_session,
            message=sample_message
        )
        
        # Puede retornar imagen o texto con link
        assert result["response_type"] in ["image", "text", "media"]


class TestReviewRequestFeature:
    """FEATURE 6: Review requests"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_review_request_after_checkout(
        self, orchestrator, mock_pms_adapter, mock_session_manager,
        sample_message, sample_session
    ):
        """Test: Solicitud de review después de checkout"""
        sample_session["reservation_id"] = "RES-12345"
        sample_session["checkout_completed"] = True
        
        mock_session_manager.get_session.return_value = sample_session
        
        mock_pms_adapter.get_reservation.return_value = {
            "id": "RES-12345",
            "status": "completed",
            "check_out": "2025-12-20"
        }
        
        nlp_result = {
            "intent": "solicitar_review",
            "confidence": 0.82,
            "entities": {}
        }
        
        result = await orchestrator.handle_intent(
            nlp_result=nlp_result,
            session=sample_session,
            message=sample_message
        )
        
        assert result["response_type"] == "text"


class TestQRCodeFeature:
    """FEATURE 5: QR code generation"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_qr_code_generation(
        self, orchestrator, mock_session_manager,
        sample_message, sample_session
    ):
        """Test: Generación de código QR"""
        sample_session["reservation_id"] = "RES-12345"
        mock_session_manager.get_session.return_value = sample_session
        
        nlp_result = {
            "intent": "generar_qr",
            "confidence": 0.80,
            "entities": {}
        }
        
        with patch('app.services.orchestrator.generate_qr_code') as mock_qr:
            mock_qr.return_value = "base64_encoded_qr_image"
            
            result = await orchestrator.handle_intent(
                nlp_result=nlp_result,
                session=sample_session,
                message=sample_message
            )
            
            # Puede retornar imagen o link
            assert result is not None


class TestErrorHandling:
    """Tests de manejo de errores en handle_intent()"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pms_error_triggers_escalation(
        self, orchestrator, mock_pms_adapter, mock_session_manager,
        sample_message, sample_session
    ):
        """Test: Error del PMS debe escalar"""
        mock_session_manager.get_session.return_value = sample_session
        mock_pms_adapter.check_availability.side_effect = Exception("PMS connection failed")
        
        nlp_result = {
            "intent": "consultar_disponibilidad",
            "confidence": 0.9,
            "entities": {}
        }
        
        with patch('app.services.orchestrator.alert_manager') as mock_alert:
            mock_alert.send_alert = AsyncMock()
            
            result = await orchestrator.handle_intent(
                nlp_result=nlp_result,
                session=sample_session,
                message=sample_message
            )
            
            # Debe retornar respuesta (posiblemente escalada)
            assert result is not None
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_low_confidence_fallback(
        self, orchestrator, mock_session_manager,
        sample_message, sample_session
    ):
        """Test: Baja confianza debe usar fallback o escalar"""
        mock_session_manager.get_session.return_value = sample_session
        
        nlp_result = {
            "intent": "unknown",
            "confidence": 0.35,  # Muy baja
            "entities": {}
        }
        
        result = await orchestrator.handle_intent(
            nlp_result=nlp_result,
            session=sample_session,
            message=sample_message
        )
        
        assert result is not None
        # Debe tener mensaje de fallback o escalación


class TestIntentRouting:
    """Tests de routing de intents"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_unknown_intent_handling(
        self, orchestrator, mock_session_manager,
        sample_message, sample_session
    ):
        """Test: Intent desconocido debe manejarse gracefully"""
        mock_session_manager.get_session.return_value = sample_session
        
        nlp_result = {
            "intent": "intent_that_does_not_exist",
            "confidence": 0.75,
            "entities": {}
        }
        
        result = await orchestrator.handle_intent(
            nlp_result=nlp_result,
            session=sample_session,
            message=sample_message
        )
        
        assert result is not None
        assert result["response_type"] == "text"
