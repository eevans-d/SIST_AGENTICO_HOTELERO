# [PROMPT 2.3] app/models/lock_audit.py

from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


def utc_now():
    """UTC timezone-aware datetime factory for SQLAlchemy default."""
    return datetime.now(timezone.utc)


class LockAudit(Base):
    __tablename__ = "lock_audit"

    id = Column(Integer, primary_key=True, index=True)
    lock_key = Column(String, index=True, nullable=False)
    event_type = Column(String, nullable=False)  # e.g., acquired, extended, released, expired
    timestamp = Column(DateTime, default=utc_now)
    details = Column(JSON)
