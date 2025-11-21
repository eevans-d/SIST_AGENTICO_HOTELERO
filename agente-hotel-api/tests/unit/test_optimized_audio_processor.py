import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import time
from app.services.audio_processor import OptimizedWhisperSTT, ESpeakTTS
from app.services.audio_cache_optimizer import AudioCacheOptimizer, AudioCacheType, CacheStrategy
from app.exceptions.audio_exceptions import AudioTranscriptionError

# Mock settings
@pytest.fixture
def mock_settings():
    with patch("app.services.audio_processor.settings") as mock:
        mock.whisper_model = "base"
        mock.whisper_language = "es"
        mock.espeak_voice = "es"
        mock.espeak_speed = 160
        mock.espeak_pitch = 50
        yield mock

@pytest.fixture
def mock_cache_optimizer():
    mock = AsyncMock(spec=AudioCacheOptimizer)
    mock.get.return_value = None
    return mock

@pytest.mark.asyncio
class TestOptimizedWhisperSTT:
    
    async def test_load_model_cache_hit(self, mock_settings, mock_cache_optimizer):
        """Test that model is loaded from cache if available"""
        stt = OptimizedWhisperSTT(cache_optimizer=mock_cache_optimizer)
        mock_model = MagicMock()
        mock_cache_optimizer.get.return_value = mock_model
        
        await stt._load_model()
        
        assert stt.model == mock_model
        assert stt._model_loaded is True
        mock_cache_optimizer.get.assert_called_once()
        
    async def test_load_model_cache_miss_success(self, mock_settings, mock_cache_optimizer):
        """Test loading model when not in cache"""
        stt = OptimizedWhisperSTT(cache_optimizer=mock_cache_optimizer)
        
        with patch("importlib.import_module") as mock_import:
            mock_whisper = MagicMock()
            mock_import.return_value = mock_whisper
            mock_whisper.load_model.return_value = "loaded_model"
            
            await stt._load_model()
            
            assert stt.model == "loaded_model"
            assert stt._model_loaded is True
            mock_cache_optimizer.set.assert_called_once()

    async def test_load_model_import_error(self, mock_settings):
        """Test fallback when whisper is not installed"""
        stt = OptimizedWhisperSTT()
        
        with patch("importlib.import_module", side_effect=ImportError):
            await stt._load_model()
            
            assert stt._model_loaded == "mock"
            assert stt.model is None

    async def test_transcribe_mock_mode(self, mock_settings):
        """Test transcription in mock mode"""
        stt = OptimizedWhisperSTT()
        stt._model_loaded = "mock"
        
        result = await stt.transcribe(Path("test.ogg"))
        
        assert result["success"] is True
        assert result["text"] == "Hola, quisiera saber si tienen disponibilidad para el fin de semana."
        assert result["confidence"] == 0.9

    async def test_transcribe_cache_hit(self, mock_settings, mock_cache_optimizer):
        """Test transcription result from cache"""
        stt = OptimizedWhisperSTT(cache_optimizer=mock_cache_optimizer)
        stt._model_loaded = True
        stt.model = MagicMock()
        
        cached_result = {"text": "cached", "success": True}
        mock_cache_optimizer.get.return_value = cached_result
        
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 100
            mock_stat.return_value.st_mtime = 1000
            
            result = await stt.transcribe(Path("test.ogg"))
            
            assert result == cached_result
            mock_cache_optimizer.get.assert_called_once()

    async def test_transcribe_success(self, mock_settings, mock_cache_optimizer):
        """Test successful transcription"""
        stt = OptimizedWhisperSTT(cache_optimizer=mock_cache_optimizer)
        stt._model_loaded = True
        stt.model = MagicMock()
        stt.model.transcribe.return_value = {
            "text": " hello world ",
            "language": "en",
            "segments": [{"start": 0, "end": 1, "no_speech_prob": 0.1}]
        }
        
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 100
            mock_stat.return_value.st_mtime = 1000
            
            result = await stt.transcribe(Path("test.ogg"))
            
            assert result["text"] == "hello world"
            assert result["success"] is True
            assert result["language"] == "en"
            assert result["confidence"] > 0.8
            mock_cache_optimizer.set.assert_called_once()

    async def test_transcribe_error(self, mock_settings):
        """Test transcription error handling"""
        stt = OptimizedWhisperSTT()
        stt._model_loaded = True
        stt.model = MagicMock()
        stt.model.transcribe.side_effect = Exception("Transcription failed")
        
        with pytest.raises(AudioTranscriptionError):
            await stt.transcribe(Path("test.ogg"))

    def test_calculate_confidence(self):
        """Test confidence calculation"""
        stt = OptimizedWhisperSTT()
        
        # Case 1: No segments
        assert stt._calculate_confidence({}) == 0.8
        
        # Case 2: Perfect confidence
        segments = [{"start": 0, "end": 1, "no_speech_prob": 0.0}]
        assert stt._calculate_confidence({"segments": segments}) == 1.0
        
        # Case 3: Low confidence
        segments = [{"start": 0, "end": 1, "no_speech_prob": 1.0}]
        assert stt._calculate_confidence({"segments": segments}) == 0.0

@pytest.mark.asyncio
class TestESpeakTTS:
    
    async def test_check_availability_success(self, mock_settings):
        """Test eSpeak availability check success"""
        tts = ESpeakTTS()
        
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"version", b"")
            mock_process.returncode = 0
            mock_exec.return_value = mock_process
            
            assert await tts._check_espeak_availability() is True
            assert tts._espeak_available is True

    async def test_check_availability_failure(self, mock_settings):
        """Test eSpeak availability check failure"""
        tts = ESpeakTTS()
        
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"", b"error")
            mock_process.returncode = 1
            mock_exec.return_value = mock_process
            
            assert await tts._check_espeak_availability() is False
            assert tts._espeak_available is False

    async def test_check_availability_not_found(self, mock_settings):
        """Test eSpeak not found"""
        tts = ESpeakTTS()
        
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
            assert await tts._check_espeak_availability() is False
            assert tts._espeak_available is False

    async def test_synthesize_test_env(self, mock_settings):
        """Test synthesize returns None in test environment"""
        tts = ESpeakTTS()
        # PYTEST_CURRENT_TEST is set by pytest
        result = await tts.synthesize("test")
        assert result is None

    async def test_synthesize_not_available(self, mock_settings):
        """Test synthesize when eSpeak is not available"""
        tts = ESpeakTTS()
        
        # Remove PYTEST_CURRENT_TEST to bypass the mock check
        with patch.dict("os.environ", clear=True):
            # Mock _check_espeak_availability to return False
            with patch.object(tts, "_check_espeak_availability", return_value=False):
                result = await tts.synthesize("test")
                assert result is None
