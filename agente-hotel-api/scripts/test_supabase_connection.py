#!/usr/bin/env python3
"""
Test Supabase Postgres connectivity using SQLAlchemy async engine.

- Reads DATABASE_URL via app.core.settings (pydantic settings)
- Ensures asyncpg driver and sslmode=require are present
- Executes a simple SELECT version() to validate connectivity

Usage:
    python scripts/test_supabase_connection.py [--insecure]

Exit codes:
    0 - success
    1 - configuration error (missing/invalid URL)
    2 - connection failure (network/SSL/auth)
"""
from __future__ import annotations

import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

import argparse

try:
    from app.core.settings import settings
except Exception as e:  # pragma: no cover
    print(f"[ERROR] Cannot import settings: {e}")
    sys.exit(1)


async def main(insecure: bool = False) -> int:
    url = settings.postgres_url
    print(f"[INFO] Using Postgres URL: {url}")

    if "asyncpg" not in url:
        print("[WARN] URL does not include asyncpg driver. settings should auto-convert.")
    if "sslmode=require" not in url:
        print("[WARN] URL does not include sslmode=require. This is required by Supabase.")

    if insecure:
        if os.getenv("CI") == "true" or os.getenv("ENVIRONMENT") == "production":
            print("❌ --insecure no permitido en CI o producción", file=sys.stderr)
            return 1
        confirmation = input("Type YES to continue with --insecure (SSL verification skipped): ").strip()
        if confirmation != "YES":
            print("Abortado (confirmación no recibida)")
            return 1
        connect_args = {"ssl": False}
        if "supabase" in url and "sslmode=require" in url:
            base, _sep, query = url.partition('?')
            params = [p for p in query.split('&') if p and not p.startswith('sslmode=')]
            url = base + (('?' + '&'.join(params)) if params else '')
            print(f"[INFO] Normalized URL (removed sslmode) for insecure mode: {url}")
        print("[WARN] SSL verification DISABLED (insecure mode)")
    elif "supabase" in url and "sslmode=require" in url:
        base, _sep, query = url.partition('?')
        params = [p for p in query.split('&') if p and not p.startswith('sslmode=')]
        url = base + (('?' + '&'.join(params)) if params else '')
        print(f"[INFO] Normalized URL (removed sslmode): {url}")
        connect_args = {"ssl": True}
    else:
        connect_args = {}

    engine = create_async_engine(url, echo=False, pool_pre_ping=True, connect_args=connect_args)
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


if __name__ == "__main__":  # pragma: no cover
    parser = argparse.ArgumentParser(description="Prueba conexión a Supabase con SELECT version()")
    parser.add_argument("--insecure", action="store_true", help="Desactivar verificación SSL (solo desarrollo, requiere confirmación)")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.insecure)))
