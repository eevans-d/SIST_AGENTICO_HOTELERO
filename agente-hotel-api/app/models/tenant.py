from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from .lock_audit import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, unique=True, index=True, nullable=False)  # logical id (slug)
    name = Column(String, nullable=False)
    status = Column(String, default="active", index=True)  # active|inactive
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    identifiers = relationship("TenantUserIdentifier", back_populates="tenant", cascade="all,delete-orphan")


class TenantUserIdentifier(Base):
    __tablename__ = "tenant_user_identifiers"
    __table_args__ = (UniqueConstraint("identifier", name="uq_identifier"),)

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False)
    identifier = Column(String, nullable=False, index=True)  # phone, email, etc
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="identifiers")
