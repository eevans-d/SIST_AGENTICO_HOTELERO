# tests/unit/test_audio_cache_service.py

import pytest
from unittest.mock import AsyncMock, patch
from app.services.audio_cache_service import AudioCacheService


@pytest.fixture
def mock_redis():
    """Mock Redis client para pruebas."""
    redis_mock = AsyncMock()
    
    # Mock para operaciones básicas
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = 1
    redis_mock.expire.return_value = True
    redis_mock.scan.return_value = (0, [])
    redis_mock.memory_usage.return_value = 1024
    
    # Mock para operaciones hash
    redis_mock.hset.return_value = 1
    redis_mock.hincrby.return_value = 1
    redis_mock.hgetall.return_value = {}
    
    return redis_mock


@pytest.fixture
async def audio_cache_service(mock_redis):
    """Instancia del servicio de caché con Redis mockeado."""
    with patch('app.services.audio_cache_service.get_redis', return_value=mock_redis):
        service = AudioCacheService()
        yield service


class TestAudioCacheService:
    """Pruebas para el servicio de caché de audio."""
    
    @pytest.mark.asyncio
    async def test_cache_disabled(self, audio_cache_service, mock_redis):
        """Prueba que el caché se comporta correctamente cuando está deshabilitado."""
        # Simular caché deshabilitado
        audio_cache_service._enabled = False
        
        # Intentar obtener desde caché
        result = await audio_cache_service.get("test text")
        assert result is None
        
        # Intentar guardar en caché
        success = await audio_cache_service.set("test text", b"audio data")
        assert success is False
        
        # Verificar que no se llamó a Redis
        mock_redis.get.assert_not_called()
        mock_redis.set.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cache_miss(self, audio_cache_service, mock_redis):
        """Prueba el comportamiento cuando no hay datos en caché."""
        mock_redis.get.return_value = None
        
        result = await audio_cache_service.get("test text")
        assert result is None
        
        # Verificar que se intentó obtener la clave correcta
        mock_redis.get.assert_called_once()
        cache_key = mock_redis.get.call_args[0][0]
        assert cache_key.startswith(AudioCacheService.CACHE_PREFIX)
    
    @pytest.mark.asyncio
    async def test_cache_hit(self, audio_cache_service, mock_redis):
        """Prueba el comportamiento cuando hay un hit en caché."""
        test_audio_data = b"test audio content"
        test_metadata = {"hits": 5, "size_bytes": len(test_audio_data)}
        
        # Configurar mock para devolver datos
        mock_redis.get.return_value = test_audio_data
        mock_redis.hgetall.return_value = test_metadata
        
        result = await audio_cache_service.get("test text")
        
        assert result is not None
        audio_data, metadata = result
        assert audio_data == test_audio_data
        assert metadata == test_metadata
        
        # Verificar que se incrementó el contador de hits
        mock_redis.hincrby.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_set_success(self, audio_cache_service, mock_redis):
        """Prueba guardar datos en caché exitosamente."""
        test_text = "Hello, world!"
        test_audio_data = b"audio data content"
        test_metadata = {"created_at": 1234567890}
        
        mock_redis.set.return_value = True
        
        success = await audio_cache_service.set(
            test_text, 
            test_audio_data, 
            metadata=test_metadata
        )
        
        assert success is True
        
        # Verificar que se llamó a set con TTL correcto
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[1]['ex'] == audio_cache_service._default_ttl
        
        # Verificar que se guardaron los metadatos
        mock_redis.hset.assert_called()
        mock_redis.expire.assert_called()
    
    @pytest.mark.asyncio
    async def test_cache_set_large_file(self, audio_cache_service, mock_redis):
        """Prueba que archivos muy grandes no se almacenan en caché."""
        large_audio_data = b"x" * (AudioCacheService.MAX_CACHE_SIZE_BYTES + 1)
        
        success = await audio_cache_service.set("test", large_audio_data)
        
        assert success is False
        mock_redis.set.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, audio_cache_service):
        """Prueba la generación de claves de caché."""
        text1 = "Hello world"
        text2 = "Hello world"
        text3 = "Different text"
        
        key1 = audio_cache_service._get_cache_key(text1, "voice1")
        key2 = audio_cache_service._get_cache_key(text2, "voice1")
        key3 = audio_cache_service._get_cache_key(text1, "voice2")
        key4 = audio_cache_service._get_cache_key(text3, "voice1")
        
        # Mismo texto y voz deben generar la misma clave
        assert key1 == key2
        
        # Diferente voz debe generar clave diferente
        assert key1 != key3
        
        # Diferente texto debe generar clave diferente
        assert key1 != key4
        
        # Todas las claves deben tener el prefijo correcto
        assert key1.startswith(AudioCacheService.CACHE_PREFIX)
        assert key3.startswith(AudioCacheService.CACHE_PREFIX)
        assert key4.startswith(AudioCacheService.CACHE_PREFIX)
    
    @pytest.mark.asyncio
    async def test_ttl_by_content_type(self, audio_cache_service):
        """Prueba que el TTL se configura correctamente según el tipo de contenido."""
        # Tipo de contenido con TTL específico
        ttl_welcome = audio_cache_service._get_ttl("welcome_message")
        assert ttl_welcome == AudioCacheService.TTL_CONFIG["welcome_message"]
        
        # Tipo de contenido sin TTL específico
        ttl_default = audio_cache_service._get_ttl("unknown_type")
        assert ttl_default == audio_cache_service._default_ttl
        
        # Sin tipo de contenido
        ttl_none = audio_cache_service._get_ttl(None)
        assert ttl_none == audio_cache_service._default_ttl
    
    @pytest.mark.asyncio
    async def test_delete_cache_entry(self, audio_cache_service, mock_redis):
        """Prueba eliminar una entrada específica de caché."""
        mock_redis.delete.return_value = 1  # Simuliar que se eliminó 1 clave
        
        result = await audio_cache_service.delete("test text", "default")
        
        assert result is True
        
        # Verificar que se eliminaron tanto los datos como los metadatos
        assert mock_redis.delete.call_count == 2
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_entry(self, audio_cache_service, mock_redis):
        """Prueba eliminar una entrada que no existe."""
        mock_redis.delete.return_value = 0  # No se eliminó nada
        
        result = await audio_cache_service.delete("nonexistent", "default")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_clear_cache(self, audio_cache_service, mock_redis):
        """Prueba limpiar toda la caché."""
        # Simular que hay 5 entradas en caché
        mock_redis.scan.return_value = (0, [
            f"{AudioCacheService.CACHE_PREFIX}key1",
            f"{AudioCacheService.CACHE_PREFIX}key2",
            f"{AudioCacheService.CACHE_PREFIX}key1:meta",
            f"{AudioCacheService.CACHE_PREFIX}key2:meta",
            "other_key"  # Esta no debería contarse
        ])
        mock_redis.delete.return_value = 4  # Se eliminaron 4 claves
        
        deleted_count = await audio_cache_service.clear_cache()
        
        assert deleted_count == 4
        mock_redis.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_stats(self, audio_cache_service, mock_redis):
        """Prueba obtener estadísticas de la caché."""
        # Simular datos de estadísticas
        mock_redis.scan.return_value = (0, [
            f"{AudioCacheService.CACHE_PREFIX}key1",
            f"{AudioCacheService.CACHE_PREFIX}key2"
        ])
        mock_redis.memory_usage.side_effect = [1024, 2048]  # Tamaños de las claves
        
        stats = await audio_cache_service.get_stats()
        
        assert stats["enabled"] is True
        assert stats["entries_count"] == 2
        assert stats["total_size_bytes"] == 3072
        assert "total_size_mb" in stats
        assert "max_entry_size_mb" in stats
    
    @pytest.mark.asyncio
    async def test_get_stats_error_handling(self, audio_cache_service, mock_redis):
        """Prueba manejo de errores al obtener estadísticas."""
        mock_redis.scan.side_effect = Exception("Redis error")
        
        stats = await audio_cache_service.get_stats()
        
        assert "error" in stats
        assert stats["enabled"] is True
    
    @pytest.mark.asyncio
    async def test_redis_connection_error(self, audio_cache_service):
        """Prueba manejo de errores de conexión a Redis."""
        with patch('app.services.audio_cache_service.get_redis', side_effect=Exception("Connection failed")):
            # Las operaciones deben fallar graciosamente
            result = await audio_cache_service.get("test")
            assert result is None
            
            success = await audio_cache_service.set("test", b"data")
            assert success is False


@pytest.mark.integration
class TestAudioCacheIntegration:
    """Pruebas de integración para el servicio de caché de audio."""
    
    @pytest.mark.asyncio
    async def test_full_cache_workflow(self, audio_cache_service, mock_redis):
        """Prueba el flujo completo de caché: set -> get -> delete."""
        test_text = "Integration test text"
        test_audio = b"integration test audio data"
        test_metadata = {"test": "metadata"}
        
        # Configurar mocks para el flujo completo
        mock_redis.set.return_value = True
        mock_redis.get.return_value = test_audio
        mock_redis.hgetall.return_value = test_metadata
        mock_redis.delete.return_value = 2
        
        # 1. Guardar en caché
        success = await audio_cache_service.set(
            test_text, 
            test_audio, 
            metadata=test_metadata
        )
        assert success is True
        
        # 2. Obtener desde caché
        result = await audio_cache_service.get(test_text)
        assert result is not None
        audio_data, metadata = result
        assert audio_data == test_audio
        
        # 3. Eliminar de caché
        deleted = await audio_cache_service.delete(test_text)
        assert deleted is True
        
        # 4. Verificar que ya no está en caché
        mock_redis.get.return_value = None
        result = await audio_cache_service.get(test_text)
        assert result is None