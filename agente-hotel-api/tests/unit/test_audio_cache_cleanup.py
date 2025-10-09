import pytest
from unittest.mock import patch, AsyncMock
from app.services.audio_cache_service import AudioCacheService

pytestmark = pytest.mark.asyncio

# Test para el comportamiento de limpieza automática
class TestAudioCacheCleanup:
    
    async def test_check_and_cleanup_cache(self):
        # Crear servicio de caché
        service = AudioCacheService()
        service._enabled = True
        
        # Mock para Redis
        with patch('app.services.audio_cache_service.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis
            
            # Mock de get_cache_stats para devolver un tamaño que NO exceda el umbral
            with patch.object(service, 'get_cache_stats') as mock_stats:
                mock_stats.return_value = {
                    'total_size_mb': 0.3,  # No excede el umbral por defecto
                    'total_entries': 5,
                    'hit_rate_percent': 75.0
                }
                
                # Ejecutar con tamaño pequeño
                result = await service._check_and_cleanup_cache(50000)  # 50KB
                
                # Verificar que no es necesaria la limpieza
                assert result['status'] == 'not_needed'
    
    async def test_cleanup_not_needed(self):
        # Configurar mock para Redis
        with patch('app.services.audio_cache_service.get_redis') as mock_get_redis:
            # Crear mock de cliente Redis
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis
            
            # Configurar respuesta para scan (devuelve algunas claves)
            mock_redis.scan.side_effect = [
                (0, [b'audio_cache:key1', b'audio_cache:key1:meta'])
            ]
            
            # Configurar respuesta para strlen (tamaño pequeño)
            mock_redis.pipeline.return_value.execute.side_effect = [
                [100000],  # 100KB (muy por debajo del umbral)
            ]
            
            # Crear servicio de caché con configuraciones específicas para testing
            service = AudioCacheService()
            service._max_cache_size_mb = 10  # 10MB máximo
            service._cleanup_threshold_percent = 90  # Limpiar al 90% (9MB)
            
            # Ejecutar la limpieza automática
            result = await service._check_and_cleanup_cache(0)
            
            # Verificar que no fue necesaria la limpieza
            assert result['status'] == 'not_needed'
            
            # Verificar que no se llamaron métodos de eliminación
            mock_redis.delete.assert_not_called()
    
    async def test_cleanup_disabled(self):
        # Crear servicio de caché con limpieza desactivada
        service = AudioCacheService()
        service._enabled = False
        
        # Ejecutar la limpieza automática
        result = await service._check_and_cleanup_cache(0)
        
        # Verificar que la limpieza está desactivada
        assert result['status'] == 'disabled'
    
    async def test_cleanup_with_lock(self):
        # Crear servicio de caché
        service = AudioCacheService()
        service._enabled = True
        
        # Adquirir el lock manualmente
        await service._cleanup_lock.acquire()
        
        try:
            # Ejecutar la limpieza automática (debería detectar que ya hay una limpieza en curso)
            result = await service._check_and_cleanup_cache(0)
            
            # Verificar que se detectó el lock (ajustado al mensaje real del código)
            assert result['status'] == 'already_running'
        finally:
            # Liberar el lock
            service._cleanup_lock.release()