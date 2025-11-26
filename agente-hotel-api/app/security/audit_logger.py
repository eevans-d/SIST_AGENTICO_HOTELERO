"""
Security Audit Logging System
Comprehensive security event logging and monitoring
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
import json
import uuid
from ipaddress import ip_address, ip_network

from prometheus_client import Counter, Histogram
from ..core.settings import get_settings
from ..core.tenant_context import get_tenant_id

logger = logging.getLogger(__name__)

# Prometheus metrics
security_events_total = Counter("security_events_total", "Total security events", ["event_type", "severity", "status"])

security_audit_duration = Histogram(
    "security_audit_duration_seconds", "Security audit operation duration", ["operation"]
)

suspicious_activity_total = Counter(
    "suspicious_activity_total", "Total suspicious activities detected", ["activity_type", "source_ip"]
)


class SecurityEventType(Enum):
    """Types of security events"""

    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_REVOKED = "token_revoked"

    # Authorization events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_ESCALATION = "permission_escalation"

    # Account events
    ACCOUNT_CREATED = "account_created"
    ACCOUNT_MODIFIED = "account_modified"
    ACCOUNT_DELETED = "account_deleted"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    PASSWORD_CHANGED = "password_changed"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"

    # Data events
    DATA_ACCESS = "data_access"
    DATA_MODIFIED = "data_modified"
    DATA_DELETED = "data_deleted"
    DATA_EXPORTED = "data_exported"

    # Security events
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INVALID_TOKEN = "invalid_token"
    BRUTE_FORCE_ATTEMPT = "brute_force_attempt"
    UNUSUAL_LOCATION = "unusual_location"

    # System events
    CONFIGURATION_CHANGED = "configuration_changed"
    SECURITY_POLICY_VIOLATED = "security_policy_violated"
    ENCRYPTION_KEY_ROTATED = "encryption_key_rotated"


class SecuritySeverity(Enum):
    """Security event severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SuspiciousActivityType(Enum):
    """Types of suspicious activities"""

    MULTIPLE_FAILED_LOGINS = "multiple_failed_logins"
    RAPID_REQUESTS = "rapid_requests"
    UNUSUAL_USER_AGENT = "unusual_user_agent"
    GEOGRAPHIC_ANOMALY = "geographic_anomaly"
    OFF_HOURS_ACCESS = "off_hours_access"
    PRIVILEGE_ESCALATION_ATTEMPT = "privilege_escalation_attempt"
    UNUSUAL_DATA_ACCESS = "unusual_data_access"
    CONCURRENT_SESSIONS = "concurrent_sessions"


@dataclass
class SecurityEvent:
    """Security event model"""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: SecurityEventType = SecurityEventType.DATA_ACCESS
    severity: SecuritySeverity = SecuritySeverity.LOW
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = None
    username: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    result: str = "unknown"  # success, failure, blocked
    details: Dict[str, Any] = field(default_factory=dict)
    risk_score: int = 0  # 0-100
    location: Optional[Dict[str, str]] = None
    correlation_id: Optional[str] = None
    tenant_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["severity"] = self.severity.value
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class ThreatIndicator:
    """Threat indicator for pattern detection"""

    indicator_type: str
    value: str
    threat_level: SecuritySeverity
    description: str
    first_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    count: int = 1


class SecurityAuditLogger:
    """Advanced security audit logging system"""

    def __init__(self):
        self.settings = get_settings()
        self.redis_client = None

        # Security thresholds
        self.failed_login_threshold = 5
        self.rate_limit_threshold = 100  # requests per minute
        self.session_timeout = 30 * 60  # 30 minutes

        # Known threat indicators
        self.threat_indicators: Dict[str, ThreatIndicator] = {}

        # IP whitelist and blacklist
        self.ip_whitelist = [ip_network("10.0.0.0/8"), ip_network("172.16.0.0/12"), ip_network("192.168.0.0/16")]
        self.ip_blacklist = []

        # Suspicious user agents
        self.suspicious_user_agents = ["sqlmap", "nikto", "nmap", "masscan", "burp", "zap", "gobuster", "dirb"]

        logger.info("Security Audit Logger initialized")

    async def initialize(self):
        """Initialize Redis connection"""
        try:
            # Mock Redis client for now
            self.redis_client = None
            await self._load_threat_indicators()
            logger.info("Security Audit Logger initialized (mock mode)")
        except Exception as e:
            logger.error(f"Failed to initialize Security Audit Logger: {e}")
            raise

    async def log_security_event(self, event: SecurityEvent) -> bool:
        """Log a security event"""

        try:
            start_time = asyncio.get_event_loop().time()

            # Populate tenant_id if missing
            if not event.tenant_id:
                event.tenant_id = get_tenant_id()

            # Enrich event with location data if IP present and location missing
            if event.ip_address and not event.location:
                event.location = await self._get_ip_geolocation(event.ip_address)

            # Calculate risk score
            event.risk_score = self._calculate_risk_score(event)

            # Enrich event data
            await self._enrich_event_data(event)

            # Check for suspicious activity
            await self._check_suspicious_activity(event)

            # Store event
            await self._store_security_event(event)

            # Update metrics
            security_events_total.labels(
                event_type=event.event_type.value, severity=event.severity.value, status=event.result
            ).inc()

            # Log based on severity
            if event.severity == SecuritySeverity.CRITICAL:
                logger.critical(f"CRITICAL Security Event: {event.event_type.value} - {event.details}")
            elif event.severity == SecuritySeverity.HIGH:
                logger.error(f"HIGH Security Event: {event.event_type.value} - {event.details}")
            elif event.severity == SecuritySeverity.MEDIUM:
                logger.warning(f"MEDIUM Security Event: {event.event_type.value} - {event.details}")
            else:
                logger.info(f"Security Event: {event.event_type.value}")

            # Trigger alerts for high-severity events
            if event.severity in [SecuritySeverity.HIGH, SecuritySeverity.CRITICAL]:
                await self._trigger_security_alert(event)

            # Update audit duration metric
            audit_duration = asyncio.get_event_loop().time() - start_time
            security_audit_duration.labels(operation="log_event").observe(audit_duration)

            return True

        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
            return False

    async def log_authentication_event(
        self,
        event_type: SecurityEventType,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        result: str = "success",
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Log authentication-related security event"""

        severity = SecuritySeverity.LOW
        if event_type == SecurityEventType.LOGIN_FAILED:
            severity = SecuritySeverity.MEDIUM
        elif event_type == SecurityEventType.BRUTE_FORCE_ATTEMPT:
            severity = SecuritySeverity.HIGH

        event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            result=result,
            details=details or {},
        )

        return await self.log_security_event(event)

    async def log_access_event(
        self,
        user_id: str,
        endpoint: str,
        method: str,
        result: str = "success",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Log access control event"""

        event_type = SecurityEventType.ACCESS_GRANTED if result == "success" else SecurityEventType.ACCESS_DENIED
        severity = SecuritySeverity.LOW if result == "success" else SecuritySeverity.MEDIUM

        event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            result=result,
            details=details or {},
        )

        return await self.log_security_event(event)

    async def log_data_access_event(
        self,
        user_id: str,
        resource: str,
        action: str,
        result: str = "success",
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Log data access event"""

        event_type = SecurityEventType.DATA_ACCESS
        if action in ["create", "update", "modify"]:
            event_type = SecurityEventType.DATA_MODIFIED
        elif action in ["delete", "remove"]:
            event_type = SecurityEventType.DATA_DELETED
        elif action in ["export", "download"]:
            event_type = SecurityEventType.DATA_EXPORTED

        severity = SecuritySeverity.LOW
        if action in ["delete", "export"] or "sensitive" in resource.lower():
            severity = SecuritySeverity.MEDIUM

        event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            resource=resource,
            action=action,
            result=result,
            details=details or {},
        )

        return await self.log_security_event(event)

    def _calculate_risk_score(self, event: SecurityEvent) -> int:
        """Calculate risk score for event (0-100)"""

        risk_score = 0

        # Base score by event type
        risk_scores = {
            SecurityEventType.LOGIN_FAILED: 20,
            SecurityEventType.ACCESS_DENIED: 30,
            SecurityEventType.BRUTE_FORCE_ATTEMPT: 80,
            SecurityEventType.SUSPICIOUS_ACTIVITY: 70,
            SecurityEventType.UNUSUAL_LOCATION: 60,
            SecurityEventType.DATA_DELETED: 50,
            SecurityEventType.DATA_EXPORTED: 40,
            SecurityEventType.SECURITY_POLICY_VIOLATED: 85,
        }

        risk_score = risk_scores.get(event.event_type, 10)

        # Adjust based on IP address
        if event.ip_address:
            if self._is_suspicious_ip(event.ip_address):
                risk_score += 30
            elif not self._is_whitelisted_ip(event.ip_address):
                risk_score += 10

        # Adjust based on user agent
        if event.user_agent and self._is_suspicious_user_agent(event.user_agent):
            risk_score += 25

        # Adjust based on time of day (off-hours)
        if self._is_off_hours(event.timestamp):
            risk_score += 15

        # Adjust based on failure result
        if event.result in ["failure", "blocked", "denied"]:
            risk_score += 20

        return min(risk_score, 100)

    async def _enrich_event_data(self, event: SecurityEvent):
        """Enrich event with additional data"""

        # Add geolocation for IP address (mock implementation)
        if event.ip_address:
            event.location = await self._get_ip_geolocation(event.ip_address)

        # Add correlation ID if not present
        if not event.correlation_id:
            event.correlation_id = str(uuid.uuid4())

    async def _check_suspicious_activity(self, event: SecurityEvent):
        """Check for suspicious activity patterns"""

        if not event.ip_address or not self.redis_client:
            return

        try:
            # Check for multiple failed logins
            if event.event_type == SecurityEventType.LOGIN_FAILED:
                key = f"failed_logins:{event.ip_address}"
                count = await self.redis_client.incr(key)
                await self.redis_client.expire(key, 3600)  # 1 hour window

                if count >= self.failed_login_threshold:
                    await self._log_suspicious_activity(
                        SuspiciousActivityType.MULTIPLE_FAILED_LOGINS,
                        event.ip_address,
                        {"failed_count": count, "threshold": self.failed_login_threshold},
                    )

            # Check for rapid requests
            if event.endpoint:
                key = f"requests:{event.ip_address}:{datetime.now().strftime('%Y%m%d%H%M')}"
                count = await self.redis_client.incr(key)
                await self.redis_client.expire(key, 60)  # 1 minute window

                if count >= self.rate_limit_threshold:
                    await self._log_suspicious_activity(
                        SuspiciousActivityType.RAPID_REQUESTS,
                        event.ip_address,
                        {"request_count": count, "threshold": self.rate_limit_threshold},
                    )

            # Check for unusual user agent
            if event.user_agent and self._is_suspicious_user_agent(event.user_agent):
                await self._log_suspicious_activity(
                    SuspiciousActivityType.UNUSUAL_USER_AGENT, event.ip_address, {"user_agent": event.user_agent}
                )

            # Check for geographic anomaly (mock implementation)
            if event.user_id and event.location:
                await self._check_geographic_anomaly(event)

        except Exception as e:
            logger.error(f"Error checking suspicious activity: {e}")

    async def _log_suspicious_activity(
        self, activity_type: SuspiciousActivityType, source_ip: str, details: Dict[str, Any]
    ):
        """Log suspicious activity"""

        suspicious_event = SecurityEvent(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            severity=SecuritySeverity.HIGH,
            ip_address=source_ip,
            details={"activity_type": activity_type.value, **details},
        )

        await self.log_security_event(suspicious_event)

        suspicious_activity_total.labels(activity_type=activity_type.value, source_ip=source_ip).inc()

    async def _store_security_event(self, event: SecurityEvent):
        """Store security event in Redis and/or database"""

        if not self.redis_client:
            return

        try:
            # Store individual event
            event_key = f"security_event:{event.event_id}"
            event_data = json.dumps(event.to_dict())
            await self.redis_client.setex(event_key, 86400 * 30, event_data)  # 30 days

            # Add to event timeline
            timeline_key = f"security_timeline:{datetime.now().strftime('%Y%m%d')}"
            await self.redis_client.zadd(timeline_key, {event.event_id: event.timestamp.timestamp()})
            await self.redis_client.expire(timeline_key, 86400 * 90)  # 90 days

            # Add to user event history if user_id present
            if event.user_id:
                user_key = f"user_events:{event.user_id}"
                await self.redis_client.zadd(user_key, {event.event_id: event.timestamp.timestamp()})
                await self.redis_client.expire(user_key, 86400 * 90)  # 90 days

            # Add to IP event history
            if event.ip_address:
                ip_key = f"ip_events:{event.ip_address}"
                await self.redis_client.zadd(ip_key, {event.event_id: event.timestamp.timestamp()})
                await self.redis_client.expire(ip_key, 86400 * 30)  # 30 days

        except Exception as e:
            logger.error(f"Failed to store security event: {e}")

    async def _trigger_security_alert(self, event: SecurityEvent):
        """Trigger security alert for high-severity events"""

        try:
            # In a real implementation, this would:
            # - Send alerts via email/Slack/PagerDuty
            # - Create tickets in security incident system
            # - Notify security team

            alert_data = {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "severity": event.severity.value,
                "risk_score": event.risk_score,
                "timestamp": event.timestamp.isoformat(),
                "details": event.details,
            }

            # Store alert for retrieval
            if self.redis_client:
                alert_key = f"security_alert:{event.event_id}"
                await self.redis_client.setex(alert_key, 86400 * 7, json.dumps(alert_data))

            logger.critical(f"SECURITY ALERT: {event.event_type.value} - Risk Score: {event.risk_score}")

        except Exception as e:
            logger.error(f"Failed to trigger security alert: {e}")

    def _is_suspicious_ip(self, ip_str: str) -> bool:
        """Check if IP is suspicious"""
        try:
            ip = ip_address(ip_str)
            for blacklisted_network in self.ip_blacklist:
                if ip in blacklisted_network:
                    return True
            return False
        except Exception:
            return True  # Invalid IP format is suspicious

    def _is_whitelisted_ip(self, ip_str: str) -> bool:
        """Check if IP is whitelisted"""
        try:
            ip = ip_address(ip_str)
            for whitelisted_network in self.ip_whitelist:
                if ip in whitelisted_network:
                    return True
            return False
        except Exception:
            return False

    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is suspicious"""
        user_agent_lower = user_agent.lower()
        return any(suspicious in user_agent_lower for suspicious in self.suspicious_user_agents)

    def _is_off_hours(self, timestamp: datetime) -> bool:
        """Check if timestamp is during off-hours"""
        hour = timestamp.hour
        return hour < 6 or hour > 22  # Before 6 AM or after 10 PM

    async def _get_ip_geolocation(self, ip_address: str) -> Dict[str, str]:
        """Get IP geolocation (mock implementation)"""
        # In real implementation, use GeoIP database or service
        return {"country": "Unknown", "region": "Unknown", "city": "Unknown", "latitude": "0.0", "longitude": "0.0"}

    async def _check_geographic_anomaly(self, event: SecurityEvent):
        """Check for geographic anomalies (mock implementation)"""
        # In real implementation, compare with user's typical locations
        pass

    async def _load_threat_indicators(self):
        """Load threat indicators from storage"""
        if not self.redis_client:
            return

        try:
            # Load known malicious IPs, domains, etc.
            # This is a mock implementation
            pass
        except Exception as e:
            logger.error(f"Failed to load threat indicators: {e}")

    async def get_security_events(
        self,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        event_type: Optional[SecurityEventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[SecurityEvent]:
        """Retrieve security events with filters"""

        if not self.redis_client:
            return []

        try:
            events = []

            if user_id:
                # Get events for specific user
                user_key = f"user_events:{user_id}"
                event_ids = await self.redis_client.zrevrange(user_key, 0, limit - 1)

                for event_id in event_ids:
                    event_key = f"security_event:{event_id.decode()}"
                    event_data = await self.redis_client.get(event_key)
                    if event_data:
                        event_dict = json.loads(event_data)
                        events.append(SecurityEvent(**event_dict))

            return events

        except Exception as e:
            logger.error(f"Failed to retrieve security events: {e}")
            return []

    async def get_security_metrics(self, time_range: Optional[Any] = None) -> Dict[str, Any]:
        """Get security metrics for dashboard"""

        try:
            # This would typically aggregate from stored events
            # Mock implementation returning sample metrics

            return {
                "total_events": 1250,
                "critical_events": 5,
                "high_events": 23,
                "medium_events": 145,
                "low_events": 1077,
                "failed_logins": 67,
                "blocked_requests": 34,
                "suspicious_activities": 12,
                "unique_ips": 89,
                "top_event_types": [
                    {"type": "login_success", "count": 456},
                    {"type": "data_access", "count": 234},
                    {"type": "login_failed", "count": 67},
                ],
            }

        except Exception as e:
            logger.error(f"Failed to get security metrics: {e}")
            return {}


# Global instance
_audit_logger = None


async def get_audit_logger() -> SecurityAuditLogger:
    """Get global security audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = SecurityAuditLogger()
        await _audit_logger.initialize()
    return _audit_logger
