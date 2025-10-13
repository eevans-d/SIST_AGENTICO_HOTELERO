"""
Sistema de Auditoría de Seguridad
Registra eventos de seguridad importantes con persistencia en PostgreSQL
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionFactory
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

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
    """Logger especializado para eventos de seguridad con persistencia en DB"""
    
    @staticmethod
    async def log_event(
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
        severity: str = "info"
    ):
        """
        Registrar evento de auditoría en logs y base de datos
        
        Args:
            event_type: Tipo de evento
            user_id: ID del usuario involucrado
            ip_address: IP de origen
            resource: Recurso accedido/modificado
            details: Detalles adicionales
            tenant_id: ID del tenant (hotel) 
            severity: Severidad del evento (info, warning, critical)
        """
        timestamp = datetime.utcnow()
        
        audit_entry = {
            "timestamp": timestamp.isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "ip_address": ip_address,
            "resource": resource,
            "details": details or {},
            "tenant_id": tenant_id,
            "severity": severity
        }
        
        # Log estructurado (mantiene compatibilidad con logging actual)
        logger.info(
            "security.audit",
            extra=audit_entry
        )
        
        # Persistir en PostgreSQL para análisis histórico
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
                    severity=severity
                )
                session.add(audit_log)
                await session.commit()
                
                logger.debug(
                    "security.audit.persisted",
                    audit_log_id=audit_log.id,
                    event_type=event_type.value
                )
                
        except Exception as db_error:
            # No fallar la operación principal si la auditoría falla
            # pero registrar el error para investigación
            logger.error(
                "security.audit.persistence_failed",
                error=str(db_error),
                event_type=event_type.value,
                user_id=user_id
            )

# Instancia global
audit_logger = AuditLogger()

async def get_audit_logger() -> AuditLogger:
    """Obtener instancia del audit logger"""
    return audit_logger
