import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.orchestrator import Orchestrator
from app.models.unified_message import UnifiedMessage


@pytest.mark.asyncio
async def test_make_reservation_with_audio():
    """Prueba que el intent make_reservation responda con audio cuando recibe un mensaje de voz."""
    # Mocks
    pms_adapter = AsyncMock()
    session_manager = AsyncMock()
    lock_service = AsyncMock()
    
    # Mock para audio_processor
    audio_processor = AsyncMock()
    audio_processor.generate_audio_response.return_value = b"audio_data_bytes"
    
    # Crear la instancia de Orchestrator con los mocks
    orchestrator = Orchestrator(
        pms_adapter=pms_adapter,
        session_manager=session_manager,
        lock_service=lock_service
    )
    orchestrator.template_service = MagicMock()
    orchestrator.audio_processor = audio_processor
    orchestrator.template_service.get_response.return_value = "Instrucciones para reserva: deposite $6000..."
    
    # Crear un mensaje de audio para la prueba
    audio_message = UnifiedMessage(
        message_id="123",
        canal="whatsapp",
        user_id="1234567890",
        timestamp_iso="2023-01-01T00:00:00Z",
        tipo="audio",
        texto="Quiero hacer una reserva para la próxima semana",
        media_url="https://example.com/audio.ogg"
    )
    
    # Crear una sesión y resultado NLP simulado
    session = {}
    nlp_result = {
        "intent": {"name": "make_reservation", "confidence": 0.95},
        "language": "es"
    }
    
    # Ejecutar la función
    result = await orchestrator.handle_intent(nlp_result, session, audio_message)
    
    # Verificar la respuesta
    assert result["response_type"] == "audio"
    assert "content" in result
    assert "text" in result["content"]
    assert "audio_data" in result["content"]
    
    # Verificar que se actualizó la sesión
    session_manager.update_session.assert_called_once()
    assert "reservation_pending" in session
    assert session["reservation_pending"]


@pytest.mark.asyncio
async def test_make_reservation_text_only():
    """Prueba que el intent make_reservation responda con texto cuando recibe un mensaje de texto."""
    # Mocks
    pms_adapter = AsyncMock()
    session_manager = AsyncMock()
    lock_service = AsyncMock()
    
    # Mock para audio_processor (no debería ser llamado)
    audio_processor = AsyncMock()
    
    # Crear la instancia de Orchestrator con los mocks
    orchestrator = Orchestrator(
        pms_adapter=pms_adapter,
        session_manager=session_manager,
        lock_service=lock_service
    )
    orchestrator.template_service = MagicMock()
    orchestrator.audio_processor = audio_processor
    orchestrator.template_service.get_response.return_value = "Instrucciones para reserva: deposite $6000..."
    
    # Crear un mensaje de texto para la prueba
    text_message = UnifiedMessage(
        message_id="123",
        canal="whatsapp",
        user_id="1234567890",
        timestamp_iso="2023-01-01T00:00:00Z",
        tipo="text",
        texto="Quiero hacer una reserva para la próxima semana"
    )
    
    # Crear una sesión y resultado NLP simulado
    session = {}
    nlp_result = {
        "intent": {"name": "make_reservation", "confidence": 0.95},
        "language": "es"
    }
    
    # Ejecutar la función
    result = await orchestrator.handle_intent(nlp_result, session, text_message)
    
    # Verificar la respuesta
    assert result["response_type"] == "text"
    assert "content" in result
    
    # Verificar que se actualizó la sesión
    session_manager.update_session.assert_called_once()
    assert "reservation_pending" in session
    assert session["reservation_pending"]
    
    # Verificar que no se llamó al generador de audio
    audio_processor.generate_audio_response.assert_not_called()


@pytest.mark.asyncio
async def test_show_room_options_with_audio():
    """Prueba que el intent show_room_options envíe audio + lista interactiva cuando recibe un mensaje de voz."""
    # Mocks
    pms_adapter = AsyncMock()
    session_manager = AsyncMock()
    lock_service = AsyncMock()
    
    # Mock para audio_processor
    audio_processor = AsyncMock()
    audio_processor.generate_audio_response.return_value = b"audio_data_bytes"
    
    # Mock para template_service
    template_service = MagicMock()
    template_service.get_interactive_list.return_value = {
        "header_text": "Opciones de Habitaciones",
        "body_text": "Estas son nuestras opciones disponibles:",
        "list_sections": [{"rows": [{"id": "room_single", "title": "Individual"}]}],
        "list_button_text": "Ver opciones"
    }
    
    # Crear la instancia de Orchestrator con los mocks
    orchestrator = Orchestrator(
        pms_adapter=pms_adapter,
        session_manager=session_manager,
        lock_service=lock_service
    )
    orchestrator.template_service = template_service
    orchestrator.audio_processor = audio_processor
    
    # Crear un mensaje de audio para la prueba
    audio_message = UnifiedMessage(
        message_id="123",
        canal="whatsapp",
        user_id="1234567890",
        timestamp_iso="2023-01-01T00:00:00Z",
        tipo="audio",
        texto="Muéstrame las habitaciones disponibles",
        media_url="https://example.com/audio.ogg"
    )
    
    # Crear una sesión y resultado NLP simulado
    session = {}
    nlp_result = {
        "intent": {"name": "show_room_options", "confidence": 0.95},
        "language": "es"
    }
    
    # Ejecutar la función
    result = await orchestrator.handle_intent(nlp_result, session, audio_message)
    
    # Verificar la respuesta
    assert result["response_type"] == "audio"
    assert "content" in result
    assert "text" in result["content"]
    assert "audio_data" in result["content"]
    assert "follow_up" in result["content"]
    assert result["content"]["follow_up"]["type"] == "interactive_list"


@pytest.mark.asyncio
async def test_default_fallback_with_audio():
    """Prueba que el fallback por defecto responda con audio cuando recibe un mensaje de voz."""
    # Mocks
    pms_adapter = AsyncMock()
    session_manager = AsyncMock()
    lock_service = AsyncMock()
    
    # Mock para audio_processor
    audio_processor = AsyncMock()
    audio_processor.generate_audio_response.return_value = b"audio_data_bytes"
    
    # Crear la instancia de Orchestrator con los mocks
    orchestrator = Orchestrator(
        pms_adapter=pms_adapter,
        session_manager=session_manager,
        lock_service=lock_service
    )
    orchestrator.audio_processor = audio_processor
    
    # Crear un mensaje de audio para la prueba
    audio_message = UnifiedMessage(
        message_id="123",
        canal="whatsapp",
        user_id="1234567890",
        timestamp_iso="2023-01-01T00:00:00Z",
        tipo="audio",
        texto="Este es un mensaje sin un intent claro",
        media_url="https://example.com/audio.ogg"
    )
    
    # Crear una sesión y resultado NLP simulado
    session = {}
    nlp_result = {
        "intent": {"name": "unknown_intent", "confidence": 0.3},
        "language": "es"
    }
    
    # Ejecutar la función
    result = await orchestrator.handle_intent(nlp_result, session, audio_message)
    
    # Verificar la respuesta
    assert result["response_type"] == "audio"
    assert "content" in result
    assert "text" in result["content"]
    assert "audio_data" in result["content"]