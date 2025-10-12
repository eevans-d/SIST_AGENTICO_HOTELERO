# [PROMPT GA-02] app/core/redis_client.py

import redis.asyncio as redis
from .settings import Environment, settings

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
    "client_name": f"hotel_agent_{settings.environment.value}",  # Client name for monitoring
}

# Additional production optimizations for Redis
if settings.environment == Environment.PROD:
    pool_kwargs.update({
        "socket_connect_timeout": 5,
        "socket_timeout": 5,
        "retry_on_timeout": True,
    })

redis_pool = redis.ConnectionPool.from_url(REDIS_URL, **pool_kwargs)


async def get_redis() -> redis.Redis:
    """Dependency to get a Redis connection."""
    return redis.Redis(connection_pool=redis_pool)
