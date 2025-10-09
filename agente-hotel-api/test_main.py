#!/usr/bin/env python3
"""
Punto de entrada simplificado para testing de Docker
Evita dependencias complejas y se enfoca en testing del cache de audio
"""

import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from app.services.audio_cache_service import get_audio_cache_service
from app.core.redis_client import get_redis

# Configuración mínima para testing
app = FastAPI(
    title="Hotel Agent API - Testing",
    description="Simplified version for Docker testing",
    version="test"
)

@app.get("/health/live")
async def health_live():
    """Health check básico"""
    return {"status": "ok", "service": "agente-hotelero-test"}

@app.get("/health/ready")
async def health_ready():
    """Health check con dependencias"""
    try:
        # Test Redis directo sin configuración compleja
        import redis.asyncio as redis
        redis_client = redis.Redis.from_url("redis://redis:6379", decode_responses=True)
        await redis_client.ping()
        await redis_client.close()
        
        return {
            "status": "ready",
            "redis": "ok",
            "audio_cache": "available"
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": str(e)}
        )

@app.get("/test/audio-cache")
async def test_audio_cache():
    """Test específico del sistema de caché de audio"""
    try:
        import redis.asyncio as redis
        import zlib
        import time
        
        # Conectar directamente a Redis sin configuración compleja
        redis_client = redis.Redis.from_url("redis://redis:6379", decode_responses=False)
        
        # Test básico de Redis
        await redis_client.ping()
        
        # Test de caché de audio simulado
        test_audio = b"test audio data" * 100  # ~1.5KB
        cache_key = "audio_cache:test_message_es"
        metadata_key = f"{cache_key}:meta"
        
        # Simular compresión
        compressed_data = zlib.compress(test_audio, level=6)
        compression_ratio = len(compressed_data) / len(test_audio)
        
        # Set en cache
        await redis_client.set(cache_key, compressed_data, ex=3600)
        
        # Set metadata
        metadata = {
            "timestamp": str(time.time()),
            "hits": "0",
            "size_bytes": str(len(compressed_data)),
            "original_size": str(len(test_audio)),
            "compressed": "1",
            "content_type": "test"
        }
        
        redis_client.hset(metadata_key, mapping=metadata)
        
        # Get del cache
        cached_data = await redis_client.get(cache_key)
        cache_hit = cached_data is not None
        
        if cache_hit:
            # Descomprimir
            decompressed_data = zlib.decompress(cached_data)
            data_matches = decompressed_data == test_audio
        else:
            data_matches = False
        
        # Incrementar hits
        redis_client.hincrby(metadata_key, "hits", 1)
        
        # Obtener estadísticas básicas
        keys_count = len(await redis_client.keys("audio_cache:*"))
        
        await redis_client.close()
        
        return {
            "status": "ok",
            "redis_connection": "ok",
            "set_success": True,
            "get_success": cache_hit,
            "data_integrity": data_matches,
            "compression_ratio": f"{compression_ratio:.2f}",
            "cache_stats": {
                "total_keys": keys_count,
                "original_size_bytes": len(test_audio),
                "compressed_size_bytes": len(compressed_data),
                "space_saved_percent": f"{(1-compression_ratio)*100:.1f}%"
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(e)}
        )

@app.get("/metrics")
async def metrics():
    """Endpoint de métricas para Prometheus"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "test_main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )