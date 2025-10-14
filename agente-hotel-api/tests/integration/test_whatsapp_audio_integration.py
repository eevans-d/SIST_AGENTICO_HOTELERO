"""
Tests de integración entre el servicio de audio y el cliente de WhatsApp.
Este módulo prueba la interacción completa entre el procesador de audio
y el cliente de WhatsApp para mensajes de audio.
"""

import pytest
from unittest.mock import AsyncMock
import os
import tempfile
from pathlib import Path

from app.services.audio_processor import AudioProcessor
from app.services.whatsapp_client import WhatsAppMetaClient
from app.models.unified_message import UnifiedMessage
from app.exceptions.audio_exceptions import AudioDownloadError, AudioProcessingError


@pytest.fixture
async def whatsapp_client():
    """Mock del cliente de WhatsApp."""
    client = AsyncMock(spec=WhatsAppMetaClient)

    # Mock para download_media
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ogg")
    temp_file.write(b"mock_audio_content")
    temp_file.close()
    client.download_media.return_value = Path(temp_file.name)

    # Mock para send_audio_message
    client.send_audio_message.return_value = {"message_id": "whatsapp_message_123456", "status": "sent"}

    yield client

    # Limpieza
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


@pytest.fixture
async def audio_processor():
    """Mock del procesador de audio."""
    processor = AsyncMock(spec=AudioProcessor)

    # Mock para transcribe_audio_file
    processor.transcribe_audio_file.return_value = {
        "text": "Hola, quisiera información sobre reservas",
        "confidence": 0.92,
        "success": True,
        "language": "es",
    }

    # Mock para generate_audio_response
    processor.generate_audio_response.return_value = b"generated_audio_data"

    return processor


@pytest.mark.asyncio
async def test_whatsapp_audio_download_integration(whatsapp_client):
    """Test que verifica la descarga de audio desde WhatsApp."""
    # Crear mensaje unificado de prueba con audio
    unified_message = UnifiedMessage(
        message_id="msg123",
        canal="whatsapp",
        user_id="5491112345678",
        timestamp_iso="2023-09-20T12:00:00Z",
        tipo="audio",
        texto=None,
        media_url="https://whatsapp-media.com/audio123.ogg",
        metadata={"audio": {"id": "audio123", "mime_type": "audio/ogg", "media_id": "media123456"}},
        tenant_id="hotel1",
    )

    # Descargar audio
    audio_path = await whatsapp_client.download_media(unified_message.metadata["audio"]["media_id"])

    # Verificaciones
    assert audio_path.exists()
    assert audio_path.suffix == ".ogg"
    assert os.path.getsize(audio_path) > 0

    # Verificar que se llamó correctamente
    whatsapp_client.download_media.assert_called_once_with(unified_message.metadata["audio"]["media_id"])


@pytest.mark.asyncio
async def test_whatsapp_audio_download_error_handling(whatsapp_client):
    """Test que verifica el manejo de errores en la descarga de audio."""
    # Configurar mock para fallar
    whatsapp_client.download_media.side_effect = AudioDownloadError("Error al descargar audio: status code 404")

    # Verificar que se propaga la excepción
    with pytest.raises(AudioDownloadError):
        await whatsapp_client.download_media("invalid_media_id")


@pytest.mark.asyncio
async def test_whatsapp_audio_send_integration(whatsapp_client):
    """Test que verifica el envío de audio mediante WhatsApp."""
    # Audio de prueba
    audio_data = b"test_audio_bytes"
    recipient = "5491123456789"

    # Enviar audio
    result = await whatsapp_client.send_audio_message(recipient, audio_data)

    # Verificaciones
    assert result["status"] == "sent"
    assert "message_id" in result

    # Verificar que se llamó correctamente
    whatsapp_client.send_audio_message.assert_called_once_with(recipient, audio_data)


@pytest.mark.asyncio
async def test_end_to_end_whatsapp_audio_flow(whatsapp_client, audio_processor):
    """Test que verifica el flujo completo: recepción → procesamiento → respuesta."""
    # Configurar mensaje de entrada
    unified_message = UnifiedMessage(
        message_id="msg123",
        canal="whatsapp",
        user_id="5491112345678",
        timestamp_iso="2023-09-20T12:00:00Z",
        tipo="audio",
        texto=None,
        media_url="https://whatsapp-media.com/audio123.ogg",
        metadata={"audio": {"id": "audio123", "mime_type": "audio/ogg", "media_id": "media123456"}},
        tenant_id="hotel1",
    )

    # 1. Simular descarga de audio
    audio_path = await whatsapp_client.download_media(unified_message.metadata["audio"]["media_id"])

    # 2. Simular transcripción
    transcription = await audio_processor.transcribe_audio_file(audio_path)
    assert transcription["success"] is True
    assert "Hola, quisiera información" in transcription["text"]

    # 3. Simular generación de respuesta (texto → audio)
    text_response = "Gracias por contactarnos. Tenemos habitaciones disponibles."
    audio_response = await audio_processor.generate_audio_response(text_response)
    assert audio_response is not None

    # 4. Simular envío de respuesta
    send_result = await whatsapp_client.send_audio_message(unified_message.user_id, audio_response)

    assert send_result["status"] == "sent"

    # Verificar secuencia completa de llamadas
    assert whatsapp_client.download_media.call_count == 1
    assert audio_processor.transcribe_audio_file.call_count == 1
    assert audio_processor.generate_audio_response.call_count == 1
    assert whatsapp_client.send_audio_message.call_count == 1


@pytest.mark.asyncio
async def test_whatsapp_error_handling_with_fallback(whatsapp_client, audio_processor):
    """Test del manejo de errores con fallback a mensaje de texto."""
    # Mock del cliente con error en envío de audio
    whatsapp_client.send_audio_message.side_effect = AudioProcessingError("Error al enviar mensaje de audio")
    whatsapp_client.send_message.return_value = {"message_id": "text_fallback_123", "status": "sent"}

    # Configurar mensaje y respuesta
    recipient = "5491123456789"
    text_response = "Este mensaje debería enviarse como audio, pero fallará y usará texto."
    audio_data = await audio_processor.generate_audio_response(text_response)

    # Intentar enviar como audio (fallará)
    try:
        await whatsapp_client.send_audio_message(recipient, audio_data)
    except AudioProcessingError:
        # Fallback a mensaje de texto
        fallback_result = await whatsapp_client.send_message(recipient, text_response)
        assert fallback_result["status"] == "sent"

    # Verificar que se intentó primero audio y luego texto
    whatsapp_client.send_audio_message.assert_called_once()
    whatsapp_client.send_message.assert_called_once_with(recipient, text_response)
