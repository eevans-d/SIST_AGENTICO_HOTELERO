# [PROMPT GA-02] app/core/database.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from .settings import Environment, settings
from .logging import logger

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
    engine_kwargs.update(
        {
            "pool_recycle": 1800,  # More aggressive recycling in production
            "pool_timeout": 30,  # Timeout waiting for connection
            "connect_args": {
                "server_settings": {
                    "jit": "off",  # Disable JIT for consistent performance
                    "application_name": f"hotel_agent_{settings.environment.value}",
                }
            },
        }
    )

engine = create_async_engine(POSTGRES_URL, **engine_kwargs)

AsyncSessionFactory = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """Database dependency with enhanced error handling and connection validation."""
    session = None
    try:
        session = AsyncSessionFactory()
        # Test connection health with a simple query
        await session.execute(text("SELECT 1"))
        yield session
    except Exception as e:
        if session:
            await session.rollback()
        logger.error(
            "Database connection error",
            error=str(e),
            error_type=type(e).__name__,
            postgres_url_masked=POSTGRES_URL.split("@")[1] if "@" in POSTGRES_URL else "unknown",
        )
        raise
    finally:
        if session:
            try:
                await session.close()
            except Exception as e:
                logger.warning("Error closing database connection", error=str(e))


async def check_database_health() -> bool:
    """Check database health for monitoring purposes."""
    try:
        async with AsyncSessionFactory() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return False
