#!/usr/bin/env python3
"""
Test Supabase Postgres connectivity using SQLAlchemy async engine.

- Reads DATABASE_URL via app.core.settings (pydantic settings)
- Ensures asyncpg driver and sslmode=require are present
- Executes a simple SELECT version() to validate connectivity

Usage:
    python scripts/test_supabase_connection.py

Exit codes:
    0 - success
    1 - configuration error (missing/invalid URL)
    2 - connection failure (network/SSL/auth)
"""
from __future__ import annotations

import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

try:
    from app.core.settings import settings
except Exception as e:  # pragma: no cover
    print(f"[ERROR] Cannot import settings: {e}")
    sys.exit(1)


async def main() -> int:
    url = settings.postgres_url
    print(f"[INFO] Using Postgres URL: {url}")

    if "asyncpg" not in url:
        print("[WARN] URL does not include asyncpg driver. settings should auto-convert.")
    if "sslmode=require" not in url:
        print("[WARN] URL does not include sslmode=require. This is required by Supabase.")

    engine = create_async_engine(url, echo=False, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version();"))
            version = result.scalar_one()
            print(f"[OK] Connected to PostgreSQL: {version}")
    except Exception as e:
        print("[ERROR] Connection failed:")
        print(f"        {type(e).__name__}: {e}")
        await engine.dispose()
        return 2

    await engine.dispose()
    print("[SUCCESS] Supabase connection test passed")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
