"""
Security API Endpoints
RESTful API endpoints for security management and authentication
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr
import pyotp
import qrcode
import io
import base64

from app.security.advanced_jwt_auth import AdvancedJWTAuth, UserRegistration, UserLogin
from app.security.audit_logger import SecurityAuditLogger, SecurityEvent, ThreatLevel
from app.security.data_encryption import DataEncryption
from app.security.rate_limiter import AdvancedRateLimiter, RateLimitRule

logger = logging.getLogger(__name__)

# Security dependencies
security = HTTPBearer()
jwt_auth = AdvancedJWTAuth()
audit_logger = SecurityAuditLogger()
data_encryption = DataEncryption()
rate_limiter = AdvancedRateLimiter()

router = APIRouter(prefix="/security", tags=["Security"])


# Request/Response Models
class LoginRequest(BaseModel):
    """Login request model"""

    email: EmailStr
    password: str
    mfa_code: Optional[str] = None
    remember_me: bool = False


class LoginResponse(BaseModel):
    """Login response model"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]
    mfa_required: bool = False


class RefreshTokenRequest(BaseModel):
    """Refresh token request model"""

    refresh_token: str


class MFASetupResponse(BaseModel):
    """MFA setup response model"""

    secret: str
    qr_code: str
    backup_codes: List[str]


class MFAVerifyRequest(BaseModel):
    """MFA verification request model"""

    code: str


class PasswordChangeRequest(BaseModel):
    """Password change request model"""

    current_password: str
    new_password: str = Field(..., min_length=8)


class UserProfileUpdate(BaseModel):
    """User profile update model"""

    full_name: Optional[str] = None
    phone: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class SecurityEventResponse(BaseModel):
    """Security event response model"""

    event_id: str
    event_type: str
    timestamp: str
    threat_level: str
    details: str
    source_ip: str
    endpoint: Optional[str] = None


class RateLimitStatusResponse(BaseModel):
    """Rate limit status response model"""

    ip: str
    blocked: bool
    block_expiry: Optional[int] = None
    violations: List[Dict[str, Any]]
    current_limits: Dict[str, Any]


# Authentication Endpoints


@router.post("/auth/register", response_model=Dict[str, Any])
async def register_user(request: Request, user_data: UserRegistration):
    """Register a new user"""

    try:
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limits
        rate_check = await rate_limiter.check_rate_limit(RateLimitRule.LOGIN_ATTEMPTS, client_ip)
        if not rate_check[0]:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many registration attempts")

        # Register user
        result = await jwt_auth.register_user(user_data)

        if not result["success"]:
            await audit_logger.log_security_event(
                event=SecurityEvent.REGISTRATION_FAILED,
                source_ip=client_ip,
                threat_level=ThreatLevel.MEDIUM,
                details=f"Registration failed: {result['message']}",
            )

            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["message"])

        # Log successful registration
        await audit_logger.log_security_event(
            event=SecurityEvent.USER_REGISTERED,
            user_id=result["user"]["user_id"],
            source_ip=client_ip,
            threat_level=ThreatLevel.LOW,
            details="User registered successfully",
        )

        return {"message": "User registered successfully", "user_id": result["user"]["user_id"]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Registration failed")


@router.post("/auth/login", response_model=LoginResponse)
async def login_user(request: Request, credentials: LoginRequest):
    """Authenticate user and return tokens"""

    try:
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limits
        rate_check = await rate_limiter.check_rate_limit(RateLimitRule.LOGIN_ATTEMPTS, client_ip)
        if not rate_check[0]:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")

        # Authenticate user
        login_data = UserLogin(email=credentials.email, password=credentials.password, mfa_code=credentials.mfa_code)

        result = await jwt_auth.authenticate_user(login_data, client_ip)

        if not result["success"]:
            await audit_logger.log_security_event(
                event=SecurityEvent.AUTHENTICATION_FAILED,
                source_ip=client_ip,
                threat_level=ThreatLevel.HIGH,
                details=f"Login failed: {result['message']}",
            )

            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=result["message"])

        # Check if MFA is required but not provided
        if result.get("mfa_required") and not credentials.mfa_code:
            return LoginResponse(access_token="", refresh_token="", expires_in=0, user={}, mfa_required=True)

        # Generate tokens
        tokens = await jwt_auth.generate_tokens(result["user"], remember_me=credentials.remember_me)

        # Log successful login
        await audit_logger.log_security_event(
            event=SecurityEvent.AUTHENTICATION_SUCCESS,
            user_id=result["user"]["user_id"],
            source_ip=client_ip,
            threat_level=ThreatLevel.LOW,
            details="User logged in successfully",
        )

        return LoginResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_in=tokens["expires_in"],
            user=result["user"],
            mfa_required=False,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed")


@router.post("/auth/refresh", response_model=Dict[str, Any])
async def refresh_access_token(request: Request, refresh_request: RefreshTokenRequest):
    """Refresh access token using refresh token"""

    try:
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limits
        rate_check = await rate_limiter.check_rate_limit(RateLimitRule.TOKEN_REFRESH, client_ip)
        if not rate_check[0]:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many refresh attempts")

        # Refresh token
        result = await jwt_auth.refresh_access_token(refresh_request.refresh_token)

        if not result["success"]:
            await audit_logger.log_security_event(
                event=SecurityEvent.TOKEN_REFRESH_FAILED,
                source_ip=client_ip,
                threat_level=ThreatLevel.MEDIUM,
                details=f"Token refresh failed: {result['message']}",
            )

            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=result["message"])

        return {"access_token": result["access_token"], "expires_in": result["expires_in"]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Token refresh failed")


@router.post("/auth/logout")
async def logout_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout user and invalidate tokens"""

    try:
        client_ip = request.client.host if request.client else "unknown"

        # Verify token and get user info
        verification_result = await jwt_auth.verify_token(credentials.credentials)
        if not verification_result["valid"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = verification_result["user"]
        session = verification_result.get("session")

        # Logout user
        await jwt_auth.logout_user(user["user_id"], session["session_id"] if session else None)

        # Log logout
        await audit_logger.log_security_event(
            event=SecurityEvent.USER_LOGOUT,
            user_id=user["user_id"],
            source_ip=client_ip,
            threat_level=ThreatLevel.LOW,
            details="User logged out successfully",
        )

        return {"message": "Logged out successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed")


# MFA Endpoints


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Setup multi-factor authentication for user"""

    try:
        # Verify token
        verification_result = await jwt_auth.verify_token(credentials.credentials)
        if not verification_result["valid"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = verification_result["user"]

        # Generate MFA secret
        secret = pyotp.random_base32()

        # Create TOTP URI
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user["email"], issuer_name="Hotel Agent System")

        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        qr_code_b64 = base64.b64encode(img_buffer.getvalue()).decode()

        # Generate backup codes
        backup_codes = [pyotp.random_base32()[:8] for _ in range(10)]

        # Store MFA configuration (temporarily)
        await jwt_auth.setup_mfa(user["user_id"], secret, backup_codes)

        # Log MFA setup
        await audit_logger.log_security_event(
            event=SecurityEvent.MFA_SETUP,
            user_id=user["user_id"],
            source_ip=request.client.host if request.client else "unknown",
            threat_level=ThreatLevel.LOW,
            details="MFA setup initiated",
        )

        return MFASetupResponse(
            secret=secret, qr_code=f"data:image/png;base64,{qr_code_b64}", backup_codes=backup_codes
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MFA setup error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="MFA setup failed")


@router.post("/mfa/verify")
async def verify_mfa(
    request: Request, verify_request: MFAVerifyRequest, credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Verify MFA code and enable MFA for user"""

    try:
        # Verify token
        verification_result = await jwt_auth.verify_token(credentials.credentials)
        if not verification_result["valid"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = verification_result["user"]

        # Verify MFA code
        result = await jwt_auth.verify_mfa_code(user["user_id"], verify_request.code)

        if not result["valid"]:
            await audit_logger.log_security_event(
                event=SecurityEvent.MFA_VERIFICATION_FAILED,
                user_id=user["user_id"],
                source_ip=request.client.host if request.client else "unknown",
                threat_level=ThreatLevel.MEDIUM,
                details="MFA verification failed",
            )

            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid MFA code")

        # Enable MFA
        await jwt_auth.enable_mfa(user["user_id"])

        # Log MFA enabled
        await audit_logger.log_security_event(
            event=SecurityEvent.MFA_ENABLED,
            user_id=user["user_id"],
            source_ip=request.client.host if request.client else "unknown",
            threat_level=ThreatLevel.LOW,
            details="MFA enabled successfully",
        )

        return {"message": "MFA enabled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MFA verification error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="MFA verification failed")


@router.post("/mfa/disable")
async def disable_mfa(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Disable multi-factor authentication for user"""

    try:
        # Verify token
        verification_result = await jwt_auth.verify_token(credentials.credentials)
        if not verification_result["valid"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = verification_result["user"]

        # Disable MFA
        await jwt_auth.disable_mfa(user["user_id"])

        # Log MFA disabled
        await audit_logger.log_security_event(
            event=SecurityEvent.MFA_DISABLED,
            user_id=user["user_id"],
            source_ip=request.client.host if request.client else "unknown",
            threat_level=ThreatLevel.MEDIUM,
            details="MFA disabled",
        )

        return {"message": "MFA disabled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MFA disable error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="MFA disable failed")


# User Management Endpoints


@router.get("/profile")
async def get_user_profile(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user profile"""

    try:
        # Verify token
        verification_result = await jwt_auth.verify_token(credentials.credentials)
        if not verification_result["valid"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = verification_result["user"]

        # Get full user profile
        profile = await jwt_auth.get_user_profile(user["user_id"])

        return profile

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get profile")


@router.put("/profile")
async def update_user_profile(
    profile_update: UserProfileUpdate, credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update user profile"""

    try:
        # Verify token
        verification_result = await jwt_auth.verify_token(credentials.credentials)
        if not verification_result["valid"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = verification_result["user"]

        # Update profile
        result = await jwt_auth.update_user_profile(user["user_id"], profile_update.dict(exclude_unset=True))

        if not result["success"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["message"])

        return {"message": "Profile updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update profile error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update profile")


@router.post("/change-password")
async def change_password(
    request: Request,
    password_change: PasswordChangeRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Change user password"""

    try:
        # Verify token
        verification_result = await jwt_auth.verify_token(credentials.credentials)
        if not verification_result["valid"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = verification_result["user"]

        # Change password
        result = await jwt_auth.change_password(
            user["user_id"], password_change.current_password, password_change.new_password
        )

        if not result["success"]:
            await audit_logger.log_security_event(
                event=SecurityEvent.PASSWORD_CHANGE_FAILED,
                user_id=user["user_id"],
                source_ip=request.client.host if request.client else "unknown",
                threat_level=ThreatLevel.MEDIUM,
                details=f"Password change failed: {result['message']}",
            )

            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["message"])

        # Log password change
        await audit_logger.log_security_event(
            event=SecurityEvent.PASSWORD_CHANGED,
            user_id=user["user_id"],
            source_ip=request.client.host if request.client else "unknown",
            threat_level=ThreatLevel.LOW,
            details="Password changed successfully",
        )

        return {"message": "Password changed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to change password")


# Security Monitoring Endpoints


@router.get("/events", response_model=List[SecurityEventResponse])
async def get_security_events(
    limit: int = 50, threat_level: Optional[str] = None, credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get security events (admin only)"""

    try:
        # Verify token and admin role
        verification_result = await jwt_auth.verify_token(credentials.credentials)
        if not verification_result["valid"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = verification_result["user"]
        if user["role"] not in ["admin", "system"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        # Get security events
        events = await audit_logger.get_security_events(
            limit=limit, threat_level=ThreatLevel(threat_level) if threat_level else None
        )

        return [
            SecurityEventResponse(
                event_id=event["event_id"],
                event_type=event["event_type"],
                timestamp=event["timestamp"],
                threat_level=event["threat_level"],
                details=event["details"],
                source_ip=event["source_ip"],
                endpoint=event.get("endpoint"),
            )
            for event in events
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get security events error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get security events")


@router.get("/rate-limits/{ip}", response_model=RateLimitStatusResponse)
async def get_rate_limit_status(ip: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get rate limit status for IP (admin only)"""

    try:
        # Verify token and admin role
        verification_result = await jwt_auth.verify_token(credentials.credentials)
        if not verification_result["valid"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = verification_result["user"]
        if user["role"] not in ["admin", "system"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        # Get rate limit status
        status_data = await rate_limiter.get_rate_limit_status(ip)

        return RateLimitStatusResponse(**status_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get rate limit status error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get rate limit status")


@router.post("/rate-limits/{ip}/whitelist")
async def whitelist_ip(ip: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Add IP to whitelist (admin only)"""

    try:
        # Verify token and admin role
        verification_result = await jwt_auth.verify_token(credentials.credentials)
        if not verification_result["valid"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = verification_result["user"]
        if user["role"] not in ["admin", "system"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        # Whitelist IP
        await rate_limiter.whitelist_ip(ip)

        # Log action
        await audit_logger.log_security_event(
            event=SecurityEvent.IP_WHITELISTED,
            user_id=user["user_id"],
            threat_level=ThreatLevel.LOW,
            details=f"IP whitelisted: {ip}",
        )

        return {"message": f"IP {ip} whitelisted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Whitelist IP error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to whitelist IP")


@router.post("/rate-limits/{ip}/blacklist")
async def blacklist_ip(
    ip: str, duration_minutes: int = 60, credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Add IP to blacklist (admin only)"""

    try:
        # Verify token and admin role
        verification_result = await jwt_auth.verify_token(credentials.credentials)
        if not verification_result["valid"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = verification_result["user"]
        if user["role"] not in ["admin", "system"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        # Blacklist IP
        await rate_limiter.blacklist_ip(ip, duration_minutes)

        # Log action
        await audit_logger.log_security_event(
            event=SecurityEvent.IP_BLACKLISTED,
            user_id=user["user_id"],
            threat_level=ThreatLevel.MEDIUM,
            details=f"IP blacklisted: {ip} for {duration_minutes} minutes",
        )

        return {"message": f"IP {ip} blacklisted for {duration_minutes} minutes"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Blacklist IP error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to blacklist IP")


# Health and Status Endpoints


@router.get("/health")
async def security_health_check():
    """Security system health check"""

    try:
        # Check security components
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {
                "jwt_auth": "healthy",
                "audit_logger": "healthy",
                "data_encryption": "healthy",
                "rate_limiter": "healthy",
            },
        }

        # Test each component
        try:
            await jwt_auth.health_check()
        except Exception:
            health_status["components"]["jwt_auth"] = "unhealthy"
            health_status["status"] = "degraded"

        try:
            await audit_logger.health_check()
        except Exception:
            health_status["components"]["audit_logger"] = "unhealthy"
            health_status["status"] = "degraded"

        try:
            await data_encryption.health_check()
        except Exception:
            health_status["components"]["data_encryption"] = "unhealthy"
            health_status["status"] = "degraded"

        return health_status

    except Exception as e:
        logger.error(f"Security health check error: {e}")
        return {"status": "unhealthy", "timestamp": datetime.now(timezone.utc).isoformat(), "error": str(e)}


@router.get("/stats")
async def get_security_stats(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get security statistics (admin only)"""

    try:
        # Verify token and admin role
        verification_result = await jwt_auth.verify_token(credentials.credentials)
        if not verification_result["valid"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = verification_result["user"]
        if user["role"] not in ["admin", "system"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        # Get security statistics
        stats = await audit_logger.get_security_statistics()

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get security stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get security statistics"
        )
