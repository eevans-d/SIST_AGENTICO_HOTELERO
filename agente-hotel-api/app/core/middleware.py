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
                        correlation_id=getattr(request.state, "correlation_id", "unknown")
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "Request entity too large",
                            "max_size_bytes": max_allowed,
                            "received_bytes": content_length_int
                        }
                    )
        
        return await call_next(request)
