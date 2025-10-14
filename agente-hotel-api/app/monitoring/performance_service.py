"""
Performance Monitoring Service
Advanced performance tracking and optimization recommendations
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import statistics
import json
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class PerformanceMetricType(str, Enum):
    """Performance metric types"""

    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    RESOURCE_USAGE = "resource_usage"
    AVAILABILITY = "availability"
    BUSINESS_KPI = "business_kpi"


class PerformanceStatus(str, Enum):
    """Performance status levels"""

    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    DEGRADED = "degraded"
    CRITICAL = "critical"


class OptimizationType(str, Enum):
    """Types of optimization recommendations"""

    SCALING = "scaling"
    CACHING = "caching"
    DATABASE = "database"
    CODE = "code"
    CONFIGURATION = "configuration"
    INFRASTRUCTURE = "infrastructure"


@dataclass
class PerformanceMetric:
    """Performance metric data"""

    name: str
    type: PerformanceMetricType
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = None
    percentiles: Dict[str, float] = None  # P50, P95, P99
    trend: str = None  # "increasing", "decreasing", "stable"


@dataclass
class PerformanceBenchmark:
    """Performance benchmark definition"""

    metric_name: str
    excellent_threshold: float
    good_threshold: float
    acceptable_threshold: float
    degraded_threshold: float
    unit: str
    higher_is_better: bool = False


@dataclass
class OptimizationRecommendation:
    """Performance optimization recommendation"""

    id: str
    type: OptimizationType
    title: str
    description: str
    priority: str  # high, medium, low
    impact_estimate: str
    effort_estimate: str
    affected_metrics: List[str]
    implementation_steps: List[str]
    expected_improvement: Dict[str, float]
    created_at: datetime


@dataclass
class PerformanceReport:
    """Performance analysis report"""

    period_start: datetime
    period_end: datetime
    overall_status: PerformanceStatus
    metric_summaries: Dict[str, Dict[str, Any]]
    recommendations: List[OptimizationRecommendation]
    trends: Dict[str, str]
    alerts_triggered: int
    performance_score: float


class PerformanceMonitoringService:
    """Advanced performance monitoring with AI-driven optimization"""

    def __init__(self, redis_client, metrics_service):
        self.redis = redis_client
        self.metrics_service = metrics_service

        # Performance data storage
        self.metrics_buffer = defaultdict(lambda: deque(maxlen=10000))
        self.benchmarks = {}
        self.optimization_history = deque(maxlen=1000)

        # Performance analysis
        self.analysis_cache = {}
        self.trend_analyzers = {}
        self.anomaly_detectors = {}

        # Initialize benchmarks
        self._init_performance_benchmarks()

        # Start background tasks
        self._start_background_tasks()

    def _init_performance_benchmarks(self):
        """Initialize performance benchmarks for hotel system"""

        benchmarks = [
            # API Performance
            PerformanceBenchmark(
                metric_name="api_response_time_p95",
                excellent_threshold=200.0,  # < 200ms
                good_threshold=500.0,  # < 500ms
                acceptable_threshold=1000.0,  # < 1s
                degraded_threshold=2000.0,  # < 2s
                unit="ms",
                higher_is_better=False,
            ),
            PerformanceBenchmark(
                metric_name="api_throughput",
                excellent_threshold=1000.0,  # > 1000 RPS
                good_threshold=500.0,  # > 500 RPS
                acceptable_threshold=100.0,  # > 100 RPS
                degraded_threshold=50.0,  # > 50 RPS
                unit="rps",
                higher_is_better=True,
            ),
            PerformanceBenchmark(
                metric_name="api_error_rate",
                excellent_threshold=0.001,  # < 0.1%
                good_threshold=0.01,  # < 1%
                acceptable_threshold=0.05,  # < 5%
                degraded_threshold=0.10,  # < 10%
                unit="percentage",
                higher_is_better=False,
            ),
            # Database Performance
            PerformanceBenchmark(
                metric_name="db_query_time_p95",
                excellent_threshold=50.0,  # < 50ms
                good_threshold=100.0,  # < 100ms
                acceptable_threshold=250.0,  # < 250ms
                degraded_threshold=500.0,  # < 500ms
                unit="ms",
                higher_is_better=False,
            ),
            PerformanceBenchmark(
                metric_name="db_connection_pool_usage",
                excellent_threshold=50.0,  # < 50%
                good_threshold=70.0,  # < 70%
                acceptable_threshold=85.0,  # < 85%
                degraded_threshold=95.0,  # < 95%
                unit="percentage",
                higher_is_better=False,
            ),
            # Business Performance
            PerformanceBenchmark(
                metric_name="reservation_processing_time",
                excellent_threshold=2.0,  # < 2s
                good_threshold=5.0,  # < 5s
                acceptable_threshold=10.0,  # < 10s
                degraded_threshold=30.0,  # < 30s
                unit="seconds",
                higher_is_better=False,
            ),
            PerformanceBenchmark(
                metric_name="guest_response_time",
                excellent_threshold=30.0,  # < 30s
                good_threshold=60.0,  # < 1min
                acceptable_threshold=300.0,  # < 5min
                degraded_threshold=600.0,  # < 10min
                unit="seconds",
                higher_is_better=False,
            ),
            # System Resources
            PerformanceBenchmark(
                metric_name="cpu_usage",
                excellent_threshold=30.0,  # < 30%
                good_threshold=50.0,  # < 50%
                acceptable_threshold=70.0,  # < 70%
                degraded_threshold=85.0,  # < 85%
                unit="percentage",
                higher_is_better=False,
            ),
            PerformanceBenchmark(
                metric_name="memory_usage",
                excellent_threshold=40.0,  # < 40%
                good_threshold=60.0,  # < 60%
                acceptable_threshold=80.0,  # < 80%
                degraded_threshold=90.0,  # < 90%
                unit="percentage",
                higher_is_better=False,
            ),
            PerformanceBenchmark(
                metric_name="cache_hit_rate",
                excellent_threshold=95.0,  # > 95%
                good_threshold=90.0,  # > 90%
                acceptable_threshold=80.0,  # > 80%
                degraded_threshold=70.0,  # > 70%
                unit="percentage",
                higher_is_better=True,
            ),
        ]

        for benchmark in benchmarks:
            self.benchmarks[benchmark.metric_name] = benchmark

        logger.info(f"Initialized {len(benchmarks)} performance benchmarks")

    async def record_metric(self, metric: PerformanceMetric):
        """Record a performance metric"""

        # Store in buffer
        self.metrics_buffer[metric.name].append(metric)

        # Store in Redis for persistence
        metric_key = f"perf_metric:{metric.name}:{int(metric.timestamp.timestamp())}"
        await self.redis.setex(
            metric_key,
            86400 * 7,  # 7 days retention
            json.dumps(asdict(metric), default=str),
        )

        # Update real-time analytics
        await self._update_real_time_analytics(metric)

    @asynccontextmanager
    async def measure_operation(self, operation_name: str, tags: Dict[str, str] = None):
        """Context manager to measure operation performance"""

        start_time = time.time()
        exception_occurred = False

        try:
            yield
        except Exception:
            exception_occurred = True
            raise
        finally:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000

            # Record latency metric
            latency_metric = PerformanceMetric(
                name=f"{operation_name}_latency",
                type=PerformanceMetricType.LATENCY,
                value=duration_ms,
                unit="ms",
                timestamp=datetime.utcnow(),
                tags=tags or {},
            )

            await self.record_metric(latency_metric)

            # Record error if applicable
            if exception_occurred:
                error_metric = PerformanceMetric(
                    name=f"{operation_name}_errors",
                    type=PerformanceMetricType.ERROR_RATE,
                    value=1.0,
                    unit="count",
                    timestamp=datetime.utcnow(),
                    tags=tags or {},
                )

                await self.record_metric(error_metric)

    async def analyze_performance(self, hours: int = 24) -> PerformanceReport:
        """Analyze performance over specified period"""

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        # Get metrics for analysis period
        period_metrics = await self._get_period_metrics(start_time, end_time)

        # Analyze each metric
        metric_summaries = {}
        overall_scores = []

        for metric_name, metrics in period_metrics.items():
            if not metrics:
                continue

            summary = await self._analyze_metric_performance(metric_name, metrics)
            metric_summaries[metric_name] = summary

            if summary.get("performance_score"):
                overall_scores.append(summary["performance_score"])

        # Calculate overall performance score
        overall_score = statistics.mean(overall_scores) if overall_scores else 0.0
        overall_status = self._determine_performance_status(overall_score)

        # Generate optimization recommendations
        recommendations = await self._generate_recommendations(metric_summaries)

        # Analyze trends
        trends = await self._analyze_trends(period_metrics)

        # Count alerts (this would integrate with alerting service)
        alerts_triggered = await self._count_performance_alerts(start_time, end_time)

        report = PerformanceReport(
            period_start=start_time,
            period_end=end_time,
            overall_status=overall_status,
            metric_summaries=metric_summaries,
            recommendations=recommendations,
            trends=trends,
            alerts_triggered=alerts_triggered,
            performance_score=overall_score,
        )

        # Cache report
        report_key = f"perf_report:{int(start_time.timestamp())}:{hours}"
        await self.redis.setex(
            report_key,
            3600,  # 1 hour cache
            json.dumps(asdict(report), default=str),
        )

        return report

    async def get_real_time_metrics(self) -> Dict[str, PerformanceMetric]:
        """Get real-time performance metrics"""

        real_time_metrics = {}

        # Get latest metrics from buffer
        for metric_name, metrics_deque in self.metrics_buffer.items():
            if metrics_deque:
                # Get metrics from last 5 minutes
                five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
                recent_metrics = [m for m in metrics_deque if m.timestamp > five_minutes_ago]

                if recent_metrics:
                    # Calculate aggregated metric
                    values = [m.value for m in recent_metrics]

                    aggregated_metric = PerformanceMetric(
                        name=metric_name,
                        type=recent_metrics[0].type,
                        value=statistics.mean(values),
                        unit=recent_metrics[0].unit,
                        timestamp=datetime.utcnow(),
                        percentiles={
                            "p50": statistics.median(values),
                            "p95": self._calculate_percentile(values, 95),
                            "p99": self._calculate_percentile(values, 99),
                        },
                        trend=self._calculate_trend(values),
                    )

                    real_time_metrics[metric_name] = aggregated_metric

        return real_time_metrics

    async def get_performance_insights(self, metric_name: str, hours: int = 24) -> Dict[str, Any]:
        """Get detailed insights for specific metric"""

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        # Get historical data
        metrics = await self._get_metric_history(metric_name, start_time, end_time)

        if not metrics:
            return {"error": "No data available"}

        values = [m.value for m in metrics]

        # Statistical analysis
        insights = {
            "metric_name": metric_name,
            "period": f"{hours} hours",
            "data_points": len(values),
            "statistics": {
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                "min": min(values),
                "max": max(values),
                "percentiles": {
                    "p50": self._calculate_percentile(values, 50),
                    "p90": self._calculate_percentile(values, 90),
                    "p95": self._calculate_percentile(values, 95),
                    "p99": self._calculate_percentile(values, 99),
                },
            },
            "trend_analysis": self._analyze_trend_detailed(values),
            "anomaly_detection": await self._detect_anomalies(metric_name, values),
            "performance_status": self._evaluate_metric_status(metric_name, statistics.mean(values)),
            "recommendations": await self._get_metric_specific_recommendations(metric_name, values),
        }

        return insights

    async def optimize_performance(self, recommendation_id: str) -> Dict[str, Any]:
        """Apply performance optimization recommendation"""

        # This would implement actual optimization actions
        # For now, return simulation of optimization

        optimization_result = {
            "recommendation_id": recommendation_id,
            "status": "applied",
            "applied_at": datetime.utcnow().isoformat(),
            "expected_improvements": {
                "api_response_time": {"reduction": "15-25%"},
                "throughput": {"increase": "10-20%"},
                "error_rate": {"reduction": "20-30%"},
            },
            "monitoring_period": "24 hours",
            "rollback_available": True,
        }

        logger.info(f"Applied optimization: {recommendation_id}")

        return optimization_result

    async def _update_real_time_analytics(self, metric: PerformanceMetric):
        """Update real-time analytics with new metric"""

        # Update moving averages
        analytics_key = f"realtime_analytics:{metric.name}"
        current_data = await self.redis.get(analytics_key)

        if current_data:
            analytics = json.loads(current_data)
        else:
            analytics = {
                "count": 0,
                "sum": 0.0,
                "sum_squares": 0.0,
                "min": float("inf"),
                "max": float("-inf"),
                "last_updated": datetime.utcnow().isoformat(),
            }

        # Update analytics
        analytics["count"] += 1
        analytics["sum"] += metric.value
        analytics["sum_squares"] += metric.value * metric.value
        analytics["min"] = min(analytics["min"], metric.value)
        analytics["max"] = max(analytics["max"], metric.value)
        analytics["last_updated"] = datetime.utcnow().isoformat()

        # Calculate derived metrics
        if analytics["count"] > 0:
            analytics["mean"] = analytics["sum"] / analytics["count"]

            if analytics["count"] > 1:
                variance = (analytics["sum_squares"] / analytics["count"]) - (analytics["mean"] ** 2)
                analytics["std_dev"] = variance**0.5 if variance > 0 else 0.0

        # Store updated analytics
        await self.redis.setex(analytics_key, 3600, json.dumps(analytics))

    async def _get_period_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, List[PerformanceMetric]]:
        """Get all metrics for a specific period"""

        period_metrics = defaultdict(list)

        # Get from buffer first (most recent data)
        for metric_name, metrics_deque in self.metrics_buffer.items():
            for metric in metrics_deque:
                if start_time <= metric.timestamp <= end_time:
                    period_metrics[metric_name].append(metric)

        # Get from Redis for older data if needed
        # This is a simplified implementation

        return dict(period_metrics)

    async def _analyze_metric_performance(self, metric_name: str, metrics: List[PerformanceMetric]) -> Dict[str, Any]:
        """Analyze performance for a specific metric"""

        if not metrics:
            return {}

        values = [m.value for m in metrics]

        # Get benchmark
        benchmark = self.benchmarks.get(metric_name)

        # Calculate statistics
        mean_value = statistics.mean(values)
        p95_value = self._calculate_percentile(values, 95)

        # Determine performance status
        status = self._evaluate_metric_status(metric_name, mean_value)

        # Calculate performance score (0-100)
        performance_score = self._calculate_performance_score(metric_name, mean_value)

        # Trend analysis
        trend = self._calculate_trend(values)

        summary = {
            "metric_name": metric_name,
            "data_points": len(values),
            "mean": mean_value,
            "p95": p95_value,
            "min": min(values),
            "max": max(values),
            "status": status,
            "performance_score": performance_score,
            "trend": trend,
            "benchmark": asdict(benchmark) if benchmark else None,
        }

        return summary

    async def _generate_recommendations(
        self, metric_summaries: Dict[str, Dict[str, Any]]
    ) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations based on performance analysis"""

        recommendations = []

        # API Performance Recommendations
        api_latency_summary = metric_summaries.get("api_response_time_p95")
        if api_latency_summary and api_latency_summary.get("status") in ["degraded", "critical"]:
            recommendations.append(
                OptimizationRecommendation(
                    id="opt_api_latency_caching",
                    type=OptimizationType.CACHING,
                    title="Implement Advanced API Response Caching",
                    description="High API latency detected. Implement Redis-based response caching for frequently accessed endpoints.",
                    priority="high",
                    impact_estimate="25-40% latency reduction",
                    effort_estimate="2-3 days",
                    affected_metrics=["api_response_time_p95", "cache_hit_rate"],
                    implementation_steps=[
                        "Analyze most frequently called endpoints",
                        "Implement Redis caching layer",
                        "Add cache invalidation logic",
                        "Monitor cache hit rates",
                    ],
                    expected_improvement={
                        "api_response_time_p95": 0.35,  # 35% improvement
                        "cache_hit_rate": 0.90,
                    },
                    created_at=datetime.utcnow(),
                )
            )

        # Database Performance Recommendations
        db_query_summary = metric_summaries.get("db_query_time_p95")
        if db_query_summary and db_query_summary.get("status") in ["degraded", "critical"]:
            recommendations.append(
                OptimizationRecommendation(
                    id="opt_db_indexing",
                    type=OptimizationType.DATABASE,
                    title="Optimize Database Indexes",
                    description="Slow database queries detected. Analyze and optimize database indexes.",
                    priority="high",
                    impact_estimate="40-60% query time reduction",
                    effort_estimate="3-5 days",
                    affected_metrics=["db_query_time_p95", "api_response_time_p95"],
                    implementation_steps=[
                        "Analyze slow query logs",
                        "Identify missing indexes",
                        "Create composite indexes for complex queries",
                        "Update query execution plans",
                    ],
                    expected_improvement={
                        "db_query_time_p95": 0.50,  # 50% improvement
                        "api_response_time_p95": 0.20,  # 20% improvement
                    },
                    created_at=datetime.utcnow(),
                )
            )

        # Resource Usage Recommendations
        cpu_summary = metric_summaries.get("cpu_usage")
        if cpu_summary and cpu_summary.get("status") in ["degraded", "critical"]:
            recommendations.append(
                OptimizationRecommendation(
                    id="opt_horizontal_scaling",
                    type=OptimizationType.SCALING,
                    title="Implement Horizontal Scaling",
                    description="High CPU usage detected. Consider horizontal scaling to distribute load.",
                    priority="medium",
                    impact_estimate="50-70% CPU usage reduction",
                    effort_estimate="1-2 weeks",
                    affected_metrics=["cpu_usage", "api_throughput", "api_response_time_p95"],
                    implementation_steps=[
                        "Set up load balancer",
                        "Configure auto-scaling policies",
                        "Deploy additional application instances",
                        "Monitor load distribution",
                    ],
                    expected_improvement={
                        "cpu_usage": 0.60,  # 60% reduction
                        "api_throughput": 2.0,  # 100% increase
                    },
                    created_at=datetime.utcnow(),
                )
            )

        # Business Process Recommendations
        reservation_summary = metric_summaries.get("reservation_processing_time")
        if reservation_summary and reservation_summary.get("status") in ["degraded", "critical"]:
            recommendations.append(
                OptimizationRecommendation(
                    id="opt_async_processing",
                    type=OptimizationType.CODE,
                    title="Implement Async Reservation Processing",
                    description="Slow reservation processing detected. Implement asynchronous processing for complex operations.",
                    priority="high",
                    impact_estimate="60-80% processing time reduction",
                    effort_estimate="1 week",
                    affected_metrics=["reservation_processing_time", "guest_response_time"],
                    implementation_steps=[
                        "Identify blocking operations in reservation flow",
                        "Implement async task queue",
                        "Add progress tracking for guests",
                        "Optimize database transactions",
                    ],
                    expected_improvement={
                        "reservation_processing_time": 0.70,  # 70% improvement
                        "guest_response_time": 0.30,  # 30% improvement
                    },
                    created_at=datetime.utcnow(),
                )
            )

        return recommendations

    async def _analyze_trends(self, period_metrics: Dict[str, List[PerformanceMetric]]) -> Dict[str, str]:
        """Analyze performance trends"""

        trends = {}

        for metric_name, metrics in period_metrics.items():
            if len(metrics) < 10:  # Need sufficient data points
                continue

            values = [m.value for m in sorted(metrics, key=lambda x: x.timestamp)]
            trend = self._calculate_trend(values)
            trends[metric_name] = trend

        return trends

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction for values"""

        if len(values) < 2:
            return "stable"

        # Simple trend calculation using first and last quarters
        quarter_size = len(values) // 4
        if quarter_size == 0:
            quarter_size = 1

        first_quarter = values[:quarter_size]
        last_quarter = values[-quarter_size:]

        first_avg = statistics.mean(first_quarter)
        last_avg = statistics.mean(last_quarter)

        change_percent = ((last_avg - first_avg) / first_avg) * 100 if first_avg != 0 else 0

        if change_percent > 5:
            return "increasing"
        elif change_percent < -5:
            return "decreasing"
        else:
            return "stable"

    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value"""

        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)

        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower_index = int(index)
            upper_index = lower_index + 1
            weight = index - lower_index

            if upper_index >= len(sorted_values):
                return sorted_values[lower_index]

            return sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight

    def _evaluate_metric_status(self, metric_name: str, value: float) -> PerformanceStatus:
        """Evaluate performance status for a metric"""

        benchmark = self.benchmarks.get(metric_name)
        if not benchmark:
            return PerformanceStatus.ACCEPTABLE

        if benchmark.higher_is_better:
            if value >= benchmark.excellent_threshold:
                return PerformanceStatus.EXCELLENT
            elif value >= benchmark.good_threshold:
                return PerformanceStatus.GOOD
            elif value >= benchmark.acceptable_threshold:
                return PerformanceStatus.ACCEPTABLE
            elif value >= benchmark.degraded_threshold:
                return PerformanceStatus.DEGRADED
            else:
                return PerformanceStatus.CRITICAL
        else:
            if value <= benchmark.excellent_threshold:
                return PerformanceStatus.EXCELLENT
            elif value <= benchmark.good_threshold:
                return PerformanceStatus.GOOD
            elif value <= benchmark.acceptable_threshold:
                return PerformanceStatus.ACCEPTABLE
            elif value <= benchmark.degraded_threshold:
                return PerformanceStatus.DEGRADED
            else:
                return PerformanceStatus.CRITICAL

    def _calculate_performance_score(self, metric_name: str, value: float) -> float:
        """Calculate performance score (0-100) for a metric"""

        benchmark = self.benchmarks.get(metric_name)
        if not benchmark:
            return 50.0  # Neutral score

        if benchmark.higher_is_better:
            if value >= benchmark.excellent_threshold:
                return 100.0
            elif value >= benchmark.good_threshold:
                # Linear interpolation between good and excellent
                range_size = benchmark.excellent_threshold - benchmark.good_threshold
                progress = (value - benchmark.good_threshold) / range_size if range_size > 0 else 0
                return 80.0 + (20.0 * progress)
            elif value >= benchmark.acceptable_threshold:
                range_size = benchmark.good_threshold - benchmark.acceptable_threshold
                progress = (value - benchmark.acceptable_threshold) / range_size if range_size > 0 else 0
                return 60.0 + (20.0 * progress)
            elif value >= benchmark.degraded_threshold:
                range_size = benchmark.acceptable_threshold - benchmark.degraded_threshold
                progress = (value - benchmark.degraded_threshold) / range_size if range_size > 0 else 0
                return 30.0 + (30.0 * progress)
            else:
                return max(0.0, min(30.0, value / benchmark.degraded_threshold * 30.0))
        else:
            if value <= benchmark.excellent_threshold:
                return 100.0
            elif value <= benchmark.good_threshold:
                range_size = benchmark.good_threshold - benchmark.excellent_threshold
                progress = (benchmark.good_threshold - value) / range_size if range_size > 0 else 0
                return 80.0 + (20.0 * progress)
            elif value <= benchmark.acceptable_threshold:
                range_size = benchmark.acceptable_threshold - benchmark.good_threshold
                progress = (benchmark.acceptable_threshold - value) / range_size if range_size > 0 else 0
                return 60.0 + (20.0 * progress)
            elif value <= benchmark.degraded_threshold:
                range_size = benchmark.degraded_threshold - benchmark.acceptable_threshold
                progress = (benchmark.degraded_threshold - value) / range_size if range_size > 0 else 0
                return 30.0 + (30.0 * progress)
            else:
                # Critical performance - score decreases as value increases beyond degraded threshold
                return max(0.0, 30.0 - ((value - benchmark.degraded_threshold) / benchmark.degraded_threshold * 30.0))

    def _determine_performance_status(self, overall_score: float) -> PerformanceStatus:
        """Determine overall performance status from score"""

        if overall_score >= 90:
            return PerformanceStatus.EXCELLENT
        elif overall_score >= 75:
            return PerformanceStatus.GOOD
        elif overall_score >= 60:
            return PerformanceStatus.ACCEPTABLE
        elif overall_score >= 40:
            return PerformanceStatus.DEGRADED
        else:
            return PerformanceStatus.CRITICAL

    async def _count_performance_alerts(self, start_time: datetime, end_time: datetime) -> int:
        """Count performance-related alerts in period"""

        # This would integrate with the alerting service
        # For now, return a simulated count
        return 5

    async def _get_metric_history(
        self, metric_name: str, start_time: datetime, end_time: datetime
    ) -> List[PerformanceMetric]:
        """Get historical data for a specific metric"""

        metrics = []

        # Get from buffer
        if metric_name in self.metrics_buffer:
            for metric in self.metrics_buffer[metric_name]:
                if start_time <= metric.timestamp <= end_time:
                    metrics.append(metric)

        return sorted(metrics, key=lambda x: x.timestamp)

    def _analyze_trend_detailed(self, values: List[float]) -> Dict[str, Any]:
        """Detailed trend analysis"""

        if len(values) < 5:
            return {"trend": "insufficient_data"}

        # Calculate trend using linear regression
        x = list(range(len(values)))
        n = len(values)

        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(xi * xi for xi in x)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)

        trend_strength = abs(slope) / (statistics.stdev(values) if len(values) > 1 else 1)

        if trend_strength < 0.1:
            trend_direction = "stable"
        elif slope > 0:
            trend_direction = "increasing"
        else:
            trend_direction = "decreasing"

        return {
            "trend": trend_direction,
            "slope": slope,
            "strength": trend_strength,
            "confidence": min(trend_strength * 100, 100),
        }

    async def _detect_anomalies(self, metric_name: str, values: List[float]) -> Dict[str, Any]:
        """Detect anomalies in metric values"""

        if len(values) < 10:
            return {"anomalies_detected": False, "reason": "insufficient_data"}

        # Simple anomaly detection using statistical methods
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values)

        anomalies = []
        threshold = 2.5  # 2.5 standard deviations

        for i, value in enumerate(values):
            z_score = abs((value - mean_val) / std_val) if std_val > 0 else 0
            if z_score > threshold:
                anomalies.append(
                    {"index": i, "value": value, "z_score": z_score, "severity": "high" if z_score > 3 else "medium"}
                )

        return {
            "anomalies_detected": len(anomalies) > 0,
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "anomaly_rate": len(anomalies) / len(values) * 100,
        }

    async def _get_metric_specific_recommendations(self, metric_name: str, values: List[float]) -> List[str]:
        """Get recommendations specific to a metric"""

        recommendations = []

        if not values:
            return recommendations

        mean_val = statistics.mean(values)
        trend = self._calculate_trend(values)

        # API Response Time recommendations
        if "response_time" in metric_name and mean_val > 1000:  # > 1 second
            recommendations.extend(
                [
                    "Implement response caching for static content",
                    "Optimize database queries with proper indexing",
                    "Consider async processing for heavy operations",
                    "Enable compression for API responses",
                ]
            )

        # Database recommendations
        if "db_query" in metric_name and mean_val > 100:  # > 100ms
            recommendations.extend(
                [
                    "Analyze and optimize slow queries",
                    "Add missing database indexes",
                    "Consider query result caching",
                    "Review database connection pooling",
                ]
            )

        # Throughput recommendations
        if "throughput" in metric_name and trend == "decreasing":
            recommendations.extend(
                [
                    "Scale horizontally to handle more concurrent requests",
                    "Optimize application bottlenecks",
                    "Review rate limiting configurations",
                    "Consider load balancing improvements",
                ]
            )

        # Error rate recommendations
        if "error_rate" in metric_name and mean_val > 0.05:  # > 5%
            recommendations.extend(
                [
                    "Implement comprehensive error handling",
                    "Add circuit breaker patterns for external services",
                    "Review and fix recurring error patterns",
                    "Improve input validation and sanitization",
                ]
            )

        return recommendations

    def _start_background_tasks(self):
        """Start background performance monitoring tasks"""

        # Start continuous performance analysis
        asyncio.create_task(self._continuous_analysis())

        # Start performance optimization suggestions
        asyncio.create_task(self._optimization_advisor())

    async def _continuous_analysis(self):
        """Continuous performance analysis"""

        while True:
            try:
                # Analyze performance every 5 minutes
                real_time_metrics = await self.get_real_time_metrics()

                # Check for performance degradation
                for metric_name, metric in real_time_metrics.items():
                    status = self._evaluate_metric_status(metric_name, metric.value)

                    if status in [PerformanceStatus.DEGRADED, PerformanceStatus.CRITICAL]:
                        logger.warning(f"Performance degradation detected: {metric_name} = {metric.value} ({status})")

                await asyncio.sleep(300)  # 5 minutes

            except Exception as e:
                logger.error(f"Error in continuous analysis: {e}")
                await asyncio.sleep(300)

    async def _optimization_advisor(self):
        """Background optimization advisor"""

        while True:
            try:
                # Generate optimization suggestions every hour
                report = await self.analyze_performance(hours=1)

                if report.recommendations:
                    logger.info(f"Generated {len(report.recommendations)} optimization recommendations")

                await asyncio.sleep(3600)  # 1 hour

            except Exception as e:
                logger.error(f"Error in optimization advisor: {e}")
                await asyncio.sleep(3600)


# Create singleton instance
performance_service = None


async def get_performance_service() -> PerformanceMonitoringService:
    """Get performance monitoring service instance"""
    global performance_service
    if performance_service is None:
        # This would be initialized with actual Redis and metrics service
        performance_service = PerformanceMonitoringService(None, None)
    return performance_service
