"""
OpenTelemetry Distributed Tracing Module

Provides comprehensive distributed tracing with OpenTelemetry.

Author: AI Agent
Date: October 14, 2025
Version: 1.0.0
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.trace import Status, StatusCode, SpanKind
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from typing import Optional
from functools import wraps
import structlog
import os

logger = structlog.get_logger(__name__)

# Configuration (externalized via environment variables)
TRACE_CONFIG = {
    "service_name": os.getenv("OTEL_SERVICE_NAME", "agente-hotel-api"),
    "otlp_endpoint": os.getenv("OTLP_ENDPOINT", "http://jaeger:4317"),
    "sampling_rate": float(os.getenv("TRACE_SAMPLING_RATE", "1.0")),
}


def setup_tracing():
    """Setup OpenTelemetry tracing with configurable sampling."""
    resource = Resource.create({SERVICE_NAME: TRACE_CONFIG["service_name"]})
    
    # Configure sampler based on sampling_rate (0.0 to 1.0)
    # ParentBased ensures distributed tracing consistency across services
    sampler = ParentBased(TraceIdRatioBased(TRACE_CONFIG["sampling_rate"]))
    provider = TracerProvider(resource=resource, sampler=sampler)

    try:
        otlp_exporter = OTLPSpanExporter(endpoint=TRACE_CONFIG["otlp_endpoint"], insecure=True)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info(
            "otlp_exporter_configured",
            endpoint=TRACE_CONFIG["otlp_endpoint"],
            sampling_rate=TRACE_CONFIG["sampling_rate"],
        )
    except Exception as e:
        logger.error("otlp_exporter_failed", error=str(e))

    trace.set_tracer_provider(provider)
    return provider


tracer_provider = setup_tracing()
tracer = trace.get_tracer(__name__)


def trace_function(name: Optional[str] = None, span_kind: SpanKind = SpanKind.INTERNAL):
    """Decorator to trace functions."""

    def decorator(func):
        span_name = name or func.__name__

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(span_name, kind=span_kind) as span:
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(span_name, kind=span_kind) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        import asyncio

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def enrich_span_from_request(span: trace.Span, request) -> None:
    """
    Enrich span with business context from FastAPI request.
    
    Extracts tenant_id, user_id, channel, correlation_id from request.state
    and adds them as span attributes for better observability.
    
    Args:
        span: OpenTelemetry Span to enrich
        request: FastAPI Request object with state attributes
        
    Example:
        >>> from opentelemetry import trace
        >>> span = trace.get_current_span()
        >>> enrich_span_from_request(span, request)
        # Span now has attributes: tenant.id, user.id, channel.type, request.correlation_id
    """
    if span is None or not span.is_recording():
        logger.warning("span_not_recording", operation="enrich_span_from_request")
        return
    
    # Tenant ID (multi-tenancy context)
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id:
        span.set_attribute("tenant.id", str(tenant_id))
    
    # User ID (guest identification)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        span.set_attribute("user.id", str(user_id))
    
    # Channel (WhatsApp, Gmail, SMS, etc.)
    channel = getattr(request.state, "channel", None) or getattr(request.state, "canal", None)
    if channel:
        span.set_attribute("channel.type", str(channel))
    
    # Correlation ID (request tracing across services)
    correlation_id = getattr(request.state, "correlation_id", None)
    if correlation_id:
        span.set_attribute("request.correlation_id", str(correlation_id))
    
    # HTTP method and path (if not already set by middleware)
    if hasattr(request, "method"):
        span.set_attribute("http.method", request.method)
    if hasattr(request, "url") and hasattr(request.url, "path"):
        span.set_attribute("http.route", request.url.path)
    
    logger.debug(
        "span_enriched",
        tenant_id=tenant_id,
        user_id=user_id,
        channel=channel,
        correlation_id=correlation_id,
    )


def enrich_span_with_business_context(
    span: trace.Span,
    intent: Optional[str] = None,
    confidence: Optional[float] = None,
    operation: Optional[str] = None,
    **kwargs
) -> None:
    """
    Enrich span with business-specific context (intent, confidence, custom data).
    
    Args:
        span: OpenTelemetry Span to enrich
        intent: NLP intent detected (e.g., "check_availability", "make_reservation")
        confidence: NLP confidence score (0.0-1.0)
        operation: Business operation being performed
        **kwargs: Additional custom attributes (e.g., availability_date, room_type)
        
    Example:
        >>> span = trace.get_current_span()
        >>> enrich_span_with_business_context(
        ...     span,
        ...     intent="check_availability",
        ...     confidence=0.95,
        ...     operation="pms_query",
        ...     availability_date="2025-11-20",
        ...     room_type="deluxe"
        ... )
    """
    if span is None or not span.is_recording():
        logger.warning("span_not_recording", operation="enrich_span_with_business_context")
        return
    
    if intent:
        span.set_attribute("business.intent", intent)
    
    if confidence is not None:
        span.set_attribute("business.confidence", float(confidence))
    
    if operation:
        span.set_attribute("business.operation", operation)
    
    # Add custom kwargs as attributes (prefix with "business.")
    for key, value in kwargs.items():
        if value is not None:
            attr_name = f"business.{key}"
            # Convert to string if not a primitive type
            if isinstance(value, (str, int, float, bool)):
                span.set_attribute(attr_name, value)
            else:
                span.set_attribute(attr_name, str(value))
    
    logger.debug(
        "span_enriched_business_context",
        intent=intent,
        confidence=confidence,
        operation=operation,
        kwargs=kwargs,
    )


__all__ = [
    "tracer",
    "tracer_provider",
    "trace_function",
    "SpanKind",
    "enrich_span_from_request",
    "enrich_span_with_business_context",
]
