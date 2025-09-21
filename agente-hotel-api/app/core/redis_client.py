# [PROMPT GA-02] app/core/redis_client.py

import redis.asyncio as redis
from .settings import settings

REDIS_URL = str(getattr(settings, "redis_url"))
REDIS_POOL_SIZE = int(getattr(settings, "redis_pool_size", 20))
REDIS_PASSWORD = getattr(settings, "redis_password", None)
REDIS_PASSWORD_VALUE = (
    REDIS_PASSWORD.get_secret_value() if hasattr(REDIS_PASSWORD, "get_secret_value") and REDIS_PASSWORD else None
)

redis_pool = redis.ConnectionPool.from_url(REDIS_URL, password=REDIS_PASSWORD_VALUE, max_connections=REDIS_POOL_SIZE)


async def get_redis() -> redis.Redis:
    """Dependency to get a Redis connection."""
    return redis.Redis(connection_pool=redis_pool)
