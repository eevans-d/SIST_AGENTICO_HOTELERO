#!/usr/bin/env python3
"""
Seed script para Supabase - Datos iniciales
============================================
Proyecto: SIST_AGENTICO_HOTELERO
Objetivo: Poblar datos mínimos necesarios en Supabase

Uso:
    1. Cargar variables de entorno:
       export $(cat .env.supabase | grep -v '^#' | xargs)
    
    2. Ejecutar script:
       poetry run python scripts/seed_supabase.py

Prerequisitos:
    - .env.supabase configurado con POSTGRES_URL válida
    - Migraciones Alembic ejecutadas (make supabase-migrate)
    - PostgreSQL accesible desde tu IP
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, UTC

# Añadir directorio raíz al path para imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text


async def seed_database():
    """Poblar base de datos con datos iniciales"""
    
    # Leer POSTGRES_URL desde variables de entorno
    postgres_url = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")
    
    if not postgres_url:
        print("❌ Error: POSTGRES_URL no encontrada en variables de entorno")
        print("   Ejecuta: export $(cat .env.supabase | grep -v '^#' | xargs)")
        sys.exit(1)
    
    print("🔗 Conectando a Supabase...")
    print(f"   URL: {postgres_url[:50]}...")  # Mostrar solo primeros 50 chars
    
    try:
        # Crear engine asíncrono
        engine = create_async_engine(postgres_url, echo=False)
        async_session_factory = sessionmaker(
            engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
        
        async with async_session_factory() as session:
            # ================================================================
            # 1. TENANT DEFAULT
            # ================================================================
            print("\n📦 Creando tenant default...")
            
            result = await session.execute(text("""
                INSERT INTO tenants (tenant_id, name, status, created_at, updated_at)
                VALUES (:tenant_id, :name, :status, :now, :now)
                ON CONFLICT (tenant_id) DO UPDATE
                SET name = EXCLUDED.name,
                    updated_at = :now
                RETURNING id, tenant_id, name
            """), {
                "tenant_id": "default",
                "name": "Default Tenant",
                "status": "active",
                "now": datetime.now(UTC)
            })
            
            tenant = result.fetchone()
            if tenant:
                print(f"   ✅ Tenant creado: ID={tenant[0]}, tenant_id={tenant[1]}, name={tenant[2]}")
            
            # ================================================================
            # 2. VERIFICAR DATOS
            # ================================================================
            print("\n🔍 Verificando datos insertados...")
            
            # Contar tenants
            result = await session.execute(text("SELECT COUNT(*) FROM tenants"))
            tenant_count = result.scalar()
            print(f"   📊 Total tenants: {tenant_count}")
            
            # Listar tenants activos
            result = await session.execute(text("""
                SELECT tenant_id, name, status 
                FROM tenants 
                WHERE status = 'active'
                ORDER BY created_at
            """))
            
            tenants = result.fetchall()
            print("   📋 Tenants activos:")
            for t in tenants:
                print(f"      - {t[0]}: {t[1]} ({t[2]})")
            
            # ================================================================
            # 3. COMMIT
            # ================================================================
            await session.commit()
            print("\n✅ Seed completado exitosamente")
            
        # Cerrar engine
        await engine.dispose()
        
    except Exception as e:
        print(f"\n❌ Error durante seed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def verify_connection():
    """Verificar que podemos conectar a Supabase"""
    
    postgres_url = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")
    
    if not postgres_url:
        return False
    
    try:
        engine = create_async_engine(postgres_url, echo=False)
        
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print("✅ Conexión exitosa")
            print(f"   PostgreSQL: {version[:80]}...")
            
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False


async def main():
    """Punto de entrada principal"""
    
    print("=" * 80)
    print("🌱 SUPABASE SEED SCRIPT")
    print("=" * 80)
    
    # Verificar conexión primero
    print("\n🔍 Verificando conexión a Supabase...")
    if not await verify_connection():
        print("\n❌ No se pudo conectar a Supabase")
        print("   Verifica que:")
        print("   1. POSTGRES_URL está configurada correctamente")
        print("   2. Supabase está accesible desde tu IP")
        print("   3. Las credenciales son correctas")
        sys.exit(1)
    
    # Ejecutar seed
    await seed_database()
    
    print("\n" + "=" * 80)
    print("✅ SEED COMPLETADO")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
