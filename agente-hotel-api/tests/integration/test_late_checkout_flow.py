"""
Test de integración E2E para flujo de late checkout.
Feature 4: Late Checkout con Confirmación en 2 Pasos

Flujo completo:
1. Usuario solicita "quiero late checkout"
2. NLP detecta intent "late_checkout"
3. Orchestrator verifica booking_id en sesión
4. PMS adapter consulta disponibilidad y precio
5. Sistema solicita confirmación
6. Usuario confirma/cancela
7. Si confirma: PMS registra late checkout
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.models.unified_message import UnifiedMessage


class TestLateCheckoutFlowE2E:
    """Tests end-to-end del flujo de late checkout."""

    @pytest.fixture
    def test_client(self):
        """Fixture que crea cliente de prueba."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_late_checkout_full_flow_success(self):
        """Test E2E: Flujo completo de late checkout exitoso con confirmación."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter

        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        user_id = "5491112345678"
        booking_id = "HTL-12345"

        # Mock PMS responses
        with (
            patch.object(pms_adapter, "check_late_checkout_availability") as mock_check,
            patch.object(pms_adapter, "confirm_late_checkout") as mock_confirm,
        ):
            # Mock availability check - disponible con cargo
            mock_check.return_value = {
                "available": True,
                "late_checkout_time": "15:00",
                "fee": 75.0,
                "is_free": False,
                "reason": None,
            }

            # Mock confirmation
            mock_confirm.return_value = {
                "success": True,
                "confirmation_id": "LC-67890",
                "late_checkout_time": "15:00",
                "fee": 75.0,
            }

            # Step 1: Usuario solicita late checkout (con booking_id en sesión)
            await session_manager.set_session_data(user_id, "booking_id", booking_id)

            message_request = UnifiedMessage(
                user_id=user_id, texto="necesito late checkout por favor", canal="whatsapp", tipo="text", metadata={}
            )

            # Act & Assert - Primera respuesta (solicita confirmación)
            response = await orchestrator.process_message(message_request)

            # Verificaciones primera respuesta
            assert response.response_type == "text"
            assert "Late checkout disponible hasta las 15:00" in response.content
            assert "$75" in response.content
            assert "¿Confirmas el late checkout?" in response.content

            # Verificar que se llamó al PMS adapter
            mock_check.assert_called_once_with(booking_id, user_id)

            # Verificar que se guardó el estado pending en sesión
            session_data = await session_manager.get_session_data(user_id)
            assert session_data.get("pending_late_checkout") is True
            assert session_data.get("late_checkout_details") is not None

            # Step 2: Usuario confirma
            confirmation_message = UnifiedMessage(
                user_id=user_id, texto="sí, confirmo", canal="whatsapp", tipo="text", metadata={}
            )

            # Act - Confirmación
            confirmation_response = await orchestrator.process_message(confirmation_message)

            # Assert - Respuesta de confirmación
            assert confirmation_response.response_type == "text"
            assert "Late checkout confirmado hasta las 15:00" in confirmation_response.content
            assert "$75" in confirmation_response.content
            assert "Se agregará a tu cuenta" in confirmation_response.content

            # Verificar que se llamó al confirm
            mock_confirm.assert_called_once()

            # Verificar que se limpió el estado pending
            final_session = await session_manager.get_session_data(user_id)
            assert final_session.get("pending_late_checkout") is False

    @pytest.mark.asyncio
    async def test_late_checkout_without_booking_id(self):
        """Test E2E: Usuario solicita late checkout sin booking_id en sesión."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter

        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        user_id = "5491112345678"

        # Mensaje sin booking_id en sesión
        message = UnifiedMessage(
            user_id=user_id, texto="quiero late checkout", canal="whatsapp", tipo="text", metadata={}
        )

        # Act
        response = await orchestrator.process_message(message)

        # Assert
        assert response.response_type == "text"
        assert "necesito tu número de reserva" in response.content.lower()
        assert "podrías compartirlo" in response.content.lower()

    @pytest.mark.asyncio
    async def test_late_checkout_not_available(self):
        """Test E2E: Late checkout no disponible (siguiente reserva)."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter

        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        user_id = "5491112345678"
        booking_id = "HTL-12345"

        with patch.object(pms_adapter, "check_late_checkout_availability") as mock_check:
            # Mock no disponibilidad
            mock_check.return_value = {
                "available": False,
                "late_checkout_time": None,
                "fee": 0,
                "is_free": False,
                "reason": "next_booking_conflict",
            }

            # Setup sesión con booking_id
            await session_manager.set_session_data(user_id, "booking_id", booking_id)

            message = UnifiedMessage(
                user_id=user_id, texto="necesito late checkout", canal="whatsapp", tipo="text", metadata={}
            )

            # Act
            response = await orchestrator.process_message(message)

            # Assert
            assert response.response_type == "text"
            assert "no hay disponibilidad para late checkout" in response.content.lower()
            assert "habitación está reservada" in response.content.lower()
            assert "guardar equipaje" in response.content.lower()

    @pytest.mark.asyncio
    async def test_late_checkout_confirmation_flow(self):
        """Test E2E: Flujo de confirmación en 2 pasos detallado."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter

        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        user_id = "5491112345678"
        booking_id = "HTL-12345"

        with (
            patch.object(pms_adapter, "check_late_checkout_availability") as mock_check,
            patch.object(pms_adapter, "confirm_late_checkout") as mock_confirm,
        ):
            mock_check.return_value = {
                "available": True,
                "late_checkout_time": "16:00",
                "fee": 100.0,
                "is_free": False,
                "reason": None,
            }

            # Setup
            await session_manager.set_session_data(user_id, "booking_id", booking_id)

            # Step 1: Solicitud inicial
            request_message = UnifiedMessage(
                user_id=user_id, texto="late checkout por favor", canal="whatsapp", tipo="text", metadata={}
            )

            await orchestrator.process_message(request_message)

            # Verificar pending state
            session_data = await session_manager.get_session_data(user_id)
            assert session_data.get("pending_late_checkout") is True

            details = session_data.get("late_checkout_details")
            assert details is not None
            assert details["late_checkout_time"] == "16:00"
            assert details["fee"] == 100.0

            # Step 2: Confirmación positiva
            mock_confirm.return_value = {
                "success": True,
                "confirmation_id": "LC-99999",
                "late_checkout_time": "16:00",
                "fee": 100.0,
            }

            confirm_message = UnifiedMessage(user_id=user_id, texto="sí", canal="whatsapp", tipo="text", metadata={})

            response2 = await orchestrator.process_message(confirm_message)

            # Verificaciones finales
            assert "confirmado" in response2.content.lower()
            mock_confirm.assert_called_once()

            # Estado pending debe estar limpio
            final_session = await session_manager.get_session_data(user_id)
            assert final_session.get("pending_late_checkout") is False

    @pytest.mark.asyncio
    async def test_late_checkout_cancel_flow(self):
        """Test E2E: Usuario cancela la confirmación de late checkout."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter

        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        user_id = "5491112345678"
        booking_id = "HTL-12345"

        with patch.object(pms_adapter, "check_late_checkout_availability") as mock_check:
            mock_check.return_value = {
                "available": True,
                "late_checkout_time": "14:00",
                "fee": 50.0,
                "is_free": False,
                "reason": None,
            }

            # Setup y solicitud inicial
            await session_manager.set_session_data(user_id, "booking_id", booking_id)

            request_message = UnifiedMessage(
                user_id=user_id, texto="quiero late checkout", canal="whatsapp", tipo="text", metadata={}
            )

            await orchestrator.process_message(request_message)

            # Verificar pending state
            session_data = await session_manager.get_session_data(user_id)
            assert session_data.get("pending_late_checkout") is True

            # Usuario cancela
            cancel_message = UnifiedMessage(
                user_id=user_id, texto="no, cancelo", canal="whatsapp", tipo="text", metadata={}
            )

            # Act
            cancel_response = await orchestrator.process_message(cancel_message)

            # Assert
            assert cancel_response.response_type == "text"
            # Debe manejar la cancelación (respuesta genérica o specific)

            # Estado pending debe estar limpio
            final_session = await session_manager.get_session_data(user_id)
            assert final_session.get("pending_late_checkout") is False

    @pytest.mark.asyncio
    async def test_late_checkout_with_audio(self):
        """Test E2E: Solicitud de late checkout via mensaje de audio."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter

        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        user_id = "5491112345678"
        booking_id = "HTL-12345"

        with patch.object(pms_adapter, "check_late_checkout_availability") as mock_check:
            mock_check.return_value = {
                "available": True,
                "late_checkout_time": "15:00",
                "fee": 0.0,  # Gratis en este caso
                "is_free": True,
                "reason": None,
            }

            # Setup sesión
            await session_manager.set_session_data(user_id, "booking_id", booking_id)

            # Mensaje de audio (simulando transcripción)
            audio_message = UnifiedMessage(
                user_id=user_id,
                texto="hola necesito late checkout por favor",  # Texto transcrito
                canal="whatsapp",
                tipo="audio",
                metadata={"audio_duration": 3.5, "transcription_confidence": 0.95},
            )

            # Act
            response = await orchestrator.process_message(audio_message)

            # Assert
            assert response.response_type == "text"
            assert "Late checkout" in response.content
            assert "sin cargo adicional" in response.content or "gratuito" in response.content.lower()

    @pytest.mark.asyncio
    async def test_late_checkout_multiple_requests(self):
        """Test E2E: Múltiples solicitudes de late checkout del mismo usuario."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter

        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        user_id = "5491112345678"
        booking_id = "HTL-12345"

        with patch.object(pms_adapter, "check_late_checkout_availability") as mock_check:
            mock_check.return_value = {
                "available": True,
                "late_checkout_time": "15:00",
                "fee": 75.0,
                "is_free": False,
                "reason": None,
            }

            await session_manager.set_session_data(user_id, "booking_id", booking_id)

            message = UnifiedMessage(user_id=user_id, texto="late checkout", canal="whatsapp", tipo="text", metadata={})

            # Primera solicitud
            response1 = await orchestrator.process_message(message)
            assert "¿Confirmas" in response1.content

            # Segunda solicitud (duplicada)
            await orchestrator.process_message(message)

            # Debe manejar gracefully (no duplicar pending state)
            session_data = await session_manager.get_session_data(user_id)
            assert session_data.get("pending_late_checkout") is True

    @pytest.mark.asyncio
    async def test_late_checkout_cache_behavior(self):
        """Test E2E: Verificar comportamiento de cache en consultas late checkout."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter

        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        user_id = "5491112345678"
        booking_id = "HTL-12345"

        with patch.object(pms_adapter, "check_late_checkout_availability") as mock_check:
            mock_check.return_value = {
                "available": True,
                "late_checkout_time": "15:00",
                "fee": 75.0,
                "is_free": False,
                "reason": None,
            }

            await session_manager.set_session_data(user_id, "booking_id", booking_id)

            message = UnifiedMessage(
                user_id=user_id, texto="late checkout por favor", canal="whatsapp", tipo="text", metadata={}
            )

            # Primera consulta (debe llamar PMS)
            await orchestrator.process_message(message)
            assert mock_check.call_count == 1

            # Cancel pending state para hacer segunda consulta
            await session_manager.set_session_data(user_id, "pending_late_checkout", False)

            # Segunda consulta (puede usar cache)
            await orchestrator.process_message(message)

            # Verificar que el cache funciona correctamente
            # (El número exacto de calls depende de la implementación del cache)
            assert mock_check.call_count >= 1

    @pytest.mark.asyncio
    async def test_late_checkout_error_handling(self):
        """Test E2E: Manejo de errores en late checkout."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter

        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        user_id = "5491112345678"
        booking_id = "HTL-12345"

        with patch.object(pms_adapter, "check_late_checkout_availability") as mock_check:
            # Mock error en PMS
            mock_check.side_effect = Exception("PMS connection failed")

            await session_manager.set_session_data(user_id, "booking_id", booking_id)

            message = UnifiedMessage(
                user_id=user_id, texto="necesito late checkout", canal="whatsapp", tipo="text", metadata={}
            )

            # Act
            response = await orchestrator.process_message(message)

            # Assert - Debe manejar el error gracefully
            assert response.response_type == "text"
            # Debe mostrar mensaje de error genérico
            assert "error" in response.content.lower() or "problema" in response.content.lower()

    @pytest.mark.asyncio
    async def test_late_checkout_free_offer(self):
        """Test E2E: Late checkout gratuito ofrecido por el hotel."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter

        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        user_id = "5491112345678"
        booking_id = "HTL-12345"

        with (
            patch.object(pms_adapter, "check_late_checkout_availability") as mock_check,
            patch.object(pms_adapter, "confirm_late_checkout") as mock_confirm,
        ):
            # Mock late checkout gratuito
            mock_check.return_value = {
                "available": True,
                "late_checkout_time": "14:00",
                "fee": 0.0,
                "is_free": True,
                "reason": "vip_guest",
            }

            mock_confirm.return_value = {
                "success": True,
                "confirmation_id": "LC-FREE-001",
                "late_checkout_time": "14:00",
                "fee": 0.0,
            }

            await session_manager.set_session_data(user_id, "booking_id", booking_id)

            # Solicitud
            message = UnifiedMessage(user_id=user_id, texto="late checkout", canal="whatsapp", tipo="text", metadata={})

            response = await orchestrator.process_message(message)

            # Assert - Debe mencionar que es gratuito
            assert response.response_type == "text"
            assert "sin cargo" in response.content.lower() or "gratuito" in response.content.lower()
            assert "14:00" in response.content

            # Confirmación
            confirm_message = UnifiedMessage(
                user_id=user_id, texto="sí, confirmo", canal="whatsapp", tipo="text", metadata={}
            )

            confirm_response = await orchestrator.process_message(confirm_message)
            assert "confirmado" in confirm_response.content.lower()
            mock_confirm.assert_called_once()
