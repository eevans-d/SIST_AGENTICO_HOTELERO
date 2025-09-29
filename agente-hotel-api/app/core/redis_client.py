# [PROMPT GA-02] app/core/redis_client.py

import redis.asyncio as redis
from .settings import Environment, settings
from .logging import logger

REDIS_URL = str(getattr(settings, "redis_url"))
REDIS_POOL_SIZE = int(getattr(settings, "redis_pool_size", 20))
REDIS_PASSWORD = getattr(settings, "redis_password", None)
REDIS_PASSWORD_VALUE = (
    REDIS_PASSWORD.get_secret_value() if hasattr(REDIS_PASSWORD, "get_secret_value") and REDIS_PASSWORD else None
)

# Production-optimized Redis pool configuration
pool_kwargs = {
    "max_connections": REDIS_POOL_SIZE,
    "password": REDIS_PASSWORD_VALUE,
    "retry_on_timeout": True,
    "health_check_interval": 30,  # Health check every 30 seconds
    "socket_keepalive": True,
    "socket_keepalive_options": {},
}

# Additional production optimizations for Redis
if settings.environment == Environment.PROD:
    pool_kwargs.update(
        {
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
            "retry_on_timeout": True,
            "connection_kwargs": {"client_name": f"hotel_agent_{settings.environment.value}"},
        }
    )

redis_pool = redis.ConnectionPool.from_url(REDIS_URL, **pool_kwargs)


async def get_redis() -> redis.Redis:
    """Redis dependency with enhanced error handling and connection validation."""
    client = None
    try:
        client = redis.Redis(connection_pool=redis_pool)
        # Test connection health
        await client.ping()
        return client
    except Exception as e:
        logger.error(
            "Redis connection error",
            error=str(e),
            error_type=type(e).__name__,
            redis_url_masked=REDIS_URL.split("@")[1] if "@" in REDIS_URL else REDIS_URL.split("://")[0] + "://***",
        )
        if client:
            await client.close()
        raise


async def check_redis_health() -> bool:
    """Check Redis health for monitoring purposes."""
    try:
        client = redis.Redis(connection_pool=redis_pool)
        await client.ping()
        await client.close()
        return True
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return False


# Global Redis client for services that need direct access
async def get_redis_client() -> redis.Redis:
    """Get Redis client for direct use in services."""
    return redis.Redis(connection_pool=redis_pool)
