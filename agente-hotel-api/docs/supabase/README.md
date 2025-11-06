# Supabase Setup Guide - Agente Hotel API

**Versión:** 1.0.0  
**Fecha:** 2025-11-06  
**Estado:** ✅ Validado contra modelos SQLAlchemy

---

## 📋 Tabla de Contenidos

1. [Arquitectura de Datos](#arquitectura-de-datos)
2. [Pre-requisitos](#pre-requisitos)
3. [Configuración Inicial](#configuración-inicial)
4. [Deployment del Schema](#deployment-del-schema)
5. [Configuración del Backend](#configuración-del-backend)
6. [Validación y Testing](#validación-y-testing)
7. [Troubleshooting](#troubleshooting)
8. [Preguntas Frecuentes](#preguntas-frecuentes)

---

## Arquitectura de Datos

### Separación de Responsabilidades

```
┌─────────────────────────────────────────────────────────────────┐
│ SUPABASE POSTGRES (Persistent State)                           │
├─────────────────────────────────────────────────────────────────┤
│ ✅ users                  → Autenticación JWT, profiles         │
│ ✅ user_sessions          → Tracking de tokens activos          │
│ ✅ password_history       → Prevención de password reuse        │
│ ✅ tenants                → Configuración multi-tenant          │
│ ✅ tenant_user_identifiers → Mapeo phone/email → tenant         │
│ ✅ lock_audit             → Auditoría de locks distribuidos     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ REDIS (Ephemeral/Cache Layer)                                  │
├─────────────────────────────────────────────────────────────────┤
│ ✅ session:{tenant}:{user} → Conversation state (TTL 30min)     │
│ ✅ feature_flags hash     → Runtime feature toggles             │
│ ✅ rate limiting counters → slowapi backend storage             │
│ ✅ distributed locks      → Reservation atomicity               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ QLOAPPS PMS (Hotel Domain - External System)                   │
├─────────────────────────────────────────────────────────────────┤
│ ✅ hotels, rooms          → Inventario hotelero                 │
│ ✅ reservations, bookings → Reservas y check-in/out             │
│ ✅ pricing, availability  → Tarifas y disponibilidad            │
│ ✅ guests, invoices       → Datos de huéspedes y facturación    │
└─────────────────────────────────────────────────────────────────┘
```

### ⚠️ IMPORTANTE: Qué NO va en Supabase

❌ **NO crear tablas del dominio hotelero** (rooms, reservations, pricing)  
→ Estas ya existen en QloApps PMS y se acceden vía API REST

❌ **NO crear tabla `sessions`** para conversation state  
→ SessionManager usa Redis con TTL de 30 minutos (ver `app/services/session_manager.py`)

❌ **NO crear tabla `feature_flags`**  
→ FeatureFlagService usa Redis hash (ver `app/services/feature_flag_service.py`)

---

## Pre-requisitos

### 1. Cuenta de Supabase

- ✅ Proyecto creado en [supabase.com](https://supabase.com)
- ✅ Plan Free (suficiente para desarrollo/staging) o Pro (producción)
- ✅ Región seleccionada (preferible: `us-east-1` o más cercana a tu infraestructura)

### 2. Herramientas Locales

```bash
# PostgreSQL client (para testing local)
sudo apt-get install postgresql-client  # Ubuntu/Debian
brew install postgresql                 # macOS

# Python 3.12+ con Poetry instalado
python --version  # debe ser >= 3.12.3
poetry --version
```

### 3. Variables de Entorno Base

Archivo `.env.example` como referencia:

```bash
# Backend API
ENVIRONMENT=development
DEBUG=true

# PostgreSQL (será reemplazado por Supabase)
POSTGRES_URL=postgresql+asyncpg://localhost:5432/postgres
POSTGRES_POOL_SIZE=10
POSTGRES_MAX_OVERFLOW=10

# Redis (mantener)
REDIS_URL=redis://localhost:6379/0

# PMS Integration
PMS_TYPE=mock  # o qloapps en staging/prod
```

---

## Configuración Inicial

### Paso 1: Obtener Credenciales de Supabase

1. Ir a tu proyecto en [app.supabase.com](https://app.supabase.com)
2. Navegar a: **Project Settings → Database**
3. Sección **Connection String**:
   - Seleccionar **"Connection pooling"** (modo Transaction)
   - Copiar el string completo

**Formato esperado:**
```
postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

**Componentes importantes:**
- `postgres.[PROJECT-REF]`: Username con project reference
- `[PASSWORD]`: Password del proyecto (almacenar de forma segura)
- `aws-0-us-east-1.pooler.supabase.com`: Pooler endpoint (varía por región)
- **Puerto 6543**: Connection pooler (NO usar 5432 directo)

### Paso 2: Agregar Parámetros SSL

⚠️ **CRÍTICO**: Agregar `?sslmode=require` al final del connection string:

```bash
postgresql://postgres.xxxxx:password@host.pooler.supabase.com:6543/postgres?sslmode=require
```

**Por qué SSL es obligatorio:**
- Supabase requiere conexiones encriptadas en todos los planes
- Sin `sslmode=require`, la conexión fallará con error de SSL
- El backend usa `asyncpg` que soporta SSL nativamente

---

## Deployment del Schema

### Método 1: Supabase SQL Editor (Recomendado)

1. Abrir el archivo `schema.sql` en este directorio
2. Ir a: **Supabase Dashboard → SQL Editor → New Query**
3. Copiar y pegar **todo el contenido** de `schema.sql`
4. Click en **Run** (o `Ctrl+Enter`)
5. Verificar que no haya errores en el panel de resultados

**Validación:**
```sql
-- Debe retornar 6 tablas
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

Resultado esperado:
```
lock_audit
password_history
tenant_user_identifiers
tenants
user_sessions
users
```

### Método 2: psql CLI (Alternativo)

```bash
# Descargar el schema
cd agente-hotel-api/docs/supabase

# Ejecutar contra Supabase (reemplazar con tu connection string)
psql "postgresql://postgres.xxxxx:pass@host.pooler.supabase.com:6543/postgres?sslmode=require" \
  -f schema.sql

# Validar
psql "..." -c "\dt"  # Listar tablas
```

### Método 3: Supabase CLI (Avanzado)

```bash
# Instalar Supabase CLI
npm install -g supabase

# Login
supabase login

# Link to project
supabase link --project-ref your-project-ref

# Deploy migrations (si usas Alembic/migrations)
supabase db push
```

---

## Configuración del Backend

### Paso 1: Actualizar Variables de Entorno

Editar `.env` en `agente-hotel-api/`:

```bash
# Reemplazar POSTGRES_URL con Supabase connection string
DATABASE_URL=postgresql://postgres.xxxxx:password@host.pooler.supabase.com:6543/postgres?sslmode=require

# O usar componentes separados (el settings.py construirá la URL):
POSTGRES_HOST=aws-0-us-east-1.pooler.supabase.com
POSTGRES_PORT=6543
POSTGRES_DB=postgres
POSTGRES_USER=postgres.xxxxxxxxxxxxx
POSTGRES_PASSWORD=your-secure-password
POSTGRES_POOL_SIZE=10
POSTGRES_MAX_OVERFLOW=10
```

### Paso 2: Verificar Auto-conversión de Driver

El `app/core/settings.py` automáticamente convierte el esquema:

```python
# Input (Supabase format):
postgresql://postgres.xxxxx:pass@host:6543/postgres?sslmode=require

# Output (asyncpg driver):
postgresql+asyncpg://postgres.xxxxx:pass@host:6543/postgres?sslmode=require
```

**Validar localmente:**
```bash
cd agente-hotel-api
python -c "from app.core.settings import settings; print(settings.postgres_url)"
```

Debe mostrar: `postgresql+asyncpg://...`

### Paso 3: Probar Conexión

```bash
# Iniciar servicios (Docker Compose)
make docker-up

# Verificar health check
curl http://localhost:8002/health/ready | jq .

# Resultado esperado:
{
  "status": "healthy",
  "postgres": "ok",
  "redis": "ok",
  "timestamp": "2025-11-06T..."
}
```

Si `postgres: "error"`, revisar logs:
```bash
docker logs agente-api --tail 50
```

---

## Validación y Testing

### Test 1: Crear Tenant de Prueba

```bash
# Via API (requiere JWT token - ver docs de auth)
curl -X POST http://localhost:8002/api/admin/tenants \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "hotel-test",
    "name": "Hotel Test",
    "status": "active"
  }'
```

### Test 2: Verificar en Supabase Table Editor

1. Ir a: **Supabase Dashboard → Table Editor**
2. Seleccionar tabla `tenants`
3. Verificar que existe el registro `hotel-test`

### Test 3: Test de Session Manager

```bash
# Ejecutar tests de integración
cd agente-hotel-api
make test-integration

# O específicamente session_manager:
pytest tests/integration/test_session_manager.py -v
```

### Test 4: Multi-Tenancy Resolution

```python
# En un script de test o notebook:
from app.services.dynamic_tenant_service import DynamicTenantService
from app.core.database import AsyncSessionFactory

async def test_tenant_resolution():
    async with AsyncSessionFactory() as session:
        service = DynamicTenantService(session)
        
        # Crear identifier
        await service.add_identifier("hotel-test", "+5491112345678", "whatsapp")
        
        # Resolver tenant
        tenant = await service.resolve_tenant("+5491112345678", "whatsapp")
        print(f"Tenant resolved: {tenant}")  # Debe retornar "hotel-test"
```

---

## Troubleshooting

### Error: "connection refused" o "timeout"

**Causa:** Usando puerto 5432 (directo) en lugar de 6543 (pooler)

**Solución:**
```bash
# ❌ Incorrecto
postgresql://...@host.supabase.com:5432/postgres

# ✅ Correcto
postgresql://...@host.pooler.supabase.com:6543/postgres?sslmode=require
```

### Error: "SSL connection has been closed unexpectedly"

**Causa:** Falta parámetro `sslmode=require`

**Solución:**
```bash
# Agregar al final del connection string
?sslmode=require
```

### Error: "password authentication failed"

**Causas posibles:**
1. Password incorrecto → Verificar en Supabase Dashboard → Database Settings
2. Username sin project ref → Debe ser `postgres.xxxxxxxxxxxxx`
3. IP bloqueada → Verificar Supabase Dashboard → Authentication → Policies

**Solución:**
```bash
# Verificar formato completo:
postgresql://postgres.[PROJECT-REF]:[CORRECT-PASSWORD]@...
```

### Error: "relation 'users' does not exist"

**Causa:** Schema no ejecutado o ejecutado en schema incorrecto

**Solución:**
```sql
-- Verificar schema público
\dt public.*

-- Si tablas en otro schema, revisar search_path:
SHOW search_path;
SET search_path TO public;
```

### Error: "too many connections"

**Causa:** Pool size excede límite de Supabase Free tier (60 conexiones)

**Solución:**
```bash
# En .env, reducir pool size:
POSTGRES_POOL_SIZE=5
POSTGRES_MAX_OVERFLOW=5
```

### Warning: "Pydantic deprecation warnings"

**Causa:** Uso de `@validator` de Pydantic v1 en vez de v2

**Solución:**
Ya completado en archivos principales (`nlp.py`, `webhook_schemas.py`). Si aparecen en otros archivos:
```python
# ❌ Pydantic v1
from pydantic import validator
@validator("field")

# ✅ Pydantic v2
from pydantic import field_validator
@field_validator("field")
```

---

## Preguntas Frecuentes

### ¿Por qué NO usar Supabase Auth?

**Respuesta:** El sistema usa **autenticación JWT custom** implementada en `app/core/security.py`:
- Tokens generados con `python-jose`
- Validación en middleware FastAPI
- Mayor control sobre claims y permisos
- Integración con multi-tenancy existente

Supabase Auth está diseñado para apps con frontend directo; nuestro caso es API backend-only.

### ¿Necesito Row Level Security (RLS)?

**Respuesta:** **NO**. RLS es útil cuando:
- Frontend accede directamente a Supabase
- Usuarios finales tienen credenciales de Supabase

En nuestro caso:
- ✅ Solo el backend accede a Supabase (service credentials)
- ✅ Validación de permisos en capa de aplicación (FastAPI dependencies)
- ✅ Multi-tenancy via `tenant_id` en queries SQL

### ¿Puedo usar Direct Connection (puerto 5432)?

**No recomendado en producción**. Razones:
- ❌ Sin connection pooling (límite de 60 conexiones concurrentes)
- ❌ Mayor latencia (sin PgBouncer intermediario)
- ❌ Sin protección contra connection exhaustion

✅ **Usar siempre Pooler (6543)** con modo Transaction.

### ¿Cómo migro datos de PostgreSQL local a Supabase?

**Opción 1: pg_dump/restore**
```bash
# Export desde local
pg_dump -h localhost -U postgres -d postgres --schema=public --data-only > data.sql

# Import a Supabase
psql "postgresql://postgres.xxxxx@host.pooler.supabase.com:6543/postgres?sslmode=require" < data.sql
```

**Opción 2: Script de migración Python**
```python
# Ver scripts/migrate_to_supabase.py (crear si no existe)
```

### ¿Supabase soporta Alembic migrations?

**Sí**, pero con configuración especial:

```python
# alembic/env.py
from app.core.settings import settings

config.set_main_option("sqlalchemy.url", settings.postgres_url)
```

**Alternativa:** Usar Supabase CLI migrations en vez de Alembic.

### ¿Qué pasa con los datos en Redis si Supabase cae?

**Redis es independiente de Supabase**:
- ✅ Conversation sessions (Redis) siguen funcionando
- ✅ Feature flags (Redis) siguen funcionando
- ❌ Auth/user lookups fallan (dependen de Postgres)
- ❌ Tenant resolution falla (depende de Postgres)

**Solución:** Implementar caché local para tenant data (ya existe con TTL de 300s en `DynamicTenantService`).

### ¿Cómo escalo el pool de conexiones?

**Supabase Free Tier:** Max 60 conexiones directas
**Supabase Pro:** Max 200 conexiones directas

**Recomendación por ambiente:**

```bash
# Development (local)
POSTGRES_POOL_SIZE=5
POSTGRES_MAX_OVERFLOW=5

# Staging (single instance)
POSTGRES_POOL_SIZE=10
POSTGRES_MAX_OVERFLOW=10

# Production (3 replicas)
POSTGRES_POOL_SIZE=10  # 10 per replica = 30 total
POSTGRES_MAX_OVERFLOW=5  # Burst capacity
```

**Monitoreo:**
```sql
-- Ver conexiones activas en Supabase Dashboard → Database → Connection Pooling
SELECT count(*) FROM pg_stat_activity;
```

---

## Mantenimiento

### Backup Automático

Supabase realiza backups automáticos:
- **Free Tier:** 7 días de retención
- **Pro Tier:** 30 días de retención + Point-in-Time Recovery

**Verificar backups:**
Dashboard → Database → Backups

### Limpieza de Sesiones Expiradas

Script de maintenance (agregar a cron):

```sql
-- Eliminar user_sessions expiradas (ejecutar diariamente)
DELETE FROM user_sessions 
WHERE expires_at < NOW() - INTERVAL '7 days';

-- Eliminar password_history antiguo (mantener últimos 10 por usuario)
DELETE FROM password_history 
WHERE id NOT IN (
    SELECT id FROM (
        SELECT id, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC) as rn
        FROM password_history
    ) sub WHERE rn <= 10
);

-- Limpiar lock_audit antiguo (mantener últimos 30 días)
DELETE FROM lock_audit 
WHERE timestamp < NOW() - INTERVAL '30 days';
```

### Monitoreo con Prometheus

Métricas disponibles:
- `postgres_connections_active` → Pool usage
- `postgres_query_duration_seconds` → Query latency
- `postgres_errors_total` → Connection errors

Ver dashboards en: `docker/grafana/dashboards/`

---

## Siguientes Pasos

1. ✅ **Completar**: Deployment de schema en Supabase
2. ✅ **Configurar**: Variables de entorno con connection string
3. ✅ **Validar**: Health checks y tests de integración
4. 🟡 **Opcional**: Configurar rol dedicado `agente_backend`
5. 🟡 **Opcional**: Implementar Alembic migrations si se requiere
6. 🟡 **Staging**: Desplegar a ambiente staging con Supabase Staging project
7. 🟡 **Producción**: Migrar a Supabase Pro con monitoring completo

---

## Referencias

- [Supabase Database Docs](https://supabase.com/docs/guides/database)
- [Connection Pooling](https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler)
- [SQLAlchemy + asyncpg](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.asyncpg)
- [Copilot Instructions](../.github/copilot-instructions.md)

---

**Última actualización:** 2025-11-06  
**Mantenido por:** Backend AI Team  
**Versión:** 1.0.0
