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
from unittest.mock import patch, AsyncMock
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

        # Patch business hours and NLP Engine
        with (
            patch("app.services.orchestrator.is_business_hours", return_value=True),
            patch("app.services.orchestrator.NLPEngine") as MockNLPEngine
        ):
            # Configure NLP Mock
            mock_nlp = MockNLPEngine.return_value
            mock_nlp.process_message = AsyncMock(return_value={
                "intent": {"name": "late_checkout", "confidence": 0.95},
                "entities": {}
            })
            mock_nlp.detect_language = AsyncMock(return_value="es")
            mock_nlp.process_text = AsyncMock(return_value={
                "intent": {"name": "late_checkout", "confidence": 0.95},
                "entities": {}
            })

            pms_adapter = get_pms_adapter()
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
                    "requested_time": "15:00",
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
                assert "late checkout disponible" in response.content.lower()
                assert "15:00" in response.content
                assert "$75" in response.content
                assert "confirmas" in response.content.lower()

                # Verificar que se llamó al PMS adapter
                mock_check.assert_called_once_with(reservation_id=booking_id, requested_checkout_time="14:00")

                # Verificar que se guardó el estado pending en sesión
                session_data = await session_manager.get_session_data(user_id)
                assert session_data.get("pending_late_checkout") is not None

                # Step 2: Usuario confirma
                # Para la confirmación, el intent podría ser "affirm" o similar, o el orchestrator maneja el contexto
                # Si el orchestrator usa NLP para detectar "sí", necesitamos actualizar el mock
                mock_nlp.process_message.return_value = {
                    "intent": {"name": "affirm", "confidence": 0.95},
                    "entities": {}
                }
                mock_nlp.process_text.return_value = {
                    "intent": {"name": "affirm", "confidence": 0.95},
                    "entities": {}
                }

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
                assert final_session.get("pending_late_checkout") is None

    @pytest.mark.asyncio
    async def test_late_checkout_without_booking_id(self):
        """Test E2E: Usuario solicita late checkout sin booking_id en sesión."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter

        # Patch business hours and NLP Engine
        with (
            patch("app.services.orchestrator.is_business_hours", return_value=True),
            patch("app.services.orchestrator.NLPEngine") as MockNLPEngine
        ):
            mock_nlp = MockNLPEngine.return_value
            mock_nlp.process_message = AsyncMock(return_value={
                "intent": {"name": "late_checkout", "confidence": 0.95},
                "entities": {}
            })
            mock_nlp.detect_language = AsyncMock(return_value="es")
            mock_nlp.process_text = AsyncMock(return_value={
                "intent": {"name": "late_checkout", "confidence": 0.95},
                "entities": {}
            })

            pms_adapter = get_pms_adapter()
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

        # Patch business hours and NLP Engine
        with (
            patch("app.services.orchestrator.is_business_hours", return_value=True),
            patch("app.services.orchestrator.NLPEngine") as MockNLPEngine
        ):
            mock_nlp = MockNLPEngine.return_value
            mock_nlp.process_message = AsyncMock(return_value={
                "intent": {"name": "late_checkout", "confidence": 0.95},
                "entities": {}
            })
            mock_nlp.detect_language = AsyncMock(return_value="es")
            mock_nlp.process_text = AsyncMock(return_value={
                "intent": {"name": "late_checkout", "confidence": 0.95},
                "entities": {}
            })

            pms_adapter = get_pms_adapter()
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

        # Patch business hours and NLP Engine
        with (
            patch("app.services.orchestrator.is_business_hours", return_value=True),
            patch("app.services.orchestrator.NLPEngine") as MockNLPEngine
        ):
            mock_nlp = MockNLPEngine.return_value
            mock_nlp.process_message = AsyncMock(return_value={
                "intent": {"name": "late_checkout", "confidence": 0.95},
                "entities": {}
            })
            mock_nlp.detect_language = AsyncMock(return_value="es")
            mock_nlp.process_text = AsyncMock(return_value={
                "intent": {"name": "late_checkout", "confidence": 0.95},
                "entities": {}
            })

            pms_adapter = get_pms_adapter()
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
                    "requested_time": "16:00",
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
                pending_data = session_data.get("pending_late_checkout")
                assert pending_data is not None
                assert isinstance(pending_data, dict)
                assert pending_data["checkout_time"] == "16:00"
                assert pending_data["fee"] == 100.0

                # Step 2: Confirmación positiva
                mock_nlp.process_message.return_value = {
                    "intent": {"name": "affirm", "confidence": 0.95},
                    "entities": {}
                }
                mock_nlp.process_text.return_value = {
                    "intent": {"name": "affirm", "confidence": 0.95},
                    "entities": {}
                }
                
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
                assert final_session.get("pending_late_checkout") is None

    @pytest.mark.asyncio
    async def test_late_checkout_cancel_flow(self):
        """Test E2E: Usuario cancela la confirmación de late checkout."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter

        # Patch business hours and NLP Engine
        with (
            patch("app.services.orchestrator.is_business_hours", return_value=True),
            patch("app.services.orchestrator.NLPEngine") as MockNLPEngine
        ):
            mock_nlp = MockNLPEngine.return_value
            mock_nlp.process_message = AsyncMock(return_value={
                "intent": {"name": "late_checkout", "confidence": 0.95},
                "entities": {}
            })
            mock_nlp.detect_language = AsyncMock(return_value="es")
            mock_nlp.process_text = AsyncMock(return_value={
                "intent": {"name": "late_checkout", "confidence": 0.95},
                "entities": {}
            })

            pms_adapter = get_pms_adapter()
            session_manager = SessionManager()
            lock_service = LockService()
            orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

            user_id = "5491112345678"
            booking_id = "HTL-12345"

            with patch.object(pms_adapter, "check_late_checkout_availability") as mock_check:
                mock_check.return_value = {
                    "available": True,
                    "requested_time": "15:00",
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
                assert session_data.get("pending_late_checkout") is not None

                # Usuario cancela
                mock_nlp.process_message.return_value = {
                    "intent": {"name": "deny", "confidence": 0.95},
                    "entities": {}
                }
                mock_nlp.process_text.return_value = {
                    "intent": {"name": "deny", "confidence": 0.95},
                    "entities": {}
                }

                cancel_message = UnifiedMessage(
                    user_id=user_id, texto="no, cancelar", canal="whatsapp", tipo="text", metadata={}
                )

                # Act - Cancelación
                cancel_response = await orchestrator.process_message(cancel_message)

                # Assert - Respuesta de cancelación
                assert cancel_response.response_type == "text"
                assert "cancelado" in cancel_response.content.lower() or "entendido" in cancel_response.content.lower()

                # Verificar que se limpió el estado pending
                final_session = await session_manager.get_session_data(user_id)
                assert final_session.get("pending_late_checkout") is None

    @pytest.mark.asyncio
    async def test_late_checkout_with_audio(self):
        """Test E2E: Solicitud de late checkout via mensaje de audio."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter

        # Patch business hours and NLP Engine
        with (
            patch("app.services.orchestrator.is_business_hours", return_value=True),
            patch("app.services.orchestrator.NLPEngine") as MockNLPEngine
        ):
            mock_nlp = MockNLPEngine.return_value
            mock_nlp.process_message = AsyncMock(return_value={
                "intent": {"name": "late_checkout", "confidence": 0.95},
                "entities": {}
            })
            mock_nlp.detect_language = AsyncMock(return_value="es")
            mock_nlp.process_text = AsyncMock(return_value={
                "intent": {"name": "late_checkout", "confidence": 0.95},
                "entities": {}
            })

            pms_adapter = get_pms_adapter()
            session_manager = SessionManager()
            lock_service = LockService()
            orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

            user_id = "5491112345678"
            booking_id = "HTL-12345"

            with patch.object(pms_adapter, "check_late_checkout_availability") as mock_check:
                mock_check.return_value = {
                    "available": True,
                    "requested_time": "15:00",
                    "fee": 0.0,  # Gratis en este caso
                    "is_free": True,
                    "reason": None,
                }

                # Setup sesión
                await session_manager.set_session_data(user_id, "booking_id", booking_id)

                # Mensaje de audio (simulando transcripción)
                audio_message = UnifiedMessage(
                    user_id=user_id,
                    texto="quisiera salir más tarde",  # Transcripción
                    canal="whatsapp",
                    tipo="audio",
                    metadata={"audio_duration": 5},
                )

                # Act
                response = await orchestrator.process_message(audio_message)

                # Assert
                # La respuesta debe ser audio también (o texto si no hay TTS configurado, pero el orchestrator intenta audio)
                # En este test verificamos el contenido del texto generado
                if response.response_type == "audio":
                    content_text = response.content["text"]
                else:
                    content_text = response.content

                assert "late checkout" in content_text.lower()
                assert "gratis" in content_text.lower() or "sin costo" in content_text.lower() or "sin cargo" in content_text.lower()

    @pytest.mark.asyncio
    async def test_late_checkout_multiple_requests(self):
        """Test E2E: Múltiples solicitudes de late checkout del mismo usuario."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter

        # Patch business hours and NLP Engine
        with (
            patch("app.services.orchestrator.is_business_hours", return_value=True),
            patch("app.services.orchestrator.NLPEngine") as MockNLPEngine
        ):
            mock_nlp = MockNLPEngine.return_value
            mock_nlp.process_message = AsyncMock(return_value={
                "intent": {"name": "late_checkout", "confidence": 0.95},
                "entities": {}
            })
            mock_nlp.detect_language = AsyncMock(return_value="es")
            mock_nlp.process_text = AsyncMock(return_value={
                "intent": {"name": "late_checkout", "confidence": 0.95},
                "entities": {}
            })

            pms_adapter = get_pms_adapter()
            session_manager = SessionManager()
            lock_service = LockService()
            orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

            user_id = "5491112345678"
            booking_id = "HTL-12345"

            with patch.object(pms_adapter, "check_late_checkout_availability") as mock_check:
                mock_check.return_value = {
                    "available": True,
                    "requested_time": "14:00",
                    "fee": 50.0,
                    "is_free": False,
                    "reason": None,
                }

                await session_manager.set_session_data(user_id, "booking_id", booking_id)

                # Primera solicitud
                msg1 = UnifiedMessage(
                    user_id=user_id, texto="late checkout", canal="whatsapp", tipo="text", metadata={}
                )
                await orchestrator.process_message(msg1)

                # Verificar estado pending
                session1 = await session_manager.get_session_data(user_id)
                assert session1.get("pending_late_checkout") is not None

                # Segunda solicitud (debería detectar que ya hay una pendiente o actualizarla)
                msg2 = UnifiedMessage(
                    user_id=user_id, texto="quiero salir tarde", canal="whatsapp", tipo="text", metadata={}
                )
                response2 = await orchestrator.process_message(msg2)

                # Assert - Debería recordar la oferta o volver a ofrecerla
                assert "disponible hasta las 14:00" in response2.content
                assert "$50" in response2.content

                # Verificar que no se duplicó el estado (o sigue siendo válido)
                session2 = await session_manager.get_session_data(user_id)
                assert session2.get("pending_late_checkout") is not None

    @pytest.mark.asyncio
    async def test_late_checkout_cache_behavior(self):
        """Test E2E: Verificar comportamiento de cache en consultas late checkout."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter

        # Patch business hours and NLP Engine
        with (
            patch("app.services.orchestrator.is_business_hours", return_value=True),
            patch("app.services.orchestrator.NLPEngine") as MockNLPEngine
        ):
            mock_nlp = MockNLPEngine.return_value
            mock_nlp.process_message = AsyncMock(return_value={
                "intent": {"name": "late_checkout", "confidence": 0.95},
                "entities": {}
            })
            mock_nlp.detect_language = AsyncMock(return_value="es")
            mock_nlp.process_text = AsyncMock(return_value={
                "intent": {"name": "late_checkout", "confidence": 0.95},
                "entities": {}
            })

            pms_adapter = get_pms_adapter()
            session_manager = SessionManager()
            lock_service = LockService()
            orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

            user_id = "5491112345678"
            booking_id = "HTL-CACHE-TEST"

            # Usamos un mock que cuente las llamadas reales (aunque el adapter tiene su propio cache,
            # aquí probamos que el orchestrator llame al adapter)
            with patch.object(pms_adapter, "check_late_checkout_availability") as mock_check:
                mock_check.return_value = {
                    "available": True,
                    "requested_time": "15:00",
                    "fee": 60.0,
                    "is_free": False,
                    "reason": None,
                }

                await session_manager.set_session_data(user_id, "booking_id", booking_id)

                # Primera llamada
                msg1 = UnifiedMessage(
                    user_id=user_id, texto="late checkout", canal="whatsapp", tipo="text", metadata={}
                )
                await orchestrator.process_message(msg1)

                # Segunda llamada inmediata
                msg2 = UnifiedMessage(
                    user_id=user_id, texto="late checkout", canal="whatsapp", tipo="text", metadata={}
                )
                await orchestrator.process_message(msg2)

                # Assert
                # Si el PMS adapter tiene cache, mock_check podría ser llamado 1 o 2 veces dependiendo de cómo se mockea.
                # Si mockeamos el método público del adapter, el cache interno del adapter NO se ejecuta (porque estamos reemplazando el método).
                # Así que esperamos 2 llamadas al mock.
                # Si quisiéramos probar el cache del adapter, deberíamos no mockear el método público sino el request interno.
                assert mock_check.call_count == 2

    @pytest.mark.asyncio
    async def test_late_checkout_error_handling(self):
        """Test E2E: Manejo de errores en late checkout."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter
        from app.exceptions.pms_exceptions import PMSError

        # Patch business hours and NLP Engine
        with (
            patch("app.services.orchestrator.is_business_hours", return_value=True),
            patch("app.services.orchestrator.NLPEngine") as MockNLPEngine
        ):
            mock_nlp = MockNLPEngine.return_value
            mock_nlp.process_message = AsyncMock(return_value={
                "intent": {"name": "late_checkout", "confidence": 0.95},
                "entities": {}
            })
            mock_nlp.detect_language = AsyncMock(return_value="es")
            mock_nlp.process_text = AsyncMock(return_value={
                "intent": {"name": "late_checkout", "confidence": 0.95},
                "entities": {}
            })

            pms_adapter = get_pms_adapter()
            session_manager = SessionManager()
            lock_service = LockService()
            orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

            user_id = "5491112345678"
            booking_id = "HTL-ERROR"

            with patch.object(pms_adapter, "check_late_checkout_availability") as mock_check:
                # Simular error del PMS
                mock_check.side_effect = PMSError("Connection timeout")

                await session_manager.set_session_data(user_id, "booking_id", booking_id)

                message = UnifiedMessage(
                    user_id=user_id, texto="late checkout", canal="whatsapp", tipo="text", metadata={}
                )

                # Act
                response = await orchestrator.process_message(message)

                # Assert - Debería dar un mensaje de error amigable o fallback
                assert response.response_type == "text"
                assert "lo siento" in response.content.lower() or "problema técnico" in response.content.lower() or "intentar más tarde" in response.content.lower()

    @pytest.mark.asyncio
    async def test_late_checkout_free_offer(self):
        """Test E2E: Late checkout gratuito ofrecido por el hotel."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter

        # Patch business hours and NLP Engine
        with (
            patch("app.services.orchestrator.is_business_hours", return_value=True),
            patch("app.services.orchestrator.NLPEngine") as MockNLPEngine
        ):
            mock_nlp = MockNLPEngine.return_value
            mock_nlp.process_message = AsyncMock(return_value={
                "intent": {"name": "late_checkout", "confidence": 0.95},
                "entities": {}
            })
            mock_nlp.detect_language = AsyncMock(return_value="es")
            mock_nlp.process_text = AsyncMock(return_value={
                "intent": {"name": "late_checkout", "confidence": 0.95},
                "entities": {}
            })

            pms_adapter = get_pms_adapter()
            session_manager = SessionManager()
            lock_service = LockService()
            orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

            user_id = "5491112345678"
            booking_id = "HTL-VIP"

            with (
                patch.object(pms_adapter, "check_late_checkout_availability") as mock_check,
                patch.object(pms_adapter, "confirm_late_checkout") as mock_confirm
            ):
                mock_check.return_value = {
                    "available": True,
                    "requested_time": "14:00",
                    "fee": 0.0,
                    "is_free": True,
                    "reason": "loyalty_program",
                }
                mock_confirm.return_value = {
                    "success": True,
                    "confirmation_id": "LC-FREE-123",
                    "late_checkout_time": "14:00",
                    "fee": 0.0
                }

                await session_manager.set_session_data(user_id, "booking_id", booking_id)

                message = UnifiedMessage(
                    user_id=user_id, texto="late checkout", canal="whatsapp", tipo="text", metadata={}
                )

                # Act
                response = await orchestrator.process_message(message)

                # Assert
                assert "gratis" in response.content.lower() or "sin costo" in response.content.lower() or "sin cargo" in response.content.lower()
                assert "14:00" in response.content

                # Confirmación
                mock_nlp.process_message.return_value = {
                    "intent": {"name": "affirm", "confidence": 0.95},
                    "entities": {}
                }
                mock_nlp.process_text.return_value = {
                    "intent": {"name": "affirm", "confidence": 0.95},
                    "entities": {}
                }

                confirm_message = UnifiedMessage(
                    user_id=user_id, texto="sí, confirmo", canal="whatsapp", tipo="text", metadata={}
                )

                confirm_response = await orchestrator.process_message(confirm_message)
                assert "confirmado" in confirm_response.content.lower()
                mock_confirm.assert_called_once()
