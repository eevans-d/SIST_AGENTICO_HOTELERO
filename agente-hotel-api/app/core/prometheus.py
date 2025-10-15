"""
Prometheus Metrics Integration Module

This module provides comprehensive Prometheus metrics for the hotel agent system,
including business metrics, performance metrics, and SLO compliance tracking.

Key Features:
- Custom metrics registration
- Business metrics (reservations, bookings, revenue)
- Performance metrics (latency, throughput, errors)
- SLO compliance tracking
- Automated metric collection
- Multi-dimensional labels

Usage:
    from app.core.prometheus import metrics
    
    # Track reservation
    metrics.reservations_total.labels(status="confirmed", source="whatsapp").inc()
    
    # Track latency
    with metrics.request_latency.labels(endpoint="/api/reservations", method="POST").time():
        result = await process_reservation()

Author: AI Agent
Date: October 14, 2025
Version: 1.0.0
"""

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    Summary,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from typing import Dict, Any, Optional, List
from functools import wraps
import time
from contextlib import contextmanager
import structlog

logger = structlog.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# PROMETHEUS REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

# Use default registry for automatic collection
registry = CollectorRegistry()


# ═══════════════════════════════════════════════════════════════════════════
# APPLICATION INFO METRICS
# ═══════════════════════════════════════════════════════════════════════════

app_info = Info(
    name="agente_hotel_app",
    documentation="Application information and metadata",
    registry=registry,
)

# Set application metadata
app_info.info(
    {
        "version": "1.0.0",
        "environment": "production",
        "service": "agente-hotel-api",
        "framework": "fastapi",
    }
)


# ═══════════════════════════════════════════════════════════════════════════
# HTTP REQUEST METRICS
# ═══════════════════════════════════════════════════════════════════════════

http_requests_total = Counter(
    name="http_requests_total",
    documentation="Total HTTP requests by method, endpoint, and status",
    labelnames=["method", "endpoint", "status_code"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    name="http_request_duration_seconds",
    documentation="HTTP request latency in seconds",
    labelnames=["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
    registry=registry,
)

http_request_size_bytes = Summary(
    name="http_request_size_bytes",
    documentation="HTTP request size in bytes",
    labelnames=["method", "endpoint"],
    registry=registry,
)

http_response_size_bytes = Summary(
    name="http_response_size_bytes",
    documentation="HTTP response size in bytes",
    labelnames=["method", "endpoint"],
    registry=registry,
)

http_requests_in_progress = Gauge(
    name="http_requests_in_progress",
    documentation="Number of HTTP requests currently in progress",
    labelnames=["method", "endpoint"],
    registry=registry,
)


# ═══════════════════════════════════════════════════════════════════════════
# BUSINESS METRICS - RESERVATIONS
# ═══════════════════════════════════════════════════════════════════════════

reservations_total = Counter(
    name="reservations_total",
    documentation="Total number of reservations by status and source",
    labelnames=["status", "source", "room_type"],
    registry=registry,
)

reservations_revenue_total = Counter(
    name="reservations_revenue_total",
    documentation="Total revenue from reservations in currency units",
    labelnames=["currency", "room_type"],
    registry=registry,
)

reservations_duration_nights = Histogram(
    name="reservations_duration_nights",
    documentation="Distribution of reservation durations in nights",
    labelnames=["room_type"],
    buckets=(1, 2, 3, 5, 7, 10, 14, 21, 30),
    registry=registry,
)

reservations_processing_time_seconds = Histogram(
    name="reservations_processing_time_seconds",
    documentation="Time to process reservation from request to confirmation",
    labelnames=["status"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
    registry=registry,
)

reservations_active = Gauge(
    name="reservations_active",
    documentation="Number of currently active reservations",
    labelnames=["room_type"],
    registry=registry,
)

reservations_pending = Gauge(
    name="reservations_pending",
    documentation="Number of pending reservations awaiting confirmation",
    registry=registry,
)


# ═══════════════════════════════════════════════════════════════════════════
# BUSINESS METRICS - GUESTS
# ═══════════════════════════════════════════════════════════════════════════

guests_total = Counter(
    name="guests_total",
    documentation="Total number of unique guests",
    labelnames=["source"],
    registry=registry,
)

guests_active = Gauge(
    name="guests_active",
    documentation="Number of guests currently checked in",
    registry=registry,
)

guest_satisfaction_score = Histogram(
    name="guest_satisfaction_score",
    documentation="Guest satisfaction scores (1-10)",
    buckets=(1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
    registry=registry,
)

guest_interactions_total = Counter(
    name="guest_interactions_total",
    documentation="Total guest interactions by channel and type",
    labelnames=["channel", "interaction_type"],
    registry=registry,
)


# ═══════════════════════════════════════════════════════════════════════════
# BUSINESS METRICS - ROOMS
# ═══════════════════════════════════════════════════════════════════════════

rooms_total = Gauge(
    name="rooms_total",
    documentation="Total number of rooms by type and status",
    labelnames=["room_type", "status"],
    registry=registry,
)

rooms_occupancy_rate = Gauge(
    name="rooms_occupancy_rate",
    documentation="Room occupancy rate (0.0-1.0)",
    labelnames=["room_type"],
    registry=registry,
)

rooms_available = Gauge(
    name="rooms_available",
    documentation="Number of rooms currently available",
    labelnames=["room_type"],
    registry=registry,
)


# ═══════════════════════════════════════════════════════════════════════════
# PMS INTEGRATION METRICS
# ═══════════════════════════════════════════════════════════════════════════

pms_operations_total = Counter(
    name="pms_operations_total",
    documentation="Total PMS operations by operation type and status",
    labelnames=["operation", "status"],
    registry=registry,
)

pms_api_latency_seconds = Histogram(
    name="pms_api_latency_seconds",
    documentation="PMS API call latency in seconds",
    labelnames=["endpoint", "method"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=registry,
)

pms_circuit_breaker_state = Gauge(
    name="pms_circuit_breaker_state",
    documentation="PMS circuit breaker state (0=closed, 1=open, 2=half-open)",
    registry=registry,
)

pms_cache_hits_total = Counter(
    name="pms_cache_hits_total",
    documentation="Total PMS cache hits",
    labelnames=["operation"],
    registry=registry,
)

pms_cache_misses_total = Counter(
    name="pms_cache_misses_total",
    documentation="Total PMS cache misses",
    labelnames=["operation"],
    registry=registry,
)


# ═══════════════════════════════════════════════════════════════════════════
# MESSAGING METRICS
# ═══════════════════════════════════════════════════════════════════════════

messages_total = Counter(
    name="messages_total",
    documentation="Total messages by channel and direction",
    labelnames=["channel", "direction", "message_type"],
    registry=registry,
)

messages_processing_time_seconds = Histogram(
    name="messages_processing_time_seconds",
    documentation="Message processing time in seconds",
    labelnames=["channel", "message_type"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
    registry=registry,
)

messages_errors_total = Counter(
    name="messages_errors_total",
    documentation="Total message processing errors",
    labelnames=["channel", "error_type"],
    registry=registry,
)

whatsapp_messages_sent_total = Counter(
    name="whatsapp_messages_sent_total",
    documentation="Total WhatsApp messages sent by template",
    labelnames=["template_name", "status"],
    registry=registry,
)

whatsapp_messages_delivered_total = Counter(
    name="whatsapp_messages_delivered_total",
    documentation="Total WhatsApp messages delivered",
    registry=registry,
)

whatsapp_messages_read_total = Counter(
    name="whatsapp_messages_read_total",
    documentation="Total WhatsApp messages read by recipients",
    registry=registry,
)


# ═══════════════════════════════════════════════════════════════════════════
# NLP METRICS
# ═══════════════════════════════════════════════════════════════════════════

nlp_intent_classification_total = Counter(
    name="nlp_intent_classification_total",
    documentation="Total NLP intent classifications",
    labelnames=["intent", "confidence_level"],
    registry=registry,
)

nlp_processing_time_seconds = Histogram(
    name="nlp_processing_time_seconds",
    documentation="NLP processing time in seconds",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=registry,
)

nlp_confidence_score = Histogram(
    name="nlp_confidence_score",
    documentation="NLP confidence scores (0.0-1.0)",
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
    registry=registry,
)


# ═══════════════════════════════════════════════════════════════════════════
# SLO COMPLIANCE METRICS
# ═══════════════════════════════════════════════════════════════════════════

slo_latency_p95_seconds = Gauge(
    name="slo_latency_p95_seconds",
    documentation="P95 latency SLO value (target: <3s)",
    labelnames=["endpoint"],
    registry=registry,
)

slo_latency_p99_seconds = Gauge(
    name="slo_latency_p99_seconds",
    documentation="P99 latency SLO value (target: <5s)",
    labelnames=["endpoint"],
    registry=registry,
)

slo_error_rate = Gauge(
    name="slo_error_rate",
    documentation="Error rate SLO value (target: <1%)",
    labelnames=["endpoint"],
    registry=registry,
)

slo_availability = Gauge(
    name="slo_availability",
    documentation="Service availability SLO (target: >99.9%)",
    registry=registry,
)

slo_compliance_status = Gauge(
    name="slo_compliance_status",
    documentation="SLO compliance status (1=compliant, 0=violation)",
    labelnames=["slo_name"],
    registry=registry,
)


# ═══════════════════════════════════════════════════════════════════════════
# DATABASE METRICS
# ═══════════════════════════════════════════════════════════════════════════

db_connections_total = Gauge(
    name="db_connections_total",
    documentation="Total database connections",
    labelnames=["database", "state"],
    registry=registry,
)

db_query_duration_seconds = Histogram(
    name="db_query_duration_seconds",
    documentation="Database query duration in seconds",
    labelnames=["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=registry,
)

db_operations_total = Counter(
    name="db_operations_total",
    documentation="Total database operations",
    labelnames=["operation", "table", "status"],
    registry=registry,
)


# ═══════════════════════════════════════════════════════════════════════════
# CACHE METRICS
# ═══════════════════════════════════════════════════════════════════════════

cache_operations_total = Counter(
    name="cache_operations_total",
    documentation="Total cache operations",
    labelnames=["operation", "status"],
    registry=registry,
)

cache_hit_rate = Gauge(
    name="cache_hit_rate",
    documentation="Cache hit rate (0.0-1.0)",
    registry=registry,
)

cache_size_bytes = Gauge(
    name="cache_size_bytes",
    documentation="Current cache size in bytes",
    registry=registry,
)

cache_evictions_total = Counter(
    name="cache_evictions_total",
    documentation="Total cache evictions",
    labelnames=["reason"],
    registry=registry,
)


# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM METRICS
# ═══════════════════════════════════════════════════════════════════════════

system_cpu_usage = Gauge(
    name="system_cpu_usage",
    documentation="System CPU usage percentage (0-100)",
    registry=registry,
)

system_memory_usage_bytes = Gauge(
    name="system_memory_usage_bytes",
    documentation="System memory usage in bytes",
    registry=registry,
)

system_uptime_seconds = Gauge(
    name="system_uptime_seconds",
    documentation="System uptime in seconds",
    registry=registry,
)


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS AND DECORATORS
# ═══════════════════════════════════════════════════════════════════════════


@contextmanager
def track_request_duration(method: str, endpoint: str):
    """
    Context manager to track HTTP request duration.
    
    Usage:
        with track_request_duration("GET", "/api/health"):
            result = await process_request()
    """
    http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()
    start_time = time.time()
    
    try:
        yield
    finally:
        duration = time.time() - start_time
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
        http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()


def track_reservation(status: str, source: str, room_type: str, revenue: float = 0.0, duration_nights: int = 1):
    """
    Track reservation metrics.
    
    Args:
        status: Reservation status (confirmed, pending, cancelled)
        source: Source channel (whatsapp, gmail, web)
        room_type: Type of room (standard, deluxe, suite)
        revenue: Revenue amount in default currency
        duration_nights: Duration of reservation in nights
    """
    reservations_total.labels(status=status, source=source, room_type=room_type).inc()
    
    if revenue > 0:
        reservations_revenue_total.labels(currency="USD", room_type=room_type).inc(revenue)
    
    if duration_nights > 0:
        reservations_duration_nights.labels(room_type=room_type).observe(duration_nights)
    
    logger.info(
        "reservation_tracked",
        status=status,
        source=source,
        room_type=room_type,
        revenue=revenue,
        duration_nights=duration_nights,
    )


def track_guest_interaction(channel: str, interaction_type: str):
    """
    Track guest interaction.
    
    Args:
        channel: Communication channel (whatsapp, gmail, phone)
        interaction_type: Type of interaction (inquiry, booking, complaint, feedback)
    """
    guest_interactions_total.labels(channel=channel, interaction_type=interaction_type).inc()


def track_pms_operation(operation: str, status: str, latency_seconds: float):
    """
    Track PMS operation metrics.
    
    Args:
        operation: PMS operation (check_availability, create_reservation, etc.)
        status: Operation status (success, error, timeout)
        latency_seconds: Operation latency in seconds
    """
    pms_operations_total.labels(operation=operation, status=status).inc()
    pms_api_latency_seconds.labels(endpoint=f"/api/{operation}", method="POST").observe(latency_seconds)


def track_message_processing(channel: str, message_type: str, processing_time: float, success: bool = True):
    """
    Track message processing metrics.
    
    Args:
        channel: Communication channel (whatsapp, gmail)
        message_type: Type of message (text, audio, image)
        processing_time: Processing time in seconds
        success: Whether processing was successful
    """
    direction = "inbound"
    messages_total.labels(channel=channel, direction=direction, message_type=message_type).inc()
    messages_processing_time_seconds.labels(channel=channel, message_type=message_type).observe(processing_time)
    
    if not success:
        messages_errors_total.labels(channel=channel, error_type="processing_failed").inc()


def update_room_metrics(room_type: str, total: int, available: int, occupancy_rate: float):
    """
    Update room availability metrics.
    
    Args:
        room_type: Type of room (standard, deluxe, suite)
        total: Total rooms of this type
        available: Available rooms
        occupancy_rate: Occupancy rate (0.0-1.0)
    """
    rooms_total.labels(room_type=room_type, status="total").set(total)
    rooms_available.labels(room_type=room_type).set(available)
    rooms_occupancy_rate.labels(room_type=room_type).set(occupancy_rate)


def update_slo_metrics(endpoint: str, p95_latency: float, p99_latency: float, error_rate: float):
    """
    Update SLO compliance metrics.
    
    Args:
        endpoint: API endpoint
        p95_latency: P95 latency in seconds
        p99_latency: P99 latency in seconds
        error_rate: Error rate (0.0-1.0)
    """
    slo_latency_p95_seconds.labels(endpoint=endpoint).set(p95_latency)
    slo_latency_p99_seconds.labels(endpoint=endpoint).set(p99_latency)
    slo_error_rate.labels(endpoint=endpoint).set(error_rate)
    
    # Check SLO compliance
    p95_compliant = p95_latency < 3.0
    p99_compliant = p99_latency < 5.0
    error_compliant = error_rate < 0.01
    
    slo_compliance_status.labels(slo_name=f"{endpoint}_p95_latency").set(1 if p95_compliant else 0)
    slo_compliance_status.labels(slo_name=f"{endpoint}_p99_latency").set(1 if p99_compliant else 0)
    slo_compliance_status.labels(slo_name=f"{endpoint}_error_rate").set(1 if error_compliant else 0)


def track_db_operation(operation: str, table: str, status: str, duration: float):
    """
    Track database operation metrics.
    
    Args:
        operation: Database operation (select, insert, update, delete)
        table: Table name
        status: Operation status (success, error)
        duration: Operation duration in seconds
    """
    db_operations_total.labels(operation=operation, table=table, status=status).inc()
    db_query_duration_seconds.labels(operation=operation, table=table).observe(duration)


def get_metrics() -> str:
    """
    Generate Prometheus metrics output in text format.
    
    Returns:
        str: Metrics in Prometheus exposition format
    """
    return generate_latest(registry).decode("utf-8")


def get_metrics_content_type() -> str:
    """
    Get the content type for Prometheus metrics.
    
    Returns:
        str: Content type header value
    """
    return CONTENT_TYPE_LATEST


# ═══════════════════════════════════════════════════════════════════════════
# METRICS COLLECTION CLASS
# ═══════════════════════════════════════════════════════════════════════════


class PrometheusMetrics:
    """
    Centralized class for managing Prometheus metrics.
    
    Provides convenient access to all metrics and helper functions.
    """
    
    def __init__(self):
        """Initialize Prometheus metrics manager."""
        self.registry = registry
        
        # HTTP metrics
        self.http_requests_total = http_requests_total
        self.http_request_duration_seconds = http_request_duration_seconds
        self.http_request_size_bytes = http_request_size_bytes
        self.http_response_size_bytes = http_response_size_bytes
        self.http_requests_in_progress = http_requests_in_progress
        
        # Business metrics
        self.reservations_total = reservations_total
        self.reservations_revenue_total = reservations_revenue_total
        self.reservations_duration_nights = reservations_duration_nights
        self.reservations_processing_time_seconds = reservations_processing_time_seconds
        self.reservations_active = reservations_active
        self.reservations_pending = reservations_pending
        
        self.guests_total = guests_total
        self.guests_active = guests_active
        self.guest_satisfaction_score = guest_satisfaction_score
        self.guest_interactions_total = guest_interactions_total
        
        self.rooms_total = rooms_total
        self.rooms_occupancy_rate = rooms_occupancy_rate
        self.rooms_available = rooms_available
        
        # PMS metrics
        self.pms_operations_total = pms_operations_total
        self.pms_api_latency_seconds = pms_api_latency_seconds
        self.pms_circuit_breaker_state = pms_circuit_breaker_state
        self.pms_cache_hits_total = pms_cache_hits_total
        self.pms_cache_misses_total = pms_cache_misses_total
        
        # Messaging metrics
        self.messages_total = messages_total
        self.messages_processing_time_seconds = messages_processing_time_seconds
        self.messages_errors_total = messages_errors_total
        self.whatsapp_messages_sent_total = whatsapp_messages_sent_total
        self.whatsapp_messages_delivered_total = whatsapp_messages_delivered_total
        self.whatsapp_messages_read_total = whatsapp_messages_read_total
        
        # NLP metrics
        self.nlp_intent_classification_total = nlp_intent_classification_total
        self.nlp_processing_time_seconds = nlp_processing_time_seconds
        self.nlp_confidence_score = nlp_confidence_score
        
        # SLO metrics
        self.slo_latency_p95_seconds = slo_latency_p95_seconds
        self.slo_latency_p99_seconds = slo_latency_p99_seconds
        self.slo_error_rate = slo_error_rate
        self.slo_availability = slo_availability
        self.slo_compliance_status = slo_compliance_status
        
        # Database metrics
        self.db_connections_total = db_connections_total
        self.db_query_duration_seconds = db_query_duration_seconds
        self.db_operations_total = db_operations_total
        
        # Cache metrics
        self.cache_operations_total = cache_operations_total
        self.cache_hit_rate = cache_hit_rate
        self.cache_size_bytes = cache_size_bytes
        self.cache_evictions_total = cache_evictions_total
        
        # System metrics
        self.system_cpu_usage = system_cpu_usage
        self.system_memory_usage_bytes = system_memory_usage_bytes
        self.system_uptime_seconds = system_uptime_seconds
        
        logger.info("prometheus_metrics_initialized", total_metrics=len(self.registry._collector_to_names))
    
    def export(self) -> str:
        """Export metrics in Prometheus format."""
        return get_metrics()
    
    def content_type(self) -> str:
        """Get Prometheus metrics content type."""
        return get_metrics_content_type()


# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL METRICS INSTANCE
# ═══════════════════════════════════════════════════════════════════════════

metrics = PrometheusMetrics()

__all__ = [
    "metrics",
    "track_request_duration",
    "track_reservation",
    "track_guest_interaction",
    "track_pms_operation",
    "track_message_processing",
    "update_room_metrics",
    "update_slo_metrics",
    "track_db_operation",
    "get_metrics",
    "get_metrics_content_type",
    "PrometheusMetrics",
]
