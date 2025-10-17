#!/usr/bin/env python3
"""
Incident Detection System
Automated incident detection and alerting based on Prometheus metrics and health checks.

Features:
- Real-time metric monitoring
- Severity classification (critical, high, medium, low)
- Alert aggregation and deduplication
- Integration with Slack/PagerDuty
- Incident tracking and history
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import httpx
import os


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """Incident severity levels"""

    CRITICAL = "critical"  # Service down, data loss
    HIGH = "high"  # Degraded performance, high error rate
    MEDIUM = "medium"  # Minor issues, warnings
    LOW = "low"  # Informational


class IncidentStatus(str, Enum):
    """Incident status"""

    OPEN = "open"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"


@dataclass
class IncidentRule:
    """Incident detection rule"""

    name: str
    query: str  # PromQL query
    threshold: float
    comparison: str  # gt, lt, eq
    severity: Severity
    duration: int = 60  # seconds
    description: str = ""


@dataclass
class Incident:
    """Incident data model"""

    id: str
    title: str
    description: str
    severity: Severity
    status: IncidentStatus
    detected_at: str
    resolved_at: Optional[str] = None
    affected_services: List[str] = None
    metrics: Dict[str, Any] = None
    assignee: Optional[str] = None

    def __post_init__(self):
        if self.affected_services is None:
            self.affected_services = []
        if self.metrics is None:
            self.metrics = {}


class IncidentDetector:
    """Automated incident detection system"""

    def __init__(
        self,
        prometheus_url: str = "http://localhost:9090",
        alert_webhook: Optional[str] = None,
        check_interval: int = 30,
        history_file: str = ".incidents.json",
    ):
        self.prometheus_url = prometheus_url
        self.alert_webhook = alert_webhook or os.getenv("INCIDENT_WEBHOOK_URL")
        self.check_interval = check_interval
        self.history_file = Path(history_file)
        self.active_incidents: Dict[str, Incident] = {}
        self.incident_history: List[Incident] = []

        # Define detection rules
        self.rules = self._define_rules()

        # Load incident history
        self._load_history()

    def _define_rules(self) -> List[IncidentRule]:
        """Define incident detection rules"""
        return [
            # Critical: Service down
            IncidentRule(
                name="service_down",
                query='up{job="agente-api"}',
                threshold=1,
                comparison="lt",
                severity=Severity.CRITICAL,
                duration=60,
                description="Service is down or unreachable",
            ),
            # Critical: High error rate
            IncidentRule(
                name="high_error_rate",
                query='rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])',
                threshold=0.05,  # 5%
                comparison="gt",
                severity=Severity.CRITICAL,
                duration=120,
                description="Error rate exceeds 5%",
            ),
            # High: Database connection failures
            IncidentRule(
                name="database_connection_failures",
                query="rate(database_connection_errors_total[5m])",
                threshold=1,
                comparison="gt",
                severity=Severity.HIGH,
                duration=60,
                description="Database connection failures detected",
            ),
            # High: High latency P95
            IncidentRule(
                name="high_latency_p95",
                query="histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
                threshold=3,  # 3 seconds
                comparison="gt",
                severity=Severity.HIGH,
                duration=300,
                description="P95 latency exceeds 3 seconds",
            ),
            # High: Memory usage
            IncidentRule(
                name="high_memory_usage",
                query="process_resident_memory_bytes / 1024 / 1024 / 1024",  # GB
                threshold=2,  # 2GB
                comparison="gt",
                severity=Severity.HIGH,
                duration=300,
                description="Memory usage exceeds 2GB",
            ),
            # Medium: Redis connection issues
            IncidentRule(
                name="redis_connection_issues",
                query="redis_up",
                threshold=1,
                comparison="lt",
                severity=Severity.MEDIUM,
                duration=120,
                description="Redis connection issues",
            ),
            # Medium: PMS circuit breaker open
            IncidentRule(
                name="pms_circuit_breaker_open",
                query="pms_circuit_breaker_state",
                threshold=1,  # 1 = open
                comparison="eq",
                severity=Severity.MEDIUM,
                duration=180,
                description="PMS circuit breaker is open",
            ),
            # Medium: High CPU usage
            IncidentRule(
                name="high_cpu_usage",
                query="rate(process_cpu_seconds_total[5m]) * 100",
                threshold=80,  # 80%
                comparison="gt",
                severity=Severity.MEDIUM,
                duration=300,
                description="CPU usage exceeds 80%",
            ),
            # Low: Slow response time P50
            IncidentRule(
                name="slow_response_p50",
                query="histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
                threshold=1,  # 1 second
                comparison="gt",
                severity=Severity.LOW,
                duration=600,
                description="P50 response time exceeds 1 second",
            ),
            # Low: Low cache hit rate
            IncidentRule(
                name="low_cache_hit_rate",
                query="rate(redis_cache_hits_total[5m]) / (rate(redis_cache_hits_total[5m]) + rate(redis_cache_misses_total[5m]))",
                threshold=0.7,  # 70%
                comparison="lt",
                severity=Severity.LOW,
                duration=600,
                description="Cache hit rate below 70%",
            ),
        ]

    async def query_prometheus(self, query: str) -> Optional[float]:
        """Query Prometheus for metric value"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.prometheus_url}/api/v1/query", params={"query": query}, timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                if data["status"] != "success":
                    logger.error(f"Prometheus query failed: {data}")
                    return None

                result = data["data"]["result"]
                if not result:
                    return None

                # Get first result value
                value = float(result[0]["value"][1])
                return value

        except Exception as e:
            logger.error(f"Error querying Prometheus: {e}")
            return None

    def _evaluate_rule(self, value: float, rule: IncidentRule) -> bool:
        """Evaluate if rule threshold is breached"""
        if rule.comparison == "gt":
            return value > rule.threshold
        elif rule.comparison == "lt":
            return value < rule.threshold
        elif rule.comparison == "eq":
            return abs(value - rule.threshold) < 0.01
        return False

    async def check_rule(self, rule: IncidentRule) -> Optional[Incident]:
        """Check a single rule and return incident if breached"""
        value = await self.query_prometheus(rule.query)

        if value is None:
            return None

        is_breached = self._evaluate_rule(value, rule)

        if is_breached:
            # Check if incident already exists
            if rule.name in self.active_incidents:
                incident = self.active_incidents[rule.name]
                logger.info(f"Incident still active: {incident.title}")
                return incident

            # Create new incident
            incident = Incident(
                id=f"INC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{rule.name}",
                title=f"{rule.severity.value.upper()}: {rule.name.replace('_', ' ').title()}",
                description=rule.description,
                severity=rule.severity,
                status=IncidentStatus.OPEN,
                detected_at=datetime.utcnow().isoformat(),
                affected_services=["agente-api"],
                metrics={
                    "query": rule.query,
                    "value": value,
                    "threshold": rule.threshold,
                    "comparison": rule.comparison,
                },
            )

            self.active_incidents[rule.name] = incident
            logger.warning(f"🚨 NEW INCIDENT: {incident.title} (value: {value}, threshold: {rule.threshold})")

            return incident

        else:
            # Check if we need to resolve an active incident
            if rule.name in self.active_incidents:
                incident = self.active_incidents[rule.name]
                incident.status = IncidentStatus.RESOLVED
                incident.resolved_at = datetime.utcnow().isoformat()

                self.incident_history.append(incident)
                del self.active_incidents[rule.name]

                logger.info(f"✅ INCIDENT RESOLVED: {incident.title}")

                # Alert about resolution
                await self._send_alert(incident, resolved=True)

        return None

    async def _send_alert(self, incident: Incident, resolved: bool = False):
        """Send alert to webhook (Slack, PagerDuty, etc.)"""
        if not self.alert_webhook:
            return

        try:
            color = {
                Severity.CRITICAL: "#FF0000",
                Severity.HIGH: "#FF8800",
                Severity.MEDIUM: "#FFAA00",
                Severity.LOW: "#00AA00",
            }.get(incident.severity, "#808080")

            if resolved:
                title = f"✅ Incident Resolved: {incident.title}"
                color = "#00AA00"
            else:
                title = f"🚨 New Incident: {incident.title}"

            # Slack webhook format
            payload = {
                "text": title,
                "attachments": [
                    {
                        "color": color,
                        "fields": [
                            {"title": "ID", "value": incident.id, "short": True},
                            {"title": "Severity", "value": incident.severity.value.upper(), "short": True},
                            {"title": "Status", "value": incident.status.value, "short": True},
                            {"title": "Detected At", "value": incident.detected_at, "short": True},
                            {"title": "Description", "value": incident.description, "short": False},
                            {
                                "title": "Affected Services",
                                "value": ", ".join(incident.affected_services),
                                "short": False,
                            },
                        ],
                    }
                ],
            }

            if incident.metrics:
                payload["attachments"][0]["fields"].append(
                    {
                        "title": "Metrics",
                        "value": f"Value: {incident.metrics.get('value', 'N/A')}, Threshold: {incident.metrics.get('threshold', 'N/A')}",
                        "short": False,
                    }
                )

            async with httpx.AsyncClient() as client:
                response = await client.post(self.alert_webhook, json=payload, timeout=10.0)
                response.raise_for_status()
                logger.info(f"Alert sent successfully for incident {incident.id}")

        except Exception as e:
            logger.error(f"Error sending alert: {e}")

    async def run_checks(self):
        """Run all detection rules once"""
        logger.info(f"Running incident detection checks ({len(self.rules)} rules)")

        new_incidents = []
        for rule in self.rules:
            incident = await self.check_rule(rule)
            if incident and incident.id not in [i.id for i in new_incidents]:
                new_incidents.append(incident)

        # Send alerts for new incidents
        for incident in new_incidents:
            await self._send_alert(incident)

        # Save history
        self._save_history()

        return new_incidents

    async def monitor(self):
        """Continuously monitor for incidents"""
        logger.info(f"Starting incident monitoring (interval: {self.check_interval}s)")

        while True:
            try:
                await self.run_checks()
                await asyncio.sleep(self.check_interval)
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)

    def _load_history(self):
        """Load incident history from file"""
        if not self.history_file.exists():
            return

        try:
            with open(self.history_file, "r") as f:
                data = json.load(f)
                self.incident_history = [Incident(**incident) for incident in data]
            logger.info(f"Loaded {len(self.incident_history)} incidents from history")
        except Exception as e:
            logger.error(f"Error loading incident history: {e}")

    def _save_history(self):
        """Save incident history to file"""
        try:
            with open(self.history_file, "w") as f:
                json.dump([asdict(incident) for incident in self.incident_history], f, indent=2)
        except Exception as e:
            logger.error(f"Error saving incident history: {e}")

    def get_active_incidents(self) -> List[Incident]:
        """Get list of active incidents"""
        return list(self.active_incidents.values())

    def get_incident_history(self, severity: Optional[Severity] = None, limit: int = 10) -> List[Incident]:
        """Get incident history with optional filtering"""
        history = self.incident_history

        if severity:
            history = [i for i in history if i.severity == severity]

        return sorted(history, key=lambda x: x.detected_at, reverse=True)[:limit]

    def generate_report(self) -> Dict[str, Any]:
        """Generate incident report"""
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        recent_incidents = [i for i in self.incident_history if datetime.fromisoformat(i.detected_at) > last_24h]

        weekly_incidents = [i for i in self.incident_history if datetime.fromisoformat(i.detected_at) > last_7d]

        return {
            "active_incidents": len(self.active_incidents),
            "active_critical": len([i for i in self.active_incidents.values() if i.severity == Severity.CRITICAL]),
            "incidents_24h": len(recent_incidents),
            "incidents_7d": len(weekly_incidents),
            "incidents_by_severity": {
                "critical": len([i for i in weekly_incidents if i.severity == Severity.CRITICAL]),
                "high": len([i for i in weekly_incidents if i.severity == Severity.HIGH]),
                "medium": len([i for i in weekly_incidents if i.severity == Severity.MEDIUM]),
                "low": len([i for i in weekly_incidents if i.severity == Severity.LOW]),
            },
            "active_incidents_list": [asdict(i) for i in self.get_active_incidents()],
            "recent_incidents": [asdict(i) for i in recent_incidents],
        }


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Incident Detection System")
    parser.add_argument(
        "--prometheus-url", default=os.getenv("PROMETHEUS_URL", "http://localhost:9090"), help="Prometheus server URL"
    )
    parser.add_argument(
        "--webhook-url", default=os.getenv("INCIDENT_WEBHOOK_URL"), help="Alert webhook URL (Slack, PagerDuty)"
    )
    parser.add_argument("--interval", type=int, default=30, help="Check interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run checks once and exit")
    parser.add_argument("--report", action="store_true", help="Generate and print incident report")

    args = parser.parse_args()

    detector = IncidentDetector(
        prometheus_url=args.prometheus_url, alert_webhook=args.webhook_url, check_interval=args.interval
    )

    if args.report:
        report = detector.generate_report()
        print(json.dumps(report, indent=2))
        return

    if args.once:
        incidents = await detector.run_checks()
        print(f"Found {len(incidents)} active incidents")
        for incident in incidents:
            print(f"  - {incident.title} ({incident.severity.value})")
    else:
        await detector.monitor()


if __name__ == "__main__":
    asyncio.run(main())
