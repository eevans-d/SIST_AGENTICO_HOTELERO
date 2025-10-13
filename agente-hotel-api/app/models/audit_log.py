"""
Modelo de Audit Log para persistencia en PostgreSQL.

Este módulo define el modelo SQLAlchemy para registros de auditoría,
permitiendo tracking completo de eventos de seguridad, accesos, y
operaciones críticas en el sistema hotelero.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AuditLog(Base):
    """
    Modelo para registro exhaustivo de auditoría de eventos del sistema.
    
    Almacena todos los eventos de seguridad, accesos, operaciones críticas
    y cambios de estado para análisis histórico, forense y compliance.
    
    Optimizado con índices compuestos para búsquedas por usuario/fecha
    y tenant/fecha (multi-tenancy).
    
    Attributes:
        id (int): Primary key autoincremental
        timestamp (DateTime): Momento UTC del evento (indexado)
        event_type (str): Tipo de evento - "login_success", "reservation_created",
            "access_denied", "pms_error", etc. (max 100 chars, indexado)
        user_id (str): Identificador del usuario (teléfono, email, ID interno)
            (max 255 chars, indexado, nullable)
        ip_address (str): Dirección IP de origen (IPv4 o IPv6)
            (max 45 chars para IPv6, indexado, nullable)
        resource (str): Recurso accedido o modificado
            (ej: "/api/reservations/123", "room:205") (max 500 chars, nullable)
        details (JSON): Metadata adicional del evento en formato JSON:
            - request_id: ID de correlación de request
            - user_agent: User agent del cliente
            - action_result: Resultado de la acción
            - error_message: Mensaje de error si aplica
            - metadata: Cualquier dato contextual adicional
        tenant_id (str): ID del tenant (multi-tenancy support)
            (max 100 chars, indexado, nullable)
        severity (str): Nivel de severidad - "info", "warning", "error", "critical"
            (max 20 chars, indexado, nullable)
        created_at (DateTime): Momento de creación del registro en DB
    
    Indexes:
        - idx_audit_user_timestamp: Compuesto (user_id, timestamp) para búsquedas por usuario
        - idx_audit_tenant_timestamp: Compuesto (tenant_id, timestamp) para multi-tenancy
        - Individual indexes en: timestamp, event_type, user_id, ip_address, tenant_id, severity
    
    Example:
        >>> log = AuditLog(
        ...     event_type="reservation_created",
        ...     user_id="+34612345678",
        ...     resource="/api/reservations/456",
        ...     details={"booking_id": "HTL-456", "room_type": "double"},
        ...     tenant_id="hotel-madrid",
        ...     severity="info"
        ... )
        >>> session.add(log)
        >>> session.commit()
    """
    __tablename__ = "audit_logs"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Timestamp del evento
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Tipo de evento (login_success, access_denied, etc.)
    event_type = Column(String(100), nullable=False, index=True)
    
    # Usuario involucrado
    user_id = Column(String(255), nullable=True, index=True)
    
    # IP de origen
    ip_address = Column(String(45), nullable=True, index=True)  # IPv6 max length
    
    # Recurso accedido/modificado
    resource = Column(String(500), nullable=True)
    
    # Detalles adicionales en formato JSON
    details = Column(JSON, nullable=True)
    
    # Metadata adicional
    tenant_id = Column(String(100), nullable=True, index=True)
    severity = Column(String(20), nullable=True, index=True)  # info, warning, critical
    
    # Timestamp de creación del registro
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Índices compuestos para queries comunes
    __table_args__ = (
        Index('idx_audit_timestamp_event', 'timestamp', 'event_type'),
        Index('idx_audit_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_audit_tenant_timestamp', 'tenant_id', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, event_type='{self.event_type}', user_id='{self.user_id}', timestamp='{self.timestamp}')>"
    
    def to_dict(self):
        """
        Convierte el registro de auditoría a diccionario para serialización.
        
        Útil para respuestas API, logging estructurado y exportación de datos.
        Todos los campos datetime se convierten a formato ISO 8601.
        
        Returns:
            dict: Representación completa del audit log con:
                - id: ID del registro
                - timestamp: Momento del evento (ISO 8601)
                - event_type: Tipo de evento auditado
                - user_id: ID del usuario que generó el evento
                - ip_address: IP de origen
                - resource: Recurso accedido
                - details: Metadata del evento (JSON)
                - tenant_id: ID del tenant (multi-tenancy)
                - severity: Nivel de severidad (info, warning, error)
                - created_at: Momento de creación del registro (ISO 8601)
        
        Example:
            >>> log = AuditLog(event_type="reservation_created", user_id="+34612345678")
            >>> log.to_dict()
            {'id': 1, 'event_type': 'reservation_created', 'user_id': '+34612345678', ...}
        """
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "event_type": self.event_type,
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "resource": self.resource,
            "details": self.details,
            "tenant_id": self.tenant_id,
            "severity": self.severity,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
