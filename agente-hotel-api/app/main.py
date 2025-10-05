# [PROMPT 3.2] app/main.py (Corregido)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi import Request
from starlette.responses import Response

from app.core.settings import settings, Environment
from app.core.logging import setup_logging, logger
from app.core.middleware import (
    correlation_id_middleware,
    logging_and_metrics_middleware,
    global_exception_handler,
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
)
from app.routers import health, metrics, webhooks, admin
from .services.dynamic_tenant_service import dynamic_tenant_service
from .services.feature_flag_service import get_feature_flag_service
from .core.redis_client import get_redis
from .services.session_manager import SessionManager

setup_logging()

# Rate limiting configurado con Redis
limiter = Limiter(key_func=get_remote_address, storage_uri=str(settings.redis_url))

# Metadatos de la app (fallbacks por si no existen en settings)
APP_TITLE = getattr(settings, "app_name", "Agente Hotel API")
APP_VERSION = getattr(settings, "version", "0.1.0")
APP_DEBUG = bool(getattr(settings, "debug", False))

# Global session manager for cleanup task
_session_manager_cleanup = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _session_manager_cleanup
    logger.info("Application startup", app_name=settings.app_name, env=settings.environment)
    
    # Inicializar servicio de tenants dinámico
    # Condicional por feature flag
    try:
        ff = await get_feature_flag_service()
        if await ff.is_enabled("tenancy.dynamic.enabled", default=True):
            await dynamic_tenant_service.start()
        else:
            logger.info("Dynamic tenant service deshabilitado por feature flag")
    except Exception as e:  # pragma: no cover
        logger.warning("DynamicTenantService start failed", error=str(e))
    
    # Iniciar tarea de limpieza de sesiones
    try:
        redis_client = await get_redis()
        _session_manager_cleanup = SessionManager(redis_client)
        _session_manager_cleanup.start_cleanup_task()
        logger.info("✅ Session cleanup task initialized")
    except Exception as e:  # pragma: no cover
        logger.warning(f"⚠️  Session cleanup task failed to start: {e}")
    
    try:
        yield
    finally:
        # Detener tarea de limpieza de sesiones
        if _session_manager_cleanup:
            try:
                await _session_manager_cleanup.stop_cleanup_task()
                logger.info("Session cleanup task stopped")
            except Exception:  # pragma: no cover
                pass
        
        try:
            await dynamic_tenant_service.stop()
        except Exception:  # pragma: no cover
            pass
        logger.info("Application shutdown")


app = FastAPI(title=APP_TITLE, version=APP_VERSION, debug=APP_DEBUG, lifespan=lifespan)

# CORS Configuration - Restrictivo en producción
if settings.environment == Environment.PROD:
    # Producción: Solo orígenes específicos
    allowed_origins = [
        "https://hotel.example.com",  # Reemplazar con dominio real
        # Añadir otros dominios autorizados
    ]
    logger.info(f"CORS enabled for production origins: {allowed_origins}")
else:
    # Desarrollo: Permitir localhost
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    logger.info("CORS enabled for development (localhost only)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    max_age=600,  # Cache preflight por 10 minutos
)

# Middlewares
app.state.limiter = limiter


def _rl_handler(request: Request, exc: Exception) -> Response:
    # FastAPI espera ExceptionHandler: (Request, Exception) -> Response
    return _rate_limit_exceeded_handler(request, exc)  # type: ignore[arg-type]


app.add_exception_handler(RateLimitExceeded, _rl_handler)
app.add_middleware(RequestSizeLimitMiddleware, max_size=1_000_000, max_media_size=10_000_000)
app.add_middleware(SecurityHeadersMiddleware)
app.middleware("http")(correlation_id_middleware)
app.middleware("http")(logging_and_metrics_middleware)
app.add_exception_handler(Exception, global_exception_handler)

# Routers
app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(webhooks.router)
app.include_router(admin.router)

# (Startup/Shutdown gestionados por lifespan)
