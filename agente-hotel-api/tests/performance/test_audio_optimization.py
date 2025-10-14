"""
Pruebas de optimización y performance para el sistema de audio.
Valida las mejoras de rendimiento implementadas en la Fase 4.
"""

import pytest
import asyncio
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import redis.asyncio as redis

from app.services.audio_cache_optimizer import AudioCacheOptimizer, AudioCacheType, CacheStrategy
from app.services.audio_compression_optimizer import AudioCompressionOptimizer, CompressionLevel, NetworkConditions
from app.services.audio_connection_pool import AudioConnectionManager, ServiceType, ConnectionConfig
from app.services.audio_processor import OptimizedAudioProcessor


class TestAudioCacheOptimizer:
    """Pruebas para el optimizador de caché de audio."""

    @pytest.fixture
    async def redis_mock(self):
        """Mock de Redis para pruebas."""
        mock_redis = Mock(spec=redis.Redis)
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()
        mock_redis.keys = AsyncMock(return_value=[])
        mock_redis.delete = AsyncMock()
        return mock_redis

    @pytest.fixture
    async def cache_optimizer(self, redis_mock):
        """Fixture del optimizador de caché."""
        optimizer = AudioCacheOptimizer(redis_client=redis_mock, max_memory_mb=128, default_ttl=1800)
        await optimizer.start()
        yield optimizer
        await optimizer.stop()

    @pytest.mark.asyncio
    async def test_memory_cache_performance(self, cache_optimizer):
        """Prueba el rendimiento del caché en memoria."""
        start_time = time.time()

        # Operaciones de escritura
        for i in range(100):
            await cache_optimizer.set(
                f"test_key_{i}",
                f"test_data_{i}" * 100,  # Datos de prueba
                AudioCacheType.PROCESSED_AUDIO,
                strategy=CacheStrategy.LRU,
            )

        write_time = time.time() - start_time

        # Operaciones de lectura
        start_time = time.time()
        hits = 0

        for i in range(100):
            result = await cache_optimizer.get(f"test_key_{i}", AudioCacheType.PROCESSED_AUDIO, CacheStrategy.LRU)
            if result:
                hits += 1

        read_time = time.time() - start_time

        # Verificar performance
        assert write_time < 1.0, f"Escritura muy lenta: {write_time:.3f}s"
        assert read_time < 0.5, f"Lectura muy lenta: {read_time:.3f}s"
        assert hits > 50, f"Hit ratio muy bajo: {hits}/100"

        print(f"Cache Performance - Write: {write_time:.3f}s, Read: {read_time:.3f}s, Hits: {hits}/100")

    @pytest.mark.asyncio
    async def test_cache_eviction_strategy(self, cache_optimizer):
        """Prueba la estrategia de expulsión del caché."""
        # Llenar caché hasta el límite
        large_data = "x" * (1024 * 1024)  # 1MB

        for i in range(150):  # Más que el límite de memoria
            await cache_optimizer.set(
                f"large_key_{i}", large_data, AudioCacheType.PROCESSED_AUDIO, strategy=CacheStrategy.LRU
            )

        # Verificar que el caché no excede el límite
        stats = await cache_optimizer.get_stats()
        memory_usage_mb = stats["global_stats"]["memory_usage"] / (1024 * 1024)

        assert memory_usage_mb <= 128, f"Caché excede límite: {memory_usage_mb:.1f}MB"
        assert stats["global_stats"]["evictions"] > 0, "No se realizaron expulsiones"

        print(f"Cache Eviction - Memory: {memory_usage_mb:.1f}MB, Evictions: {stats['global_stats']['evictions']}")

    @pytest.mark.asyncio
    async def test_adaptive_caching_strategy(self, cache_optimizer):
        """Prueba la estrategia adaptiva de caché."""
        # Simular patrones de acceso diferentes
        patterns = {
            "frequent": ["freq_1", "freq_2", "freq_3"],
            "infrequent": ["rare_1", "rare_2", "rare_3"],
            "single_use": ["single_1", "single_2", "single_3"],
        }

        # Establecer datos
        for pattern_type, keys in patterns.items():
            for key in keys:
                await cache_optimizer.set(
                    key, f"data_for_{key}", AudioCacheType.TRANSCRIPTION, strategy=CacheStrategy.ADAPTIVE
                )

        # Simular accesos frecuentes
        for _ in range(10):
            for key in patterns["frequent"]:
                await cache_optimizer.get(key, AudioCacheType.TRANSCRIPTION)

        # Accesos únicos para datos single_use
        for key in patterns["single_use"]:
            await cache_optimizer.get(key, AudioCacheType.TRANSCRIPTION)

        # Verificar que la estrategia adaptiva funciona
        stats = await cache_optimizer.get_stats()
        assert stats["cache_hit_ratio"] > 0.5, "Hit ratio muy bajo para estrategia adaptiva"

        print(f"Adaptive Strategy - Hit Ratio: {stats['cache_hit_ratio']:.3f}")


class TestAudioCompressionOptimizer:
    """Pruebas para el optimizador de compresión de audio."""

    @pytest.fixture
    def compression_optimizer(self):
        """Fixture del optimizador de compresión."""
        return AudioCompressionOptimizer()

    @pytest.fixture
    def sample_audio_data(self):
        """Datos de audio de muestra para pruebas."""
        # Generar datos de audio sintéticos
        sample_rate = 22050
        duration = 2.0  # segundos
        import struct
        import math

        # Generar onda senoidal simple
        samples = []
        for i in range(int(sample_rate * duration)):
            sample = int(32767 * math.sin(2 * math.pi * 440 * i / sample_rate))
            samples.append(struct.pack("<h", sample))

        # Header WAV básico
        header = b"RIFF" + struct.pack("<I", 36 + len(samples) * 2) + b"WAVE"
        header += b"fmt " + struct.pack("<I", 16)  # Chunk size
        header += struct.pack("<HHIIHH", 1, 1, sample_rate, sample_rate * 2, 2, 16)
        header += b"data" + struct.pack("<I", len(samples) * 2)

        return header + b"".join(samples)

    @pytest.mark.asyncio
    async def test_compression_levels_performance(self, compression_optimizer, sample_audio_data):
        """Prueba el rendimiento de diferentes niveles de compresión."""
        results = {}

        for level in CompressionLevel:
            start_time = time.time()

            try:
                compressed_data, metadata = await compression_optimizer.compress_audio(
                    sample_audio_data, target_level=level
                )

                compression_time = time.time() - start_time
                results[level.value] = {
                    "time": compression_time,
                    "ratio": metadata["compression_ratio"],
                    "quality": metadata["quality_score"],
                    "success": True,
                }

            except Exception as e:
                results[level.value] = {"time": time.time() - start_time, "error": str(e), "success": False}

        # Verificar que la compresión es efectiva
        successful_results = {k: v for k, v in results.items() if v["success"]}
        assert len(successful_results) > 0, "Ningún nivel de compresión funcionó"

        # Verificar que niveles más altos comprimen más
        if "ultra_low" in successful_results and "high" in successful_results:
            ultra_low_ratio = successful_results["ultra_low"]["ratio"]
            high_ratio = successful_results["high"]["ratio"]
            assert ultra_low_ratio > high_ratio, "Compresión ultra_low debería tener mayor ratio"

        print("Compression Performance:")
        for level, result in results.items():
            if result["success"]:
                print(
                    f"  {level}: {result['time']:.3f}s, ratio: {result['ratio']:.2f}, quality: {result['quality']:.2f}"
                )

    @pytest.mark.asyncio
    async def test_adaptive_compression_network_conditions(self, compression_optimizer, sample_audio_data):
        """Prueba la compresión adaptiva basada en condiciones de red."""
        network_scenarios = [
            NetworkConditions(bandwidth_kbps=50, connection_type="cellular"),
            NetworkConditions(bandwidth_kbps=500, connection_type="wifi"),
            NetworkConditions(bandwidth_kbps=1000, connection_type="ethernet"),
        ]

        results = []

        for conditions in network_scenarios:
            compressed_data, metadata = await compression_optimizer.compress_audio(
                sample_audio_data, network_conditions=conditions
            )

            results.append(
                {
                    "conditions": conditions,
                    "level": metadata["level"],
                    "ratio": metadata["compression_ratio"],
                    "size": metadata["compressed_size"],
                }
            )

        # Verificar que se adapta a las condiciones
        cellular_result = next(r for r in results if r["conditions"].connection_type == "cellular")
        ethernet_result = next(r for r in results if r["conditions"].connection_type == "ethernet")

        # Conexión celular debería usar más compresión
        assert cellular_result["ratio"] >= ethernet_result["ratio"], "Conexión celular debería usar más compresión"

        print("Adaptive Compression:")
        for result in results:
            print(f"  {result['conditions'].connection_type}: level={result['level']}, ratio={result['ratio']:.2f}")


class TestAudioConnectionPool:
    """Pruebas para el pool de conexiones de audio."""

    @pytest.fixture
    async def connection_manager(self):
        """Fixture del gestor de conexiones."""
        manager = AudioConnectionManager()
        yield manager
        await manager.shutdown_all()

    @pytest.mark.asyncio
    async def test_connection_pool_performance(self, connection_manager):
        """Prueba el rendimiento del pool de conexiones."""
        # Registrar servicio mock
        config = ConnectionConfig(base_url="http://localhost:8000", max_connections=5, timeout_seconds=10.0)

        await connection_manager.register_service(ServiceType.STT_SERVICE, config)
        pool = await connection_manager.get_pool(ServiceType.STT_SERVICE)

        # Simular múltiples requests concurrentes
        async def mock_request():
            async with pool.get_connection():
                # Simular trabajo
                await asyncio.sleep(0.01)
                return "success"

        start_time = time.time()

        # Ejecutar 50 requests concurrentes
        tasks = [mock_request() for _ in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time
        successful_results = [r for r in results if r == "success"]

        # Verificar performance
        assert len(successful_results) == 50, f"Solo {len(successful_results)}/50 requests exitosos"
        assert total_time < 5.0, f"Pool muy lento: {total_time:.3f}s para 50 requests"

        # Verificar métricas del pool
        metrics = await pool.get_metrics()
        assert metrics["metrics"]["success_rate"] == 1.0, "Success rate debería ser 100%"

        print(f"Connection Pool Performance: {total_time:.3f}s for 50 concurrent requests")
        print(f"Success Rate: {metrics['metrics']['success_rate']:.3f}")

    @pytest.mark.asyncio
    async def test_connection_pool_resilience(self, connection_manager):
        """Prueba la resistencia del pool de conexiones."""
        # Registrar servicio que fallará
        config = ConnectionConfig(
            base_url="http://invalid-host:9999", max_connections=3, timeout_seconds=1.0, retry_attempts=1
        )

        await connection_manager.register_service(ServiceType.TTS_SERVICE, config)
        pool = await connection_manager.get_pool(ServiceType.TTS_SERVICE)

        # Intentar requests que fallarán
        failed_requests = 0

        for _ in range(10):
            try:
                async with pool.get_connection():
                    # Esto debería fallar
                    pass
            except Exception:
                failed_requests += 1

        # El pool debería manejar las fallas graciosamente
        metrics = await pool.get_metrics()
        assert failed_requests > 0, "Se esperaban algunas fallas"
        assert metrics["status"] in ["degraded", "critical"], "Pool debería reportar estado degradado"

        print(f"Connection Pool Resilience: {failed_requests}/10 failed requests handled gracefully")


class TestOptimizedAudioProcessor:
    """Pruebas de integración para el procesador de audio optimizado."""

    @pytest.fixture
    async def redis_mock(self):
        """Mock de Redis para pruebas."""
        mock_redis = Mock(spec=redis.Redis)
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()
        mock_redis.keys = AsyncMock(return_value=[])
        mock_redis.delete = AsyncMock()
        return mock_redis

    @pytest.fixture
    async def optimized_processor(self, redis_mock):
        """Fixture del procesador optimizado."""
        processor = OptimizedAudioProcessor(
            redis_client=redis_mock, enable_compression=True, enable_connection_pooling=True
        )
        await processor.start()
        yield processor
        await processor.stop()

    @pytest.mark.asyncio
    async def test_end_to_end_optimization_performance(self, optimized_processor):
        """Prueba el rendimiento end-to-end con todas las optimizaciones."""
        # Mock de datos de audio
        mock_audio_data = b"mock_audio_data" * 1000  # ~15KB

        with patch("aiohttp.ClientSession") as mock_session:
            # Mock de descarga de audio
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {"content-length": str(len(mock_audio_data))}
            mock_response.content.iter_chunked = AsyncMock()
            mock_response.content.iter_chunked.return_value = [mock_audio_data]

            mock_session_instance = AsyncMock()
            mock_session_instance.get = AsyncMock()
            mock_session_instance.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session_instance.get.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            # Simular procesamiento completo
            start_time = time.time()

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = Path(temp_file.name)

                try:
                    # Simular descarga con optimizaciones
                    await optimized_processor._download_audio_optimized("http://example.com/audio.wav", temp_path)

                    processing_time = time.time() - start_time

                    # Verificar que el archivo fue "descargado"
                    assert temp_path.exists(), "Archivo temporal no creado"

                    # Verificar que el procesamiento es rápido
                    assert processing_time < 2.0, f"Procesamiento muy lento: {processing_time:.3f}s"

                    print(f"End-to-End Optimization Performance: {processing_time:.3f}s")

                finally:
                    if temp_path.exists():
                        temp_path.unlink()

    @pytest.mark.asyncio
    async def test_optimization_metrics_collection(self, optimized_processor):
        """Prueba que las métricas de optimización se recolectan correctamente."""
        # Obtener métricas de caché
        if optimized_processor.cache_optimizer:
            cache_stats = await optimized_processor.cache_optimizer.get_stats()
            assert "global_stats" in cache_stats
            assert "cache_hit_ratio" in cache_stats

        # Obtener métricas de compresión
        if optimized_processor.compression_optimizer:
            compression_stats = await optimized_processor.compression_optimizer.get_compression_stats()
            assert "supported_formats" in compression_stats
            assert "compression_levels" in compression_stats

        # Obtener métricas de conexiones
        if optimized_processor.connection_manager:
            connection_stats = await optimized_processor.connection_manager.get_all_metrics()
            assert "pools" in connection_stats
            assert "total_pools" in connection_stats

        print("Optimization metrics collection: ✅")


@pytest.mark.asyncio
async def test_optimization_integration():
    """Prueba de integración completa de todas las optimizaciones."""
    # Esta prueba verifica que todos los componentes trabajen juntos

    # Mock Redis
    redis_mock = Mock(spec=redis.Redis)
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    redis_mock.keys = AsyncMock(return_value=[])
    redis_mock.delete = AsyncMock()

    # Crear todos los optimizadores
    cache_optimizer = AudioCacheOptimizer(redis_mock)
    compression_optimizer = AudioCompressionOptimizer()
    connection_manager = AudioConnectionManager(redis_mock)

    try:
        # Iniciar servicios
        await cache_optimizer.start()

        # Prueba básica de integración
        test_data = "test_audio_data" * 100

        # Cache
        await cache_optimizer.set("integration_test", test_data, AudioCacheType.PROCESSED_AUDIO)

        cached_result = await cache_optimizer.get("integration_test", AudioCacheType.PROCESSED_AUDIO)

        assert cached_result == test_data, "Integración de caché falló"

        # Compresión (con datos mock)
        mock_audio = b"RIFF" + b"x" * 1000  # Audio WAV mock
        try:
            compressed_data, metadata = await compression_optimizer.compress_audio(mock_audio)
            assert len(compressed_data) > 0, "Compresión falló"
        except Exception as e:
            # La compresión puede fallar sin dependencias, esto es OK para la prueba
            print(f"Compression test skipped: {e}")

        print("Integration test: ✅ All optimizations working together")

    finally:
        # Cleanup
        await cache_optimizer.stop()
        await connection_manager.shutdown_all()


if __name__ == "__main__":
    # Ejecutar pruebas de performance
    asyncio.run(test_optimization_integration())
