from __future__ import annotations

import os
from logging.config import fileConfig
import sys
from pathlib import Path

import asyncio
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Alembic Config object, provides access to values within the .ini file
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Ensure 'app' package is importable when running via Alembic CLI
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import target metadata from app models (after sys.path patch)
from app.models.lock_audit import Base as LockAuditBase  # type: ignore  # noqa: E402
from app.models import tenant as tenant_models  # type: ignore  # noqa: E402

target_metadata = LockAuditBase.metadata


def get_database_url() -> str:
    # Priority: ALEMBIC_DB_URL > POSTGRES_URL > from settings
    url = os.getenv("ALEMBIC_DB_URL") or os.getenv("POSTGRES_URL")
    if url:
        return url
    try:
        from app.core.settings import settings  # lazy import

        return settings.postgres_url
    except Exception:
        # Fallback to SQLite file if nothing provided
        return "sqlite:///./agente_hotel.db"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """

    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    configuration = config.get_section(config.config_ini_section) or {}
    url = get_database_url()
    configuration["sqlalchemy.url"] = url

    # Async drivers need async engine
    if "+asyncpg" in url or url.startswith("sqlite+aiosqlite"):
        async def do_run_migrations() -> None:
            connectable = async_engine_from_config(
                configuration,
                prefix="sqlalchemy.",
                poolclass=pool.NullPool,
                future=True,
            )
            async with connectable.connect() as connection:
                await connection.run_sync(
                    lambda sync_conn: context.configure(connection=sync_conn, target_metadata=target_metadata, compare_type=True)
                )
                await connection.run_sync(lambda _: context.begin_transaction())
                await connection.run_sync(lambda _: context.run_migrations())

        asyncio.run(do_run_migrations())
    else:
        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
