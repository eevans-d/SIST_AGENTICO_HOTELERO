import pytest
import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from app.services.audio_processor import OptimizedAudioProcessor, OptimizedWhisperSTT
from app.exceptions.audio_exceptions import (
    AudioDownloadError,
    AudioConversionError,
    AudioTimeoutError,
    AudioValidationError
)
from app.core.settings import settings

# Mock settings
@pytest.fixture
def mock_settings():
    with patch("app.services.audio_processor.settings") as mock_settings:
        mock_settings.audio_timeout_seconds = 1.0
        mock_settings.audio_max_size_mb = 1.0
        mock_settings.whisper_model = "base"
        mock_settings.whisper_language = "es"
        mock_settings.audio_enabled = True
        yield mock_settings

@pytest.fixture
def audio_processor(mock_settings):
    processor = OptimizedAudioProcessor()
    # Mock internal components
    processor.stt = AsyncMock(spec=OptimizedWhisperSTT)
    processor.cache_optimizer = AsyncMock()
    processor.compression_optimizer = AsyncMock()
    return processor

@pytest.mark.asyncio
async def test_temporary_file_cleanup(audio_processor):
    """Test that temporary files are cleaned up after use."""
    temp_path = None
    
    async with audio_processor._temporary_file(suffix=".test") as temp_file:
        temp_path = temp_file
        # Simulate file creation
        with open(temp_path, "w") as f:
            f.write("test")
        assert temp_path.exists()
    
    # Verify cleanup
    assert not temp_path.exists()

@pytest.mark.asyncio
async def test_temporary_file_cleanup_on_error(audio_processor):
    """Test that temporary files are cleaned up even if an error occurs."""
    temp_path = None
    
    try:
        async with audio_processor._temporary_file(suffix=".test") as temp_file:
            temp_path = temp_file
            with open(temp_path, "w") as f:
                f.write("test")
            raise ValueError("Simulated error")
    except ValueError:
        pass
    
    assert not temp_path.exists()

@pytest.mark.asyncio
async def test_download_audio_success(audio_processor):
    """Test successful audio download."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {"content-length": "1024"}
    mock_response.read.side_effect = [b"audio_data", b""]
    
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        with patch("builtins.open", mock_open()) as mock_file:
            await audio_processor._download_audio_optimized("http://example.com/audio.ogg", Path("test.ogg"))
            
            mock_file().write.assert_called()

@pytest.mark.asyncio
async def test_download_audio_too_large_header(audio_processor, mock_settings):
    """Test download rejection based on Content-Length header."""
    mock_settings.audio_max_size_mb = 1.0 # 1MB
    
    mock_response = AsyncMock()
    mock_response.status = 200
    # 2MB in bytes
    mock_response.headers = {"content-length": str(2 * 1024 * 1024)}
    
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(AudioValidationError) as exc:
            await audio_processor._download_audio_optimized("http://example.com/large.ogg", Path("test.ogg"))
        
        assert "Audio file too large" in str(exc.value)

@pytest.mark.asyncio
async def test_download_audio_too_large_stream(audio_processor, mock_settings):
    """Test download rejection during streaming if size exceeds limit."""
    mock_settings.audio_max_size_mb = 0.001 # ~1KB
    
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {} # No content length
    # Chunk larger than limit
    mock_response.content.read.side_effect = [b"a" * 2048, b""]
    
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        with patch("builtins.open", mock_open()):
            with pytest.raises(AudioValidationError) as exc:
                await audio_processor._download_audio_optimized("http://example.com/stream.ogg", Path("test.ogg"))
            
            assert "Audio file too large" in str(exc.value)

@pytest.mark.asyncio
async def test_download_audio_timeout(audio_processor):
    """Test download timeout."""
    mock_session = AsyncMock()
    mock_session.get.side_effect = asyncio.TimeoutError()
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(AudioTimeoutError):
            await audio_processor._download_audio_optimized("http://example.com/timeout.ogg", Path("test.ogg"))

@pytest.mark.asyncio
async def test_convert_to_wav_success(audio_processor):
    """Test successful audio conversion."""
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (b"", b"")
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
        await audio_processor._convert_to_wav(Path("input.ogg"), Path("output.wav"))
        
        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        assert "ffmpeg" in args
        assert str(Path("input.ogg")) in args
        assert str(Path("output.wav")) in args

@pytest.mark.asyncio
async def test_convert_to_wav_failure(audio_processor):
    """Test audio conversion failure (ffmpeg error)."""
    mock_process = AsyncMock()
    mock_process.returncode = 1
    mock_process.communicate.return_value = (b"", b"Error details")
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with pytest.raises(AudioConversionError) as exc:
            await audio_processor._convert_to_wav(Path("input.ogg"), Path("output.wav"))
        
        assert "FFmpeg conversion failed" in str(exc.value)

@pytest.mark.asyncio
async def test_transcribe_whatsapp_audio_success(audio_processor):
    """Test full transcription pipeline success."""
    # Mock download and conversion to avoid external dependencies
    audio_processor._download_audio_optimized = AsyncMock()
    audio_processor._convert_to_wav = AsyncMock()
    
    # Mock STT result
    expected_result = {"text": "Hello world", "confidence": 0.95}
    audio_processor.stt.transcribe.return_value = expected_result
    
    result = await audio_processor.transcribe_whatsapp_audio("http://example.com/audio.ogg")
    
    assert result["text"] == "Hello world"
    assert result["confidence"] == 0.95
    assert result["success"] is not False # It might not be explicitly set to True in result, but shouldn't be False
    
    audio_processor._download_audio_optimized.assert_called_once()
    audio_processor._convert_to_wav.assert_called_once()
    audio_processor.stt.transcribe.assert_called_once()

@pytest.mark.asyncio
async def test_transcribe_whatsapp_audio_error_handling(audio_processor):
    """Test error handling in transcription pipeline."""
    # Mock download to fail
    audio_processor._download_audio_optimized = AsyncMock(side_effect=AudioDownloadError("Download failed"))
    
    result = await audio_processor.transcribe_whatsapp_audio("http://example.com/audio.ogg")
    
    assert result["success"] is False
    assert "Download failed" in result["error"]
    assert result["confidence"] == 0.0

@pytest.mark.asyncio
async def test_transcribe_disabled(audio_processor, mock_settings):
    """Test behavior when audio processing is disabled."""
    mock_settings.audio_enabled = False
    
    result = await audio_processor.transcribe_whatsapp_audio("http://example.com/audio.ogg")
    
    assert result["success"] is False
    assert "deshabilitado" in result["text"]
