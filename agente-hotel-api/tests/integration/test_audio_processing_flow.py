"""
Tests integrados del flujo completo de audio: STT → NLP → TTS con caching.
Este test verifica el ciclo completo de procesamiento de audio desde la entrada
hasta la respuesta, incluyendo cache y métricas.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os
from pathlib import Path
import tempfile

from app.services.audio_processor import AudioProcessor, WhisperSTT, ESpeakTTS
from app.services.audio_cache_service import AudioCacheService
from app.services.audio_metrics import AudioMetrics
from app.services.nlp_engine import NLPEngine
from app.exceptions.audio_exceptions import AudioProcessingError


@pytest.fixture
async def audio_processor():
    """Crea un procesador de audio para pruebas."""
    processor = AudioProcessor()
    # Override para usar modo mock
    processor.stt._model_loaded = "mock"
    processor.stt.model = MagicMock()

    # Mock del servicio de cache
    mock_cache = MagicMock(spec=AudioCacheService)
    mock_cache.get.return_value = None  # Siempre miss de cache
    mock_cache.set.return_value = True
    processor.cache_service = mock_cache

    return processor


@pytest.fixture
def mock_audio_path():
    """Crea un archivo de audio temporal para pruebas."""
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp.write(b"mock_audio_data")
        path = Path(tmp.name)

    yield path

    # Limpieza: eliminar archivo temporal
    if path.exists():
        os.unlink(path)


@pytest.mark.asyncio
async def test_audio_processing_flow_full_cycle(audio_processor, mock_audio_path):
    """Test de flujo completo: WhatsApp audio → STT → NLP → TTS → response."""

    # 1. Preparar mock para transcripción
    with patch.object(WhisperSTT, "transcribe") as mock_transcribe:
        mock_transcribe.return_value = {
            "text": "¿Tienen habitaciones disponibles para este fin de semana?",
            "confidence": 0.95,
            "success": True,
            "language": "es",
            "duration": 1.5,
        }

        # 2. Simular la transcripción
        transcription = await audio_processor.transcribe_audio_file(mock_audio_path)

        # Verificar la transcripción
        assert transcription["success"] is True
        assert "¿Tienen habitaciones disponibles" in transcription["text"]
        assert transcription["confidence"] > 0.9

        # 3. Procesar con NLP (mock)
        nlp_engine = AsyncMock(spec=NLPEngine)
        nlp_engine.analyze_text.return_value = {
            "intent": {"name": "check_availability", "confidence": 0.92},
            "entities": [{"type": "date", "value": "fin de semana", "confidence": 0.89}],
            "language": "es",
        }

        nlp_result = await nlp_engine.analyze_text(transcription["text"])

        # Verificar el resultado NLP
        assert nlp_result["intent"]["name"] == "check_availability"
        assert len(nlp_result["entities"]) == 1
        assert nlp_result["entities"][0]["type"] == "date"

        # 4. Generar respuesta de texto
        text_response = "Sí, tenemos habitaciones disponibles para este fin de semana. Disponemos de 5 habitaciones dobles a partir de €120 por noche."

        # 5. Sintetizar audio para la respuesta (mock TTS)
        with patch.object(ESpeakTTS, "synthesize") as mock_synthesize:
            mock_synthesize.return_value = b"synthesized_audio_response_data"

            audio_response = await audio_processor.generate_audio_response(text_response)

            # Verificar audio response
            assert audio_response == b"synthesized_audio_response_data"
            assert mock_synthesize.called
            assert audio_processor.cache_service.set.called


@pytest.mark.asyncio
async def test_audio_cache_hits_in_flow(audio_processor):
    """Test que verifica que el cache funciona correctamente en el flujo de audio."""

    # Configurar el servicio de caché para simular hit en segunda llamada
    audio_processor.cache_service.get.side_effect = [None, b"cached_audio_data"]

    text_response = "Gracias por su consulta. Le responderemos a la brevedad."

    # Primera llamada - Cache miss
    with patch.object(ESpeakTTS, "synthesize") as mock_synthesize:
        mock_synthesize.return_value = b"new_synthesized_audio_data"

        # Primera generación - debe llamar a synthesize (miss)
        result1 = await audio_processor.generate_audio_response(text_response)

        # Verificar primera llamada
        assert result1 == b"new_synthesized_audio_data"
        assert mock_synthesize.call_count == 1
        assert audio_processor.cache_service.get.call_count == 1
        assert audio_processor.cache_service.set.call_count == 1

    # Segunda llamada - Cache hit
    with patch.object(ESpeakTTS, "synthesize") as mock_synthesize:
        # Segunda generación - NO debe llamar a synthesize (hit)
        result2 = await audio_processor.generate_audio_response(text_response)

        # Verificar segunda llamada
        assert result2 == b"cached_audio_data"
        assert mock_synthesize.call_count == 0
        assert audio_processor.cache_service.get.call_count == 2
        assert audio_processor.cache_service.set.call_count == 1  # No incrementa


@pytest.mark.asyncio
async def test_error_handling_in_audio_flow(audio_processor, mock_audio_path):
    """Test que verifica el manejo adecuado de errores en el flujo de audio."""

    # 1. Simular error en transcripción
    with patch.object(WhisperSTT, "transcribe") as mock_transcribe:
        mock_transcribe.side_effect = AudioProcessingError("Error en transcripción de audio")

        # Verificar que se propaga la excepción
        with pytest.raises(AudioProcessingError):
            await audio_processor.transcribe_audio_file(mock_audio_path)

    # 2. Simular error en síntesis
    with patch.object(ESpeakTTS, "synthesize") as mock_synthesize:
        mock_synthesize.side_effect = AudioProcessingError("Error en síntesis de audio")

        # La función debe manejar la excepción y retornar None
        result = await audio_processor.generate_audio_response("Texto de prueba")
        assert result is None


@pytest.mark.asyncio
async def test_audio_metrics_integration(audio_processor):
    """Test de integración con métricas de audio durante el flujo."""

    # Reset contadores de métricas
    AudioMetrics.reset_for_testing()

    # Mock para síntesis
    with patch.object(ESpeakTTS, "synthesize") as mock_synthesize:
        mock_synthesize.return_value = b"audio_data" * 100  # 900 bytes

        # Generar audio
        text_response = "Este es un mensaje de prueba para métricas."
        await audio_processor.generate_audio_response(text_response)

        # Verificar que se registraron métricas
        assert (
            AudioMetrics.get_counter("audio_operations_total", {"operation": "generate_audio", "status": "success"})
            == 1
        )
        assert AudioMetrics.get_counter("audio_cache_operations_total", {"operation": "set", "result": "success"}) == 1
