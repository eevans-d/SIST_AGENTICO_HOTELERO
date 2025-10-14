import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.orchestrator import Orchestrator
from app.models.unified_message import UnifiedMessage


@pytest.mark.asyncio
async def test_guest_services_with_audio():
    """Prueba que el intent guest_services responda con audio cuando recibe un mensaje de voz."""
    # Mocks
    pms_adapter = AsyncMock()
    session_manager = AsyncMock()
    lock_service = AsyncMock()

    # Mock para audio_processor
    audio_processor = AsyncMock()
    audio_processor.generate_audio_response.return_value = b"audio_data_bytes"

    # Crear la instancia de Orchestrator con los mocks
    orchestrator = Orchestrator(pms_adapter=pms_adapter, session_manager=session_manager, lock_service=lock_service)
    orchestrator.template_service = MagicMock()
    orchestrator.audio_processor = audio_processor
    orchestrator.template_service.get_response.return_value = "Nuestros servicios para huéspedes incluyen..."

    # Crear un mensaje de audio para la prueba
    audio_message = UnifiedMessage(
        message_id="123",
        canal="whatsapp",
        user_id="1234567890",
        timestamp_iso="2023-01-01T00:00:00Z",
        tipo="audio",
        texto="¿Qué servicios ofrecen para los huéspedes?",
        media_url="https://example.com/audio.ogg",
    )

    # Crear una sesión y resultado NLP simulado
    session = {}
    nlp_result = {"intent": {"name": "guest_services", "confidence": 0.95}, "language": "es"}

    # Ejecutar la función
    result = await orchestrator.handle_intent(nlp_result, session, audio_message)

    # Verificar la respuesta
    assert result["response_type"] == "audio"
    assert "content" in result
    assert "text" in result["content"]
    assert "audio_data" in result["content"]

    # Verificar que se llamó al template service con el template correcto
    orchestrator.template_service.get_response.assert_called_once_with("guest_services")

    # Verificar que se generó audio
    audio_processor.generate_audio_response.assert_called_once()


@pytest.mark.asyncio
async def test_hotel_amenities_with_audio():
    """Prueba que el intent hotel_amenities responda con audio cuando recibe un mensaje de voz."""
    # Mocks
    pms_adapter = AsyncMock()
    session_manager = AsyncMock()
    lock_service = AsyncMock()

    # Mock para audio_processor con métricas y compresión
    audio_processor = AsyncMock()
    audio_processor.generate_audio_response.return_value = b"audio_data_bytes"
    audio_processor.get_audio_metrics.return_value = {
        "compression_ratio": 0.02,
        "original_size": 1500,
        "compressed_size": 36,
    }

    # Crear la instancia de Orchestrator con los mocks
    orchestrator = Orchestrator(pms_adapter=pms_adapter, session_manager=session_manager, lock_service=lock_service)
    orchestrator.template_service = MagicMock()
    orchestrator.audio_processor = audio_processor
    orchestrator.template_service.get_response.return_value = "Nuestras amenidades incluyen: piscina al aire libre..."

    # Crear un mensaje de audio para la prueba
    audio_message = UnifiedMessage(
        message_id="123",
        canal="whatsapp",
        user_id="1234567890",
        timestamp_iso="2023-01-01T00:00:00Z",
        tipo="audio",
        texto="¿Qué amenidades tiene el hotel?",
        media_url="https://example.com/audio.ogg",
    )

    # Crear una sesión y resultado NLP simulado
    session = {}
    nlp_result = {"intent": {"name": "hotel_amenities", "confidence": 0.95}, "language": "es"}

    # Ejecutar la función
    result = await orchestrator.handle_intent(nlp_result, session, audio_message)

    # Verificar la respuesta
    assert result["response_type"] == "audio"
    assert "content" in result
    assert "text" in result["content"]
    assert "audio_data" in result["content"]

    # Verificar que se llamó al template service con el template correcto
    orchestrator.template_service.get_response.assert_called_once_with("hotel_amenities")


@pytest.mark.asyncio
async def test_check_in_info_with_audio():
    """Prueba que el intent check_in_info responda con audio cuando recibe un mensaje de voz."""
    # Mocks
    pms_adapter = AsyncMock()
    session_manager = AsyncMock()
    lock_service = AsyncMock()

    # Mock para audio_processor
    audio_processor = AsyncMock()
    audio_processor.generate_audio_response.return_value = b"audio_data_bytes"

    # Crear la instancia de Orchestrator con los mocks
    orchestrator = Orchestrator(pms_adapter=pms_adapter, session_manager=session_manager, lock_service=lock_service)
    orchestrator.template_service = MagicMock()
    orchestrator.audio_processor = audio_processor
    orchestrator.template_service.get_response.return_value = "El check-in es a partir de las 15:00 horas..."

    # Crear un mensaje de audio para la prueba
    audio_message = UnifiedMessage(
        message_id="123",
        canal="whatsapp",
        user_id="1234567890",
        timestamp_iso="2023-01-01T00:00:00Z",
        tipo="audio",
        texto="¿A qué hora puedo hacer el check-in?",
        media_url="https://example.com/audio.ogg",
    )

    # Crear una sesión y resultado NLP simulado
    session = {}
    nlp_result = {"intent": {"name": "check_in_info", "confidence": 0.95}, "language": "es"}

    # Ejecutar la función
    result = await orchestrator.handle_intent(nlp_result, session, audio_message)

    # Verificar la respuesta
    assert result["response_type"] == "audio"
    assert "content" in result
    assert "text" in result["content"]
    assert "audio_data" in result["content"]

    # Verificar que se llamó al template service con el template correcto
    orchestrator.template_service.get_response.assert_called_once_with("check_in_info")


@pytest.mark.asyncio
async def test_check_out_info_with_audio():
    """Prueba que el intent check_out_info responda con audio cuando recibe un mensaje de voz."""
    # Mocks
    pms_adapter = AsyncMock()
    session_manager = AsyncMock()
    lock_service = AsyncMock()

    # Mock para audio_processor
    audio_processor = AsyncMock()
    audio_processor.generate_audio_response.return_value = b"audio_data_bytes"

    # Crear la instancia de Orchestrator con los mocks
    orchestrator = Orchestrator(pms_adapter=pms_adapter, session_manager=session_manager, lock_service=lock_service)
    orchestrator.template_service = MagicMock()
    orchestrator.audio_processor = audio_processor
    orchestrator.template_service.get_response.return_value = "El check-out es hasta las 12:00 horas..."

    # Crear un mensaje de audio para la prueba
    audio_message = UnifiedMessage(
        message_id="123",
        canal="whatsapp",
        user_id="1234567890",
        timestamp_iso="2023-01-01T00:00:00Z",
        tipo="audio",
        texto="¿Hasta qué hora puedo hacer el check-out?",
        media_url="https://example.com/audio.ogg",
    )

    # Crear una sesión y resultado NLP simulado
    session = {}
    nlp_result = {"intent": {"name": "check_out_info", "confidence": 0.95}, "language": "es"}

    # Ejecutar la función
    result = await orchestrator.handle_intent(nlp_result, session, audio_message)

    # Verificar la respuesta
    assert result["response_type"] == "audio"
    assert "content" in result
    assert "text" in result["content"]
    assert "audio_data" in result["content"]

    # Verificar que se llamó al template service con el template correcto
    orchestrator.template_service.get_response.assert_called_once_with("check_out_info")


@pytest.mark.asyncio
async def test_cancellation_policy_with_audio():
    """Prueba que el intent cancellation_policy responda con audio cuando recibe un mensaje de voz."""
    # Mocks
    pms_adapter = AsyncMock()
    session_manager = AsyncMock()
    lock_service = AsyncMock()

    # Mock para audio_processor
    audio_processor = AsyncMock()
    audio_processor.generate_audio_response.return_value = b"audio_data_bytes"

    # Crear la instancia de Orchestrator con los mocks
    orchestrator = Orchestrator(pms_adapter=pms_adapter, session_manager=session_manager, lock_service=lock_service)
    orchestrator.template_service = MagicMock()
    orchestrator.audio_processor = audio_processor
    orchestrator.template_service.get_response.return_value = "Nuestra política de cancelación permite..."

    # Crear un mensaje de audio para la prueba
    audio_message = UnifiedMessage(
        message_id="123",
        canal="whatsapp",
        user_id="1234567890",
        timestamp_iso="2023-01-01T00:00:00Z",
        tipo="audio",
        texto="¿Cuál es la política de cancelación?",
        media_url="https://example.com/audio.ogg",
    )

    # Crear una sesión y resultado NLP simulado
    session = {}
    nlp_result = {"intent": {"name": "cancellation_policy", "confidence": 0.95}, "language": "es"}

    # Ejecutar la función
    result = await orchestrator.handle_intent(nlp_result, session, audio_message)

    # Verificar la respuesta
    assert result["response_type"] == "audio"
    assert "content" in result
    assert "text" in result["content"]
    assert "audio_data" in result["content"]

    # Verificar que se llamó al template service con el template correcto
    orchestrator.template_service.get_response.assert_called_once_with("cancellation_policy")


@pytest.mark.asyncio
async def test_new_intents_with_text_messages():
    """Prueba que los nuevos intents respondan correctamente con mensajes de texto (sin audio)."""
    # Mocks
    pms_adapter = AsyncMock()
    session_manager = AsyncMock()
    lock_service = AsyncMock()

    # Mock para audio_processor (no debería ser llamado)
    audio_processor = AsyncMock()

    # Crear la instancia de Orchestrator con los mocks
    orchestrator = Orchestrator(pms_adapter=pms_adapter, session_manager=session_manager, lock_service=lock_service)
    orchestrator.template_service = MagicMock()
    orchestrator.audio_processor = audio_processor

    # Lista de intents a probar
    intents_to_test = [
        ("guest_services", "¿Qué servicios ofrecen?"),
        ("hotel_amenities", "¿Qué amenidades tiene el hotel?"),
        ("check_in_info", "¿A qué hora es el check-in?"),
        ("check_out_info", "¿Hasta qué hora puedo hacer check-out?"),
        ("cancellation_policy", "¿Cuál es la política de cancelación?"),
    ]

    for intent_name, message_text in intents_to_test:
        # Reset mocks
        orchestrator.template_service.reset_mock()
        audio_processor.reset_mock()
        orchestrator.template_service.get_response.return_value = f"Respuesta para {intent_name}"

        # Crear un mensaje de texto para la prueba
        text_message = UnifiedMessage(
            message_id="123",
            canal="whatsapp",
            user_id="1234567890",
            timestamp_iso="2023-01-01T00:00:00Z",
            tipo="text",
            texto=message_text,
        )

        # Crear una sesión y resultado NLP simulado
        session = {}
        nlp_result = {"intent": {"name": intent_name, "confidence": 0.95}, "language": "es"}

        # Ejecutar la función
        result = await orchestrator.handle_intent(nlp_result, session, text_message)

        # Verificar la respuesta
        assert result["response_type"] == "text", f"Failed for intent {intent_name}"
        assert "content" in result, f"Failed for intent {intent_name}"

        # Verificar que se llamó al template service con el template correcto
        orchestrator.template_service.get_response.assert_called_once_with(intent_name)

        # Verificar que NO se generó audio
        audio_processor.generate_audio_response.assert_not_called()


@pytest.mark.asyncio
async def test_audio_whisper_transcription():
    """Prueba la transcripción de audio con Whisper."""
    # Mocks para la prueba
    audio_processor = AsyncMock()
    audio_processor.transcribe_whatsapp_audio.return_value = {
        "text": "Me gustaría saber si tienen habitaciones disponibles",
        "confidence": 0.92,
        "success": True,
        "language": "es",
        "duration": 2.3,
    }

    # Mock de NLP Engine para procesar la transcripción
    nlp_engine = AsyncMock()
    nlp_engine.analyze_text.return_value = {
        "intent": {"name": "check_availability", "confidence": 0.89},
        "entities": [{"type": "date", "value": "mañana", "confidence": 0.87}],
        "language": "es",
    }

    # Mensaje de audio para procesar
    audio_message = UnifiedMessage(
        message_id="234",
        canal="whatsapp",
        user_id="1234567890",
        timestamp_iso="2023-01-01T00:00:00Z",
        tipo="audio",
        texto="",  # Sin texto inicialmente
        media_url="https://example.com/audio_mensaje.ogg",
    )

    # Orquestador con mocks
    orchestrator = AsyncMock()
    orchestrator.audio_processor = audio_processor
    orchestrator.nlp_engine = nlp_engine

    # Simular el flujo de procesamiento de audio
    # 1. Transcribir audio
    transcription = await audio_processor.transcribe_whatsapp_audio(audio_message.media_url)

    # 2. Actualizar mensaje con texto transcrito
    audio_message.texto = transcription["text"]

    # 3. Procesar con NLP
    nlp_result = await nlp_engine.analyze_text(audio_message.texto)

    # Verificaciones
    assert audio_message.texto == "Me gustaría saber si tienen habitaciones disponibles"
    assert nlp_result["intent"]["name"] == "check_availability"
    assert audio_processor.transcribe_whatsapp_audio.called
    assert nlp_engine.analyze_text.called


@pytest.mark.asyncio
async def test_audio_espeak_synthesis():
    """Prueba la síntesis de voz con eSpeak."""
    # Mock para audio_processor
    audio_processor = AsyncMock()
    audio_data = b"audio_bytes_data_espeak_synthesis"
    audio_processor.synthesize_text.return_value = {
        "audio_data": audio_data,
        "format": "ogg",
        "duration": 3.2,
        "success": True,
    }

    # Crear mensaje y texto para la respuesta
    text_response = "Su reserva ha sido confirmada para el viernes 15 de octubre, habitación superior con vista al mar."

    # Simular la síntesis de voz
    result = await audio_processor.synthesize_text(text_response)

    # Verificaciones
    assert result["success"] is True
    assert result["audio_data"] == audio_data
    assert result["format"] == "ogg"
    assert isinstance(result["duration"], float)
    assert audio_processor.synthesize_text.called


@pytest.mark.asyncio
async def test_audio_generation_error_fallback():
    """Prueba que si falla la generación de audio, el sistema haga fallback a respuesta de texto."""
    # Mocks
    pms_adapter = AsyncMock()
    session_manager = AsyncMock()
    lock_service = AsyncMock()

    # Mock para audio_processor que falla
    audio_processor = AsyncMock()
    audio_processor.generate_audio_response.side_effect = Exception("Audio generation failed")

    # Crear la instancia de Orchestrator con los mocks
    orchestrator = Orchestrator(pms_adapter=pms_adapter, session_manager=session_manager, lock_service=lock_service)
    orchestrator.template_service = MagicMock()
    orchestrator.audio_processor = audio_processor
    orchestrator.template_service.get_response.return_value = "Nuestros servicios incluyen..."

    # Crear un mensaje de audio para la prueba
    audio_message = UnifiedMessage(
        message_id="123",
        canal="whatsapp",
        user_id="1234567890",
        timestamp_iso="2023-01-01T00:00:00Z",
        tipo="audio",
        texto="¿Qué servicios ofrecen?",
        media_url="https://example.com/audio.ogg",
    )

    # Crear una sesión y resultado NLP simulado
    session = {}
    nlp_result = {"intent": {"name": "guest_services", "confidence": 0.95}, "language": "es"}

    # Ejecutar la función
    result = await orchestrator.handle_intent(nlp_result, session, audio_message)

    # Verificar que hace fallback a respuesta de texto
    assert result["response_type"] == "text"
    assert "content" in result

    # Verificar que se intentó generar audio
    audio_processor.generate_audio_response.assert_called_once()
