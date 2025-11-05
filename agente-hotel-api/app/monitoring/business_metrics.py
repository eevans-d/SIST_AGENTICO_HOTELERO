"""
Advanced Business Metrics Service
Hotel-specific business intelligence and operational metrics
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import json
import logging
from collections import defaultdict, deque

from prometheus_client import Counter, Histogram, Gauge
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class MetricCategory(str, Enum):
    """Metric categories for business intelligence"""

    RESERVATIONS = "reservations"
    OCCUPANCY = "occupancy"
    REVENUE = "revenue"
    GUEST_SATISFACTION = "guest_satisfaction"
    OPERATIONAL = "operational"
    PERFORMANCE = "performance"
    SECURITY = "security"
    COMMUNICATION = "communication"


class AlertSeverity(str, Enum):
    """Alert severity levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class BusinessMetric:
    """Business metric data structure"""

    name: str
    category: MetricCategory
    value: float
    timestamp: datetime
    labels: Dict[str, str]
    metadata: Dict[str, Any] = None


@dataclass
class AlertCondition:
    """Alert condition configuration"""

    metric_name: str
    threshold: float
    operator: str  # >, <, >=, <=, ==, !=
    severity: AlertSeverity
    message: str
    cooldown_minutes: int = 5


class AdvancedBusinessMetrics:
    """Advanced business metrics collection and analysis"""

    def __init__(self, redis_client, database_session_factory):
        self.redis = redis_client
        self.db_factory = database_session_factory

        # Business metrics storage
        self.metrics_buffer = deque(maxlen=10000)
        self.alert_conditions = {}
        self.alert_history = defaultdict(list)

        # Prometheus metrics for business intelligence
        self._init_prometheus_metrics()

        # Time series data for trends
        self.time_series_data = defaultdict(lambda: deque(maxlen=1440))  # 24 hours of minute data

        # Real-time calculation cache
        self._calculation_cache = {}
        self._cache_ttl = 60  # 1 minute cache

    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics for business intelligence"""

        # Reservation metrics
        self.reservations_total = Counter(
            "hotel_reservations_total", "Total number of reservations", ["status", "channel", "room_type"]
        )

        self.reservation_value = Histogram(
            "hotel_reservation_value_euros",
            "Reservation value in euros",
            ["room_type", "channel"],
            buckets=[50, 100, 200, 500, 1000, 2000, 5000],
        )

        self.booking_lead_time = Histogram(
            "hotel_booking_lead_time_days",
            "Days between booking and check-in",
            ["channel", "room_type"],
            buckets=[0, 1, 3, 7, 14, 30, 60, 90],
        )

        # Occupancy metrics
        self.occupancy_rate = Gauge(
            "hotel_occupancy_rate_percent", "Current occupancy rate percentage", ["date", "room_type"]
        )

        self.available_rooms = Gauge("hotel_available_rooms_count", "Number of available rooms", ["room_type", "date"])

        self.adr = Gauge("hotel_adr_euros", "Average Daily Rate in euros", ["date", "room_type"])

        self.revpar = Gauge("hotel_revpar_euros", "Revenue per Available Room in euros", ["date", "room_type"])

        # Guest satisfaction metrics
        self.guest_satisfaction_score = Gauge(
            "hotel_guest_satisfaction_score", "Guest satisfaction score (1-10)", ["category", "date"]
        )

        self.nps_score = Gauge("hotel_nps_score", "Net Promoter Score (-100 to 100)", ["date"])

        # Operational metrics
        self.check_in_duration = Histogram(
            "hotel_check_in_duration_seconds",
            "Check-in process duration",
            ["method"],  # automated, assisted, manual
            buckets=[30, 60, 120, 300, 600, 1200],
        )

        self.response_time_guest = Histogram(
            "hotel_guest_response_time_seconds",
            "Time to respond to guest requests",
            ["request_type", "channel"],
            buckets=[10, 30, 60, 300, 600, 1800],
        )

        self.maintenance_requests = Counter(
            "hotel_maintenance_requests_total", "Number of maintenance requests", ["type", "priority", "room"]
        )

        # Revenue metrics
        self.daily_revenue = Gauge("hotel_daily_revenue_euros", "Daily revenue in euros", ["date", "revenue_type"])

        self.forecast_accuracy = Gauge(
            "hotel_forecast_accuracy_percent", "Revenue forecast accuracy percentage", ["forecast_horizon_days"]
        )

        # Communication metrics
        self.message_volume = Counter("hotel_messages_total", "Total messages processed", ["channel", "type", "status"])

        self.intent_recognition_accuracy = Gauge(
            "hotel_intent_accuracy_percent", "Intent recognition accuracy", ["intent_category"]
        )

    async def record_reservation_metrics(self, reservation_data: Dict[str, Any]):
        """Record reservation-related business metrics"""

        # Extract key information
        status = reservation_data.get("status", "unknown")
        channel = reservation_data.get("booking_channel", "direct")
        room_type = reservation_data.get("room_type", "standard")
        value = float(reservation_data.get("total_amount", 0))
        check_in_date = reservation_data.get("check_in_date")
        booking_date = reservation_data.get("booking_date")

        # Update Prometheus metrics
        self.reservations_total.labels(status=status, channel=channel, room_type=room_type).inc()

        if value > 0:
            self.reservation_value.labels(room_type=room_type, channel=channel).observe(value)

        # Calculate lead time
        if check_in_date and booking_date:
            try:
                check_in = datetime.fromisoformat(check_in_date)
                booking = datetime.fromisoformat(booking_date)
                lead_time_days = (check_in - booking).days

                if lead_time_days >= 0:
                    self.booking_lead_time.labels(channel=channel, room_type=room_type).observe(lead_time_days)

            except (ValueError, TypeError) as e:
                logger.warning(f"Error calculating lead time: {e}")

        # Store business metric
        metric = BusinessMetric(
            name="reservation_created",
            category=MetricCategory.RESERVATIONS,
            value=value,
            timestamp=datetime.now(timezone.utc),
            labels={"status": status, "channel": channel, "room_type": room_type},
            metadata=reservation_data,
        )

        await self._store_metric(metric)

        logger.info(f"Recorded reservation metric: {status} - {value}€ - {channel}")

    async def calculate_occupancy_metrics(self, date: str = None):
        """Calculate and update occupancy metrics"""

        if not date:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        try:
            # Get room data from database
            async with self.db_factory() as session:
                # This would query actual room data
                # For now, we'll simulate the calculation
                room_data = await self._get_room_occupancy_data(session, date)

            total_rooms = room_data.get("total_rooms", 100)
            occupied_rooms = room_data.get("occupied_rooms", 0)

            # Calculate occupancy rate
            occupancy_rate = (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0

            # Update metrics by room type
            room_types = room_data.get("by_room_type", {})
            for room_type, data in room_types.items():
                type_occupancy = (data["occupied"] / data["total"] * 100) if data["total"] > 0 else 0

                self.occupancy_rate.labels(date=date, room_type=room_type).set(type_occupancy)

                self.available_rooms.labels(room_type=room_type, date=date).set(data["available"])

            # Store business metric
            metric = BusinessMetric(
                name="occupancy_calculated",
                category=MetricCategory.OCCUPANCY,
                value=occupancy_rate,
                timestamp=datetime.now(timezone.utc),
                labels={"date": date},
                metadata=room_data,
            )

            await self._store_metric(metric)

            logger.info(f"Calculated occupancy for {date}: {occupancy_rate:.1f}%")

            return occupancy_rate

        except Exception as e:
            logger.error(f"Error calculating occupancy metrics: {e}")
            return None

    async def calculate_revenue_metrics(self, date: str = None):
        """Calculate revenue metrics (ADR, RevPAR, etc.)"""

        if not date:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        try:
            async with self.db_factory() as session:
                revenue_data = await self._get_revenue_data(session, date)

            total_revenue = revenue_data.get("total_revenue", 0)
            rooms_sold = revenue_data.get("rooms_sold", 0)
            total_rooms = revenue_data.get("total_rooms", 100)

            # Calculate ADR (Average Daily Rate)
            adr = total_revenue / rooms_sold if rooms_sold > 0 else 0

            # Calculate RevPAR (Revenue per Available Room)
            revpar = total_revenue / total_rooms if total_rooms > 0 else 0

            # Update metrics by room type
            room_types = revenue_data.get("by_room_type", {})
            for room_type, data in room_types.items():
                type_adr = data["revenue"] / data["sold"] if data["sold"] > 0 else 0
                type_revpar = data["revenue"] / data["available"] if data["available"] > 0 else 0

                self.adr.labels(date=date, room_type=room_type).set(type_adr)

                self.revpar.labels(date=date, room_type=room_type).set(type_revpar)

            # Update daily revenue
            self.daily_revenue.labels(date=date, revenue_type="rooms").set(total_revenue)

            # Store business metrics
            for name, value in [("adr", adr), ("revpar", revpar), ("daily_revenue", total_revenue)]:
                metric = BusinessMetric(
                    name=name,
                    category=MetricCategory.REVENUE,
                    value=value,
                    timestamp=datetime.now(timezone.utc),
                    labels={"date": date},
                    metadata=revenue_data,
                )
                await self._store_metric(metric)

            logger.info(f"Calculated revenue metrics for {date}: ADR={adr:.2f}€, RevPAR={revpar:.2f}€")

            return {"adr": adr, "revpar": revpar, "revenue": total_revenue}

        except Exception as e:
            logger.error(f"Error calculating revenue metrics: {e}")
            return None

    async def record_guest_satisfaction(self, satisfaction_data: Dict[str, Any]):
        """Record guest satisfaction metrics"""

        score = float(satisfaction_data.get("score", 0))
        category = satisfaction_data.get("category", "overall")
        date = satisfaction_data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))

        # Update Prometheus metrics
        self.guest_satisfaction_score.labels(category=category, date=date).set(score)

        # Calculate NPS if we have recommendation data
        if "would_recommend" in satisfaction_data:
            nps = await self._calculate_nps(date)
            if nps is not None:
                self.nps_score.labels(date=date).set(nps)

        # Store business metric
        metric = BusinessMetric(
            name="guest_satisfaction",
            category=MetricCategory.GUEST_SATISFACTION,
            value=score,
            timestamp=datetime.now(timezone.utc),
            labels={"category": category, "date": date},
            metadata=satisfaction_data,
        )

        await self._store_metric(metric)

        logger.info(f"Recorded guest satisfaction: {category}={score}")

    async def record_operational_metrics(self, operation_data: Dict[str, Any]):
        """Record operational performance metrics"""

        operation_type = operation_data.get("type")
        duration = float(operation_data.get("duration_seconds", 0))

        if operation_type == "check_in":
            method = operation_data.get("method", "manual")
            self.check_in_duration.labels(method=method).observe(duration)

        elif operation_type == "guest_response":
            request_type = operation_data.get("request_type", "general")
            channel = operation_data.get("channel", "unknown")
            self.response_time_guest.labels(request_type=request_type, channel=channel).observe(duration)

        elif operation_type == "maintenance_request":
            maintenance_type = operation_data.get("maintenance_type", "general")
            priority = operation_data.get("priority", "medium")
            room = operation_data.get("room", "unknown")
            self.maintenance_requests.labels(type=maintenance_type, priority=priority, room=room).inc()

        # Store business metric
        metric = BusinessMetric(
            name=f"operation_{operation_type}",
            category=MetricCategory.OPERATIONAL,
            value=duration,
            timestamp=datetime.now(timezone.utc),
            labels={
                "type": operation_type,
                **{k: str(v) for k, v in operation_data.items() if k not in ["type", "duration_seconds"]},
            },
            metadata=operation_data,
        )

        await self._store_metric(metric)

    async def record_communication_metrics(self, message_data: Dict[str, Any]):
        """Record communication and AI performance metrics"""

        channel = message_data.get("channel", "unknown")
        message_type = message_data.get("type", "text")
        status = message_data.get("status", "processed")

        # Update message volume
        self.message_volume.labels(channel=channel, type=message_type, status=status).inc()

        # Update intent recognition accuracy if available
        if "intent_accuracy" in message_data:
            intent_category = message_data.get("intent_category", "general")
            accuracy = float(message_data["intent_accuracy"])

            self.intent_recognition_accuracy.labels(intent_category=intent_category).set(accuracy)

        # Store business metric
        metric = BusinessMetric(
            name="message_processed",
            category=MetricCategory.COMMUNICATION,
            value=1,
            timestamp=datetime.now(timezone.utc),
            labels={"channel": channel, "type": message_type, "status": status},
            metadata=message_data,
        )

        await self._store_metric(metric)

    async def get_business_dashboard_data(self, timeframe: str = "24h") -> Dict[str, Any]:
        """Get comprehensive business dashboard data"""

        cache_key = f"dashboard_data_{timeframe}"
        cached_data = await self._get_cached_calculation(cache_key)
        if cached_data:
            return cached_data

        try:
            # Calculate timeframe
            now = datetime.now(timezone.utc)
            if timeframe == "24h":
                start_time = now - timedelta(hours=24)
            elif timeframe == "7d":
                start_time = now - timedelta(days=7)
            elif timeframe == "30d":
                start_time = now - timedelta(days=30)
            else:
                start_time = now - timedelta(hours=24)

            # Get current metrics
            today = now.strftime("%Y-%m-%d")
            occupancy = await self.calculate_occupancy_metrics(today)
            revenue = await self.calculate_revenue_metrics(today)

            # Aggregate historical data
            historical_metrics = await self._get_historical_metrics(start_time, now)

            dashboard_data = {
                "timestamp": now.isoformat(),
                "timeframe": timeframe,
                "current": {
                    "occupancy_rate": occupancy,
                    "daily_revenue": revenue.get("revenue", 0) if revenue else 0,
                    "adr": revenue.get("adr", 0) if revenue else 0,
                    "revpar": revenue.get("revpar", 0) if revenue else 0,
                },
                "trends": await self._calculate_trends(historical_metrics),
                "alerts": await self._get_active_alerts(),
                "kpis": await self._calculate_kpis(historical_metrics),
                "forecasts": await self._generate_forecasts(historical_metrics),
            }

            await self._cache_calculation(cache_key, dashboard_data, self._cache_ttl)

            return dashboard_data

        except Exception as e:
            logger.error(f"Error generating dashboard data: {e}")
            return {}

    async def setup_alert_conditions(self, conditions: List[AlertCondition]):
        """Setup business alert conditions"""

        for condition in conditions:
            self.alert_conditions[condition.metric_name] = condition

        logger.info(f"Setup {len(conditions)} alert conditions")

    async def check_alert_conditions(self):
        """Check all alert conditions and trigger alerts if needed"""

        alerts_triggered = []

        for metric_name, condition in self.alert_conditions.items():
            try:
                # Get current metric value
                current_value = await self._get_current_metric_value(metric_name)
                if current_value is None:
                    continue

                # Check condition
                triggered = self._evaluate_condition(current_value, condition)

                if triggered:
                    # Check cooldown
                    last_alert = self._get_last_alert_time(metric_name)
                    if (
                        last_alert
                        and (datetime.now(timezone.utc) - last_alert).total_seconds() < condition.cooldown_minutes * 60
                    ):
                        continue

                    # Trigger alert
                    alert_data = {
                        "metric_name": metric_name,
                        "condition": condition,
                        "current_value": current_value,
                        "timestamp": datetime.now(timezone.utc),
                        "severity": condition.severity,
                    }

                    await self._trigger_alert(alert_data)
                    alerts_triggered.append(alert_data)

            except Exception as e:
                logger.error(f"Error checking alert condition for {metric_name}: {e}")

        return alerts_triggered

    async def _store_metric(self, metric: BusinessMetric):
        """Store business metric"""

        # Add to buffer
        self.metrics_buffer.append(metric)

        # Store in Redis for real-time access
        metric_key = f"metric:{metric.category}:{metric.name}:{metric.timestamp.timestamp()}"
        metric_data = asdict(metric)
        metric_data["timestamp"] = metric.timestamp.isoformat()

        await self.redis.setex(
            metric_key,
            3600,  # 1 hour TTL
            json.dumps(metric_data),
        )

        # Add to time series
        minute_key = metric.timestamp.strftime("%Y-%m-%d-%H-%M")
        self.time_series_data[f"{metric.category}:{metric.name}"].append(
            {"timestamp": minute_key, "value": metric.value, "labels": metric.labels}
        )

    async def _get_room_occupancy_data(self, session: AsyncSession, date: str) -> Dict[str, Any]:
        """Get room occupancy data from database"""
        # This would implement actual database queries
        # For now, return simulated data
        return {
            "total_rooms": 100,
            "occupied_rooms": 75,
            "by_room_type": {
                "standard": {"total": 60, "occupied": 45, "available": 15},
                "deluxe": {"total": 30, "occupied": 25, "available": 5},
                "suite": {"total": 10, "occupied": 5, "available": 5},
            },
        }

    async def _get_revenue_data(self, session: AsyncSession, date: str) -> Dict[str, Any]:
        """Get revenue data from database"""
        # This would implement actual database queries
        # For now, return simulated data
        return {
            "total_revenue": 15000,
            "rooms_sold": 75,
            "total_rooms": 100,
            "by_room_type": {
                "standard": {"revenue": 6750, "sold": 45, "available": 60},
                "deluxe": {"revenue": 6250, "sold": 25, "available": 30},
                "suite": {"revenue": 2000, "sold": 5, "available": 10},
            },
        }

    async def _calculate_nps(self, date: str) -> Optional[float]:
        """Calculate Net Promoter Score"""
        # This would calculate NPS from satisfaction data
        # For now, return simulated NPS
        return 65.0

    async def _get_cached_calculation(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached calculation result"""
        try:
            cached = await self.redis.get(f"calc_cache:{key}")
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Error getting cached calculation: {e}")
        return None

    async def _cache_calculation(self, key: str, data: Dict[str, Any], ttl: int):
        """Cache calculation result"""
        try:
            await self.redis.setex(f"calc_cache:{key}", ttl, json.dumps(data, default=str))
        except Exception as e:
            logger.warning(f"Error caching calculation: {e}")

    async def _get_historical_metrics(self, start_time: datetime, end_time: datetime) -> List[BusinessMetric]:
        """Get historical metrics from time range"""
        # This would query stored metrics
        # For now, return simulated data
        return []

    async def _calculate_trends(self, historical_metrics: List[BusinessMetric]) -> Dict[str, Any]:
        """Calculate trends from historical data"""
        # This would calculate actual trends
        return {
            "occupancy_trend": 5.2,  # +5.2% vs previous period
            "revenue_trend": 8.1,  # +8.1% vs previous period
            "satisfaction_trend": -1.5,  # -1.5% vs previous period
        }

    async def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active alerts"""
        # This would return actual active alerts
        return []

    async def _calculate_kpis(self, historical_metrics: List[BusinessMetric]) -> Dict[str, Any]:
        """Calculate key performance indicators"""
        return {
            "average_occupancy": 76.8,
            "average_adr": 185.50,
            "average_revpar": 142.30,
            "guest_satisfaction": 8.7,
            "nps_score": 65.0,
        }

    async def _generate_forecasts(self, historical_metrics: List[BusinessMetric]) -> Dict[str, Any]:
        """Generate business forecasts"""
        return {"occupancy_forecast_7d": 78.5, "revenue_forecast_7d": 105000, "confidence_level": 85.0}

    async def _get_current_metric_value(self, metric_name: str) -> Optional[float]:
        """Get current value of a metric"""
        # This would get the actual current value
        # For now, return simulated data
        metric_values = {
            "occupancy_rate": 76.8,
            "daily_revenue": 15000,
            "guest_satisfaction": 8.7,
            "response_time": 45.0,
        }
        return metric_values.get(metric_name)

    def _evaluate_condition(self, value: float, condition: AlertCondition) -> bool:
        """Evaluate if alert condition is met"""
        if condition.operator == ">":
            return value > condition.threshold
        elif condition.operator == "<":
            return value < condition.threshold
        elif condition.operator == ">=":
            return value >= condition.threshold
        elif condition.operator == "<=":
            return value <= condition.threshold
        elif condition.operator == "==":
            return value == condition.threshold
        elif condition.operator == "!=":
            return value != condition.threshold
        return False

    def _get_last_alert_time(self, metric_name: str) -> Optional[datetime]:
        """Get timestamp of last alert for metric"""
        alerts = self.alert_history.get(metric_name, [])
        return alerts[-1] if alerts else None

    async def _trigger_alert(self, alert_data: Dict[str, Any]):
        """Trigger business alert"""
        metric_name = alert_data["metric_name"]
        timestamp = alert_data["timestamp"]

        # Record alert in history
        self.alert_history[metric_name].append(timestamp)

        # Store alert in Redis
        alert_key = f"alert:{metric_name}:{timestamp.timestamp()}"
        await self.redis.setex(
            alert_key,
            86400,  # 24 hours TTL
            json.dumps(alert_data, default=str),
        )

        logger.warning(f"Business alert triggered: {metric_name} = {alert_data['current_value']}")


# Create singleton instance
business_metrics_service = None


async def get_business_metrics_service() -> AdvancedBusinessMetrics:
    """Get business metrics service instance"""
    global business_metrics_service
    if business_metrics_service is None:
        # This would be initialized with actual Redis and DB connections
        business_metrics_service = AdvancedBusinessMetrics(None, None)
    return business_metrics_service
