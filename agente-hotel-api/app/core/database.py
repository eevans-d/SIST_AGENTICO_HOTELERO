# [PROMPT GA-02] app/core/database.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from .settings import settings

POSTGRES_URL = getattr(settings, "postgres_url")
POOL_SIZE = getattr(settings, "postgres_pool_size", 5)
MAX_OVERFLOW = getattr(settings, "postgres_max_overflow", 10)
DEBUG_SQL = bool(getattr(settings, "debug", False))

engine = create_async_engine(
    POSTGRES_URL,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_recycle=3600,
    echo=DEBUG_SQL,
)

AsyncSessionFactory = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """Dependency to get a database session."""
    async with AsyncSessionFactory() as session:
        yield session
