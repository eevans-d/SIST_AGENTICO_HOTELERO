"""
Modelo de Audit Log para persistencia en PostgreSQL
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AuditLog(Base):
    """
    Modelo para registro de auditoría de eventos de seguridad.
    Almacena todos los eventos de seguridad para análisis histórico y forense.
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
        """Convertir a diccionario para serialización"""
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
