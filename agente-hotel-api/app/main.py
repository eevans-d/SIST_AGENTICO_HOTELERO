# [PROMPT 3.2] app/main.py (Corregido)

from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.settings import settings
from app.core.logging import setup_logging, logger
from app.core.middleware import (
    correlation_id_middleware,
    logging_and_metrics_middleware,
    global_exception_handler,
    SecurityHeadersMiddleware,
)
from app.routers import health, metrics, webhooks, admin

setup_logging()

# Rate limiting configurado con Redis
limiter = Limiter(key_func=get_remote_address, storage_uri=str(settings.redis_url))

# Metadatos de la app (fallbacks por si no existen en settings)
APP_TITLE = getattr(settings, "app_name", "Agente Hotel API")
APP_VERSION = getattr(settings, "version", "0.1.0")
APP_DEBUG = bool(getattr(settings, "debug", False))

app = FastAPI(title=APP_TITLE, version=APP_VERSION, debug=APP_DEBUG)

# Middlewares
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SecurityHeadersMiddleware)
app.middleware("http")(correlation_id_middleware)
app.middleware("http")(logging_and_metrics_middleware)
app.add_exception_handler(Exception, global_exception_handler)

# Routers
app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(webhooks.router)
app.include_router(admin.router)


@app.on_event("startup")
async def startup_event():
    logger.info("Application startup", app_name=settings.app_name, env=settings.environment)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown")
