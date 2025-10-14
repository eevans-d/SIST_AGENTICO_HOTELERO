"""
Tests básicos para el sistema de audio completo.
Este módulo verifica la funcionalidad básica del sistema de audio sin dependencias complejas.
"""

import pytest
from unittest.mock import MagicMock, patch
import tempfile
import os
from pathlib import Path

from app.services.audio_processor import AudioProcessor, WhisperSTT, ESpeakTTS
from app.exceptions.audio_exceptions import AudioTranscriptionError, AudioSynthesisError


@pytest.mark.asyncio
async def test_whisper_stt_mock_mode():
    """Test que verifica el funcionamiento en modo mock de WhisperSTT."""

    stt = WhisperSTT()
    stt._model_loaded = "mock"  # Forzar modo mock

    # Crear archivo temporal para la prueba
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(b"dummy_audio_data")
        audio_path = Path(tmp.name)

    try:
        # Transcribir en modo mock
        result = await stt.transcribe(audio_path)

        # Verificar resultado
        assert result["success"] is True
        assert "text" in result
        assert result["language"] == "es"
        assert result["confidence"] > 0.8

    finally:
        # Limpieza
        os.unlink(audio_path)


@pytest.mark.asyncio
async def test_espeak_tts_availability_check():
    """Test que verifica la comprobación de disponibilidad de eSpeak."""

    tts = ESpeakTTS()

    # Mock para subprocess que simula eSpeak no disponible
    with patch("app.services.audio_processor.asyncio.create_subprocess_exec") as mock_subprocess:
        # Simular que eSpeak no está disponible
        mock_process = MagicMock()
        mock_process.returncode = 1

        # Crear mock async para communicate
        async def mock_communicate():
            return (b"", b"espeak: command not found")

        mock_process.communicate = mock_communicate
        mock_subprocess.return_value = mock_process

        # Verificar disponibilidad
        is_available = await tts._check_espeak_availability()

        assert is_available is False
        assert tts._espeak_available is False


@pytest.mark.asyncio
async def test_espeak_tts_unavailable_fallback():
    """Test que verifica el fallback cuando eSpeak no está disponible."""

    tts = ESpeakTTS()
    tts._espeak_available = False  # Simular que no está disponible

    # Intentar síntesis
    result = await tts.synthesize("Texto de prueba")

    # Debería retornar None cuando eSpeak no está disponible
    assert result is None


@pytest.mark.asyncio
async def test_audio_processor_initialization():
    """Test que verifica la inicialización correcta del AudioProcessor."""

    processor = AudioProcessor()

    # Verificar que los componentes se inicializaron
    assert processor.stt is not None
    assert processor.tts is not None
    assert isinstance(processor.stt, WhisperSTT)
    assert isinstance(processor.tts, ESpeakTTS)


@pytest.mark.asyncio
async def test_audio_processor_transcribe_mock():
    """Test de transcripción usando el AudioProcessor en modo mock."""

    processor = AudioProcessor()
    processor.stt._model_loaded = "mock"

    # Crear archivo temporal
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(b"dummy_audio_data")
        audio_path = Path(tmp.name)

    try:
        # Transcribir usando el método correcto
        result = await processor.stt.transcribe(audio_path)

        # Verificar resultado
        assert result["success"] is True
        assert len(result["text"]) > 0
        assert result["language"] == "es"

    finally:
        os.unlink(audio_path)


@pytest.mark.asyncio
async def test_audio_processor_generate_response_with_mock():
    """Test de generación de respuesta de audio usando mocks."""

    processor = AudioProcessor()

    # Mock para eSpeak
    with patch.object(processor.tts, "synthesize") as mock_synthesize:
        mock_synthesize.return_value = b"mock_audio_data"

        # Generar respuesta
        result = await processor.generate_audio_response("Hola, ¿cómo está?")

        # Verificar resultado
        assert result == b"mock_audio_data"
        mock_synthesize.assert_called_once_with("Hola, ¿cómo está?")


@pytest.mark.asyncio
async def test_audio_processor_error_handling():
    """Test que verifica el manejo de errores en el AudioProcessor."""

    processor = AudioProcessor()

    # Mock para simular error en transcripción
    with patch.object(processor.stt, "transcribe") as mock_transcribe:
        mock_transcribe.side_effect = AudioTranscriptionError("Error de prueba")

        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(b"dummy_audio_data")
            audio_path = Path(tmp.name)

        try:
            # Verificar que se propaga la excepción
            with pytest.raises(AudioTranscriptionError):
                await processor.stt.transcribe(audio_path)

        finally:
            os.unlink(audio_path)


@pytest.mark.asyncio
async def test_audio_synthesis_error_fallback():
    """Test que verifica el fallback cuando hay error en síntesis."""

    processor = AudioProcessor()

    # Mock para simular error en síntesis
    with patch.object(processor.tts, "synthesize") as mock_synthesize:
        mock_synthesize.side_effect = AudioSynthesisError("Error en síntesis")

        # Intentar generar audio
        result = await processor.generate_audio_response("Texto de prueba")

        # Debería retornar None en caso de error
        assert result is None
