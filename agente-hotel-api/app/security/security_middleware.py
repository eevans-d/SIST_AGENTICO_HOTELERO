"""
Security Middleware Integration
Comprehensive security middleware for the hotel agent system
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timezone
import json
import time
import ipaddress
import re
from dataclasses import dataclass
from enum import Enum

from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import jwt

from app.security.advanced_jwt_auth import AdvancedJWTAuth, UserRole
from app.security.audit_logger import SecurityAuditLogger, SecurityEvent, ThreatLevel
from app.security.data_encryption import DataEncryption, DataClassification
from app.security.rate_limiter import AdvancedRateLimiter, RateLimitRule

logger = logging.getLogger(__name__)

class SecurityLevel(Enum):
    """Security levels for different endpoints"""
    PUBLIC = "public"           # No authentication required
    AUTHENTICATED = "authenticated"  # Basic authentication required
    AUTHORIZED = "authorized"   # Role-based authorization required
    ADMIN = "admin"            # Admin access required
    SYSTEM = "system"          # System-level access required

@dataclass
class SecurityPolicy:
    """Security policy configuration"""
    endpoint_pattern: str
    security_level: SecurityLevel
    allowed_roles: List[UserRole]
    rate_limit_rules: List[RateLimitRule]
    require_mfa: bool = False
    require_encryption: bool = False
    audit_level: ThreatLevel = ThreatLevel.LOW
    ip_whitelist: Optional[List[str]] = None
    ip_blacklist: Optional[List[str]] = None

class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware"""
    
    def __init__(self, app):
        super().__init__(app)
        self.jwt_auth = AdvancedJWTAuth()
        self.audit_logger = SecurityAuditLogger()
        self.data_encryption = DataEncryption()
        self.rate_limiter = AdvancedRateLimiter()
        
        # Security headers
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self'; font-src 'self'; object-src 'none'; media-src 'self'; frame-src 'none';",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }
        
        # Security policies for different endpoints
        self.security_policies = self._initialize_security_policies()
        
        logger.info("Security middleware initialized")
    
    def _initialize_security_policies(self) -> Dict[str, SecurityPolicy]:
        """Initialize security policies for different endpoints"""
        
        return {
            # Public endpoints
            r"/health/.*": SecurityPolicy(
                endpoint_pattern=r"/health/.*",
                security_level=SecurityLevel.PUBLIC,
                allowed_roles=[],
                rate_limit_rules=[RateLimitRule.API_REQUESTS],
                audit_level=ThreatLevel.LOW
            ),
            
            r"/docs.*": SecurityPolicy(
                endpoint_pattern=r"/docs.*",
                security_level=SecurityLevel.PUBLIC,
                allowed_roles=[],
                rate_limit_rules=[RateLimitRule.API_REQUESTS],
                audit_level=ThreatLevel.LOW
            ),
            
            # Authentication endpoints
            r"/auth/login": SecurityPolicy(
                endpoint_pattern=r"/auth/login",
                security_level=SecurityLevel.PUBLIC,
                allowed_roles=[],
                rate_limit_rules=[RateLimitRule.LOGIN_ATTEMPTS, RateLimitRule.BRUTE_FORCE_PROTECTION],
                audit_level=ThreatLevel.HIGH
            ),
            
            r"/auth/refresh": SecurityPolicy(
                endpoint_pattern=r"/auth/refresh",
                security_level=SecurityLevel.AUTHENTICATED,
                allowed_roles=[UserRole.GUEST, UserRole.RECEPTIONIST, UserRole.MANAGER, UserRole.ADMIN, UserRole.SYSTEM],
                rate_limit_rules=[RateLimitRule.TOKEN_REFRESH],
                audit_level=ThreatLevel.MEDIUM
            ),
            
            r"/auth/logout": SecurityPolicy(
                endpoint_pattern=r"/auth/logout",
                security_level=SecurityLevel.AUTHENTICATED,
                allowed_roles=[UserRole.GUEST, UserRole.RECEPTIONIST, UserRole.MANAGER, UserRole.ADMIN, UserRole.SYSTEM],
                rate_limit_rules=[RateLimitRule.API_REQUESTS],
                audit_level=ThreatLevel.LOW
            ),
            
            # API endpoints
            r"/api/reservations.*": SecurityPolicy(
                endpoint_pattern=r"/api/reservations.*",
                security_level=SecurityLevel.AUTHORIZED,
                allowed_roles=[UserRole.GUEST, UserRole.RECEPTIONIST, UserRole.MANAGER, UserRole.ADMIN],
                rate_limit_rules=[RateLimitRule.RESERVATION_REQUESTS, RateLimitRule.API_REQUESTS],
                require_encryption=True,
                audit_level=ThreatLevel.HIGH
            ),
            
            r"/api/availability.*": SecurityPolicy(
                endpoint_pattern=r"/api/availability.*",
                security_level=SecurityLevel.AUTHENTICATED,
                allowed_roles=[UserRole.GUEST, UserRole.RECEPTIONIST, UserRole.MANAGER, UserRole.ADMIN],
                rate_limit_rules=[RateLimitRule.AVAILABILITY_CHECKS, RateLimitRule.API_REQUESTS],
                audit_level=ThreatLevel.MEDIUM
            ),
            
            r"/api/guests.*": SecurityPolicy(
                endpoint_pattern=r"/api/guests.*",
                security_level=SecurityLevel.AUTHORIZED,
                allowed_roles=[UserRole.RECEPTIONIST, UserRole.MANAGER, UserRole.ADMIN],
                rate_limit_rules=[RateLimitRule.API_REQUESTS],
                require_encryption=True,
                audit_level=ThreatLevel.HIGH
            ),
            
            # Webhook endpoints
            r"/webhooks/whatsapp": SecurityPolicy(
                endpoint_pattern=r"/webhooks/whatsapp",
                security_level=SecurityLevel.PUBLIC,  # Webhook verification handled separately
                allowed_roles=[],
                rate_limit_rules=[RateLimitRule.API_REQUESTS],
                audit_level=ThreatLevel.MEDIUM,
                ip_whitelist=["127.0.0.1", "::1"]  # Add WhatsApp webhook IPs in production
            ),
            
            r"/webhooks/gmail": SecurityPolicy(
                endpoint_pattern=r"/webhooks/gmail",
                security_level=SecurityLevel.PUBLIC,  # Webhook verification handled separately
                allowed_roles=[],
                rate_limit_rules=[RateLimitRule.API_REQUESTS],
                audit_level=ThreatLevel.MEDIUM,
                ip_whitelist=["127.0.0.1", "::1"]  # Add Gmail webhook IPs in production
            ),
            
            # Admin endpoints
            r"/admin.*": SecurityPolicy(
                endpoint_pattern=r"/admin.*",
                security_level=SecurityLevel.ADMIN,
                allowed_roles=[UserRole.ADMIN, UserRole.SYSTEM],
                rate_limit_rules=[RateLimitRule.API_REQUESTS],
                require_mfa=True,
                require_encryption=True,
                audit_level=ThreatLevel.CRITICAL
            ),
            
            # Metrics and monitoring
            r"/metrics": SecurityPolicy(
                endpoint_pattern=r"/metrics",
                security_level=SecurityLevel.SYSTEM,
                allowed_roles=[UserRole.SYSTEM],
                rate_limit_rules=[RateLimitRule.API_REQUESTS],
                audit_level=ThreatLevel.LOW,
                ip_whitelist=["127.0.0.1", "::1"]  # Add monitoring system IPs
            )
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through security middleware"""
        
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        endpoint = request.url.path
        method = request.method
        
        try:
            # Get security policy for endpoint
            policy = self._get_security_policy(endpoint)
            
            # Apply security headers
            response_headers = self.security_headers.copy()
            
            # 1. IP Filtering
            ip_check_result = await self._check_ip_filtering(client_ip, policy)
            if not ip_check_result["allowed"]:
                await self._log_security_event(
                    request, SecurityEvent.ACCESS_DENIED,
                    ThreatLevel.HIGH, f"IP blocked: {ip_check_result['reason']}"
                )
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Access denied"},
                    headers=response_headers
                )
            
            # 2. Rate Limiting
            for rule in policy.rate_limit_rules:
                rate_limit_result = await self.rate_limiter.check_rate_limit(
                    rule, client_ip, endpoint=endpoint
                )
                
                if not rate_limit_result[0]:
                    await self._log_security_event(
                        request, SecurityEvent.RATE_LIMIT_EXCEEDED,
                        ThreatLevel.MEDIUM, f"Rate limit exceeded: {rule.value}"
                    )
                    
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "detail": "Rate limit exceeded",
                            "retry_after": rate_limit_result[1].get("retry_after")
                        },
                        headers={
                            **response_headers,
                            "Retry-After": str(rate_limit_result[1].get("retry_after", 60))
                        }
                    )
            
            # 3. Authentication and Authorization
            auth_result = await self._check_authentication_authorization(request, policy)
            if not auth_result["allowed"]:
                await self._log_security_event(
                    request, SecurityEvent.AUTHENTICATION_FAILED,
                    ThreatLevel.HIGH, auth_result["reason"]
                )
                
                return JSONResponse(
                    status_code=auth_result["status_code"],
                    content={"detail": auth_result["reason"]},
                    headers=response_headers
                )
            
            # 4. MFA Check (if required)
            if policy.require_mfa and auth_result.get("user"):
                mfa_result = await self._check_mfa_requirement(auth_result["user"])
                if not mfa_result["valid"]:
                    await self._log_security_event(
                        request, SecurityEvent.MFA_REQUIRED,
                        ThreatLevel.HIGH, "MFA verification required"
                    )
                    
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": "MFA verification required"},
                        headers=response_headers
                    )
            
            # 5. Request Data Encryption/Decryption
            if policy.require_encryption and method in ["POST", "PUT", "PATCH"]:
                await self._process_encrypted_request(request, policy)
            
            # Add security context to request
            request.state.security_context = {
                "policy": policy,
                "client_ip": client_ip,
                "user": auth_result.get("user"),
                "session": auth_result.get("session")
            }
            
            # Log successful access
            await self._log_security_event(
                request, SecurityEvent.ACCESS_GRANTED,
                policy.audit_level, "Access granted"
            )
            
            # Process request
            response = await call_next(request)
            
            # 6. Response Data Encryption
            if policy.require_encryption:
                response = await self._process_encrypted_response(response, policy)
            
            # Add security headers to response
            for header, value in response_headers.items():
                response.headers[header] = value
            
            # Log response
            processing_time = time.time() - start_time
            await self._log_request_response(request, response, processing_time)
            
            return response
            
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            
            await self._log_security_event(
                request, SecurityEvent.SYSTEM_ERROR,
                ThreatLevel.HIGH, f"Security middleware error: {str(e)}"
            )
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal security error"},
                headers=self.security_headers
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        
        # Check X-Forwarded-For header (for reverse proxy setups)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _get_security_policy(self, endpoint: str) -> SecurityPolicy:
        """Get security policy for endpoint"""
        
        for pattern, policy in self.security_policies.items():
            if re.match(pattern, endpoint):
                return policy
        
        # Default policy for unmatched endpoints
        return SecurityPolicy(
            endpoint_pattern=".*",
            security_level=SecurityLevel.AUTHENTICATED,
            allowed_roles=[UserRole.GUEST, UserRole.RECEPTIONIST, UserRole.MANAGER, UserRole.ADMIN],
            rate_limit_rules=[RateLimitRule.API_REQUESTS],
            audit_level=ThreatLevel.MEDIUM
        )
    
    async def _check_ip_filtering(self, client_ip: str, policy: SecurityPolicy) -> Dict[str, Any]:
        """Check IP whitelist/blacklist filtering"""
        
        try:
            # Check blacklist first
            if policy.ip_blacklist:
                for blacklisted_ip in policy.ip_blacklist:
                    if self._ip_matches(client_ip, blacklisted_ip):
                        return {"allowed": False, "reason": "IP blacklisted"}
            
            # Check whitelist
            if policy.ip_whitelist:
                for whitelisted_ip in policy.ip_whitelist:
                    if self._ip_matches(client_ip, whitelisted_ip):
                        return {"allowed": True, "reason": "IP whitelisted"}
                
                # If whitelist exists but IP not in it, deny
                return {"allowed": False, "reason": "IP not whitelisted"}
            
            # No IP restrictions
            return {"allowed": True, "reason": "No IP restrictions"}
            
        except Exception as e:
            logger.error(f"IP filtering error: {e}")
            # Fail secure - deny access on error
            return {"allowed": False, "reason": "IP filtering error"}
    
    def _ip_matches(self, client_ip: str, filter_ip: str) -> bool:
        """Check if client IP matches filter (supports CIDR notation)"""
        
        try:
            # Handle CIDR notation
            if "/" in filter_ip:
                network = ipaddress.ip_network(filter_ip, strict=False)
                return ipaddress.ip_address(client_ip) in network
            else:
                return client_ip == filter_ip
        except:
            return False
    
    async def _check_authentication_authorization(self, request: Request, 
                                                policy: SecurityPolicy) -> Dict[str, Any]:
        """Check authentication and authorization"""
        
        if policy.security_level == SecurityLevel.PUBLIC:
            return {"allowed": True, "reason": "Public endpoint"}
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return {
                "allowed": False,
                "reason": "Missing or invalid authorization header",
                "status_code": status.HTTP_401_UNAUTHORIZED
            }
        
        token = auth_header.split(" ")[1]
        
        try:
            # Verify token
            verification_result = await self.jwt_auth.verify_token(token)
            if not verification_result["valid"]:
                return {
                    "allowed": False,
                    "reason": verification_result["reason"],
                    "status_code": status.HTTP_401_UNAUTHORIZED
                }
            
            user = verification_result["user"]
            session = verification_result.get("session")
            
            # Check if authentication is sufficient
            if policy.security_level == SecurityLevel.AUTHENTICATED:
                return {"allowed": True, "user": user, "session": session}
            
            # Check role-based authorization
            if policy.security_level in [SecurityLevel.AUTHORIZED, SecurityLevel.ADMIN, SecurityLevel.SYSTEM]:
                if user.role not in policy.allowed_roles:
                    return {
                        "allowed": False,
                        "reason": f"Insufficient privileges. Required roles: {[r.value for r in policy.allowed_roles]}",
                        "status_code": status.HTTP_403_FORBIDDEN
                    }
                
                # Check admin access
                if policy.security_level == SecurityLevel.ADMIN and user.role not in [UserRole.ADMIN, UserRole.SYSTEM]:
                    return {
                        "allowed": False,
                        "reason": "Admin access required",
                        "status_code": status.HTTP_403_FORBIDDEN
                    }
                
                # Check system access
                if policy.security_level == SecurityLevel.SYSTEM and user.role != UserRole.SYSTEM:
                    return {
                        "allowed": False,
                        "reason": "System access required",
                        "status_code": status.HTTP_403_FORBIDDEN
                    }
            
            return {"allowed": True, "user": user, "session": session}
            
        except Exception as e:
            logger.error(f"Authentication/authorization error: {e}")
            return {
                "allowed": False,
                "reason": "Authentication error",
                "status_code": status.HTTP_401_UNAUTHORIZED
            }
    
    async def _check_mfa_requirement(self, user) -> Dict[str, Any]:
        """Check MFA requirement for user"""
        
        try:
            # Check if user has MFA enabled and verified
            mfa_status = await self.jwt_auth.get_mfa_status(user.user_id)
            
            if not mfa_status["enabled"]:
                return {"valid": False, "reason": "MFA not enabled"}
            
            if not mfa_status["verified_in_session"]:
                return {"valid": False, "reason": "MFA not verified in current session"}
            
            return {"valid": True}
            
        except Exception as e:
            logger.error(f"MFA check error: {e}")
            return {"valid": False, "reason": "MFA check error"}
    
    async def _process_encrypted_request(self, request: Request, policy: SecurityPolicy):
        """Process encrypted request data"""
        
        try:
            # This would decrypt request body if encryption is implemented
            # For now, just log that encryption should be applied
            logger.debug(f"Encryption required for {request.url.path}")
            
        except Exception as e:
            logger.error(f"Request encryption processing error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request encryption processing failed"
            )
    
    async def _process_encrypted_response(self, response: Response, policy: SecurityPolicy) -> Response:
        """Process encrypted response data"""
        
        try:
            # This would encrypt response body if encryption is implemented
            # For now, just return original response
            logger.debug("Response encryption should be applied")
            return response
            
        except Exception as e:
            logger.error(f"Response encryption processing error: {e}")
            return response
    
    async def _log_security_event(self, request: Request, event: SecurityEvent,
                                threat_level: ThreatLevel, details: str):
        """Log security event"""
        
        try:
            client_ip = self._get_client_ip(request)
            user_id = getattr(request.state, 'security_context', {}).get('user', {}).get('user_id')
            
            await self.audit_logger.log_security_event(
                event=event,
                user_id=user_id,
                source_ip=client_ip,
                endpoint=request.url.path,
                method=request.method,
                threat_level=threat_level,
                details=details,
                user_agent=request.headers.get("User-Agent"),
                session_id=getattr(request.state, 'security_context', {}).get('session', {}).get('session_id')
            )
            
        except Exception as e:
            logger.error(f"Security event logging error: {e}")
    
    async def _log_request_response(self, request: Request, response: Response, processing_time: float):
        """Log request/response for audit purposes"""
        
        try:
            security_context = getattr(request.state, 'security_context', {})
            
            log_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "method": request.method,
                "endpoint": request.url.path,
                "client_ip": security_context.get("client_ip"),
                "user_id": security_context.get("user", {}).get("user_id") if security_context.get("user") else None,
                "status_code": response.status_code,
                "processing_time": processing_time,
                "user_agent": request.headers.get("User-Agent"),
                "content_length": response.headers.get("Content-Length")
            }
            
            logger.info(f"Request processed: {json.dumps(log_data)}")
            
        except Exception as e:
            logger.error(f"Request/response logging error: {e}")

# Security middleware factory
def create_security_middleware():
    """Create and configure security middleware"""
    return SecurityMiddleware