"""
Script de migración para crear la tabla audit_logs

Ejecutar con:
    python scripts/create_audit_logs_table.py
"""

import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from app.models.audit_log import Base


async def create_audit_logs_table():
    """Crear tabla audit_logs en PostgreSQL"""
    print("📋 Creando tabla audit_logs...")

    try:
        async with engine.begin() as conn:
            # Crear solo la tabla AuditLog
            await conn.run_sync(Base.metadata.create_all)

        print("✅ Tabla audit_logs creada exitosamente")
        print("\nEstructura de la tabla:")
        print("  - id (INTEGER, PK, autoincrement)")
        print("  - timestamp (DATETIME, indexed)")
        print("  - event_type (VARCHAR(100), indexed)")
        print("  - user_id (VARCHAR(255), indexed)")
        print("  - ip_address (VARCHAR(45), indexed)")
        print("  - resource (VARCHAR(500))")
        print("  - details (JSON)")
        print("  - tenant_id (VARCHAR(100), indexed)")
        print("  - severity (VARCHAR(20), indexed)")
        print("  - created_at (DATETIME)")
        print("\nÍndices creados:")
        print("  - idx_audit_timestamp_event (timestamp, event_type)")
        print("  - idx_audit_user_timestamp (user_id, timestamp)")
        print("  - idx_audit_tenant_timestamp (tenant_id, timestamp)")

    except Exception as e:
        print(f"❌ Error al crear tabla: {e}")
        raise


async def verify_table():
    """Verificar que la tabla fue creada correctamente"""
    from sqlalchemy import text

    print("\n🔍 Verificando tabla...")

    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_name = 'audit_logs'")
            )
            row = result.fetchone()

            if row:
                print("✅ Tabla 'audit_logs' verificada en PostgreSQL")

                # Verificar columnas
                columns_result = await conn.execute(
                    text("""
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_name = 'audit_logs'
                        ORDER BY ordinal_position
                    """)
                )

                print("\nColumnas:")
                for col in columns_result:
                    print(f"  - {col[0]}: {col[1]}")
            else:
                print("❌ Tabla 'audit_logs' no encontrada")

    except Exception as e:
        print(f"❌ Error al verificar tabla: {e}")


async def main():
    """Función principal"""
    print("=" * 60)
    print("MIGRACIÓN: Crear tabla audit_logs")
    print("=" * 60)

    await create_audit_logs_table()
    await verify_table()

    print("\n" + "=" * 60)
    print("✅ Migración completada")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
