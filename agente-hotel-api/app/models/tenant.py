from __future__ import annotations
from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, foreign

from .lock_audit import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, unique=True, index=True, nullable=False)  # logical id (slug)
    name = Column(String, nullable=False)
    status = Column(String, default="active", index=True)  # active|inactive
    # Optional per-tenant business hours
    business_hours_start = Column(Integer, nullable=True)
    business_hours_end = Column(Integer, nullable=True)
    business_hours_timezone = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    identifiers = relationship("TenantUserIdentifier", back_populates="tenant", cascade="all,delete-orphan")
    # Relación por clave lógica tenant_id (no PK). Usar ruta completa para evitar problemas de import.
    users = relationship(
        "app.models.user.User",
        back_populates="tenant",
        primaryjoin="Tenant.tenant_id==foreign(app.models.user.User.tenant_id)",
    )


class TenantUserIdentifier(Base):
    __tablename__ = "tenant_user_identifiers"
    __table_args__ = (UniqueConstraint("identifier", name="uq_identifier"),)

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False)
    identifier = Column(String, nullable=False, index=True)  # phone, email, etc
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    tenant = relationship("Tenant", back_populates="identifiers")


# Asegurar que el modelo User esté registrado en el registry antes de configurar mappers
# para que la relación por nombre "User"/ruta completa pueda resolverse en tests.
try:
    from .user import User  # noqa: F401
except Exception:
    pass
