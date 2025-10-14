"""
Health checks específicos para el sistema de audio optimizado.
Monitorea el estado de todas las optimizaciones y servicios de audio.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from enum import Enum

from ..core.logging import logger
from ..services.audio_processor import OptimizedAudioProcessor


class HealthStatus(Enum):
    """Estados de salud de los componentes."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ComponentHealth:
    """Información de salud de un componente."""

    def __init__(
        self,
        name: str,
        status: HealthStatus = HealthStatus.UNKNOWN,
        details: Optional[Dict[str, Any]] = None,
        last_check: Optional[float] = None,
    ):
        self.name = name
        self.status = status
        self.details = details or {}
        self.last_check = last_check or time.time()
        self.check_duration: Optional[float] = None


class AudioSystemHealthChecker:
    """
    Verificador de salud integral para el sistema de audio optimizado.
    Monitorea todos los componentes de optimización y reporta el estado general.
    """

    def __init__(
        self, audio_processor: OptimizedAudioProcessor, check_interval: int = 60, timeout_seconds: float = 30.0
    ):
        self.audio_processor = audio_processor
        self.check_interval = check_interval
        self.timeout_seconds = timeout_seconds

        # Estado de componentes
        self.component_health: Dict[str, ComponentHealth] = {}
        self.overall_status = HealthStatus.UNKNOWN
        self.last_full_check: Optional[float] = None

        # Task de monitoreo
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False

    async def start_monitoring(self):
        """Inicia el monitoreo continuo de salud."""
        if self._running:
            return

        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("AudioSystemHealthChecker iniciado")

    async def stop_monitoring(self):
        """Detiene el monitoreo de salud."""
        if not self._running:
            return

        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("AudioSystemHealthChecker detenido")

    async def perform_full_health_check(self) -> Dict[str, Any]:
        """
        Realiza una verificación completa de salud del sistema de audio.
        """
        start_time = time.time()
        logger.info("Iniciando verificación completa de salud del sistema de audio")

        # Verificar cada componente
        checks = [
            self._check_cache_optimizer(),
            self._check_compression_optimizer(),
            self._check_connection_manager(),
            self._check_audio_processor_core(),
            self._check_stt_service(),
            self._check_tts_service(),
            self._check_system_resources(),
        ]

        try:
            # Ejecutar verificaciones con timeout
            results = await asyncio.wait_for(
                asyncio.gather(*checks, return_exceptions=True), timeout=self.timeout_seconds
            )

            # Procesar resultados
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    component_name = checks[i].__name__.replace("_check_", "")
                    self.component_health[component_name] = ComponentHealth(
                        name=component_name, status=HealthStatus.CRITICAL, details={"error": str(result)}
                    )

        except asyncio.TimeoutError:
            logger.error(f"Health check timeout después de {self.timeout_seconds}s")
            return {
                "status": HealthStatus.CRITICAL.value,
                "error": "Health check timeout",
                "duration": time.time() - start_time,
            }

        # Calcular estado general
        self._calculate_overall_status()
        self.last_full_check = time.time()

        total_duration = time.time() - start_time

        result = {
            "status": self.overall_status.value,
            "components": {
                name: {
                    "status": health.status.value,
                    "details": health.details,
                    "last_check": health.last_check,
                    "check_duration": health.check_duration,
                }
                for name, health in self.component_health.items()
            },
            "summary": self._generate_health_summary(),
            "duration": total_duration,
            "timestamp": time.time(),
        }

        logger.info(f"Health check completado en {total_duration:.3f}s - Estado: {self.overall_status.value}")
        return result

    async def _check_cache_optimizer(self) -> ComponentHealth:
        """Verifica la salud del optimizador de caché."""
        component_name = "cache_optimizer"
        start_time = time.time()

        try:
            if not self.audio_processor.cache_optimizer:
                return self._create_component_health(
                    component_name, HealthStatus.UNKNOWN, {"message": "Cache optimizer not enabled"}, start_time
                )

            # Verificar estadísticas del caché
            stats = await self.audio_processor.cache_optimizer.get_stats()

            # Evaluar salud basada en métricas
            memory_utilization = stats.get("memory_utilization", 0)
            hit_ratio = stats.get("cache_hit_ratio", 0)

            if memory_utilization > 0.95:
                status = HealthStatus.CRITICAL
                details = {"issue": "Memory utilization too high", "utilization": memory_utilization}
            elif hit_ratio < 0.3 and stats["global_stats"]["hits"] + stats["global_stats"]["misses"] > 100:
                status = HealthStatus.DEGRADED
                details = {"issue": "Low cache hit ratio", "hit_ratio": hit_ratio}
            else:
                status = HealthStatus.HEALTHY
                details = {
                    "memory_utilization": memory_utilization,
                    "hit_ratio": hit_ratio,
                    "cache_size": stats.get("memory_cache_size", 0),
                }

            return self._create_component_health(component_name, status, details, start_time)

        except Exception as e:
            return self._create_component_health(component_name, HealthStatus.CRITICAL, {"error": str(e)}, start_time)

    async def _check_compression_optimizer(self) -> ComponentHealth:
        """Verifica la salud del optimizador de compresión."""
        component_name = "compression_optimizer"
        start_time = time.time()

        try:
            if not self.audio_processor.compression_optimizer:
                return self._create_component_health(
                    component_name, HealthStatus.UNKNOWN, {"message": "Compression optimizer not enabled"}, start_time
                )

            # Verificar estadísticas de compresión
            stats = await self.audio_processor.compression_optimizer.get_compression_stats()

            status = HealthStatus.HEALTHY
            details = {
                "supported_formats": len(stats.get("supported_formats", [])),
                "compression_levels": len(stats.get("compression_levels", [])),
                "cache_size": stats.get("cache_size", 0),
            }

            return self._create_component_health(component_name, status, details, start_time)

        except Exception as e:
            return self._create_component_health(component_name, HealthStatus.CRITICAL, {"error": str(e)}, start_time)

    async def _check_connection_manager(self) -> ComponentHealth:
        """Verifica la salud del gestor de conexiones."""
        component_name = "connection_manager"
        start_time = time.time()

        try:
            if not self.audio_processor.connection_manager:
                return self._create_component_health(
                    component_name, HealthStatus.UNKNOWN, {"message": "Connection manager not enabled"}, start_time
                )

            # Verificar métricas de conexiones
            metrics = await self.audio_processor.connection_manager.get_all_metrics()

            # Evaluar salud de cada pool
            degraded_pools = 0
            critical_pools = 0

            for pool_name, pool_metrics in metrics.get("pools", {}).items():
                pool_status = pool_metrics.get("status", "unknown")
                if pool_status == "degraded":
                    degraded_pools += 1
                elif pool_status == "critical":
                    critical_pools += 1

            total_pools = metrics.get("total_pools", 0)

            if critical_pools > 0:
                status = HealthStatus.CRITICAL
            elif degraded_pools > 0:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY

            details = {
                "total_pools": total_pools,
                "degraded_pools": degraded_pools,
                "critical_pools": critical_pools,
                "pool_details": metrics.get("pools", {}),
            }

            return self._create_component_health(component_name, status, details, start_time)

        except Exception as e:
            return self._create_component_health(component_name, HealthStatus.CRITICAL, {"error": str(e)}, start_time)

    async def _check_audio_processor_core(self) -> ComponentHealth:
        """Verifica la salud del procesador de audio principal."""
        component_name = "audio_processor_core"
        start_time = time.time()

        try:
            # Verificar que el procesador esté iniciado
            if not self.audio_processor._started:
                return self._create_component_health(
                    component_name, HealthStatus.CRITICAL, {"error": "Audio processor not started"}, start_time
                )

            # Verificar componentes internos
            issues = []

            if not hasattr(self.audio_processor, "stt") or not self.audio_processor.stt:
                issues.append("STT service not initialized")

            if not hasattr(self.audio_processor, "tts") or not self.audio_processor.tts:
                issues.append("TTS service not initialized")

            if not hasattr(self.audio_processor, "cache") or not self.audio_processor.cache:
                issues.append("Cache service not initialized")

            if issues:
                status = HealthStatus.DEGRADED
                details = {"issues": issues}
            else:
                status = HealthStatus.HEALTHY
                details = {"message": "All core components initialized"}

            return self._create_component_health(component_name, status, details, start_time)

        except Exception as e:
            return self._create_component_health(component_name, HealthStatus.CRITICAL, {"error": str(e)}, start_time)

    async def _check_stt_service(self) -> ComponentHealth:
        """Verifica la salud del servicio STT."""
        component_name = "stt_service"
        start_time = time.time()

        try:
            # Verificar que el modelo STT esté disponible
            if hasattr(self.audio_processor.stt, "_model_loaded"):
                if self.audio_processor.stt._model_loaded == "mock":
                    status = HealthStatus.DEGRADED
                    details = {"message": "Using mock STT (Whisper not available)"}
                elif self.audio_processor.stt._model_loaded:
                    status = HealthStatus.HEALTHY
                    details = {"message": "STT model loaded successfully"}
                else:
                    status = HealthStatus.UNKNOWN
                    details = {"message": "STT model not yet loaded"}
            else:
                status = HealthStatus.UNKNOWN
                details = {"message": "STT status unknown"}

            return self._create_component_health(component_name, status, details, start_time)

        except Exception as e:
            return self._create_component_health(component_name, HealthStatus.CRITICAL, {"error": str(e)}, start_time)

    async def _check_tts_service(self) -> ComponentHealth:
        """Verifica la salud del servicio TTS."""
        component_name = "tts_service"
        start_time = time.time()

        try:
            # Verificar disponibilidad de herramientas TTS
            import shutil

            espeak_available = shutil.which("espeak") is not None
            ffmpeg_available = shutil.which("ffmpeg") is not None

            if not espeak_available or not ffmpeg_available:
                status = HealthStatus.CRITICAL
                details = {
                    "error": "Required TTS tools not available",
                    "espeak_available": espeak_available,
                    "ffmpeg_available": ffmpeg_available,
                }
            else:
                status = HealthStatus.HEALTHY
                details = {
                    "message": "TTS tools available",
                    "espeak_available": espeak_available,
                    "ffmpeg_available": ffmpeg_available,
                }

            return self._create_component_health(component_name, status, details, start_time)

        except Exception as e:
            return self._create_component_health(component_name, HealthStatus.CRITICAL, {"error": str(e)}, start_time)

    async def _check_system_resources(self) -> ComponentHealth:
        """Verifica los recursos del sistema."""
        component_name = "system_resources"
        start_time = time.time()

        try:
            import psutil

            # Verificar uso de memoria
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            cpu_percent = psutil.cpu_percent(interval=0.1)

            issues = []

            if memory.percent > 90:
                issues.append(f"High memory usage: {memory.percent:.1f}%")

            if disk.percent > 95:
                issues.append(f"High disk usage: {disk.percent:.1f}%")

            if cpu_percent > 90:
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")

            if issues:
                status = HealthStatus.DEGRADED if len(issues) < 2 else HealthStatus.CRITICAL
            else:
                status = HealthStatus.HEALTHY

            details = {
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "cpu_percent": cpu_percent,
                "issues": issues,
            }

            return self._create_component_health(component_name, status, details, start_time)

        except ImportError:
            return self._create_component_health(
                component_name,
                HealthStatus.UNKNOWN,
                {"message": "psutil not available for system monitoring"},
                start_time,
            )
        except Exception as e:
            return self._create_component_health(component_name, HealthStatus.CRITICAL, {"error": str(e)}, start_time)

    def _create_component_health(
        self, name: str, status: HealthStatus, details: Dict[str, Any], start_time: float
    ) -> ComponentHealth:
        """Crea un objeto ComponentHealth y lo almacena."""
        health = ComponentHealth(name=name, status=status, details=details, last_check=time.time())
        health.check_duration = time.time() - start_time

        self.component_health[name] = health
        return health

    def _calculate_overall_status(self):
        """Calcula el estado general basado en los componentes."""
        if not self.component_health:
            self.overall_status = HealthStatus.UNKNOWN
            return

        statuses = [health.status for health in self.component_health.values()]

        if HealthStatus.CRITICAL in statuses:
            self.overall_status = HealthStatus.CRITICAL
        elif HealthStatus.DEGRADED in statuses:
            self.overall_status = HealthStatus.DEGRADED
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            self.overall_status = HealthStatus.HEALTHY
        else:
            self.overall_status = HealthStatus.DEGRADED

    def _generate_health_summary(self) -> Dict[str, Any]:
        """Genera un resumen del estado de salud."""
        status_counts = {}
        for status in HealthStatus:
            status_counts[status.value] = sum(1 for health in self.component_health.values() if health.status == status)

        total_components = len(self.component_health)
        healthy_ratio = status_counts.get("healthy", 0) / total_components if total_components > 0 else 0

        return {
            "total_components": total_components,
            "status_counts": status_counts,
            "healthy_ratio": healthy_ratio,
            "recommendations": self._generate_recommendations(),
        }

    def _generate_recommendations(self) -> List[str]:
        """Genera recomendaciones basadas en el estado actual."""
        recommendations = []

        for name, health in self.component_health.items():
            if health.status == HealthStatus.CRITICAL:
                if "error" in health.details:
                    recommendations.append(f"Investigate critical error in {name}: {health.details['error']}")
                else:
                    recommendations.append(f"Address critical issues in {name}")

            elif health.status == HealthStatus.DEGRADED:
                if "issues" in health.details:
                    recommendations.append(f"Optimize {name}: {', '.join(health.details['issues'])}")
                else:
                    recommendations.append(f"Monitor and optimize {name}")

        # Recomendaciones generales
        status_counts = {}
        for health in self.component_health.values():
            status_counts[health.status] = status_counts.get(health.status, 0) + 1

        if status_counts.get(HealthStatus.CRITICAL, 0) > 1:
            recommendations.append("Multiple critical components detected - consider system restart")

        if status_counts.get(HealthStatus.DEGRADED, 0) > 2:
            recommendations.append("Multiple degraded components - review system load and resources")

        return recommendations

    async def _monitoring_loop(self):
        """Bucle de monitoreo continuo."""
        while self._running:
            try:
                await asyncio.sleep(self.check_interval)
                await self.perform_full_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error en monitoreo de salud: {e}")

    async def get_quick_status(self) -> Dict[str, Any]:
        """Obtiene un estado rápido sin verificación completa."""
        return {
            "status": self.overall_status.value,
            "last_check": self.last_full_check,
            "component_count": len(self.component_health),
            "healthy_components": sum(
                1 for health in self.component_health.values() if health.status == HealthStatus.HEALTHY
            ),
        }
