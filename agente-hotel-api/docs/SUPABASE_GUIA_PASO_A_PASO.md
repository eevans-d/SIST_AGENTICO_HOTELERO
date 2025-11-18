# 🛠️ SUPABASE – GUÍA PASO A PASO DEFINITIVA

**Proyecto**: SIST_AGENTICO_HOTELERO  
**Rol esperado del lector**: Tú (operador único)  
**Objetivo**: Tener un único documento que puedas seguir, paso a paso, para:

1. Crear y configurar Supabase (PostgreSQL gestionado) para este proyecto.  
2. Crear y configurar Redis gestionado (Upstash).  
3. Crear el `.env.supabase` correcto.  
4. Ejecutar migraciones Alembic contra Supabase.  
5. Validar que todo funciona y saber cómo actuar si algo falla.

> IMPORTANTE: Todo lo que necesitas hacer respecto a Supabase está aquí. Si un paso no aparece en este documento, no es obligatorio para que el sistema funcione.

---

## MÓDULO 1 – PREPARAR LOS SERVICIOS (SUPABASE + REDIS)

### 1. Crear el proyecto Supabase

1. Abre el navegador e inicia sesión en: `https://supabase.com/dashboard`.
2. Haz clic en **"New project"**.
3. Completa los datos:
   - **Organization**: la que uses habitualmente (por ejemplo, tu usuario personal).
   - **Name**: `agente-hotelero-staging` (para entorno de staging).  
   - **Database Password**: genera una contraseña larga y segura (mínimo 32 caracteres).  
   - **Region**: `South America (São Paulo)` (para menor latencia).  
   - **Pricing Plan**: **Pro** (no Free). Esto te da:
     - Backups automáticos.  
     - Point-in-time recovery (PITR).  
     - Límites razonables para producción pequeña.
4. Espera a que el proyecto termine de crearse (puede tardar 1–3 minutos).

#### 1.1. Datos que DEBES guardar

En el panel de Supabase del proyecto recién creado, anota y guarda en tu gestor de contraseñas (Bitwarden, 1Password, etc.):

- `PROJECT_REF`: aparece en la URL del proyecto, algo como `abcd1234`.  
- `DB_PASSWORD`: la contraseña que definiste.  
- `ANON_KEY`: se obtiene desde **Project Settings → API → anon public**.  
- `SERVICE_ROLE_KEY`: desde **Project Settings → API → service_role**.  
- `CONNECTION_STRING` (opcional, pero útil):
  - Ve a **Project Settings → Database → Connection info**.  
  - Localiza una cadena tipo `postgresql://postgres:[DB_PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres`.

Estos valores los usarás para construir `POSTGRES_URL` en `.env.supabase`.

---

### 2. Crear la base de datos Redis en Upstash

1. Ve a `https://upstash.com/` y regístrate (puedes usar GitHub).  
2. Dentro del dashboard, haz clic en **"Create Database"**.
3. Configura la base de datos:
   - **Name**: `agente-hotelero-redis`.  
   - **Region**: `South America (São Paulo)` (igual que Supabase).  
   - **Type**: `Regional` (más barato que Global y suficiente para este proyecto).  
   - **Eviction Policy**: `allkeys-lru`.
4. Crea la base de datos.

#### 2.1. Obtener la URL de Redis

Dentro del detalle de la base de datos en Upstash:

1. Ve a la sección **"Redis Connect"**.  
2. Copia la URL **TLS** (importante que sea `rediss://`, con doble `s`):

Ejemplo de formato:

```text
rediss://default:SUPER_SECRETO@sa-east-1-xxx-yyy.upstash.io:6379
```

Guarda esta URL en tu gestor de contraseñas como `REDIS_URL`.

---

### 3. Crear el archivo `.env.supabase`

Ahora vas a crear el archivo de entorno específico que usará la app cuando quieras trabajar contra Supabase.

#### 3.1. Crear el archivo

En tu terminal (WSL):

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

nano .env.supabase
```

Dentro de `nano`, pega este contenido base y **luego edita los placeholders**.

```bash
# ============================================================================
# SUPABASE STAGING - Variables de Entorno
# ============================================================================

# Environment
ENVIRONMENT=staging
DEBUG=false
USE_SUPABASE=true

# Database (Supabase PostgreSQL 15)
# IMPORTANTE: reemplaza [REF] y [DB_PASSWORD] con tus valores reales
POSTGRES_URL=postgresql+asyncpg://postgres.[REF]:[DB_PASSWORD]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
DATABASE_URL=${POSTGRES_URL}

# Alembic (para migraciones)
ALEMBIC_DB_URL=${POSTGRES_URL}

# Redis (Upstash)
# IMPORTANTE: pega la URL completa que copiaste de Upstash (rediss://...)
REDIS_URL=rediss://default:[REDIS_PASSWORD]@sa-east-1-xxxxx.upstash.io:6379

# Pool de conexiones (auto-ajustado por settings.py, no tocar)
# POSTGRES_POOL_SIZE, POSTGRES_MAX_OVERFLOW se ajustan automáticamente con USE_SUPABASE=true

# PMS (Mock para staging inicial)
PMS_TYPE=mock
PMS_BASE_URL=http://localhost:8080

# Observabilidad (local - sin cambios)
PROMETHEUS_URL=http://localhost:9090
GRAFANA_ADMIN_PASSWORD=cambia_esto

# Tracing (local Jaeger)
OTLP_ENDPOINT=http://jaeger:4317
TRACE_SAMPLING_RATE=0.1  # 10% en staging

# Secrets (cambiar todos por valores reales y seguros)
SECRET_KEY=cambia_esto_por_un_token_largo
WHATSAPP_ACCESS_TOKEN=cambia_esto
WHATSAPP_VERIFY_TOKEN=cambia_esto
GMAIL_APP_PASSWORD=cambia_esto
PMS_API_KEY=cambia_esto_si_usas_PMS_real

# Multi-tenancy
TENANCY_DYNAMIC_ENABLED=true
```

Guarda con `Ctrl+O`, Enter, y sal con `Ctrl+X`.

#### 3.2. Qué debes reemplazar EXACTAMENTE

En el archivo `.env.supabase`, reemplaza:

- `[REF]` → por tu `PROJECT_REF` de Supabase, por ejemplo `abcd1234`.
- `[DB_PASSWORD]` → por la contraseña que definiste al crear el proyecto.  
- `rediss://default:[REDIS_PASSWORD]@sa-east-1-xxxxx.upstash.io:6379` → pega la URL **completa** que copiaste de Upstash (no dejes `[REDIS_PASSWORD]` literal).
- `cambia_esto...` → cámbialos por valores reales y seguros.

> **CRÍTICO**: Si dejas contraseñas dummy, el sistema puede negarse a arrancar en ciertos modos (validadores de seguridad) o será inseguro.

**Para generar secretos seguros**, ejecuta:

```bash
# SECRET_KEY (32 bytes)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Cualquier otro token
openssl rand -hex 32
```

#### 3.3. Validar que el archivo existe y se puede leer

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

ls .env.supabase

# Ver un resumen (sin mostrar secretos completos)
head -n 20 .env.supabase
```

Si `ls` muestra `.env.supabase`, el archivo existe. Si te da `No such file or directory`, repite el paso 3.1.

---

## MÓDULO 2 – MIGRAR Y VALIDAR BASE DE DATOS EN SUPABASE

> A partir de aquí, asumimos que ya tienes:
> - Proyecto Supabase creado.  
> - Redis Upstash creado.  
> - `.env.supabase` creado y con placeholders reemplazados.

### 4. Validar conexión contra Supabase

Usarás el target `supabase-validate` que ya está en el `Makefile`.

En la terminal:

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

make supabase-validate
```

¿Qué hace internamente?

1. Comprueba que `.env.supabase` existe.  
2. Exporta sus variables de entorno.  
3. Ejecuta `psql "$POSTGRES_URL" -c "SELECT version();"`.

Resultados posibles:

- ✅ **Conexión OK**: verás algo como `PostgreSQL 15.x ...` y luego `✅ Supabase connection OK`.  
- ❌ **Fallo de conexión**: verás el mensaje `Connection failed. Check POSTGRES_URL in .env.supabase`.

Si falla:

1. Verifica que `POSTGRES_URL` está bien formado (sin espacios, sin caracteres raros).  
2. Confirma que `PROJECT_REF` y `DB_PASSWORD` son correctos.  
3. Asegúrate de que no tienes cortafuegos o VPN bloqueando el puerto 6543.
4. Si usas WSL, verifica que `psql` está instalado: `sudo apt install postgresql-client`

---

### 5. Habilitar Extensiones PostgreSQL en Supabase

**IMPORTANTE**: Estas extensiones son críticas para el funcionamiento del sistema. Supabase Pro las soporta todas.

Ve al **SQL Editor** de Supabase (Dashboard → SQL Editor) y ejecuta:

```sql
-- Extensiones requeridas
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;  -- Métricas de queries
CREATE EXTENSION IF NOT EXISTS pgcrypto;            -- Funciones de criptografía
CREATE EXTENSION IF NOT EXISTS pg_trgm;             -- Búsqueda full-text
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";         -- Generación de UUIDs

-- Verificar que se instalaron correctamente
SELECT extname, extversion 
FROM pg_extension 
WHERE extname IN ('pg_stat_statements', 'pgcrypto', 'pg_trgm', 'uuid-ossp');
```

**Salida esperada**:
```
        extname        | extversion 
-----------------------+------------
 pg_stat_statements    | 1.10
 pgcrypto              | 1.3
 pg_trgm               | 1.6
 uuid-ossp             | 1.1
```

Si alguna extensión falla al crear, contacta al soporte de Supabase (raro en Plan Pro).

---

### 6. Ejecutar migraciones Alembic en Supabase

Si `make supabase-validate` fue exitoso:

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

make supabase-migrate
```

Esto hace:

1. Exporta variables de `.env.supabase`.  
2. Ejecuta `poetry run alembic upgrade head` contra Supabase.

Salida esperada (simplificada):

```text
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial, initial schema
INFO  [alembic.runtime.migration] Running upgrade 0001_initial -> 0002_add_tenants, multi-tenancy
INFO  [alembic.runtime.migration] Running upgrade 0002_add_tenants -> 0003_add_lock_audit, lock audit
INFO  [alembic.runtime.migration] Running upgrade 0003_add_lock_audit -> 0004_add_dlq, dead letter queue
✅ Migrations completed
```

Si ves errores de Alembic:

- Copia el mensaje y no sigas con pasos posteriores.  
- Usualmente serán por:
  - URL mal definida.  
  - Problemas de permisos en Supabase (raro con Pro).  
  - Migraciones ya aplicadas manualmente (caso avanzado).

---

### 6. Ejecutar migraciones Alembic en Supabase

Si `make supabase-validate` fue exitoso:

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

make supabase-migrate
```

Esto hace:

1. Exporta variables de `.env.supabase`.  
2. Ejecuta `poetry run alembic upgrade head` contra Supabase.

Salida esperada (simplificada):

```text
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial, initial schema
INFO  [alembic.runtime.migration] Running upgrade 0001_initial -> 0002_add_tenants, multi-tenancy
INFO  [alembic.runtime.migration] Running upgrade 0002_add_tenants -> 0003_add_lock_audit, lock audit
INFO  [alembic.runtime.migration] Running upgrade 0003_add_lock_audit -> 0004_add_dlq, dead letter queue
✅ Migrations completed
```

**Posibles Errores**:

- **`connection refused`**: Verifica `POSTGRES_URL` y que no tengas firewall bloqueando.
- **`relation already exists`**: Las tablas ya fueron creadas manualmente. Solución:
  ```bash
  # Opción 1: Stamp current version sin ejecutar migraciones
  export $(cat .env.supabase | grep -v '^#' | xargs)
  poetry run alembic stamp head
  
  # Opción 2: Rollback y re-ejecutar
  poetry run alembic downgrade base
  poetry run alembic upgrade head
  ```
- **`permission denied`**: Verifica que el usuario de Supabase tiene permisos CREATE. En Plan Pro esto no debería ocurrir.

---

### 7. Crear Índices de Performance

**CRÍTICO**: Sin estos índices, el sistema será lento en producción. Ejecuta en **SQL Editor de Supabase**:

```sql
-- ============================================================================
-- ÍNDICES OPTIMIZADOS PARA SUPABASE
-- ============================================================================

-- Tenant resolution (usado en CADA request multi-tenant)
CREATE INDEX IF NOT EXISTS idx_tenant_user_identifiers_identifier 
  ON tenant_user_identifiers(identifier);

CREATE INDEX IF NOT EXISTS idx_tenant_user_identifiers_tenant_id 
  ON tenant_user_identifiers(tenant_id);

-- Tenant status (filtro común en queries)
CREATE INDEX IF NOT EXISTS idx_tenants_status 
  ON tenants(status) WHERE status = 'active';

-- Lock service (crítico para concurrencia)
CREATE INDEX IF NOT EXISTS idx_lock_audit_resource_id 
  ON lock_audit(resource_id);

CREATE INDEX IF NOT EXISTS idx_lock_audit_acquired_at 
  ON lock_audit(acquired_at DESC);

-- DLQ (dead letter queue)
CREATE INDEX IF NOT EXISTS idx_dlq_permanent_failures_channel 
  ON dlq_permanent_failures(channel);

CREATE INDEX IF NOT EXISTS idx_dlq_permanent_failures_created_at 
  ON dlq_permanent_failures(created_at DESC);

-- Users (filtro por tenant + activos)
CREATE INDEX IF NOT EXISTS idx_users_tenant_id 
  ON users(tenant_id) WHERE is_active = true;

-- Verificar índices creados
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('tenants', 'tenant_user_identifiers', 'users', 'lock_audit', 'dlq_permanent_failures')
ORDER BY tablename, indexname;
```

**Salida esperada**: Deberías ver al menos 8 índices creados (más los automáticos de PKs/UKs).

---

### 8. Poblar Datos Iniciales (Seed)

**Opción A - SQL Manual** (para staging/producción simple):

```sql
-- Crear tenant por defecto
INSERT INTO tenants (tenant_id, name, status, created_at, updated_at)
VALUES ('default', 'Default Tenant', 'active', NOW(), NOW())
ON CONFLICT (tenant_id) DO NOTHING;

-- Verificar
SELECT id, tenant_id, name, status FROM tenants;
```

**Opción B - Script Python** (para datos complejos):

```bash
# Crear script temporal
cat > /tmp/seed_supabase.py << 'EOFPYTHON'
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime, UTC

async def seed():
    # Leer POSTGRES_URL desde .env.supabase
    with open('.env.supabase') as f:
        for line in f:
            if line.startswith('POSTGRES_URL='):
                db_url = line.split('=', 1)[1].strip()
                break
    
    engine = create_async_engine(db_url, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Insertar tenant default
        await session.execute("""
            INSERT INTO tenants (tenant_id, name, status, created_at, updated_at)
            VALUES ('default', 'Default Tenant', 'active', :now, :now)
            ON CONFLICT (tenant_id) DO NOTHING
        """, {"now": datetime.now(UTC)})
        
        await session.commit()
        print("✅ Tenant default creado")

asyncio.run(seed())
EOFPYTHON

# Ejecutar
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api
export $(cat .env.supabase | grep -v '^#' | xargs)
python /tmp/seed_supabase.py
```

---

### 9. Quick check de tablas y extensiones

Para verificar que las tablas y extensiones existen:

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

make supabase-quick-check
```

Esto ejecuta:

1. `\dt` para listar tablas.  
2. Un `SELECT` sobre `pg_extension` para comprobar extensiones.

---

### 9. Quick check de tablas y extensiones

Para verificar que todo está correcto:

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

make supabase-quick-check
```

Esto ejecuta:

1. `\dt` para listar tablas.  
2. Un `SELECT` sobre `pg_extension` para comprobar extensiones.

Qué deberías ver:

**Tablas críticas**:
```
           List of relations
 Schema |          Name              | Type  |  Owner   
--------+----------------------------+-------+----------
 public | alembic_version            | table | postgres
 public | dlq_permanent_failures     | table | postgres
 public | lock_audit                 | table | postgres
 public | tenant_user_identifiers    | table | postgres
 public | tenants                    | table | postgres
 public | users                      | table | postgres
```

**Extensiones presentes**:
```
        extname        
-----------------------
 pg_stat_statements
 pgcrypto
 pg_trgm
 uuid-ossp
```

Si falta alguna tabla, repite `make supabase-migrate`.  
Si falta alguna extensión, ejecuta el SQL del **Paso 5** manualmente en SQL Editor.

---

### 10. Validar Pool de Conexiones (Ajuste Automático)

El sistema detecta automáticamente si estás usando Supabase y ajusta los límites del pool.

**Verificar en logs al arrancar la app**:

```bash
# Arrancar app con .env.supabase
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api
export $(cat .env.supabase | grep -v '^#' | xargs)
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8002
```

**Buscar en logs** (primeras 10 líneas):

```text
INFO     [app.core.database] Supabase detected: adjusting pool to 2/2 (from default 10/10)
INFO     [app.core.database] PostgreSQL connection pool initialized
```

Si **NO ves** el mensaje "Supabase detected", verifica que:
1. `USE_SUPABASE=true` está en `.env.supabase`.
2. `POSTGRES_URL` contiene `supabase.co` en la URL.

---

### 11. Troubleshooting Común

#### Error: `connection refused` al ejecutar `make supabase-validate`

**Causa**: Firewall, VPN, o URL incorrecta.

**Solución**:
```bash
# 1. Verificar que puedes hacer ping al host
ping aws-0-sa-east-1.pooler.supabase.com

# 2. Verificar que el puerto 6543 está abierto (pooler port)
nc -zv aws-0-sa-east-1.pooler.supabase.com 6543

# 3. Verificar variables exportadas correctamente
export $(cat .env.supabase | grep -v '^#' | xargs)
echo $POSTGRES_URL
# Debe mostrar: postgresql+asyncpg://postgres.[REF]:...@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
```

#### Error: `permission denied for schema public`

**Causa**: Usuario de Supabase no tiene permisos CREATE en schema public (raro en Plan Pro).

**Solución**:
```sql
-- Ejecutar en SQL Editor de Supabase como superuser
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres;
```

#### Error: `idle_in_transaction_session_timeout` o `statement_timeout`

**Causa**: Queries muy lentas excediendo timeouts configurados (15s statement, 10s idle).

**Solución**:
1. Revisar logs de Supabase Dashboard → Logs → Database.
2. Identificar query lenta con `pg_stat_statements`:
   ```sql
   SELECT query, mean_exec_time, calls 
   FROM pg_stat_statements 
   ORDER BY mean_exec_time DESC 
   LIMIT 10;
   ```
3. Optimizar query o añadir índice específico.

#### Error: `too many connections`

**Causa**: Pool mal configurado o muchas instancias de la app.

**Solución**:
```bash
# Verificar pool actual
export $(cat .env.supabase | grep -v '^#' | xargs)
psql "$POSTGRES_URL" -c "SELECT count(*) FROM pg_stat_activity WHERE usename = 'postgres';"

# Si >10 conexiones activas, reduce pool:
# En .env.supabase, el pool debería auto-ajustarse a 2/2
# Si no lo hace, fuerza manualmente:
nano .env.supabase
# Añadir (o descomentar):
# POSTGRES_POOL_SIZE=2
# POSTGRES_MAX_OVERFLOW=2
```

#### Error: `RedisError: connection refused` (Upstash)

**Causa**: URL de Redis incorrecta o TLS requerido pero no usado.

**Solución**:
```bash
# 1. Verificar que la URL comienza con rediss:// (doble s = TLS)
echo $REDIS_URL
# Debe ser: rediss://default:[PASSWORD]@sa-east-1-xxxxx.upstash.io:6379

# 2. Test de conexión manual con redis-cli
redis-cli -u "$REDIS_URL" PING
# Debe responder: PONG

# Si falla, regenera la URL desde Upstash Dashboard
```

---

## MÓDULO 3 – VALIDACIÓN POST-MIGRACIÓN Y COSTOS

### 12. Ejecutar Suite de Tests contra Supabase

**IMPORTANTE**: Estos tests validan que el sistema funciona correctamente con Supabase.

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

# Cargar .env.supabase
export $(cat .env.supabase | grep -v '^#' | xargs)

# Tests unitarios (sin deps externas)
make test-unit

# Tests de integración (requieren DB + Redis)
make test-integration
```

**Salida esperada**:
```
tests/unit/test_session_manager.py::test_session_creation PASSED
tests/integration/test_pms_integration.py::test_availability_check PASSED
...
======= X passed, Y warnings in Z.ZZs =======
```

Si fallan tests de integración:
1. Verifica que `POSTGRES_URL` y `REDIS_URL` son correctos.
2. Asegúrate de que Supabase y Upstash están accesibles desde tu IP.
3. Revisa logs con `--verbose` para ver el error exacto.

---

### 13. Monitorear Uso de Recursos en Supabase

**Dashboard de Supabase**:
1. Ve a tu proyecto → **Reports** → **Database**.
2. Verás:
   - **Database Size**: Espacio usado (incluido en Plan Pro hasta 8GB).
   - **Active Connections**: Número de conexiones activas (límite 100 en Pro).
   - **Egress**: Tráfico de salida (incluido 50GB/mes en Pro, luego $0.09/GB).

**Alertas Recomendadas**:
- Si **Database Size** > 7GB → planificar limpieza o upgrade.
- Si **Active Connections** > 80 → revisar pool o escalar plan.
- Si **Egress** > 45GB/mes → posible uso ineficiente (revisar caching).

**Costos Estimados**:

| Concepto | Plan Pro | Notas |
|----------|----------|-------|
| **Supabase Base** | $25/mes | Incluye 8GB DB, 100 conexiones, 50GB egress |
| **Upstash Redis** | $0-10/mes | Plan free hasta 10K commands/day, luego $0.20/100K |
| **Total Estimado** | **$25-35/mes** | Para staging pequeño/mediano |

Para producción con tráfico alto:
- Supabase Pro + adicionales: ~$40-60/mes
- Upstash Regional: ~$10-20/mes
- **Total**: **$50-80/mes**

---

### 14. Rollback Plan (Si Algo Sale Mal)

Si después de migrar a Supabase tienes problemas críticos, puedes volver a la DB local:

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

# 1. Detener app
# (Ctrl+C si está corriendo)

# 2. Volver a usar .env normal (local)
cp .env.example .env  # O usar tu .env previo

# 3. Arrancar contenedores locales
make docker-up

# 4. Verificar salud
make health

# 5. Ejecutar migraciones locales (si es necesario)
poetry run alembic upgrade head

# 6. Re-arrancar app con .env local
poetry run uvicorn app.main:app --reload
```

**Backup de Supabase antes de cambios críticos**:
```bash
# Exportar dump completo
export $(cat .env.supabase | grep -v '^#' | xargs)
pg_dump "$POSTGRES_URL" > backup-supabase-$(date +%Y%m%d-%H%M%S).sql

# Restaurar si es necesario
psql "$POSTGRES_URL" < backup-supabase-YYYYMMDD-HHMMSS.sql
```

---

## MÓDULO 4 – OPCIONAL (RLS MULTI-TENANT AVANZADO)

### 15. Row Level Security (RLS) - Solo si Multi-Tenant en Producción

**¿Cuándo habilitar RLS?**
- Si tienes **múltiples tenants** en producción que comparten la misma base de datos.
- Si necesitas **aislamiento a nivel de fila** garantizado por PostgreSQL (además del middleware).

**¿Cuándo NO es necesario?**
- Si usas **un solo tenant** (default).
- Si el middleware de tenant resolution es suficiente (la app filtra correctamente).

**Habilitar RLS** (en SQL Editor de Supabase):

```sql
-- 1. Activar RLS en tablas sensibles
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_user_identifiers ENABLE ROW LEVEL SECURITY;

-- 2. Crear política por defecto (usa current_setting para tenant_id)
CREATE POLICY tenant_isolation_users ON users
  USING (tenant_id = current_setting('app.current_tenant_id', TRUE));

CREATE POLICY tenant_isolation_identifiers ON tenant_user_identifiers
  USING (tenant_id::text = current_setting('app.current_tenant_id', TRUE));

-- 3. Permitir a superuser (postgres) ver todo
CREATE POLICY bypass_rls_for_superuser ON users
  USING (current_user = 'postgres');

-- 4. Verificar políticas
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE tablename IN ('users', 'tenant_user_identifiers');
```

**Middleware SET LOCAL** (ya está preparado pero desactivado):

```python
# app/core/middleware.py
# Ya implementado pero comentado - descomentar para activar RLS

# En request processing:
if hasattr(request.state, "tenant_id") and request.state.tenant_id:
    await session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": request.state.tenant_id}
    )
```

**IMPORTANTE**: RLS añade overhead de CPU (~5-10%). Solo habilita si necesitas seguridad extra.

---

---

## CHECKLIST FINAL (SUPABASE)

Puedes marcar cada punto una vez completado.

### A. Servicios creados
- [ ] Proyecto Supabase `agente-hotelero-staging` creado (Plan Pro, región São Paulo).  
- [ ] Guardado `PROJECT_REF`, `DB_PASSWORD`, `ANON_KEY`, `SERVICE_ROLE_KEY` en gestor de secretos.  
- [ ] Base de datos Redis Upstash creada en `sa-east-1` con URL `rediss://...`.

### B. Configuración local
- [ ] `.env.supabase` creado en `agente-hotel-api/`.  
- [ ] `POSTGRES_URL` correcto (formato: `postgresql+asyncpg://postgres.[REF]:[PASS]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres`).  
- [ ] `REDIS_URL` pega la URL de Upstash completa (comienza con `rediss://`, doble s = TLS).  
- [ ] Secrets reales generados con `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
- [ ] `USE_SUPABASE=true` configurado para auto-ajuste de pool.

### C. Migraciones y Schema
- [ ] `make supabase-validate` → conexión OK (muestra versión PostgreSQL 15.x).  
- [ ] Extensiones PostgreSQL habilitadas: `pg_stat_statements`, `pgcrypto`, `pg_trgm`, `uuid-ossp`.
- [ ] `make supabase-migrate` → migraciones Alembic aplicadas sin errores.
- [ ] Índices de performance creados (8 índices mínimos en tablas críticas).
- [ ] Datos iniciales (seed) creados: tenant `default` existe en tabla `tenants`.

### D. Validación funcional
- [ ] `make supabase-quick-check` → tablas y extensiones visibles.
- [ ] Logs de app muestran "Supabase detected: adjusting pool to 2/2".
- [ ] `make test-unit` → tests unitarios pasan sin errores.
- [ ] `make test-integration` → tests de integración pasan (requiere Supabase + Redis accesibles).

### E. Monitoreo y Costos
- [ ] Dashboard de Supabase revisado: Database Size, Active Connections, Egress dentro de límites.
- [ ] Upstash Redis Dashboard: Commands/day dentro del plan free o pagado según uso.
- [ ] Backup inicial creado: `pg_dump "$POSTGRES_URL" > backup-supabase-$(date +%Y%m%d).sql`.

### F. Documentación y Rollback
- [ ] Plan de rollback documentado y probado (volver a DB local si es necesario).
- [ ] Credenciales guardadas en gestor de secretos (no en archivos de texto plano).
- [ ] Entiendes cómo monitorear costos y uso de recursos en Supabase/Upstash dashboards.

### G. Opcional (RLS Multi-Tenant)
- [ ] RLS habilitado en tablas `users`, `tenant_user_identifiers` (solo si multi-tenant en producción).
- [ ] Políticas RLS creadas y testeadas.
- [ ] Middleware SET LOCAL descomentado en `app/core/middleware.py` (si usas RLS).

---

## ANEXO: Comandos Útiles de Referencia Rápida

```bash
# ============================================================================
# CONEXIÓN Y VALIDACIÓN
# ============================================================================

# Cargar variables de .env.supabase
export $(cat .env.supabase | grep -v '^#' | xargs)

# Test de conexión PostgreSQL
psql "$POSTGRES_URL" -c "SELECT version();"

# Test de conexión Redis
redis-cli -u "$REDIS_URL" PING

# Listar tablas
psql "$POSTGRES_URL" -c "\dt"

# Listar extensiones
psql "$POSTGRES_URL" -c "SELECT extname, extversion FROM pg_extension;"

# Ver conexiones activas
psql "$POSTGRES_URL" -c "SELECT count(*) FROM pg_stat_activity WHERE usename = 'postgres';"

# ============================================================================
# MIGRACIONES
# ============================================================================

# Aplicar migraciones
make supabase-migrate

# Ver historial de migraciones
psql "$POSTGRES_URL" -c "SELECT version_num FROM alembic_version;"

# Rollback última migración (CUIDADO)
poetry run alembic downgrade -1

# Stamp sin ejecutar migraciones (si tablas ya existen)
poetry run alembic stamp head

# ============================================================================
# BACKUP Y RESTORE
# ============================================================================

# Crear backup completo
pg_dump "$POSTGRES_URL" > backup-$(date +%Y%m%d-%H%M%S).sql

# Crear backup solo de schema (sin datos)
pg_dump "$POSTGRES_URL" --schema-only > schema-backup.sql

# Crear backup solo de datos (sin schema)
pg_dump "$POSTGRES_URL" --data-only > data-backup.sql

# Restaurar backup completo
psql "$POSTGRES_URL" < backup-YYYYMMDD-HHMMSS.sql

# ============================================================================
# MONITOREO Y DEBUG
# ============================================================================

# Ver queries lentas (top 10)
psql "$POSTGRES_URL" -c "
  SELECT query, mean_exec_time, calls 
  FROM pg_stat_statements 
  ORDER BY mean_exec_time DESC 
  LIMIT 10;
"

# Ver tamaño de base de datos
psql "$POSTGRES_URL" -c "
  SELECT pg_size_pretty(pg_database_size('postgres')) AS db_size;
"

# Ver tamaño de tablas individuales
psql "$POSTGRES_URL" -c "
  SELECT 
    tablename, 
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
  FROM pg_tables 
  WHERE schemaname = 'public' 
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# Ver índices faltantes (sugerencias de PostgreSQL)
psql "$POSTGRES_URL" -c "
  SELECT schemaname, tablename, attname, n_distinct, correlation
  FROM pg_stats
  WHERE schemaname = 'public'
    AND n_distinct > 100
    AND correlation < 0.1;
"

# ============================================================================
# LIMPIEZA Y MANTENIMIENTO
# ============================================================================

# Limpiar registros viejos de lock_audit (ejemplo: >30 días)
psql "$POSTGRES_URL" -c "
  DELETE FROM lock_audit 
  WHERE acquired_at < NOW() - INTERVAL '30 days';
"

# Limpiar DLQ (dead letter queue) procesada
psql "$POSTGRES_URL" -c "
  DELETE FROM dlq_permanent_failures 
  WHERE created_at < NOW() - INTERVAL '90 days';
"

# Vacuum y análisis (optimización)
psql "$POSTGRES_URL" -c "VACUUM ANALYZE;"

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

# Verificar variables de entorno cargadas
env | grep -E 'POSTGRES|REDIS|SUPABASE'

# Test completo de stack (DB + Redis + App)
make health

# Ver logs de última ejecución de app
tail -f logs/app.log  # Si tienes logging a archivo

# Verificar que pool se ajusta automáticamente
poetry run uvicorn app.main:app --log-level debug | grep -i "pool"
# Debe mostrar: "Supabase detected: adjusting pool to 2/2"
```

---

## RESUMEN EJECUTIVO: ¿QUÉ LOGRASTE?

Al completar esta guía, ahora tienes:

✅ **Supabase Pro** configurado con PostgreSQL 15, región São Paulo, backups automáticos  
✅ **Redis Upstash** configurado con TLS, región São Paulo, eviction policy óptimo  
✅ **`.env.supabase`** con todas las variables necesarias, secretos seguros generados  
✅ **Extensiones PostgreSQL** habilitadas (pg_stat_statements, pgcrypto, pg_trgm, uuid-ossp)  
✅ **Migraciones Alembic** aplicadas correctamente, schema actualizado  
✅ **Índices de performance** creados para queries críticas (tenant resolution, locks, DLQ)  
✅ **Datos iniciales** (seed) configurados con tenant default  
✅ **Pool de conexiones** auto-ajustado a 2/2 para Supabase (ahorro de recursos)  
✅ **Tests validados** contra Supabase (unitarios + integración)  
✅ **Monitoreo configurado** (Dashboard Supabase + métricas de costos)  
✅ **Plan de rollback** documentado (volver a DB local si es necesario)  
✅ **Troubleshooting** común documentado con soluciones paso a paso  
✅ **Comandos de referencia** rápida para operaciones diarias  

**Próximos pasos sugeridos**:

1. **Staging → Producción**: Repetir proceso con `.env.production` (proyecto Supabase separado).
2. **CI/CD**: Añadir GitHub Actions para ejecutar migraciones automáticamente en deploy.
3. **Monitoreo Avanzado**: Configurar alertas en Supabase Dashboard (DB size, conexiones, egress).
4. **Backups Programados**: Configurar cron job para `pg_dump` diario (aunque Supabase Pro ya hace backups automáticos).
5. **RLS (opcional)**: Si escalas a multi-tenant real, habilitar Row Level Security según Módulo 4.

---

Con este documento tienes **todo** lo necesario para configurar, migrar, validar y operar Supabase en este proyecto de forma correcta y segura. Si en algún momento necesitas ampliar (RLS avanzado, multi-región, optimizaciones específicas, etc.), lo podemos documentar en una guía complementaria, pero esto cubre el **100%** de lo requerido para migrar y operar la base de datos en Supabase.

**Última actualización**: 2025-11-16  
**Mantenido por**: Backend AI Team (Copilot Agent)  
**Revisión sugerida**: Mensual o tras cambios arquitectónicos mayores
