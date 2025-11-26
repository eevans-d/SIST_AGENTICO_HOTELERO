# [PROMPT 3.2] app/core/middleware.py (Corregido)

import time
import traceback
from uuid import uuid4
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

try:  # opentelemetry es opcional en entornos locales/test
    from opentelemetry import trace
except ModuleNotFoundError:  # pragma: no cover - degradación cuando no está instalado
    trace = None

from .logging import logger
from ..services.metrics_service import metrics_service
from .settings import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Aplica cabeceras de seguridad estándar.

    Ajustable vía settings (permitir orígenes extra para CSP, habilitar/deshabilitar HSTS en entornos no prod).
    """

    def build_csp(self) -> str:
        default_sources = ["'self'"]
        raw = getattr(settings, "csp_extra_sources", None)
        extra_list = raw.split() if isinstance(raw, str) and raw else []
        merged = default_sources + list(dict.fromkeys(extra_list))
        return f"default-src {' '.join(merged)}"

    async def dispatch(self, request, call_next):  # type: ignore[override]
        response = await call_next(request)
        # Seguridad básica
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        if settings.environment == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        # CSP
        response.headers.setdefault("Content-Security-Policy", self.build_csp())
        # COOP / COEP (opt-in; puede romper integraciones pop-up, revisarlo antes de activar)
        if getattr(settings, "coop_enabled", False):
            response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if getattr(settings, "coep_enabled", False):
            response.headers.setdefault("Cross-Origin-Embedder-Policy", "require-corp")
        # API responses: evitar cacheo inadvertido (excepto métricas estáticas si se decide luego)
        if request.url.path.startswith("/health") or request.url.path.startswith("/metrics"):
            # health puede cachearse unos segundos si se quiere; por ahora no-cache
            response.headers.setdefault("Cache-Control", "no-store")
        elif request.method != "GET":
            response.headers.setdefault("Cache-Control", "no-store")
        return response


async def correlation_id_middleware(request: Request, call_next):
    # Prefer X-Request-ID if provided by upstream, fallback to X-Correlation-ID
    incoming = request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID")
    correlation_id = incoming or str(uuid4())
    request.state.correlation_id = correlation_id

    # Set contextvar for downstream services
    try:
        from .correlation import set_correlation_id

        set_correlation_id(correlation_id)
    except Exception:
        # Non-fatal if context var cannot be set
        pass

    response = await call_next(request)
    # Expose both headers for compatibility
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Request-ID"] = correlation_id
    return response


async def logging_and_metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    # Logging
    client_ip = request.client.host if request.client else None
    logger.info(
        "http_request",
        correlation_id=getattr(request.state, "correlation_id", None),
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration * 1000,
        client_ip=client_ip,
    )

    # Metrics
    metrics_service.record_request_latency(
        method=request.method, endpoint=request.url.path, latency=duration, status_code=response.status_code
    )

    return response


async def global_exception_handler(request: Request, exc: Exception):
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    logger.error("unhandled_exception", correlation_id=correlation_id, error=str(exc), traceback=traceback.format_exc())
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "correlation_id": correlation_id})


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to limit request body size and prevent DoS attacks.

    Default limit: 1MB for regular requests, 10MB for media uploads.
    """

    def __init__(self, app, max_size: int = 1_000_000, max_media_size: int = 10_000_000):
        super().__init__(app)
        self.max_size = max_size  # 1MB default
        self.max_media_size = max_media_size  # 10MB for media

    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")

            if content_length:
                content_length_int = int(content_length)

                # Allow larger size for media upload endpoints
                max_allowed = self.max_media_size if "/media" in request.url.path else self.max_size

                if content_length_int > max_allowed:
                    logger.warning(
                        "request_too_large",
                        path=request.url.path,
                        size=content_length_int,
                        max_allowed=max_allowed,
                        correlation_id=getattr(request.state, "correlation_id", "unknown"),
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "Request entity too large",
                            "max_size_bytes": max_allowed,
                            "received_bytes": content_length_int,
                        },
                    )

        return await call_next(request)


async def tracing_enrichment_middleware(request: Request, call_next):
    """Middleware to enrich OpenTelemetry spans with business context.

    Si opentelemetry no está instalado (trace is None), el middleware
    simplemente delega sin intentar enriquecer spans.
    """

    # Get current span (created by OpenTelemetry FastAPI instrumentation or manually)
    span = trace.get_current_span() if trace is not None else None

    if span and span.is_recording():
        from .tracing import enrich_span_from_request
        
        try:
            # Enrich with business context from request
            enrich_span_from_request(span, request)
            
            # Add HTTP-specific attributes if not already set
            if not span.attributes or "http.method" not in span.attributes:
                span.set_attribute("http.method", request.method)
                span.set_attribute("http.route", request.url.path)
                span.set_attribute("http.url", str(request.url))
                
                # Client IP for debugging
                if request.client:
                    span.set_attribute("http.client_ip", request.client.host)
            
            logger.debug(
                "span_enriched_middleware",
                correlation_id=getattr(request.state, "correlation_id", None),
                span_context=span.get_span_context(),
            )
        except Exception as e:
            # Non-fatal: log but don't break the request
            logger.warning(
                "span_enrichment_failed",
                error=str(e),
                correlation_id=getattr(request.state, "correlation_id", None),
            )
    
    response = await call_next(request)
    
    # Add response status to span if available
    if span and span.is_recording():
        span.set_attribute("http.status_code", response.status_code)
        
        # Mark span status based on HTTP status
        if 200 <= response.status_code < 400:
            from opentelemetry.trace import Status, StatusCode
            span.set_status(Status(StatusCode.OK))
        elif 400 <= response.status_code < 500:
            # Client errors are not span errors (valid business logic)
            span.set_attribute("http.error_type", "client_error")
        elif response.status_code >= 500:
            # Server errors should mark span as error
            from opentelemetry.trace import Status, StatusCode
            span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
            span.set_attribute("http.error_type", "server_error")
    
    return response


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to resolve and set the tenant ID for each request.
    
    Tenant resolution order:
    1. X-Tenant-ID header (explicit tenant selection)
    2. JWT token claims (tenant_id field)
    3. Default tenant from settings
    
    The resolved tenant_id is stored in:
    - request.state.tenant_id (for request-scoped access)
    - tenant_context (for global access via contextvars)
    """
    
    def __init__(self, app, default_tenant: str = "default"):
        super().__init__(app)
        self.default_tenant = default_tenant
    
    async def dispatch(self, request: Request, call_next):
        from .tenant_context import set_tenant_id, clear_tenant_id
        
        tenant_id = None
        
        # 1. Check X-Tenant-ID header
        tenant_id = request.headers.get("X-Tenant-ID") or request.headers.get("x-tenant-id")
        
        # 2. If not in header, try to extract from JWT token
        if not tenant_id:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                try:
                    # Import here to avoid circular dependencies
                    from ..services.auth_service import decode_token
                    token = auth_header.split(" ")[1]
                    payload = decode_token(token)
                    tenant_id = payload.get("tenant_id")
                except Exception as e:
                    # Log but don't fail - we'll use default tenant
                    logger.debug(
                        "tenant_extraction_from_jwt_failed",
                        error=str(e),
                        correlation_id=getattr(request.state, "correlation_id", None),
                    )
        
        # 3. Fall back to default tenant
        if not tenant_id:
            tenant_id = self.default_tenant
        
        # Set tenant_id in request state and context
        request.state.tenant_id = tenant_id
        set_tenant_id(tenant_id)
        
        logger.debug(
            "tenant_resolved",
            tenant_id=tenant_id,
            correlation_id=getattr(request.state, "correlation_id", None),
            path=request.url.path,
        )
        
        try:
            response = await call_next(request)
            # Add tenant ID to response headers for debugging
            response.headers["X-Tenant-ID"] = tenant_id
            return response
        finally:
            # Clean up context after request
            clear_tenant_id()
