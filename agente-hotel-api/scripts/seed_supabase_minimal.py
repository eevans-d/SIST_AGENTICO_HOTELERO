#!/usr/bin/env python3
"""Seed mínimo para Supabase (tenant + identificador + usuario admin opcional).

Objetivo: Poblar datos esenciales SIN generar costes excesivos. Idempotente.

Uso seguro:
  DATABASE_URL=postgresql://... python scripts/seed_supabase_minimal.py --tenant hotel-demo --name "Hotel Demo" \
      --identifier +5491112345678 --admin-email admin@hotel-demo.com --admin-username admin --admin-password admin123

Flags:
  --skip-admin        Omite creación de usuario admin
  --force-password    Fuerza password incluso si usuario existe (rotación)

Notas:
  - El password se hashea con bcrypt (cost=12)
  - No recrea tablas; asume schema aplicado
  - Usa transacción para consistencia
  - Detecta Supabase y normaliza sslmode=require
"""

from __future__ import annotations

import argparse
import os
import sys
import asyncio
from typing import Optional
import bcrypt
import asyncpg


def normalize_supabase_url(url: str) -> str:
    if "supabase" in url and "sslmode=" in url:
        base, _sep, query = url.partition('?')
        parts = [p for p in query.split('&') if not p.startswith('sslmode=') and p]
        return base + (('?' + '&'.join(parts)) if parts else '')
    return url


async def seed(
    dsn: str,
    tenant_slug: str,
    tenant_name: str,
    identifier: Optional[str],
    admin_email: Optional[str],
    admin_username: Optional[str],
    admin_password: Optional[str],
    skip_admin: bool,
    force_password: bool,
    update_if_exists: bool,
) -> None:
    dsn_norm = normalize_supabase_url(dsn)
    conn = await asyncpg.connect(dsn_norm, ssl=True if "supabase" in dsn_norm else None)
    try:
        async with conn.transaction():
            # 1. Tenant
            tenant_row = await conn.fetchrow(
                "SELECT id FROM tenants WHERE tenant_id=$1", tenant_slug
            )
            if tenant_row:
                tenant_id = tenant_row["id"]
                print(f"[OK] Tenant existente: {tenant_slug} (id={tenant_id})")
                if update_if_exists:
                    await conn.execute(
                        "UPDATE tenants SET name=$2, updated_at=NOW() WHERE id=$1", tenant_id, tenant_name
                    )
            else:
                tenant_id = await conn.fetchval(
                    """
                    INSERT INTO tenants (tenant_id, name, status)
                    VALUES ($1, $2, 'active') RETURNING id
                    """,
                    tenant_slug,
                    tenant_name,
                )
                print(f"[CREATE] Tenant creado: {tenant_slug} (id={tenant_id})")

            # 2. Identifier (phone/email) → tenant_user_identifiers
            if identifier:
                ident_row = await conn.fetchrow(
                    "SELECT id FROM tenant_user_identifiers WHERE identifier=$1", identifier
                )
                if ident_row:
                    print(f"[OK] Identifier existente: {identifier}")
                else:
                    await conn.execute(
                        """
                        INSERT INTO tenant_user_identifiers (tenant_id, identifier)
                        VALUES ($1, $2) ON CONFLICT (identifier) DO NOTHING
                        """,
                        tenant_id,
                        identifier,
                    )
                    print(f"[CREATE] Identifier añadido: {identifier}")

            # 3. Admin user
            if not skip_admin and admin_email and admin_username and admin_password:
                user_row = await conn.fetchrow(
                    "SELECT id, hashed_password FROM users WHERE email=$1", admin_email
                )
                hashed_new = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt(12)).decode()
                if user_row:
                    if force_password:
                        await conn.execute(
                            """
                            UPDATE users SET hashed_password=$2, updated_at=NOW()
                            WHERE id=$1
                            """,
                            user_row["id"],
                            hashed_new,
                        )
                        print(f"[ROTATE] Password actualizado para usuario {admin_email}")
                    else:
                        print(f"[OK] Usuario existente {admin_email} (sin cambio de password)")
                else:
                    user_id = f"usr_admin_{tenant_slug}"
                    await conn.execute(
                        """
                        INSERT INTO users (id, username, email, hashed_password, full_name, is_active, is_superuser, tenant_id)
                        VALUES ($1, $2, $3, $4, $5, TRUE, TRUE, $6)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        user_id,
                        admin_username,
                        admin_email,
                        hashed_new,
                        "Administrator",
                        tenant_slug,
                    )
                    print(f"[CREATE] Usuario admin creado: {admin_email}")
            elif not skip_admin:
                print("[WARN] Datos incompletos para crear admin (email/username/password)")
        print("[DONE] Seed mínimo completado")
    finally:
        await conn.close()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed mínimo Supabase")
    p.add_argument("--tenant", required=True, help="Slug tenant_id (ej: hotel-demo)")
    p.add_argument("--name", required=True, help="Nombre legible del tenant")
    p.add_argument("--identifier", help="Phone/email para mapeo dinámico (+E.164 o correo)")
    p.add_argument("--admin-email", help="Email usuario admin")
    p.add_argument("--admin-username", help="Username usuario admin")
    p.add_argument("--admin-password", help="Password plano (será hasheado bcrypt)")
    p.add_argument("--skip-admin", action="store_true", help="Omitir creación de usuario admin")
    p.add_argument("--force-password", action="store_true", help="Forzar rotación de password si ya existe usuario")
    p.add_argument("--update-if-exists", action="store_true", help="Actualizar nombre de tenant si ya existe")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("❌ Falta DATABASE_URL en entorno")
        sys.exit(1)
    if "sslmode=require" not in dsn:
        print("⚠️  Recomendado incluir sslmode=require en DATABASE_URL para Supabase")
    try:
        asyncio.run(
            seed(
                dsn,
                tenant_slug=args.tenant,
                tenant_name=args.name,
                identifier=args.identifier,
                admin_email=args.admin_email,
                admin_username=args.admin_username,
                admin_password=args.admin_password,
                skip_admin=args.skip_admin,
                force_password=args.force_password,
                update_if_exists=args.update_if_exists,
            )
        )
    except KeyboardInterrupt:
        print("Interrumpido")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Seed falló: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
