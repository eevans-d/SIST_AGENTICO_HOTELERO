"""
Auto Scaling Service para Agente Hotelero IA System
Sistema de escalado automático basado en métricas y predicciones
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import math

import redis.asyncio as redis
from prometheus_client import Histogram, Counter, Gauge

from app.core.redis_client import get_redis_client
from app.core.settings import settings
from app.services.resource_monitor import get_resource_monitor, ResourceType

# Configurar logging
logger = logging.getLogger(__name__)

# Métricas de Prometheus
scaling_operations_total = Counter(
    'scaling_operations_total',
    'Total de operaciones de escalado',
    ['operation', 'resource_type', 'status']
)

scaling_decision_duration = Histogram(
    'scaling_decision_duration_seconds',
    'Tiempo tomado para decisiones de escalado',
    ['decision_type']
)

active_instances_gauge = Gauge(
    'active_instances',
    'Número de instancias activas por servicio',
    ['service_name']
)

scaling_efficiency_gauge = Gauge(
    'scaling_efficiency',
    'Eficiencia del escalado (0-1)',
    ['metric_type']
)

class ScalingAction(Enum):
    """Acciones de escalado"""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    NO_ACTION = "no_action"
    REBALANCE = "rebalance"

class ScalingTrigger(Enum):
    """Triggers para escalado"""
    CPU_HIGH = "cpu_high"
    MEMORY_HIGH = "memory_high"
    LOAD_HIGH = "load_high"
    RESPONSE_TIME_HIGH = "response_time_high"
    QUEUE_SIZE_HIGH = "queue_size_high"
    PREDICTION_BASED = "prediction_based"
    SCHEDULE_BASED = "schedule_based"

class ServiceTier(Enum):
    """Niveles de servicio"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class ScalingRule:
    """Regla de escalado"""
    name: str
    service_name: str
    metric_type: str
    threshold_up: float
    threshold_down: float
    cooldown_seconds: int
    min_instances: int
    max_instances: int
    scale_up_step: int
    scale_down_step: int
    enabled: bool = True

@dataclass
class ScalingDecision:
    """Decisión de escalado"""
    service_name: str
    current_instances: int
    target_instances: int
    action: ScalingAction
    trigger: ScalingTrigger
    metric_value: float
    threshold: float
    confidence: float
    reason: str
    timestamp: datetime

@dataclass
class ServiceConfig:
    """Configuración de servicio escalable"""
    name: str
    tier: ServiceTier
    min_instances: int
    max_instances: int
    target_cpu_percent: float
    target_memory_percent: float
    target_response_time_ms: float
    scale_up_cooldown: int
    scale_down_cooldown: int
    health_check_url: str
    startup_time_seconds: int

class AutoScaler:
    """
    Sistema de escalado automático inteligente
    Escalado basado en métricas, predicciones y horarios
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.resource_monitor = None
        
        # Configuración de servicios
        self.service_configs: Dict[str, ServiceConfig] = {}
        self.scaling_rules: Dict[str, List[ScalingRule]] = {}
        self.scaling_history: List[ScalingDecision] = []
        
        # Estado actual
        self.current_instances: Dict[str, int] = {}
        self.last_scaling_times: Dict[str, datetime] = {}
        
        # Configuración del escalador
        self.config = {
            'evaluation_interval': 30,      # segundos
            'prediction_weight': 0.3,       # peso de predicciones en decisiones
            'trend_weight': 0.4,            # peso de tendencias
            'current_weight': 0.3,          # peso de métricas actuales
            'safety_margin': 0.1,           # margen de seguridad (10%)
            'max_scaling_rate': 0.5,        # máx 50% cambio por operación
            'enable_proactive_scaling': True,
            'enable_schedule_scaling': True,
            'enable_ml_predictions': False   # Para futuras mejoras
        }
        
        # Horarios de escalado programado
        self.scaling_schedules = {
            'peak_hours': {
                'start_time': '08:00',
                'end_time': '22:00',
                'scale_factor': 1.5,
                'services': ['agente-api', 'nlp-engine', 'orchestrator']
            },
            'low_hours': {
                'start_time': '01:00',
                'end_time': '06:00',
                'scale_factor': 0.7,
                'services': ['agente-api', 'orchestrator']
            }
        }
        
        self._initialize_default_configs()
    
    def _initialize_default_configs(self):
        """Inicializar configuraciones por defecto"""
        # Configuración de servicios
        self.service_configs = {
            'agente-api': ServiceConfig(
                name='agente-api',
                tier=ServiceTier.CRITICAL,
                min_instances=2,
                max_instances=10,
                target_cpu_percent=70.0,
                target_memory_percent=80.0,
                target_response_time_ms=500.0,
                scale_up_cooldown=300,    # 5 minutos
                scale_down_cooldown=600,  # 10 minutos
                health_check_url='/health/ready',
                startup_time_seconds=60
            ),
            'orchestrator': ServiceConfig(
                name='orchestrator',
                tier=ServiceTier.HIGH,
                min_instances=1,
                max_instances=5,
                target_cpu_percent=60.0,
                target_memory_percent=75.0,
                target_response_time_ms=200.0,
                scale_up_cooldown=180,
                scale_down_cooldown=360,
                health_check_url='/health',
                startup_time_seconds=45
            ),
            'nlp-engine': ServiceConfig(
                name='nlp-engine',
                tier=ServiceTier.HIGH,
                min_instances=1,
                max_instances=4,
                target_cpu_percent=80.0,
                target_memory_percent=70.0,
                target_response_time_ms=300.0,
                scale_up_cooldown=240,
                scale_down_cooldown=480,
                health_check_url='/health',
                startup_time_seconds=30
            ),
            'pms-adapter': ServiceConfig(
                name='pms-adapter',
                tier=ServiceTier.MEDIUM,
                min_instances=1,
                max_instances=3,
                target_cpu_percent=70.0,
                target_memory_percent=60.0,
                target_response_time_ms=400.0,
                scale_up_cooldown=300,
                scale_down_cooldown=600,
                health_check_url='/health',
                startup_time_seconds=20
            )
        }
        
        # Reglas de escalado por defecto
        for service_name, config in self.service_configs.items():
            self.scaling_rules[service_name] = [
                ScalingRule(
                    name=f"{service_name}_cpu_rule",
                    service_name=service_name,
                    metric_type="cpu_percent",
                    threshold_up=config.target_cpu_percent,
                    threshold_down=config.target_cpu_percent * 0.6,
                    cooldown_seconds=config.scale_up_cooldown,
                    min_instances=config.min_instances,
                    max_instances=config.max_instances,
                    scale_up_step=1,
                    scale_down_step=1
                ),
                ScalingRule(
                    name=f"{service_name}_memory_rule",
                    service_name=service_name,
                    metric_type="memory_percent",
                    threshold_up=config.target_memory_percent,
                    threshold_down=config.target_memory_percent * 0.7,
                    cooldown_seconds=config.scale_up_cooldown,
                    min_instances=config.min_instances,
                    max_instances=config.max_instances,
                    scale_up_step=1,
                    scale_down_step=1
                )
            ]
        
        # Inicializar instancias actuales
        for service_name in self.service_configs:
            self.current_instances[service_name] = self.service_configs[service_name].min_instances
    
    async def start(self):
        """Inicializar el auto escalador"""
        try:
            self.redis_client = await get_redis_client()
            self.resource_monitor = await get_resource_monitor()
            
            # Cargar estado desde Redis
            await self._load_scaling_state()
            
            logger.info("Auto Scaler iniciado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar Auto Scaler: {e}")
            raise
    
    async def stop(self):
        """Detener el auto escalador"""
        # Guardar estado en Redis
        await self._save_scaling_state()
        
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Auto Scaler detenido")
    
    async def _load_scaling_state(self):
        """Cargar estado de escalado desde Redis"""
        try:
            # Cargar instancias actuales
            instances_data = await self.redis_client.get('autoscaler:instances')
            if instances_data:
                self.current_instances = json.loads(instances_data)
            
            # Cargar historial de escalado
            history_data = await self.redis_client.get('autoscaler:history')
            if history_data:
                history_list = json.loads(history_data)
                self.scaling_history = [
                    ScalingDecision(**item) for item in history_list[-100:]  # Últimos 100
                ]
            
            logger.info(f"Estado de escalado cargado: {len(self.current_instances)} servicios")
        except Exception as e:
            logger.warning(f"Error cargando estado de escalado: {e}")
    
    async def _save_scaling_state(self):
        """Guardar estado de escalado en Redis"""
        try:
            # Guardar instancias actuales
            await self.redis_client.setex(
                'autoscaler:instances',
                3600,  # 1 hora
                json.dumps(self.current_instances)
            )
            
            # Guardar historial
            if self.scaling_history:
                history_list = []
                for decision in self.scaling_history[-50:]:  # Últimos 50
                    decision_dict = asdict(decision)
                    decision_dict['timestamp'] = decision.timestamp.isoformat()
                    decision_dict['action'] = decision.action.value
                    decision_dict['trigger'] = decision.trigger.value
                    history_list.append(decision_dict)
                
                await self.redis_client.setex(
                    'autoscaler:history',
                    3600,
                    json.dumps(history_list)
                )
        except Exception as e:
            logger.warning(f"Error guardando estado de escalado: {e}")
    
    async def evaluate_scaling_decisions(self) -> List[ScalingDecision]:
        """Evaluar todas las decisiones de escalado necesarias"""
        with scaling_decision_duration.labels('full_evaluation').time():
            decisions = []
            
            try:
                # Obtener métricas actuales
                resource_report = await self.resource_monitor.get_resource_report()
                current_metrics = resource_report.get('current_metrics', {})
                predictions = resource_report.get('predictions', {})
                
                # Evaluar cada servicio
                for service_name, config in self.service_configs.items():
                    service_decisions = await self._evaluate_service_scaling(
                        service_name, config, current_metrics, predictions
                    )
                    decisions.extend(service_decisions)
                
                # Aplicar escalado programado si está habilitado
                if self.config['enable_schedule_scaling']:
                    schedule_decisions = await self._evaluate_schedule_scaling()
                    decisions.extend(schedule_decisions)
                
                # Filtrar decisiones conflictivas
                decisions = self._resolve_conflicting_decisions(decisions)
                
                return decisions
                
            except Exception as e:
                logger.error(f"Error evaluando decisiones de escalado: {e}")
                return []
    
    async def _evaluate_service_scaling(
        self,
        service_name: str,
        config: ServiceConfig,
        current_metrics: Dict,
        predictions: Dict
    ) -> List[ScalingDecision]:
        """Evaluar escalado para un servicio específico"""
        decisions = []
        
        try:
            current_instances = self.current_instances.get(service_name, config.min_instances)
            
            # Verificar cooldown
            if await self._is_in_cooldown(service_name):
                return decisions
            
            # Evaluar reglas de escalado
            for rule in self.scaling_rules.get(service_name, []):
                if not rule.enabled:
                    continue
                
                decision = await self._evaluate_scaling_rule(
                    rule, current_instances, current_metrics, predictions
                )
                
                if decision and decision.action != ScalingAction.NO_ACTION:
                    decisions.append(decision)
            
            return decisions
            
        except Exception as e:
            logger.warning(f"Error evaluando escalado para {service_name}: {e}")
            return []
    
    async def _evaluate_scaling_rule(
        self,
        rule: ScalingRule,
        current_instances: int,
        current_metrics: Dict,
        predictions: Dict
    ) -> Optional[ScalingDecision]:
        """Evaluar una regla de escalado específica"""
        try:
            # Obtener valor actual de la métrica
            metric_value = current_metrics.get(rule.metric_type, 0)
            
            # Obtener predicción si está disponible
            prediction_value = None
            if rule.metric_type in predictions:
                pred_data = predictions[rule.metric_type]
                if pred_data.get('confidence', 0) > 0.6:  # Solo predicciones confiables
                    prediction_value = pred_data.get('predicted_value', 0)
            
            # Calcular valor ponderado para decisión
            weighted_value = self._calculate_weighted_value(
                metric_value, prediction_value
            )
            
            # Determinar acción necesaria
            action = ScalingAction.NO_ACTION
            target_instances = current_instances
            threshold = 0
            trigger = ScalingTrigger.CPU_HIGH  # Default
            
            if weighted_value >= rule.threshold_up:
                # Necesario escalar hacia arriba
                if current_instances < rule.max_instances:
                    action = ScalingAction.SCALE_UP
                    target_instances = min(
                        current_instances + rule.scale_up_step,
                        rule.max_instances
                    )
                    threshold = rule.threshold_up
                    trigger = self._get_trigger_from_metric(rule.metric_type)
            
            elif weighted_value <= rule.threshold_down:
                # Posible escalado hacia abajo
                if current_instances > rule.min_instances:
                    action = ScalingAction.SCALE_DOWN
                    target_instances = max(
                        current_instances - rule.scale_down_step,
                        rule.min_instances
                    )
                    threshold = rule.threshold_down
                    trigger = self._get_trigger_from_metric(rule.metric_type)
            
            # Calcular confianza de la decisión
            confidence = self._calculate_decision_confidence(
                metric_value, prediction_value, weighted_value, threshold
            )
            
            if action != ScalingAction.NO_ACTION:
                return ScalingDecision(
                    service_name=rule.service_name,
                    current_instances=current_instances,
                    target_instances=target_instances,
                    action=action,
                    trigger=trigger,
                    metric_value=weighted_value,
                    threshold=threshold,
                    confidence=confidence,
                    reason=f"{rule.metric_type} {action.value}: {weighted_value:.1f} vs {threshold:.1f}",
                    timestamp=datetime.now()
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"Error evaluando regla {rule.name}: {e}")
            return None
    
    def _calculate_weighted_value(
        self,
        current_value: float,
        prediction_value: Optional[float]
    ) -> float:
        """Calcular valor ponderado para decisiones"""
        if prediction_value is None:
            return current_value
        
        # Aplicar pesos configurados
        weighted = (
            current_value * self.config['current_weight'] +
            prediction_value * self.config['prediction_weight']
        )
        
        # Normalizar
        total_weight = self.config['current_weight'] + self.config['prediction_weight']
        return weighted / total_weight
    
    def _get_trigger_from_metric(self, metric_type: str) -> ScalingTrigger:
        """Obtener trigger apropiado según tipo de métrica"""
        trigger_map = {
            'cpu_percent': ScalingTrigger.CPU_HIGH,
            'memory_percent': ScalingTrigger.MEMORY_HIGH,
            'load_average_1m': ScalingTrigger.LOAD_HIGH,
            'response_time': ScalingTrigger.RESPONSE_TIME_HIGH,
            'queue_size': ScalingTrigger.QUEUE_SIZE_HIGH
        }
        return trigger_map.get(metric_type, ScalingTrigger.CPU_HIGH)
    
    def _calculate_decision_confidence(
        self,
        current_value: float,
        prediction_value: Optional[float],
        weighted_value: float,
        threshold: float
    ) -> float:
        """Calcular confianza de la decisión de escalado"""
        try:
            # Distancia del threshold (más lejos = más confianza)
            distance_factor = abs(weighted_value - threshold) / max(threshold, 1)
            distance_confidence = min(1.0, distance_factor)
            
            # Consistencia entre valor actual y predicción
            consistency_confidence = 1.0
            if prediction_value is not None:
                diff = abs(current_value - prediction_value)
                max_diff = max(current_value, prediction_value, 1)
                consistency_confidence = 1.0 - (diff / max_diff)
            
            # Confianza final
            confidence = (distance_confidence * 0.6 + consistency_confidence * 0.4)
            return max(0.1, min(1.0, confidence))
            
        except Exception as e:
            logger.warning(f"Error calculando confianza: {e}")
            return 0.5  # Confianza media por defecto
    
    async def _evaluate_schedule_scaling(self) -> List[ScalingDecision]:
        """Evaluar escalado basado en horarios programados"""
        decisions = []
        
        try:
            current_time = datetime.now().time()
            current_hour_minute = current_time.strftime('%H:%M')
            
            for schedule_name, schedule in self.scaling_schedules.items():
                start_time = schedule['start_time']
                end_time = schedule['end_time']
                scale_factor = schedule['scale_factor']
                
                # Verificar si estamos en el horario programado
                if self._is_time_in_range(current_hour_minute, start_time, end_time):
                    for service_name in schedule['services']:
                        if service_name in self.service_configs:
                            config = self.service_configs[service_name]
                            current_instances = self.current_instances.get(service_name, config.min_instances)
                            
                            # Calcular instancias objetivo basadas en el factor
                            base_instances = (config.min_instances + config.max_instances) // 2
                            target_instances = int(base_instances * scale_factor)
                            target_instances = max(config.min_instances, min(target_instances, config.max_instances))
                            
                            if target_instances != current_instances:
                                action = ScalingAction.SCALE_UP if target_instances > current_instances else ScalingAction.SCALE_DOWN
                                
                                decisions.append(ScalingDecision(
                                    service_name=service_name,
                                    current_instances=current_instances,
                                    target_instances=target_instances,
                                    action=action,
                                    trigger=ScalingTrigger.SCHEDULE_BASED,
                                    metric_value=scale_factor,
                                    threshold=1.0,
                                    confidence=0.8,
                                    reason=f"Escalado programado: {schedule_name}",
                                    timestamp=datetime.now()
                                ))
            
            return decisions
            
        except Exception as e:
            logger.warning(f"Error evaluando escalado programado: {e}")
            return []
    
    def _is_time_in_range(self, current_time: str, start_time: str, end_time: str) -> bool:
        """Verificar si la hora actual está en el rango especificado"""
        try:
            current = datetime.strptime(current_time, '%H:%M').time()
            start = datetime.strptime(start_time, '%H:%M').time()
            end = datetime.strptime(end_time, '%H:%M').time()
            
            if start <= end:
                return start <= current <= end
            else:  # Rango que cruza medianoche
                return current >= start or current <= end
        except Exception:
            return False
    
    def _resolve_conflicting_decisions(self, decisions: List[ScalingDecision]) -> List[ScalingDecision]:
        """Resolver decisiones conflictivas para el mismo servicio"""
        if not decisions:
            return decisions
        
        # Agrupar por servicio
        service_decisions = {}
        for decision in decisions:
            if decision.service_name not in service_decisions:
                service_decisions[decision.service_name] = []
            service_decisions[decision.service_name].append(decision)
        
        # Resolver conflictos por servicio
        resolved_decisions = []
        for service_name, service_decision_list in service_decisions.items():
            if len(service_decision_list) == 1:
                resolved_decisions.append(service_decision_list[0])
            else:
                # Seleccionar decisión con mayor confianza
                best_decision = max(service_decision_list, key=lambda d: d.confidence)
                resolved_decisions.append(best_decision)
        
        return resolved_decisions
    
    async def _is_in_cooldown(self, service_name: str) -> bool:
        """Verificar si un servicio está en cooldown"""
        if service_name not in self.last_scaling_times:
            return False
        
        config = self.service_configs.get(service_name)
        if not config:
            return False
        
        last_scaling = self.last_scaling_times[service_name]
        time_since_scaling = (datetime.now() - last_scaling).total_seconds()
        
        # Usar cooldown más corto como referencia
        cooldown = min(config.scale_up_cooldown, config.scale_down_cooldown)
        
        return time_since_scaling < cooldown
    
    async def execute_scaling_decisions(self, decisions: List[ScalingDecision]) -> List[bool]:
        """Ejecutar decisiones de escalado"""
        results = []
        
        for decision in decisions:
            try:
                success = await self._execute_single_scaling(decision)
                results.append(success)
                
                if success:
                    # Actualizar estado
                    self.current_instances[decision.service_name] = decision.target_instances
                    self.last_scaling_times[decision.service_name] = datetime.now()
                    self.scaling_history.append(decision)
                    
                    # Actualizar métricas
                    scaling_operations_total.labels(
                        decision.action.value,
                        'service',
                        'success' if success else 'failed'
                    ).inc()
                    
                    active_instances_gauge.labels(decision.service_name).set(decision.target_instances)
                    
                    logger.info(
                        f"Escalado ejecutado: {decision.service_name} "
                        f"{decision.current_instances} -> {decision.target_instances} "
                        f"({decision.action.value})"
                    )
                
            except Exception as e:
                logger.error(f"Error ejecutando escalado para {decision.service_name}: {e}")
                results.append(False)
        
        return results
    
    async def _execute_single_scaling(self, decision: ScalingDecision) -> bool:
        """Ejecutar una decisión de escalado individual"""
        try:
            service_name = decision.service_name
            target_instances = decision.target_instances
            
            # En una implementación real, esto interactuaría con Docker, Kubernetes, etc.
            # Por ahora, simulamos la operación
            
            if decision.action == ScalingAction.SCALE_UP:
                # Simular escalado hacia arriba
                logger.info(f"Escalando hacia arriba {service_name} a {target_instances} instancias")
                # Aquí iría: docker-compose scale, kubectl scale, etc.
                
            elif decision.action == ScalingAction.SCALE_DOWN:
                # Simular escalado hacia abajo
                logger.info(f"Escalando hacia abajo {service_name} a {target_instances} instancias")
                # Aquí iría: comandos de reducción de instancias
            
            # Simular tiempo de startup/shutdown
            await asyncio.sleep(1)
            
            return True
            
        except Exception as e:
            logger.error(f"Error en ejecución de escalado: {e}")
            return False
    
    async def get_scaling_status(self) -> Dict:
        """Obtener estado actual del escalado"""
        try:
            # Calcular eficiencia de escalado
            efficiency_metrics = await self._calculate_scaling_efficiency()
            
            # Decisiones recientes
            recent_decisions = [
                {
                    'service': d.service_name,
                    'action': d.action.value,
                    'trigger': d.trigger.value,
                    'instances': f"{d.current_instances} -> {d.target_instances}",
                    'confidence': d.confidence,
                    'reason': d.reason,
                    'timestamp': d.timestamp.isoformat()
                }
                for d in self.scaling_history[-10:]  # Últimas 10
            ]
            
            return {
                'current_instances': self.current_instances.copy(),
                'service_configs': {
                    name: {
                        'tier': config.tier.value,
                        'min_instances': config.min_instances,
                        'max_instances': config.max_instances,
                        'target_cpu': config.target_cpu_percent,
                        'target_memory': config.target_memory_percent
                    }
                    for name, config in self.service_configs.items()
                },
                'scaling_efficiency': efficiency_metrics,
                'recent_decisions': recent_decisions,
                'active_rules_count': sum(
                    len([r for r in rules if r.enabled])
                    for rules in self.scaling_rules.values()
                ),
                'config': self.config,
                'schedules': self.scaling_schedules,
                'decisions_today': len([
                    d for d in self.scaling_history
                    if d.timestamp.date() == datetime.now().date()
                ]),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estado de escalado: {e}")
            return {'error': str(e)}
    
    async def _calculate_scaling_efficiency(self) -> Dict:
        """Calcular métricas de eficiencia del escalado"""
        try:
            if not self.scaling_history:
                return {'overall': 0.0, 'by_trigger': {}}
            
            # Decisiones en las últimas 24 horas
            recent_decisions = [
                d for d in self.scaling_history
                if (datetime.now() - d.timestamp).total_seconds() < 86400
            ]
            
            if not recent_decisions:
                return {'overall': 0.0, 'by_trigger': {}}
            
            # Eficiencia general (basada en confianza promedio)
            total_confidence = sum(d.confidence for d in recent_decisions)
            overall_efficiency = total_confidence / len(recent_decisions)
            
            # Eficiencia por trigger
            trigger_efficiency = {}
            trigger_groups = {}
            
            for decision in recent_decisions:
                trigger = decision.trigger.value
                if trigger not in trigger_groups:
                    trigger_groups[trigger] = []
                trigger_groups[trigger].append(decision.confidence)
            
            for trigger, confidences in trigger_groups.items():
                trigger_efficiency[trigger] = sum(confidences) / len(confidences)
            
            # Actualizar métricas de Prometheus
            scaling_efficiency_gauge.labels('overall').set(overall_efficiency)
            for trigger, efficiency in trigger_efficiency.items():
                scaling_efficiency_gauge.labels(trigger).set(efficiency)
            
            return {
                'overall': overall_efficiency,
                'by_trigger': trigger_efficiency,
                'total_decisions': len(recent_decisions),
                'scale_up_count': len([d for d in recent_decisions if d.action == ScalingAction.SCALE_UP]),
                'scale_down_count': len([d for d in recent_decisions if d.action == ScalingAction.SCALE_DOWN])
            }
            
        except Exception as e:
            logger.warning(f"Error calculando eficiencia de escalado: {e}")
            return {'overall': 0.0, 'by_trigger': {}}
    
    async def update_scaling_rule(
        self,
        service_name: str,
        rule_name: str,
        updates: Dict
    ) -> bool:
        """Actualizar una regla de escalado"""
        try:
            if service_name not in self.scaling_rules:
                return False
            
            for rule in self.scaling_rules[service_name]:
                if rule.name == rule_name:
                    # Actualizar campos especificados
                    for field, value in updates.items():
                        if hasattr(rule, field):
                            setattr(rule, field, value)
                    
                    logger.info(f"Regla de escalado actualizada: {rule_name}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error actualizando regla de escalado: {e}")
            return False
    
    async def continuous_scaling(self):
        """Bucle continuo de evaluación y escalado"""
        logger.info("Iniciando escalado automático continuo")
        
        try:
            while True:
                # Evaluar decisiones de escalado
                decisions = await self.evaluate_scaling_decisions()
                
                # Ejecutar decisiones si las hay
                if decisions:
                    logger.info(f"Ejecutando {len(decisions)} decisiones de escalado")
                    await self.execute_scaling_decisions(decisions)
                
                # Guardar estado periódicamente
                await self._save_scaling_state()
                
                # Esperar próxima evaluación
                await asyncio.sleep(self.config['evaluation_interval'])
                
        except asyncio.CancelledError:
            logger.info("Escalado automático cancelado")
        except Exception as e:
            logger.error(f"Error en escalado continuo: {e}")

# Instancia global del auto escalador
auto_scaler = AutoScaler()

async def get_auto_scaler() -> AutoScaler:
    """Obtener instancia del auto escalador"""
    return auto_scaler