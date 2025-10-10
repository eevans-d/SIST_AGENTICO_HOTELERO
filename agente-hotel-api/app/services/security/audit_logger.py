"""
Sistema de Auditoría de Seguridad
Registra eventos de seguridad importantes
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

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

class AuditLogger:
    """Logger especializado para eventos de seguridad"""
    
    @staticmethod
    async def log_event(
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Registrar evento de auditoría
        
        Args:
            event_type: Tipo de evento
            user_id: ID del usuario involucrado
            ip_address: IP de origen
            resource: Recurso accedido/modificado
            details: Detalles adicionales
        """
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "ip_address": ip_address,
            "resource": resource,
            "details": details or {}
        }
        
        logger.info(
            "security.audit",
            extra=audit_entry
        )
        
        # TODO: Persistir en DB para análisis histórico
        # await db.audit_logs.insert(audit_entry)

# Instancia global
audit_logger = AuditLogger()

async def get_audit_logger() -> AuditLogger:
    """Obtener instancia del audit logger"""
    return audit_logger
