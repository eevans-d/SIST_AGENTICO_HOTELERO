"""
User and Authentication Models
===============================

SQLAlchemy ORM models for user management and password history.

Author: Backend AI Team
Date: 2025-11-03
"""

from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, Text, Enum as SAEnum
from sqlalchemy.orm import relationship

from app.models.lock_audit import Base


class UserRole(str, PyEnum):
    """User roles for RBAC"""
    GUEST = "guest"
    RECEPTIONIST = "receptionist"
    MANAGER = "manager"
    ADMIN = "admin"
    SYSTEM = "system"


class User(Base):
    """
    User model for authentication and authorization.

    Attributes:
        id: Primary key (UUID)
        username: Unique username
        email: User email address
        hashed_password: Bcrypt hashed password
        role: User role (RBAC)
        full_name: User's full name
        is_active: Whether user is active
        is_superuser: Whether user has admin privileges
        tenant_id: Associated tenant (for multi-tenancy)
        password_last_changed: When password was last updated
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "users"

    id = Column(String(255), primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.GUEST, nullable=False)
    full_name = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # MFA
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String(255), nullable=True)

    # Login stats
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    last_login = Column(DateTime, nullable=True)
    account_locked_until = Column(DateTime, nullable=True)

    tenant_id = Column(String(255), ForeignKey("tenants.tenant_id"), nullable=True)

    # Password management
    password_last_changed = Column(DateTime, default=datetime.utcnow, nullable=False)
    password_must_change = Column(Boolean, default=False, nullable=False)

    # Audit timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    password_history = relationship("PasswordHistory", back_populates="user", cascade="all, delete-orphan")
    # Relación por clave lógica tenant_id (no PK). Usar ruta completa y primaryjoin explícito.
    tenant = relationship(
        "app.models.tenant.Tenant",
        back_populates="users",
        primaryjoin="foreign(User.tenant_id)==app.models.tenant.Tenant.tenant_id",
    )

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"


class PasswordHistory(Base):
    """
    Password history for enforcing password reuse policy.

    Stores hashed passwords to prevent users from reusing recent passwords.
    Typically keeps last 5-10 passwords per user.

    Attributes:
        id: Primary key (auto-increment)
        user_id: Foreign key to User
        password_hash: Bcrypt hashed password
        created_at: When password was set
    """

    __tablename__ = "password_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="password_history")

    def __repr__(self):
        return f"<PasswordHistory(user_id={self.user_id}, created_at={self.created_at})>"


class UserSession(Base):
    """
    Active user sessions for JWT token management.

    Tracks active sessions to support token revocation and logout.

    Attributes:
        id: Primary key (UUID)
        user_id: Foreign key to User
        token_jti: JWT token ID (jti claim)
        expires_at: Token expiration timestamp
        created_at: Session creation timestamp
        is_revoked: Whether session was manually revoked
    """

    __tablename__ = "user_sessions"

    id = Column(String(255), primary_key=True, index=True)
    user_id = Column(String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_jti = Column(String(255), unique=True, nullable=False, index=True)

    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)

    # User agent and IP for security auditing
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, expires_at={self.expires_at}, revoked={self.is_revoked})>"
