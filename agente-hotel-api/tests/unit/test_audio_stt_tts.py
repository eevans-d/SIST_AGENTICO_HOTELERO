"""
Tests unitarios para las clases de procesamiento de audio.

Nota: Este archivo depende de implementaciones opcionales de audio (WhisperSTT).
Si el entorno base no incluye estas clases/mods, se omiten las pruebas de este módulo
para no romper la suite mínima.
"""

import pytest
from unittest.mock import MagicMock, patch
import os
import tempfile
import wave
from pathlib import Path

# Intentar importar clases opcionales; si no existen, omitir módulo
try:
    from app.services.audio_processor import WhisperSTT, ESpeakTTS  # type: ignore
except Exception:  # noqa: BLE001 - cualquier fallo de import implica dependencia opcional ausente
    pytest.skip("Componentes de audio opcionales no disponibles en el perfil base", allow_module_level=True)

from app.exceptions.audio_exceptions import AudioTranscriptionError, AudioSynthesisError


def create_test_wav_file():
    """Crea un archivo WAV de prueba con 1 segundo de silencio."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = tmp.name

    with wave.open(path, "w") as wav:
        wav.setnchannels(1)  # Mono
        wav.setsampwidth(2)  # 2 bytes por muestra (16 bits)
        wav.setframerate(16000)  # 16kHz
        # 1 segundo de silencio (zeros)
        wav.writeframes(b"\x00" * 16000 * 2)

    return path


@pytest.fixture
def temp_wav_file():
    """Fixture que crea un archivo WAV temporal para pruebas."""
    path = create_test_wav_file()
    yield path

    # Limpieza
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def mock_whisper_model():
    """Fixture que proporciona un mock del modelo Whisper."""
    model = MagicMock()
    model.transcribe.return_value = {
        "text": "Texto de prueba transcrito por Whisper.",
        "segments": [{"text": "Texto de prueba", "start": 0.0, "end": 1.0}],
        "language": "es",
    }
    return model


@pytest.mark.asyncio
async def test_whisper_stt_initialization():
    """Test que verifica la inicialización correcta de WhisperSTT."""
    with patch("app.services.audio_processor.whisper") as mock_whisper:
        # Configurar mock
        mock_whisper.load_model.return_value = MagicMock()

        # Crear instancia
        stt = WhisperSTT(model_name="tiny")

        # Verificar inicialización
        assert stt.model_name == "tiny"
        assert mock_whisper.load_model.called
        assert stt._model_loaded == "tiny"


@pytest.mark.asyncio
async def test_whisper_transcribe_success(temp_wav_file, mock_whisper_model):
    """Test que verifica una transcripción exitosa."""
    with patch("app.services.audio_processor.whisper") as mock_whisper:
        mock_whisper.load_model.return_value = mock_whisper_model

        # Crear instancia con modelo precargado
        stt = WhisperSTT(model_name="base")

        # Transcribir
        result = await stt.transcribe(temp_wav_file)

        # Verificaciones
        assert result["success"] is True
        assert "Texto de prueba transcrito" in result["text"]
        assert "es" in result["language"]
        assert "confidence" in result
        assert "duration" in result
        assert mock_whisper_model.transcribe.call_count == 1


@pytest.mark.asyncio
async def test_whisper_transcribe_with_language_hint():
    """Test que verifica que las sugerencias de idioma funcionan correctamente."""
    with patch("app.services.audio_processor.whisper") as mock_whisper:
        # Crear mock de modelo que verifica las opciones
        model_mock = MagicMock()
        mock_whisper.load_model.return_value = model_mock
        model_mock.transcribe.return_value = {
            "text": "Texto en español",
            "segments": [{"text": "Texto en español", "start": 0.0, "end": 0.5}],
            "language": "es",
        }

        # Crear instancia y transcribir
        stt = WhisperSTT(model_name="base")
        stt.language = "es"  # Configurar idioma
        audio_path = create_test_wav_file()

        await stt.transcribe(Path(audio_path))

        # Verificar que se pasó el idioma al modelo
        call_kwargs = model_mock.transcribe.call_args[1]
        assert call_kwargs.get("language") == "es"

        # Limpieza
        os.unlink(audio_path)


@pytest.mark.asyncio
async def test_whisper_error_handling():
    """Test que verifica el manejo correcto de errores de Whisper."""
    with patch("app.services.audio_processor.whisper") as mock_whisper:
        # Mock que genera un error
        model_mock = MagicMock()
        mock_whisper.load_model.return_value = model_mock
        model_mock.transcribe.side_effect = Exception("Error al procesar audio")

        # Crear instancia
        stt = WhisperSTT()
        audio_path = create_test_wav_file()

        # Verificar que se lanza excepción apropiada
        with pytest.raises(AudioTranscriptionError):
            await stt.transcribe(Path(audio_path))

        # Limpieza
        os.unlink(audio_path)


@pytest.mark.asyncio
async def test_espeak_tts_initialization():
    """Test que verifica la inicialización correcta de ESpeakTTS."""
    with patch("app.services.audio_processor.subprocess") as mock_subprocess:
        mock_subprocess.run.return_value = MagicMock(returncode=0)

        # Crear instancia
        tts = ESpeakTTS()

        # Verificar inicialización
        assert tts.voice == "es"
        assert tts.speed == 175
        assert tts.pitch == 50
        assert hasattr(tts, "_espeak_available")


@pytest.mark.asyncio
async def test_espeak_synthesize_success():
    """Test que verifica una síntesis exitosa."""
    with patch("app.services.audio_processor.subprocess") as mock_subprocess:
        # Mock para subprocess
        mock_subprocess.run.return_value = MagicMock(returncode=0)

        # Mock para la función de leer el archivo
        with patch("app.services.audio_processor.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = b"audio_data"
            mock_open.return_value.__enter__.return_value = mock_file

            # Crear instancia y sintetizar
            tts = ESpeakTTS(voice="es-mx")
            result = await tts.synthesize("Este es un texto de prueba.")

            # Verificaciones
            assert isinstance(result, bytes)
            assert result == b"audio_data"
            assert mock_subprocess.run.call_count == 1

            # Verificar comando espeak
            args = mock_subprocess.run.call_args[0][0]
            assert "espeak" in args[0]
            assert "-v" in args
            assert "es-mx" in args
            assert "-w" in args


@pytest.mark.asyncio
async def test_espeak_synthesize_error():
    """Test que verifica el manejo correcto de errores de eSpeak."""
    with patch("app.services.audio_processor.subprocess") as mock_subprocess:
        # Mock para simular error en espeak
        mock_subprocess.run.return_value = MagicMock(returncode=1)

        # Crear instancia
        tts = ESpeakTTS()

        # Verificar que se lanza excepción apropiada
        with pytest.raises(AudioSynthesisError):
            await tts.synthesize("Texto que debería fallar.")

        assert mock_subprocess.run.call_count == 1


@pytest.mark.asyncio
async def test_espeak_voice_configuration():
    """Test que verifica diferentes configuraciones de voz."""
    voices_to_test = ["es", "es-mx", "es-la", "en"]

    for voice in voices_to_test:
        with patch("app.services.audio_processor.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = MagicMock(returncode=0)

            # Crear instancia con voz específica
            tts = ESpeakTTS(voice=voice)

            # Mock para leer archivo
            with patch("app.services.audio_processor.open", create=True) as mock_open:
                mock_file = MagicMock()
                mock_file.read.return_value = b"audio_data"
                mock_open.return_value.__enter__.return_value = mock_file

                # Sintetizar
                await tts.synthesize("Prueba con voz " + voice)

                # Verificar comando
                args = mock_subprocess.run.call_args[0][0]
                assert "-v" in args
                voice_index = args.index("-v") + 1
                assert args[voice_index] == voice
