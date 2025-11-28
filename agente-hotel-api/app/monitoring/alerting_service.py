"""
Advanced Alerting System
Intelligent alerting with escalation and business logic
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict
import json
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, Enum):
    """Alert status"""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class AlertCategory(str, Enum):
    """Alert categories"""

    REVENUE = "revenue"
    OPERATIONS = "operations"
    GUEST_SATISFACTION = "guest_satisfaction"
    SYSTEM_HEALTH = "system_health"
    SECURITY = "security"
    MAINTENANCE = "maintenance"
    STAFFING = "staffing"


class NotificationChannel(str, Enum):
    """Notification channels"""

    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    WEBHOOK = "webhook"
    PUSH = "push"
    DASHBOARD = "dashboard"


@dataclass
class AlertCondition:
    """Alert condition definition"""

    id: str
    name: str
    description: str
    category: AlertCategory
    severity: AlertSeverity
    metric_name: str
    threshold: float
    operator: str  # >, <, >=, <=, ==, !=
    evaluation_window: int  # seconds
    evaluation_function: str  # avg, max, min, sum, count
    cooldown_period: int = 300  # 5 minutes default
    escalation_rules: List[Dict[str, Any]] = None
    notification_channels: List[NotificationChannel] = None
    business_hours_only: bool = False
    enabled: bool = True


@dataclass
class Alert:
    """Alert instance"""

    id: str
    condition_id: str
    title: str
    description: str
    severity: AlertSeverity
    category: AlertCategory
    status: AlertStatus
    metric_name: str
    current_value: float
    threshold: float
    created_at: datetime
    updated_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    escalation_level: int = 0
    notification_history: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None


@dataclass
class EscalationRule:
    """Alert escalation rule"""

    level: int
    delay_minutes: int
    notification_channels: List[NotificationChannel]
    recipients: List[str]
    message_template: str


class AdvancedAlertingService:
    """Advanced alerting system with business intelligence"""

    def __init__(self, redis_client, notification_service):
        self.redis = redis_client
        self.notification_service = notification_service

        # Alert storage
        self.alert_conditions = {}
        self.active_alerts = {}
        self.alert_history = deque(maxlen=10000)

        # Escalation tracking
        self.escalation_timers = {}
        self.notification_history = defaultdict(list)

        # Business logic evaluators
        self.custom_evaluators = {}

        # Alert suppression
        self.suppression_rules = {}

        # Initialize default alert conditions
        self._init_default_conditions()

        # Start background tasks
        self._start_background_tasks()

    def _init_default_conditions(self):
        """Initialize default hotel business alert conditions"""

        default_conditions = [
            # Revenue Alerts
            AlertCondition(
                id="low_occupancy_critical",
                name="Critical Low Occupancy",
                description="Occupancy rate below critical threshold",
                category=AlertCategory.REVENUE,
                severity=AlertSeverity.CRITICAL,
                metric_name="occupancy_rate",
                threshold=60.0,
                operator="<",
                evaluation_window=3600,  # 1 hour
                evaluation_function="avg",
                cooldown_period=7200,  # 2 hours
                escalation_rules=[
                    {"level": 1, "delay_minutes": 15, "channels": ["email", "dashboard"]},
                    {"level": 2, "delay_minutes": 30, "channels": ["email", "sms", "slack"]},
                    {"level": 3, "delay_minutes": 60, "channels": ["email", "sms", "slack", "webhook"]},
                ],
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.DASHBOARD],
                business_hours_only=False,
            ),
            AlertCondition(
                id="revenue_target_miss",
                name="Daily Revenue Target Miss",
                description="Daily revenue significantly below target",
                category=AlertCategory.REVENUE,
                severity=AlertSeverity.HIGH,
                metric_name="daily_revenue",
                threshold=0.85,  # 85% of target
                operator="<",
                evaluation_window=86400,  # 24 hours
                evaluation_function="sum",
                cooldown_period=86400,  # 24 hours
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
            ),
            AlertCondition(
                id="adr_decline",
                name="ADR Significant Decline",
                description="Average Daily Rate declining below acceptable range",
                category=AlertCategory.REVENUE,
                severity=AlertSeverity.MEDIUM,
                metric_name="adr",
                threshold=0.90,  # 90% of baseline
                operator="<",
                evaluation_window=7200,  # 2 hours
                evaluation_function="avg",
                notification_channels=[NotificationChannel.EMAIL],
            ),
            # Guest Satisfaction Alerts
            AlertCondition(
                id="guest_satisfaction_low",
                name="Low Guest Satisfaction",
                description="Guest satisfaction score below acceptable level",
                category=AlertCategory.GUEST_SATISFACTION,
                severity=AlertSeverity.HIGH,
                metric_name="guest_satisfaction_score",
                threshold=7.0,
                operator="<",
                evaluation_window=86400,  # 24 hours
                evaluation_function="avg",
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
            ),
            AlertCondition(
                id="nps_critical",
                name="Critical NPS Score",
                description="Net Promoter Score in critical range",
                category=AlertCategory.GUEST_SATISFACTION,
                severity=AlertSeverity.CRITICAL,
                metric_name="nps_score",
                threshold=30.0,
                operator="<",
                evaluation_window=86400,  # 24 hours
                evaluation_function="avg",
                escalation_rules=[
                    {"level": 1, "delay_minutes": 30, "channels": ["email", "dashboard"]},
                    {"level": 2, "delay_minutes": 60, "channels": ["email", "sms"]},
                ],
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.SMS],
            ),
            # Operational Alerts
            AlertCondition(
                id="maintenance_backlog_high",
                name="High Maintenance Backlog",
                description="Maintenance requests exceeding capacity",
                category=AlertCategory.MAINTENANCE,
                severity=AlertSeverity.MEDIUM,
                metric_name="maintenance_requests_pending",
                threshold=10.0,
                operator=">",
                evaluation_window=3600,  # 1 hour
                evaluation_function="max",
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.DASHBOARD],
            ),
            AlertCondition(
                id="guest_response_time_high",
                name="High Guest Response Time",
                description="Guest request response time above SLA",
                category=AlertCategory.OPERATIONS,
                severity=AlertSeverity.MEDIUM,
                metric_name="guest_response_time_avg",
                threshold=600.0,  # 10 minutes
                operator=">",
                evaluation_window=3600,  # 1 hour
                evaluation_function="avg",
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.DASHBOARD],
            ),
            AlertCondition(
                id="check_in_duration_high",
                name="Long Check-in Duration",
                description="Check-in process taking too long",
                category=AlertCategory.OPERATIONS,
                severity=AlertSeverity.LOW,
                metric_name="check_in_duration_avg",
                threshold=300.0,  # 5 minutes
                operator=">",
                evaluation_window=3600,  # 1 hour
                evaluation_function="avg",
                notification_channels=[NotificationChannel.DASHBOARD],
            ),
            # System Health Alerts
            AlertCondition(
                id="api_error_rate_high",
                name="High API Error Rate",
                description="API error rate above acceptable threshold",
                category=AlertCategory.SYSTEM_HEALTH,
                severity=AlertSeverity.HIGH,
                metric_name="api_error_rate",
                threshold=0.05,  # 5%
                operator=">",
                evaluation_window=900,  # 15 minutes
                evaluation_function="avg",
                escalation_rules=[
                    {"level": 1, "delay_minutes": 5, "channels": ["email", "slack"]},
                    {"level": 2, "delay_minutes": 15, "channels": ["email", "sms", "webhook"]},
                ],
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
            ),
            AlertCondition(
                id="response_time_degradation",
                name="API Response Time Degradation",
                description="API response time significantly increased",
                category=AlertCategory.SYSTEM_HEALTH,
                severity=AlertSeverity.MEDIUM,
                metric_name="api_response_time_p95",
                threshold=2000.0,  # 2 seconds
                operator=">",
                evaluation_window=600,  # 10 minutes
                evaluation_function="avg",
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.DASHBOARD],
            ),
            # Security Alerts
            AlertCondition(
                id="failed_login_spike",
                name="Failed Login Spike",
                description="Unusual spike in failed login attempts",
                category=AlertCategory.SECURITY,
                severity=AlertSeverity.HIGH,
                metric_name="failed_login_rate",
                threshold=50.0,  # 50 failed logins per hour
                operator=">",
                evaluation_window=3600,  # 1 hour
                evaluation_function="sum",
                escalation_rules=[
                    {"level": 1, "delay_minutes": 0, "channels": ["email", "sms"]},
                    {"level": 2, "delay_minutes": 15, "channels": ["email", "sms", "webhook"]},
                ],
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.SMS],
                business_hours_only=False,
            ),
            AlertCondition(
                id="rate_limit_breaches",
                name="Rate Limit Breaches",
                description="High number of rate limit breaches detected",
                category=AlertCategory.SECURITY,
                severity=AlertSeverity.MEDIUM,
                metric_name="rate_limit_violations",
                threshold=100.0,
                operator=">",
                evaluation_window=3600,  # 1 hour
                evaluation_function="sum",
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.DASHBOARD],
            ),
        ]

        # Store conditions
        for condition in default_conditions:
            self.alert_conditions[condition.id] = condition

        logger.info(f"Initialized {len(default_conditions)} default alert conditions")

    async def add_custom_condition(self, condition: AlertCondition):
        """Add custom alert condition"""
        self.alert_conditions[condition.id] = condition

        # Store in Redis for persistence
        condition_key = f"alert_condition:{condition.id}"
        await self.redis.set(condition_key, json.dumps(asdict(condition), default=str))

        logger.info(f"Added custom alert condition: {condition.id}")

    async def evaluate_conditions(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Evaluate alert conditions for a metric"""

        triggered_alerts = []

        for condition_id, condition in self.alert_conditions.items():
            if not condition.enabled or condition.metric_name != metric_name:
                continue

            # Check business hours restriction
            if condition.business_hours_only and not self._is_business_hours():
                continue

            try:
                # Get historical data for evaluation
                historical_values = await self._get_historical_values(metric_name, condition.evaluation_window)

                # Evaluate condition
                evaluation_value = self._apply_evaluation_function(
                    historical_values + [value], condition.evaluation_function
                )

                triggered = self._evaluate_threshold(evaluation_value, condition.threshold, condition.operator)

                if triggered:
                    # Check cooldown
                    if self._is_in_cooldown(condition_id, condition.cooldown_period):
                        continue

                    # Create alert
                    alert = await self._create_alert(condition, evaluation_value, labels)
                    triggered_alerts.append(alert)

                    # Start escalation if configured
                    if condition.escalation_rules:
                        await self._start_escalation(alert)

                    logger.warning(
                        f"Alert triggered: {condition.name} - {evaluation_value} {condition.operator} {condition.threshold}"
                    )

            except Exception as e:
                logger.error(f"Error evaluating condition {condition_id}: {e}")

        return triggered_alerts

    async def acknowledge_alert(self, alert_id: str, user_id: str, comment: str = None):
        """Acknowledge an alert"""

        if alert_id not in self.active_alerts:
            raise ValueError(f"Alert not found: {alert_id}")

        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = user_id
        alert.updated_at = datetime.now(timezone.utc)

        if comment:
            if not alert.metadata:
                alert.metadata = {}
            alert.metadata["acknowledgment_comment"] = comment

        # Stop escalation
        await self._stop_escalation(alert_id)

        # Notify acknowledgment
        await self._send_notification(alert, f"Alert acknowledged by {user_id}", [NotificationChannel.DASHBOARD])

        # Store updated alert
        await self._store_alert(alert)

        logger.info(f"Alert acknowledged: {alert_id} by {user_id}")

    async def resolve_alert(self, alert_id: str, user_id: str, comment: str = None):
        """Resolve an alert"""

        if alert_id not in self.active_alerts:
            raise ValueError(f"Alert not found: {alert_id}")

        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolved_by = user_id
        alert.updated_at = datetime.now(timezone.utc)

        if comment:
            if not alert.metadata:
                alert.metadata = {}
            alert.metadata["resolution_comment"] = comment

        # Stop escalation
        await self._stop_escalation(alert_id)

        # Move to history
        self.alert_history.append(alert)
        del self.active_alerts[alert_id]

        # Notify resolution
        await self._send_notification(alert, f"Alert resolved by {user_id}", [NotificationChannel.DASHBOARD])

        logger.info(f"Alert resolved: {alert_id} by {user_id}")

    async def get_active_alerts(self, category: AlertCategory = None, severity: AlertSeverity = None) -> List[Alert]:
        """Get active alerts with optional filtering"""

        alerts = list(self.active_alerts.values())

        if category:
            alerts = [a for a in alerts if a.category == category]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        # Sort by severity and creation time
        severity_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.HIGH: 1,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.LOW: 3,
            AlertSeverity.INFO: 4,
        }

        alerts.sort(key=lambda a: (severity_order[a.severity], a.created_at))

        return alerts

    async def get_alert_history(self, hours: int = 24, category: AlertCategory = None) -> List[Alert]:
        """Get alert history"""

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        history = [alert for alert in self.alert_history if alert.created_at > cutoff_time]

        if category:
            history = [a for a in history if a.category == category]

        return sorted(history, key=lambda a: a.created_at, reverse=True)

    async def get_alert_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get alert statistics"""

        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)

        # Get recent alerts
        recent_alerts = [alert for alert in self.alert_history if alert.created_at > cutoff_time]

        # Add active alerts
        recent_alerts.extend(self.active_alerts.values())

        # Calculate statistics
        stats = {
            "total_alerts": len(recent_alerts),
            "active_alerts": len(self.active_alerts),
            "by_severity": defaultdict(int),
            "by_category": defaultdict(int),
            "by_status": defaultdict(int),
            "resolution_time_avg": 0,
            "most_frequent_conditions": defaultdict(int),
            "escalation_rate": 0,
        }

        resolution_times = []
        escalated_count = 0

        for alert in recent_alerts:
            stats["by_severity"][alert.severity] += 1
            stats["by_category"][alert.category] += 1
            stats["by_status"][alert.status] += 1
            stats["most_frequent_conditions"][alert.condition_id] += 1

            if alert.escalation_level > 0:
                escalated_count += 1

            if alert.resolved_at and alert.created_at:
                resolution_time = (alert.resolved_at - alert.created_at).total_seconds()
                resolution_times.append(resolution_time)

        if resolution_times:
            stats["resolution_time_avg"] = sum(resolution_times) / len(resolution_times)

        if len(recent_alerts) > 0:
            stats["escalation_rate"] = escalated_count / len(recent_alerts) * 100

        return dict(stats)

    async def create_suppression_rule(self, rule_config: Dict[str, Any]):
        """Create alert suppression rule"""

        rule_id = rule_config["id"]
        self.suppression_rules[rule_id] = {
            "condition_ids": rule_config.get("condition_ids", []),
            "categories": rule_config.get("categories", []),
            "severities": rule_config.get("severities", []),
            "start_time": rule_config.get("start_time"),
            "end_time": rule_config.get("end_time"),
            "reason": rule_config.get("reason", ""),
            "created_by": rule_config.get("created_by", ""),
            "created_at": datetime.now(timezone.utc),
        }

        logger.info(f"Created suppression rule: {rule_id}")

    def _start_background_tasks(self):
        """Start background tasks for alerting"""

        # Start escalation processor
        asyncio.create_task(self._process_escalations())

        # Start condition evaluator (if needed for periodic checks)
        asyncio.create_task(self._periodic_evaluation())

    async def _create_alert(
        self, condition: AlertCondition, current_value: float, labels: Dict[str, str] = None
    ) -> Alert:
        """Create new alert"""

        alert_id = f"alert_{condition.id}_{int(datetime.now(timezone.utc).timestamp())}"

        alert = Alert(
            id=alert_id,
            condition_id=condition.id,
            title=condition.name,
            description=condition.description,
            severity=condition.severity,
            category=condition.category,
            status=AlertStatus.ACTIVE,
            metric_name=condition.metric_name,
            current_value=current_value,
            threshold=condition.threshold,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            escalation_level=0,
            notification_history=[],
            metadata={
                "labels": labels or {},
                "operator": condition.operator,
                "evaluation_window": condition.evaluation_window,
                "evaluation_function": condition.evaluation_function,
            },
        )

        # Store alert
        self.active_alerts[alert_id] = alert
        await self._store_alert(alert)

        # Send initial notification
        if condition.notification_channels:
            await self._send_notification(alert, "New alert created", condition.notification_channels)

        return alert

    async def _start_escalation(self, alert: Alert):
        """Start alert escalation process"""

        condition = self.alert_conditions.get(alert.condition_id)
        if not condition or not condition.escalation_rules:
            return

        # Schedule escalation levels
        for rule in condition.escalation_rules:
            delay_seconds = rule["delay_minutes"] * 60

            self.escalation_timers[f"{alert.id}_{rule['level']}"] = {
                "alert_id": alert.id,
                "level": rule["level"],
                "scheduled_at": datetime.now(timezone.utc) + timedelta(seconds=delay_seconds),
                "channels": rule["channels"],
                "executed": False,
            }

    async def _stop_escalation(self, alert_id: str):
        """Stop escalation for alert"""

        # Mark all pending escalations as cancelled
        for timer_key in list(self.escalation_timers.keys()):
            if timer_key.startswith(f"{alert_id}_"):
                self.escalation_timers[timer_key]["executed"] = True

    async def _process_escalations(self):
        """Background task to process escalations"""

        while True:
            try:
                now = datetime.now(timezone.utc)

                for timer_key, timer_data in list(self.escalation_timers.items()):
                    if timer_data["executed"]:
                        continue

                    if now >= timer_data["scheduled_at"]:
                        # Execute escalation
                        alert_id = timer_data["alert_id"]
                        level = timer_data["level"]

                        if alert_id in self.active_alerts:
                            alert = self.active_alerts[alert_id]
                            alert.escalation_level = max(alert.escalation_level, level)

                            # Send escalation notification
                            channels = [NotificationChannel(ch) for ch in timer_data["channels"]]
                            await self._send_notification(alert, f"Alert escalated to level {level}", channels)

                            logger.warning(f"Alert escalated: {alert_id} to level {level}")

                        # Mark as executed
                        timer_data["executed"] = True

                # Clean up executed timers
                self.escalation_timers = {k: v for k, v in self.escalation_timers.items() if not v["executed"]}

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error in escalation processor: {e}")
                await asyncio.sleep(60)

    async def _periodic_evaluation(self):
        """Periodic evaluation of conditions that need it"""

        while True:
            try:
                # This could be used for conditions that need periodic checking
                # rather than event-driven evaluation
                await asyncio.sleep(300)  # Check every 5 minutes

            except Exception as e:
                logger.error(f"Error in periodic evaluation: {e}")
                await asyncio.sleep(300)

    async def _send_notification(self, alert: Alert, message: str, channels: List[NotificationChannel]):
        """Send alert notification"""

        for channel in channels:
            try:
                notification_data = {
                    "alert_id": alert.id,
                    "title": alert.title,
                    "message": message,
                    "severity": alert.severity,
                    "category": alert.category,
                    "current_value": alert.current_value,
                    "threshold": alert.threshold,
                    "created_at": alert.created_at.isoformat(),
                }

                # Send notification via channel
                await self.notification_service.send_notification(channel, notification_data)

                # Record notification
                if not alert.notification_history:
                    alert.notification_history = []

                alert.notification_history.append(
                    {"channel": channel, "message": message, "sent_at": datetime.now(timezone.utc).isoformat(), "status": "sent"}
                )

            except Exception as e:
                logger.error(f"Error sending notification via {channel}: {e}")

    async def _store_alert(self, alert: Alert):
        """Store alert in Redis"""

        alert_key = f"alert:{alert.id}"
        alert_data = asdict(alert)

        # Convert datetime objects to ISO strings
        for field in ["created_at", "updated_at", "acknowledged_at", "resolved_at"]:
            if alert_data[field]:
                alert_data[field] = alert_data[field].isoformat()

        await self.redis.setex(
            alert_key,
            86400 * 7,  # 7 days TTL
            json.dumps(alert_data, default=str),
        )

    async def _get_historical_values(self, metric_name: str, window_seconds: int) -> List[float]:
        """Get historical metric values for evaluation"""

        # This would query actual historical data
        # For now, return simulated data
        return [75.0, 76.2, 74.8, 73.5, 72.1]

    def _apply_evaluation_function(self, values: List[float], function: str) -> float:
        """Apply evaluation function to values"""

        if not values:
            return 0.0

        if function == "avg":
            return sum(values) / len(values)
        elif function == "max":
            return max(values)
        elif function == "min":
            return min(values)
        elif function == "sum":
            return sum(values)
        elif function == "count":
            return len(values)
        elif function == "latest":
            return values[-1]
        else:
            return values[-1]  # Default to latest value

    def _evaluate_threshold(self, value: float, threshold: float, operator: str) -> bool:
        """Evaluate threshold condition"""

        if operator == ">":
            return value > threshold
        elif operator == "<":
            return value < threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "==":
            return value == threshold
        elif operator == "!=":
            return value != threshold
        else:
            return False

    def _is_in_cooldown(self, condition_id: str, cooldown_seconds: int) -> bool:
        """Check if condition is in cooldown period"""

        # Check if there's a recent alert for this condition
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=cooldown_seconds)

        for alert in self.active_alerts.values():
            if alert.condition_id == condition_id and alert.created_at > cutoff_time:
                return True

        # Check recent history
        for alert in self.alert_history:
            if alert.condition_id == condition_id and alert.created_at > cutoff_time:
                return True

        return False

    def _is_business_hours(self) -> bool:
        """Check if current time is within business hours"""

        now = datetime.now(timezone.utc)
        hour = now.hour

        # Define business hours (can be configurable)
        business_start = 8  # 8 AM
        business_end = 18  # 6 PM

        return business_start <= hour < business_end


# Create singleton instance
alerting_service = None


async def get_alerting_service() -> AdvancedAlertingService:
    """Get alerting service instance"""
    global alerting_service
    if alerting_service is None:
        # This would be initialized with actual Redis and notification service
        alerting_service = AdvancedAlertingService(None, None)
    return alerting_service
