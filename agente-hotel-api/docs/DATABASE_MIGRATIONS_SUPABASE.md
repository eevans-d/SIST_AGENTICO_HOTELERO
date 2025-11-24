# Migraciones de Base de Datos con Supabase

## Resumen Ejecutivo

Este documento detalla la configuración y solución implementada para ejecutar migraciones de Alembic contra Supabase, que utiliza **PgBouncer en modo transacción** como connection pooler.

**Problema Principal**: `DuplicatePreparedStatementError` al ejecutar migraciones debido a incompatibilidad entre asyncpg/SQLAlchemy prepared statements y PgBouncer Transaction Mode.

**Solución**: Conexión directa (puerto 5432) para migraciones, bypassing PgBouncer completamente.

---

## Arquitectura de Conexión

### Puertos y Modos de Conexión

| Puerto | Propósito | Uso | Pooling |
|--------|-----------|-----|---------|
| **5432** | Conexión Directa PostgreSQL | Migraciones Alembic, tareas administrativas | ❌ Sin pooling (NullPool) |
| **6543** | PgBouncer Pooler (Transaction Mode) | Runtime API, operaciones normales | ✅ PgBouncer pooling |

### Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────┐
│                   SUPABASE POSTGRESQL                       │
│                                                             │
│  ┌──────────────────────┐      ┌──────────────────────┐   │
│  │  Puerto 5432         │      │  Puerto 6543         │   │
│  │  (Direct Connection) │      │  (PgBouncer Pooler)  │   │
│  │                      │      │  Transaction Mode    │   │
│  └──────────────────────┘      └──────────────────────┘   │
│           ▲                              ▲                 │
│           │                              │                 │
└───────────┼──────────────────────────────┼─────────────────┘
            │                              │
            │                              │
   ┌────────┴────────┐          ┌─────────┴──────────┐
   │  ALEMBIC        │          │  FASTAPI APP       │
   │  Migrations     │          │  Runtime           │
   │                 │          │                    │
   │  • NullPool     │          │  • NullPool        │
   │  • cache_size=0 │          │  • cache_size=0    │
   └─────────────────┘          └────────────────────┘
```

---

## Configuración Implementada

### 1. `alembic/env.py` (Configuración de Migraciones)

```python
def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    url = get_database_url()
    configuration["sqlalchemy.url"] = url

    # Handle Supabase/PgBouncer prepared statements issue
    connect_args = {}
    if "supabase" in url or os.getenv("DISABLE_STATEMENT_CACHE", "false").lower() == "true":
        connect_args["statement_cache_size"] = 0
    
    print(f"DEBUG: Alembic URL: {url}")
    print(f"DEBUG: connect_args: {connect_args}")

    # Async drivers need async engine
    if "+asyncpg" in url or url.startswith("sqlite+aiosqlite"):
        # Force Direct Connection for Migrations (Port 5432) if using Supabase
        # This bypasses PgBouncer Transaction Mode which is incompatible with Alembic/SQLAlchemy prepared statements
        if "supabase" in url and ":6543" in url:
             print("DEBUG: Switching to Direct Connection (Port 5432) for migrations...")
             url = url.replace(":6543", ":5432")
        
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy.pool import NullPool
        
        # Create a dedicated engine for migrations
        connect_args = {"statement_cache_size": 0}
        
        app_engine = create_async_engine(
            url,
            connect_args=connect_args,
            poolclass=NullPool
        )

        def do_run_migrations_sync(connection):
            context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
            with context.begin_transaction():
                context.run_migrations()

        async def do_run_migrations() -> None:
            async with app_engine.connect() as connection:
                await connection.run_sync(do_run_migrations_sync)
            
            await app_engine.dispose()

        asyncio.run(do_run_migrations())
```

**Características Clave**:
- ✅ Detección automática de URLs de Supabase
- ✅ Cambio automático de puerto `6543` → `5432`
- ✅ `NullPool` para evitar pooling client-side
- ✅ `statement_cache_size=0` para desactivar prepared statements
- ✅ Motor dedicado para migraciones (no reutiliza el del runtime)

### 2. `app/core/database.py` (Configuración Runtime)

```python
# Cost guardrails for Supabase or when explicitly requested
is_supabase = (
    "supabase.co" in (POSTGRES_URL or "")
    or "supabase.com" in (POSTGRES_URL or "")
    or bool(getattr(settings, "use_supabase", False))
)

if is_supabase:
    # Set conservative timeouts to avoid runaway queries consuming credits
    connect_args["server_settings"].update(
        {
            "statement_timeout": "15000",  # 15s hard timeout per statement
            "idle_in_transaction_session_timeout": "10000",  # 10s
        }
    )
    # Enforce SSL for Supabase connections
    connect_args["ssl"] = "require"
    
    # Use NullPool for Supabase (PgBouncer transaction mode)
    from sqlalchemy.pool import NullPool
    engine_kwargs["poolclass"] = NullPool
    engine_kwargs.pop("pool_size", None)
    engine_kwargs.pop("max_overflow", None)
    engine_kwargs.pop("pool_recycle", None)

# Disable prepared statements if Supabase (pgbouncer) or explicitly requested
if is_supabase or os.getenv("DISABLE_STATEMENT_CACHE", "false").lower() == "true":
    connect_args["statement_cache_size"] = 0
```

**Razones para NullPool**:
1. **Evita conflictos con PgBouncer**: PgBouncer ya hace pooling, el pooling client-side es redundante
2. **Compatibilidad con Serverless**: Supabase puede cerrar conexiones idle, NullPool abre/cierra según necesidad
3. **Prevent state leaks**: Transaction Mode de PgBouncer no soporta estado de conexión entre transacciones

---

## Por Qué Falla PgBouncer Transaction Mode con Prepared Statements

### El Problema Técnico

**PgBouncer Transaction Mode**:
- Asigna una conexión de backend solo durante la duración de una transacción
- Una vez que `COMMIT`/`ROLLBACK` se ejecuta, la conexión vuelve al pool y puede ser asignada a otro cliente

**asyncpg Prepared Statements**:
- asyncpg crea prepared statements con identificadores únicos (ej: `__asyncpg_stmt_1__`)
- Estos prepared statements están **ligados a una conexión específica**
- Si PgBouncer reutiliza la conexión para otro cliente, el nuevo cliente puede intentar crear un prepared statement con el mismo identificador

**Resultado**: `DuplicatePreparedStatementError`

### Ejemplo de Secuencia de Error

```
Cliente A → PgBouncer → Backend Connection #1
  PREPARE "__asyncpg_stmt_1__" AS SELECT ...
  COMMIT
  [Conexión #1 vuelve al pool]

Cliente B → PgBouncer → Backend Connection #1 (misma)
  PREPARE "__asyncpg_stmt_1__" AS SELECT ...
  ❌ ERROR: prepared statement "__asyncpg_stmt_1__" already exists
```

### Soluciones Intentadas (sin éxito)

| Solución | Resultado | Por Qué Falló |
|----------|-----------|---------------|
| `statement_cache_size=0` en `connect_args` | ❌ Falla | SQLAlchemy fuerza preparación en `dialect.initialize()` |
| `NullPool` + `statement_cache_size=0` | ❌ Falla | SQLAlchemy aún prepara la query `SELECT pg_catalog.version()` en inicialización |
| `AUTOCOMMIT` isolation level | ❌ Falla | No evita la preparación de statements |

### Solución Final (exitosa)

✅ **Bypass PgBouncer completamente para migraciones** usando conexión directa al puerto 5432.

---

## Comandos de Migración

### Crear Nueva Migración

```bash
# Alembic detecta automáticamente Supabase y cambia a puerto 5432
poetry run alembic revision --autogenerate -m "descripcion_migracion"
```

### Aplicar Migraciones

```bash
# Ejecuta todas las migraciones pendientes
poetry run alembic upgrade head

# Ejecuta una migración específica
poetry run alembic upgrade <revision_id>
```

### Verificar Estado Actual

```bash
# Ver la revisión actual de la BD
poetry run alembic current

# Ver historial de migraciones
poetry run alembic history

# Ver migraciones pendientes
poetry run alembic heads
```

### Rollback (downgrade)

```bash
# Revertir una migración
poetry run alembic downgrade -1

# Revertir a una revisión específica
poetry run alembic downgrade <revision_id>
```

### Sincronizar Estado (stamp)

Si la base de datos ya tiene el esquema aplicado manualmente pero Alembic no lo sabe:

```bash
# Marcar la BD como actualizada sin ejecutar migraciones
poetry run alembic stamp head
```

---

## Variables de Entorno

### `.env` / `.env.supabase`

```bash
# URL con Pooler (puerto 6543) - usado por el runtime
POSTGRES_URL=postgresql+asyncpg://postgres.xxx:PASSWORD@aws-1-us-east-1.pooler.supabase.com:6543/postgres

# URL con Conexión Directa (puerto 5432) - opcional, Alembic la genera automáticamente
# ALEMBIC_DB_URL=postgresql+asyncpg://postgres.xxx:PASSWORD@aws-1-us-east-1.pooler.supabase.com:5432/postgres

# Forzar desactivación de cache (útil en tests)
DISABLE_STATEMENT_CACHE=false
```

### Prioridad de URLs en Alembic

1. `ALEMBIC_DB_URL` (si está definida)
2. `POSTGRES_URL` (automáticamente modificada de 6543→5432 si es Supabase)
3. `settings.postgres_url` (del módulo de configuración)
4. Fallback: `sqlite:///./agente_hotel.db`

---

## Debugging y Troubleshooting

### Verificar Conectividad Directa (Puerto 5432)

```python
# test_connection.py
import asyncio
import asyncpg

async def main():
    url = "postgresql://postgres.xxx:PASSWORD@aws-1-us-east-1.pooler.supabase.com:5432/postgres"
    
    # Conectar con statement_cache_size=0 (buena práctica)
    conn = await asyncpg.connect(url, statement_cache_size=0)
    print("✓ Connection successful!")
    
    # Test query
    version = await conn.fetchval("SELECT version()")
    print(f"✓ Database version: {version[:100]}")
    
    # Test prepared statement (debe funcionar)
    stmt = await conn.prepare("SELECT 1")
    result = await stmt.fetchval()
    print(f"✓ Prepared statement result: {result}")
    
    await conn.close()

asyncio.run(main())
```

### Errores Comunes

#### 1. `relation "alembic_version" does not exist`

**Causa**: Primera ejecución de Alembic, tabla de control no inicializada.

**Solución**:
```bash
# Marcar la BD como actualizada sin ejecutar migraciones
poetry run alembic stamp head
```

#### 2. `Target database is not up to date`

**Causa**: Hay cambios no aplicados en el esquema o múltiples heads de migración.

**Solución**:
```bash
# Ver el estado actual
poetry run alembic current

# Ver heads disponibles
poetry run alembic heads

# Aplicar migraciones pendientes
poetry run alembic upgrade head
```

#### 3. `DuplicatePreparedStatementError` aún persiste

**Causa**: La URL sigue apuntando al puerto 6543.

**Verificación**:
```bash
# Ver logs de Alembic (debe mostrar cambio a puerto 5432)
poetry run alembic revision --autogenerate -m "test"
# Salida esperada: "DEBUG: Switching to Direct Connection (Port 5432) for migrations..."
```

**Solución**:
- Verificar que `alembic/env.py` tiene el código de cambio de puerto
- Forzar URL directa: `export ALEMBIC_DB_URL="postgresql+asyncpg://...5432/postgres"`

---

## Modelos y Metadata

### Importación de Modelos en `alembic/env.py`

**Crítico**: Todos los modelos deben importarse para que Alembic detecte cambios correctamente.

```python
# Import target metadata from app models (after sys.path patch)
from app.models.lock_audit import Base as LockAuditBase  # type: ignore  # noqa: E402
from app.models.tenant import Tenant  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.dlq import DLQEntry  # noqa: F401

target_metadata = LockAuditBase.metadata
```

**Por qué es importante**:
- Si un modelo no se importa, Alembic intentará **eliminar** su tabla durante la comparación
- Alembic compara `target_metadata` (código) vs esquema de BD

### Base Declarative Única

**Problema común**: Múltiples instancias de `Base = declarative_base()` en diferentes archivos.

**Solución**: Una sola `Base` compartida por todos los modelos.

```python
# ✅ Correcto (app/models/lock_audit.py)
from sqlalchemy.orm import declarative_base
Base = declarative_base()

# ✅ Correcto (otros modelos)
from app.models.lock_audit import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    # ...
```

---

## Mejores Prácticas

### 1. Migraciones

- ✅ **Siempre revisar** el archivo de migración generado antes de aplicarlo
- ✅ **Test en desarrollo** antes de aplicar en staging/producción
- ✅ **Backups** antes de ejecutar migraciones destructivas
- ✅ **Downgrade functions** completos para rollback seguro

### 2. Conexiones

- ✅ Usar **puerto 5432** (Directo) para: Migraciones, tareas admin, análisis manual
- ✅ Usar **puerto 6543** (Pooler) para: Runtime API, operaciones normales
- ✅ **NullPool** siempre con Supabase (tanto 5432 como 6543)
- ✅ **SSL obligatorio** (`ssl="require"`) para conexiones a Supabase

### 3. Multi-Tenancy

- ✅ Añadir `tenant_id` a todas las tablas que almacenan datos específicos de tenant
- ✅ Indexar `tenant_id` para performance
- ✅ Considerar `tenant_id` en constraints de unicidad (ej: `UNIQUE(tenant_id, identifier)`)

---

## Referencias

### Documentación Oficial

- [Supabase Connection Pooling](https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooling)
- [PgBouncer Documentation](https://www.pgbouncer.org/config.html)
- [asyncpg Issue #527 - PgBouncer Compatibility](https://github.com/MagicStack/asyncpg/issues/527)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

### Commits Relacionados

- `feat(db): Configurar Alembic para Supabase con PgBouncer` - Commit inicial con solución completa

---

## Próximos Pasos

### Tareas Pendientes

1. **Aplicar Migración**: `poetry run alembic upgrade head`
2. **Validar Esquema**: Verificar que todas las tablas tienen `tenant_id` donde corresponde
3. **Tests de Integración**: Crear tests que validen multi-tenancy
4. **Monitoring**: Añadir métricas para rastrear errores de migración

### Mejoras Futuras

- [ ] Script automatizado para cambio de puerto en `POSTGRES_URL`
- [ ] Health check que valide conectividad a ambos puertos (5432 y 6543)
- [ ] Dashboard Grafana con métricas de migraciones (duración, errores)
- [ ] Rollback automático en caso de fallo de migración

---

**Última Actualización**: 2025-11-24  
**Autor**: Backend Team  
**Estado**: ✅ Producción-Ready
