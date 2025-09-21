# [PROMPT GA-02] app/routers/health.py

from datetime import datetime
import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from ..core.database import get_db
from ..core.redis_client import get_redis
from ..core.settings import settings
from ..core.logging import logger
from ..models.schemas import HealthCheck, ReadinessCheck, LivenessCheck

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check básico"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/ready", response_model=ReadinessCheck)
async def readiness_check(db: AsyncSession = Depends(get_db), redis_client: redis.Redis = Depends(get_redis)):
    """Verifica que todas las dependencias estén listas"""
    checks = {"database": False, "redis": False, "pms": False}

    # Check PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    # Check Redis
    try:
        await redis_client.ping()
        checks["redis"] = True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")

    # Check PMS
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.pms_base_url}/api/health",  # Asumiendo que QloApps tiene este endpoint
                timeout=5.0,
            )
            checks["pms"] = response.status_code == 200
    except Exception as e:
        logger.error(f"PMS health check failed: {e}")

    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={"ready": all_healthy, "checks": checks, "timestamp": datetime.utcnow().isoformat()},
    )


@router.get("/health/live", response_model=LivenessCheck)
async def liveness_check():
    """Verifica que la aplicación esté viva"""
    return {"alive": True, "timestamp": datetime.utcnow().isoformat()}
