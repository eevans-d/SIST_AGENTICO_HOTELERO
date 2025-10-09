import pytest
from unittest.mock import patch, AsyncMock
from app.services.audio_cache_service import AudioCacheService

pytestmark = pytest.mark.asyncio

class TestAudioCompression:
    
    async def test_compression_enabled(self):
        """Prueba que la compresión se active correctamente cuando está habilitada"""
        # Configurar mock para Redis
        with patch('app.services.audio_cache_service.get_redis') as mock_get_redis:
            # Crear mock de cliente Redis
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis
            
            # Crear servicio con compresión habilitada
            service = AudioCacheService()
            service._compression_enabled = True
            service._compression_threshold_kb = 1  # Comprimir todo lo que supere 1KB
            service._compression_level = 6
            
            # Crear datos de prueba (2KB)
            test_data = b'x' * 2048
            
            # Verificar que se debe comprimir
            assert service._should_compress(test_data)
            
            # Comprimir datos
            compressed = service._compress_data(test_data)
            
            # Verificar que se comprimió (prefijo c:)
            assert compressed[:2] == b'c:'
            assert len(compressed) < len(test_data)
            
            # Descomprimir
            decompressed = service._decompress_data(compressed)
            
            # Verificar que los datos son iguales después de descomprimir
            assert decompressed == test_data
    
    async def test_compression_disabled(self):
        """Prueba que la compresión no se active cuando está deshabilitada"""
        # Configurar mock para Redis
        with patch('app.services.audio_cache_service.get_redis') as mock_get_redis:
            # Crear mock de cliente Redis
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis
            
            # Crear servicio con compresión deshabilitada
            service = AudioCacheService()
            service._compression_enabled = False
            
            # Crear datos de prueba (2KB)
            test_data = b'x' * 2048
            
            # Verificar que no se debe comprimir
            assert not service._should_compress(test_data)
    
    async def test_threshold_enforcement(self):
        """Prueba que la compresión solo se active cuando se supera el umbral"""
        # Configurar mock para Redis
        with patch('app.services.audio_cache_service.get_redis') as mock_get_redis:
            # Crear mock de cliente Redis
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis
            
            # Crear servicio con compresión habilitada
            service = AudioCacheService()
            service._compression_enabled = True
            service._compression_threshold_kb = 5  # Comprimir lo que supere 5KB
            
            # Datos pequeños (1KB)
            small_data = b'x' * 1024
            
            # Datos grandes (10KB)
            large_data = b'x' * 10240
            
            # Verificar que solo se comprimen datos grandes
            assert not service._should_compress(small_data)
            assert service._should_compress(large_data)
    
    async def test_cache_set_with_compression(self):
        """Prueba que set() use compresión cuando corresponda"""
        # Configurar mock para Redis
        with patch('app.services.audio_cache_service.get_redis') as mock_get_redis:
            # Crear mock de cliente Redis
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis
            
            # Crear servicio con compresión habilitada
            service = AudioCacheService()
            service._enabled = True
            service._compression_enabled = True
            service._compression_threshold_kb = 1  # Comprimir todo lo que supere 1KB
            service._compression_level = 6
            
            # Crear datos de prueba (2KB)
            test_data = b'x' * 2048
            
            # Llamar a set()
            result = await service.set(
                text="texto de prueba",
                audio_data=test_data,
                voice="es",
                content_type="test"
            )
            
            # Verificar que set tuvo éxito
            assert result
            
            # Verificar que se llamó a Redis.set con datos comprimidos
            # (no podemos verificar el contenido exacto porque es generado dinámicamente,
            # pero podemos comprobar que se llamó a la función)
            mock_redis.set.assert_called_once()
            
            # Verificar que se guardó metadata con el campo 'compressed'
            any_metadata_call = False
            for call in mock_redis.hset.call_args_list:
                args, kwargs = call
                if len(args) >= 3 and args[1] == 'compressed':
                    any_metadata_call = True
                    assert args[2]
            
            assert any_metadata_call, "No se encontró llamada para guardar metadata de compresión"
            
    async def test_cache_get_with_decompression(self):
        """Prueba que get() descomprima automáticamente"""
        # Configurar mock para Redis
        with patch('app.services.audio_cache_service.get_redis') as mock_get_redis:
            # Crear mock de cliente Redis
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis
            
            # Datos de prueba originales
            original_data = b'x' * 2048
            
            # Datos comprimidos simulados (con prefijo c:)
            import zlib
            compressed_data = b'c:' + zlib.compress(original_data, level=6)
            
            # Configurar mock para devolver datos comprimidos
            mock_redis.get.return_value = compressed_data
            
            # Configurar mock para metadata
            mock_redis.hgetall.return_value = {
                b'compressed': b'True',
                b'size_bytes': str(len(compressed_data)).encode(),
                b'original_size': str(len(original_data)).encode(),
                b'hits': b'0'
            }
            
            # Crear servicio
            service = AudioCacheService()
            service._enabled = True
            service._compression_enabled = True
            
            # Llamar a get()
            result = await service.get(
                text="texto de prueba",
                voice="es"
            )
            
            # Verificar que get tuvo éxito
            assert result is not None
            
            # Verificar que los datos fueron descomprimidos
            data, metadata = result
            assert data == original_data
            assert metadata['compressed'] == 'True'  # Redis devuelve string 'True', no booleano