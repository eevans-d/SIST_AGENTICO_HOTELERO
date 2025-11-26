# test_audio_processor.py

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch
from app.services.audio_processor import AudioProcessor, OptimizedWhisperSTT, ESpeakTTS
from app.exceptions.audio_exceptions import AudioDownloadError, AudioConversionError


class TestOptimizedWhisperSTT:
    @pytest.mark.asyncio
    async def test_transcribe_returns_mock_response(self):
        """Test que OptimizedWhisperSTT retorna respuesta mock"""
        stt = OptimizedWhisperSTT()
        # Force mock mode
        stt._model_loaded = "mock"
        
        audio_file = Path("/fake/path/audio.wav")

        result = await stt.transcribe(audio_file)

        assert result["success"] is True
        assert result["confidence"] == 0.9
        assert "disponibilidad" in result["text"]


class TestESpeakTTS:
    @pytest.mark.asyncio
    async def test_synthesize_returns_none(self):
        """Test que ESpeakTTS retorna None (mock)"""
        tts = ESpeakTTS()

        result = await tts.synthesize("Hola mundo")

        assert result is None


class TestAudioProcessor:
    @pytest.fixture
    def audio_processor(self):
        return AudioProcessor()

    @pytest.mark.asyncio
    async def test_temporary_file_context_manager(self, audio_processor):
        """Test el context manager de archivos temporales"""
        temp_path = None

        async with audio_processor._temporary_file(suffix=".test") as temp_file:
            temp_path = temp_file
            assert temp_file.exists()
            assert temp_file.suffix == ".test"

            # Escribir algo en el archivo
            with open(temp_file, "w") as f:
                f.write("test content")

        # El archivo debe haber sido eliminado
        assert not temp_path.exists()

    @pytest.mark.asyncio
    async def test_download_audio_success(self, audio_processor):
        """Test descarga exitosa de audio"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content.read = AsyncMock(side_effect=[b"audio_chunk", b""])

        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = Path(temp_file.name)

                try:
                    await audio_processor._download_audio("http://example.com/audio.ogg", temp_path)

                    # Verificar que el archivo fue creado con contenido
                    assert temp_path.exists()
                    with open(temp_path, "rb") as f:
                        content = f.read()
                    assert content == b"audio_chunk"
                finally:
                    temp_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_download_audio_http_error(self, audio_processor):
        """Test manejo de error HTTP en descarga"""
        mock_response = AsyncMock()
        mock_response.status = 404

        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = Path(temp_file.name)

                try:
                    with pytest.raises(AudioDownloadError) as exc_info:
                        await audio_processor._download_audio("http://example.com/audio.ogg", temp_path)

                    assert "HTTP Status: 404" in str(exc_info.value)
                finally:
                    temp_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_convert_to_wav_success(self, audio_processor):
        """Test conversión exitosa a WAV"""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"stdout", b"stderr")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            input_file = Path("/fake/input.ogg")
            output_file = Path("/fake/output.wav")

            # No debe lanzar excepción
            await audio_processor._convert_to_wav(input_file, output_file)

            # Verificar que se llamó con los argumentos correctos
            asyncio.create_subprocess_exec.assert_called_once()
            args = asyncio.create_subprocess_exec.call_args[0]
            assert args[0] == "ffmpeg"
            assert str(input_file) in args
            assert str(output_file) in args

    @pytest.mark.asyncio
    async def test_convert_to_wav_ffmpeg_error(self, audio_processor):
        """Test manejo de error de FFmpeg"""
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b"stdout", b"error message")

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            input_file = Path("/fake/input.ogg")
            output_file = Path("/fake/output.wav")

            with pytest.raises(AudioConversionError) as exc_info:
                await audio_processor._convert_to_wav(input_file, output_file)

            assert "Return code: 1" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_convert_to_wav_ffmpeg_not_found(self, audio_processor):
        """Test manejo cuando FFmpeg no está instalado"""
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError()):
            input_file = Path("/fake/input.ogg")
            output_file = Path("/fake/output.wav")

            with pytest.raises(AudioConversionError) as exc_info:
                await audio_processor._convert_to_wav(input_file, output_file)

            assert "FFmpeg not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_transcribe_whatsapp_audio_success(self, audio_processor):
        """Test transcripción exitosa de audio de WhatsApp"""
        # Mock de los métodos internos
        audio_processor._download_audio = AsyncMock()
        audio_processor._convert_to_wav = AsyncMock()
        audio_processor.stt.transcribe = AsyncMock(
            return_value={"text": "Transcripción de prueba", "confidence": 0.95, "success": True}
        )

        result = await audio_processor.transcribe_whatsapp_audio("http://example.com/audio.ogg")

        assert result["success"] is True
        assert result["text"] == "Transcripción de prueba"
        assert result["confidence"] == 0.95

        # Verificar que se llamaron los métodos
        audio_processor._download_audio.assert_called_once()
        audio_processor._convert_to_wav.assert_called_once()
        audio_processor.stt.transcribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_transcribe_whatsapp_audio_error(self, audio_processor):
        """Test manejo de error en transcripción"""
        # Mock que lanza excepción
        audio_processor._download_audio = AsyncMock(side_effect=AudioDownloadError("Download failed"))

        result = await audio_processor.transcribe_whatsapp_audio("http://example.com/audio.ogg")

        assert result["success"] is False
        assert result["text"] == ""
        assert result["confidence"] == 0.0
        assert "error" in result

    @pytest.mark.asyncio
    async def test_generate_audio_response_success(self, audio_processor):
        """Test generación exitosa de respuesta de audio"""
        audio_processor.tts.synthesize = AsyncMock(return_value=b"audio_data")

        result = await audio_processor.generate_audio_response("Hola mundo")

        assert result == b"audio_data"
        audio_processor.tts.synthesize.assert_called_once_with("Hola mundo")

    @pytest.mark.asyncio
    async def test_generate_audio_response_error(self, audio_processor):
        """Test manejo de error en generación de audio"""
        audio_processor.tts.synthesize = AsyncMock(side_effect=Exception("TTS error"))

        result = await audio_processor.generate_audio_response("Hola mundo")

        assert result is None
