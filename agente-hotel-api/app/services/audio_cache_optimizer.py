"""
Sistema de caché inteligente para optimización de modelos de audio STT/TTS.
Implementa estrategias de caching avanzadas para mejorar el rendimiento.
"""

import asyncio
import hashlib
import pickle
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

class CacheStrategy(Enum):
    """Estrategias de caché para diferentes tipos de contenido de audio."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    ADAPTIVE = "adaptive"  # Adaptativo basado en patrones de uso

class AudioCacheType(Enum):
    """Tipos de caché de audio."""
    STT_MODEL = "stt_model"
    TTS_MODEL = "tts_model"
    PROCESSED_AUDIO = "processed_audio"
    TRANSCRIPTION = "transcription"
    SYNTHESIS = "synthesis"

@dataclass
class CacheEntry:
    """Entrada de caché con metadatos de optimización."""
    key: str
    data: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size_bytes: int = 0
    cache_type: AudioCacheType = AudioCacheType.PROCESSED_AUDIO
    metadata: Dict[str, Any] = field(default_factory=dict)

class AudioCacheOptimizer:
    """
    Optimizador de caché inteligente para componentes de audio.
    Implementa múltiples estrategias de caching y optimización automática.
    """
    
    # Métricas globales (singleton)
    _metrics_initialized = False
    _cache_hits = None
    _cache_misses = None
    _cache_latency = None
    _cache_memory_usage = None
    
    def __init__(
        self,
        redis_client: redis.Redis,
        max_memory_mb: int = 512,
        default_ttl: int = 3600,
        cleanup_interval: int = 300
    ):
        self.redis_client = redis_client
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        
        # Cache local en memoria para acceso ultra-rápido
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.cache_stats: Dict[str, int] = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "memory_usage": 0
        }
        
        # Inicializar métricas de Prometheus (singleton)
        self._initialize_metrics()
        
        # Task de limpieza
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    def _initialize_metrics(self):
        """Inicializa las métricas de Prometheus una sola vez."""
        if not AudioCacheOptimizer._metrics_initialized:
            try:
                AudioCacheOptimizer._cache_hits = Counter(
                    "audio_cache_hits_total",
                    "Cache hits por tipo",
                    ["cache_type", "strategy"]
                )
                AudioCacheOptimizer._cache_misses = Counter(
                    "audio_cache_misses_total",
                    "Cache misses por tipo",
                    ["cache_type", "strategy"]
                )
                AudioCacheOptimizer._cache_latency = Histogram(
                    "audio_cache_operation_seconds",
                    "Latencia de operaciones de caché",
                    ["operation", "cache_type"]
                )
                AudioCacheOptimizer._cache_memory_usage = Gauge(
                    "audio_cache_memory_bytes",
                    "Uso de memoria del caché de audio"
                )
                AudioCacheOptimizer._metrics_initialized = True
            except (ValueError, Exception) as e:
                # Las métricas ya existen o hay un error, usar dummy metrics
                logger.warning(f"No se pueden registrar métricas: {e}")
                # Crear métricas dummy para pruebas
                AudioCacheOptimizer._cache_hits = self._create_dummy_counter()
                AudioCacheOptimizer._cache_misses = self._create_dummy_counter()
                AudioCacheOptimizer._cache_latency = self._create_dummy_histogram()
                AudioCacheOptimizer._cache_memory_usage = self._create_dummy_gauge()
                AudioCacheOptimizer._metrics_initialized = True
    
    def _create_dummy_counter(self):
        """Crea un counter dummy para pruebas."""
        class DummyCounter:
            def labels(self, **kwargs):
                return self
            def inc(self, amount=1):
                pass
        return DummyCounter()
    
    def _create_dummy_histogram(self):
        """Crea un histogram dummy para pruebas."""
        class DummyHistogram:
            def labels(self, **kwargs):
                return self
            def observe(self, amount):
                pass
        return DummyHistogram()
    
    def _create_dummy_gauge(self):
        """Crea un gauge dummy para pruebas."""
        class DummyGauge:
            def set(self, value):
                pass
        return DummyGauge()
    
    @property
    def cache_hits(self):
        """Acceso a las métricas de cache hits."""
        return AudioCacheOptimizer._cache_hits
    
    @property
    def cache_misses(self):
        """Acceso a las métricas de cache misses."""
        return AudioCacheOptimizer._cache_misses
    
    @property
    def cache_latency(self):
        """Acceso a las métricas de latencia."""
        return AudioCacheOptimizer._cache_latency
    
    @property
    def cache_memory_usage(self):
        """Acceso a las métricas de uso de memoria."""
        return AudioCacheOptimizer._cache_memory_usage
    
    async def start(self):
        """Inicia el optimizador de caché."""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("AudioCacheOptimizer iniciado")
    
    async def stop(self):
        """Detiene el optimizador de caché."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("AudioCacheOptimizer detenido")
    
    async def get(
        self,
        key: str,
        cache_type: AudioCacheType,
        strategy: CacheStrategy = CacheStrategy.ADAPTIVE
    ) -> Optional[Any]:
        """
        Obtiene un valor del caché con estrategia optimizada.
        """
        start_time = time.time()
        
        try:
            # 1. Verificar caché en memoria primero
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                entry.last_accessed = datetime.now()
                entry.access_count += 1
                
                self.cache_hits.labels(
                    cache_type=cache_type.value,
                    strategy=strategy.value
                ).inc()
                self.cache_stats["hits"] += 1
                
                logger.debug(f"Cache hit (memoria): {key}")
                return entry.data
            
            # 2. Verificar Redis como caché secundario
            redis_key = f"audio_cache:{cache_type.value}:{key}"
            cached_data = await self.redis_client.get(redis_key)
            
            if cached_data:
                data = pickle.loads(cached_data)
                
                # Promover a caché en memoria si hay espacio
                await self._add_to_memory_cache(key, data, cache_type)
                
                self.cache_hits.labels(
                    cache_type=cache_type.value,
                    strategy=strategy.value
                ).inc()
                self.cache_stats["hits"] += 1
                
                logger.debug(f"Cache hit (Redis): {key}")
                return data
            
            # 3. Cache miss
            self.cache_misses.labels(
                cache_type=cache_type.value,
                strategy=strategy.value
            ).inc()
            self.cache_stats["misses"] += 1
            
            logger.debug(f"Cache miss: {key}")
            return None
            
        finally:
            self.cache_latency.labels(
                operation="get",
                cache_type=cache_type.value
            ).observe(time.time() - start_time)
    
    async def set(
        self,
        key: str,
        data: Any,
        cache_type: AudioCacheType,
        ttl: Optional[int] = None,
        strategy: CacheStrategy = CacheStrategy.ADAPTIVE
    ):
        """
        Almacena un valor en el caché con estrategia optimizada.
        """
        start_time = time.time()
        
        try:
            ttl = ttl or self.default_ttl
            
            # 1. Almacenar en Redis
            redis_key = f"audio_cache:{cache_type.value}:{key}"
            serialized_data = pickle.dumps(data)
            
            await self.redis_client.setex(
                redis_key,
                ttl,
                serialized_data
            )
            
            # 2. Almacenar en caché en memoria si es estratégico
            if self._should_cache_in_memory(cache_type, strategy):
                await self._add_to_memory_cache(key, data, cache_type)
            
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            
        finally:
            self.cache_latency.labels(
                operation="set",
                cache_type=cache_type.value
            ).observe(time.time() - start_time)
    
    async def invalidate(
        self,
        pattern: str,
        cache_type: Optional[AudioCacheType] = None
    ):
        """
        Invalida entradas de caché que coincidan con el patrón.
        """
        # Invalidar caché en memoria
        keys_to_remove = []
        for key in self.memory_cache:
            if pattern in key:
                if not cache_type or self.memory_cache[key].cache_type == cache_type:
                    keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.memory_cache[key]
        
        # Invalidar en Redis
        if cache_type:
            redis_pattern = f"audio_cache:{cache_type.value}:*{pattern}*"
        else:
            redis_pattern = f"audio_cache:*{pattern}*"
        
        keys = await self.redis_client.keys(redis_pattern)
        if keys:
            await self.redis_client.delete(*keys)
        
        logger.info(f"Invalidated {len(keys_to_remove) + len(keys)} cache entries for pattern: {pattern}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas detalladas del caché.
        """
        # Actualizar uso de memoria
        memory_usage = sum(
            entry.size_bytes for entry in self.memory_cache.values()
        )
        self.cache_stats["memory_usage"] = memory_usage
        self.cache_memory_usage.set(memory_usage)
        
        # Estadísticas por tipo de caché
        type_stats = {}
        for entry in self.memory_cache.values():
            cache_type = entry.cache_type.value
            if cache_type not in type_stats:
                type_stats[cache_type] = {
                    "count": 0,
                    "total_size": 0,
                    "avg_access_count": 0
                }
            
            type_stats[cache_type]["count"] += 1
            type_stats[cache_type]["total_size"] += entry.size_bytes
            type_stats[cache_type]["avg_access_count"] += entry.access_count
        
        # Calcular promedios
        for stats in type_stats.values():
            if stats["count"] > 0:
                stats["avg_access_count"] /= stats["count"]
        
        return {
            "global_stats": self.cache_stats.copy(),
            "type_stats": type_stats,
            "memory_cache_size": len(self.memory_cache),
            "memory_utilization": memory_usage / self.max_memory_bytes,
            "cache_hit_ratio": (
                self.cache_stats["hits"] / 
                (self.cache_stats["hits"] + self.cache_stats["misses"])
                if (self.cache_stats["hits"] + self.cache_stats["misses"]) > 0
                else 0.0
            )
        }
    
    async def _add_to_memory_cache(
        self,
        key: str,
        data: Any,
        cache_type: AudioCacheType
    ):
        """
        Añade una entrada al caché en memoria con gestión de espacio.
        """
        # Calcular tamaño aproximado
        size_bytes = len(pickle.dumps(data))
        
        # Verificar si hay espacio suficiente
        current_usage = sum(
            entry.size_bytes for entry in self.memory_cache.values()
        )
        
        if current_usage + size_bytes > self.max_memory_bytes:
            await self._evict_entries_to_make_space(size_bytes)
        
        # Crear entrada
        entry = CacheEntry(
            key=key,
            data=data,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=1,
            size_bytes=size_bytes,
            cache_type=cache_type
        )
        
        self.memory_cache[key] = entry
    
    async def _evict_entries_to_make_space(self, required_bytes: int):
        """
        Expulsa entradas del caché para hacer espacio usando estrategia LRU.
        """
        if not self.memory_cache:
            return
        
        # Ordenar por último acceso (LRU)
        sorted_entries = sorted(
            self.memory_cache.items(),
            key=lambda x: x[1].last_accessed
        )
        
        freed_bytes = 0
        keys_to_remove = []
        
        for key, entry in sorted_entries:
            if freed_bytes >= required_bytes:
                break
            
            freed_bytes += entry.size_bytes
            keys_to_remove.append(key)
            self.cache_stats["evictions"] += 1
        
        for key in keys_to_remove:
            del self.memory_cache[key]
        
        logger.debug(f"Evicted {len(keys_to_remove)} entries, freed {freed_bytes} bytes")
    
    def _should_cache_in_memory(
        self,
        cache_type: AudioCacheType,
        strategy: CacheStrategy
    ) -> bool:
        """
        Determina si un elemento debe almacenarse en caché en memoria.
        """
        # Modelos STT/TTS son prioritarios para caché en memoria
        if cache_type in [AudioCacheType.STT_MODEL, AudioCacheType.TTS_MODEL]:
            return True
        
        # Para otros tipos, depende de la estrategia
        if strategy == CacheStrategy.ADAPTIVE:
            # Lógica adaptativa basada en uso actual
            current_usage = sum(
                entry.size_bytes for entry in self.memory_cache.values()
            )
            return current_usage < (self.max_memory_bytes * 0.8)
        
        return strategy in [CacheStrategy.LRU, CacheStrategy.LFU]
    
    async def _cleanup_loop(self):
        """
        Bucle de limpieza periódica del caché.
        """
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._perform_cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error en cleanup de caché: {e}")
    
    async def _perform_cleanup(self):
        """
        Realiza limpieza del caché eliminando entradas expiradas.
        """
        now = datetime.now()
        expired_keys = []
        
        for key, entry in self.memory_cache.items():
            # Remover entradas muy antiguas (más de 1 hora sin acceso)
            if (now - entry.last_accessed).total_seconds() > 3600:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.memory_cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")