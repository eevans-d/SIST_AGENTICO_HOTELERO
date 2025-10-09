#!/usr/bin/env python3
"""
Runner independiente para pruebas de optimización de audio.
"""

import sys
import asyncio
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Imports directos sin pytest
from app.services.audio_cache_optimizer import (
    AudioCacheOptimizer, 
    AudioCacheType, 
    CacheStrategy,
    CacheEntry
)
from unittest.mock import Mock, AsyncMock
import time

async def test_basic_cache_operations():
    """Prueba operaciones básicas de caché."""
    print("🧪 Testando operaciones básicas de caché...")
    
    # Mock Redis
    redis_mock = Mock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    redis_mock.keys = AsyncMock(return_value=[])
    redis_mock.delete = AsyncMock()
    
    # Crear optimizador
    optimizer = AudioCacheOptimizer(
        redis_client=redis_mock,
        max_memory_mb=64,
        default_ttl=1800
    )
    
    await optimizer.start()
    
    try:
        # Test SET
        await optimizer.set(
            "test_key",
            "test_data",
            AudioCacheType.PROCESSED_AUDIO
        )
        
        # Test GET
        result = await optimizer.get(
            "test_key",
            AudioCacheType.PROCESSED_AUDIO
        )
        
        assert result == "test_data", f"Expected 'test_data', got {result}"
        print("✅ Operaciones básicas de caché: PASS")
        
    finally:
        await optimizer.stop()

async def test_cache_performance():
    """Prueba el rendimiento del caché."""
    print("🚀 Testando rendimiento de caché...")
    
    redis_mock = Mock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    redis_mock.keys = AsyncMock(return_value=[])
    redis_mock.delete = AsyncMock()
    
    optimizer = AudioCacheOptimizer(
        redis_client=redis_mock,
        max_memory_mb=32
    )
    
    await optimizer.start()
    
    try:
        # Medir tiempo de escritura
        start_time = time.time()
        
        for i in range(100):
            await optimizer.set(
                f"perf_key_{i}",
                f"perf_data_{i}" * 10,  # Datos más grandes
                AudioCacheType.PROCESSED_AUDIO
            )
        
        write_time = time.time() - start_time
        
        # Medir tiempo de lectura
        start_time = time.time()
        hits = 0
        
        for i in range(100):
            result = await optimizer.get(f"perf_key_{i}", AudioCacheType.PROCESSED_AUDIO)
            if result:
                hits += 1
        
        read_time = time.time() - start_time
        
        # Estadísticas
        stats = await optimizer.get_stats()
        
        print(f"📊 Resultados de Performance:")
        print(f"   - Escritura (100 ops): {write_time:.3f}s ({write_time*10:.1f}ms/op)")
        print(f"   - Lectura (100 ops): {read_time:.3f}s ({read_time*10:.1f}ms/op)")
        print(f"   - Cache hits: {hits}/100 ({hits}%)")
        print(f"   - Hit ratio total: {stats.get('cache_hit_ratio', 0):.3f}")
        print(f"   - Memory utilization: {stats.get('memory_utilization', 0):.3f}")
        
        # Verificar que es rápido
        assert write_time < 2.0, f"Escritura muy lenta: {write_time:.3f}s"
        assert read_time < 1.0, f"Lectura muy lenta: {read_time:.3f}s"
        assert hits > 90, f"Hit ratio muy bajo: {hits}/100"
        
        print("✅ Performance de caché: PASS")
        
    finally:
        await optimizer.stop()

async def test_concurrent_operations():
    """Prueba operaciones concurrentes."""
    print("🔄 Testando operaciones concurrentes...")
    
    redis_mock = Mock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    redis_mock.keys = AsyncMock(return_value=[])
    redis_mock.delete = AsyncMock()
    
    optimizer = AudioCacheOptimizer(redis_client=redis_mock)
    await optimizer.start()
    
    try:
        # Operaciones concurrentes
        async def concurrent_operation(i):
            await optimizer.set(f"concurrent_{i}", f"data_{i}", AudioCacheType.PROCESSED_AUDIO)
            result = await optimizer.get(f"concurrent_{i}", AudioCacheType.PROCESSED_AUDIO)
            return result == f"data_{i}"
        
        start_time = time.time()
        
        # Ejecutar 50 operaciones concurrentes
        tasks = [concurrent_operation(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        
        concurrent_time = time.time() - start_time
        successful = sum(results)
        
        print(f"📊 Resultados de Concurrencia:")
        print(f"   - Tiempo total: {concurrent_time:.3f}s")
        print(f"   - Operaciones exitosas: {successful}/50")
        print(f"   - Tiempo promedio por operación: {concurrent_time/50*1000:.1f}ms")
        
        # Verificar resultados
        assert successful == 50, f"Solo {successful}/50 operaciones exitosas"
        assert concurrent_time < 5.0, f"Operaciones concurrentes muy lentas: {concurrent_time:.3f}s"
        
        print("✅ Operaciones concurrentes: PASS")
        
    finally:
        await optimizer.stop()

async def test_cache_strategies():
    """Prueba diferentes estrategias de caché."""
    print("🎯 Testando estrategias de caché...")
    
    redis_mock = Mock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    redis_mock.keys = AsyncMock(return_value=[])
    redis_mock.delete = AsyncMock()
    
    optimizer = AudioCacheOptimizer(redis_client=redis_mock)
    await optimizer.start()
    
    try:
        strategies = [CacheStrategy.LRU, CacheStrategy.LFU, CacheStrategy.ADAPTIVE]
        
        for strategy in strategies:
            key = f"test_{strategy.value}"
            await optimizer.set(
                key,
                f"data_{strategy.value}",
                AudioCacheType.TRANSCRIPTION,
                strategy=strategy
            )
            
            result = await optimizer.get(
                key,
                AudioCacheType.TRANSCRIPTION,
                strategy
            )
            
            assert result == f"data_{strategy.value}", f"Estrategia {strategy.value} falló"
            print(f"   ✅ Estrategia {strategy.value}: OK")
        
        print("✅ Estrategias de caché: PASS")
        
    finally:
        await optimizer.stop()

async def main():
    """Ejecuta todas las pruebas de optimización."""
    print("🚀 INICIANDO PRUEBAS DE OPTIMIZACIÓN DE AUDIO")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        await test_basic_cache_operations()
        print()
        
        await test_cache_performance()
        print()
        
        await test_concurrent_operations()
        print()
        
        await test_cache_strategies()
        print()
        
        total_time = time.time() - start_time
        
        print("=" * 60)
        print(f"🎉 TODAS LAS PRUEBAS PASARON EN {total_time:.3f}s")
        print("✅ Sistema de optimización de audio funcionando correctamente")
        
    except Exception as e:
        print(f"❌ PRUEBA FALLIDA: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())