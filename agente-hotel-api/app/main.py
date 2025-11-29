"""
Sistema de Agente Hotelero IA - Aplicación Principal
Sistema empresarial completo con integración de todos los servicios
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi import Request
from starlette.responses import Response
import asyncio

try:  # opentelemetry es opcional en entornos locales/test
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
except ModuleNotFoundError:  # pragma: no cover - degradación cuando no está instalado
    FastAPIInstrumentor = None

from app.core.settings import settings, Environment
from app.core.logging import setup_logging, logger
from app.core.middleware import (
    correlation_id_middleware,
    logging_and_metrics_middleware,
    tracing_enrichment_middleware,
    global_exception_handler,
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
    TenantMiddleware,
)

# Importar todos los routers
from app.routers import health, metrics, webhooks, admin, monitoring

# Importar router de NLP
try:
    from app.routers import nlp
    NLP_ROUTER_AVAILABLE = True
except Exception:
    NLP_ROUTER_AVAILABLE = False
    logger.warning("NLP router not available")

# Importar router de performance optimization
try:
    from app.routers import performance

    PERFORMANCE_ROUTER_AVAILABLE = True
except ImportError:
    PERFORMANCE_ROUTER_AVAILABLE = False
    logger.warning("Performance router not available")

# Servicios principales
from .services.dynamic_tenant_service import dynamic_tenant_service
from .services.feature_flag_service import get_feature_flag_service
from .core.redis_client import get_redis
from .services.session_manager import SessionManager
from sqlalchemy import select, func
from app.core.database import engine
from app.models.user import UserSession
from app.services.metrics_service import metrics_service

# Importaciones opcionales (solo si existen los servicios)
try:
    from .monitoring.business_metrics import get_business_metrics_service
    from .monitoring.dashboard_service import get_dashboard_service
    from .monitoring.alerting_service import get_alerting_service
    from .monitoring.performance_service import get_performance_service
    from .monitoring.health_service import get_health_service
    from .monitoring.tracing_service import get_tracing_service

    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    logger.warning("Monitoring services not available")

# Importar servicios de optimización de performance
try:
    from .services.performance_optimizer import get_performance_optimizer
    from .services.database_tuner import get_db_performance_tuner
    from .services.cache_optimizer import get_cache_optimizer
    from .services.resource_monitor import get_resource_monitor
    from .services.auto_scaler import get_auto_scaler
    from .services.performance_scheduler import get_performance_scheduler

    OPTIMIZATION_AVAILABLE = True
except Exception:
    OPTIMIZATION_AVAILABLE = False
    logger.warning("Performance optimization services not available")

setup_logging()

# Rate limiting configurado con Redis
limiter = Limiter(key_func=get_remote_address, storage_uri=str(settings.redis_url))

# Metadatos de la app (fallbacks por si no existen en settings)
APP_TITLE = getattr(settings, "app_name", "Agente Hotel API")
APP_VERSION = getattr(settings, "version", "0.1.0")
APP_DEBUG = bool(getattr(settings, "debug", False))

# Global session manager for cleanup task
_session_manager_cleanup = None


# ============================================================================
# HELPERS DE INICIALIZACIÓN (extraídos para reducir CC de lifespan)
# ============================================================================


async def _init_monitoring_services(initialized_services: list[str]) -> None:
    """Inicializa servicios de monitoreo si están disponibles."""
    if not MONITORING_AVAILABLE:
        return
    try:
        await get_health_service()
        await get_performance_service()
        await get_business_metrics_service()
        await get_alerting_service()
        await get_tracing_service()
        await get_dashboard_service()
        initialized_services.extend([
            "health_service", "performance_service", "business_metrics_service",
            "alerting_service", "tracing_service", "dashboard_service",
        ])
        logger.info("✅ Servicios de monitoreo inicializados")
    except Exception as e:
        logger.warning(f"⚠️  Error inicializando servicios de monitoreo: {e}")


async def _init_optimization_services(initialized_services: list[str]) -> None:
    """Inicializa servicios de optimización de performance."""
    if not OPTIMIZATION_AVAILABLE:
        return
    try:
        performance_optimizer = await get_performance_optimizer()
        database_tuner = await get_db_performance_tuner()
        cache_optimizer = await get_cache_optimizer()
        resource_monitor = await get_resource_monitor()
        auto_scaler = await get_auto_scaler()
        performance_scheduler = await get_performance_scheduler()

        await performance_optimizer.start()
        await database_tuner.start()
        await cache_optimizer.start()
        await resource_monitor.start()
        await auto_scaler.start()
        await performance_scheduler.start()

        asyncio.create_task(resource_monitor.continuous_monitoring())
        asyncio.create_task(auto_scaler.continuous_scaling())
        asyncio.create_task(performance_scheduler.continuous_scheduling())

        initialized_services.extend([
            "performance_optimizer", "database_tuner", "cache_optimizer",
            "resource_monitor", "auto_scaler", "performance_scheduler",
        ])
        logger.info("✅ Servicios de optimización de performance inicializados")
    except Exception as e:
        logger.warning(f"⚠️  Error inicializando servicios de optimización: {e}")


async def _init_dynamic_tenant(initialized_services: list[str]) -> None:
    """Inicializa servicio de tenants dinámico."""
    try:
        ff = await get_feature_flag_service()
        if await ff.is_enabled("tenancy.dynamic.enabled", default=True):
            await dynamic_tenant_service.start()
            initialized_services.append("dynamic_tenant_service")
            logger.info("✅ Servicio de tenants dinámico inicializado")
        else:
            logger.info("ℹ️  Servicio de tenants dinámico deshabilitado por feature flag")
    except Exception as e:
        logger.warning(f"⚠️  Error inicializando servicio de tenants: {e}")


async def _init_session_manager(initialized_services: list[str]) -> SessionManager | None:
    """Inicializa gestor de sesiones."""
    global _session_manager_cleanup
    try:
        redis_client = await get_redis()
        _session_manager_cleanup = SessionManager(redis_client)
        _session_manager_cleanup.start_cleanup_task()
        try:
            await _session_manager_cleanup.refresh_active_sessions_metric()
        except Exception as e:
            logger.debug("metric_active_sessions_initialization_failed", error=str(e))
        initialized_services.append("session_manager")
        logger.info("✅ Gestor de sesiones inicializado")
        return _session_manager_cleanup
    except Exception as e:
        logger.warning(f"⚠️  Error inicializando gestor de sesiones: {e}")
        return None


async def _init_dlq_worker(initialized_services: list[str]) -> asyncio.Task | None:
    """Inicializa DLQ Retry Worker para procesamiento automático de mensajes fallidos."""
    try:
        from app.services.dlq_service import DLQService
        from app.core.database import AsyncSessionFactory

        redis_client = await get_redis()

        async def dlq_retry_worker():
            """Background worker que procesa mensajes de DLQ listos para retry."""
            async with AsyncSessionFactory() as db_session:
                dlq_service = DLQService(
                    redis_client=redis_client,
                    db_session=db_session,
                    max_retries=settings.dlq_max_retries,
                    retry_backoff_base=settings.dlq_retry_backoff_base,
                    ttl_days=settings.dlq_ttl_days,
                )
                logger.info("🔄 DLQ Retry Worker iniciado", interval=f"{settings.dlq_worker_interval}s")
                while True:
                    await _dlq_worker_cycle(dlq_service)
                    await asyncio.sleep(settings.dlq_worker_interval)

        task = asyncio.create_task(dlq_retry_worker())
        initialized_services.append("dlq_retry_worker")
        logger.info("✅ DLQ Retry Worker inicializado")
        return task
    except Exception as e:
        logger.warning(f"⚠️  Error inicializando DLQ Retry Worker: {e}")
        return None


async def _dlq_worker_cycle(dlq_service) -> None:
    """Ejecuta un ciclo del DLQ worker."""
    try:
        candidates = await dlq_service.get_retry_candidates()
        if candidates:
            logger.info("dlq_processing_candidates", count=len(candidates),
                        candidates=[c["dlq_id"] for c in candidates[:5]])
            for entry in candidates:
                dlq_id = entry["dlq_id"]
                try:
                    success = await dlq_service.retry_message(dlq_id)
                    if success:
                        logger.info("dlq_retry_success", dlq_id=dlq_id)
                    else:
                        logger.warning("dlq_retry_failed", dlq_id=dlq_id)
                except Exception as retry_error:
                    logger.error("dlq_retry_error", dlq_id=dlq_id, error=str(retry_error))
        await dlq_service._update_queue_size_metric()
    except Exception as e:
        logger.error("dlq_worker_error", error=str(e))


async def _verify_redis_connection() -> None:
    """Verifica conexión a Redis."""
    try:
        redis_client = await get_redis()
        import inspect
        _ping = redis_client.ping()
        if inspect.isawaitable(_ping):
            await _ping
        logger.info("✅ Conexión Redis verificada")
    except Exception as e:
        logger.error(f"❌ Error conectando a Redis: {e}")


def _start_metrics_tasks() -> tuple[asyncio.Task, asyncio.Task]:
    """Inicia tareas periódicas de métricas (JWT sessions y DB connections)."""
    from app.core.database import AsyncSessionFactory

    async def _update_jwt_sessions_periodically():
        while True:
            try:
                async with AsyncSessionFactory() as session:
                    count = await session.scalar(
                        select(func.count()).select_from(UserSession)
                        .where(UserSession.is_revoked == False)  # noqa: E712
                        .where(UserSession.expires_at > func.now())
                    )
                    metrics_service.set_jwt_sessions_active(count or 0)
            except Exception as e:
                logger.debug("metric_jwt_sessions_update_failed", error=str(e))
            await asyncio.sleep(60)

    async def _update_db_connections_periodically():
        while True:
            try:
                pool = engine.pool
                active = getattr(pool, "checkedout", lambda: 0)()
                metrics_service.set_db_connections_active(active)
            except Exception as e:
                logger.debug("metric_db_connections_update_failed", error=str(e))
            await asyncio.sleep(30)

    return (
        asyncio.create_task(_update_jwt_sessions_periodically()),
        asyncio.create_task(_update_db_connections_periodically()),
    )


# ============================================================================
# HELPERS DE SHUTDOWN (extraídos para reducir CC de lifespan)
# ============================================================================


async def _shutdown_session_manager(manager: SessionManager | None) -> None:
    """Detiene gestor de sesiones."""
    if not manager:
        return
    try:
        await manager.stop_cleanup_task()
        logger.info("✅ Gestor de sesiones detenido")
    except Exception as e:
        logger.warning(f"⚠️  Error deteniendo gestor de sesiones: {e}")


async def _shutdown_dlq_worker(task: asyncio.Task | None) -> None:
    """Detiene DLQ Retry Worker."""
    if not task or task.done():
        return
    try:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        logger.info("✅ DLQ Retry Worker detenido")
    except Exception as e:
        logger.warning(f"⚠️  Error deteniendo DLQ Retry Worker: {e}")


async def _shutdown_dynamic_tenant() -> None:
    """Detiene servicio de tenants."""
    try:
        await dynamic_tenant_service.stop()
        logger.info("✅ Servicio de tenants detenido")
    except Exception as e:
        logger.warning(f"⚠️  Error deteniendo servicio de tenants: {e}")


async def _shutdown_optimization_services() -> None:
    """Detiene servicios de optimización."""
    if not OPTIMIZATION_AVAILABLE:
        return
    try:
        performance_optimizer = await get_performance_optimizer()
        database_tuner = await get_db_performance_tuner()
        cache_optimizer = await get_cache_optimizer()
        resource_monitor = await get_resource_monitor()
        auto_scaler = await get_auto_scaler()
        performance_scheduler = await get_performance_scheduler()

        await performance_optimizer.stop()
        await database_tuner.stop()
        await cache_optimizer.stop()
        await resource_monitor.stop()
        await auto_scaler.stop()
        await performance_scheduler.stop()
        logger.info("✅ Servicios de optimización detenidos")
    except Exception as e:
        logger.warning(f"⚠️  Error deteniendo servicios de optimización: {e}")


def _shutdown_metrics_tasks(tasks: tuple[asyncio.Task | None, ...]) -> None:
    """Cancela tareas de métricas."""
    for t in tasks:
        if t:
            try:
                t.cancel()
            except Exception:
                pass


# ============================================================================
# LIFESPAN - FUNCIÓN COORDINADORA (CC reducido mediante helpers)
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión completa del ciclo de vida de la aplicación (coordinadora)."""
    logger.info(
        "🚀 Sistema de Agente Hotelero IA iniciando...",
        app_name=settings.app_name,
        env=settings.environment,
        version=APP_VERSION,
    )

    initialized_services: list[str] = []
    session_manager: SessionManager | None = None
    dlq_worker_task: asyncio.Task | None = None
    metrics_tasks: tuple[asyncio.Task, asyncio.Task] | None = None

    try:
        # 1. Inicializar servicios
        await _init_monitoring_services(initialized_services)
        await _init_optimization_services(initialized_services)
        await _init_dynamic_tenant(initialized_services)
        session_manager = await _init_session_manager(initialized_services)
        dlq_worker_task = await _init_dlq_worker(initialized_services)

        # 2. Verificar conexiones
        await _verify_redis_connection()

        # 3. Log de servicios
        logger.info(
            "🎯 Sistema completamente inicializado",
            services_count=len(initialized_services),
            services=initialized_services,
        )

        # 4. Iniciar tareas periódicas de métricas
        metrics_tasks = _start_metrics_tasks()

        # Aplicación lista para recibir requests
        yield

    except Exception as e:
        logger.error(f"💥 Error crítico durante la inicialización: {e}")
        raise

    finally:
        # Cleanup durante shutdown
        logger.info("🔄 Iniciando shutdown del sistema...")
        await _shutdown_session_manager(session_manager)
        await _shutdown_dlq_worker(dlq_worker_task)
        await _shutdown_dynamic_tenant()
        await _shutdown_optimization_services()
        if metrics_tasks:
            _shutdown_metrics_tasks(metrics_tasks)
        logger.info("✅ Conexiones cerradas")
        logger.info("🏁 Sistema de Agente Hotelero IA detenido correctamente")


# SECURITY: Disable documentation endpoints in production
docs_url = "/docs" if settings.environment != Environment.PROD else None
redoc_url = "/redoc" if settings.environment != Environment.PROD else None
openapi_url = "/openapi.json" if settings.environment != Environment.PROD else None

if settings.environment == Environment.PROD:
    logger.info("🔒 API documentation endpoints disabled in production (security hardening)")
else:
    logger.info("📚 API documentation available at /docs and /redoc")

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    debug=APP_DEBUG,
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)

# OpenTelemetry FastAPI Instrumentation (H1: Trace Enrichment)
# CRITICAL: This enables automatic span creation for all HTTP requests
# Without this, tracing_enrichment_middleware gets NonRecordingSpan and H1 doesn't work
if FastAPIInstrumentor is not None:
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/health/live,/health/ready,/metrics",  # Exclude high-frequency endpoints
    )
    logger.info("✅ OpenTelemetry FastAPI instrumentation enabled (H1 activated)")
else:
    logger.warning("OpenTelemetry FastAPI instrumentation not enabled (opentelemetry not installed)")

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

# TrustedHostMiddleware - DEBE IR ANTES DE CORS para validar Host headers
if settings.environment == Environment.PROD:
    # Validar que allowed_hosts está configurado correctamente
    default_hosts = ["localhost", "127.0.0.1"]
    if settings.allowed_hosts == default_hosts:
        logger.warning(
            "⚠️  TrustedHostMiddleware in production with default localhost values. "
            "Update allowed_hosts in settings with production domain(s)."
        )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts
    )
    logger.info(f"🔒 TrustedHostMiddleware enabled. Allowed hosts: {settings.allowed_hosts}")
else:
    logger.info("TrustedHostMiddleware disabled in development (not production)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-Correlation-ID",
        "X-Tenant-ID",
        "Accept",
        "Accept-Language",
        "Cache-Control",
    ],
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
app.add_middleware(TenantMiddleware, default_tenant="default")  # Multi-tenancy support
app.middleware("http")(correlation_id_middleware)
app.middleware("http")(tracing_enrichment_middleware)  # H1: Enrich spans with business context
app.middleware("http")(logging_and_metrics_middleware)
app.add_exception_handler(Exception, global_exception_handler)

# Routers principales
app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(webhooks.router)
app.include_router(admin.router)

# Router de monitoreo (si está disponible)
if MONITORING_AVAILABLE:
    app.include_router(monitoring.router)
    logger.info("✅ Router de monitoreo incluido")
else:
    logger.warning("⚠️  Router de monitoreo no disponible")

# Router de performance optimization (si está disponible)
if PERFORMANCE_ROUTER_AVAILABLE:
    app.include_router(performance.router)
    logger.info("✅ Router de optimización de performance incluido")
else:
    logger.warning("⚠️  Router de optimización no disponible")

# Router de NLP (si está disponible)
if NLP_ROUTER_AVAILABLE:
    app.include_router(nlp.router)
    logger.info("✅ Router de NLP incluido")
else:
    logger.warning("⚠️  Router de NLP no disponible")


# Endpoints adicionales para información del sistema
@app.get("/")
async def root():
    """Endpoint raíz con información del sistema"""
    return {
        "service": "Sistema de Agente Hotelero IA",
        "version": APP_VERSION,
        "environment": settings.environment,
        "status": "active",
        "features": {
            "monitoring": MONITORING_AVAILABLE,
            "performance_optimization": OPTIMIZATION_AVAILABLE,
            "dynamic_tenancy": True,
            "rate_limiting": True,
            "security_headers": True,
        },
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
    }


@app.get("/info")
async def system_info():
    """Información detallada del sistema"""
    return {
        "system": {
            "name": "Sistema de Agente Hotelero IA",
            "version": APP_VERSION,
            "environment": settings.environment,
            "debug": APP_DEBUG,
        },
        "capabilities": {
            "audio_processing": "WhatsApp/Gmail audio message handling",
            "nlp_engine": "Hotel-specific intent recognition",
            "pms_integration": "QloApps PMS integration",
            "multi_channel": "WhatsApp, Email, API support",
            "security": "JWT auth, encryption, rate limiting",
            "monitoring": "Business intelligence and observability" if MONITORING_AVAILABLE else "Basic monitoring",
            "optimization": "Auto-scaling, performance tuning, resource monitoring"
            if OPTIMIZATION_AVAILABLE
            else "Manual optimization",
        },
        "endpoints": {
            "health_checks": "/health/*",
            "business_metrics": "/metrics/*",
            "webhooks": "/webhooks/*",
            "admin": "/admin/*",
            "monitoring": "/monitoring/*" if MONITORING_AVAILABLE else "Not available",
            "performance": "/api/v1/performance/*" if OPTIMIZATION_AVAILABLE else "Not available",
        },
    }


# (Startup/Shutdown gestionados por lifespan)
