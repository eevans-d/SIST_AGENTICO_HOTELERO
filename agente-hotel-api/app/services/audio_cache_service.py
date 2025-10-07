# app/services/audio_cache_service.py

import hashlib
import json
from typing import Dict, Any, Optional, Tuple
import redis.asyncio as redis
import time

from ..core.logging import logger
from ..core.redis_client import get_redis
from ..core.settings import settings
from .audio_metrics import AudioMetrics


class AudioCacheService:
    """
    Servicio para cachear respuestas de audio generadas por TTS.
    Utiliza Redis para almacenar las respuestas y permite configurar TTL 
    por tipo de contenido.
    """

    # Prefijo para claves de caché en Redis
    CACHE_PREFIX = "audio_cache:"
    
    # TTL en segundos para diferentes tipos de respuestas (24 horas por defecto)
    DEFAULT_TTL = 86400
    
    # TTLs específicos por tipo de contenido
    TTL_CONFIG = {
        "welcome_message": 7 * 86400,  # 7 días para mensajes de bienvenida
        "common_responses": 3 * 86400,  # 3 días para respuestas comunes
        "error_messages": 7 * 86400,   # 7 días para mensajes de error
        # Los demás tipos usarán DEFAULT_TTL
    }
    
    # Tamaño máximo por archivo para almacenar en caché (2MB por defecto)
    MAX_CACHE_SIZE_BYTES = 2 * 1024 * 1024
    
    # TTL por defecto (24 horas)
    DEFAULT_CACHE_TTL = 86400
    
    def __init__(self):
        self._redis = None
        self._enabled = settings.audio_cache_enabled
        self._default_ttl = settings.audio_cache_ttl_seconds or self.DEFAULT_CACHE_TTL
    
    async def _get_redis(self) -> redis.Redis:
        """Obtener conexión a Redis de forma lazy."""
        if not self._redis:
            self._redis = await get_redis()
        return self._redis
    
    def _get_cache_key(self, text: str, voice: str = "default") -> str:
        """
        Genera una clave única para la caché basada en el texto y la voz.
        
        Args:
            text: Texto a sintetizar
            voice: Identificador de voz (default si no se especifica)
            
        Returns:
            Clave única para Redis
        """
        # Generar hash basado en texto + voz para evitar colisiones
        content_hash = hashlib.md5(f"{text}:{voice}".encode()).hexdigest()
        return f"{self.CACHE_PREFIX}{content_hash}"
    
    def _get_ttl(self, content_type: Optional[str] = None) -> int:
        """
        Obtiene el TTL adecuado según el tipo de contenido.
        
        Args:
            content_type: Tipo de contenido para determinar TTL
        
        Returns:
            TTL en segundos
        """
        if content_type and content_type in self.TTL_CONFIG:
            return self.TTL_CONFIG[content_type]
        if self._default_ttl is not None:
            return self._default_ttl
        return self.DEFAULT_CACHE_TTL
    
    async def get(
        self, 
        text: str, 
        voice: str = "default", 
        content_type: Optional[str] = None
    ) -> Optional[Tuple[bytes, Dict[str, Any]]]:
        """
        Obtiene audio cacheado si existe.
        
        Args:
            text: Texto para el que se generó el audio
            voice: Identificador de voz
            
        Returns:
            Datos de audio en bytes o None si no está en caché
        """
        if not self._enabled:
            return None
            
        try:
            start_time = time.time()
            redis_client = await self._get_redis()
            cache_key = self._get_cache_key(text, voice)
            
            # Obtener audio cacheado
            cached_data = await redis_client.get(cache_key)
            
            if cached_data:
                # Actualizar métricas
                access_time = time.time() - start_time
                AudioMetrics.record_operation_duration("audio_cache_hit", access_time)
                AudioMetrics.record_operation("audio_cache", "hit")
                
                # Actualizar metadata de uso
                metadata_key = f"{cache_key}:meta"
                redis_client.hincrby(metadata_key, "hits", 1)  # No await - operación fire and forget
                
                logger.debug(f"Audio cache hit for text: '{text[:30]}...' ({len(cached_data)} bytes)")
                return cached_data
            else:
                # Cache miss
                AudioMetrics.record_operation("audio_cache", "miss")
                return None
                
        except Exception as e:
            logger.warning(f"Error accessing audio cache: {e}")
            AudioMetrics.record_error("audio_cache_access_error")
            return None
    
    async def set(
        self, 
        text: str, 
        audio_data: bytes, 
        voice: str = "default", 
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Almacena audio en caché.
        
        Args:
            text: Texto para el que se generó el audio
            audio_data: Datos binarios del audio
            voice: Identificador de voz
            content_type: Tipo de contenido para determinar TTL
            metadata: Información adicional sobre el audio
            
        Returns:
            True si se guardó correctamente, False en caso contrario
        """
        if not self._enabled:
            return False
            
        # No cachear archivos muy grandes
        if len(audio_data) > self.MAX_CACHE_SIZE_BYTES:
            logger.debug(f"Audio too large for cache: {len(audio_data)} bytes")
            AudioMetrics.record_operation("audio_cache", "too_large")
            return False
        
        try:
            start_time = time.time()
            redis_client = await self._get_redis()
            cache_key = self._get_cache_key(text, voice)
            ttl = self._get_ttl(content_type)
            
            # Guardar audio
            await redis_client.set(cache_key, audio_data, ex=ttl)
            
            # Guardar metadata
            if metadata is None:
                metadata = {}
                
            # Añadir metadata básica
            metadata.update({
                "timestamp": time.time(),
                "size_bytes": len(audio_data),
                "ttl": ttl,
                "content_type": content_type or "general",
                "voice": voice,
                "hits": 0,
                "text_length": len(text)
            })
            
            # Guardar metadata con el mismo TTL
            metadata_key = f"{cache_key}:meta"
            if metadata:
                for key, value in metadata.items():
                    redis_client.hset(metadata_key, key, value)
                await redis_client.expire(metadata_key, ttl)
            
            # Actualizar métricas
            set_time = time.time() - start_time
            AudioMetrics.record_operation_duration("audio_cache_set", set_time)
            AudioMetrics.record_operation("audio_cache", "set")
            AudioMetrics.record_file_size("cached_audio", len(audio_data))
            
            logger.debug(f"Cached audio for text: '{text[:30]}...' ({len(audio_data)} bytes, TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.warning(f"Error setting audio cache: {e}")
            AudioMetrics.record_error("audio_cache_set_error")
            return False
    
    async def invalidate(self, text: str, voice: str = "default") -> bool:
        """
        Invalida una entrada específica de la caché.
        
        Args:
            text: Texto para el que se generó el audio
            voice: Identificador de voz
            
        Returns:
            True si se invalidó correctamente, False en caso contrario
        """
        if not self._enabled:
            return False
            
        try:
            redis_client = await self._get_redis()
            cache_key = self._get_cache_key(text, voice)
            
            # Eliminar entrada y metadata
            await redis_client.delete(cache_key)
            await redis_client.delete(f"{cache_key}:meta")
            
            AudioMetrics.record_operation("audio_cache", "invalidate")
            return True
            
        except Exception as e:
            logger.warning(f"Error invalidating audio cache: {e}")
            AudioMetrics.record_error("audio_cache_invalidate_error")
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de uso de la caché de audio.
        
        Returns:
            Diccionario con estadísticas
        """
        if not self._enabled:
            return {"enabled": False}
            
        try:
            redis_client = await self._get_redis()
            
            # Contar entradas de caché
            cursor = 0
            count = 0
            total_size = 0
            
            # Escanear con patrón para contar entradas y tamaño
            while True:
                cursor, keys = await redis_client.scan(
                    cursor=cursor, 
                    match=f"{self.CACHE_PREFIX}*",
                    count=100
                )
                
                # Filtrar sólo claves de audio (sin metadata)
                audio_keys = [k for k in keys if b":meta" not in k]
                count += len(audio_keys)
                
                # Calcular tamaño de las entradas encontradas
                if audio_keys:
                    # Obtener tamaños en pipeline para optimizar
                    pipe = redis_client.pipeline()
                    for key in audio_keys:
                        pipe.strlen(key)
                    sizes = await pipe.execute()
                    total_size += sum(s for s in sizes if s)
                
                if cursor == 0:
                    break
            
            return {
                "enabled": True,
                "entries_count": count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2) if total_size > 0 else 0,
                "max_entry_size_mb": round(self.MAX_CACHE_SIZE_BYTES / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.warning(f"Error getting audio cache stats: {e}")
            return {
                "enabled": self._enabled,
                "error": str(e)
            }
    
    async def clear_cache(self) -> int:
        """
        Limpia toda la caché de audio.
        
        Returns:
            Número de entradas eliminadas
        """
        if not self._enabled:
            return 0
            
        try:
            redis_client = await self._get_redis()
            
            # Contar entradas eliminadas
            deleted_count = 0
            cursor = 0
            
            # Escanear con patrón para evitar cargar todas las claves a la vez
            while True:
                cursor, keys = await redis_client.scan(
                    cursor=cursor, 
                    match=f"{self.CACHE_PREFIX}*",
                    count=100
                )
                
                if keys:
                    deleted = await redis_client.delete(*keys)
                    deleted_count += deleted
                
                if cursor == 0:
                    break
            
            AudioMetrics.record_operation("audio_cache", "clear")
            logger.info(f"Audio cache cleared: {deleted_count} entries removed")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error clearing audio cache: {e}")
            AudioMetrics.record_error("audio_cache_clear_error")
            return 0

# Instancia singleton
_audio_cache_service = None

async def get_audio_cache_service() -> AudioCacheService:
    """
    Obtiene instancia singleton del servicio de caché de audio.
    """
    global _audio_cache_service
    if _audio_cache_service is None:
        _audio_cache_service = AudioCacheService()
    return _audio_cache_service