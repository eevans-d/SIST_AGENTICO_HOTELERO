# [PROMPT GA-02] app/core/database.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator

from .settings import Environment, settings

POSTGRES_URL = getattr(settings, "postgres_url")
POOL_SIZE = getattr(settings, "postgres_pool_size", 10)
MAX_OVERFLOW = getattr(settings, "postgres_max_overflow", 10)
DEBUG_SQL = bool(getattr(settings, "debug", False))

# Production-optimized engine configuration
engine_kwargs = {
    "pool_size": POOL_SIZE,
    "max_overflow": MAX_OVERFLOW,
    "pool_recycle": 3600,  # Recycle connections after 1 hour
    "echo": DEBUG_SQL,
    "pool_pre_ping": True,  # Validate connections before use
}

# Additional production optimizations
if settings.environment == Environment.PROD:
    engine_kwargs.update({
        "pool_recycle": 1800,  # More aggressive recycling in production
        "pool_timeout": 30,     # Timeout waiting for connection
        "connect_args": {
            "server_settings": {
                "jit": "off",  # Disable JIT for consistent performance
                "application_name": f"hotel_agent_{settings.environment.value}"
            }
        }
    })

engine = create_async_engine(POSTGRES_URL, **engine_kwargs)

# SQLAlchemy 2.0 style: use async_sessionmaker instead of sessionmaker
AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get a database session."""
    async with AsyncSessionFactory() as session:
        yield session
