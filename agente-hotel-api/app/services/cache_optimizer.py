"""
Cache Optimizer Service para Agente Hotelero IA System
Optimización inteligente de estrategias de cache, preloading y invalidación
"""

import asyncio
import time
import json
import zlib
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import logging
import hashlib

import redis.asyncio as redis
from prometheus_client import Histogram, Counter, Gauge

from app.core.redis_client import get_redis_client
from app.core.settings import settings

# Configurar logging
logger = logging.getLogger(__name__)

# Métricas de Prometheus
cache_optimization_duration = Histogram(
    'cache_optimization_duration_seconds',
    'Tiempo tomado por optimizaciones de cache',
    ['operation']
)

cache_metrics_gauge = Gauge(
    'cache_performance_metrics',
    'Métricas de performance de cache',
    ['metric_type']
)

cache_operations_total = Counter(
    'cache_operations_total',
    'Total de operaciones de cache ejecutadas',
    ['operation', 'status']
)

cache_hit_rate_gauge = Gauge(
    'cache_hit_rate',
    'Tasa de aciertos de cache',
    ['cache_type']
)

class CacheStrategy(Enum):
    """Estrategias de cache disponibles"""
    LRU = "lru"
    LFU = "lfu"
    TTL_BASED = "ttl_based"
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"
    READ_THROUGH = "read_through"

class CacheLayer(Enum):
    """Capas de cache"""
    L1_APPLICATION = "l1_application"  # Cache en memoria de la aplicación
    L2_REDIS = "l2_redis"             # Cache Redis
    L3_DATABASE = "l3_database"       # Query cache de DB

@dataclass
class CachePattern:
    """Patrón de uso de cache"""
    key_pattern: str
    access_frequency: float
    hit_rate: float
    avg_size: int
    ttl: int
    last_access: datetime
    hotness_score: float

@dataclass
class CacheStats:
    """Estadísticas de cache"""
    total_keys: int
    memory_usage: int
    hit_rate: float
    miss_rate: float
    eviction_rate: float
    avg_ttl: float
    fragmentation_ratio: float
    ops_per_second: float

class CacheOptimizer:
    """
    Optimizador inteligente de cache
    Analiza patrones de uso y optimiza estrategias automáticamente
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.cache_patterns: Dict[str, CachePattern] = {}
        self.optimization_history: List[Dict] = []
        self.hot_keys: Set[str] = set()
        self.cold_keys: Set[str] = set()
        
        # Configuración de optimización
        self.config = {
            'hot_key_threshold': 0.8,      # 80% hit rate para considerar hot
            'cold_key_threshold': 0.2,     # 20% hit rate para considerar cold
            'preload_top_keys': 50,        # Precargar top 50 keys
            'max_memory_usage': 0.85,      # 85% uso máximo de memoria
            'compression_threshold': 1024,  # Comprimir datos > 1KB
            'adaptive_ttl_enabled': True,   # TTL adaptativo
            'auto_preload_enabled': True    # Precarga automática
        }
    
    async def start(self):
        """Inicializar el optimizador de cache"""
        try:
            self.redis_client = await get_redis_client()
            
            # Configurar Redis para optimización
            await self._configure_redis_optimization()
            
            logger.info("Cache Optimizer iniciado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar Cache Optimizer: {e}")
            raise
    
    async def stop(self):
        """Detener el optimizador"""
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Cache Optimizer detenido")
    
    async def _configure_redis_optimization(self):
        """Configurar Redis para optimización"""
        try:
            # Configurar política de eviction
            await self.redis_client.config_set('maxmemory-policy', 'allkeys-lru')
            
            # Configurar sampling para LRU
            await self.redis_client.config_set('maxmemory-samples', '10')
            
            # Habilitar compresión de listas
            await self.redis_client.config_set('list-compress-depth', '2')
            
            logger.info("Configuración de Redis optimizada")
        except Exception as e:
            logger.warning(f"Error configurando Redis: {e}")
    
    async def analyze_cache_patterns(self) -> Dict[str, CachePattern]:
        """Analizar patrones de uso de cache"""
        with cache_optimization_duration.labels('pattern_analysis').time():
            try:
                # Obtener todas las keys
                keys = await self.redis_client.keys('*')
                
                patterns = {}
                
                for key_bytes in keys:
                    key = key_bytes.decode('utf-8') if isinstance(key_bytes, bytes) else key_bytes
                    
                    try:
                        # Analizar patrón de la key
                        pattern = await self._analyze_key_pattern(key)
                        if pattern:
                            pattern_key = self._extract_pattern_key(key)
                            patterns[pattern_key] = pattern
                    except Exception as e:
                        logger.debug(f"Error analizando key {key}: {e}")
                
                self.cache_patterns = patterns
                
                # Actualizar métricas
                cache_metrics_gauge.labels('total_patterns').set(len(patterns))
                
                logger.info(f"Analizados {len(patterns)} patrones de cache")
                return patterns
                
            except Exception as e:
                logger.error(f"Error analizando patrones de cache: {e}")
                return {}
    
    async def _analyze_key_pattern(self, key: str) -> Optional[CachePattern]:
        """Analizar un patrón específico de key"""
        try:
            # Obtener información de la key
            key_type = await self.redis_client.type(key)
            ttl = await self.redis_client.ttl(key)
            memory_usage = await self.redis_client.memory_usage(key)
            
            if memory_usage is None:
                return None
            
            # Simular estadísticas de acceso (en producción vendría de métricas)
            access_frequency = await self._estimate_access_frequency(key)
            hit_rate = await self._estimate_hit_rate(key)
            
            # Calcular hotness score
            hotness_score = self._calculate_hotness_score(access_frequency, hit_rate, memory_usage)
            
            return CachePattern(
                key_pattern=key,
                access_frequency=access_frequency,
                hit_rate=hit_rate,
                avg_size=memory_usage,
                ttl=ttl if ttl > 0 else 3600,  # Default 1 hora
                last_access=datetime.now(),
                hotness_score=hotness_score
            )
            
        except Exception as e:
            logger.debug(f"Error analizando key pattern {key}: {e}")
            return None
    
    def _extract_pattern_key(self, key: str) -> str:
        """Extraer patrón de key (ej: user:123 -> user:*"""
        parts = key.split(':')
        if len(parts) >= 2:
            # Reemplazar IDs numéricos con *
            pattern_parts = []
            for part in parts:
                if part.isdigit() or self._looks_like_id(part):
                    pattern_parts.append('*')
                else:
                    pattern_parts.append(part)
            return ':'.join(pattern_parts)
        return key
    
    def _looks_like_id(self, value: str) -> bool:
        """Determinar si un valor parece un ID"""
        # UUID, hash, etc.
        return (len(value) > 10 and 
                (value.replace('-', '').replace('_', '').isalnum()) and
                any(c.isdigit() for c in value))
    
    async def _estimate_access_frequency(self, key: str) -> float:
        """Estimar frecuencia de acceso (simulado)"""
        # En producción esto vendría de métricas reales
        try:
            # Keys de session y availability son más frecuentes
            if 'session' in key or 'availability' in key:
                return 0.8
            elif 'user' in key or 'reservation' in key:
                return 0.6
            elif 'config' in key:
                return 0.9
            else:
                return 0.3
        except Exception:
            return 0.5
    
    async def _estimate_hit_rate(self, key: str) -> float:
        """Estimar hit rate (simulado)"""
        # En producción esto vendría de métricas de Redis
        try:
            if 'config' in key:
                return 0.95
            elif 'availability' in key:
                return 0.75
            elif 'session' in key:
                return 0.85
            else:
                return 0.6
        except Exception:
            return 0.7
    
    def _calculate_hotness_score(self, frequency: float, hit_rate: float, size: int) -> float:
        """Calcular score de hotness de una key"""
        # Score basado en frecuencia, hit rate y tamaño (menor tamaño = mejor)
        size_factor = max(0.1, 1.0 - (size / 10000))  # Penalizar keys grandes
        return (frequency * 0.4 + hit_rate * 0.4 + size_factor * 0.2)
    
    async def identify_hot_cold_keys(self) -> Tuple[Set[str], Set[str]]:
        """Identificar keys hot y cold"""
        hot_keys = set()
        cold_keys = set()
        
        for pattern_key, pattern in self.cache_patterns.items():
            if pattern.hotness_score >= self.config['hot_key_threshold']:
                hot_keys.add(pattern_key)
            elif pattern.hotness_score <= self.config['cold_key_threshold']:
                cold_keys.add(pattern_key)
        
        self.hot_keys = hot_keys
        self.cold_keys = cold_keys
        
        # Actualizar métricas
        cache_metrics_gauge.labels('hot_keys_count').set(len(hot_keys))
        cache_metrics_gauge.labels('cold_keys_count').set(len(cold_keys))
        
        logger.info(f"Identificadas {len(hot_keys)} keys hot, {len(cold_keys)} keys cold")
        return hot_keys, cold_keys
    
    async def optimize_ttl_strategy(self) -> Dict[str, int]:
        """Optimizar estrategia de TTL basada en patrones"""
        with cache_optimization_duration.labels('ttl_optimization').time():
            try:
                optimized_ttls = {}
                
                for pattern_key, pattern in self.cache_patterns.items():
                    optimal_ttl = await self._calculate_optimal_ttl(pattern)
                    optimized_ttls[pattern_key] = optimal_ttl
                    
                    # Aplicar TTL optimizado a keys existentes del patrón
                    await self._apply_ttl_to_pattern(pattern_key, optimal_ttl)
                
                cache_operations_total.labels('ttl_optimization', 'success').inc()
                
                logger.info(f"TTL optimizado para {len(optimized_ttls)} patrones")
                return optimized_ttls
                
            except Exception as e:
                logger.error(f"Error optimizando TTL: {e}")
                cache_operations_total.labels('ttl_optimization', 'failed').inc()
                return {}
    
    async def _calculate_optimal_ttl(self, pattern: CachePattern) -> int:
        """Calcular TTL óptimo para un patrón"""
        base_ttl = pattern.ttl
        
        # Ajustar TTL basado en hotness score
        if pattern.hotness_score >= 0.8:
            # Keys muy hot: TTL más largo
            optimal_ttl = int(base_ttl * 1.5)
        elif pattern.hotness_score >= 0.6:
            # Keys moderadamente hot: TTL normal
            optimal_ttl = base_ttl
        elif pattern.hotness_score >= 0.4:
            # Keys templadas: TTL reducido
            optimal_ttl = int(base_ttl * 0.7)
        else:
            # Keys cold: TTL muy reducido
            optimal_ttl = int(base_ttl * 0.5)
        
        # Límites mínimos y máximos
        optimal_ttl = max(300, min(optimal_ttl, 86400))  # Entre 5 min y 24 horas
        
        return optimal_ttl
    
    async def _apply_ttl_to_pattern(self, pattern_key: str, ttl: int):
        """Aplicar TTL a todas las keys de un patrón"""
        try:
            # Convertir patrón a Redis pattern
            redis_pattern = pattern_key.replace('*', '*')
            
            # Obtener keys que coinciden con el patrón
            keys = await self.redis_client.keys(redis_pattern)
            
            # Aplicar TTL en lotes
            pipe = self.redis_client.pipeline()
            batch_size = 100
            
            for i, key in enumerate(keys):
                pipe.expire(key, ttl)
                
                if (i + 1) % batch_size == 0:
                    await pipe.execute()
                    pipe = self.redis_client.pipeline()
            
            # Ejecutar lote restante
            if len(keys) % batch_size != 0:
                await pipe.execute()
            
        except Exception as e:
            logger.warning(f"Error aplicando TTL a patrón {pattern_key}: {e}")
    
    async def implement_compression(self) -> Dict[str, Any]:
        """Implementar compresión para keys grandes"""
        with cache_optimization_duration.labels('compression').time():
            try:
                compressed_keys = []
                total_savings = 0
                
                # Analizar keys grandes para compresión
                keys = await self.redis_client.keys('*')
                
                for key_bytes in keys:
                    key = key_bytes.decode('utf-8') if isinstance(key_bytes, bytes) else key_bytes
                    
                    try:
                        size = await self.redis_client.memory_usage(key)
                        if size and size > self.config['compression_threshold']:
                            # Intentar comprimir
                            savings = await self._compress_key(key)
                            if savings > 0:
                                compressed_keys.append({
                                    'key': key,
                                    'original_size': size,
                                    'savings': savings
                                })
                                total_savings += savings
                    except Exception as e:
                        logger.debug(f"Error comprimiendo key {key}: {e}")
                
                cache_operations_total.labels('compression', 'success').inc()
                
                result = {
                    'compressed_keys_count': len(compressed_keys),
                    'total_savings_bytes': total_savings,
                    'compression_ratio': total_savings / sum(k['original_size'] for k in compressed_keys) if compressed_keys else 0,
                    'compressed_keys': compressed_keys[:10]  # Top 10
                }
                
                logger.info(f"Compresión aplicada: {len(compressed_keys)} keys, {total_savings} bytes ahorrados")
                return result
                
            except Exception as e:
                logger.error(f"Error implementando compresión: {e}")
                cache_operations_total.labels('compression', 'failed').inc()
                return {'error': str(e)}
    
    async def _compress_key(self, key: str) -> int:
        """Comprimir una key específica"""
        try:
            # Obtener valor actual
            value = await self.redis_client.get(key)
            if not value:
                return 0
            
            original_size = len(value)
            
            # Comprimir con zlib
            if isinstance(value, str):
                value = value.encode('utf-8')
            
            compressed_value = zlib.compress(value)
            compressed_size = len(compressed_value)
            
            # Solo actualizar si hay ahorros significativos (>20%)
            if compressed_size < original_size * 0.8:
                # Almacenar valor comprimido con metadatos
                compressed_data = {
                    'compressed': True,
                    'algorithm': 'zlib',
                    'data': compressed_value.hex()
                }
                
                await self.redis_client.set(f"{key}:compressed", json.dumps(compressed_data))
                
                # Mantener TTL original
                ttl = await self.redis_client.ttl(key)
                if ttl > 0:
                    await self.redis_client.expire(f"{key}:compressed", ttl)
                
                return original_size - compressed_size
            
            return 0
            
        except Exception as e:
            logger.debug(f"Error comprimiendo key {key}: {e}")
            return 0
    
    async def preload_hot_data(self) -> Dict[str, Any]:
        """Pre-cargar datos hot basado en patrones"""
        with cache_optimization_duration.labels('preload').time():
            try:
                if not self.config['auto_preload_enabled']:
                    return {'status': 'disabled'}
                
                preloaded_items = []
                
                # Pre-cargar datos de configuración críticos
                config_items = await self._preload_configuration_data()
                preloaded_items.extend(config_items)
                
                # Pre-cargar datos de habitaciones frecuentes
                room_items = await self._preload_room_data()
                preloaded_items.extend(room_items)
                
                # Pre-cargar templates de respuesta
                template_items = await self._preload_template_data()
                preloaded_items.extend(template_items)
                
                # Pre-cargar datos de usuarios activos
                user_items = await self._preload_active_user_data()
                preloaded_items.extend(user_items)
                
                cache_operations_total.labels('preload', 'success').inc()
                
                result = {
                    'status': 'completed',
                    'preloaded_items_count': len(preloaded_items),
                    'categories': {
                        'configuration': len(config_items),
                        'rooms': len(room_items),
                        'templates': len(template_items),
                        'users': len(user_items)
                    },
                    'items': preloaded_items[:20]  # Top 20
                }
                
                logger.info(f"Pre-carga completada: {len(preloaded_items)} items")
                return result
                
            except Exception as e:
                logger.error(f"Error en pre-carga: {e}")
                cache_operations_total.labels('preload', 'failed').inc()
                return {'status': 'failed', 'error': str(e)}
    
    async def _preload_configuration_data(self) -> List[Dict]:
        """Pre-cargar datos de configuración"""
        items = []
        
        try:
            # Configuración del hotel
            hotel_config = {
                'name': settings.hotel_name if hasattr(settings, 'hotel_name') else 'Hotel Example',
                'rooms_count': 100,
                'amenities': ['wifi', 'pool', 'spa', 'gym', 'restaurant'],
                'policies': {
                    'check_in': '15:00',
                    'check_out': '11:00',
                    'cancellation': '24h'
                }
            }
            
            await self.redis_client.setex('config:hotel', 7200, json.dumps(hotel_config))
            items.append({'key': 'config:hotel', 'type': 'configuration'})
            
            # Configuración de tarifas
            pricing_config = {
                'base_rates': {
                    'standard': 120,
                    'deluxe': 180,
                    'suite': 280
                },
                'seasonal_multipliers': {
                    'high': 1.3,
                    'medium': 1.0,
                    'low': 0.8
                }
            }
            
            await self.redis_client.setex('config:pricing', 7200, json.dumps(pricing_config))
            items.append({'key': 'config:pricing', 'type': 'configuration'})
            
        except Exception as e:
            logger.warning(f"Error pre-cargando configuración: {e}")
        
        return items
    
    async def _preload_room_data(self) -> List[Dict]:
        """Pre-cargar datos de habitaciones frecuentes"""
        items = []
        
        try:
            # Datos de tipos de habitación populares
            room_types = {
                'standard': {
                    'name': 'Habitación Estándar',
                    'capacity': 2,
                    'amenities': ['wifi', 'tv', 'ac'],
                    'size': '25m²'
                },
                'deluxe': {
                    'name': 'Habitación Deluxe',
                    'capacity': 2,
                    'amenities': ['wifi', 'tv', 'ac', 'minibar'],
                    'size': '35m²'
                },
                'suite': {
                    'name': 'Suite',
                    'capacity': 4,
                    'amenities': ['wifi', 'tv', 'ac', 'minibar', 'balcony'],
                    'size': '50m²'
                }
            }
            
            for room_type, data in room_types.items():
                key = f'room_type:{room_type}'
                await self.redis_client.setex(key, 3600, json.dumps(data))
                items.append({'key': key, 'type': 'room_data'})
                
        except Exception as e:
            logger.warning(f"Error pre-cargando datos de habitaciones: {e}")
        
        return items
    
    async def _preload_template_data(self) -> List[Dict]:
        """Pre-cargar templates de respuesta"""
        items = []
        
        try:
            templates = {
                'greeting': 'Hola! Bienvenido a nuestro hotel. ¿En qué puedo ayudarte?',
                'availability_check': 'Permíteme verificar la disponibilidad para esas fechas...',
                'reservation_confirm': 'Perfecto! Tu reserva ha sido confirmada. Recibirás un email con los detalles.',
                'payment_request': 'Para confirmar tu reserva, necesitamos procesar el pago. ¿Prefieres pagar ahora o en el hotel?',
                'checkout_info': 'El checkout es a las 11:00 AM. ¿Necesitas checkout tardío?'
            }
            
            for template_key, template_text in templates.items():
                key = f'template:{template_key}'
                await self.redis_client.setex(key, 1800, template_text)  # 30 min
                items.append({'key': key, 'type': 'template'})
                
        except Exception as e:
            logger.warning(f"Error pre-cargando templates: {e}")
        
        return items
    
    async def _preload_active_user_data(self) -> List[Dict]:
        """Pre-cargar datos de usuarios activos"""
        items = []
        
        try:
            # Simular pre-carga de usuarios activos (en producción vendría de DB)
            active_sessions = await self.redis_client.keys('session:*')
            
            for session_key in active_sessions[:10]:  # Top 10 sesiones activas
                # Pre-cargar configuración de usuario
                user_config = {
                    'language': 'es',
                    'preferences': {
                        'room_type': 'standard',
                        'notifications': True
                    }
                }
                
                user_key = session_key.replace(b'session:', b'user_config:').decode('utf-8')
                await self.redis_client.setex(user_key, 1800, json.dumps(user_config))
                items.append({'key': user_key, 'type': 'user_data'})
                
        except Exception as e:
            logger.warning(f"Error pre-cargando datos de usuarios: {e}")
        
        return items
    
    async def cleanup_expired_keys(self) -> Dict[str, int]:
        """Limpiar keys expiradas y optimizar memoria"""
        with cache_optimization_duration.labels('cleanup').time():
            try:
                # Obtener información de memoria antes
                memory_info_before = await self.redis_client.info('memory')
                used_memory_before = memory_info_before.get('used_memory', 0)
                
                # Limpiar keys expiradas manualmente
                expired_keys = 0
                keys = await self.redis_client.keys('*')
                
                pipe = self.redis_client.pipeline()
                batch_size = 100
                
                for i, key in enumerate(keys):
                    ttl = await self.redis_client.ttl(key)
                    if ttl == -2:  # Key expirada
                        pipe.delete(key)
                        expired_keys += 1
                    
                    if (i + 1) % batch_size == 0:
                        await pipe.execute()
                        pipe = self.redis_client.pipeline()
                
                # Ejecutar lote restante
                if len(keys) % batch_size != 0:
                    await pipe.execute()
                
                # Obtener información de memoria después
                memory_info_after = await self.redis_client.info('memory')
                used_memory_after = memory_info_after.get('used_memory', 0)
                
                memory_freed = used_memory_before - used_memory_after
                
                cache_operations_total.labels('cleanup', 'success').inc()
                
                result = {
                    'expired_keys_removed': expired_keys,
                    'memory_freed_bytes': memory_freed,
                    'memory_before_mb': used_memory_before // (1024 * 1024),
                    'memory_after_mb': used_memory_after // (1024 * 1024)
                }
                
                logger.info(f"Limpieza completada: {expired_keys} keys eliminadas, {memory_freed} bytes liberados")
                return result
                
            except Exception as e:
                logger.error(f"Error en limpieza de cache: {e}")
                cache_operations_total.labels('cleanup', 'failed').inc()
                return {'error': str(e)}
    
    async def get_cache_performance_report(self) -> Dict:
        """Obtener reporte completo de performance de cache"""
        try:
            # Estadísticas generales de Redis
            info = await self.redis_client.info()
            
            # Calcular hit rate
            keyspace_hits = info.get('keyspace_hits', 0)
            keyspace_misses = info.get('keyspace_misses', 0)
            total_commands = keyspace_hits + keyspace_misses
            hit_rate = keyspace_hits / total_commands if total_commands > 0 else 0
            
            # Actualizar métricas de Prometheus
            cache_hit_rate_gauge.labels('overall').set(hit_rate)
            cache_metrics_gauge.labels('memory_usage_mb').set(info.get('used_memory', 0) // (1024 * 1024))
            cache_metrics_gauge.labels('connected_clients').set(info.get('connected_clients', 0))
            
            return {
                'general_stats': {
                    'total_keys': info.get('db0', {}).get('keys', 0),
                    'memory_usage_mb': info.get('used_memory', 0) // (1024 * 1024),
                    'hit_rate': round(hit_rate, 4),
                    'miss_rate': round(1 - hit_rate, 4),
                    'connected_clients': info.get('connected_clients', 0),
                    'ops_per_second': info.get('instantaneous_ops_per_sec', 0),
                    'fragmentation_ratio': info.get('mem_fragmentation_ratio', 0)
                },
                'optimization_stats': {
                    'hot_keys_count': len(self.hot_keys),
                    'cold_keys_count': len(self.cold_keys),
                    'patterns_identified': len(self.cache_patterns),
                    'optimization_enabled': self.config['auto_preload_enabled']
                },
                'top_patterns': [
                    {
                        'pattern': pattern.key_pattern,
                        'hotness_score': round(pattern.hotness_score, 3),
                        'hit_rate': round(pattern.hit_rate, 3),
                        'access_frequency': round(pattern.access_frequency, 3),
                        'avg_size_kb': pattern.avg_size // 1024
                    }
                    for pattern in sorted(self.cache_patterns.values(), 
                                        key=lambda x: x.hotness_score, reverse=True)[:10]
                ],
                'recent_optimizations': self.optimization_history[-10:],
                'configuration': self.config,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generando reporte de cache: {e}")
            return {'error': str(e)}
    
    async def auto_optimize_cache(self) -> Dict:
        """Ejecutar optimización automática completa de cache"""
        try:
            logger.info("Iniciando auto-optimización de cache")
            
            results = {}
            
            # 1. Analizar patrones
            patterns = await self.analyze_cache_patterns()
            results['patterns_analyzed'] = len(patterns)
            
            # 2. Identificar keys hot/cold
            hot_keys, cold_keys = await self.identify_hot_cold_keys()
            results['hot_keys'] = len(hot_keys)
            results['cold_keys'] = len(cold_keys)
            
            # 3. Optimizar TTL
            ttl_optimizations = await self.optimize_ttl_strategy()
            results['ttl_optimizations'] = len(ttl_optimizations)
            
            # 4. Implementar compresión
            compression_result = await self.implement_compression()
            results['compression'] = compression_result
            
            # 5. Pre-cargar datos hot
            preload_result = await self.preload_hot_data()
            results['preload'] = preload_result
            
            # 6. Limpiar keys expiradas
            cleanup_result = await self.cleanup_expired_keys()
            results['cleanup'] = cleanup_result
            
            # Registrar en historial
            optimization_record = {
                'timestamp': datetime.now().isoformat(),
                'type': 'auto_optimization',
                'results': results
            }
            self.optimization_history.append(optimization_record)
            
            logger.info("Auto-optimización de cache completada")
            return {
                'status': 'completed',
                'optimizations': results,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error en auto-optimización de cache: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

# Instancia global del optimizador
cache_optimizer = CacheOptimizer()

async def get_cache_optimizer() -> CacheOptimizer:
    """Obtener instancia del optimizador de cache"""
    return cache_optimizer