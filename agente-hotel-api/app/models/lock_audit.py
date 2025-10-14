# [PROMPT 2.3] app/models/lock_audit.py

from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


def utc_now():
    """UTC timezone-aware datetime factory for SQLAlchemy default."""
    return datetime.now(timezone.utc)


class LockAudit(Base):
    """
    Modelo de auditoría para operaciones de locks distribuidos.

    Registra el ciclo de vida completo de locks: adquisición, extensión,
    liberación y expiración. Útil para debugging, monitoreo y análisis
    de contención de recursos.

    Attributes:
        id (int): Primary key autoincremental
        lock_key (str): Identificador único del lock (ej: "reservation:12345")
        event_type (str): Tipo de evento - "acquired", "extended", "released", "expired"
        timestamp (DateTime): Momento UTC del evento (timezone-aware)
        details (JSON): Metadata adicional del evento:
            - holder_id: ID del proceso/worker que tiene el lock
            - ttl: Time-to-live en segundos
            - reason: Razón de liberación/expiración
            - stack_trace: Stack trace si hay error

    Example:
        >>> audit = LockAudit(
        ...     lock_key="reservation:guest123",
        ...     event_type="acquired",
        ...     details={"holder_id": "worker-1", "ttl": 30}
        ... )
    """

    __tablename__ = "lock_audit"

    id = Column(Integer, primary_key=True, index=True)
    lock_key = Column(String, index=True, nullable=False)
    event_type = Column(String, nullable=False)  # e.g., acquired, extended, released, expired
    timestamp = Column(DateTime, default=utc_now)
    details = Column(JSON)
