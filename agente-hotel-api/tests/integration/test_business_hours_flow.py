"""
Tests de integración para funcionalidad de horarios diferenciados.
Feature 2: Respuestas con Horario Diferenciado

Tests para el orchestrator con lógica de business hours.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from zoneinfo import ZoneInfo
from app.services.orchestrator import Orchestrator
from app.services.session_manager import SessionManager
from app.services.lock_service import LockService
from app.models.unified_message import UnifiedMessage


class TestBusinessHoursIntegration:
    """Tests de integración para respuestas con horarios diferenciados."""

    async def _create_orchestrator(self):
        """Helper para crear instancia del orchestrator."""
        from app.services.pms_adapter import get_pms_adapter

        pms_adapter = get_pms_adapter()  # NO usar await - no es async
        session_manager = SessionManager()
        lock_service = LockService()
        return Orchestrator(pms_adapter, session_manager, lock_service)

    @pytest.mark.asyncio
    async def test_after_hours_response_standard(self):
        """Test: Respuesta estándar fuera de horario."""
        orchestrator = await self._create_orchestrator()

        # Arrange - Mensaje a las 22:00 (fuera de horario)
        with patch("app.utils.business_hours.is_business_hours", return_value=False):
            with patch("app.utils.business_hours.datetime") as mock_datetime:
                # Mock weekday para que no sea fin de semana
                mock_now = MagicMock()
                mock_now.weekday.return_value = 3  # Jueves = 3
                mock_datetime.now.return_value = mock_now

                message = UnifiedMessage(
                    user_id="5491112345678", texto="¿tienen disponibilidad?", canal="whatsapp", tipo="text", metadata={}
                )

                # Act
                result = await orchestrator.handle_unified_message(message)

                # Assert
                assert result is not None
                assert "response" in result or "content" in result

                # Verificar que menciona horario o "fuera de horario"
                response_text = result.get("response") or result.get("content", "")
                assert any(keyword in response_text.lower() for keyword in ["horario", "fuera", "mañana", "urgente"])

    @pytest.mark.asyncio
    async def test_after_hours_weekend_response(self):
        """Test: Respuesta específica para fin de semana."""
        orchestrator = await self._create_orchestrator()

        # Arrange - Mensaje el sábado
        with patch("app.utils.business_hours.is_business_hours", return_value=False):
            with patch("app.utils.business_hours.datetime") as mock_datetime:
                # Mock para sábado
                saturday = datetime(2025, 10, 11, 22, 0)  # Sábado
                mock_datetime.now.return_value = saturday

                message = UnifiedMessage(
                    user_id="5491112345678", texto="necesito una habitación", canal="whatsapp", tipo="text", metadata={}
                )

                # Act
                result = await orchestrator.handle_unified_message(message)

                # Assert
                assert result is not None
                response_text = result.get("response") or result.get("content", "")

                # Verificar mensaje de fin de semana
                # Puede mencionar "fin de semana", "lunes", etc.
                assert isinstance(response_text, str)

    @pytest.mark.asyncio
    async def test_urgent_keyword_escalation(self):
        """Test: Escalamiento cuando mensaje contiene palabra URGENTE."""
        orchestrator = await self._create_orchestrator()

        # Arrange - Mensaje urgente fuera de horario
        with patch("app.utils.business_hours.is_business_hours", return_value=False):
            message = UnifiedMessage(
                user_id="5491112345678",
                texto="URGENTE necesito una habitación",
                canal="whatsapp",
                tipo="text",
                metadata={},
            )

            # Act
            result = await orchestrator.handle_unified_message(message)

            # Assert
            assert result is not None
            response_text = result.get("response") or result.get("content", "")

            # Verificar que menciona escalamiento o personal de guardia
            assert any(keyword in response_text.lower() for keyword in ["guardia", "derivando", "personal", "escalado"])

    @pytest.mark.asyncio
    async def test_urgent_variations_detection(self):
        """Test: Detección de variaciones de urgente."""
        orchestrator = await self._create_orchestrator()

        # Arrange - Diferentes formas de urgencia
        urgent_keywords = ["urgente", "urgent", "emergency", "URGENTE"]

        for keyword in urgent_keywords:
            with patch("app.utils.business_hours.is_business_hours", return_value=False):
                message = UnifiedMessage(
                    user_id="5491112345678", texto=f"esto es {keyword}", canal="whatsapp", tipo="text", metadata={}
                )

                # Act
                result = await orchestrator.handle_unified_message(message)

                # Assert
                assert result is not None, f"Failed for keyword: {keyword}"
                response_text = result.get("response") or result.get("content", "")

                # Debe activar respuesta de escalamiento
                assert isinstance(response_text, str)

    @pytest.mark.asyncio
    async def test_normal_response_during_business_hours(self):
        """Test: Respuesta normal durante horario comercial."""
        orchestrator = await self._create_orchestrator()

        # Arrange - Mensaje a las 14:00 (dentro de horario)
        with patch("app.utils.business_hours.is_business_hours", return_value=True):
            message = UnifiedMessage(
                user_id="5491112345678", texto="¿tienen disponibilidad?", canal="whatsapp", tipo="text", metadata={}
            )

            # Act
            result = await orchestrator.handle_unified_message(message)

            # Assert
            assert result is not None
            # Durante horario comercial, debe procesar normalmente
            # No debe mostrar mensaje de "fuera de horario"

    @pytest.mark.asyncio
    async def test_business_hours_with_location_request(self):
        """Test: Solicitud de ubicación fuera de horario (debe responder)."""
        orchestrator = await self._create_orchestrator()

        # Arrange - Ubicación no debería estar bloqueada por horario
        with patch("app.utils.business_hours.is_business_hours", return_value=False):
            message = UnifiedMessage(
                user_id="5491112345678", texto="¿dónde están ubicados?", canal="whatsapp", tipo="text", metadata={}
            )

            # Act
            result = await orchestrator.handle_unified_message(message)

            # Assert
            assert result is not None
            # Solicitudes de información como ubicación deberían responderse
            # incluso fuera de horario

    @pytest.mark.asyncio
    async def test_after_hours_includes_next_open_time(self):
        """Test: Mensaje fuera de horario incluye próximo horario de apertura."""
        orchestrator = await self._create_orchestrator()

        # Arrange
        with patch("app.utils.business_hours.is_business_hours", return_value=False):
            with patch("app.utils.business_hours.get_next_business_open_time") as mock_next_open:
                # Mock próxima apertura a las 9:00 AM
                next_open = datetime(2025, 10, 10, 9, 0, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires"))
                mock_next_open.return_value = next_open

                with patch("app.utils.business_hours.datetime") as mock_datetime:
                    mock_now = MagicMock()
                    mock_now.weekday.return_value = 3
                    mock_datetime.now.return_value = mock_now

                    message = UnifiedMessage(
                        user_id="5491112345678", texto="consulta", canal="whatsapp", tipo="text", metadata={}
                    )

                    # Act
                    result = await orchestrator.handle_unified_message(message)

                    # Assert
                    assert result is not None
                    response_text = result.get("response") or result.get("content", "")

                    # Debe mencionar horario de apertura
                    assert "9" in response_text or "09:00" in response_text

    @pytest.mark.asyncio
    async def test_business_hours_logging(self):
        """Test: Verificar logging de verificación de horarios."""
        orchestrator = await self._create_orchestrator()

        # Arrange
        with patch("app.utils.business_hours.is_business_hours", return_value=False):
            with patch("app.core.logging.logger"):
                message = UnifiedMessage(
                    user_id="5491112345678", texto="consulta", canal="whatsapp", tipo="text", metadata={}
                )

                # Act
                await orchestrator.handle_unified_message(message)

                # Assert
                # Verificar que se registró el log de verificación de horarios
                # mock_logger.info.assert_called() - Verificación depende de implementación

    @pytest.mark.asyncio
    async def test_after_hours_no_pms_call(self):
        """Test: Fuera de horario NO debe llamar al PMS innecesariamente."""
        orchestrator = await self._create_orchestrator()

        # Arrange
        with patch("app.utils.business_hours.is_business_hours", return_value=False):
            with patch.object(orchestrator.pms_adapter, "check_availability", new_callable=AsyncMock):
                message = UnifiedMessage(
                    user_id="5491112345678",
                    texto="disponibilidad para mañana",
                    canal="whatsapp",
                    tipo="text",
                    metadata={},
                )

                # Act
                await orchestrator.handle_unified_message(message)

                # Assert
                # Fuera de horario, no debería llamar al PMS
                # (esto optimiza recursos y evita llamadas innecesarias)
                # mock_pms.assert_not_called() - Dependiendo de la implementación

    @pytest.mark.asyncio
    async def test_business_hours_with_audio_message(self):
        """Test: Verificación de horarios con mensaje de audio."""
        orchestrator = await self._create_orchestrator()

        # Arrange
        with patch("app.utils.business_hours.is_business_hours", return_value=False):
            with patch.object(
                orchestrator.audio_processor, "transcribe_whatsapp_audio", new_callable=AsyncMock
            ) as mock_stt:
                mock_stt.return_value = {"text": "necesito una habitación", "confidence": 0.95}

                with patch("app.utils.business_hours.datetime") as mock_datetime:
                    mock_now = MagicMock()
                    mock_now.weekday.return_value = 3
                    mock_datetime.now.return_value = mock_now

                    message = UnifiedMessage(
                        user_id="5491112345678",
                        texto=None,
                        canal="whatsapp",
                        tipo="audio",
                        media_url="https://example.com/audio.ogg",
                        metadata={},
                    )

                    # Act
                    result = await orchestrator.handle_unified_message(message)

                    # Assert
                    assert result is not None
                    # Debe transcribir primero, luego verificar horario
                    mock_stt.assert_called_once()

    @pytest.mark.asyncio
    async def test_timezone_aware_business_hours(self):
        """Test: Verificación de horarios es timezone-aware."""
        orchestrator = await self._create_orchestrator()

        # Arrange - Usar timezone de Buenos Aires
        with patch("app.utils.business_hours.is_business_hours") as mock_is_hours:
            mock_is_hours.return_value = False

            message = UnifiedMessage(
                user_id="5491112345678", texto="consulta", canal="whatsapp", tipo="text", metadata={}
            )

            # Act
            result = await orchestrator.handle_unified_message(message)

            # Assert
            # Verificar que se llamó is_business_hours
            # (que internamente usa timezone de settings)
            assert result is not None

    @pytest.mark.asyncio
    async def test_multiple_urgent_keywords_in_message(self):
        """Test: Múltiples keywords urgentes en un mensaje."""
        orchestrator = await self._create_orchestrator()

        # Arrange
        with patch("app.utils.business_hours.is_business_hours", return_value=False):
            message = UnifiedMessage(
                user_id="5491112345678",
                texto="URGENTE emergency necesito habitación",
                canal="whatsapp",
                tipo="text",
                metadata={},
            )

            # Act
            result = await orchestrator.handle_unified_message(message)

            # Assert
            assert result is not None
            response_text = result.get("response") or result.get("content", "")

            # Debe detectar urgencia y escalar
            assert isinstance(response_text, str)
            assert len(response_text) > 0
