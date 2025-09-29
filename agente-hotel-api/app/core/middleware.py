# [PROMPT 3.2] app/core/middleware.py (Corregido)

import time
import traceback
from uuid import uuid4
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .logging import logger
from ..services.metrics_service import metrics_service
from .settings import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Aplica cabeceras de seguridad estándar.

    Ajustable vía settings (permitir orígenes extra para CSP, habilitar/deshabilitar HSTS en entornos no prod).
    """

    def build_csp(self) -> str:
        """Build Content Security Policy with secure defaults and optional extensions."""
        default_sources = ["'self'"]
        raw = getattr(settings, "csp_extra_sources", None)
        extra_list = raw.split() if isinstance(raw, str) and raw else []

        # Validate extra sources to prevent injection
        validated_extra = []
        for source in extra_list:
            # Basic validation for CSP sources
            if source.startswith(("https://", "http://localhost", "'unsafe-inline'", "'unsafe-eval'")):
                validated_extra.append(source)
            elif source in ["'none'", "'self'", "'strict-dynamic'"]:
                validated_extra.append(source)
            else:
                logger.warning("Invalid CSP source ignored", source=source)

        merged = default_sources + list(dict.fromkeys(validated_extra))
        base_policy = f"default-src {' '.join(merged)}"

        # Add additional restrictive policies
        additional_policies = [
            f"script-src {' '.join(merged)}",
            f"style-src {' '.join(merged)} 'unsafe-inline'",  # Allow inline styles for flexibility
            f"img-src {' '.join(merged)} data:",  # Allow data: URLs for images
            "object-src 'none'",  # Prevent Flash and other plugins
            "base-uri 'self'",  # Restrict base tag URLs
            "form-action 'self'",  # Restrict form submissions
            "frame-ancestors 'none'",  # Prevent embedding in frames
            "upgrade-insecure-requests",  # Upgrade HTTP to HTTPS
        ]

        return f"{base_policy}; {'; '.join(additional_policies)}"

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
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
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
    """Enhanced global exception handler with comprehensive error context."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    client_ip = request.client.host if request.client else "unknown"

    # Determine error type and appropriate response
    error_context = {
        "correlation_id": correlation_id,
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "method": request.method,
        "path": request.url.path,
        "client_ip": client_ip,
        "user_agent": request.headers.get("user-agent", "unknown"),
        "timestamp": time.time(),
    }

    # Handle specific exception types
    if hasattr(exc, "to_dict"):
        # Custom exceptions with enhanced context
        error_context.update(exc.to_dict())

    # Log with appropriate level based on error type
    if isinstance(exc, (KeyboardInterrupt, SystemExit)):
        # Don't log system interrupts as errors
        logger.info("System interrupt received", **error_context)
        return JSONResponse(
            status_code=503, content={"detail": "Service temporarily unavailable", "correlation_id": correlation_id}
        )
    elif isinstance(exc, (ValueError, TypeError)):
        # Client errors - log as warning
        logger.warning("Client error", **error_context)
        return JSONResponse(
            status_code=400, content={"detail": "Bad request - invalid input", "correlation_id": correlation_id}
        )
    else:
        # Server errors - log as error with full traceback
        logger.error("Unhandled server exception", **error_context, traceback=traceback.format_exc())

        # Don't expose internal error details in production
        if settings.environment == "production":
            error_detail = "Internal server error"
        else:
            error_detail = f"Internal server error: {str(exc)}"

        return JSONResponse(
            status_code=500,
            content={
                "detail": error_detail,
                "correlation_id": correlation_id,
                "error_type": type(exc).__name__ if settings.debug else None,
            },
        )
