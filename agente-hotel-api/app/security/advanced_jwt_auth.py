"""
Advanced JWT Authentication System
Enterprise-grade JWT authentication with refresh tokens, role-based access control, and security features
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import jwt
import secrets
from passlib.context import CryptContext
import pyotp
import qrcode
import io
import base64

from app.core.settings import get_settings
from app.core.redis_client import get_redis
from app.security.password_policy import get_password_policy, PasswordPolicyViolation
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# Prometheus metrics
auth_operations_total = Counter("auth_operations_total", "Total authentication operations", ["operation", "status"])

auth_duration_seconds = Histogram("auth_duration_seconds", "Authentication operation duration", ["operation"])

active_sessions_gauge = Gauge("active_sessions_total", "Number of active user sessions")

failed_login_attempts_gauge = Gauge("failed_login_attempts_total", "Number of failed login attempts", ["user_id"])


class UserRole(Enum):
    """User roles for RBAC"""

    GUEST = "guest"
    RECEPTIONIST = "receptionist"
    MANAGER = "manager"
    ADMIN = "admin"
    SYSTEM = "system"


class Permission(Enum):
    """System permissions"""

    # Guest permissions
    VIEW_OWN_RESERVATIONS = "view_own_reservations"
    MODIFY_OWN_RESERVATIONS = "modify_own_reservations"

    # Receptionist permissions
    VIEW_RESERVATIONS = "view_reservations"
    CREATE_RESERVATIONS = "create_reservations"
    MODIFY_RESERVATIONS = "modify_reservations"
    CHECK_AVAILABILITY = "check_availability"
    GUEST_CHECKIN = "guest_checkin"
    GUEST_CHECKOUT = "guest_checkout"

    # Manager permissions
    VIEW_REPORTS = "view_reports"
    MANAGE_RATES = "manage_rates"
    MANAGE_INVENTORY = "manage_inventory"
    VIEW_ANALYTICS = "view_analytics"
    CANCEL_RESERVATIONS = "cancel_reservations"

    # Admin permissions
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    SYSTEM_CONFIG = "system_config"
    VIEW_LOGS = "view_logs"
    MANAGE_INTEGRATIONS = "manage_integrations"


class TokenType(Enum):
    """Token types"""

    ACCESS = "access"
    REFRESH = "refresh"
    RESET_PASSWORD = "reset_password"
    VERIFY_EMAIL = "verify_email"
    MFA = "mfa"


@dataclass
class User:
    """User model"""

    user_id: str
    username: str
    email: str
    password_hash: str
    role: UserRole
    is_active: bool = True
    is_verified: bool = False
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    failed_login_attempts: int = 0
    last_login: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    password_changed_at: datetime = field(default_factory=datetime.now)
    account_locked_until: Optional[datetime] = None

    @property
    def is_locked(self) -> bool:
        """Check if account is locked"""
        if self.account_locked_until:
            return datetime.now(timezone.utc) < self.account_locked_until
        return False


@dataclass
class JWTToken:
    """JWT token model"""

    token: str
    token_type: TokenType
    expires_at: datetime
    user_id: str
    jti: str  # JWT ID for revocation
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AuthSession:
    """Authentication session"""

    session_id: str
    user_id: str
    access_token: JWTToken
    refresh_token: JWTToken
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    is_active: bool = True


class AdvancedJWTAuth:
    """Advanced JWT authentication system"""

    def __init__(self):
        self.settings = get_settings()
        self.redis_client = None

        # Password hashing
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # JWT settings
        self.algorithm = "HS256"
        self.access_token_expire = timedelta(minutes=30)
        self.refresh_token_expire = timedelta(days=7)

        # Security settings
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=30)
        self.password_min_length = 8

        # Role permissions mapping
        self.role_permissions = {
            UserRole.GUEST: [Permission.VIEW_OWN_RESERVATIONS, Permission.MODIFY_OWN_RESERVATIONS],
            UserRole.RECEPTIONIST: [
                Permission.VIEW_OWN_RESERVATIONS,
                Permission.MODIFY_OWN_RESERVATIONS,
                Permission.VIEW_RESERVATIONS,
                Permission.CREATE_RESERVATIONS,
                Permission.MODIFY_RESERVATIONS,
                Permission.CHECK_AVAILABILITY,
                Permission.GUEST_CHECKIN,
                Permission.GUEST_CHECKOUT,
            ],
            UserRole.MANAGER: [
                Permission.VIEW_OWN_RESERVATIONS,
                Permission.MODIFY_OWN_RESERVATIONS,
                Permission.VIEW_RESERVATIONS,
                Permission.CREATE_RESERVATIONS,
                Permission.MODIFY_RESERVATIONS,
                Permission.CHECK_AVAILABILITY,
                Permission.GUEST_CHECKIN,
                Permission.GUEST_CHECKOUT,
                Permission.VIEW_REPORTS,
                Permission.MANAGE_RATES,
                Permission.MANAGE_INVENTORY,
                Permission.VIEW_ANALYTICS,
                Permission.CANCEL_RESERVATIONS,
            ],
            UserRole.ADMIN: [permission for permission in Permission],
            UserRole.SYSTEM: [permission for permission in Permission],
        }

        # Active sessions and revoked tokens
        self.active_sessions: Dict[str, AuthSession] = {}

        logger.info("Advanced JWT Authentication system initialized")

    async def initialize(self):
        """Initialize Redis connection and load revoked tokens"""
        try:
            self.redis_client = await get_redis()
            logger.info("JWT Auth Redis connection established")
        except Exception as e:
            logger.error(f"Failed to initialize JWT Auth Redis: {e}")
            raise

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt - DEPRECATED: Use password_policy.hash_password()"""
        logger.warning("Using deprecated hash_password in advanced_jwt_auth. Migrate to password_policy")
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash - DEPRECATED: Use password_policy.verify_password()"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def validate_password_strength(self, password: str) -> List[str]:
        """
        Validate password strength using PasswordPolicy.

        DEPRECATED: Use password_policy.validate_password_strength() directly.
        This method maintained for backward compatibility.

        Returns:
            List of validation errors (empty if valid)
        """
        logger.warning("Using deprecated validate_password_strength. Migrate to password_policy module")

        policy = get_password_policy()
        is_valid, violations = policy.validate_password_strength(password)

        return violations if not is_valid else []

    def generate_mfa_secret(self) -> str:
        """Generate MFA secret for TOTP"""
        return pyotp.random_base32()

    def generate_mfa_qr_code(self, user: User, secret: str) -> str:
        """Generate QR code for MFA setup"""

        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="Hotel Agent IA")

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")

        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_base64}"

    def verify_mfa_token(self, secret: str, token: str) -> bool:
        """Verify MFA TOTP token"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)

    def create_jwt_token(
        self,
        user_id: str,
        token_type: TokenType,
        expires_delta: Optional[timedelta] = None,
        extra_claims: Optional[Dict[str, Any]] = None,
    ) -> JWTToken:
        """Create JWT token"""

        now = datetime.now(timezone.utc)

        if expires_delta:
            expire = now + expires_delta
        else:
            if token_type == TokenType.ACCESS:
                expire = now + self.access_token_expire
            elif token_type == TokenType.REFRESH:
                expire = now + self.refresh_token_expire
            else:
                expire = now + timedelta(hours=1)

        jti = secrets.token_urlsafe(32)

        payload = {"sub": user_id, "type": token_type.value, "exp": expire, "iat": now, "jti": jti}

        if extra_claims:
            payload.update(extra_claims)

        token = jwt.encode(payload, self.settings.secret_key, algorithm=self.algorithm)

        return JWTToken(token=token, token_type=token_type, expires_at=expire, user_id=user_id, jti=jti)

    def decode_jwt_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate JWT token"""

        try:
            payload = jwt.decode(token, self.settings.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")

    async def authenticate_user(
        self,
        username: str,
        password: str,
        mfa_token: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[AuthSession]:
        """Authenticate user with credentials and optional MFA"""

        start_time = asyncio.get_event_loop().time()

        try:
            # Get user (mock implementation - replace with actual user service)
            user = await self._get_user_by_username(username)

            if not user or not user.is_active:
                auth_operations_total.labels(operation="authenticate", status="user_not_found").inc()
                return None

            if user.is_locked:
                auth_operations_total.labels(operation="authenticate", status="account_locked").inc()
                logger.warning(f"Attempted login to locked account: {username}")
                return None

            # Verify password
            if not self.verify_password(password, user.password_hash):
                await self._handle_failed_login(user)
                auth_operations_total.labels(operation="authenticate", status="invalid_password").inc()
                return None

            # Check MFA if enabled
            if user.mfa_enabled:
                if not mfa_token:
                    auth_operations_total.labels(operation="authenticate", status="mfa_required").inc()
                    return None

                if not self.verify_mfa_token(user.mfa_secret, mfa_token):
                    auth_operations_total.labels(operation="authenticate", status="invalid_mfa").inc()
                    return None

            # Create tokens
            access_token = self.create_jwt_token(
                user_id=user.user_id,
                token_type=TokenType.ACCESS,
                extra_claims={
                    "role": user.role.value,
                    "permissions": [p.value for p in self.role_permissions[user.role]],
                },
            )

            refresh_token = self.create_jwt_token(user_id=user.user_id, token_type=TokenType.REFRESH)

            # Create session
            session_id = secrets.token_urlsafe(32)
            session = AuthSession(
                session_id=session_id,
                user_id=user.user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                user_agent=user_agent,
                ip_address=ip_address,
            )

            # Store session
            self.active_sessions[session_id] = session

            # Store in Redis for persistence
            if self.redis_client:
                await self.redis_client.setex(
                    f"session:{session_id}", int(self.refresh_token_expire.total_seconds()), session_id
                )

                await self.redis_client.setex(
                    f"access_token:{access_token.jti}", int(self.access_token_expire.total_seconds()), user.user_id
                )

                await self.redis_client.setex(
                    f"refresh_token:{refresh_token.jti}", int(self.refresh_token_expire.total_seconds()), user.user_id
                )

            # Reset failed attempts and update last login
            await self._reset_failed_attempts(user)
            await self._update_last_login(user)

            # Update metrics
            auth_duration_seconds.labels(operation="authenticate").observe(asyncio.get_event_loop().time() - start_time)

            auth_operations_total.labels(operation="authenticate", status="success").inc()

            active_sessions_gauge.inc()

            logger.info(f"User authenticated successfully: {username}")
            return session

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            auth_operations_total.labels(operation="authenticate", status="error").inc()
            return None

    async def refresh_token(self, refresh_token: str) -> Optional[JWTToken]:
        """Refresh access token using refresh token"""

        try:
            payload = self.decode_jwt_token(refresh_token)

            if payload.get("type") != TokenType.REFRESH.value:
                return None

            user_id = payload.get("sub")
            jti = payload.get("jti")

            # Check if token is revoked
            if self.redis_client:
                is_revoked = await self.redis_client.get(f"revoked_token:{jti}")
                if is_revoked:
                    return None

            # Get user and verify still active
            user = await self._get_user_by_id(user_id)
            if not user or not user.is_active:
                return None

            # Create new access token
            new_access_token = self.create_jwt_token(
                user_id=user_id,
                token_type=TokenType.ACCESS,
                extra_claims={
                    "role": user.role.value,
                    "permissions": [p.value for p in self.role_permissions[user.role]],
                },
            )

            # Store new token in Redis
            if self.redis_client:
                await self.redis_client.setex(
                    f"access_token:{new_access_token.jti}", int(self.access_token_expire.total_seconds()), user_id
                )

            auth_operations_total.labels(operation="refresh_token", status="success").inc()

            return new_access_token

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            auth_operations_total.labels(operation="refresh_token", status="error").inc()
            return None

    async def revoke_token(self, token: str, token_type: TokenType) -> bool:
        """Revoke token (add to blacklist)"""

        try:
            payload = self.decode_jwt_token(token)
            jti = payload.get("jti")
            exp = payload.get("exp")

            if not jti:
                return False

            # Calculate TTL until token expires
            exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
            ttl = int((exp_datetime - datetime.now(timezone.utc)).total_seconds())

            if ttl > 0 and self.redis_client:
                await self.redis_client.setex(f"revoked_token:{jti}", ttl, "1")

            auth_operations_total.labels(operation="revoke_token", status="success").inc()

            return True

        except Exception as e:
            logger.error(f"Token revocation error: {e}")
            auth_operations_total.labels(operation="revoke_token", status="error").inc()
            return False

    async def logout_session(self, session_id: str) -> bool:
        """Logout and revoke session"""

        try:
            session = self.active_sessions.get(session_id)
            if not session:
                return False

            # Revoke tokens
            await self.revoke_token(session.access_token.token, TokenType.ACCESS)
            await self.revoke_token(session.refresh_token.token, TokenType.REFRESH)

            # Remove session
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]

            # Remove from Redis
            if self.redis_client:
                await self.redis_client.delete(f"session:{session_id}")

            active_sessions_gauge.dec()

            auth_operations_total.labels(operation="logout", status="success").inc()

            return True

        except Exception as e:
            logger.error(f"Logout error: {e}")
            auth_operations_total.labels(operation="logout", status="error").inc()
            return False

    async def validate_token(
        self, token: str, required_permissions: Optional[List[Permission]] = None
    ) -> Optional[Dict[str, Any]]:
        """Validate token and check permissions"""

        try:
            payload = self.decode_jwt_token(token)

            if payload.get("type") != TokenType.ACCESS.value:
                return None

            jti = payload.get("jti")
            user_id = payload.get("sub")

            # Check if token is revoked
            if self.redis_client:
                is_revoked = await self.redis_client.get(f"revoked_token:{jti}")
                if is_revoked:
                    return None

            # Check permissions if required
            if required_permissions:
                user_permissions = payload.get("permissions", [])
                for permission in required_permissions:
                    if permission.value not in user_permissions:
                        logger.warning(f"Permission denied for user {user_id}: {permission.value}")
                        return None

            return payload

        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None

    def check_permission(self, user_role: UserRole, permission: Permission) -> bool:
        """Check if user role has specific permission"""
        return permission in self.role_permissions.get(user_role, [])

    async def _get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username (mock implementation)"""
        # This would typically query your user database
        # For demo purposes, creating a mock admin user
        if username == "admin":
            return User(
                user_id="admin_001",
                username="admin",
                email="admin@hotelagenteia.com",
                password_hash=self.hash_password("admin123!"),
                role=UserRole.ADMIN,
                is_verified=True,
            )

        # Mock receptionist user
        if username == "receptionist":
            return User(
                user_id="rec_001",
                username="receptionist",
                email="receptionist@hotelagenteia.com",
                password_hash=self.hash_password("reception123!"),
                role=UserRole.RECEPTIONIST,
                is_verified=True,
            )

        return None

    async def _get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID (mock implementation)"""
        if user_id == "admin_001":
            return await self._get_user_by_username("admin")
        elif user_id == "rec_001":
            return await self._get_user_by_username("receptionist")
        return None

    async def _handle_failed_login(self, user: User):
        """Handle failed login attempt"""
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= self.max_failed_attempts:
            user.account_locked_until = datetime.now(timezone.utc) + self.lockout_duration
            logger.warning(f"Account locked due to failed attempts: {user.username}")

        failed_login_attempts_gauge.labels(user_id=user.user_id).set(user.failed_login_attempts)

    async def _reset_failed_attempts(self, user: User):
        """Reset failed login attempts"""
        user.failed_login_attempts = 0
        user.account_locked_until = None
        failed_login_attempts_gauge.labels(user_id=user.user_id).set(0)

    async def _update_last_login(self, user: User):
        """Update last login timestamp"""
        user.last_login = datetime.now(timezone.utc)

    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        now = datetime.now(timezone.utc)
        expired_sessions = []

        for session_id, session in self.active_sessions.items():
            if session.refresh_token.expires_at < now:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            await self.logout_session(session_id)

        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")


# Global instance
_jwt_auth = None


async def get_jwt_auth() -> AdvancedJWTAuth:
    """Get global JWT auth instance"""
    global _jwt_auth
    if _jwt_auth is None:
        _jwt_auth = AdvancedJWTAuth()
        await _jwt_auth.initialize()
    return _jwt_auth
