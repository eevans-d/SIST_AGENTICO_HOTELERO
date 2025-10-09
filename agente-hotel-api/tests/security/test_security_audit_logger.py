"""
Security Audit Logger Testing Suite
Comprehensive tests for security event logging and threat detection
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta, timezone
import json
import uuid

from app.security.audit_logger import SecurityAuditLogger
try:
    from app.security.audit_logger import SecurityEvent, ThreatLevel
except ImportError:
    # Define test enums if not available
    from enum import Enum
    
    class SecurityEvent(Enum):
        AUTHENTICATION_SUCCESS = "authentication_success"
        AUTHENTICATION_FAILED = "authentication_failed"
        BRUTE_FORCE_ATTACK = "brute_force_attack"
        UNAUTHORIZED_ACCESS = "unauthorized_access"
        RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
        DATA_BREACH = "data_breach"
    
    class ThreatLevel(Enum):
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"

class TestSecurityAuditLogger:
    """Test suite for Security Audit Logger"""
    
    @pytest_asyncio.fixture
    async def audit_logger(self):
        """Create audit logger instance for testing"""
        logger = SecurityAuditLogger()
        
        # Mock Redis connection
        logger.redis_client = AsyncMock()
        logger.redis_client.get = AsyncMock(return_value=None)
        logger.redis_client.set = AsyncMock(return_value=True)
        logger.redis_client.lpush = AsyncMock(return_value=True)
        logger.redis_client.lrange = AsyncMock(return_value=[])
        logger.redis_client.incr = AsyncMock(return_value=1)
        logger.redis_client.expire = AsyncMock(return_value=True)
        logger.redis_client.exists = AsyncMock(return_value=False)
        
        # Mock database connection
        logger.db_session = AsyncMock()
        
        return logger
    
    @pytest_asyncio.fixture
    def sample_security_event(self):
        """Sample security event for testing"""
        return {
            "event": SecurityEvent.AUTHENTICATION_SUCCESS,
            "user_id": "user-123",
            "source_ip": "192.168.1.100",
            "endpoint": "/api/login",
            "method": "POST",
            "threat_level": ThreatLevel.LOW,
            "details": "User logged in successfully",
            "user_agent": "Mozilla/5.0 Test Browser",
            "session_id": "session-456"
        }

class TestSecurityEventLogging:
    """Test security event logging functionality"""
    
    async def test_log_security_event_success(self, audit_logger, sample_security_event):
        """Test successful security event logging"""
        
        result = await audit_logger.log_security_event(**sample_security_event)
        
        assert result["success"] is True
        assert "event_id" in result
        
        # Verify Redis operations
        audit_logger.redis_client.lpush.assert_called()
        audit_logger.redis_client.incr.assert_called()
    
    async def test_log_security_event_with_correlation_id(self, audit_logger, sample_security_event):
        """Test logging with correlation ID"""
        
        correlation_id = str(uuid.uuid4())
        sample_security_event["correlation_id"] = correlation_id
        
        result = await audit_logger.log_security_event(**sample_security_event)
        
        assert result["success"] is True
        
        # Verify correlation ID was included
        call_args = audit_logger.redis_client.lpush.call_args
        logged_data = json.loads(call_args[0][1])
        assert logged_data["correlation_id"] == correlation_id
    
    async def test_log_high_severity_event(self, audit_logger):
        """Test logging high severity security event"""
        
        high_severity_event = {
            "event": SecurityEvent.BRUTE_FORCE_ATTACK,
            "source_ip": "192.168.1.100",
            "threat_level": ThreatLevel.CRITICAL,
            "details": "Multiple failed login attempts detected"
        }
        
        result = await audit_logger.log_security_event(**high_severity_event)
        
        assert result["success"] is True
        
        # Verify alert was triggered for high severity
        audit_logger.redis_client.lpush.assert_called()
    
    async def test_log_event_with_metadata(self, audit_logger):
        """Test logging event with additional metadata"""
        
        event_with_metadata = {
            "event": SecurityEvent.UNAUTHORIZED_ACCESS,
            "source_ip": "192.168.1.100",
            "threat_level": ThreatLevel.HIGH,
            "details": "Unauthorized access attempt",
            "metadata": {
                "attempted_resource": "/admin/users",
                "user_role": "guest",
                "required_role": "admin"
            }
        }
        
        result = await audit_logger.log_security_event(**event_with_metadata)
        
        assert result["success"] is True
        
        # Verify metadata was included
        call_args = audit_logger.redis_client.lpush.call_args
        logged_data = json.loads(call_args[0][1])
        assert "metadata" in logged_data
        assert logged_data["metadata"]["attempted_resource"] == "/admin/users"

class TestThreatDetection:
    """Test threat detection and analysis"""
    
    async def test_detect_brute_force_attack(self, audit_logger):
        """Test brute force attack detection"""
        
        source_ip = "192.168.1.100"
        
        # Mock failed login attempts
        failed_attempts = [
            json.dumps({
                "event_type": SecurityEvent.AUTHENTICATION_FAILED.value,
                "source_ip": source_ip,
                "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=i)).isoformat()
            })
            for i in range(10)  # 10 failed attempts
        ]
        
        audit_logger.redis_client.lrange = AsyncMock(return_value=failed_attempts)
        
        threat_analysis = await audit_logger.analyze_threats(source_ip)
        
        assert threat_analysis["threat_level"] >= ThreatLevel.HIGH.value
        assert any("brute force" in indicator.lower() for indicator in threat_analysis["indicators"])
    
    async def test_detect_rate_limit_violations(self, audit_logger):
        """Test rate limit violation detection"""
        
        source_ip = "192.168.1.100"
        
        # Mock rate limit violations
        violations = [
            json.dumps({
                "event_type": SecurityEvent.RATE_LIMIT_EXCEEDED.value,
                "source_ip": source_ip,
                "timestamp": (datetime.now(timezone.utc) - timedelta(seconds=i*10)).isoformat()
            })
            for i in range(20)  # 20 violations in short time
        ]
        
        audit_logger.redis_client.lrange = AsyncMock(return_value=violations)
        
        threat_analysis = await audit_logger.analyze_threats(source_ip)
        
        assert threat_analysis["threat_level"] >= ThreatLevel.MEDIUM.value
        assert any("rate limit" in indicator.lower() for indicator in threat_analysis["indicators"])
    
    async def test_detect_suspicious_activity_patterns(self, audit_logger):
        """Test detection of suspicious activity patterns"""
        
        source_ip = "192.168.1.100"
        
        # Mock suspicious patterns: accessing admin endpoints without authorization
        suspicious_events = [
            json.dumps({
                "event_type": SecurityEvent.UNAUTHORIZED_ACCESS.value,
                "source_ip": source_ip,
                "endpoint": "/admin/users",
                "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=i)).isoformat()
            })
            for i in range(5)
        ]
        
        audit_logger.redis_client.lrange = AsyncMock(return_value=suspicious_events)
        
        threat_analysis = await audit_logger.analyze_threats(source_ip)
        
        assert threat_analysis["threat_level"] >= ThreatLevel.MEDIUM.value
        assert any("unauthorized" in indicator.lower() for indicator in threat_analysis["indicators"])
    
    async def test_calculate_threat_score(self, audit_logger):
        """Test threat score calculation"""
        
        # Test different event types and their scores
        test_events = [
            (SecurityEvent.AUTHENTICATION_FAILED, ThreatLevel.LOW, 10),
            (SecurityEvent.BRUTE_FORCE_ATTACK, ThreatLevel.CRITICAL, 100),
            (SecurityEvent.UNAUTHORIZED_ACCESS, ThreatLevel.HIGH, 75),
            (SecurityEvent.RATE_LIMIT_EXCEEDED, ThreatLevel.MEDIUM, 25)
        ]
        
        for event, threat_level, expected_min_score in test_events:
            score = await audit_logger._calculate_threat_score(event, threat_level, {})
            assert score >= expected_min_score
    
    async def test_threat_score_aggregation(self, audit_logger):
        """Test threat score aggregation over time"""
        
        source_ip = "192.168.1.100"
        
        # Mock multiple events with different scores
        audit_logger.redis_client.get = AsyncMock(return_value="50")  # Existing score
        audit_logger.redis_client.set = AsyncMock(return_value=True)
        
        # Add new threat event
        new_score = await audit_logger._update_threat_score(
            source_ip, SecurityEvent.UNAUTHORIZED_ACCESS, ThreatLevel.HIGH
        )
        
        assert new_score > 50  # Should increase from existing score
        audit_logger.redis_client.set.assert_called()

class TestSecurityMetrics:
    """Test security metrics collection and analysis"""
    
    async def test_collect_security_metrics(self, audit_logger):
        """Test security metrics collection"""
        
        # Mock Redis data for metrics
        audit_logger.redis_client.get = AsyncMock(side_effect=lambda key: {
            "metrics:events:total": "100",
            "metrics:events:high_severity": "15",
            "metrics:threats:active": "5",
            "metrics:users:blocked": "3"
        }.get(key, "0"))
        
        metrics = await audit_logger.get_security_metrics()
        
        assert "total_events" in metrics
        assert "high_severity_events" in metrics
        assert "active_threats" in metrics
        assert "blocked_users" in metrics
        assert metrics["total_events"] == 100
        assert metrics["high_severity_events"] == 15
    
    async def test_metrics_time_series(self, audit_logger):
        """Test time series metrics collection"""
        
        # Mock time series data
        time_series_data = [
            json.dumps({
                "timestamp": "2024-01-01T10:00:00Z",
                "event_count": 10,
                "threat_level": "medium"
            }),
            json.dumps({
                "timestamp": "2024-01-01T11:00:00Z",
                "event_count": 15,
                "threat_level": "high"
            })
        ]
        
        audit_logger.redis_client.lrange = AsyncMock(return_value=time_series_data)
        
        metrics = await audit_logger.get_time_series_metrics(hours=24)
        
        assert len(metrics) == 2
        assert metrics[0]["event_count"] == 10
        assert metrics[1]["event_count"] == 15
    
    async def test_security_statistics(self, audit_logger):
        """Test security statistics generation"""
        
        # Mock various statistics
        audit_logger.redis_client.get = AsyncMock(side_effect=lambda key: {
            "stats:events:authentication_failed": "25",
            "stats:events:authentication_success": "150",
            "stats:events:unauthorized_access": "8",
            "stats:ips:blocked": "12",
            "stats:users:mfa_enabled": "45"
        }.get(key, "0"))
        
        stats = await audit_logger.get_security_statistics()
        
        assert "authentication_stats" in stats
        assert "access_stats" in stats
        assert "security_measures" in stats
        assert stats["authentication_stats"]["failed_attempts"] == 25
        assert stats["authentication_stats"]["successful_logins"] == 150

class TestAlertSystem:
    """Test security alert system"""
    
    async def test_trigger_security_alert(self, audit_logger):
        """Test security alert triggering"""
        
        alert_data = {
            "alert_type": "CRITICAL_THREAT",
            "source_ip": "192.168.1.100",
            "threat_level": ThreatLevel.CRITICAL,
            "description": "Multiple unauthorized access attempts detected"
        }
        
        audit_logger.redis_client.lpush = AsyncMock(return_value=True)
        audit_logger.redis_client.publish = AsyncMock(return_value=True)
        
        result = await audit_logger.trigger_security_alert(**alert_data)
        
        assert result["success"] is True
        assert "alert_id" in result
        
        # Verify alert was stored and published
        audit_logger.redis_client.lpush.assert_called()
        audit_logger.redis_client.publish.assert_called()
    
    async def test_alert_deduplication(self, audit_logger):
        """Test alert deduplication to prevent spam"""
        
        alert_data = {
            "alert_type": "BRUTE_FORCE",
            "source_ip": "192.168.1.100",
            "threat_level": ThreatLevel.HIGH,
            "description": "Brute force attack detected"
        }
        
        # Mock existing recent alert
        audit_logger.redis_client.exists = AsyncMock(return_value=True)
        
        result = await audit_logger.trigger_security_alert(**alert_data)
        
        # Should not create duplicate alert
        assert result["success"] is False
        assert "duplicate" in result["message"].lower()
    
    async def test_escalation_rules(self, audit_logger):
        """Test alert escalation rules"""
        
        # Critical events should trigger immediate escalation
        critical_alert = {
            "alert_type": "SYSTEM_COMPROMISE",
            "threat_level": ThreatLevel.CRITICAL,
            "description": "Potential system compromise detected"
        }
        
        audit_logger.redis_client.exists = AsyncMock(return_value=False)
        audit_logger.redis_client.lpush = AsyncMock(return_value=True)
        audit_logger.redis_client.publish = AsyncMock(return_value=True)
        
        result = await audit_logger.trigger_security_alert(**critical_alert)
        
        assert result["success"] is True
        assert result["escalated"] is True
        
        # Verify escalation channels were notified
        publish_calls = audit_logger.redis_client.publish.call_args_list
        assert len(publish_calls) >= 2  # Normal and escalation channels

class TestIPBlacklisting:
    """Test IP blacklisting functionality"""
    
    async def test_automatic_ip_blocking(self, audit_logger):
        """Test automatic IP blocking based on threat score"""
        
        source_ip = "192.168.1.100"
        high_threat_score = 95
        
        audit_logger.redis_client.get = AsyncMock(return_value=str(high_threat_score))
        audit_logger.redis_client.set = AsyncMock(return_value=True)
        audit_logger.redis_client.expire = AsyncMock(return_value=True)
        
        result = await audit_logger.check_and_block_ip(source_ip)
        
        assert result["blocked"] is True
        assert result["reason"] == "high_threat_score"
        
        # Verify IP was added to blacklist
        audit_logger.redis_client.set.assert_called()
    
    async def test_ip_whitelist_protection(self, audit_logger):
        """Test that whitelisted IPs are not blocked"""
        
        whitelisted_ip = "127.0.0.1"
        
        # Mock high threat score for whitelisted IP
        audit_logger.redis_client.get = AsyncMock(return_value="100")
        
        result = await audit_logger.check_and_block_ip(whitelisted_ip)
        
        assert result["blocked"] is False
        assert result["reason"] == "whitelisted"
    
    async def test_temporary_blocking(self, audit_logger):
        """Test temporary IP blocking"""
        
        source_ip = "192.168.1.100"
        block_duration = 3600  # 1 hour
        
        audit_logger.redis_client.set = AsyncMock(return_value=True)
        audit_logger.redis_client.expire = AsyncMock(return_value=True)
        
        await audit_logger.block_ip_temporarily(source_ip, block_duration, "Suspicious activity")
        
        # Verify blocking with expiration
        audit_logger.redis_client.set.assert_called()
        audit_logger.redis_client.expire.assert_called_with(f"blocked_ip:{source_ip}", block_duration)

class TestDataRetention:
    """Test data retention and cleanup"""
    
    async def test_cleanup_old_events(self, audit_logger):
        """Test cleanup of old security events"""
        
        # Mock old events beyond retention period
        old_events = [
            json.dumps({
                "event_id": f"event-{i}",
                "timestamp": (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
            })
            for i in range(10)
        ]
        
        recent_events = [
            json.dumps({
                "event_id": f"event-recent-{i}",
                "timestamp": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
            })
            for i in range(5)
        ]
        
        all_events = old_events + recent_events
        audit_logger.redis_client.lrange = AsyncMock(return_value=all_events)
        audit_logger.redis_client.ltrim = AsyncMock(return_value=True)
        
        cleaned_count = await audit_logger.cleanup_old_events(retention_days=30)
        
        assert cleaned_count == 10  # Should clean 10 old events
        audit_logger.redis_client.ltrim.assert_called()
    
    async def test_archive_old_data(self, audit_logger):
        """Test archiving old security data"""
        
        audit_logger.db_session.execute = AsyncMock()
        audit_logger.db_session.commit = AsyncMock()
        
        # Mock events to archive
        events_to_archive = [
            {
                "event_id": f"event-{i}",
                "timestamp": datetime.now(timezone.utc) - timedelta(days=35),
                "event_type": "authentication_failed"
            }
            for i in range(5)
        ]
        
        result = await audit_logger.archive_old_data(events_to_archive)
        
        assert result["success"] is True
        assert result["archived_count"] == 5
        
        # Verify database operations
        audit_logger.db_session.execute.assert_called()
        audit_logger.db_session.commit.assert_called()

class TestSecurityReporting:
    """Test security reporting functionality"""
    
    async def test_generate_security_report(self, audit_logger):
        """Test security report generation"""
        
        # Mock data for report
        audit_logger.redis_client.get = AsyncMock(side_effect=lambda key: {
            "stats:events:total": "500",
            "stats:events:high_severity": "50",
            "stats:threats:blocked": "15",
            "stats:ips:blacklisted": "8"
        }.get(key, "0"))
        
        report_period = {
            "start_date": datetime.now(timezone.utc) - timedelta(days=7),
            "end_date": datetime.now(timezone.utc)
        }
        
        report = await audit_logger.generate_security_report(**report_period)
        
        assert "summary" in report
        assert "events" in report
        assert "threats" in report
        assert "recommendations" in report
        assert report["summary"]["total_events"] == 500
        assert report["summary"]["high_severity_events"] == 50
    
    async def test_compliance_report(self, audit_logger):
        """Test compliance report generation"""
        
        # Mock compliance-related data
        audit_logger.redis_client.lrange = AsyncMock(return_value=[
            json.dumps({
                "event_type": "data_access",
                "user_id": "user-123",
                "data_classification": "sensitive",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        ])
        
        compliance_report = await audit_logger.generate_compliance_report(
            start_date=datetime.now(timezone.utc) - timedelta(days=30),
            end_date=datetime.now(timezone.utc)
        )
        
        assert "data_access_events" in compliance_report
        assert "user_activities" in compliance_report
        assert "security_violations" in compliance_report
    
    async def test_threat_intelligence_report(self, audit_logger):
        """Test threat intelligence report"""
        
        # Mock threat data
        threat_data = [
            {
                "source_ip": "192.168.1.100",
                "threat_score": 85,
                "attack_types": ["brute_force", "unauthorized_access"],
                "first_seen": datetime.now(timezone.utc) - timedelta(hours=6),
                "last_seen": datetime.now(timezone.utc) - timedelta(minutes=30)
            }
        ]
        
        audit_logger.redis_client.hgetall = AsyncMock(return_value={
            "192.168.1.100": json.dumps(threat_data[0])
        })
        
        threat_report = await audit_logger.generate_threat_intelligence_report()
        
        assert "active_threats" in threat_report
        assert "threat_trends" in threat_report
        assert "mitigation_recommendations" in threat_report
        assert len(threat_report["active_threats"]) > 0

class TestPerformanceAndScaling:
    """Test performance and scaling aspects"""
    
    async def test_high_volume_event_logging(self, audit_logger):
        """Test logging performance with high volume events"""
        
        import asyncio
        
        # Mock Redis operations to be fast
        audit_logger.redis_client.lpush = AsyncMock(return_value=True)
        audit_logger.redis_client.incr = AsyncMock(return_value=1)
        
        # Test logging many events concurrently
        events = [
            {
                "event": SecurityEvent.AUTHENTICATION_SUCCESS,
                "user_id": f"user-{i}",
                "source_ip": f"192.168.1.{i % 255}",
                "threat_level": ThreatLevel.LOW,
                "details": f"Test event {i}"
            }
            for i in range(100)
        ]
        
        start_time = datetime.now()
        
        # Log events concurrently
        tasks = [audit_logger.log_security_event(**event) for event in events]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Verify all events were logged successfully
        successful_logs = sum(1 for result in results if isinstance(result, dict) and result.get("success"))
        assert successful_logs >= 90  # At least 90% success rate
        
        # Performance check - should handle 100 events quickly
        assert duration < 5.0  # Should complete in under 5 seconds
    
    async def test_memory_efficient_log_storage(self, audit_logger):
        """Test memory-efficient log storage"""
        
        # Test with large event data
        large_event = {
            "event": SecurityEvent.DATA_BREACH,
            "source_ip": "192.168.1.100",
            "threat_level": ThreatLevel.CRITICAL,
            "details": "Large event data " * 1000,  # Large details
            "metadata": {f"key_{i}": f"value_{i}" for i in range(100)}  # Large metadata
        }
        
        audit_logger.redis_client.lpush = AsyncMock(return_value=True)
        
        result = await audit_logger.log_security_event(**large_event)
        
        assert result["success"] is True
        
        # Verify data was compressed or truncated appropriately
        call_args = audit_logger.redis_client.lpush.call_args
        logged_data = call_args[0][1]
        
        # Should not be excessively large
        assert len(logged_data) < 100000  # Less than 100KB per event

class TestErrorHandling:
    """Test error handling in audit logger"""
    
    async def test_redis_connection_failure(self, audit_logger, sample_security_event):
        """Test handling of Redis connection failures"""
        
        # Mock Redis failure
        audit_logger.redis_client.lpush = AsyncMock(side_effect=Exception("Redis connection failed"))
        
        result = await audit_logger.log_security_event(**sample_security_event)
        
        # Should handle gracefully
        assert result["success"] is False
        assert "error" in result["message"].lower()
    
    async def test_database_failure_during_archiving(self, audit_logger):
        """Test handling of database failures during archiving"""
        
        # Mock database failure
        audit_logger.db_session.execute = AsyncMock(side_effect=Exception("Database error"))
        
        events_to_archive = [{"event_id": "test-event"}]
        result = await audit_logger.archive_old_data(events_to_archive)
        
        assert result["success"] is False
        assert "error" in result["message"].lower()
    
    async def test_malformed_event_data(self, audit_logger):
        """Test handling of malformed event data"""
        
        malformed_events = [
            {},  # Empty event
            {"event": "invalid_event_type"},  # Invalid event type
            {"event": SecurityEvent.AUTHENTICATION_SUCCESS},  # Missing required fields
        ]
        
        for event in malformed_events:
            result = await audit_logger.log_security_event(**event)
            # Should either succeed with defaults or fail gracefully
            assert isinstance(result, dict)
            assert "success" in result

if __name__ == "__main__":
    pytest.main([__file__, "-v"])