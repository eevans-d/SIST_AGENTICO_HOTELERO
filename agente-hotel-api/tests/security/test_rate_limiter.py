"""
Rate Limiter Security Testing Suite
Comprehensive tests for rate limiting and DDoS protection
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock
from datetime import datetime, timedelta, timezone
import asyncio
from collections import defaultdict

# Import with fallback
try:
    from app.security.rate_limiter import AdvancedRateLimiter, RateLimitRule, AttackType
except ImportError:
    # Define test enums if not available
    from enum import Enum

    class RateLimitRule(Enum):
        LOGIN_ATTEMPTS = "login_attempts"
        API_REQUESTS = "api_requests"
        RESERVATION_REQUESTS = "reservation_requests"
        AVAILABILITY_CHECKS = "availability_checks"
        BRUTE_FORCE_PROTECTION = "brute_force_protection"

    class AttackType(Enum):
        VOLUMETRIC_ATTACK = "volumetric_attack"
        DISTRIBUTED_ATTACK = "distributed_attack"
        APPLICATION_LAYER_ATTACK = "application_layer_attack"

    # Mock rate limiter for testing
    class AdvancedRateLimiter:
        def __init__(self):
            self.request_counters = defaultdict(dict)
            self.violation_history = defaultdict(list)
            self.blocked_ips = {}
            self.attack_signatures = {}
            self.request_timeline = []


class TestRateLimiterBasics:
    """Test basic rate limiting functionality"""

    @pytest_asyncio.fixture
    async def rate_limiter(self):
        """Create rate limiter instance for testing"""
        limiter = AdvancedRateLimiter()
        return limiter

    async def test_api_rate_limit_within_bounds(self, rate_limiter):
        """Test API requests within rate limits"""

        source_ip = "192.168.1.100"
        rule_type = RateLimitRule.API_REQUESTS

        # Make requests within limit
        for i in range(50):  # Assuming limit is 100/minute
            allowed, details = await rate_limiter.check_rate_limit(rule_type, source_ip)
            assert allowed is True
            assert details["allowed"] is True

    async def test_api_rate_limit_exceeded(self, rate_limiter):
        """Test API rate limit exceeded"""

        source_ip = "192.168.1.100"
        rule_type = RateLimitRule.API_REQUESTS

        # Mock request counter to be at limit
        window_key = rate_limiter._get_window_key(rule_type, source_ip, datetime.now(timezone.utc), 60)
        rate_limiter.request_counters[rule_type.value][window_key] = 100

        # Next request should be blocked
        allowed, details = await rate_limiter.check_rate_limit(rule_type, source_ip)
        assert allowed is False
        assert details["blocked"] is True
        assert "rate limit exceeded" in details["reason"].lower()

    async def test_login_attempts_rate_limit(self, rate_limiter):
        """Test login attempts rate limiting"""

        source_ip = "192.168.1.100"
        rule_type = RateLimitRule.LOGIN_ATTEMPTS

        # Simulate multiple login attempts
        for i in range(5):  # Assuming limit is 5 per 5 minutes
            allowed, details = await rate_limiter.check_rate_limit(rule_type, source_ip)
            if i < 4:  # First 4 should be allowed
                assert allowed is True
            else:  # 5th should be blocked
                assert allowed is False


class TestProgressivePenalties:
    """Test progressive penalty system"""

    async def test_progressive_blocking_duration(self, rate_limiter):
        """Test progressive blocking duration increases"""

        source_ip = "192.168.1.100"

        # Simulate multiple violations
        for violation_count in range(1, 5):
            await rate_limiter._apply_progressive_penalty(source_ip, RateLimitRule.LOGIN_ATTEMPTS)

            # Check if IP is blocked
            is_blocked = await rate_limiter._is_ip_blocked(source_ip)

            if violation_count >= 3:  # Should be blocked after 3 violations
                assert is_blocked is True

                # Block duration should increase
                block_expiry = rate_limiter._get_block_expiry(source_ip)
                assert block_expiry > 0

    async def test_violation_history_tracking(self, rate_limiter):
        """Test violation history tracking"""

        source_ip = "192.168.1.100"
        rule_type = RateLimitRule.LOGIN_ATTEMPTS

        # Record violation
        await rate_limiter._record_violation(rule_type, source_ip, "user-123", 10, datetime.now(timezone.utc))

        # Check violation history
        violations = rate_limiter.violation_history[source_ip]
        assert len(violations) == 1
        assert violations[0].rule_type == rule_type
        assert violations[0].source_ip == source_ip

    async def test_adaptive_threshold_adjustment(self, rate_limiter):
        """Test adaptive threshold adjustment based on history"""

        source_ip = "192.168.1.100"
        config = rate_limiter.default_configs[RateLimitRule.API_REQUESTS]

        # Add violation history
        for i in range(3):
            await rate_limiter._record_violation(
                RateLimitRule.API_REQUESTS, source_ip, None, 100, datetime.now(timezone.utc) - timedelta(minutes=i * 10)
            )

        # Check effective limit is reduced
        effective_limit = await rate_limiter._calculate_effective_limit(config, source_ip)
        assert effective_limit < config.requests_per_window


class TestDDoSDetection:
    """Test DDoS attack detection"""

    async def test_volumetric_attack_detection(self, rate_limiter):
        """Test detection of volumetric attacks"""

        timestamp = datetime.now(timezone.utc)

        # Simulate high volume of requests
        for i in range(1200):  # Above threshold
            rate_limiter.request_timeline.append(
                (timestamp - timedelta(seconds=i % 60), f"192.168.1.{i % 10}", "/api/endpoint")
            )

        # Trigger detection
        await rate_limiter._detect_volumetric_attack(timestamp)

        # Check if attack was detected
        volumetric_attacks = [
            sig for sig in rate_limiter.attack_signatures.values() if sig.attack_type == AttackType.VOLUMETRIC_ATTACK
        ]
        assert len(volumetric_attacks) > 0

    async def test_distributed_attack_detection(self, rate_limiter):
        """Test detection of distributed attacks"""

        timestamp = datetime.now(timezone.utc)

        # Simulate requests from many unique IPs
        for i in range(150):  # Above unique IP threshold
            rate_limiter.request_timeline.append(
                (timestamp - timedelta(seconds=i % 120), f"192.168.{i % 256}.{i % 256}", "/api/endpoint")
            )

        # Trigger detection
        await rate_limiter._detect_distributed_attack(timestamp)

        # Check if distributed attack was detected
        distributed_attacks = [
            sig for sig in rate_limiter.attack_signatures.values() if sig.attack_type == AttackType.DISTRIBUTED_ATTACK
        ]
        assert len(distributed_attacks) > 0

    async def test_application_layer_attack_detection(self, rate_limiter):
        """Test detection of application layer attacks"""

        timestamp = datetime.now(timezone.utc)
        source_ip = "192.168.1.100"

        # Simulate scanning different endpoints
        endpoints = [f"/api/endpoint{i}" for i in range(15)]
        for i, endpoint in enumerate(endpoints):
            for j in range(4):  # Multiple requests per endpoint
                rate_limiter.request_timeline.append(
                    (timestamp - timedelta(minutes=i, seconds=j * 10), source_ip, endpoint)
                )

        # Trigger detection
        await rate_limiter._detect_application_layer_attack(timestamp)

        # Check if application layer attack was detected
        app_layer_attacks = [
            sig
            for sig in rate_limiter.attack_signatures.values()
            if sig.attack_type == AttackType.APPLICATION_LAYER_ATTACK
        ]
        assert len(app_layer_attacks) > 0


class TestIPFiltering:
    """Test IP filtering functionality"""

    async def test_whitelist_functionality(self, rate_limiter):
        """Test IP whitelisting"""

        whitelisted_ip = "192.168.1.100"
        rule_types = [RateLimitRule.API_REQUESTS, RateLimitRule.LOGIN_ATTEMPTS]

        # Add IP to whitelist
        await rate_limiter.whitelist_ip(whitelisted_ip, rule_types)

        # Verify whitelist status
        for rule_type in rule_types:
            config = rate_limiter.default_configs[rule_type]
            assert whitelisted_ip in config.whitelist_ips

        # Test that whitelisted IP is not blocked even with high request count
        window_key = rate_limiter._get_window_key(
            RateLimitRule.API_REQUESTS, whitelisted_ip, datetime.now(timezone.utc), 60
        )
        rate_limiter.request_counters[RateLimitRule.API_REQUESTS.value][window_key] = 1000

        allowed, details = await rate_limiter.check_rate_limit(RateLimitRule.API_REQUESTS, whitelisted_ip)
        assert allowed is True
        assert details.get("whitelisted") is True

    async def test_blacklist_functionality(self, rate_limiter):
        """Test IP blacklisting"""

        blacklisted_ip = "192.168.1.100"
        duration_minutes = 30

        # Add IP to blacklist
        await rate_limiter.blacklist_ip(blacklisted_ip, duration_minutes)

        # Verify IP is blocked
        is_blocked = await rate_limiter._is_ip_blocked(blacklisted_ip)
        assert is_blocked is True

        # Check block expiry time
        block_expiry = rate_limiter._get_block_expiry(blacklisted_ip)
        assert block_expiry > 0
        assert block_expiry <= duration_minutes * 60

    async def test_temporary_blocking_expiry(self, rate_limiter):
        """Test that temporary blocks expire correctly"""

        blocked_ip = "192.168.1.100"

        # Set block to expire in the past
        past_time = datetime.now(timezone.utc) - timedelta(minutes=1)
        rate_limiter.blocked_ips[blocked_ip] = past_time

        # Check that IP is no longer blocked
        is_blocked = await rate_limiter._is_ip_blocked(blocked_ip)
        assert is_blocked is False

        # Verify IP was removed from blocked list
        assert blocked_ip not in rate_limiter.blocked_ips


class TestRateLimitRules:
    """Test different rate limit rules"""

    async def test_brute_force_protection(self, rate_limiter):
        """Test brute force protection rules"""

        source_ip = "192.168.1.100"
        rule_type = RateLimitRule.BRUTE_FORCE_PROTECTION

        # Simulate brute force attempts
        for i in range(4):  # Assuming limit is 3 per 10 minutes
            allowed, details = await rate_limiter.check_rate_limit(rule_type, source_ip)
            if i < 3:
                assert allowed is True
            else:
                assert allowed is False
                assert "rate limit exceeded" in details["reason"].lower()

    async def test_reservation_request_limits(self, rate_limiter):
        """Test reservation request rate limits"""

        source_ip = "192.168.1.100"
        rule_type = RateLimitRule.RESERVATION_REQUESTS

        # Test within reasonable limits
        for i in range(8):  # Assuming limit is 10 per 5 minutes
            allowed, details = await rate_limiter.check_rate_limit(rule_type, source_ip)
            assert allowed is True

        # Mock hitting the limit
        window_key = rate_limiter._get_window_key(rule_type, source_ip, datetime.now(timezone.utc), 300)
        rate_limiter.request_counters[rule_type.value][window_key] = 10

        # Next request should be blocked
        allowed, details = await rate_limiter.check_rate_limit(rule_type, source_ip)
        assert allowed is False

    async def test_availability_check_limits(self, rate_limiter):
        """Test availability check rate limits"""

        source_ip = "192.168.1.100"
        rule_type = RateLimitRule.AVAILABILITY_CHECKS

        # Test rapid availability checks
        for i in range(45):  # Assuming limit is 50 per minute
            allowed, details = await rate_limiter.check_rate_limit(rule_type, source_ip)
            assert allowed is True


class TestRateLimitStatus:
    """Test rate limit status reporting"""

    async def test_get_rate_limit_status(self, rate_limiter):
        """Test getting rate limit status for IP"""

        source_ip = "192.168.1.100"

        # Add some violations
        await rate_limiter._record_violation(
            RateLimitRule.LOGIN_ATTEMPTS, source_ip, "user-123", 5, datetime.now(timezone.utc)
        )

        # Get status
        status = await rate_limiter.get_rate_limit_status(source_ip)

        assert status["ip"] == source_ip
        assert "blocked" in status
        assert "violations" in status
        assert "current_limits" in status
        assert len(status["violations"]) > 0

    async def test_attack_signatures_reporting(self, rate_limiter):
        """Test attack signatures reporting"""

        # Mock attack signature
        attack_id = "volumetric_123"
        from app.security.rate_limiter import AttackSignature

        signature = AttackSignature(
            attack_type=AttackType.VOLUMETRIC_ATTACK,
            source_ips={"192.168.1.100", "192.168.1.101"},
            request_count=1500,
            confidence_score=0.9,
        )
        rate_limiter.attack_signatures[attack_id] = signature

        # Get attack signatures
        signatures = await rate_limiter.get_attack_signatures()

        assert len(signatures) > 0
        assert signatures[0]["attack_type"] == AttackType.VOLUMETRIC_ATTACK.value
        assert signatures[0]["confidence_score"] == 0.9


class TestDataCleanup:
    """Test data cleanup functionality"""

    async def test_cleanup_expired_counters(self, rate_limiter):
        """Test cleanup of expired request counters"""

        # Add old counter data
        old_timestamp = int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp())
        old_window_key = f"api_requests:192.168.1.100:{old_timestamp}"
        rate_limiter.request_counters["api_requests"][old_window_key] = 50

        # Add recent counter data
        recent_timestamp = int(datetime.now(timezone.utc).timestamp())
        recent_window_key = f"api_requests:192.168.1.100:{recent_timestamp}"
        rate_limiter.request_counters["api_requests"][recent_window_key] = 10

        # Run cleanup
        await rate_limiter.cleanup_expired_data()

        # Verify old data is removed but recent data remains
        assert old_window_key not in rate_limiter.request_counters["api_requests"]
        assert recent_window_key in rate_limiter.request_counters["api_requests"]

    async def test_cleanup_expired_blocks(self, rate_limiter):
        """Test cleanup of expired IP blocks"""

        # Add expired block
        expired_ip = "192.168.1.100"
        rate_limiter.blocked_ips[expired_ip] = datetime.now(timezone.utc) - timedelta(minutes=1)

        # Add active block
        active_ip = "192.168.1.101"
        rate_limiter.blocked_ips[active_ip] = datetime.now(timezone.utc) + timedelta(minutes=30)

        # Run cleanup
        await rate_limiter.cleanup_expired_data()

        # Verify expired block is removed but active block remains
        assert expired_ip not in rate_limiter.blocked_ips
        assert active_ip in rate_limiter.blocked_ips

    async def test_cleanup_old_violations(self, rate_limiter):
        """Test cleanup of old violation records"""

        source_ip = "192.168.1.100"

        # Add old violation
        old_violation = Mock()
        old_violation.timestamp = datetime.now(timezone.utc) - timedelta(hours=25)
        rate_limiter.violation_history[source_ip].append(old_violation)

        # Add recent violation
        recent_violation = Mock()
        recent_violation.timestamp = datetime.now(timezone.utc) - timedelta(hours=1)
        rate_limiter.violation_history[source_ip].append(recent_violation)

        # Run cleanup
        await rate_limiter.cleanup_expired_data()

        # Verify old violation is removed but recent violation remains
        assert len(rate_limiter.violation_history[source_ip]) == 1
        assert rate_limiter.violation_history[source_ip][0] == recent_violation


class TestConcurrentAccess:
    """Test concurrent access scenarios"""

    async def test_concurrent_rate_limit_checks(self, rate_limiter):
        """Test concurrent rate limit checks from same IP"""

        source_ip = "192.168.1.100"
        rule_type = RateLimitRule.API_REQUESTS

        # Simulate concurrent requests
        tasks = []
        for i in range(20):
            task = rate_limiter.check_rate_limit(rule_type, source_ip)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful requests
        allowed_count = sum(1 for allowed, _ in results if allowed)

        # Should respect rate limits even under concurrent access
        assert allowed_count <= rate_limiter.default_configs[rule_type].requests_per_window

    async def test_concurrent_violation_recording(self, rate_limiter):
        """Test concurrent violation recording"""

        source_ip = "192.168.1.100"
        rule_type = RateLimitRule.LOGIN_ATTEMPTS

        # Simulate concurrent violations
        tasks = []
        for i in range(10):
            task = rate_limiter._record_violation(rule_type, source_ip, f"user-{i}", 5, datetime.now(timezone.utc))
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all violations were recorded
        violations = rate_limiter.violation_history[source_ip]
        assert len(violations) == 10


class TestErrorHandling:
    """Test error handling in rate limiter"""

    async def test_malformed_window_key(self, rate_limiter):
        """Test handling of malformed window keys"""

        # Add malformed window key
        malformed_key = "invalid:window:key:format"
        rate_limiter.request_counters["api_requests"][malformed_key] = 50

        # Cleanup should handle malformed keys gracefully
        try:
            await rate_limiter.cleanup_expired_data()
            # Should not raise exception
            assert True
        except Exception as e:
            pytest.fail(f"Cleanup failed with malformed key: {e}")

    async def test_invalid_rule_type(self, rate_limiter):
        """Test handling of invalid rule types"""

        source_ip = "192.168.1.100"

        # Create mock invalid rule type
        class InvalidRule:
            value = "invalid_rule"

        invalid_rule = InvalidRule()

        # Should handle gracefully
        allowed, details = await rate_limiter.check_rate_limit(invalid_rule, source_ip)

        # Should default to allowing the request
        assert allowed is True

    async def test_memory_pressure_handling(self, rate_limiter):
        """Test handling under memory pressure"""

        # Simulate many IPs with violation history
        for i in range(1000):
            source_ip = f"192.168.{i // 256}.{i % 256}"
            await rate_limiter._record_violation(
                RateLimitRule.API_REQUESTS, source_ip, None, 10, datetime.now(timezone.utc)
            )

        # System should still function
        test_ip = "192.168.1.100"
        allowed, details = await rate_limiter.check_rate_limit(RateLimitRule.API_REQUESTS, test_ip)

        assert isinstance(allowed, bool)
        assert isinstance(details, dict)


class TestPerformanceOptimization:
    """Test performance optimization features"""

    async def test_efficient_window_key_generation(self, rate_limiter):
        """Test efficient window key generation"""

        rule_type = RateLimitRule.API_REQUESTS
        source_ip = "192.168.1.100"
        timestamp = datetime.now(timezone.utc)
        window_size = 60

        # Generate many window keys
        start_time = datetime.now()

        for i in range(1000):
            key = rate_limiter._get_window_key(rule_type, source_ip, timestamp, window_size)
            assert isinstance(key, str)
            assert len(key) > 0

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Should be very fast
        assert duration < 1.0  # Less than 1 second for 1000 operations

    async def test_memory_efficient_storage(self, rate_limiter):
        """Test memory-efficient storage of rate limit data"""

        # Add many counters
        for i in range(100):
            source_ip = f"192.168.1.{i}"
            rule_type = RateLimitRule.API_REQUESTS
            window_key = rate_limiter._get_window_key(rule_type, source_ip, datetime.now(timezone.utc), 60)
            rate_limiter.request_counters[rule_type.value][window_key] = i

        # Verify data structure efficiency
        assert len(rate_limiter.request_counters[RateLimitRule.API_REQUESTS.value]) == 100

        # Cleanup should reduce memory usage
        await rate_limiter.cleanup_expired_data()

        # Memory usage should be reasonable
        import sys

        memory_usage = sys.getsizeof(rate_limiter.request_counters)
        assert memory_usage < 1024 * 1024  # Less than 1MB


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
