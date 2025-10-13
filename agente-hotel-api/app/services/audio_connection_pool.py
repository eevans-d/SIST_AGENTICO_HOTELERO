"""
Pool de conexiones optimizado para servicios de audio externos.
Gestiona conexiones persistentes para STT/TTS y otros servicios de audio.
"""

import asyncio
import time
from typing import Dict, Optional, List, Any, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
import logging
from contextlib import asynccontextmanager

# TEMPORAL FIX: Comentado hasta agregar aiohttp a requirements
# import aiohttp
from prometheus_client import Counter, Histogram, Gauge
import redis.asyncio as redis

logger = logging.getLogger(__name__)

T = TypeVar('T')

class PoolStatus(Enum):
    """Estados del pool de conexiones."""
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    SHUTDOWN = "shutdown"

class ServiceType(Enum):
    """Tipos de servicios de audio."""
    STT_SERVICE = "stt_service"
    TTS_SERVICE = "tts_service"
    AUDIO_PROCESSING = "audio_processing"
    TRANSCRIPTION = "transcription"
    SYNTHESIS = "synthesis"

@dataclass
class ConnectionConfig:
    """Configuración de conexión para un servicio."""
    base_url: str
    max_connections: int = 10
    timeout_seconds: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    health_check_interval: int = 60
    idle_timeout: int = 300
    headers: Dict[str, str] = field(default_factory=dict)
    auth_token: Optional[str] = None

@dataclass
class PoolMetrics:
    """Métricas del pool de conexiones."""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0

class ConnectionPool(Generic[T]):
    """
    Pool de conexiones genérico con gestión automática de salud y balanceo.
    """
    
    def __init__(
        self,
        service_type: ServiceType,
        config: ConnectionConfig,
        redis_client: Optional[redis.Redis] = None
    ):
        self.service_type = service_type
        self.config = config
        self.redis_client = redis_client
        
        # Pool de conexiones
        self._connections: List[Any] = []
        self._available_connections: asyncio.Queue = asyncio.Queue()
        self._connection_health: Dict[int, bool] = {}
        
        # Estado del pool
        self.status = PoolStatus.INITIALIZING
        self._metrics = PoolMetrics()
        self._lock = asyncio.Lock()
        
        # Tasks de mantenimiento
        self._health_check_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Métricas de Prometheus
        self.connection_pool_size = Gauge(
            "audio_connection_pool_size",
            "Tamaño del pool de conexiones",
            ["service_type", "status"]
        )
        self.connection_requests = Counter(
            "audio_connection_requests_total",
            "Requests totales por servicio",
            ["service_type", "result"]
        )
        self.connection_latency = Histogram(
            "audio_connection_latency_seconds",
            "Latencia de conexiones de audio",
            ["service_type", "endpoint"]
        )
        self.pool_health_score = Gauge(
            "audio_pool_health_score",
            "Score de salud del pool (0-1)",
            ["service_type"]
        )
    
    async def start(self):
        """Inicia el pool de conexiones."""
        async with self._lock:
            if self._running:
                return
            
            self._running = True
            self.status = PoolStatus.INITIALIZING
            
            # Crear conexiones iniciales
            await self._initialize_connections()
            
            # Iniciar tasks de mantenimiento
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self.status = PoolStatus.HEALTHY
            logger.info(f"ConnectionPool iniciado para {self.service_type.value}")
    
    async def stop(self):
        """Detiene el pool de conexiones."""
        async with self._lock:
            if not self._running:
                return
            
            self._running = False
            self.status = PoolStatus.SHUTDOWN
            
            # Cancelar tasks de mantenimiento
            if self._health_check_task:
                self._health_check_task.cancel()
            if self._cleanup_task:
                self._cleanup_task.cancel()
            
            # Cerrar todas las conexiones
            await self._close_all_connections()
            
            logger.info(f"ConnectionPool detenido para {self.service_type.value}")
    
    @asynccontextmanager
    async def get_connection(self):
        """
        Context manager para obtener una conexión del pool.
        """
        if not self._running:
            raise RuntimeError("Connection pool no está ejecutándose")
        
        connection = None
        try:
            # Obtener conexión disponible
            connection = await self._acquire_connection()
            yield connection
            
        except Exception as e:
            self.connection_requests.labels(
                service_type=self.service_type.value,
                result="error"
            ).inc()
            self._metrics.failed_requests += 1
            raise
        
        finally:
            if connection:
                await self._release_connection(connection)
    
    async def execute_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Any:
        """
        Ejecuta una request usando una conexión del pool.
        """
        start_time = time.time()
        
        async with self.get_connection() as session:
            url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
            # Configurar headers
            headers = kwargs.get('headers', {})
            headers.update(self.config.headers)
            
            if self.config.auth_token:
                headers['Authorization'] = f"Bearer {self.config.auth_token}"
            
            kwargs['headers'] = headers
            kwargs['timeout'] = Any(
                total=self.config.timeout_seconds
            )
            
            try:
                response = await session.request(method, url, **kwargs)
                
                # Actualizar métricas de éxito
                self.connection_requests.labels(
                    service_type=self.service_type.value,
                    result="success"
                ).inc()
                self._metrics.successful_requests += 1
                
                return response
                
            except Exception as e:
                logger.error(f"Error en request a {url}: {e}")
                raise
            
            finally:
                # Actualizar latencia
                latency = time.time() - start_time
                self.connection_latency.labels(
                    service_type=self.service_type.value,
                    endpoint=endpoint
                ).observe(latency)
                
                self._update_average_response_time(latency)
    
    async def _initialize_connections(self):
        """Inicializa las conexiones del pool."""
        for i in range(self.config.max_connections):
            try:
                session = Any(
                    connector=Any(
                        limit=1,
                        ttl_dns_cache=300,
                        use_dns_cache=True,
                        enable_cleanup_closed=True
                    )
                )
                
                self._connections.append(session)
                self._connection_health[i] = True
                await self._available_connections.put(session)
                
            except Exception as e:
                logger.error(f"Error creando conexión {i}: {e}")
                self._connection_health[i] = False
        
        self._update_pool_metrics()
    
    async def _acquire_connection(self) -> Any:
        """Adquiere una conexión del pool."""
        try:
            # Intentar obtener conexión con timeout
            connection = await asyncio.wait_for(
                self._available_connections.get(),
                timeout=self.config.timeout_seconds
            )
            
            self._metrics.active_connections += 1
            self._update_pool_metrics()
            
            return connection
            
        except asyncio.TimeoutError:
            self.status = PoolStatus.CRITICAL
            raise RuntimeError("Timeout obteniendo conexión del pool")
    
    async def _release_connection(self, connection: Any):
        """Libera una conexión de vuelta al pool."""
        try:
            if not connection.closed:
                await self._available_connections.put(connection)
                self._metrics.active_connections = max(0, self._metrics.active_connections - 1)
                self._update_pool_metrics()
            else:
                # Conexión cerrada, crear una nueva
                await self._replace_connection(connection)
                
        except Exception as e:
            logger.error(f"Error liberando conexión: {e}")
    
    async def _replace_connection(self, old_connection: Any):
        """Reemplaza una conexión defectuosa."""
        try:
            # Cerrar conexión antigua
            if not old_connection.closed:
                await old_connection.close()
            
            # Crear nueva conexión
            new_session = Any(
                connector=Any(
                    limit=1,
                    ttl_dns_cache=300,
                    use_dns_cache=True,
                    enable_cleanup_closed=True
                )
            )
            
            # Reemplazar en la lista
            try:
                index = self._connections.index(old_connection)
                self._connections[index] = new_session
                self._connection_health[index] = True
            except ValueError:
                # Si no se encuentra, añadir al final
                self._connections.append(new_session)
                self._connection_health[len(self._connections) - 1] = True
            
            await self._available_connections.put(new_session)
            
        except Exception as e:
            logger.error(f"Error reemplazando conexión: {e}")
    
    async def _health_check_loop(self):
        """Bucle de verificación de salud de conexiones."""
        while self._running:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error en health check: {e}")
    
    async def _perform_health_check(self):
        """Realiza verificación de salud de las conexiones."""
        healthy_connections = 0
        total_connections = len(self._connections)
        
        for i, session in enumerate(self._connections):
            try:
                if session.closed:
                    self._connection_health[i] = False
                    continue
                
                # Verificar con un request simple (HEAD al endpoint base)
                async with session.head(
                    self.config.base_url,
                    timeout=Any(total=5.0)
                ) as response:
                    if response.status < 500:
                        self._connection_health[i] = True
                        healthy_connections += 1
                    else:
                        self._connection_health[i] = False
                        
            except Exception:
                self._connection_health[i] = False
        
        # Actualizar estado del pool
        health_ratio = healthy_connections / total_connections if total_connections > 0 else 0
        
        if health_ratio >= 0.8:
            self.status = PoolStatus.HEALTHY
        elif health_ratio >= 0.5:
            self.status = PoolStatus.DEGRADED
        else:
            self.status = PoolStatus.CRITICAL
        
        # Actualizar métricas
        self.pool_health_score.labels(
            service_type=self.service_type.value
        ).set(health_ratio)
        
        self._update_pool_metrics()
    
    async def _cleanup_loop(self):
        """Bucle de limpieza de conexiones inactivas."""
        while self._running:
            try:
                await asyncio.sleep(60)  # Limpieza cada minuto
                await self._cleanup_idle_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error en cleanup: {e}")
    
    async def _cleanup_idle_connections(self):
        """Limpia conexiones inactivas o defectuosas."""
        connections_to_replace = []
        
        for i, (session, is_healthy) in enumerate(
            zip(self._connections, self._connection_health.values())
        ):
            if not is_healthy or session.closed:
                connections_to_replace.append((i, session))
        
        # Reemplazar conexiones defectuosas
        for index, old_session in connections_to_replace:
            try:
                await self._replace_connection(old_session)
                logger.debug(f"Reemplazada conexión {index} defectuosa")
            except Exception as e:
                logger.error(f"Error reemplazando conexión {index}: {e}")
    
    async def _close_all_connections(self):
        """Cierra todas las conexiones del pool."""
        for session in self._connections:
            try:
                if not session.closed:
                    await session.close()
            except Exception as e:
                logger.error(f"Error cerrando conexión: {e}")
        
        self._connections.clear()
        self._connection_health.clear()
        
        # Limpiar queue
        while not self._available_connections.empty():
            try:
                self._available_connections.get_nowait()
            except asyncio.QueueEmpty:
                break
    
    def _update_pool_metrics(self):
        """Actualiza métricas del pool."""
        healthy_count = sum(1 for h in self._connection_health.values() if h)
        
        self.connection_pool_size.labels(
            service_type=self.service_type.value,
            status="healthy"
        ).set(healthy_count)
        
        self.connection_pool_size.labels(
            service_type=self.service_type.value,
            status="total"
        ).set(len(self._connections))
        
        self._metrics.total_connections = len(self._connections)
        self._metrics.idle_connections = self._available_connections.qsize()
        self._metrics.failed_connections = sum(
            1 for h in self._connection_health.values() if not h
        )
    
    def _update_average_response_time(self, latency: float):
        """Actualiza el tiempo promedio de respuesta."""
        if self._metrics.total_requests == 0:
            self._metrics.average_response_time = latency
        else:
            # Media móvil simple
            alpha = 0.1  # Factor de suavizado
            self._metrics.average_response_time = (
                alpha * latency + 
                (1 - alpha) * self._metrics.average_response_time
            )
        
        self._metrics.total_requests += 1
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas del pool."""
        return {
            "service_type": self.service_type.value,
            "status": self.status.value,
            "metrics": {
                "total_connections": self._metrics.total_connections,
                "active_connections": self._metrics.active_connections,
                "idle_connections": self._metrics.idle_connections,
                "failed_connections": self._metrics.failed_connections,
                "total_requests": self._metrics.total_requests,
                "successful_requests": self._metrics.successful_requests,
                "failed_requests": self._metrics.failed_requests,
                "average_response_time": self._metrics.average_response_time,
                "success_rate": (
                    self._metrics.successful_requests / self._metrics.total_requests
                    if self._metrics.total_requests > 0 else 0.0
                )
            },
            "config": {
                "max_connections": self.config.max_connections,
                "timeout_seconds": self.config.timeout_seconds,
                "retry_attempts": self.config.retry_attempts
            }
        }


class AudioConnectionManager:
    """
    Gestor centralizado de pools de conexiones para servicios de audio.
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.pools: Dict[ServiceType, ConnectionPool] = {}
        self._lock = asyncio.Lock()
    
    async def register_service(
        self,
        service_type: ServiceType,
        config: ConnectionConfig
    ):
        """Registra un nuevo servicio de audio."""
        async with self._lock:
            if service_type in self.pools:
                await self.pools[service_type].stop()
            
            pool = ConnectionPool(service_type, config, self.redis_client)
            await pool.start()
            
            self.pools[service_type] = pool
            logger.info(f"Servicio registrado: {service_type.value}")
    
    async def get_pool(self, service_type: ServiceType) -> ConnectionPool:
        """Obtiene el pool para un tipo de servicio."""
        if service_type not in self.pools:
            raise ValueError(f"Servicio no registrado: {service_type.value}")
        
        return self.pools[service_type]
    
    async def execute_request(
        self,
        service_type: ServiceType,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Any:
        """Ejecuta una request usando el pool apropiado."""
        pool = await self.get_pool(service_type)
        return await pool.execute_request(method, endpoint, **kwargs)
    
    async def get_all_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de todos los pools."""
        metrics = {}
        
        for service_type, pool in self.pools.items():
            metrics[service_type.value] = await pool.get_metrics()
        
        return {
            "pools": metrics,
            "total_pools": len(self.pools),
            "total_services": len(ServiceType)
        }
    
    async def shutdown_all(self):
        """Cierra todos los pools de conexiones."""
        tasks = []
        for pool in self.pools.values():
            tasks.append(pool.stop())
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self.pools.clear()
        logger.info("Todos los pools de conexiones cerrados")