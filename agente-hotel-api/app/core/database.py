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
    "pool_recycle": 1800 if settings.environment == Environment.PROD else 3600,
    "echo": DEBUG_SQL,
    "pool_pre_ping": True,
}

# Additional production optimizations
connect_args = {
    "server_settings": {
        "jit": "off",
        "application_name": f"hotel_agent_{settings.environment.value}",
    }
}

# Cost guardrails for Supabase or when explicitly requested
is_supabase = (
    "supabase.co" in (POSTGRES_URL or "")
    or "supabase.com" in (POSTGRES_URL or "")
    or bool(getattr(settings, "use_supabase", False))
)
if is_supabase:
    # Set conservative timeouts to avoid runaway queries consuming credits
    # Values in milliseconds
    connect_args["server_settings"].update(
        {
            "statement_timeout": "15000",  # 15s hard timeout per statement
            "idle_in_transaction_session_timeout": "10000",  # 10s
        }
    )
    # Enforce SSL for Supabase connections
    connect_args["ssl"] = "require"
    # Disable prepared statements for PgBouncer (Supabase transaction pooler)
    connect_args["statement_cache_size"] = 0
    # Ensure asyncpg doesn't try to prepare statements (redundant but safe)
    # connect_args["prepare_threshold"] = None

if settings.environment == Environment.PROD:
    engine_kwargs.update({"pool_timeout": 30})

engine_kwargs["connect_args"] = connect_args
print(f"DEBUG: connect_args={connect_args}")

engine = create_async_engine(POSTGRES_URL, **engine_kwargs)

# --- Instrumentación de errores de base de datos (statement_timeout) ---
try:
    from sqlalchemy import event

    @event.listens_for(engine, "handle_error")
    def _db_handle_error(context):  # type: ignore[override]
        try:
            exc = context.original_exception
            if exc and "statement timeout" in str(exc).lower():
                from app.services.metrics_service import metrics_service
                metrics_service.inc_statement_timeout()
        except Exception:
            # Nunca permitir que la instrumentación rompa el flujo normal
            pass
except Exception:
    # Si falla la instalación del listener, continuar sin métricas de timeout
    pass

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
