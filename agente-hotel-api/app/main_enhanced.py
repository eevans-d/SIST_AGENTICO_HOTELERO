"""
Enhanced Main Application with Security Integration
FastAPI application with comprehensive security middleware integration
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any
import uvloop
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import Response, JSONResponse
from starlette.middleware.gzip import GZipMiddleware

# Core imports
from app.core.settings import get_settings
from app.core.logging import setup_logging
from app.core.database import get_database
from app.core.redis_client import get_redis_client
from app.exceptions.global_exception_handler import setup_exception_handlers

# Security imports
from app.security.security_middleware import SecurityMiddleware
from app.security.advanced_jwt_auth import AdvancedJWTAuth
from app.security.audit_logger import SecurityAuditLogger
from app.security.data_encryption import DataEncryption
from app.security.rate_limiter import AdvancedRateLimiter

# Router imports
from app.routers import health, metrics, webhooks, admin, security
from app.routers.nlp import router as nlp_router
from app.routers.pms import router as pms_router

# Service imports
from app.services.monitoring_service import MonitoringService
from app.services.audio_processor import AudioProcessor
from app.services.whatsapp_client import WhatsAppClient
from app.services.gmail_client import GmailClient
from app.services.nlp_engine import NLPEngine
from app.services.pms_adapter import PMSAdapter
from app.services.orchestrator import Orchestrator
from app.services.session_manager import SessionManager
from app.services.template_service import TemplateService
from app.services.lock_service import LockService

# Set asyncio event loop policy
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with enhanced security"""
    
    settings = get_settings()
    
    logger.info("Starting Hotel Agent API with Enhanced Security")
    
    try:
        # Initialize core services
        logger.info("Initializing core services...")
        
        # Database
        database = get_database()
        await database.start()
        app.state.database = database
        
        # Redis
        redis_client = get_redis_client()
        await redis_client.start()
        app.state.redis = redis_client
        
        # Security services
        logger.info("Initializing security services...")
        
        # JWT Authentication
        jwt_auth = AdvancedJWTAuth()
        await jwt_auth.start()
        app.state.jwt_auth = jwt_auth
        
        # Security Audit Logger
        audit_logger = SecurityAuditLogger()
        await audit_logger.start()
        app.state.audit_logger = audit_logger
        
        # Data Encryption
        data_encryption = DataEncryption()
        await data_encryption.start()
        app.state.data_encryption = data_encryption
        
        # Rate Limiter
        rate_limiter = AdvancedRateLimiter()
        app.state.rate_limiter = rate_limiter
        
        # Application services
        logger.info("Initializing application services...")
        
        # Monitoring
        monitoring_service = MonitoringService()
        await monitoring_service.start()
        app.state.monitoring = monitoring_service
        
        # Audio Processing
        audio_processor = AudioProcessor()
        await audio_processor.start()
        app.state.audio_processor = audio_processor
        
        # Communication clients
        whatsapp_client = WhatsAppClient()
        await whatsapp_client.start()
        app.state.whatsapp_client = whatsapp_client
        
        gmail_client = GmailClient()
        await gmail_client.start()
        app.state.gmail_client = gmail_client
        
        # NLP Engine
        nlp_engine = NLPEngine()
        await nlp_engine.start()
        app.state.nlp_engine = nlp_engine
        
        # PMS Adapter
        pms_adapter = PMSAdapter()
        await pms_adapter.start()
        app.state.pms_adapter = pms_adapter
        
        # Session Manager
        session_manager = SessionManager()
        await session_manager.start()
        app.state.session_manager = session_manager
        
        # Template Service
        template_service = TemplateService()
        await template_service.start()
        app.state.template_service = template_service
        
        # Lock Service
        lock_service = LockService()
        await lock_service.start()
        app.state.lock_service = lock_service
        
        # Orchestrator (depends on other services)
        orchestrator = Orchestrator()
        await orchestrator.start()
        app.state.orchestrator = orchestrator
        
        logger.info("All services initialized successfully")
        
        # Start background tasks
        await start_background_tasks(app)
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Shutting down Hotel Agent API...")
        
        # Stop background tasks
        await stop_background_tasks(app)
        
        # Stop services in reverse order
        services_to_stop = [
            "orchestrator", "lock_service", "template_service", "session_manager",
            "pms_adapter", "nlp_engine", "gmail_client", "whatsapp_client",
            "audio_processor", "monitoring", "rate_limiter", "data_encryption",
            "audit_logger", "jwt_auth", "redis", "database"
        ]
        
        for service_name in services_to_stop:
            try:
                service = getattr(app.state, service_name, None)
                if service and hasattr(service, 'stop'):
                    await service.stop()
                    logger.info(f"{service_name} stopped")
            except Exception as e:
                logger.error(f"Error stopping {service_name}: {e}")
        
        logger.info("Application shutdown complete")

async def start_background_tasks(app: FastAPI):
    """Start background tasks"""
    
    try:
        # Start monitoring background tasks
        if hasattr(app.state, 'monitoring'):
            await app.state.monitoring.start_background_tasks()
        
        # Start security cleanup tasks
        if hasattr(app.state, 'rate_limiter'):
            # Schedule periodic cleanup of expired rate limiting data
            asyncio.create_task(periodic_security_cleanup(app))
        
        # Start session cleanup
        if hasattr(app.state, 'session_manager'):
            asyncio.create_task(periodic_session_cleanup(app))
        
        logger.info("Background tasks started")
        
    except Exception as e:
        logger.error(f"Failed to start background tasks: {e}")

async def stop_background_tasks(app: FastAPI):
    """Stop background tasks"""
    
    try:
        # Cancel all running tasks
        tasks = [task for task in asyncio.all_tasks() if not task.done()]
        for task in tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("Background tasks stopped")
        
    except Exception as e:
        logger.error(f"Error stopping background tasks: {e}")

async def periodic_security_cleanup(app: FastAPI):
    """Periodic security data cleanup"""
    
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            
            if hasattr(app.state, 'rate_limiter'):
                await app.state.rate_limiter.cleanup_expired_data()
            
            if hasattr(app.state, 'audit_logger'):
                await app.state.audit_logger.cleanup_old_events()
            
            logger.debug("Security cleanup completed")
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Security cleanup error: {e}")

async def periodic_session_cleanup(app: FastAPI):
    """Periodic session cleanup"""
    
    while True:
        try:
            await asyncio.sleep(1800)  # Run every 30 minutes
            
            if hasattr(app.state, 'session_manager'):
                await app.state.session_manager.cleanup_expired_sessions()
            
            if hasattr(app.state, 'jwt_auth'):
                await app.state.jwt_auth.cleanup_expired_tokens()
            
            logger.debug("Session cleanup completed")
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    settings = get_settings()
    
    # Setup logging first
    setup_logging()
    
    app = FastAPI(
        title="Hotel Agent API",
        description="Intelligent Hotel Receptionist Agent with Multi-Channel Communication",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # Security middleware (add first, processes last)
    app.add_middleware(SecurityMiddleware)
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Trusted host middleware
    if settings.environment.is_production():
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.allowed_hosts
        )
    
    # Compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Include routers
    app.include_router(health.router, prefix="/health", tags=["Health"])
    app.include_router(security.router, tags=["Security"])
    app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
    app.include_router(nlp_router, prefix="/api/nlp", tags=["NLP"])
    app.include_router(pms_router, prefix="/api/pms", tags=["PMS"])
    app.include_router(admin.router, prefix="/admin", tags=["Admin"])
    app.include_router(metrics.router, prefix="/metrics", tags=["Metrics"])
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "service": "Hotel Agent API",
            "version": "1.0.0",
            "status": "running",
            "features": [
                "Multi-channel communication (WhatsApp, Gmail)",
                "Advanced NLP with hotel-specific intents",
                "PMS integration with intelligent workflows",
                "Enhanced security with JWT, MFA, and audit logging",
                "Real-time monitoring and alerting",
                "Audio processing with STT/TTS",
                "Rate limiting and DDoS protection",
                "Data encryption and privacy protection"
            ]
        }
    
    # Prometheus metrics endpoint (separate from metrics router for security)
    @app.get("/prometheus")
    async def prometheus_metrics(request: Request):
        """Prometheus metrics endpoint"""
        
        # Simple IP-based access control for metrics
        client_ip = request.client.host if request.client else "unknown"
        allowed_ips = ["127.0.0.1", "::1"]  # Add your monitoring system IPs
        
        if client_ip not in allowed_ips:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return Response(
            generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    
    # Security headers for all responses
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        """Add security headers to all responses"""
        
        response = await call_next(request)
        
        # Additional security headers not handled by SecurityMiddleware
        response.headers["X-Request-ID"] = getattr(request.state, 'request_id', 'unknown')
        response.headers["X-Response-Time"] = str(getattr(request.state, 'response_time', 0))
        
        return response
    
    logger.info(f"FastAPI application created - Environment: {settings.environment.value}")
    
    return app

# Create the application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment.is_development(),
        workers=1 if settings.environment.is_development() else 4,
        loop="uvloop",
        access_log=True,
        log_config=None  # Use our custom logging configuration
    )