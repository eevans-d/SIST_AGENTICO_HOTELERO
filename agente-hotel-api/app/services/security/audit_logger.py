"""
Sistema de Auditoría de Seguridad con Circuit Breaker
Registra eventos de seguridad importantes con persistencia en PostgreSQL
y fallback a file logging cuando la DB no está disponible.

Características de robustez:
- Circuit breaker para proteger PostgreSQL de sobrecarga
- Retry con exponential backoff en escrituras DB
- Fallback a file logging cuando el circuit está OPEN
- Structured logging en todos los puntos de fallo
- Métricas de Prometheus para observabilidad
"""

import logging
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from sqlalchemy.exc import SQLAlchemyError

from prometheus_client import Counter, Gauge

from app.core.database import AsyncSessionFactory
from app.models.audit_log import AuditLog
from app.core.circuit_breaker import CircuitBreaker, CircuitState
from app.core.constants import (
    MAX_RETRIES_DEFAULT,
    RETRY_DELAY_BASE,
    PMS_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    PMS_CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
)
from app.exceptions.pms_exceptions import CircuitBreakerOpenError

logger = logging.getLogger(__name__)

# Métricas Prometheus para audit logging
audit_events_total = Counter(
    "audit_events_total", "Total audit events logged", ["event_type", "persistence_method", "result"]
)

audit_circuit_breaker_state = Gauge(
    "audit_circuit_breaker_state", "Audit logger circuit breaker state (0=closed, 1=open, 2=half-open)"
)

audit_fallback_writes = Counter("audit_fallback_writes_total", "Total fallback writes to file when DB unavailable")


class AuditEventType(Enum):
    """Tipos de eventos de auditoría"""

    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    ACCESS_DENIED = "access_denied"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ESCALATION = "escalation"
    PMS_ERROR = "pms_error"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"


class AuditLogger:
    """
    Logger especializado para eventos de seguridad con persistencia en DB.

    Este logger está diseñado para production-grade reliability:
    - Circuit breaker protege PostgreSQL de sobrecarga durante fallos
    - Retry con exponential backoff en escrituras a DB
    - Fallback a file logging cuando circuit breaker está OPEN
    - Structured logging en todos los puntos de fallo
    - Métricas de Prometheus para observabilidad

    El circuit breaker se abre después de PMS_CIRCUIT_BREAKER_FAILURE_THRESHOLD
    fallos consecutivos y permanece abierto por PMS_CIRCUIT_BREAKER_RECOVERY_TIMEOUT
    segundos antes de intentar recovery en estado HALF_OPEN.

    Cuando el circuit está OPEN, los eventos se escriben a un archivo de fallback
    en ./logs/audit_fallback.jsonl para prevenir pérdida de datos.

    Atributos:
        circuit_breaker: CircuitBreaker instance para proteger PostgreSQL
        fallback_file: Path al archivo de fallback para eventos durante circuit OPEN
        max_retries: Número máximo de reintentos en escrituras (default: 3)
        retry_delay_base: Delay base para exponential backoff (default: 1s)

    Ejemplo de uso:
        ```python
        audit_logger = AuditLogger()
        await audit_logger.log_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
            user_id="user123",
            ip_address="192.168.1.100",
            resource="/api/reservations",
            details={"method": "POST"},
            tenant_id="hotel_abc"
        )
        ```
    """

    def __init__(
        self,
        fallback_dir: str = "./logs",
        max_retries: int = MAX_RETRIES_DEFAULT,
        retry_delay_base: int = RETRY_DELAY_BASE,
    ):
        """
        Inicializa el audit logger con circuit breaker y fallback.

        Args:
            fallback_dir: Directorio para archivos de fallback (default: "./logs")
            max_retries: Número máximo de reintentos (default: 3)
            retry_delay_base: Delay base para exponential backoff (default: 1s)
        """
        # Circuit breaker para proteger PostgreSQL
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=PMS_CIRCUIT_BREAKER_FAILURE_THRESHOLD,  # 5 fallos
            recovery_timeout=PMS_CIRCUIT_BREAKER_RECOVERY_TIMEOUT,  # 30s
            expected_exception=SQLAlchemyError,  # Errores de DB
        )

        # Fallback file para cuando el circuit está OPEN
        self.fallback_file = Path(fallback_dir) / "audit_fallback.jsonl"
        self.fallback_file.parent.mkdir(parents=True, exist_ok=True)

        # Retry configuration
        self.max_retries = max_retries
        self.retry_delay_base = retry_delay_base

        # Exponer estado del circuit breaker en métrica
        self._update_circuit_breaker_metric()

        logger.info(
            "audit_logger.initialized",
            extra={
                "fallback_file": str(self.fallback_file),
                "failure_threshold": PMS_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                "recovery_timeout": PMS_CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
            },
        )

    def _update_circuit_breaker_metric(self):
        """Actualiza métrica de Prometheus con estado del circuit breaker."""
        state_mapping = {
            CircuitState.CLOSED: 0,
            CircuitState.OPEN: 1,
            CircuitState.HALF_OPEN: 2,
        }
        audit_circuit_breaker_state.set(state_mapping[self.circuit_breaker.state])

    async def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
        severity: str = "info",
    ):
        """
        Registrar evento de auditoría con circuit breaker protection.

        Intenta persistir en PostgreSQL con retry y exponential backoff.
        Si el circuit breaker está OPEN, escribe a archivo de fallback.

        Args:
            event_type: Tipo de evento de auditoría
            user_id: ID del usuario involucrado (opcional)
            ip_address: IP de origen (opcional)
            resource: Recurso accedido/modificado (opcional)
            details: Detalles adicionales en formato dict (opcional)
            tenant_id: ID del tenant/hotel (opcional)
            severity: Severidad del evento ("info", "warning", "critical")

        Returns:
            None (no falla nunca para no romper flujo principal)

        Ejemplo:
            ```python
            await audit_logger.log_event(
                event_type=AuditEventType.LOGIN_SUCCESS,
                user_id="user123",
                ip_address="192.168.1.100",
                resource="/api/auth/login",
                details={"method": "POST", "user_agent": "Mozilla/5.0"},
                tenant_id="hotel_abc",
                severity="info"
            )
            ```
        """
        timestamp = datetime.utcnow()

        # Construir entrada de auditoría
        audit_entry = {
            "timestamp": timestamp.isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "ip_address": ip_address,
            "resource": resource,
            "details": details or {},
            "tenant_id": tenant_id,
            "severity": severity,
        }

        # Log estructurado inmediato (siempre se ejecuta)
        logger.info("security.audit", extra=audit_entry)

        # Intentar persistir en PostgreSQL con circuit breaker
        try:
            # Usar circuit breaker para proteger PostgreSQL
            await self.circuit_breaker.call(
                self._persist_to_db_with_retry,
                timestamp=timestamp,
                event_type=event_type,
                user_id=user_id,
                ip_address=ip_address,
                resource=resource,
                details=details,
                tenant_id=tenant_id,
                severity=severity,
            )

            # Actualizar métrica de éxito
            audit_events_total.labels(
                event_type=event_type.value, persistence_method="database", result="success"
            ).inc()

            # Actualizar métrica de circuit breaker
            self._update_circuit_breaker_metric()

        except CircuitBreakerOpenError:
            # Circuit breaker está OPEN - usar fallback a file
            logger.warning(
                "audit_logger.circuit_open_using_fallback",
                extra={
                    "event_type": event_type.value,
                    "user_id": user_id,
                    "fallback_file": str(self.fallback_file),
                },
            )

            # Escribir a archivo de fallback
            await self._write_to_fallback_file(audit_entry)

            # Métricas
            audit_events_total.labels(
                event_type=event_type.value, persistence_method="fallback_file", result="success"
            ).inc()
            audit_fallback_writes.inc()

            # Actualizar métrica de circuit breaker
            self._update_circuit_breaker_metric()

        except Exception as e:
            # Error inesperado - log pero no fallar
            logger.error(
                "audit_logger.unexpected_error",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "event_type": event_type.value,
                    "user_id": user_id,
                },
                exc_info=True,
            )

            # Métrica de fallo
            audit_events_total.labels(event_type=event_type.value, persistence_method="failed", result="error").inc()

    async def _persist_to_db_with_retry(
        self,
        timestamp: datetime,
        event_type: AuditEventType,
        user_id: Optional[str],
        ip_address: Optional[str],
        resource: Optional[str],
        details: Optional[Dict[str, Any]],
        tenant_id: Optional[str],
        severity: str,
    ) -> bool:
        """
        Persistir evento en PostgreSQL con retry y exponential backoff.

        Este método es llamado por el circuit breaker. Si falla después de
        todos los reintentos, el circuit breaker incrementará su contador
        de fallos y potencialmente abrirá el circuito.

        Args:
            timestamp: Timestamp del evento
            event_type: Tipo de evento
            user_id: ID del usuario (opcional)
            ip_address: IP de origen (opcional)
            resource: Recurso accedido (opcional)
            details: Detalles adicionales (opcional)
            tenant_id: ID del tenant (opcional)
            severity: Severidad del evento

        Returns:
            True si persistió exitosamente

        Raises:
            SQLAlchemyError: Si todos los reintentos fallan
        """
        for attempt in range(self.max_retries):
            try:
                async with AsyncSessionFactory() as session:
                    audit_log = AuditLog(
                        timestamp=timestamp,
                        event_type=event_type.value,
                        user_id=user_id,
                        ip_address=ip_address,
                        resource=resource,
                        details=details,
                        tenant_id=tenant_id,
                        severity=severity,
                    )
                    session.add(audit_log)
                    await session.commit()

                    # Log de éxito (solo en retry)
                    if attempt > 0:
                        logger.info(
                            "audit_logger.db_persist_retry_success",
                            extra={
                                "audit_log_id": audit_log.id,
                                "event_type": event_type.value,
                                "attempt": attempt + 1,
                            },
                        )
                    else:
                        # Primer intento exitoso (log debug)
                        logger.debug(
                            "audit_logger.db_persist_success",
                            extra={
                                "audit_log_id": audit_log.id,
                                "event_type": event_type.value,
                            },
                        )

                    return True

            except SQLAlchemyError as e:
                is_last_attempt = attempt == self.max_retries - 1

                if is_last_attempt:
                    # Último intento falló - log error y re-lanzar
                    logger.error(
                        "audit_logger.db_persist_all_retries_failed",
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "event_type": event_type.value,
                            "user_id": user_id,
                            "total_attempts": self.max_retries,
                        },
                        exc_info=True,
                    )
                    raise
                else:
                    # Calcular delay con exponential backoff
                    delay = self.retry_delay_base * (2**attempt)

                    logger.warning(
                        "audit_logger.db_persist_retry",
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "event_type": event_type.value,
                            "attempt": attempt + 1,
                            "max_attempts": self.max_retries,
                            "retry_delay": delay,
                        },
                    )

                    # Esperar antes del siguiente intento
                    await asyncio.sleep(delay)

        return False

    async def _write_to_fallback_file(self, audit_entry: Dict[str, Any]):
        """
        Escribe evento de auditoría a archivo de fallback en formato JSONL.

        Este método se ejecuta cuando el circuit breaker está OPEN y
        PostgreSQL no está disponible. Los eventos se escriben línea por
        línea en formato JSON para facilitar re-procesamiento posterior.

        Args:
            audit_entry: Diccionario con datos del evento de auditoría
        """
        try:
            with open(self.fallback_file, "a") as f:
                json.dump(audit_entry, f)
                f.write("\n")

            logger.debug(
                "audit_logger.fallback_write_success",
                extra={
                    "event_type": audit_entry.get("event_type"),
                    "file": str(self.fallback_file),
                },
            )

        except IOError as e:
            # Error escribiendo a file - último recurso: log error
            logger.error(
                "audit_logger.fallback_write_failed",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "event_type": audit_entry.get("event_type"),
                    "fallback_file": str(self.fallback_file),
                },
                exc_info=True,
            )

    async def get_audit_logs(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: Optional[int] = None,
    ) -> tuple[list[AuditLog], int]:
        """
        Obtiene logs de auditoría con paginación y filtros opcionales.

        Este método implementa paginación para prevenir OOM (Out of Memory)
        al cargar miles de registros. Soporta filtros múltiples para queries
        específicas.

        Args:
            tenant_id: Filtrar por tenant/hotel específico (opcional)
            user_id: Filtrar por usuario específico (opcional)
            event_type: Filtrar por tipo de evento (opcional)
            start_date: Fecha de inicio del rango (inclusive, opcional)
            end_date: Fecha de fin del rango (inclusive, opcional)
            page: Número de página (1-indexed, default: 1)
            page_size: Registros por página (default: DEFAULT_PAGE_SIZE=20)

        Returns:
            Tuple[List[AuditLog], int]:
                - Lista de audit logs de la página solicitada
                - Total de registros que cumplen los filtros

        Raises:
            ValueError: Si page < 1 o page_size fuera de rango permitido

        Ejemplo:
            ```python
            # Obtener primera página (20 registros)
            logs, total = await audit_logger.get_audit_logs(
                tenant_id="hotel_abc",
                page=1
            )
            print(f"Mostrando {len(logs)} de {total} registros")

            # Obtener logs de login fallidos de un usuario
            logs, total = await audit_logger.get_audit_logs(
                user_id="user123",
                event_type=AuditEventType.LOGIN_FAILED,
                page=1,
                page_size=50
            )

            # Rango de fechas con paginación
            from datetime import datetime, timedelta
            start = datetime.now() - timedelta(days=7)
            end = datetime.now()
            logs, total = await audit_logger.get_audit_logs(
                start_date=start,
                end_date=end,
                page=2,
                page_size=100
            )
            ```

        Performance:
            - Query optimizada con LIMIT/OFFSET
            - Índices recomendados: (tenant_id, timestamp), (user_id, timestamp)
            - Evita cargar todos los registros en memoria
        """
        from sqlalchemy import select, func
        from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, MIN_PAGE_SIZE

        # Validar page
        if page < 1:
            raise ValueError(f"page debe ser >= 1, recibido: {page}")

        # Validar y normalizar page_size
        if page_size is None:
            page_size = DEFAULT_PAGE_SIZE

        if page_size < MIN_PAGE_SIZE:
            raise ValueError(f"page_size debe ser >= {MIN_PAGE_SIZE}, recibido: {page_size}")

        if page_size > MAX_PAGE_SIZE:
            raise ValueError(f"page_size debe ser <= {MAX_PAGE_SIZE}, recibido: {page_size}")

        # Calcular offset
        offset = (page - 1) * page_size

        try:
            async with AsyncSessionFactory() as session:
                # Construir query base con filtros
                query = select(AuditLog)

                if tenant_id:
                    query = query.where(AuditLog.tenant_id == tenant_id)

                if user_id:
                    query = query.where(AuditLog.user_id == user_id)

                if event_type:
                    query = query.where(AuditLog.event_type == event_type.value)

                if start_date:
                    query = query.where(AuditLog.timestamp >= start_date)

                if end_date:
                    query = query.where(AuditLog.timestamp <= end_date)

                # Ordenar por timestamp descendente (más recientes primero)
                query = query.order_by(AuditLog.timestamp.desc())

                # Query para contar total de registros (sin paginación)
                count_query = select(func.count()).select_from(query.subquery())
                total_result = await session.execute(count_query)
                total = total_result.scalar() or 0

                # Aplicar paginación
                query = query.offset(offset).limit(page_size)

                # Ejecutar query paginada
                result = await session.execute(query)
                logs = result.scalars().all()

                logger.info(
                    "audit_logger.get_audit_logs",
                    extra={
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "event_type": event_type.value if event_type else None,
                        "page": page,
                        "page_size": page_size,
                        "total": total,
                        "returned": len(logs),
                    },
                )

                return list(logs), total

        except Exception as e:
            logger.error(
                "audit_logger.get_audit_logs_failed",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "page": page,
                    "page_size": page_size,
                },
                exc_info=True,
            )
            # Devolver lista vacía en caso de error (no romper flujo)
            return [], 0


# Instancia global del audit logger
_audit_logger_instance: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """
    Obtiene la instancia singleton del audit logger.

    Crea la instancia en el primer acceso (lazy initialization).

    Returns:
        AuditLogger instance configurado con circuit breaker y fallback

    Ejemplo:
        ```python
        audit_logger = get_audit_logger()
        await audit_logger.log_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
            user_id="user123"
        )
        ```
    """
    global _audit_logger_instance

    if _audit_logger_instance is None:
        _audit_logger_instance = AuditLogger()

    return _audit_logger_instance


# Backward compatibility: mantener nombre audit_logger como alias
audit_logger = get_audit_logger()
