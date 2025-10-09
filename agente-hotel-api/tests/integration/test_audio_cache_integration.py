# tests/integration/test_audio_cache_integration.py

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.audio_processor import AudioProcessor


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = 1
    redis_mock.expire.return_value = True
    redis_mock.hset.return_value = 1
    redis_mock.hgetall.return_value = {}
    redis_mock.hincrby.return_value = 1
    return redis_mock


@pytest.fixture
def mock_espeak_tts():
    """Mock ESpeakTTS."""
    tts_mock = MagicMock()
    tts_mock.voice = "default"
    tts_mock.synthesize = AsyncMock(return_value=b"mock audio data")
    return tts_mock


@pytest.fixture
async def audio_processor_with_cache(mock_redis, mock_espeak_tts):
    """AudioProcessor con caché mockeado."""
    with patch('app.services.audio_cache_service.get_redis', return_value=mock_redis), \
         patch('app.services.audio_processor.ESpeakTTS', return_value=mock_espeak_tts):
        processor = AudioProcessor()
        yield processor


class TestAudioCacheIntegration:
    """Pruebas de integración entre AudioProcessor y AudioCacheService."""
    
    @pytest.mark.asyncio
    async def test_audio_generation_with_cache_miss(self, audio_processor_with_cache, mock_redis, mock_espeak_tts):
        """Prueba generación de audio cuando no está en caché (cache miss)."""
        # Cache miss - no hay datos en caché
        mock_redis.get.return_value = None
        
        text = "Hello, this is a test message"
        result = await audio_processor_with_cache.generate_audio_response(text, "test_content")
        
        # Debe devolver audio generado por TTS
        assert result == b"mock audio data"
        
        # Debe intentar obtener desde caché
        mock_redis.get.assert_called_once()
        
        # Debe generar audio usando TTS
        mock_espeak_tts.synthesize.assert_called_once_with(text)
        
        # Debe guardar en caché el resultado
        mock_redis.set.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_audio_generation_with_cache_hit(self, audio_processor_with_cache, mock_redis, mock_espeak_tts):
        """Prueba generación de audio cuando está en caché (cache hit)."""
        cached_audio = b"cached audio data"
        cached_metadata = {"hits": 3, "size_bytes": len(cached_audio)}
        
        # Cache hit - hay datos en caché
        mock_redis.get.return_value = cached_audio
        mock_redis.hgetall.return_value = cached_metadata
        
        text = "Hello, this is a cached message"
        result = await audio_processor_with_cache.generate_audio_response(text, "test_content")
        
        # Debe devolver audio desde caché
        assert result == cached_audio
        
        # Debe obtener desde caché
        mock_redis.get.assert_called_once()
        
        # NO debe generar audio usando TTS
        mock_espeak_tts.synthesize.assert_not_called()
        
        # Debe incrementar contador de hits
        mock_redis.hincrby.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_different_content_types_different_cache_keys(self, audio_processor_with_cache, mock_redis):
        """Prueba que diferentes content_types generan claves de caché diferentes."""
        text = "Same text, different content types"
        
        # Generar para tipo 1
        await audio_processor_with_cache.generate_audio_response(text, "welcome_message")
        first_call_key = mock_redis.get.call_args[0][0]
        
        # Reset mock
        mock_redis.reset_mock()
        
        # Generar para tipo 2  
        await audio_processor_with_cache.generate_audio_response(text, "error_message")
        second_call_key = mock_redis.get.call_args[0][0]
        
        # Las claves deben ser iguales (content_type no afecta la clave, solo el TTL)
        assert first_call_key == second_call_key
        
    @pytest.mark.asyncio
    async def test_cache_stats_integration(self, audio_processor_with_cache, mock_redis):
        """Prueba obtener estadísticas de caché a través del procesador."""
        # Configurar mock para estadísticas
        mock_redis.scan.return_value = (0, ["audio_cache:key1", "audio_cache:key2"])
        mock_redis.memory_usage.side_effect = [1024, 2048]
        
        stats = await audio_processor_with_cache.get_cache_stats()
        
        assert "enabled" in stats
        assert "entries_count" in stats
        assert "total_size_bytes" in stats
        
    @pytest.mark.asyncio
    async def test_cache_clear_integration(self, audio_processor_with_cache, mock_redis):
        """Prueba limpiar caché a través del procesador."""
        mock_redis.scan.return_value = (0, ["audio_cache:key1", "audio_cache:key2"])
        mock_redis.delete.return_value = 2
        
        deleted_count = await audio_processor_with_cache.clear_audio_cache()
        
        assert deleted_count == 2
        mock_redis.delete.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_remove_specific_entry_integration(self, audio_processor_with_cache, mock_redis):
        """Prueba eliminar entrada específica a través del procesador."""
        mock_redis.delete.return_value = 1
        
        removed = await audio_processor_with_cache.remove_from_cache("test text", "default")
        
        assert removed is True
        # Debe eliminar tanto datos como metadatos
        assert mock_redis.delete.call_count == 2
        
    @pytest.mark.asyncio
    async def test_audio_disabled_bypasses_cache(self, audio_processor_with_cache, mock_redis):
        """Prueba que cuando el audio está deshabilitado, se omite la caché."""
        with patch('app.core.settings.settings.audio_enabled', False):
            result = await audio_processor_with_cache.generate_audio_response("test", "test_content")
            
            assert result is None
            # No debe interactuar con Redis en absoluto
            mock_redis.get.assert_not_called()
            mock_redis.set.assert_not_called()
            
    @pytest.mark.asyncio
    async def test_tts_failure_handling(self, audio_processor_with_cache, mock_redis, mock_espeak_tts):
        """Prueba manejo de errores cuando TTS falla."""
        # Cache miss
        mock_redis.get.return_value = None
        
        # TTS falla
        mock_espeak_tts.synthesize.side_effect = Exception("TTS failed")
        
        result = await audio_processor_with_cache.generate_audio_response("test", "test_content")
        
        assert result is None
        
        # Debe intentar caché pero no debe guardar nada por el error
        mock_redis.get.assert_called_once()
        mock_redis.set.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_cache_disabled_fallback_to_tts(self, mock_redis, mock_espeak_tts):
        """Prueba que cuando la caché está deshabilitada, funciona el TTS normal."""
        with patch('app.services.audio_cache_service.get_redis', return_value=mock_redis), \
             patch('app.services.audio_processor.ESpeakTTS', return_value=mock_espeak_tts), \
             patch('app.core.settings.settings.audio_cache_enabled', False):
            
            processor = AudioProcessor()
            
            result = await processor.generate_audio_response("test", "test_content")
            
            assert result == b"mock audio data"
            
            # Debe generar con TTS
            mock_espeak_tts.synthesize.assert_called_once()
            
            # No debe usar caché
            mock_redis.get.assert_not_called()
            mock_redis.set.assert_not_called()


@pytest.mark.integration
class TestAudioCacheMetrics:
    """Pruebas de métricas de caché de audio."""
    
    @pytest.mark.asyncio
    async def test_cache_hit_metrics(self, audio_processor_with_cache, mock_redis):
        """Prueba que se registran métricas de cache hit correctamente."""
        # Configurar cache hit
        mock_redis.get.return_value = b"cached audio"
        mock_redis.hgetall.return_value = {"hits": 5}
        
        with patch('app.services.audio_processor.AudioMetrics.record_cache_operation') as mock_metrics:
            await audio_processor_with_cache.generate_audio_response("test", "test_content")
            
            # Debe registrar cache hit
            mock_metrics.assert_called_with("get", "hit")
            
    @pytest.mark.asyncio
    async def test_cache_miss_metrics(self, audio_processor_with_cache, mock_redis, mock_espeak_tts):
        """Prueba que se registran métricas de cache miss correctamente."""
        # Configurar cache miss
        mock_redis.get.return_value = None
        
        with patch('app.services.audio_processor.AudioMetrics.record_cache_operation') as mock_metrics:
            await audio_processor_with_cache.generate_audio_response("test", "test_content")
            
            # Debe registrar cache miss
            mock_metrics.assert_called_with("get", "miss")