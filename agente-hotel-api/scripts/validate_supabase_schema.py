#!/usr/bin/env python3
"""
Valida la existencia de tablas y algunos índices/claves tras aplicar el schema de Supabase.

Uso:
  python scripts/validate_supabase_schema.py

Lee DATABASE_URL de entorno o .env y verifica:
- Tablas esperadas en esquema 'public': users, user_sessions, password_history,
  tenants, tenant_user_identifiers, lock_audit.
- Opcional: presencia de índices por nombre si existen en schema.sql (best-effort).
"""

from __future__ import annotations

import asyncio
import os
import sys
import argparse
from pathlib import Path
from typing import Iterable

import asyncpg


EXPECTED_TABLES = {
    "users",
    "user_sessions",
    "password_history",
    "tenants",
    "tenant_user_identifiers",
    "lock_audit",
}


def load_env_file_if_present(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return
    try:
        for line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
    except Exception:
        pass


async def fetch_existing_tables(conn: asyncpg.Connection) -> set[str]:
    rows = await conn.fetch(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """
    )
    return {r["table_name"] for r in rows}


async def fetch_indexes_for(conn: asyncpg.Connection, table: str) -> set[str]:
    rows = await conn.fetch(
        """
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = $1
        """,
        table,
    )
    return {r["indexname"] for r in rows}


def print_set_diff(title: str, expected: Iterable[str], actual: Iterable[str]) -> None:
    expected_set = set(expected)
    actual_set = set(actual)
    missing = expected_set - actual_set
    extra = actual_set - expected_set
    print(f"\n{title}")
    print(f"  Encontradas: {len(actual_set)} | Esperadas: {len(expected_set)}")
    if missing:
        print(f"  ❌ Faltantes: {sorted(missing)}")
    else:
        print("  ✅ No faltan elementos")
    if extra:
        print(f"  ℹ️  Extras: {sorted(extra)}")


async def main(insecure: bool = False) -> int:
    load_env_file_if_present(Path(".env"))
    load_env_file_if_present(Path(".env.supabase"))
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DATABASE_URL")
    if not dsn:
        print("❌ Falta DATABASE_URL en el entorno/.env")
        return 1

    connect_kwargs: dict = {}
    sanitized_dsn = dsn

    if "supabase" in dsn and "sslmode=" in dsn and not insecure:
        base, _sep, query = dsn.partition('?')
        parts = [p for p in query.split('&') if not p.startswith('sslmode=') and p]
        sanitized_dsn = base + (('?' + '&'.join(parts)) if parts else '')
        connect_kwargs["ssl"] = True
        print(f"[INFO] Normalizando DSN Supabase (quitando sslmode): {sanitized_dsn}")
    elif "supabase" in dsn and not insecure:
        connect_kwargs["ssl"] = True
        print("[INFO] Activando SSL explícito para Supabase")

    if insecure:
        if os.getenv("CI") == "true" or os.getenv("ENVIRONMENT") == "production":
            print("❌ --insecure no permitido en CI o producción", file=sys.stderr)
            return 1
        confirmation = input("Type YES to continue with --insecure (SSL verification skipped): ").strip()
        if confirmation != "YES":
            print("Abortado (confirmación no recibida)")
            return 1
        base, _sep, query = dsn.partition('?')
        if query:
            parts = [p for p in query.split('&') if p and not p.startswith('sslmode=')]
            sanitized_dsn = base + (("?" + "&".join(parts)) if parts else '')
        connect_kwargs["ssl"] = False
        print(f"[WARN] SSL verification DISABLED (insecure mode). DSN: {sanitized_dsn}")
    else:
        if "supabase" in dsn and "sslmode=" in dsn:
            base, _sep, query = dsn.partition('?')
            parts = [p for p in query.split('&') if not p.startswith('sslmode=') and p]
            sanitized_dsn = base + (("?" + "&".join(parts)) if parts else '')
            connect_kwargs["ssl"] = True
            print(f"[INFO] Normalizando DSN Supabase (quitando sslmode): {sanitized_dsn}")
        elif "supabase" in dsn:
            connect_kwargs["ssl"] = True
            print("[INFO] Activando SSL explícito para Supabase")

    conn = await asyncpg.connect(sanitized_dsn, **connect_kwargs)
    try:
        existing = await fetch_existing_tables(conn)
        print_set_diff("Tablas en esquema 'public':", EXPECTED_TABLES, existing)

        # Validaciones rápidas de índices (best-effort): no fallar si no coinciden nombres
        for tbl in sorted(EXPECTED_TABLES):
            idx = await fetch_indexes_for(conn, tbl)
            print(f"  Índices en {tbl}: {sorted(idx) if idx else '—'}")
    finally:
        await conn.close()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Valida tablas e índices del schema en Supabase")
    parser.add_argument("--insecure", action="store_true", help="Desactivar verificación SSL (solo desarrollo, requiere confirmación)")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(insecure=args.insecure)))
