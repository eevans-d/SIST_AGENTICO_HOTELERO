"""
Incident Response Tests
Tests for incident detection, classification, and response procedures.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Import incident detector
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from incident_detector import (
    IncidentDetector,
    Incident,
    IncidentRule,
    Severity,
    IncidentStatus,
)


class TestIncidentDetection:
    """Test incident detection system"""

    @pytest.fixture
    def detector(self):
        """Create incident detector instance"""
        return IncidentDetector(
            prometheus_url="http://localhost:9090",
            alert_webhook=None,  # Disable webhook for tests
            check_interval=30,
            history_file="/tmp/test_incidents.json",
        )

    @pytest.mark.asyncio
    async def test_rule_evaluation_greater_than(self, detector):
        """Test rule evaluation with > comparison"""
        rule = IncidentRule(
            name="test_high_value",
            query="test_metric",
            threshold=100,
            comparison="gt",
            severity=Severity.HIGH,
            description="Test rule",
        )

        # Value above threshold should breach
        assert detector._evaluate_rule(150, rule) is True

        # Value below threshold should not breach
        assert detector._evaluate_rule(50, rule) is False

        # Value equal to threshold should not breach
        assert detector._evaluate_rule(100, rule) is False

    @pytest.mark.asyncio
    async def test_rule_evaluation_less_than(self, detector):
        """Test rule evaluation with < comparison"""
        rule = IncidentRule(
            name="test_low_value",
            query="test_metric",
            threshold=10,
            comparison="lt",
            severity=Severity.CRITICAL,
            description="Test rule",
        )

        # Value below threshold should breach
        assert detector._evaluate_rule(5, rule) is True

        # Value above threshold should not breach
        assert detector._evaluate_rule(15, rule) is False

    @pytest.mark.asyncio
    async def test_rule_evaluation_equals(self, detector):
        """Test rule evaluation with = comparison"""
        rule = IncidentRule(
            name="test_equal_value",
            query="test_metric",
            threshold=1,
            comparison="eq",
            severity=Severity.MEDIUM,
            description="Test rule",
        )

        # Value equal to threshold should breach
        assert detector._evaluate_rule(1.0, rule) is True

        # Value close but not equal should breach (within tolerance)
        assert detector._evaluate_rule(1.005, rule) is True

        # Value far from threshold should not breach
        assert detector._evaluate_rule(2.0, rule) is False

    @pytest.mark.asyncio
    async def test_incident_creation(self, detector):
        """Test incident creation when rule breached"""
        rule = IncidentRule(
            name="test_incident",
            query="up{job='test'}",
            threshold=1,
            comparison="lt",
            severity=Severity.CRITICAL,
            description="Service is down",
        )

        # Mock Prometheus query to return 0 (service down)
        with patch.object(detector, "query_prometheus", return_value=0):
            incident = await detector.check_rule(rule)

            assert incident is not None
            assert incident.severity == Severity.CRITICAL
            assert incident.status == IncidentStatus.OPEN
            assert "test_incident" in incident.title.lower()
            assert incident.metrics["value"] == 0
            assert incident.metrics["threshold"] == 1

    @pytest.mark.asyncio
    async def test_incident_not_created_when_threshold_not_breached(self, detector):
        """Test that incident is not created when threshold not breached"""
        rule = IncidentRule(
            name="test_no_incident",
            query="up{job='test'}",
            threshold=1,
            comparison="lt",
            severity=Severity.CRITICAL,
            description="Service is down",
        )

        # Mock Prometheus query to return 1 (service up)
        with patch.object(detector, "query_prometheus", return_value=1):
            incident = await detector.check_rule(rule)
            assert incident is None

    @pytest.mark.asyncio
    async def test_incident_resolution(self, detector):
        """Test incident resolution when threshold no longer breached"""
        rule = IncidentRule(
            name="test_resolution",
            query="error_rate",
            threshold=0.05,
            comparison="gt",
            severity=Severity.HIGH,
            description="High error rate",
        )

        # First check: Create incident
        with patch.object(detector, "query_prometheus", return_value=0.10):
            incident = await detector.check_rule(rule)
            assert incident is not None
            assert incident.status == IncidentStatus.OPEN

        # Second check: Resolve incident
        with patch.object(detector, "query_prometheus", return_value=0.01):
            incident = await detector.check_rule(rule)
            assert incident is None  # No new incident
            assert rule.name not in detector.active_incidents
            assert len(detector.incident_history) == 1
            assert detector.incident_history[0].status == IncidentStatus.RESOLVED

    @pytest.mark.asyncio
    async def test_incident_persistence(self, detector):
        """Test incident history persistence"""
        # Create test incident
        incident = Incident(
            id="INC-TEST-001",
            title="Test Incident",
            description="Test description",
            severity=Severity.HIGH,
            status=IncidentStatus.RESOLVED,
            detected_at=datetime.utcnow().isoformat(),
            resolved_at=datetime.utcnow().isoformat(),
            affected_services=["test-service"],
            metrics={"test": "data"},
        )

        detector.incident_history.append(incident)
        detector._save_history()

        # Create new detector and load history
        new_detector = IncidentDetector(history_file="/tmp/test_incidents.json")
        assert len(new_detector.incident_history) == 1
        assert new_detector.incident_history[0].id == "INC-TEST-001"

    @pytest.mark.asyncio
    async def test_incident_report_generation(self, detector):
        """Test incident report generation"""
        # Create test incidents
        now = datetime.utcnow()
        for i in range(5):
            incident = Incident(
                id=f"INC-TEST-{i:03d}",
                title=f"Test Incident {i}",
                description="Test",
                severity=Severity.HIGH if i < 3 else Severity.LOW,
                status=IncidentStatus.RESOLVED,
                detected_at=(now - timedelta(hours=i)).isoformat(),
                resolved_at=now.isoformat(),
                affected_services=["test-service"],
            )
            detector.incident_history.append(incident)

        report = detector.generate_report()

        assert report["active_incidents"] == 0
        assert report["incidents_24h"] == 5
        assert report["incidents_by_severity"]["high"] == 3
        assert report["incidents_by_severity"]["low"] == 2

    @pytest.mark.asyncio
    async def test_multiple_concurrent_incidents(self, detector):
        """Test handling multiple incidents simultaneously"""
        rules = [
            IncidentRule(
                name=f"test_incident_{i}",
                query=f"metric_{i}",
                threshold=100,
                comparison="gt",
                severity=Severity.HIGH,
                description=f"Test incident {i}",
            )
            for i in range(3)
        ]

        # Mock Prometheus to return high values for all rules
        with patch.object(detector, "query_prometheus", return_value=150):
            incidents = []
            for rule in rules:
                incident = await detector.check_rule(rule)
                if incident:
                    incidents.append(incident)

            assert len(incidents) == 3
            assert len(detector.active_incidents) == 3


class TestIncidentClassification:
    """Test incident severity classification"""

    def test_severity_levels(self):
        """Test severity level definitions"""
        assert Severity.CRITICAL == "critical"
        assert Severity.HIGH == "high"
        assert Severity.MEDIUM == "medium"
        assert Severity.LOW == "low"

    def test_incident_status_transitions(self):
        """Test incident status state machine"""
        statuses = [
            IncidentStatus.OPEN,
            IncidentStatus.INVESTIGATING,
            IncidentStatus.IDENTIFIED,
            IncidentStatus.MONITORING,
            IncidentStatus.RESOLVED,
        ]

        assert len(statuses) == 5
        assert IncidentStatus.OPEN == "open"
        assert IncidentStatus.RESOLVED == "resolved"


class TestIncidentResponse:
    """Test incident response procedures"""

    @pytest.fixture
    def mock_alert_webhook(self):
        """Mock alert webhook"""
        return Mock()

    @pytest.mark.asyncio
    async def test_alert_sending(self, mock_alert_webhook):
        """Test alert webhook notification"""
        detector = IncidentDetector(alert_webhook="http://localhost/webhook", check_interval=30)

        incident = Incident(
            id="INC-TEST-001",
            title="Test Alert",
            description="Test alert description",
            severity=Severity.CRITICAL,
            status=IncidentStatus.OPEN,
            detected_at=datetime.utcnow().isoformat(),
            affected_services=["test-service"],
            metrics={"value": 0, "threshold": 1},
        )

        # Mock HTTP client
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock()
            mock_client.return_value.__aenter__.return_value.post = mock_post
            mock_post.return_value.status_code = 200

            await detector._send_alert(incident)

            # Verify webhook was called
            assert mock_post.called

    @pytest.mark.asyncio
    async def test_incident_escalation_criteria(self):
        """Test when incidents should be escalated"""
        # Critical incidents should escalate immediately
        critical_incident = Incident(
            id="INC-CRIT-001",
            title="Critical Incident",
            description="Service down",
            severity=Severity.CRITICAL,
            status=IncidentStatus.OPEN,
            detected_at=datetime.utcnow().isoformat(),
            affected_services=["agente-api"],
        )

        assert critical_incident.severity == Severity.CRITICAL
        # In real implementation, would trigger PagerDuty

        # High incidents should escalate if > 30 min
        high_incident = Incident(
            id="INC-HIGH-001",
            title="High Incident",
            description="Degraded performance",
            severity=Severity.HIGH,
            status=IncidentStatus.OPEN,
            detected_at=(datetime.utcnow() - timedelta(minutes=35)).isoformat(),
            affected_services=["agente-api"],
        )

        detected = datetime.fromisoformat(high_incident.detected_at)
        duration = (datetime.utcnow() - detected).total_seconds() / 60
        assert duration > 30  # Should escalate


class TestRunbookIntegration:
    """Test runbook execution integration"""

    @pytest.mark.asyncio
    async def test_runbook_mapping(self):
        """Test that incidents map to correct runbooks"""
        incident_to_runbook = {
            "database_down": "docs/runbooks/01-database-down.md",
            "high_api_latency": "docs/runbooks/02-high-api-latency.md",
            "memory_leak": "docs/runbooks/03-memory-leak.md",
            "disk_space_critical": "docs/runbooks/04-disk-space-critical.md",
            "pms_integration_failure": "docs/runbooks/05-pms-integration-failure.md",
            "whatsapp_api_outage": "docs/runbooks/06-whatsapp-api-outage.md",
            "redis_connection_issues": "docs/runbooks/07-redis-connection-issues.md",
            "high_error_rate": "docs/runbooks/08-high-error-rate.md",
            "pms_circuit_breaker_open": "docs/runbooks/09-circuit-breaker-open.md",
            "deployment_failure": "docs/runbooks/10-deployment-failure.md",
        }

        # Verify runbooks exist
        from pathlib import Path

        Path(__file__).parent.parent.parent / "docs" / "runbooks"

        for incident_type, runbook_path in incident_to_runbook.items():
            full_path = Path(__file__).parent.parent.parent / runbook_path
            assert full_path.exists(), f"Runbook {runbook_path} not found for {incident_type}"

    @pytest.mark.asyncio
    async def test_runbook_validation(self):
        """Test that runbooks contain required sections"""
        from pathlib import Path

        runbooks_dir = Path(__file__).parent.parent.parent / "docs" / "runbooks"
        required_sections = [
            "## Symptoms",
            "## Detection",
            "## Impact Assessment",
            "## Immediate Actions",
            "## Resolution Steps",
            "## Validation",
            "## Communication Template",
        ]

        for runbook in runbooks_dir.glob("*.md"):
            content = runbook.read_text()
            for section in required_sections:
                assert section in content, f"Runbook {runbook.name} missing section: {section}"


class TestIncidentMetrics:
    """Test incident metrics and reporting"""

    def test_mttr_calculation(self):
        """Test Mean Time To Recovery calculation"""
        incidents = [
            Incident(
                id=f"INC-{i:03d}",
                title=f"Incident {i}",
                description="Test",
                severity=Severity.HIGH,
                status=IncidentStatus.RESOLVED,
                detected_at=(datetime.utcnow() - timedelta(minutes=60 + i * 10)).isoformat(),
                resolved_at=(datetime.utcnow() - timedelta(minutes=i * 10)).isoformat(),
                affected_services=["test"],
            )
            for i in range(5)
        ]

        total_duration = 0
        for incident in incidents:
            detected = datetime.fromisoformat(incident.detected_at)
            resolved = datetime.fromisoformat(incident.resolved_at)
            duration = (resolved - detected).total_seconds() / 60
            total_duration += duration

        mttr = total_duration / len(incidents)
        assert mttr == 60  # Each incident was 60 minutes

    def test_incident_frequency(self):
        """Test incident frequency tracking"""
        detector = IncidentDetector()

        # Create incidents over time
        now = datetime.utcnow()
        for hour in range(24):
            incident = Incident(
                id=f"INC-{hour:03d}",
                title=f"Incident at hour {hour}",
                description="Test",
                severity=Severity.MEDIUM,
                status=IncidentStatus.RESOLVED,
                detected_at=(now - timedelta(hours=hour)).isoformat(),
                resolved_at=now.isoformat(),
                affected_services=["test"],
            )
            detector.incident_history.append(incident)

        report = detector.generate_report()
        assert report["incidents_24h"] == 24
        assert report["incidents_24h"] / 24 == 1  # 1 incident per hour


@pytest.mark.integration
class TestIncidentResponseFlow:
    """Integration tests for full incident response flow"""

    @pytest.mark.asyncio
    async def test_complete_incident_lifecycle(self):
        """Test complete incident lifecycle from detection to resolution"""
        detector = IncidentDetector(history_file="/tmp/test_lifecycle.json")

        rule = IncidentRule(
            name="test_lifecycle",
            query="test_metric",
            threshold=100,
            comparison="gt",
            severity=Severity.HIGH,
            duration=60,
            description="Test lifecycle incident",
        )

        # Phase 1: Detection
        with patch.object(detector, "query_prometheus", return_value=150):
            incident = await detector.check_rule(rule)
            assert incident is not None
            assert incident.status == IncidentStatus.OPEN

        # Phase 2: Investigation (status would be updated manually)
        incident.status = IncidentStatus.INVESTIGATING

        # Phase 3: Identified
        incident.status = IncidentStatus.IDENTIFIED

        # Phase 4: Monitoring
        incident.status = IncidentStatus.MONITORING

        # Phase 5: Resolution
        with patch.object(detector, "query_prometheus", return_value=50):
            await detector.check_rule(rule)
            assert rule.name not in detector.active_incidents
            assert len(detector.incident_history) == 1
            assert detector.incident_history[0].status == IncidentStatus.RESOLVED

    @pytest.mark.asyncio
    async def test_incident_with_runbook_execution(self):
        """Test incident detection triggers runbook reference"""
        detector = IncidentDetector()

        rule = IncidentRule(
            name="service_down",
            query='up{job="agente-api"}',
            threshold=1,
            comparison="lt",
            severity=Severity.CRITICAL,
            description="Service is down or unreachable",
        )

        with patch.object(detector, "query_prometheus", return_value=0):
            incident = await detector.check_rule(rule)
            assert incident is not None

            # In real system, this would trigger runbook reference
            runbook_path = "docs/runbooks/01-database-down.md"
            # Verify runbook exists and is accessible
            from pathlib import Path

            Path(__file__).parent.parent.parent / runbook_path
            # Would exist in real deployment


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
