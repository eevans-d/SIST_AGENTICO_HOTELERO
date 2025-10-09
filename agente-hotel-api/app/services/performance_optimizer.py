"""
Performance Optimizer Service para Agente Hotelero IA System
Optimiza automáticamente el rendimiento del sistema basado en métricas en tiempo real
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import json
from datetime import datetime, timedelta

import psutil
import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from prometheus_client import Histogram, Counter, Gauge

from app.core.database import AsyncSessionFactory
from app.core.redis_client import get_redis_client
from app.core.settings import settings

# Configurar logging
logger = logging.getLogger(__name__)

# Métricas de Prometheus
performance_optimization_duration = Histogram(
    'performance_optimization_duration_seconds',
    'Tiempo tomado por optimizaciones de performance',
    ['optimization_type']
)

performance_metrics_gauge = Gauge(
    'system_performance_metrics',
    'Métricas de performance del sistema',
    ['metric_type', 'component']
)

optimization_actions_total = Counter(
    'performance_optimization_actions_total',
    'Total de acciones de optimización ejecutadas',
    ['action_type', 'status']
)

class OptimizationType(Enum):
    """Tipos de optimización disponibles"""
    DATABASE = "database"
    CACHE = "cache"
    MEMORY = "memory"
    CPU = "cpu"
    NETWORK = "network"
    DISK_IO = "disk_io"
    APPLICATION = "application"

@dataclass
class PerformanceMetrics:
    """Métricas de performance del sistema"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, float]
    db_connections: int
    db_slow_queries: int
    cache_hit_rate: float
    cache_memory_usage: float
    api_latency_p95: float
    api_throughput: float
    timestamp: datetime

@dataclass
class OptimizationAction:
    """Acción de optimización a ejecutar"""
    type: OptimizationType
    priority: int  # 1 (alta) a 5 (baja)
    description: str
    action_func: str
    parameters: Dict
    estimated_impact: float  # 0.0 a 1.0

class PerformanceOptimizer:
    """
    Servicio de optimización automática de performance
    Monitorea métricas en tiempo real y aplica optimizaciones automáticas
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.db_engine = None
        self.optimization_history: List[Dict] = []
        self.thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'db_connections': 50,
            'cache_hit_rate': 0.8,
            'api_latency_p95': 1.0,  # 1 segundo
            'slow_queries_per_minute': 10
        }
        
    async def start(self):
        """Inicializar el servicio de optimización"""
        try:
            self.redis_client = await get_redis_client()
            self.db_engine = create_async_engine(
                settings.postgres_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True
            )
            logger.info("Performance Optimizer iniciado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar Performance Optimizer: {e}")
            raise
    
    async def stop(self):
        """Detener el servicio"""
        if self.redis_client:
            await self.redis_client.close()
        if self.db_engine:
            await self.db_engine.dispose()
        logger.info("Performance Optimizer detenido")
    
    async def collect_metrics(self) -> PerformanceMetrics:
        """Recopilar métricas actuales del sistema"""
        try:
            # Métricas del sistema
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            # Métricas de base de datos
            db_metrics = await self._collect_db_metrics()
            
            # Métricas de cache
            cache_metrics = await self._collect_cache_metrics()
            
            # Métricas de API
            api_metrics = await self._collect_api_metrics()
            
            metrics = PerformanceMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=(disk.used / disk.total) * 100,
                network_io={
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                },
                db_connections=db_metrics['connections'],
                db_slow_queries=db_metrics['slow_queries'],
                cache_hit_rate=cache_metrics['hit_rate'],
                cache_memory_usage=cache_metrics['memory_usage'],
                api_latency_p95=api_metrics['latency_p95'],
                api_throughput=api_metrics['throughput'],
                timestamp=datetime.now()
            )
            
            # Actualizar métricas de Prometheus
            performance_metrics_gauge.labels('cpu', 'system').set(cpu_usage)
            performance_metrics_gauge.labels('memory', 'system').set(memory.percent)
            performance_metrics_gauge.labels('disk', 'system').set((disk.used / disk.total) * 100)
            performance_metrics_gauge.labels('connections', 'database').set(db_metrics['connections'])
            performance_metrics_gauge.labels('hit_rate', 'cache').set(cache_metrics['hit_rate'])
            performance_metrics_gauge.labels('latency_p95', 'api').set(api_metrics['latency_p95'])
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error al recopilar métricas: {e}")
            raise
    
    async def _collect_db_metrics(self) -> Dict:
        """Recopilar métricas de base de datos"""
        try:
            async with AsyncSessionFactory() as session:
                # Consultar conexiones activas
                result = await session.execute(
                    text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
                )
                connections = result.scalar()
                
                # Consultar queries lentas (últimos 5 minutos)
                result = await session.execute(
                    text("""
                    SELECT count(*) FROM pg_stat_statements 
                    WHERE mean_time > 1000 
                    AND last_exec > now() - interval '5 minutes'
                    """)
                )
                slow_queries = result.scalar() or 0
                
                return {
                    'connections': connections or 0,
                    'slow_queries': slow_queries
                }
        except Exception as e:
            logger.warning(f"Error al obtener métricas de DB: {e}")
            return {'connections': 0, 'slow_queries': 0}
    
    async def _collect_cache_metrics(self) -> Dict:
        """Recopilar métricas de cache Redis"""
        try:
            if not self.redis_client:
                return {'hit_rate': 0.0, 'memory_usage': 0.0}
            
            info = await self.redis_client.info('stats')
            keyspace_hits = info.get('keyspace_hits', 0)
            keyspace_misses = info.get('keyspace_misses', 0)
            
            hit_rate = 0.0
            if keyspace_hits + keyspace_misses > 0:
                hit_rate = keyspace_hits / (keyspace_hits + keyspace_misses)
            
            memory_info = await self.redis_client.info('memory')
            memory_usage = memory_info.get('used_memory', 0)
            
            return {
                'hit_rate': hit_rate,
                'memory_usage': memory_usage
            }
        except Exception as e:
            logger.warning(f"Error al obtener métricas de cache: {e}")
            return {'hit_rate': 0.0, 'memory_usage': 0.0}
    
    async def _collect_api_metrics(self) -> Dict:
        """Recopilar métricas de API desde Prometheus"""
        try:
            # En un sistema real, esto consultaría Prometheus
            # Por ahora simulamos valores
            return {
                'latency_p95': 0.5,  # 500ms
                'throughput': 100.0  # 100 req/s
            }
        except Exception as e:
            logger.warning(f"Error al obtener métricas de API: {e}")
            return {'latency_p95': 0.0, 'throughput': 0.0}
    
    async def analyze_performance(self, metrics: PerformanceMetrics) -> List[OptimizationAction]:
        """Analizar métricas y determinar optimizaciones necesarias"""
        actions = []
        
        # Análisis de CPU
        if metrics.cpu_usage > self.thresholds['cpu_usage']:
            actions.append(OptimizationAction(
                type=OptimizationType.CPU,
                priority=1,
                description=f"CPU usage alto: {metrics.cpu_usage:.1f}%",
                action_func='optimize_cpu_usage',
                parameters={'current_usage': metrics.cpu_usage},
                estimated_impact=0.3
            ))
        
        # Análisis de memoria
        if metrics.memory_usage > self.thresholds['memory_usage']:
            actions.append(OptimizationAction(
                type=OptimizationType.MEMORY,
                priority=1,
                description=f"Memoria usage alto: {metrics.memory_usage:.1f}%",
                action_func='optimize_memory_usage',
                parameters={'current_usage': metrics.memory_usage},
                estimated_impact=0.25
            ))
        
        # Análisis de base de datos
        if metrics.db_connections > self.thresholds['db_connections']:
            actions.append(OptimizationAction(
                type=OptimizationType.DATABASE,
                priority=2,
                description=f"Muchas conexiones DB: {metrics.db_connections}",
                action_func='optimize_db_connections',
                parameters={'current_connections': metrics.db_connections},
                estimated_impact=0.2
            ))
        
        if metrics.db_slow_queries > self.thresholds['slow_queries_per_minute']:
            actions.append(OptimizationAction(
                type=OptimizationType.DATABASE,
                priority=1,
                description=f"Queries lentas: {metrics.db_slow_queries}",
                action_func='optimize_slow_queries',
                parameters={'slow_query_count': metrics.db_slow_queries},
                estimated_impact=0.4
            ))
        
        # Análisis de cache
        if metrics.cache_hit_rate < self.thresholds['cache_hit_rate']:
            actions.append(OptimizationAction(
                type=OptimizationType.CACHE,
                priority=2,
                description=f"Cache hit rate bajo: {metrics.cache_hit_rate:.2f}",
                action_func='optimize_cache_strategy',
                parameters={'hit_rate': metrics.cache_hit_rate},
                estimated_impact=0.3
            ))
        
        # Análisis de API
        if metrics.api_latency_p95 > self.thresholds['api_latency_p95']:
            actions.append(OptimizationAction(
                type=OptimizationType.APPLICATION,
                priority=1,
                description=f"API latency alta: {metrics.api_latency_p95:.2f}s",
                action_func='optimize_api_performance',
                parameters={'latency': metrics.api_latency_p95},
                estimated_impact=0.35
            ))
        
        # Ordenar por prioridad e impacto estimado
        actions.sort(key=lambda x: (x.priority, -x.estimated_impact))
        
        return actions
    
    async def execute_optimization(self, action: OptimizationAction) -> bool:
        """Ejecutar una acción de optimización específica"""
        try:
            with performance_optimization_duration.labels(action.type.value).time():
                success = False
                
                if action.action_func == 'optimize_cpu_usage':
                    success = await self._optimize_cpu_usage(action.parameters)
                elif action.action_func == 'optimize_memory_usage':
                    success = await self._optimize_memory_usage(action.parameters)
                elif action.action_func == 'optimize_db_connections':
                    success = await self._optimize_db_connections(action.parameters)
                elif action.action_func == 'optimize_slow_queries':
                    success = await self._optimize_slow_queries(action.parameters)
                elif action.action_func == 'optimize_cache_strategy':
                    success = await self._optimize_cache_strategy(action.parameters)
                elif action.action_func == 'optimize_api_performance':
                    success = await self._optimize_api_performance(action.parameters)
                
                # Registrar acción en historial
                self.optimization_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'action': action.description,
                    'type': action.type.value,
                    'success': success,
                    'parameters': action.parameters
                })
                
                # Actualizar métricas
                status = 'success' if success else 'failed'
                optimization_actions_total.labels(action.type.value, status).inc()
                
                logger.info(f"Optimización ejecutada: {action.description} - {'Éxito' if success else 'Falló'}")
                return success
                
        except Exception as e:
            logger.error(f"Error ejecutando optimización {action.description}: {e}")
            optimization_actions_total.labels(action.type.value, 'error').inc()
            return False
    
    async def _optimize_cpu_usage(self, params: Dict) -> bool:
        """Optimizar uso de CPU"""
        try:
            # Reducir workers de proceso intensivo
            await self.redis_client.set('cpu_optimization:worker_limit', '2', ex=3600)
            
            # Implementar throttling temporal
            await self.redis_client.set('cpu_optimization:throttle_enabled', 'true', ex=1800)
            
            logger.info("Optimización de CPU aplicada: limitando workers y habilitando throttling")
            return True
        except Exception as e:
            logger.error(f"Error en optimización de CPU: {e}")
            return False
    
    async def _optimize_memory_usage(self, params: Dict) -> bool:
        """Optimizar uso de memoria"""
        try:
            # Limpiar cache expirado
            await self.redis_client.eval("""
                local keys = redis.call('keys', ARGV[1])
                for i=1,#keys do
                    local ttl = redis.call('ttl', keys[i])
                    if ttl == -1 then
                        redis.call('expire', keys[i], 3600)
                    end
                end
                return #keys
            """, 0, 'cache:*')
            
            # Configurar límites de memoria más estrictos
            await self.redis_client.config_set('maxmemory-policy', 'allkeys-lru')
            
            logger.info("Optimización de memoria aplicada: limpieza de cache y política LRU")
            return True
        except Exception as e:
            logger.error(f"Error en optimización de memoria: {e}")
            return False
    
    async def _optimize_db_connections(self, params: Dict) -> bool:
        """Optimizar conexiones de base de datos"""
        try:
            async with AsyncSessionFactory() as session:
                # Cerrar conexiones idle
                await session.execute(text("""
                    SELECT pg_terminate_backend(pid) 
                    FROM pg_stat_activity 
                    WHERE state = 'idle' 
                    AND state_change < now() - interval '10 minutes'
                    AND pid != pg_backend_pid()
                """))
                
                await session.commit()
            
            # Reducir pool size temporalmente
            await self.redis_client.set('db_optimization:pool_size_limit', '5', ex=3600)
            
            logger.info("Optimización de DB aplicada: conexiones idle cerradas y pool limitado")
            return True
        except Exception as e:
            logger.error(f"Error en optimización de DB: {e}")
            return False
    
    async def _optimize_slow_queries(self, params: Dict) -> bool:
        """Optimizar queries lentas"""
        try:
            async with AsyncSessionFactory() as session:
                # Ejecutar ANALYZE para actualizar estadísticas
                await session.execute(text("ANALYZE;"))
                await session.commit()
            
            # Habilitar cache de queries más agresivo
            await self.redis_client.set('query_optimization:aggressive_cache', 'true', ex=7200)
            
            logger.info("Optimización de queries aplicada: ANALYZE ejecutado y cache agresivo habilitado")
            return True
        except Exception as e:
            logger.error(f"Error en optimización de queries: {e}")
            return False
    
    async def _optimize_cache_strategy(self, params: Dict) -> bool:
        """Optimizar estrategia de cache"""
        try:
            # Aumentar TTL para datos estables
            await self.redis_client.eval("""
                local keys = redis.call('keys', ARGV[1])
                for i=1,#keys do
                    redis.call('expire', keys[i], ARGV[2])
                end
                return #keys
            """, 0, 'availability:*', '7200')  # 2 horas
            
            # Pre-cargar datos frecuentemente accedidos
            await self._preload_frequent_data()
            
            logger.info("Optimización de cache aplicada: TTL extendido y pre-carga de datos")
            return True
        except Exception as e:
            logger.error(f"Error en optimización de cache: {e}")
            return False
    
    async def _optimize_api_performance(self, params: Dict) -> bool:
        """Optimizar performance de API"""
        try:
            # Habilitar compresión de respuestas
            await self.redis_client.set('api_optimization:compression_enabled', 'true', ex=3600)
            
            # Reducir timeout de requests
            await self.redis_client.set('api_optimization:request_timeout', '30', ex=3600)
            
            # Habilitar cache de respuestas
            await self.redis_client.set('api_optimization:response_cache_enabled', 'true', ex=3600)
            
            logger.info("Optimización de API aplicada: compresión, timeouts y cache de respuestas")
            return True
        except Exception as e:
            logger.error(f"Error en optimización de API: {e}")
            return False
    
    async def _preload_frequent_data(self):
        """Pre-cargar datos frecuentemente accedidos"""
        try:
            # Pre-cargar configuración del hotel
            await self.redis_client.setex('preload:hotel_config', 7200, json.dumps({
                'name': 'Hotel Example',
                'rooms': 100,
                'amenities': ['wifi', 'pool', 'spa']
            }))
            
            # Pre-cargar templates de respuesta
            await self.redis_client.setex('preload:response_templates', 7200, json.dumps({
                'greeting': 'Hola, bienvenido a nuestro hotel',
                'availability': 'Verificando disponibilidad...',
                'confirmation': 'Su reserva ha sido confirmada'
            }))
            
        except Exception as e:
            logger.warning(f"Error en pre-carga de datos: {e}")
    
    async def get_optimization_report(self) -> Dict:
        """Obtener reporte de optimizaciones aplicadas"""
        try:
            # Obtener métricas actuales
            current_metrics = await self.collect_metrics()
            
            # Estadísticas de optimizaciones
            total_optimizations = len(self.optimization_history)
            successful_optimizations = sum(1 for opt in self.optimization_history if opt['success'])
            
            # Optimizaciones por tipo
            optimization_types = {}
            for opt in self.optimization_history:
                opt_type = opt['type']
                if opt_type not in optimization_types:
                    optimization_types[opt_type] = {'total': 0, 'successful': 0}
                optimization_types[opt_type]['total'] += 1
                if opt['success']:
                    optimization_types[opt_type]['successful'] += 1
            
            return {
                'current_metrics': {
                    'cpu_usage': current_metrics.cpu_usage,
                    'memory_usage': current_metrics.memory_usage,
                    'db_connections': current_metrics.db_connections,
                    'cache_hit_rate': current_metrics.cache_hit_rate,
                    'api_latency_p95': current_metrics.api_latency_p95
                },
                'optimization_stats': {
                    'total_optimizations': total_optimizations,
                    'successful_optimizations': successful_optimizations,
                    'success_rate': successful_optimizations / total_optimizations if total_optimizations > 0 else 0,
                    'by_type': optimization_types
                },
                'recent_optimizations': self.optimization_history[-10:],  # Últimas 10
                'thresholds': self.thresholds,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generando reporte de optimización: {e}")
            return {'error': str(e)}
    
    async def auto_optimize(self) -> Dict:
        """Ejecutar optimización automática completa"""
        try:
            logger.info("Iniciando ciclo de auto-optimización")
            
            # Recopilar métricas
            metrics = await self.collect_metrics()
            
            # Analizar y determinar acciones
            actions = await self.analyze_performance(metrics)
            
            if not actions:
                logger.info("No se requieren optimizaciones en este momento")
                return {
                    'status': 'no_optimization_needed',
                    'metrics': metrics.__dict__,
                    'actions_taken': 0
                }
            
            # Ejecutar acciones de alta prioridad
            executed_actions = []
            for action in actions[:3]:  # Máximo 3 acciones por ciclo
                success = await self.execute_optimization(action)
                executed_actions.append({
                    'action': action.description,
                    'type': action.type.value,
                    'priority': action.priority,
                    'success': success
                })
                
                # Esperar entre optimizaciones
                await asyncio.sleep(2)
            
            logger.info(f"Auto-optimización completada: {len(executed_actions)} acciones ejecutadas")
            
            return {
                'status': 'optimization_completed',
                'metrics': metrics.__dict__,
                'actions_taken': len(executed_actions),
                'actions': executed_actions
            }
            
        except Exception as e:
            logger.error(f"Error en auto-optimización: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'actions_taken': 0
            }

# Instancia global del optimizador
performance_optimizer = PerformanceOptimizer()

async def get_performance_optimizer() -> PerformanceOptimizer:
    """Obtener instancia del optimizador de performance"""
    return performance_optimizer