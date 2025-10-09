"""
Resource Monitor Service para Agente Hotelero IA System
Monitoreo avanzado de recursos del sistema con predicción y alertas proactivas
"""

import asyncio
import time
import psutil
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json

import redis.asyncio as redis
from prometheus_client import Histogram, Counter, Gauge

from app.core.redis_client import get_redis_client
from app.core.settings import settings

# Configurar logging
logger = logging.getLogger(__name__)

# Métricas de Prometheus
resource_monitoring_duration = Histogram(
    'resource_monitoring_duration_seconds',
    'Tiempo tomado por operaciones de monitoreo',
    ['operation']
)

system_resource_gauge = Gauge(
    'system_resource_usage',
    'Uso de recursos del sistema',
    ['resource_type', 'component']
)

resource_alerts_total = Counter(
    'resource_alerts_total',
    'Total de alertas de recursos generadas',
    ['alert_type', 'severity']
)

resource_predictions_gauge = Gauge(
    'resource_predictions',
    'Predicciones de uso de recursos',
    ['resource_type', 'timeframe']
)

class AlertSeverity(Enum):
    """Niveles de severidad de alertas"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ResourceType(Enum):
    """Tipos de recursos monitoreados"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    PROCESSES = "processes"
    DATABASE = "database"
    CACHE = "cache"

@dataclass
class ResourceMetrics:
    """Métricas de recursos del sistema"""
    cpu_percent: float
    cpu_count: int
    cpu_freq_current: float
    memory_total: int
    memory_used: int
    memory_percent: float
    memory_available: int
    swap_total: int
    swap_used: int
    swap_percent: float
    disk_total: int
    disk_used: int
    disk_percent: float
    disk_free: int
    network_bytes_sent: int
    network_bytes_recv: int
    network_packets_sent: int
    network_packets_recv: int
    network_errors: int
    process_count: int
    load_average_1m: float
    load_average_5m: float
    load_average_15m: float
    timestamp: datetime

@dataclass
class ResourceAlert:
    """Alerta de recurso"""
    resource_type: ResourceType
    severity: AlertSeverity
    threshold_value: float
    current_value: float
    message: str
    timestamp: datetime
    resolved: bool = False

@dataclass
class ResourcePrediction:
    """Predicción de recursos"""
    resource_type: ResourceType
    predicted_value: float
    confidence: float
    timeframe_minutes: int
    trend: str  # 'increasing', 'decreasing', 'stable'
    timestamp: datetime

class ResourceMonitor:
    """
    Monitor avanzado de recursos del sistema
    Monitoreo en tiempo real, alertas proactivas y predicciones
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.metrics_history: List[ResourceMetrics] = []
        self.active_alerts: List[ResourceAlert] = []
        self.predictions: Dict[ResourceType, ResourcePrediction] = {}
        
        # Configuración de thresholds
        self.thresholds = {
            ResourceType.CPU: {
                'warning': 70.0,
                'critical': 85.0
            },
            ResourceType.MEMORY: {
                'warning': 80.0,
                'critical': 90.0
            },
            ResourceType.DISK: {
                'warning': 80.0,
                'critical': 90.0
            },
            ResourceType.NETWORK: {
                'warning': 80.0,  # % de ancho de banda
                'critical': 95.0
            }
        }
        
        # Configuración de monitoreo
        self.config = {
            'monitoring_interval': 30,      # segundos
            'history_retention': 1440,     # minutos (24 horas)
            'prediction_enabled': True,    # Habilitar predicciones
            'alert_cooldown': 300,         # segundos entre alertas del mismo tipo
            'auto_cleanup_enabled': True   # Limpieza automática
        }
        
        self.last_alert_times: Dict[str, datetime] = {}
    
    async def start(self):
        """Inicializar el monitor de recursos"""
        try:
            self.redis_client = await get_redis_client()
            
            # Inicializar historia desde Redis si existe
            await self._load_metrics_history()
            
            logger.info("Resource Monitor iniciado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar Resource Monitor: {e}")
            raise
    
    async def stop(self):
        """Detener el monitor"""
        # Guardar historia en Redis
        await self._save_metrics_history()
        
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Resource Monitor detenido")
    
    async def _load_metrics_history(self):
        """Cargar historia de métricas desde Redis"""
        try:
            history_data = await self.redis_client.get('resource_monitor:history')
            if history_data:
                history_list = json.loads(history_data)
                self.metrics_history = [
                    ResourceMetrics(**item) for item in history_list[-100:]  # Últimos 100
                ]
                logger.info(f"Cargada historia de {len(self.metrics_history)} métricas")
        except Exception as e:
            logger.warning(f"Error cargando historia de métricas: {e}")
            self.metrics_history = []
    
    async def _save_metrics_history(self):
        """Guardar historia de métricas en Redis"""
        try:
            if self.metrics_history:
                # Convertir a diccionarios serializables
                history_list = []
                for metric in self.metrics_history[-100:]:  # Últimos 100
                    metric_dict = asdict(metric)
                    metric_dict['timestamp'] = metric.timestamp.isoformat()
                    history_list.append(metric_dict)
                
                await self.redis_client.setex(
                    'resource_monitor:history',
                    3600,  # 1 hora
                    json.dumps(history_list)
                )
        except Exception as e:
            logger.warning(f"Error guardando historia de métricas: {e}")
    
    async def collect_system_metrics(self) -> ResourceMetrics:
        """Recopilar métricas actuales del sistema"""
        with resource_monitoring_duration.labels('metrics_collection').time():
            try:
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_count = psutil.cpu_count()
                cpu_freq = psutil.cpu_freq()
                cpu_freq_current = cpu_freq.current if cpu_freq else 0
                
                # Memory metrics
                memory = psutil.virtual_memory()
                swap = psutil.swap_memory()
                
                # Disk metrics
                disk = psutil.disk_usage('/')
                
                # Network metrics
                network = psutil.net_io_counters()
                
                # Process metrics
                process_count = len(psutil.pids())
                
                # Load average (solo en Unix)
                try:
                    load_avg = psutil.getloadavg()
                    load_1m, load_5m, load_15m = load_avg
                except (AttributeError, OSError):
                    load_1m = load_5m = load_15m = 0.0
                
                metrics = ResourceMetrics(
                    cpu_percent=cpu_percent,
                    cpu_count=cpu_count,
                    cpu_freq_current=cpu_freq_current,
                    memory_total=memory.total,
                    memory_used=memory.used,
                    memory_percent=memory.percent,
                    memory_available=memory.available,
                    swap_total=swap.total,
                    swap_used=swap.used,
                    swap_percent=swap.percent,
                    disk_total=disk.total,
                    disk_used=disk.used,
                    disk_percent=(disk.used / disk.total) * 100,
                    disk_free=disk.free,
                    network_bytes_sent=network.bytes_sent,
                    network_bytes_recv=network.bytes_recv,
                    network_packets_sent=network.packets_sent,
                    network_packets_recv=network.packets_recv,
                    network_errors=network.errin + network.errout,
                    process_count=process_count,
                    load_average_1m=load_1m,
                    load_average_5m=load_5m,
                    load_average_15m=load_15m,
                    timestamp=datetime.now()
                )
                
                # Actualizar métricas de Prometheus
                self._update_prometheus_metrics(metrics)
                
                return metrics
                
            except Exception as e:
                logger.error(f"Error recopilando métricas del sistema: {e}")
                raise
    
    def _update_prometheus_metrics(self, metrics: ResourceMetrics):
        """Actualizar métricas de Prometheus"""
        try:
            # CPU
            system_resource_gauge.labels('cpu', 'usage_percent').set(metrics.cpu_percent)
            system_resource_gauge.labels('cpu', 'frequency_mhz').set(metrics.cpu_freq_current)
            
            # Memory
            system_resource_gauge.labels('memory', 'usage_percent').set(metrics.memory_percent)
            system_resource_gauge.labels('memory', 'used_bytes').set(metrics.memory_used)
            system_resource_gauge.labels('memory', 'available_bytes').set(metrics.memory_available)
            
            # Swap
            system_resource_gauge.labels('swap', 'usage_percent').set(metrics.swap_percent)
            system_resource_gauge.labels('swap', 'used_bytes').set(metrics.swap_used)
            
            # Disk
            system_resource_gauge.labels('disk', 'usage_percent').set(metrics.disk_percent)
            system_resource_gauge.labels('disk', 'used_bytes').set(metrics.disk_used)
            system_resource_gauge.labels('disk', 'free_bytes').set(metrics.disk_free)
            
            # Network
            system_resource_gauge.labels('network', 'bytes_sent').set(metrics.network_bytes_sent)
            system_resource_gauge.labels('network', 'bytes_recv').set(metrics.network_bytes_recv)
            system_resource_gauge.labels('network', 'errors').set(metrics.network_errors)
            
            # Process
            system_resource_gauge.labels('processes', 'count').set(metrics.process_count)
            
            # Load average
            system_resource_gauge.labels('load', '1m').set(metrics.load_average_1m)
            system_resource_gauge.labels('load', '5m').set(metrics.load_average_5m)
            system_resource_gauge.labels('load', '15m').set(metrics.load_average_15m)
            
        except Exception as e:
            logger.warning(f"Error actualizando métricas de Prometheus: {e}")
    
    async def analyze_resource_trends(self, metrics: ResourceMetrics):
        """Analizar tendencias de recursos y generar alertas"""
        try:
            # Agregar métricas a historia
            self.metrics_history.append(metrics)
            
            # Mantener solo las últimas N métricas
            if len(self.metrics_history) > self.config['history_retention']:
                self.metrics_history = self.metrics_history[-self.config['history_retention']:]
            
            # Analizar cada tipo de recurso
            await self._analyze_cpu_trends(metrics)
            await self._analyze_memory_trends(metrics)
            await self._analyze_disk_trends(metrics)
            await self._analyze_network_trends(metrics)
            
            # Generar predicciones si está habilitado
            if self.config['prediction_enabled']:
                await self._generate_predictions()
            
        except Exception as e:
            logger.error(f"Error analizando tendencias de recursos: {e}")
    
    async def _analyze_cpu_trends(self, metrics: ResourceMetrics):
        """Analizar tendencias de CPU"""
        try:
            cpu_usage = metrics.cpu_percent
            
            # Verificar thresholds
            if cpu_usage >= self.thresholds[ResourceType.CPU]['critical']:
                await self._generate_alert(
                    ResourceType.CPU,
                    AlertSeverity.CRITICAL,
                    self.thresholds[ResourceType.CPU]['critical'],
                    cpu_usage,
                    f"Uso crítico de CPU: {cpu_usage:.1f}%"
                )
            elif cpu_usage >= self.thresholds[ResourceType.CPU]['warning']:
                await self._generate_alert(
                    ResourceType.CPU,
                    AlertSeverity.HIGH,
                    self.thresholds[ResourceType.CPU]['warning'],
                    cpu_usage,
                    f"Uso alto de CPU: {cpu_usage:.1f}%"
                )
            
            # Análisis de tendencia
            if len(self.metrics_history) >= 5:
                recent_cpu = [m.cpu_percent for m in self.metrics_history[-5:]]
                cpu_trend = self._calculate_trend(recent_cpu)
                
                if cpu_trend > 0.1 and cpu_usage > 60:  # Tendencia creciente
                    await self._generate_alert(
                        ResourceType.CPU,
                        AlertSeverity.MEDIUM,
                        60.0,
                        cpu_usage,
                        f"Tendencia creciente en CPU: {cpu_usage:.1f}% (+{cpu_trend:.1f}%/min)"
                    )
            
        except Exception as e:
            logger.warning(f"Error analizando tendencias de CPU: {e}")
    
    async def _analyze_memory_trends(self, metrics: ResourceMetrics):
        """Analizar tendencias de memoria"""
        try:
            memory_usage = metrics.memory_percent
            
            # Verificar thresholds
            if memory_usage >= self.thresholds[ResourceType.MEMORY]['critical']:
                await self._generate_alert(
                    ResourceType.MEMORY,
                    AlertSeverity.CRITICAL,
                    self.thresholds[ResourceType.MEMORY]['critical'],
                    memory_usage,
                    f"Uso crítico de memoria: {memory_usage:.1f}%"
                )
            elif memory_usage >= self.thresholds[ResourceType.MEMORY]['warning']:
                await self._generate_alert(
                    ResourceType.MEMORY,
                    AlertSeverity.HIGH,
                    self.thresholds[ResourceType.MEMORY]['warning'],
                    memory_usage,
                    f"Uso alto de memoria: {memory_usage:.1f}%"
                )
            
            # Verificar swap usage
            if metrics.swap_percent > 10:  # 10% swap usage
                await self._generate_alert(
                    ResourceType.MEMORY,
                    AlertSeverity.MEDIUM,
                    10.0,
                    metrics.swap_percent,
                    f"Uso de swap detectado: {metrics.swap_percent:.1f}%"
                )
            
        except Exception as e:
            logger.warning(f"Error analizando tendencias de memoria: {e}")
    
    async def _analyze_disk_trends(self, metrics: ResourceMetrics):
        """Analizar tendencias de disco"""
        try:
            disk_usage = metrics.disk_percent
            
            # Verificar thresholds
            if disk_usage >= self.thresholds[ResourceType.DISK]['critical']:
                await self._generate_alert(
                    ResourceType.DISK,
                    AlertSeverity.CRITICAL,
                    self.thresholds[ResourceType.DISK]['critical'],
                    disk_usage,
                    f"Uso crítico de disco: {disk_usage:.1f}%"
                )
            elif disk_usage >= self.thresholds[ResourceType.DISK]['warning']:
                await self._generate_alert(
                    ResourceType.DISK,
                    AlertSeverity.HIGH,
                    self.thresholds[ResourceType.DISK]['warning'],
                    disk_usage,
                    f"Uso alto de disco: {disk_usage:.1f}%"
                )
            
            # Verificar crecimiento rápido de uso de disco
            if len(self.metrics_history) >= 10:
                recent_disk = [m.disk_percent for m in self.metrics_history[-10:]]
                disk_growth = recent_disk[-1] - recent_disk[0]  # Crecimiento en últimas 10 mediciones
                
                if disk_growth > 5:  # Crecimiento de 5% en poco tiempo
                    await self._generate_alert(
                        ResourceType.DISK,
                        AlertSeverity.MEDIUM,
                        5.0,
                        disk_growth,
                        f"Crecimiento rápido de uso de disco: +{disk_growth:.1f}%"
                    )
            
        except Exception as e:
            logger.warning(f"Error analizando tendencias de disco: {e}")
    
    async def _analyze_network_trends(self, metrics: ResourceMetrics):
        """Analizar tendencias de red"""
        try:
            # Calcular throughput si tenemos historia
            if len(self.metrics_history) >= 2:
                prev_metrics = self.metrics_history[-2]
                time_diff = (metrics.timestamp - prev_metrics.timestamp).total_seconds()
                
                if time_diff > 0:
                    bytes_sent_rate = (metrics.network_bytes_sent - prev_metrics.network_bytes_sent) / time_diff
                    bytes_recv_rate = (metrics.network_bytes_recv - prev_metrics.network_bytes_recv) / time_diff
                    
                    # Actualizar métricas de throughput
                    system_resource_gauge.labels('network', 'throughput_sent_bps').set(bytes_sent_rate)
                    system_resource_gauge.labels('network', 'throughput_recv_bps').set(bytes_recv_rate)
            
            # Verificar errores de red
            if metrics.network_errors > 0:
                if len(self.metrics_history) >= 2:
                    prev_errors = self.metrics_history[-2].network_errors
                    new_errors = metrics.network_errors - prev_errors
                    
                    if new_errors > 10:  # Más de 10 errores nuevos
                        await self._generate_alert(
                            ResourceType.NETWORK,
                            AlertSeverity.MEDIUM,
                            10.0,
                            new_errors,
                            f"Errores de red detectados: {new_errors} nuevos errores"
                        )
            
        except Exception as e:
            logger.warning(f"Error analizando tendencias de red: {e}")
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calcular tendencia de una serie de valores"""
        if len(values) < 2:
            return 0.0
        
        # Regresión lineal simple
        n = len(values)
        x_values = list(range(n))
        
        sum_x = sum(x_values)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(x_values, values))
        sum_x2 = sum(x * x for x in x_values)
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        return slope
    
    async def _generate_alert(
        self,
        resource_type: ResourceType,
        severity: AlertSeverity,
        threshold: float,
        current_value: float,
        message: str
    ):
        """Generar alerta de recurso"""
        try:
            # Verificar cooldown
            alert_key = f"{resource_type.value}_{severity.value}"
            now = datetime.now()
            
            if alert_key in self.last_alert_times:
                time_since_last = (now - self.last_alert_times[alert_key]).total_seconds()
                if time_since_last < self.config['alert_cooldown']:
                    return  # En cooldown
            
            # Crear alerta
            alert = ResourceAlert(
                resource_type=resource_type,
                severity=severity,
                threshold_value=threshold,
                current_value=current_value,
                message=message,
                timestamp=now
            )
            
            self.active_alerts.append(alert)
            self.last_alert_times[alert_key] = now
            
            # Actualizar métricas
            resource_alerts_total.labels(resource_type.value, severity.value).inc()
            
            # Guardar alerta en Redis
            await self._save_alert_to_redis(alert)
            
            logger.warning(f"ALERTA {severity.value.upper()}: {message}")
            
        except Exception as e:
            logger.error(f"Error generando alerta: {e}")
    
    async def _save_alert_to_redis(self, alert: ResourceAlert):
        """Guardar alerta en Redis"""
        try:
            alert_data = {
                'resource_type': alert.resource_type.value,
                'severity': alert.severity.value,
                'threshold_value': alert.threshold_value,
                'current_value': alert.current_value,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'resolved': alert.resolved
            }
            
            # Guardar en lista de alertas
            alert_key = f"alerts:{datetime.now().strftime('%Y%m%d')}"
            await self.redis_client.lpush(alert_key, json.dumps(alert_data))
            await self.redis_client.expire(alert_key, 86400 * 7)  # 7 días
            
        except Exception as e:
            logger.warning(f"Error guardando alerta en Redis: {e}")
    
    async def _generate_predictions(self):
        """Generar predicciones de recursos"""
        try:
            if len(self.metrics_history) < 10:
                return  # Necesitamos historia suficiente
            
            # Predicción de CPU
            cpu_values = [m.cpu_percent for m in self.metrics_history[-10:]]
            cpu_prediction = await self._predict_resource_usage(cpu_values, ResourceType.CPU)
            if cpu_prediction:
                self.predictions[ResourceType.CPU] = cpu_prediction
                resource_predictions_gauge.labels('cpu', '15min').set(cpu_prediction.predicted_value)
            
            # Predicción de memoria
            memory_values = [m.memory_percent for m in self.metrics_history[-10:]]
            memory_prediction = await self._predict_resource_usage(memory_values, ResourceType.MEMORY)
            if memory_prediction:
                self.predictions[ResourceType.MEMORY] = memory_prediction
                resource_predictions_gauge.labels('memory', '15min').set(memory_prediction.predicted_value)
            
            # Predicción de disco
            disk_values = [m.disk_percent for m in self.metrics_history[-10:]]
            disk_prediction = await self._predict_resource_usage(disk_values, ResourceType.DISK)
            if disk_prediction:
                self.predictions[ResourceType.DISK] = disk_prediction
                resource_predictions_gauge.labels('disk', '15min').set(disk_prediction.predicted_value)
            
        except Exception as e:
            logger.warning(f"Error generando predicciones: {e}")
    
    async def _predict_resource_usage(
        self,
        values: List[float],
        resource_type: ResourceType,
        timeframe_minutes: int = 15
    ) -> Optional[ResourcePrediction]:
        """Predecir uso de recurso usando regresión lineal simple"""
        try:
            if len(values) < 3:
                return None
            
            # Calcular tendencia
            trend_value = self._calculate_trend(values)
            
            # Predecir valor futuro
            current_value = values[-1]
            predicted_value = current_value + (trend_value * timeframe_minutes)
            
            # Calcular confianza basada en variabilidad
            variance = sum((v - sum(values) / len(values)) ** 2 for v in values) / len(values)
            confidence = max(0.1, 1.0 - (variance / 100))  # Normalizar varianza
            
            # Determinar tendencia
            if trend_value > 0.5:
                trend = 'increasing'
            elif trend_value < -0.5:
                trend = 'decreasing'
            else:
                trend = 'stable'
            
            # Limitar predicción a rangos razonables
            predicted_value = max(0, min(predicted_value, 100))
            
            return ResourcePrediction(
                resource_type=resource_type,
                predicted_value=predicted_value,
                confidence=confidence,
                timeframe_minutes=timeframe_minutes,
                trend=trend,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.warning(f"Error prediciendo uso de {resource_type.value}: {e}")
            return None
    
    async def get_resource_report(self) -> Dict:
        """Obtener reporte completo de recursos"""
        try:
            # Obtener métricas actuales
            current_metrics = await self.collect_system_metrics()
            
            # Alertas activas (últimas 24 horas)
            active_alerts = [
                alert for alert in self.active_alerts
                if (datetime.now() - alert.timestamp).total_seconds() < 86400 and not alert.resolved
            ]
            
            return {
                'current_metrics': {
                    'cpu_percent': current_metrics.cpu_percent,
                    'memory_percent': current_metrics.memory_percent,
                    'memory_used_gb': current_metrics.memory_used // (1024**3),
                    'memory_available_gb': current_metrics.memory_available // (1024**3),
                    'disk_percent': current_metrics.disk_percent,
                    'disk_used_gb': current_metrics.disk_used // (1024**3),
                    'disk_free_gb': current_metrics.disk_free // (1024**3),
                    'process_count': current_metrics.process_count,
                    'load_average_1m': current_metrics.load_average_1m,
                    'network_errors': current_metrics.network_errors
                },
                'thresholds': {
                    resource.value: thresholds
                    for resource, thresholds in self.thresholds.items()
                },
                'active_alerts': [
                    {
                        'resource': alert.resource_type.value,
                        'severity': alert.severity.value,
                        'message': alert.message,
                        'current_value': alert.current_value,
                        'threshold': alert.threshold_value,
                        'timestamp': alert.timestamp.isoformat()
                    }
                    for alert in active_alerts
                ],
                'predictions': {
                    resource.value: {
                        'predicted_value': pred.predicted_value,
                        'confidence': pred.confidence,
                        'trend': pred.trend,
                        'timeframe_minutes': pred.timeframe_minutes
                    }
                    for resource, pred in self.predictions.items()
                },
                'monitoring_config': self.config,
                'metrics_history_count': len(self.metrics_history),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generando reporte de recursos: {e}")
            return {'error': str(e)}
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolver una alerta específica"""
        try:
            # En una implementación real, buscaríamos por ID
            # Por simplicidad, resolvemos alertas por tipo y timestamp
            resolved_count = 0
            
            for alert in self.active_alerts:
                if not alert.resolved and alert_id in alert.message:
                    alert.resolved = True
                    resolved_count += 1
            
            logger.info(f"Resueltas {resolved_count} alertas")
            return resolved_count > 0
            
        except Exception as e:
            logger.error(f"Error resolviendo alerta: {e}")
            return False
    
    async def cleanup_old_data(self):
        """Limpiar datos antiguos"""
        try:
            if not self.config['auto_cleanup_enabled']:
                return
            
            now = datetime.now()
            cutoff_time = now - timedelta(hours=24)
            
            # Limpiar alertas antiguas
            self.active_alerts = [
                alert for alert in self.active_alerts
                if alert.timestamp > cutoff_time
            ]
            
            # Limpiar métricas antiguas
            self.metrics_history = [
                metrics for metrics in self.metrics_history
                if metrics.timestamp > cutoff_time
            ]
            
            logger.info("Limpieza de datos antiguos completada")
            
        except Exception as e:
            logger.warning(f"Error en limpieza de datos: {e}")
    
    async def continuous_monitoring(self):
        """Monitoreo continuo en bucle"""
        logger.info("Iniciando monitoreo continuo de recursos")
        
        try:
            while True:
                # Recopilar métricas
                metrics = await self.collect_system_metrics()
                
                # Analizar tendencias y generar alertas
                await self.analyze_resource_trends(metrics)
                
                # Limpiar datos antiguos periódicamente
                if len(self.metrics_history) % 100 == 0:
                    await self.cleanup_old_data()
                
                # Guardar estado periódicamente
                if len(self.metrics_history) % 50 == 0:
                    await self._save_metrics_history()
                
                # Esperar intervalo de monitoreo
                await asyncio.sleep(self.config['monitoring_interval'])
                
        except asyncio.CancelledError:
            logger.info("Monitoreo continuo cancelado")
        except Exception as e:
            logger.error(f"Error en monitoreo continuo: {e}")

# Instancia global del monitor
resource_monitor = ResourceMonitor()

async def get_resource_monitor() -> ResourceMonitor:
    """Obtener instancia del monitor de recursos"""
    return resource_monitor