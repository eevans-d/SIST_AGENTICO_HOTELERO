# [PROMPT 3.2] app/core/middleware.py (Corregido)

import time
import traceback
from uuid import uuid4
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .logging import logger
from ..services.metrics_service import metrics_service


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
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
    logger.info(
        "http_request",
        correlation_id=request.state.correlation_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration * 1000,
        client_ip=request.client.host,
    )

    # Metrics
    metrics_service.record_request_latency(
        endpoint=request.url.path, latency=duration, status_code=response.status_code
    )

    return response


async def global_exception_handler(request: Request, exc: Exception):
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    logger.error("unhandled_exception", correlation_id=correlation_id, error=str(exc), traceback=traceback.format_exc())
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "correlation_id": correlation_id})
