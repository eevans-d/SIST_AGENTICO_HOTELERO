import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.orchestrator import Orchestrator
from app.models.unified_message import UnifiedMessage


@pytest.mark.asyncio
async def test_handle_hotel_location_text():
    """Prueba que el manejo de la intención hotel_location funcione para mensajes de texto."""
    # Mocks
    pms_adapter = AsyncMock()
    session_manager = AsyncMock()
    lock_service = AsyncMock()

    # Mock para template_service
    template_service = MagicMock()
    template_service.get_location.return_value = {
        "latitude": 19.4326,
        "longitude": -99.1332,
        "name": "Hotel Test",
        "address": "Av. Principal 123",
    }

    # Crear la instancia de Orchestrator con los mocks
    orchestrator = Orchestrator(pms_adapter=pms_adapter, session_manager=session_manager, lock_service=lock_service)
    orchestrator.template_service = template_service

    # Crear un mensaje de texto para la prueba
    text_message = UnifiedMessage(
        message_id="123",
        canal="whatsapp",
        user_id="1234567890",
        timestamp_iso="2023-01-01T00:00:00Z",
        tipo="text",
        texto="¿Dónde está ubicado el hotel?",
    )

    # Crear una sesión y resultado NLP simulado
    session = {}
    nlp_result = {"intent": {"name": "hotel_location", "confidence": 0.95}, "language": "es"}

    # Ejecutar la función
    result = await orchestrator.handle_intent(nlp_result, session, text_message)

    # Verificar la respuesta
    assert result["response_type"] == "location"
    assert "content" in result
    assert "latitude" in result["content"]
    assert "longitude" in result["content"]


@pytest.mark.asyncio
async def test_handle_hotel_location_audio():
    """Prueba que el manejo de la intención hotel_location funcione para mensajes de audio."""
    # Mocks
    pms_adapter = AsyncMock()
    session_manager = AsyncMock()
    lock_service = AsyncMock()

    # Mock para template_service
    template_service = MagicMock()
    template_service.get_audio_with_location.return_value = {
        "text": "Nuestro hotel está ubicado en Av. Principal 123, Centro, Ciudad. ¡Esperamos tu visita!",
        "audio_data": b"audio_data_bytes",
        "location": {"latitude": 19.4326, "longitude": -99.1332, "name": "Hotel Test", "address": "Av. Principal 123"},
    }

    # Mock para audio_processor
    audio_processor = AsyncMock()
    audio_processor.generate_audio_response.return_value = b"audio_data_bytes"

    # Crear la instancia de Orchestrator con los mocks
    orchestrator = Orchestrator(pms_adapter=pms_adapter, session_manager=session_manager, lock_service=lock_service)
    orchestrator.template_service = template_service
    orchestrator.audio_processor = audio_processor

    # Crear un mensaje de audio para la prueba
    audio_message = UnifiedMessage(
        message_id="123",
        canal="whatsapp",
        user_id="1234567890",
        timestamp_iso="2023-01-01T00:00:00Z",
        tipo="audio",
        texto="¿Dónde está ubicado el hotel?",
        media_url="https://example.com/audio.ogg",
    )

    # Crear una sesión y resultado NLP simulado
    session = {}
    nlp_result = {"intent": {"name": "hotel_location", "confidence": 0.95}, "language": "es"}

    # Ejecutar la función
    result = await orchestrator.handle_intent(nlp_result, session, audio_message)

    # Verificar la respuesta
    assert result["response_type"] == "audio_with_location"
    assert "content" in result
    assert "text" in result["content"]
    assert "audio_data" in result["content"]
    assert "location" in result["content"]
    assert "latitude" in result["content"]["location"]
    assert "longitude" in result["content"]["location"]
