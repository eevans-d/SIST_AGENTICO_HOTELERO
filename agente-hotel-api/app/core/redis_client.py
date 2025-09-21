# [PROMPT GA-02] app/core/redis_client.py

import redis.asyncio as redis
from .settings import settings

redis_pool = redis.ConnectionPool.from_url(
    settings.redis_url, password=settings.redis_password.get_secret_value(), max_connections=settings.redis_pool_size
)


async def get_redis() -> redis.Redis:
    """Dependency to get a Redis connection."""
    return redis.Redis(connection_pool=redis_pool)
