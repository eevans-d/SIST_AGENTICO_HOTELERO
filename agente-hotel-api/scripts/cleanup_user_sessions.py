#!/usr/bin/env python3
"""
Elimina sesiones expiradas de la tabla user_sessions en lotes.

Uso básico:
  python scripts/cleanup_user_sessions.py               # Borra expires_at < NOW()
  python scripts/cleanup_user_sessions.py --dry-run     # Solo muestra conteos
  python scripts/cleanup_user_sessions.py --older-than-days 7  # Borra expiradas hace >7 días

Notas de seguridad:
- Lee DATABASE_URL de entorno/.env.
- Usa SSL automático para Supabase (elimina sslmode y pasa ssl=True al conector asyncpg).
- Modo --insecure desactiva verificación SSL SOLO para desarrollo (requiere confirmación); bloqueado en CI/producción.

Idempotencia:
- Puede ejecutarse múltiples veces; no borra nada no vencido.

Salida:
- Imprime conteos de candidatos y borradas por lote. Código de salida 0 si OK.
"""
from __future__ import annotations

import asyncio
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

import asyncpg


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


async def count_candidates(conn: asyncpg.Connection, threshold_iso: str) -> int:
    row = await conn.fetchrow(
        """
        SELECT COUNT(*) AS c
        FROM user_sessions
        WHERE expires_at < $1
        """,
        threshold_iso,
    )
    return int(row["c"]) if row else 0


async def delete_batch(conn: asyncpg.Connection, threshold_iso: str, batch_size: int) -> int:
    # Ejecutar una sola vez y usar el status para conocer la cantidad borrada.
    status = await conn.execute(
        """
        WITH to_delete AS (
            SELECT id FROM user_sessions
            WHERE expires_at < $1
            ORDER BY expires_at ASC
            LIMIT $2
        )
        DELETE FROM user_sessions u
        USING to_delete d
        WHERE u.id = d.id
        """,
        threshold_iso,
        batch_size,
    )
    # status is like "DELETE <rows>"
    try:
        return int(status.split()[-1])
    except Exception:
        return 0


async def main(dry_run: bool, older_than_days: int, batch_size: int, insecure: bool) -> int:
    load_env_file_if_present(Path(".env"))
    load_env_file_if_present(Path(".env.supabase"))

    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DATABASE_URL")
    if not dsn:
        print("❌ Falta DATABASE_URL en el entorno/.env")
        return 1

    # Threshold time in UTC
    now_utc = datetime.now(timezone.utc)
    threshold = now_utc - timedelta(days=max(0, older_than_days))
    threshold_iso = threshold.isoformat()

    # SSL handling (Supabase)
    connect_kwargs: dict = {}
    sanitized_dsn = dsn

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
        total_candidates = await count_candidates(conn, threshold_iso)
        print(f"[INFO] Candidatos a borrar (expires_at < {threshold_iso}): {total_candidates}")
        if dry_run or total_candidates == 0:
            print("[DRY-RUN] No se borrará nada")
            return 0

        # Require interactive confirmation if not dry-run
        confirm = input("Escribe CLEANUP para confirmar borrado: ").strip()
        if confirm != "CLEANUP":
            print("Abortado (confirmación no recibida)")
            return 1

        deleted_total = 0
        while True:
            deleted = await delete_batch(conn, threshold_iso, batch_size)
            if deleted == 0:
                break
            deleted_total += deleted
            print(f"[OK] Borradas {deleted} filas en este lote (acumulado: {deleted_total})")
        print(f"[SUCCESS] Limpieza completada. Total borrado: {deleted_total}")
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Limpia sesiones expiradas de user_sessions")
    parser.add_argument("--dry-run", action="store_true", help="No borra, solo muestra conteos")
    parser.add_argument("--older-than-days", type=int, default=0, help="Borra expiradas hace más de N días (por defecto 0)")
    parser.add_argument("--batch-size", type=int, default=500, help="Tamaño de lote para DELETE en cascada")
    parser.add_argument("--insecure", action="store_true", help="Desactivar verificación SSL (solo DEV; confirmación requerida)")
    args = parser.parse_args()

    exit_code = asyncio.run(main(
        dry_run=args.dry_run,
        older_than_days=args.older_than_days,
        batch_size=args.batch_size,
        insecure=args.insecure,
    ))
    sys.exit(exit_code)
