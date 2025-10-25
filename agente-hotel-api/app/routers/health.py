# [PROMPT GA-02] app/routers/health.py

from datetime import datetime, timezone
import httpx
import os
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
from .metrics import dependency_up, readiness_up, readiness_last_check_timestamp

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check básico"""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/health/ready", response_model=ReadinessCheck)
async def readiness_check(db: AsyncSession = Depends(get_db), redis_client: redis.Redis = Depends(get_redis)):
    """Verifica que todas las dependencias estén listas.

    - DB y Redis son siempre requeridos.
    - PMS es opcional: solo se chequea si `check_pms_in_readiness` es True y `pms_type` no es `mock`.
    """
    checks = {"database": False, "redis": False}

    # Read flags directly from environment to ensure they're respected on Fly
    check_db = os.getenv("CHECK_DB_IN_READINESS", "true").lower() in ("true", "1", "yes")
    check_redis = os.getenv("CHECK_REDIS_IN_READINESS", "true").lower() in ("true", "1", "yes")

    # Check PostgreSQL (configurable)
    if check_db:
        try:
            await db.execute(text("SELECT 1"))
            checks["database"] = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
    else:
        checks["database"] = True  # skipped by config

    # Check Redis (configurable)
    if check_redis:
        try:
            await redis_client.ping()
            checks["redis"] = True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
    else:
        checks["redis"] = True  # skipped by config

    # PMS: opcional por configuración y no bloquea si es tipo MOCK
    pms_required = bool(getattr(settings, "check_pms_in_readiness", False))
    pms_type = getattr(settings, "pms_type", None)
    # Use .value to get the actual enum value (e.g., "mock" instead of "PMSType.MOCK")
    if pms_type is None:
        pms_type_value = ""
    else:
        pms_type_value = pms_type.value if hasattr(pms_type, "value") else str(pms_type).lower()

    if not pms_required or pms_type_value == "mock":
        checks["pms"] = True
    else:
        checks["pms"] = False
        try:
            async with httpx.AsyncClient() as client:
                # Intento simple al base_url del PMS; podría reemplazarse por un endpoint /health propio del PMS
                response = await client.get(str(settings.pms_base_url), timeout=5.0)
                checks["pms"] = response.status_code < 500
        except Exception as e:
            logger.error(f"PMS health check failed: {e}")

    all_healthy = all(checks.values())

    # Actualizar métricas de readiness/dependencias
    try:
        for dep, ok in checks.items():
            dependency_up.labels(name=dep).set(1 if ok else 0)
        readiness_up.set(1 if all_healthy else 0)
        readiness_last_check_timestamp.set(int(datetime.now(timezone.utc).timestamp()))
    except Exception as e:
        logger.error(f"Failed to update readiness metrics: {e}")
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={"ready": all_healthy, "checks": checks, "timestamp": datetime.now(timezone.utc).isoformat()},
    )


@router.get("/health/live", response_model=LivenessCheck)
async def liveness_check():
    """Verifica que la aplicación esté viva"""
    return {"alive": True, "timestamp": datetime.now(timezone.utc).isoformat()}
