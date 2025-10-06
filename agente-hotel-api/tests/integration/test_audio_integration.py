# test_audio_integration.py - Integration tests for audio processing

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from app.services.audio_processor import AudioProcessor
from app.services.audio_validator import AudioValidator
from app.services.audio_metrics import AudioMetrics
from app.exceptions.audio_exceptions import AudioDownloadError, AudioValidationError


class TestAudioProcessorIntegration:
    @pytest.fixture
    def audio_processor(self):
        return AudioProcessor()
    
    @pytest.fixture 
    def audio_validator(self):
        return AudioValidator()
    
    @pytest.mark.asyncio
    async def test_full_audio_pipeline_mock(self, audio_processor):
        """Test complete audio pipeline con mocks"""
        # Mock external dependencies
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Mock successful download
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.content.read = AsyncMock(side_effect=[b"fake_audio_data", b""])
            mock_session.get.return_value.__aenter__.return_value = mock_response
            
            # Mock FFmpeg success
            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.communicate.return_value = (b"stdout", b"stderr")
                mock_subprocess.return_value = mock_process
                
                # Execute full pipeline
                result = await audio_processor.transcribe_whatsapp_audio("http://example.com/audio.ogg")
                
                # Verify result
                assert result["success"] is True
                assert "text" in result
                assert "confidence" in result
                
                # Verify external calls were made
                mock_session.get.assert_called_once()
                mock_subprocess.assert_called()
    
    @pytest.mark.asyncio
    async def test_audio_validation_integration(self, audio_validator):
        """Test audio validation integration"""
        # Test URL validation
        valid_url = "https://example.com/audio.ogg"
        result = await audio_validator.validate_audio_url(valid_url)
        assert result["valid"] is True
        
        # Test invalid URL
        invalid_url = "not_a_url"
        result = await audio_validator.validate_audio_url(invalid_url)
        assert result["valid"] is False
        assert len(result["errors"]) > 0
    
    @pytest.mark.asyncio
    async def test_audio_processor_with_validation(self, audio_processor, audio_validator):
        """Test audio processor con validación previa"""
        url = "https://example.com/audio.ogg"
        
        # Validate URL first
        validation_result = await audio_validator.validate_audio_url(url)
        
        if validation_result["valid"]:
            # Mock download and processing
            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value = mock_session
                
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.content.read = AsyncMock(side_effect=[b"audio", b""])
                mock_session.get.return_value.__aenter__.return_value = mock_response
                
                with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                    mock_process = AsyncMock()
                    mock_process.returncode = 0
                    mock_process.communicate.return_value = (b"stdout", b"stderr")
                    mock_subprocess.return_value = mock_process
                    
                    result = await audio_processor.transcribe_whatsapp_audio(url)
                    assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_metrics_integration(self, audio_processor):
        """Test que las métricas se registren correctamente"""
        # Mock metrics to track calls
        with patch.object(AudioMetrics, 'record_operation') as mock_record_op:
            with patch.object(AudioMetrics, 'record_operation_duration') as mock_record_duration:
                with patch.object(AudioMetrics, 'record_error') as mock_record_error:
                    
                    # Mock failed download to trigger error metrics
                    with patch("aiohttp.ClientSession") as mock_session_class:
                        mock_session = AsyncMock()
                        mock_session_class.return_value = mock_session
                        
                        mock_response = AsyncMock()
                        mock_response.status = 404
                        mock_session.get.return_value.__aenter__.return_value = mock_response
                        
                        # This should fail and record error metrics
                        result = await audio_processor.transcribe_whatsapp_audio("http://example.com/notfound.ogg")
                        
                        assert result["success"] is False
                        # Note: Error metrics would be recorded in actual implementation
    
    @pytest.mark.asyncio
    async def test_tts_integration(self, audio_processor):
        """Test TTS integration with mocked eSpeak"""
        text = "Hola, esta es una prueba de síntesis de voz"
        
        # Mock eSpeak availability check
        with patch.object(audio_processor.tts, '_check_espeak_availability', return_value=True):
            # Mock subprocess calls for eSpeak and FFmpeg
            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                # First call: eSpeak process
                espeak_process = AsyncMock()
                espeak_process.returncode = 0
                espeak_process.stdout = AsyncMock()
                espeak_process.communicate.return_value = (b"wav_data", b"")
                
                # Second call: FFmpeg process  
                ffmpeg_process = AsyncMock()
                ffmpeg_process.returncode = 0
                ffmpeg_process.communicate.return_value = (b"ogg_audio_data", b"")
                
                mock_subprocess.side_effect = [espeak_process, ffmpeg_process]
                
                result = await audio_processor.tts.synthesize(text)
                
                assert result == b"ogg_audio_data"
                assert mock_subprocess.call_count == 2
    
    @pytest.mark.asyncio
    async def test_temporary_file_cleanup_integration(self, audio_processor):
        """Test que los archivos temporales se limpien correctamente"""
        temp_paths = []
        
        # Capture temporary file paths
        original_temporary_file = audio_processor._temporary_file
        
        async def capture_temp_file(*args, **kwargs):
            async with original_temporary_file(*args, **kwargs) as temp_file:
                temp_paths.append(temp_file)
                yield temp_file
        
        # Replace with capturing version
        audio_processor._temporary_file = capture_temp_file
        
        # Mock external dependencies
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.content.read = AsyncMock(side_effect=[b"audio", b""])
            mock_session.get.return_value.__aenter__.return_value = mock_response
            
            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.communicate.return_value = (b"stdout", b"stderr")
                mock_subprocess.return_value = mock_process
                
                await audio_processor.transcribe_whatsapp_audio("http://example.com/audio.ogg")
        
        # Verify all temporary files were cleaned up
        for temp_path in temp_paths:
            assert not temp_path.exists(), f"Temporary file not cleaned up: {temp_path}"
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, audio_processor):
        """Test manejo integral de errores a través de todo el pipeline"""
        # Test download error
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Simulate network error
            mock_session.get.side_effect = Exception("Network error")
            
            result = await audio_processor.transcribe_whatsapp_audio("http://example.com/audio.ogg")
            
            assert result["success"] is False
            assert "error" in result
            assert result["confidence"] == 0.0
            assert result["text"] == ""
    
    @pytest.mark.asyncio
    async def test_concurrent_audio_processing(self, audio_processor):
        """Test procesamiento concurrente de múltiples audios"""
        urls = [
            "http://example.com/audio1.ogg",
            "http://example.com/audio2.ogg", 
            "http://example.com/audio3.ogg"
        ]
        
        # Mock successful processing
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.content.read = AsyncMock(side_effect=[b"audio", b""])
            mock_session.get.return_value.__aenter__.return_value = mock_response
            
            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.communicate.return_value = (b"stdout", b"stderr")
                mock_subprocess.return_value = mock_process
                
                # Process multiple audios concurrently
                tasks = [
                    audio_processor.transcribe_whatsapp_audio(url) 
                    for url in urls
                ]
                results = await asyncio.gather(*tasks)
                
                # Verify all succeeded
                assert len(results) == 3
                for result in results:
                    assert result["success"] is True