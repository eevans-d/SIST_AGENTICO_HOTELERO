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
from typing import Optional, Dict, Any
from functools import wraps
import structlog

logger = structlog.get_logger(__name__)

# Configuration
TRACE_CONFIG = {
    "service_name": "agente-hotel-api",
    "otlp_endpoint": "http://jaeger:4317",
    "sampling_rate": 1.0,
}

def setup_tracing():
    """Setup OpenTelemetry tracing."""
    resource = Resource.create({SERVICE_NAME: TRACE_CONFIG["service_name"]})
    provider = TracerProvider(resource=resource)
    
    try:
        otlp_exporter = OTLPSpanExporter(endpoint=TRACE_CONFIG["otlp_endpoint"], insecure=True)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info("otlp_exporter_configured")
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

__all__ = ["tracer", "tracer_provider", "trace_function", "SpanKind"]
