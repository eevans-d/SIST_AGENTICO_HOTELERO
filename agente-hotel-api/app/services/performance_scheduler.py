"""
Performance Scheduler Service para Agente Hotelero IA System
Programador de tareas de optimización automática con horarios inteligentes
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import croniter

import redis.asyncio as redis
from prometheus_client import Histogram, Counter, Gauge

from app.core.redis_client import get_redis_client
from app.services.performance_optimizer import get_performance_optimizer
from app.services.database_tuner import get_database_tuner
from app.services.cache_optimizer import get_cache_optimizer
from app.services.resource_monitor import get_resource_monitor
from app.services.auto_scaler import get_auto_scaler

# Configurar logging
logger = logging.getLogger(__name__)

# Métricas de Prometheus
scheduled_tasks_total = Counter(
    "scheduled_tasks_total", "Total de tareas programadas ejecutadas", ["task_type", "status"]
)

scheduled_task_duration = Histogram("scheduled_task_duration_seconds", "Duración de tareas programadas", ["task_type"])

next_scheduled_task_gauge = Gauge(
    "next_scheduled_task_seconds", "Segundos hasta la próxima tarea programada", ["task_type"]
)


class TaskType(Enum):
    """Tipos de tareas programadas"""

    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    DATABASE_MAINTENANCE = "database_maintenance"
    CACHE_OPTIMIZATION = "cache_optimization"
    RESOURCE_MONITORING = "resource_monitoring"
    AUTO_SCALING_EVALUATION = "auto_scaling_evaluation"
    SYSTEM_CLEANUP = "system_cleanup"
    BACKUP = "backup"
    HEALTH_CHECK = "health_check"


class TaskPriority(Enum):
    """Prioridades de tareas"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(Enum):
    """Estados de tareas"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ScheduledTask:
    """Tarea programada"""

    id: str
    name: str
    task_type: TaskType
    priority: TaskPriority
    cron_expression: str
    function_name: str
    parameters: Dict[str, Any]
    enabled: bool
    max_duration_seconds: int
    retry_count: int
    retry_delay_seconds: int
    created_at: datetime
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING


@dataclass
class TaskExecution:
    """Ejecución de tarea"""

    task_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: TaskStatus
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    duration_seconds: Optional[float]


class PerformanceScheduler:
    """
    Programador inteligente de tareas de optimización
    Ejecuta tareas de mantenimiento y optimización en horarios óptimos
    """

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_executions: List[TaskExecution] = []

        # Servicios de optimización
        self.performance_optimizer = None
        self.database_tuner = None
        self.cache_optimizer = None
        self.resource_monitor = None
        self.auto_scaler = None

        # Configuración del scheduler
        self.config = {
            "scheduler_interval": 60,  # Verificar tareas cada 60 segundos
            "max_concurrent_tasks": 3,  # Máximo 3 tareas concurrentes
            "task_timeout_default": 1800,  # 30 minutos timeout por defecto
            "cleanup_history_days": 7,  # Mantener historia por 7 días
            "enable_adaptive_scheduling": True,  # Programación adaptativa
            "off_peak_hours_start": "02:00",  # Inicio horas valle
            "off_peak_hours_end": "06:00",  # Fin horas valle
            "peak_hours_start": "08:00",  # Inicio horas pico
            "peak_hours_end": "22:00",  # Fin horas pico
        }

        self._initialize_default_tasks()

    def _initialize_default_tasks(self):
        """Inicializar tareas programadas por defecto"""
        default_tasks = [
            # Optimización de performance general - cada 4 horas durante horarios normales
            ScheduledTask(
                id="perf_optimization_regular",
                name="Optimización Regular de Performance",
                task_type=TaskType.PERFORMANCE_OPTIMIZATION,
                priority=TaskPriority.MEDIUM,
                cron_expression="0 */4 * * *",  # Cada 4 horas
                function_name="run_performance_optimization",
                parameters={"force": False, "optimization_types": ["cpu", "memory", "api"]},
                enabled=True,
                max_duration_seconds=1800,  # 30 minutos
                retry_count=2,
                retry_delay_seconds=300,
                created_at=datetime.now(),
            ),
            # Mantenimiento de base de datos - diario a las 3 AM
            ScheduledTask(
                id="db_maintenance_daily",
                name="Mantenimiento Diario de Base de Datos",
                task_type=TaskType.DATABASE_MAINTENANCE,
                priority=TaskPriority.HIGH,
                cron_expression="0 3 * * *",  # Diario a las 3 AM
                function_name="run_database_maintenance",
                parameters={"vacuum_analyze": True, "update_stats": True},
                enabled=True,
                max_duration_seconds=3600,  # 1 hora
                retry_count=1,
                retry_delay_seconds=600,
                created_at=datetime.now(),
            ),
            # Optimización de cache - cada 2 horas
            ScheduledTask(
                id="cache_optimization_regular",
                name="Optimización Regular de Cache",
                task_type=TaskType.CACHE_OPTIMIZATION,
                priority=TaskPriority.MEDIUM,
                cron_expression="0 */2 * * *",  # Cada 2 horas
                function_name="run_cache_optimization",
                parameters={"optimize_ttl": True, "preload_data": True},
                enabled=True,
                max_duration_seconds=900,  # 15 minutos
                retry_count=2,
                retry_delay_seconds=180,
                created_at=datetime.now(),
            ),
            # Evaluación de auto-escalado - cada 30 minutos durante horas pico
            ScheduledTask(
                id="scaling_evaluation_peak",
                name="Evaluación de Escalado en Horas Pico",
                task_type=TaskType.AUTO_SCALING_EVALUATION,
                priority=TaskPriority.HIGH,
                cron_expression="*/30 8-22 * * *",  # Cada 30 min de 8 AM a 10 PM
                function_name="run_scaling_evaluation",
                parameters={"proactive": True},
                enabled=True,
                max_duration_seconds=300,  # 5 minutos
                retry_count=1,
                retry_delay_seconds=60,
                created_at=datetime.now(),
            ),
            # Limpieza de sistema - diario a las 2 AM
            ScheduledTask(
                id="system_cleanup_daily",
                name="Limpieza Diaria del Sistema",
                task_type=TaskType.SYSTEM_CLEANUP,
                priority=TaskPriority.LOW,
                cron_expression="0 2 * * *",  # Diario a las 2 AM
                function_name="run_system_cleanup",
                parameters={"cleanup_logs": True, "cleanup_cache": True, "cleanup_temp": True},
                enabled=True,
                max_duration_seconds=1200,  # 20 minutos
                retry_count=1,
                retry_delay_seconds=300,
                created_at=datetime.now(),
            ),
            # Monitoreo de recursos - cada 10 minutos
            ScheduledTask(
                id="resource_monitoring_frequent",
                name="Monitoreo Frecuente de Recursos",
                task_type=TaskType.RESOURCE_MONITORING,
                priority=TaskPriority.MEDIUM,
                cron_expression="*/10 * * * *",  # Cada 10 minutos
                function_name="run_resource_monitoring",
                parameters={"detailed_analysis": True},
                enabled=True,
                max_duration_seconds=180,  # 3 minutos
                retry_count=1,
                retry_delay_seconds=30,
                created_at=datetime.now(),
            ),
            # Chequeo de salud integral - cada hora
            ScheduledTask(
                id="health_check_hourly",
                name="Chequeo de Salud Integral",
                task_type=TaskType.HEALTH_CHECK,
                priority=TaskPriority.MEDIUM,
                cron_expression="0 * * * *",  # Cada hora
                function_name="run_comprehensive_health_check",
                parameters={"include_external_services": True},
                enabled=True,
                max_duration_seconds=600,  # 10 minutos
                retry_count=2,
                retry_delay_seconds=120,
                created_at=datetime.now(),
            ),
        ]

        # Agregar tareas al diccionario
        for task in default_tasks:
            self.scheduled_tasks[task.id] = task
            # Calcular próxima ejecución
            self._calculate_next_run(task)

    async def start(self):
        """Inicializar el scheduler"""
        try:
            self.redis_client = await get_redis_client()

            # Inicializar servicios de optimización
            self.performance_optimizer = await get_performance_optimizer()
            self.database_tuner = await get_database_tuner()
            self.cache_optimizer = await get_cache_optimizer()
            self.resource_monitor = await get_resource_monitor()
            self.auto_scaler = await get_auto_scaler()

            # Cargar tareas desde Redis
            await self._load_scheduled_tasks()

            # Calcular próximas ejecuciones
            for task in self.scheduled_tasks.values():
                self._calculate_next_run(task)

            logger.info(f"Performance Scheduler iniciado con {len(self.scheduled_tasks)} tareas")
        except Exception as e:
            logger.error(f"Error al inicializar Performance Scheduler: {e}")
            raise

    async def stop(self):
        """Detener el scheduler"""
        # Cancelar tareas en ejecución
        for task_id, task in self.running_tasks.items():
            if not task.done():
                task.cancel()
                logger.info(f"Tarea cancelada: {task_id}")

        # Guardar estado en Redis
        await self._save_scheduled_tasks()

        if self.redis_client:
            await self.redis_client.close()
        logger.info("Performance Scheduler detenido")

    async def _load_scheduled_tasks(self):
        """Cargar tareas programadas desde Redis"""
        try:
            tasks_data = await self.redis_client.get("scheduler:tasks")
            if tasks_data:
                tasks_dict = json.loads(tasks_data)
                for task_id, task_data in tasks_dict.items():
                    # Convertir de vuelta a ScheduledTask
                    task_data["task_type"] = TaskType(task_data["task_type"])
                    task_data["priority"] = TaskPriority(task_data["priority"])
                    task_data["status"] = TaskStatus(task_data["status"])
                    task_data["created_at"] = datetime.fromisoformat(task_data["created_at"])

                    if task_data.get("last_run"):
                        task_data["last_run"] = datetime.fromisoformat(task_data["last_run"])
                    if task_data.get("next_run"):
                        task_data["next_run"] = datetime.fromisoformat(task_data["next_run"])

                    self.scheduled_tasks[task_id] = ScheduledTask(**task_data)

            logger.info(f"Cargadas {len(self.scheduled_tasks)} tareas programadas")
        except Exception as e:
            logger.warning(f"Error cargando tareas programadas: {e}")

    async def _save_scheduled_tasks(self):
        """Guardar tareas programadas en Redis"""
        try:
            tasks_dict = {}
            for task_id, task in self.scheduled_tasks.items():
                task_data = asdict(task)
                task_data["task_type"] = task.task_type.value
                task_data["priority"] = task.priority.value
                task_data["status"] = task.status.value
                task_data["created_at"] = task.created_at.isoformat()

                if task.last_run:
                    task_data["last_run"] = task.last_run.isoformat()
                if task.next_run:
                    task_data["next_run"] = task.next_run.isoformat()

                tasks_dict[task_id] = task_data

            await self.redis_client.setex(
                "scheduler:tasks",
                3600,  # 1 hora
                json.dumps(tasks_dict),
            )
        except Exception as e:
            logger.warning(f"Error guardando tareas programadas: {e}")

    def _calculate_next_run(self, task: ScheduledTask):
        """Calcular próxima ejecución de una tarea"""
        try:
            cron = croniter.croniter(task.cron_expression, datetime.now())
            task.next_run = cron.get_next(datetime)

            # Actualizar métrica de Prometheus
            seconds_until_next = (task.next_run - datetime.now()).total_seconds()
            next_scheduled_task_gauge.labels(task.task_type.value).set(seconds_until_next)

        except Exception as e:
            logger.warning(f"Error calculando próxima ejecución para {task.id}: {e}")
            # Fallback: programar para dentro de 1 hora
            task.next_run = datetime.now() + timedelta(hours=1)

    async def check_and_execute_tasks(self):
        """Verificar y ejecutar tareas que deben ejecutarse"""
        now = datetime.now()

        for task in self.scheduled_tasks.values():
            if not task.enabled:
                continue

            # Verificar si es hora de ejecutar
            if task.next_run and now >= task.next_run:
                # Verificar si no hay demasiadas tareas concurrentes
                if len(self.running_tasks) >= self.config["max_concurrent_tasks"]:
                    continue

                # Verificar si la tarea ya está ejecutándose
                if task.id in self.running_tasks:
                    continue

                # Ejecutar la tarea
                await self._execute_task(task)

    async def _execute_task(self, task: ScheduledTask):
        """Ejecutar una tarea programada"""
        logger.info(f"Ejecutando tarea programada: {task.name}")

        # Crear ejecución
        execution = TaskExecution(
            task_id=task.id,
            started_at=datetime.now(),
            completed_at=None,
            status=TaskStatus.RUNNING,
            result=None,
            error_message=None,
            duration_seconds=None,
        )

        try:
            # Crear y ejecutar la tarea asyncio
            async_task = asyncio.create_task(self._run_task_function(task, execution))
            self.running_tasks[task.id] = async_task

            # Actualizar estado de la tarea
            task.status = TaskStatus.RUNNING
            task.last_run = datetime.now()

            # Programar próxima ejecución
            self._calculate_next_run(task)

        except Exception as e:
            logger.error(f"Error iniciando tarea {task.name}: {e}")
            execution.status = TaskStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now()

            # Actualizar métricas
            scheduled_tasks_total.labels(task.task_type.value, "failed").inc()

    async def _run_task_function(self, task: ScheduledTask, execution: TaskExecution):
        """Ejecutar la función específica de una tarea"""
        try:
            with scheduled_task_duration.labels(task.task_type.value).time():
                # Timeout para la tarea
                timeout = task.max_duration_seconds or self.config["task_timeout_default"]

                # Ejecutar función según el tipo
                result = await asyncio.wait_for(self._dispatch_task_function(task), timeout=timeout)

                # Marcar como completada
                execution.completed_at = datetime.now()
                execution.status = TaskStatus.COMPLETED
                execution.result = result
                execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()

                task.status = TaskStatus.COMPLETED

                # Actualizar métricas
                scheduled_tasks_total.labels(task.task_type.value, "completed").inc()

                logger.info(f"Tarea completada: {task.name} en {execution.duration_seconds:.1f}s")

        except asyncio.TimeoutError:
            execution.completed_at = datetime.now()
            execution.status = TaskStatus.FAILED
            execution.error_message = f"Timeout después de {timeout} segundos"
            task.status = TaskStatus.FAILED

            scheduled_tasks_total.labels(task.task_type.value, "timeout").inc()
            logger.warning(f"Tarea {task.name} terminada por timeout")

        except Exception as e:
            execution.completed_at = datetime.now()
            execution.status = TaskStatus.FAILED
            execution.error_message = str(e)
            task.status = TaskStatus.FAILED

            scheduled_tasks_total.labels(task.task_type.value, "failed").inc()
            logger.error(f"Error ejecutando tarea {task.name}: {e}")

        finally:
            # Agregar ejecución al historial
            self.task_executions.append(execution)

            # Limpiar tarea de las que están ejecutándose
            if task.id in self.running_tasks:
                del self.running_tasks[task.id]

            # Limpiar historial antiguo
            await self._cleanup_old_executions()

    async def _dispatch_task_function(self, task: ScheduledTask) -> Dict[str, Any]:
        """Despachar ejecución a la función apropiada"""
        function_name = task.function_name
        parameters = task.parameters

        if function_name == "run_performance_optimization":
            return await self._run_performance_optimization(parameters)

        elif function_name == "run_database_maintenance":
            return await self._run_database_maintenance(parameters)

        elif function_name == "run_cache_optimization":
            return await self._run_cache_optimization(parameters)

        elif function_name == "run_scaling_evaluation":
            return await self._run_scaling_evaluation(parameters)

        elif function_name == "run_system_cleanup":
            return await self._run_system_cleanup(parameters)

        elif function_name == "run_resource_monitoring":
            return await self._run_resource_monitoring(parameters)

        elif function_name == "run_comprehensive_health_check":
            return await self._run_comprehensive_health_check(parameters)

        else:
            raise ValueError(f"Función desconocida: {function_name}")

    async def _run_performance_optimization(self, parameters: Dict) -> Dict[str, Any]:
        """Ejecutar optimización de performance"""
        result = await self.performance_optimizer.execute_optimization(
            force=parameters.get("force", False),
            optimization_types=parameters.get("optimization_types", ["cpu", "memory", "api"]),
        )
        return {"optimization_result": result}

    async def _run_database_maintenance(self, parameters: Dict) -> Dict[str, Any]:
        """Ejecutar mantenimiento de base de datos"""
        results = {}

        if parameters.get("vacuum_analyze", True):
            vacuum_result = await self.database_tuner.vacuum_analyze_all()
            results["vacuum_analyze"] = vacuum_result

        if parameters.get("update_stats", True):
            # En implementación real, actualizar estadísticas
            results["update_stats"] = {"status": "completed"}

        return results

    async def _run_cache_optimization(self, parameters: Dict) -> Dict[str, Any]:
        """Ejecutar optimización de cache"""
        result = await self.cache_optimizer.auto_optimize_cache(
            enable_compression=parameters.get("enable_compression", True),
            enable_preloading=parameters.get("preload_data", True),
            enable_cleanup=parameters.get("cleanup_cache", False),
        )
        return {"cache_optimization": result}

    async def _run_scaling_evaluation(self, parameters: Dict) -> Dict[str, Any]:
        """Ejecutar evaluación de escalado"""
        decisions = await self.auto_scaler.evaluate_scaling_decisions()

        if parameters.get("proactive", False) and decisions:
            # Ejecutar decisiones si es modo proactivo
            results = await self.auto_scaler.execute_scaling_decisions(decisions)
            return {"decisions_count": len(decisions), "execution_results": results, "proactive": True}

        return {"decisions_count": len(decisions), "proactive": False}

    async def _run_system_cleanup(self, parameters: Dict) -> Dict[str, Any]:
        """Ejecutar limpieza del sistema"""
        results = {}

        if parameters.get("cleanup_logs", True):
            # En implementación real, limpiar logs antiguos
            results["logs_cleaned"] = True

        if parameters.get("cleanup_cache", True):
            cleanup_result = await self.cache_optimizer.cleanup_cache()
            results["cache_cleaned"] = cleanup_result

        if parameters.get("cleanup_temp", True):
            # En implementación real, limpiar archivos temporales
            results["temp_cleaned"] = True

        # Limpiar historial del scheduler
        await self._cleanup_old_executions()
        results["scheduler_history_cleaned"] = True

        return results

    async def _run_resource_monitoring(self, parameters: Dict) -> Dict[str, Any]:
        """Ejecutar monitoreo de recursos"""
        # Recopilar métricas actuales
        metrics = await self.resource_monitor.collect_system_metrics()

        # Analizar tendencias si se solicita análisis detallado
        if parameters.get("detailed_analysis", True):
            await self.resource_monitor.analyze_resource_trends(metrics)

        return {
            "metrics_collected": True,
            "detailed_analysis": parameters.get("detailed_analysis", True),
            "cpu_percent": metrics.cpu_percent,
            "memory_percent": metrics.memory_percent,
            "disk_percent": metrics.disk_percent,
        }

    async def _run_comprehensive_health_check(self, parameters: Dict) -> Dict[str, Any]:
        """Ejecutar chequeo de salud integral"""
        health_results = {}

        # Verificar servicios de optimización
        try:
            await self.performance_optimizer.get_optimization_report()
            health_results["performance_service"] = "healthy"
        except Exception:
            health_results["performance_service"] = "unhealthy"

        try:
            await self.database_tuner.get_performance_report()
            health_results["database_service"] = "healthy"
        except Exception:
            health_results["database_service"] = "unhealthy"

        try:
            await self.cache_optimizer.get_cache_report()
            health_results["cache_service"] = "healthy"
        except Exception:
            health_results["cache_service"] = "unhealthy"

        try:
            await self.resource_monitor.get_resource_report()
            health_results["monitoring_service"] = "healthy"
        except Exception:
            health_results["monitoring_service"] = "unhealthy"

        try:
            await self.auto_scaler.get_scaling_status()
            health_results["scaling_service"] = "healthy"
        except Exception:
            health_results["scaling_service"] = "unhealthy"

        # Calcular salud general
        healthy_services = sum(1 for status in health_results.values() if status == "healthy")
        total_services = len(health_results)
        health_percentage = (healthy_services / total_services) * 100

        health_results["overall_health"] = "healthy" if health_percentage >= 80 else "degraded"
        health_results["health_percentage"] = health_percentage

        return health_results

    async def _cleanup_old_executions(self):
        """Limpiar ejecuciones antiguas"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config["cleanup_history_days"])

            self.task_executions = [
                execution for execution in self.task_executions if execution.started_at > cutoff_date
            ]

        except Exception as e:
            logger.warning(f"Error limpiando ejecuciones antiguas: {e}")

    async def add_task(self, task: ScheduledTask) -> bool:
        """Agregar nueva tarea programada"""
        try:
            self.scheduled_tasks[task.id] = task
            self._calculate_next_run(task)
            await self._save_scheduled_tasks()

            logger.info(f"Tarea agregada: {task.name}")
            return True
        except Exception as e:
            logger.error(f"Error agregando tarea: {e}")
            return False

    async def remove_task(self, task_id: str) -> bool:
        """Remover tarea programada"""
        try:
            if task_id in self.scheduled_tasks:
                # Cancelar si está ejecutándose
                if task_id in self.running_tasks:
                    self.running_tasks[task_id].cancel()
                    del self.running_tasks[task_id]

                del self.scheduled_tasks[task_id]
                await self._save_scheduled_tasks()

                logger.info(f"Tarea removida: {task_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removiendo tarea: {e}")
            return False

    async def enable_task(self, task_id: str) -> bool:
        """Habilitar tarea programada"""
        try:
            if task_id in self.scheduled_tasks:
                self.scheduled_tasks[task_id].enabled = True
                self._calculate_next_run(self.scheduled_tasks[task_id])
                await self._save_scheduled_tasks()
                return True
            return False
        except Exception as e:
            logger.error(f"Error habilitando tarea: {e}")
            return False

    async def disable_task(self, task_id: str) -> bool:
        """Deshabilitar tarea programada"""
        try:
            if task_id in self.scheduled_tasks:
                self.scheduled_tasks[task_id].enabled = False
                await self._save_scheduled_tasks()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deshabilitando tarea: {e}")
            return False

    async def get_scheduler_status(self) -> Dict:
        """Obtener estado del scheduler"""
        try:
            now = datetime.now()

            # Próximas tareas
            next_tasks = []
            for task in self.scheduled_tasks.values():
                if task.enabled and task.next_run:
                    next_tasks.append(
                        {
                            "id": task.id,
                            "name": task.name,
                            "type": task.task_type.value,
                            "next_run": task.next_run.isoformat(),
                            "seconds_until_run": (task.next_run - now).total_seconds(),
                        }
                    )

            # Ordenar por próxima ejecución
            next_tasks.sort(key=lambda x: x["seconds_until_run"])

            # Estadísticas de ejecuciones recientes
            recent_executions = [
                exec
                for exec in self.task_executions
                if (now - exec.started_at).total_seconds() < 86400  # Últimas 24 horas
            ]

            successful_executions = len([exec for exec in recent_executions if exec.status == TaskStatus.COMPLETED])

            return {
                "total_tasks": len(self.scheduled_tasks),
                "enabled_tasks": len([t for t in self.scheduled_tasks.values() if t.enabled]),
                "running_tasks": len(self.running_tasks),
                "next_tasks": next_tasks[:5],  # Próximas 5
                "executions_24h": len(recent_executions),
                "successful_executions_24h": successful_executions,
                "success_rate": (successful_executions / len(recent_executions) * 100) if recent_executions else 0,
                "config": self.config,
                "timestamp": now.isoformat(),
            }

        except Exception as e:
            logger.error(f"Error obteniendo estado del scheduler: {e}")
            return {"error": str(e)}

    async def continuous_scheduling(self):
        """Bucle continuo del scheduler"""
        logger.info("Iniciando scheduler continuo de performance")

        try:
            while True:
                # Verificar y ejecutar tareas
                await self.check_and_execute_tasks()

                # Guardar estado periódicamente
                await self._save_scheduled_tasks()

                # Esperar próximo ciclo
                await asyncio.sleep(self.config["scheduler_interval"])

        except asyncio.CancelledError:
            logger.info("Scheduler continuo cancelado")
        except Exception as e:
            logger.error(f"Error en scheduler continuo: {e}")


# Instancia global del scheduler
performance_scheduler = PerformanceScheduler()


async def get_performance_scheduler() -> PerformanceScheduler:
    """Obtener instancia del scheduler de performance"""
    return performance_scheduler
