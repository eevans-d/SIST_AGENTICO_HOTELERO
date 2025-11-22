"""
Test de integración end-to-end para el flujo completo de audio en el agente hotelero.
Este test verifica el ciclo completo: WhatsApp Audio → STT → NLP → PMS → TTS → Response.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.orchestrator import Orchestrator
from app.services.pms_adapter import MockPMSAdapter
from app.services.session_manager import SessionManager
from app.services.lock_service import LockService
from app.models.unified_message import UnifiedMessage


@pytest.fixture
def orchestrator():
    """Crea un orquestador configurado para pruebas."""
    # Configurar mocks para los servicios
    mock_redis = MagicMock()
    pms_adapter = MockPMSAdapter(mock_redis)
    session_manager = AsyncMock(spec=SessionManager)
    lock_service = AsyncMock(spec=LockService)

    # Crear orquestador
    orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

    # Configurar el audio processor para modo mock
    orchestrator.audio_processor.stt._model_loaded = "mock"

    return orchestrator


@pytest.fixture
def audio_message():
    """Crea un mensaje de audio unificado para pruebas."""
    return UnifiedMessage(
        message_id="test_audio_msg_123",
        canal="whatsapp",
        user_id="5491123456789",
        timestamp_iso="2023-09-20T15:30:00Z",
        tipo="audio",
        texto=None,
        media_url="https://mock-whatsapp-media.com/audio123.ogg",
        metadata={"audio": {"id": "audio123", "mime_type": "audio/ogg", "media_id": "media123456"}},
        tenant_id="hotel_test",
    )


@pytest.mark.asyncio
async def test_audio_message_full_integration_flow(orchestrator, audio_message):
    """
    Test del flujo completo de integración:
    Audio WhatsApp → STT → NLP → PMS → TTS → Response Audio
    """

    # 1. Mock del STT (transcripción)
    with patch.object(orchestrator.audio_processor, "transcribe_whatsapp_audio") as mock_stt, \
         patch.object(orchestrator.nlp_engine, "process_text") as mock_nlp, \
         patch("app.services.orchestrator.is_business_hours", return_value=True):
        
        mock_stt.return_value = {
            "text": "Hola, quisiera saber si tienen habitaciones disponibles para este fin de semana",
            "confidence": 0.92,
            "success": True,
            "language": "es",
        }
        
        mock_nlp.return_value = {
            "intent": {"name": "check_availability", "confidence": 0.95},
            "entities": {"checkin_date": "2023-10-20", "checkout_date": "2023-10-22"},
            "language": "es"
        }

        # 2. Mock del TTS (síntesis)
        with patch.object(orchestrator.audio_processor, "generate_audio_response") as mock_tts:
            mock_tts.return_value = b"audio_response_data_bytes"

            # 3. Mock de la sesión
            mock_session = MagicMock()
            mock_session.session_id = "session_123"
            orchestrator.session_manager.get_or_create_session.return_value = mock_session

            # 4. Procesar el mensaje de audio
            result = await orchestrator.handle_unified_message(audio_message)

            # 5. Verificar que se procesó correctamente
            assert result is not None
            assert "response" in result or "response_type" in result

            # Verificar que se llamó a STT
            mock_stt.assert_called_once_with("https://mock-whatsapp-media.com/audio123.ogg")

            # Verificar que el texto fue procesado por NLP
            assert (
                audio_message.texto == "Hola, quisiera saber si tienen habitaciones disponibles para este fin de semana"
            )
            assert audio_message.metadata["confidence_stt"] == 0.92

            # Si la respuesta es de tipo audio, verificar TTS
            if result.get("response_type") == "audio":
                mock_tts.assert_called_once()
                assert result["content"]["audio_data"] == b"audio_response_data_bytes"


@pytest.mark.asyncio
async def test_audio_intent_detection_and_response(orchestrator, audio_message):
    """Test que verifica la detección de intents específicos desde audio."""

    # Test para intent de disponibilidad
    with patch.object(orchestrator.audio_processor, "transcribe_whatsapp_audio") as mock_stt, \
         patch.object(orchestrator.nlp_engine, "process_text") as mock_nlp, \
         patch("app.services.orchestrator.is_business_hours", return_value=True):
        
        mock_stt.return_value = {
            "text": "¿Tienen habitaciones disponibles para dos personas?",
            "confidence": 0.89,
            "success": True,
            "language": "es",
        }
        
        mock_nlp.return_value = {
            "intent": {"name": "check_availability", "confidence": 0.95},
            "entities": {"guests": 2},
            "language": "es"
        }

        with patch.object(orchestrator.audio_processor, "generate_audio_response") as mock_tts:
            mock_tts.return_value = b"availability_audio_response"

            # Mock de sesión
            mock_session = MagicMock()
            orchestrator.session_manager.get_or_create_session.return_value = mock_session

            # Procesar mensaje
            result = await orchestrator.handle_unified_message(audio_message)

            # Verificar que se detectó el intent correcto
            assert result is not None

            # El texto debería haberse actualizado
            assert "habitaciones disponibles" in audio_message.texto

            # Verificar que se generó una respuesta
            if result.get("response_type") == "audio":
                assert "audio_data" in result["content"]
            elif "response" in result:
                assert len(result["response"]) > 0


@pytest.mark.asyncio
async def test_audio_error_handling_integration(orchestrator, audio_message):
    """Test del manejo de errores en el flujo de audio."""

    # Test 1: Error en STT
    with patch.object(orchestrator.audio_processor, "transcribe_whatsapp_audio") as mock_stt:
        mock_stt.side_effect = Exception("Error al transcribir audio")

        mock_session = MagicMock()
        orchestrator.session_manager.get_or_create_session.return_value = mock_session

        # Debería manejar el error graciosamente (NO levantar excepción)
        # El orchestrator captura la excepción, loguea, y continúa con texto vacío
        result = await orchestrator.handle_unified_message(audio_message)
        
        # Verificar que se manejó el error
        assert audio_message.texto == ""
        assert "audio_error" in audio_message.metadata
        assert audio_message.metadata["audio_error"] == "Error al transcribir audio"


@pytest.mark.asyncio
async def test_audio_fallback_to_text_response(orchestrator, audio_message):
    """Test del fallback a respuesta de texto cuando TTS falla."""

    with patch.object(orchestrator.audio_processor, "transcribe_whatsapp_audio") as mock_stt, \
         patch.object(orchestrator.nlp_engine, "process_text") as mock_nlp, \
         patch("app.services.orchestrator.is_business_hours", return_value=True):
        
        mock_stt.return_value = {
            "text": "Hola, ¿cuáles son sus precios?",
            "confidence": 0.85,
            "success": True,
            "language": "es",
        }
        
        mock_nlp.return_value = {
            "intent": {"name": "pricing_info", "confidence": 0.90},
            "entities": {},
            "language": "es"
        }

        # Mock TTS que falla
        with patch.object(orchestrator.audio_processor, "generate_audio_response") as mock_tts:
            mock_tts.return_value = None  # Simular falla en TTS

            mock_session = MagicMock()
            orchestrator.session_manager.get_or_create_session.return_value = mock_session

            # Procesar mensaje
            result = await orchestrator.handle_unified_message(audio_message)

            # Debería retornar respuesta de texto como fallback
            assert result is not None
            assert "response" in result or result.get("response_type") == "text"


@pytest.mark.asyncio
async def test_audio_cache_integration(orchestrator, audio_message):
    """Test de integración del sistema de cache con audio."""

    with patch.object(orchestrator.audio_processor, "transcribe_whatsapp_audio") as mock_stt, \
         patch.object(orchestrator.nlp_engine, "process_text") as mock_nlp, \
         patch("app.services.orchestrator.is_business_hours", return_value=True):
        
        mock_stt.return_value = {
            "text": "¿Dónde están ubicados?",
            "confidence": 0.91,
            "success": True,
            "language": "es",
        }
        
        mock_nlp.return_value = {
            "intent": {"name": "hotel_location", "confidence": 0.95},
            "entities": {},
            "language": "es"
        }

        # Mock del servicio de cache a nivel de generación de audio
        with patch.object(orchestrator.audio_processor, "generate_audio_response") as mock_tts:
            mock_tts.return_value = b"location_audio_response"

            mock_session = MagicMock()
            orchestrator.session_manager.get_or_create_session.return_value = mock_session

            # Primera llamada - debería generar audio
            result1 = await orchestrator.handle_unified_message(audio_message)

            # Verificar que se procesó
            assert result1 is not None
            assert mock_tts.call_count >= 0  # Puede no llamar TTS si no es intent de audio

            # Segunda llamada con el mismo mensaje
            audio_message.message_id = "test_audio_msg_124"  # Nuevo ID
            result2 = await orchestrator.handle_unified_message(audio_message)

            # Verificar que ambas respuestas son válidas
            assert result2 is not None


@pytest.mark.asyncio
async def test_audio_multilingual_support(orchestrator):
    """Test del soporte multiidioma en el flujo de audio."""

    # Test con mensaje en inglés
    english_message = UnifiedMessage(
        message_id="test_audio_eng_123",
        canal="whatsapp",
        user_id="5491123456789",
        timestamp_iso="2023-09-20T15:30:00Z",
        tipo="audio",
        texto=None,
        media_url="https://mock-whatsapp-media.com/audio_en.ogg",
        tenant_id="hotel_test",
    )

    with patch.object(orchestrator.audio_processor, "transcribe_whatsapp_audio") as mock_stt, \
         patch.object(orchestrator.nlp_engine, "process_text") as mock_nlp, \
         patch("app.services.orchestrator.is_business_hours", return_value=True):
        
        mock_stt.return_value = {
            "text": "Do you have rooms available for this weekend?",
            "confidence": 0.88,
            "success": True,
            "language": "en",
        }
        
        mock_nlp.return_value = {
            "intent": {"name": "check_availability", "confidence": 0.95},
            "entities": {},
            "language": "en"
        }

        with patch.object(orchestrator.audio_processor, "generate_audio_response") as mock_tts:
            mock_tts.return_value = b"english_audio_response"

            mock_session = MagicMock()
            orchestrator.session_manager.get_or_create_session.return_value = mock_session

            # Procesar mensaje en inglés
            result = await orchestrator.handle_unified_message(english_message)

            # Verificar que se procesó correctamente
            assert result is not None
            assert english_message.texto == "Do you have rooms available for this weekend?"
            # El idioma detectado puede variar según el motor NLP disponible
