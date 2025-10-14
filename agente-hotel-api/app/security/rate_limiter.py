"""
Advanced Rate Limiting and DDoS Protection
Sophisticated rate limiting with adaptive thresholds and attack detection
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from collections import defaultdict

from prometheus_client import Counter, Gauge

logger = logging.getLogger(__name__)

# Prometheus metrics
rate_limit_operations_total = Counter(
    "rate_limit_operations_total", "Total rate limiting operations", ["limiter_type", "result"]
)

rate_limit_violations_total = Counter(
    "rate_limit_violations_total", "Total rate limit violations", ["rule_type", "source_ip"]
)

active_rate_limits_gauge = Gauge("active_rate_limits_total", "Number of active rate limits", ["rule_type"])

ddos_attacks_detected_total = Counter(
    "ddos_attacks_detected_total", "Total DDoS attacks detected", ["attack_type", "source"]
)


class RateLimitRule(Enum):
    """Rate limiting rule types"""

    # Authentication limits
    LOGIN_ATTEMPTS = "login_attempts"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_RESET = "password_reset"

    # API limits
    API_REQUESTS = "api_requests"
    RESERVATION_REQUESTS = "reservation_requests"
    AVAILABILITY_CHECKS = "availability_checks"

    # Resource limits
    FILE_UPLOADS = "file_uploads"
    DATA_EXPORTS = "data_exports"
    EMAIL_SENDING = "email_sending"

    # Protection limits
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    FAILED_VALIDATIONS = "failed_validations"
    BRUTE_FORCE_PROTECTION = "brute_force_protection"


class AttackType(Enum):
    """Types of detected attacks"""

    VOLUMETRIC_ATTACK = "volumetric_attack"
    SLOW_ATTACK = "slow_attack"
    APPLICATION_LAYER_ATTACK = "application_layer_attack"
    DISTRIBUTED_ATTACK = "distributed_attack"
    CREDENTIAL_STUFFING = "credential_stuffing"
    API_ABUSE = "api_abuse"


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""

    rule_type: RateLimitRule
    requests_per_window: int
    window_size_seconds: int
    burst_allowance: int = 0
    progressive_penalty: bool = True
    whitelist_ips: List[str] = field(default_factory=list)
    blacklist_ips: List[str] = field(default_factory=list)
    adaptive_threshold: bool = False
    min_requests: int = 1
    max_requests: int = 1000


@dataclass
class RateLimitViolation:
    """Rate limit violation record"""

    violation_id: str
    rule_type: RateLimitRule
    source_ip: str
    user_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    requests_count: int = 0
    window_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    penalty_until: Optional[datetime] = None
    violation_count: int = 1


@dataclass
class AttackSignature:
    """Attack detection signature"""

    attack_type: AttackType
    source_ips: Set[str] = field(default_factory=set)
    request_count: int = 0
    unique_endpoints: Set[str] = field(default_factory=set)
    user_agents: Set[str] = field(default_factory=set)
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence_score: float = 0.0
    is_active: bool = True


class AdvancedRateLimiter:
    """Advanced rate limiting with DDoS protection"""

    def __init__(self):
        # Rate limiting storage
        self.request_counters: Dict[str, Dict[str, int]] = defaultdict(dict)
        self.violation_history: Dict[str, List[RateLimitViolation]] = defaultdict(list)
        self.blocked_ips: Dict[str, datetime] = {}

        # Attack detection
        self.attack_signatures: Dict[str, AttackSignature] = {}
        self.request_timeline: List[Tuple[datetime, str, str]] = []  # time, ip, endpoint

        # Configuration
        self.default_configs = {
            RateLimitRule.LOGIN_ATTEMPTS: RateLimitConfig(
                rule_type=RateLimitRule.LOGIN_ATTEMPTS,
                requests_per_window=5,
                window_size_seconds=300,  # 5 minutes
                progressive_penalty=True,
            ),
            RateLimitRule.API_REQUESTS: RateLimitConfig(
                rule_type=RateLimitRule.API_REQUESTS,
                requests_per_window=100,
                window_size_seconds=60,  # 1 minute
                burst_allowance=20,
                adaptive_threshold=True,
            ),
            RateLimitRule.RESERVATION_REQUESTS: RateLimitConfig(
                rule_type=RateLimitRule.RESERVATION_REQUESTS,
                requests_per_window=10,
                window_size_seconds=300,  # 5 minutes
                progressive_penalty=True,
            ),
            RateLimitRule.AVAILABILITY_CHECKS: RateLimitConfig(
                rule_type=RateLimitRule.AVAILABILITY_CHECKS,
                requests_per_window=50,
                window_size_seconds=60,  # 1 minute
                adaptive_threshold=True,
            ),
            RateLimitRule.BRUTE_FORCE_PROTECTION: RateLimitConfig(
                rule_type=RateLimitRule.BRUTE_FORCE_PROTECTION,
                requests_per_window=3,
                window_size_seconds=600,  # 10 minutes
                progressive_penalty=True,
            ),
        }

        # DDoS detection thresholds
        self.ddos_thresholds = {
            "requests_per_second": 1000,
            "unique_ips_threshold": 100,
            "error_rate_threshold": 0.5,
            "slow_request_threshold": 10.0,  # seconds
        }

        logger.info("Advanced Rate Limiter initialized")

    async def check_rate_limit(
        self, rule_type: RateLimitRule, source_ip: str, user_id: Optional[str] = None, endpoint: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is within rate limits"""

        try:
            # Check if IP is blocked
            if await self._is_ip_blocked(source_ip):
                rate_limit_violations_total.labels(rule_type=rule_type.value, source_ip=source_ip).inc()

                return False, {
                    "blocked": True,
                    "reason": "IP temporarily blocked",
                    "retry_after": self._get_block_expiry(source_ip),
                }

            config = self.default_configs.get(rule_type)
            if not config:
                # Allow if no configuration found
                return True, {"allowed": True}

            # Check whitelist
            if source_ip in config.whitelist_ips:
                return True, {"allowed": True, "whitelisted": True}

            # Check blacklist
            if source_ip in config.blacklist_ips:
                return False, {"blocked": True, "reason": "IP blacklisted"}

            # Get current window
            now = datetime.now(timezone.utc)
            window_key = self._get_window_key(rule_type, source_ip, now, config.window_size_seconds)

            # Get current count
            current_count = self.request_counters[rule_type.value].get(window_key, 0)

            # Calculate effective limit (considering adaptive thresholds)
            effective_limit = await self._calculate_effective_limit(config, source_ip)

            # Check if limit exceeded
            if current_count >= effective_limit:
                # Record violation
                await self._record_violation(rule_type, source_ip, user_id, current_count, now)

                rate_limit_violations_total.labels(rule_type=rule_type.value, source_ip=source_ip).inc()

                return False, {
                    "blocked": True,
                    "reason": "Rate limit exceeded",
                    "current_count": current_count,
                    "limit": effective_limit,
                    "window_size": config.window_size_seconds,
                    "retry_after": config.window_size_seconds,
                }

            # Increment counter
            self.request_counters[rule_type.value][window_key] = current_count + 1

            # Update attack detection
            if endpoint:
                await self._update_attack_detection(source_ip, endpoint, now)

            # Update metrics
            rate_limit_operations_total.labels(limiter_type=rule_type.value, result="allowed").inc()

            return True, {
                "allowed": True,
                "current_count": current_count + 1,
                "limit": effective_limit,
                "remaining": effective_limit - (current_count + 1),
            }

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open - allow request if check fails
            return True, {"allowed": True, "error": str(e)}

    async def _is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is currently blocked"""

        if ip not in self.blocked_ips:
            return False

        block_until = self.blocked_ips[ip]
        now = datetime.now(timezone.utc)

        if now >= block_until:
            # Block expired, remove it
            del self.blocked_ips[ip]
            return False

        return True

    def _get_block_expiry(self, ip: str) -> Optional[int]:
        """Get block expiry time in seconds"""

        if ip not in self.blocked_ips:
            return None

        block_until = self.blocked_ips[ip]
        now = datetime.now(timezone.utc)

        if now >= block_until:
            return 0

        return int((block_until - now).total_seconds())

    def _get_window_key(self, rule_type: RateLimitRule, source_ip: str, timestamp: datetime, window_size: int) -> str:
        """Generate window key for rate limiting"""

        # Create time-based window
        window_start = int(timestamp.timestamp()) // window_size * window_size
        return f"{rule_type.value}:{source_ip}:{window_start}"

    async def _calculate_effective_limit(self, config: RateLimitConfig, source_ip: str) -> int:
        """Calculate effective rate limit considering adaptive thresholds"""

        base_limit = config.requests_per_window

        if not config.adaptive_threshold:
            return base_limit

        # Get violation history for this IP
        violations = self.violation_history.get(source_ip, [])
        recent_violations = [
            v
            for v in violations
            if (datetime.now(timezone.utc) - v.timestamp).total_seconds() < 3600  # Last hour
        ]

        # Reduce limit based on recent violations
        penalty_factor = min(len(recent_violations) * 0.2, 0.8)  # Max 80% reduction
        adjusted_limit = int(base_limit * (1 - penalty_factor))

        return max(adjusted_limit, config.min_requests)

    async def _record_violation(
        self, rule_type: RateLimitRule, source_ip: str, user_id: Optional[str], request_count: int, timestamp: datetime
    ):
        """Record rate limit violation"""

        violation = RateLimitViolation(
            violation_id=f"{rule_type.value}_{source_ip}_{timestamp.timestamp()}",
            rule_type=rule_type,
            source_ip=source_ip,
            user_id=user_id,
            timestamp=timestamp,
            requests_count=request_count,
        )

        self.violation_history[source_ip].append(violation)

        # Clean old violations (keep only last 24 hours)
        cutoff_time = timestamp - timedelta(hours=24)
        self.violation_history[source_ip] = [v for v in self.violation_history[source_ip] if v.timestamp > cutoff_time]

        # Apply progressive penalties
        config = self.default_configs[rule_type]
        if config.progressive_penalty:
            await self._apply_progressive_penalty(source_ip, rule_type)

        logger.warning(f"Rate limit violation: {rule_type.value} from {source_ip}")

    async def _apply_progressive_penalty(self, source_ip: str, rule_type: RateLimitRule):
        """Apply progressive penalty for repeated violations"""

        violations = self.violation_history.get(source_ip, [])
        recent_violations = [
            v
            for v in violations
            if (datetime.now(timezone.utc) - v.timestamp).total_seconds() < 3600  # Last hour
        ]

        if len(recent_violations) >= 3:
            # Block IP for progressive duration
            block_duration_minutes = min(len(recent_violations) * 5, 60)  # Max 1 hour
            block_until = datetime.now(timezone.utc) + timedelta(minutes=block_duration_minutes)

            self.blocked_ips[source_ip] = block_until

            logger.warning(f"Progressive penalty applied: {source_ip} blocked for {block_duration_minutes} minutes")

    async def _update_attack_detection(self, source_ip: str, endpoint: str, timestamp: datetime):
        """Update attack detection based on request patterns"""

        # Add to request timeline
        self.request_timeline.append((timestamp, source_ip, endpoint))

        # Keep only last 5 minutes of data
        cutoff_time = timestamp - timedelta(minutes=5)
        self.request_timeline = [req for req in self.request_timeline if req[0] > cutoff_time]

        # Detect potential attacks
        await self._detect_volumetric_attack(timestamp)
        await self._detect_distributed_attack(timestamp)
        await self._detect_application_layer_attack(timestamp)

    async def _detect_volumetric_attack(self, timestamp: datetime):
        """Detect volumetric DDoS attacks"""

        # Count requests in last minute
        cutoff_time = timestamp - timedelta(minutes=1)
        recent_requests = [req for req in self.request_timeline if req[0] > cutoff_time]

        requests_per_second = len(recent_requests) / 60.0

        if requests_per_second > self.ddos_thresholds["requests_per_second"]:
            attack_id = f"volumetric_{timestamp.timestamp()}"

            if attack_id not in self.attack_signatures:
                source_ips = set(req[1] for req in recent_requests)

                signature = AttackSignature(
                    attack_type=AttackType.VOLUMETRIC_ATTACK,
                    source_ips=source_ips,
                    request_count=len(recent_requests),
                    confidence_score=min(requests_per_second / self.ddos_thresholds["requests_per_second"], 1.0),
                )

                self.attack_signatures[attack_id] = signature

                ddos_attacks_detected_total.labels(
                    attack_type=AttackType.VOLUMETRIC_ATTACK.value,
                    source="multiple" if len(source_ips) > 1 else list(source_ips)[0],
                ).inc()

                logger.critical(
                    f"Volumetric attack detected: {requests_per_second:.1f} req/s from {len(source_ips)} IPs"
                )

    async def _detect_distributed_attack(self, timestamp: datetime):
        """Detect distributed attacks"""

        # Count unique IPs in last 2 minutes
        cutoff_time = timestamp - timedelta(minutes=2)
        recent_requests = [req for req in self.request_timeline if req[0] > cutoff_time]
        unique_ips = set(req[1] for req in recent_requests)

        if len(unique_ips) > self.ddos_thresholds["unique_ips_threshold"]:
            attack_id = f"distributed_{timestamp.timestamp()}"

            if attack_id not in self.attack_signatures:
                signature = AttackSignature(
                    attack_type=AttackType.DISTRIBUTED_ATTACK,
                    source_ips=unique_ips,
                    request_count=len(recent_requests),
                    confidence_score=min(len(unique_ips) / self.ddos_thresholds["unique_ips_threshold"], 1.0),
                )

                self.attack_signatures[attack_id] = signature

                ddos_attacks_detected_total.labels(
                    attack_type=AttackType.DISTRIBUTED_ATTACK.value, source="distributed"
                ).inc()

                logger.critical(f"Distributed attack detected: {len(unique_ips)} unique IPs")

    async def _detect_application_layer_attack(self, timestamp: datetime):
        """Detect application layer attacks"""

        # Analyze request patterns
        cutoff_time = timestamp - timedelta(minutes=5)
        recent_requests = [req for req in self.request_timeline if req[0] > cutoff_time]

        # Group by IP
        ip_requests = defaultdict(list)
        for req in recent_requests:
            ip_requests[req[1]].append(req)

        for ip, requests in ip_requests.items():
            if len(requests) > 50:  # Suspicious if more than 50 requests in 5 minutes
                endpoints = set(req[2] for req in requests)

                # Check for endpoint scanning
                if len(endpoints) > 10:  # Accessing many different endpoints
                    attack_id = f"app_layer_{ip}_{timestamp.timestamp()}"

                    if attack_id not in self.attack_signatures:
                        signature = AttackSignature(
                            attack_type=AttackType.APPLICATION_LAYER_ATTACK,
                            source_ips={ip},
                            request_count=len(requests),
                            unique_endpoints=endpoints,
                            confidence_score=min(len(endpoints) / 20.0, 1.0),
                        )

                        self.attack_signatures[attack_id] = signature

                        ddos_attacks_detected_total.labels(
                            attack_type=AttackType.APPLICATION_LAYER_ATTACK.value, source=ip
                        ).inc()

                        logger.warning(f"Application layer attack detected from {ip}: {len(endpoints)} endpoints")

    async def get_rate_limit_status(self, source_ip: str) -> Dict[str, Any]:
        """Get current rate limit status for IP"""

        status = {
            "ip": source_ip,
            "blocked": await self._is_ip_blocked(source_ip),
            "block_expiry": self._get_block_expiry(source_ip),
            "violations": [],
            "current_limits": {},
        }

        # Get recent violations
        violations = self.violation_history.get(source_ip, [])
        recent_violations = [
            {"rule_type": v.rule_type.value, "timestamp": v.timestamp.isoformat(), "request_count": v.requests_count}
            for v in violations[-10:]  # Last 10 violations
        ]
        status["violations"] = recent_violations

        # Get current limits for each rule
        now = datetime.now(timezone.utc)
        for rule_type, config in self.default_configs.items():
            window_key = self._get_window_key(rule_type, source_ip, now, config.window_size_seconds)
            current_count = self.request_counters[rule_type.value].get(window_key, 0)
            effective_limit = await self._calculate_effective_limit(config, source_ip)

            status["current_limits"][rule_type.value] = {
                "current_count": current_count,
                "limit": effective_limit,
                "remaining": max(0, effective_limit - current_count),
                "window_size": config.window_size_seconds,
            }

        return status

    async def whitelist_ip(self, ip: str, rule_types: Optional[List[RateLimitRule]] = None):
        """Add IP to whitelist"""

        if not rule_types:
            rule_types = list(self.default_configs.keys())

        for rule_type in rule_types:
            config = self.default_configs[rule_type]
            if ip not in config.whitelist_ips:
                config.whitelist_ips.append(ip)

        logger.info(f"IP whitelisted: {ip} for rules: {[rt.value for rt in rule_types]}")

    async def blacklist_ip(self, ip: str, duration_minutes: int = 60):
        """Add IP to blacklist temporarily"""

        block_until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        self.blocked_ips[ip] = block_until

        logger.warning(f"IP blacklisted: {ip} for {duration_minutes} minutes")

    async def get_attack_signatures(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get detected attack signatures"""

        signatures = []

        for attack_id, signature in self.attack_signatures.items():
            if active_only and not signature.is_active:
                continue

            signatures.append(
                {
                    "attack_id": attack_id,
                    "attack_type": signature.attack_type.value,
                    "source_ips": list(signature.source_ips),
                    "request_count": signature.request_count,
                    "unique_endpoints": list(signature.unique_endpoints),
                    "start_time": signature.start_time.isoformat(),
                    "last_activity": signature.last_activity.isoformat(),
                    "confidence_score": signature.confidence_score,
                    "is_active": signature.is_active,
                }
            )

        return signatures

    async def cleanup_expired_data(self):
        """Clean up expired rate limiting data"""

        now = datetime.now(timezone.utc)

        # Clean expired request counters
        for rule_type in self.request_counters:
            expired_keys = []
            for window_key in self.request_counters[rule_type]:
                # Extract timestamp from window key
                try:
                    window_start = int(window_key.split(":")[-1])
                    window_time = datetime.fromtimestamp(window_start, tz=timezone.utc)

                    config = self.default_configs.get(RateLimitRule(rule_type))
                    if config and (now - window_time).total_seconds() > config.window_size_seconds * 2:
                        expired_keys.append(window_key)
                except Exception:
                    expired_keys.append(window_key)  # Remove malformed keys

            for key in expired_keys:
                del self.request_counters[rule_type][key]

        # Clean expired blocks
        expired_blocks = [ip for ip, block_until in self.blocked_ips.items() if now >= block_until]
        for ip in expired_blocks:
            del self.blocked_ips[ip]

        # Clean old violations
        for ip in self.violation_history:
            cutoff_time = now - timedelta(hours=24)
            self.violation_history[ip] = [v for v in self.violation_history[ip] if v.timestamp > cutoff_time]

        # Deactivate old attack signatures
        for signature in self.attack_signatures.values():
            if (now - signature.last_activity).total_seconds() > 3600:  # 1 hour
                signature.is_active = False

        logger.debug("Expired rate limiting data cleaned up")


# Global instance
_rate_limiter = None


def get_rate_limiter() -> AdvancedRateLimiter:
    """Get global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = AdvancedRateLimiter()
    return _rate_limiter
