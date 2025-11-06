# 🎯 PLAN DE EJECUCIÓN: INTEGRACIÓN SUPABASE

**Proyecto:** Agente Hotel API  
**Fecha Inicio:** 2025-11-06  
**Estado:** ✅ READY TO EXECUTE  
**Estimación Total:** 4-6 horas (sin contar aprobaciones)  
**Complejidad:** Media-Alta  
**Risk Level:** Medio (backup strategy required)

---

## 📋 TABLA DE CONTENIDOS

1. [Executive Summary](#executive-summary)
2. [Pre-requisitos Críticos](#pre-requisitos-críticos)
3. [Blueprint de Arquitectura](#blueprint-de-arquitectura)
4. [Fases de Ejecución](#fases-de-ejecución)
5. [Checklist Completo](#checklist-completo)
6. [Rollback Plan](#rollback-plan)
7. [Success Criteria](#success-criteria)

---

## 📊 EXECUTIVE SUMMARY

### Objetivo
Migrar la capa de persistencia del backend desde PostgreSQL local a **Supabase Managed PostgreSQL**, manteniendo Redis para caché/sesiones y QloApps PMS para dominio hotelero.

### Alcance

**✅ IN SCOPE:**
- Deployment de schema SQL en Supabase (6 tablas)
- Configuración de connection string con pooler
- Validación de conexión asyncpg + SSL
- Tests de integración end-to-end
- Actualización de documentación

**❌ OUT OF SCOPE:**
- Migración de datos existentes (si hay producción corriendo)
- Implementación de Supabase Auth (usamos JWT custom)
- Implementación de RLS policies (innecesario para backend único)
- Cambios en QloApps PMS (permanece externo)
- Cambios en Redis (permanece para sesiones/caché)

### Beneficios Esperados

| Aspecto | Antes (Local Postgres) | Después (Supabase) | Mejora |
|---------|----------------------|-------------------|---------|
| **Uptime SLA** | Best-effort | 99.9% | ✅ +99% |
| **Backups** | Manual (si existe) | Automático 7-30d | ✅ PITR |
| **Scaling** | Manual vertical | Auto-scaling | ✅ Dynamic |
| **Monitoring** | Custom/Prometheus | Built-in + Custom | ✅ Dashboards |
| **SSL/TLS** | Opcional | Obligatorio | ✅ Security |
| **Connection Pooling** | PgBouncer manual | Built-in pooler | ✅ Managed |
| **Cost** | $0 (self-hosted) | $0-25/mo (Free tier) | ⚠️ +$0-25 |

### Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|-----------|
| Connection string incorrecto | Alta | Alto | Validación previa con psql CLI |
| SSL errors con asyncpg | Media | Alto | Documentación en troubleshooting |
| Pool exhaustion | Baja | Medio | Configurar POSTGRES_POOL_SIZE=10 |
| Schema deployment fails | Baja | Alto | Dry-run en SQL Editor antes |
| Tests fallan post-migración | Media | Medio | Suite completa de tests preparada |
| Downtime durante migración | Baja | Alto | Blue-green deployment pattern |

---

## 🔐 PRE-REQUISITOS CRÍTICOS

### 1️⃣ Acceso a Supabase

**NECESITO DE TI:**

```bash
# ¿Ya tienes un proyecto de Supabase creado?
[ ] SÍ - Proporcionar credenciales existentes
[ ] NO - Crear nuevo proyecto juntos

# Si NO tienes proyecto:
1. Ir a: https://supabase.com/dashboard
2. Click "New Project"
3. Completar:
   - Project Name: agente-hotel-api-[env]  # dev, staging, prod
   - Database Password: [generar segura]
   - Region: us-east-1 (o más cercana)
   - Plan: Free (para desarrollo/staging)

# Tiempo estimado: 5 minutos
# Output esperado: Project provisioned (2-3 min)
```

**INFORMACIÓN QUE NECESITAS PROPORCIONARME:**

```bash
# 1. Project URL
SUPABASE_PROJECT_URL=https://xxxxxxxxxxxxx.supabase.co

# 2. Project Reference (del dashboard)
SUPABASE_PROJECT_REF=xxxxxxxxxxxxx

# 3. Database Password (que estableciste al crear proyecto)
SUPABASE_DB_PASSWORD=your-secure-password

# 4. Connection String (Database → Connection String → Connection Pooling)
DATABASE_URL=postgresql://postgres.xxxxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require

# 5. API Keys (Settings → API)
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 2️⃣ Herramientas Locales

**YO VOY A VERIFICAR:**

```bash
# Python 3.12+ con poetry
python --version  # >= 3.12.3
poetry --version

# PostgreSQL client (para testing)
psql --version

# Docker (para servicios auxiliares)
docker --version
docker-compose --version

# Git (para commits)
git --version
```

**SI FALTA ALGUNA, TE PEDIRÉ INSTALAR:**

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y postgresql-client python3.12 docker.io docker-compose

# macOS
brew install postgresql python@3.12 docker
```

### 3️⃣ Estado del Repositorio

**YO VOY A VALIDAR:**

```bash
# Branch limpio
git status  # Should be clean or only untracked files

# No hay cambios sin commitear en archivos críticos
# app/core/settings.py, app/core/database.py, etc.

# Tests actuales passing
make test-unit  # Al menos tests críticos pasando
```

---

## 🏗️ BLUEPRINT DE ARQUITECTURA

### Estado Actual (AS-IS)

```
┌─────────────────────────────────────────────────────────────┐
│ AGENTE-API (FastAPI)                                        │
│ ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│ │ Auth/Users      │  │ Multi-Tenancy   │  │ Lock Audit  │ │
│ │ (SQLAlchemy)    │  │ (SQLAlchemy)    │  │ (SQLAlchemy)│ │
│ └────────┬────────┘  └────────┬────────┘  └──────┬──────┘ │
│          │                     │                   │        │
│          └─────────────────────┴───────────────────┘        │
│                              │                              │
│                    ┌─────────▼─────────┐                   │
│                    │ AsyncSessionFactory│                   │
│                    │ (asyncpg driver)   │                   │
│                    └─────────┬─────────┘                   │
└──────────────────────────────┼──────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │ PostgreSQL:5432     │
                    │ (Docker Container)  │
                    │ - Local volume      │
                    │ - No backups auto   │
                    └─────────────────────┘

┌────────────────────────────────────────────────────┐
│ REDIS:6379 (Ephemeral Data)                       │
│ - Conversation sessions (TTL 30min)               │
│ - Feature flags hash                              │
│ - Distributed locks                               │
└────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│ QLOAPPS PMS (External - HTTP API)                 │
│ - Hotel domain (rooms, reservations, etc.)        │
└────────────────────────────────────────────────────┘
```

### Estado Objetivo (TO-BE)

```
┌─────────────────────────────────────────────────────────────┐
│ AGENTE-API (FastAPI)                                        │
│ ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│ │ Auth/Users      │  │ Multi-Tenancy   │  │ Lock Audit  │ │
│ │ (SQLAlchemy)    │  │ (SQLAlchemy)    │  │ (SQLAlchemy)│ │
│ └────────┬────────┘  └────────┬────────┘  └──────┬──────┘ │
│          │                     │                   │        │
│          └─────────────────────┴───────────────────┘        │
│                              │                              │
│                    ┌─────────▼─────────┐                   │
│                    │ AsyncSessionFactory│                   │
│                    │ (asyncpg driver)   │                   │
│                    └─────────┬─────────┘                   │
└──────────────────────────────┼──────────────────────────────┘
                               │
                               │ ✅ SSL/TLS Required
                               │ ✅ Connection Pooler :6543
                               │
                    ┌──────────▼────────────────────────┐
                    │ SUPABASE POSTGRES                 │
                    │ ┌───────────────────────────────┐ │
                    │ │ PgBouncer (Transaction Mode)  │ │
                    │ └──────────┬────────────────────┘ │
                    │            │                       │
                    │ ┌──────────▼────────────────────┐ │
                    │ │ PostgreSQL 14                 │ │
                    │ │ - Managed service             │ │
                    │ │ - Auto backups (7d/30d)       │ │
                    │ │ - PITR recovery               │ │
                    │ │ - 99.9% SLA                   │ │
                    │ └───────────────────────────────┘ │
                    └───────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│ REDIS:6379 (Sin cambios)                          │
│ - Conversation sessions (TTL 30min)               │
│ - Feature flags hash                              │
│ - Distributed locks                               │
└────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│ QLOAPPS PMS (Sin cambios - External)              │
│ - Hotel domain (rooms, reservations, etc.)        │
└────────────────────────────────────────────────────┘
```

### Cambios en Configuración

| Archivo | Cambio | Antes | Después |
|---------|--------|-------|---------|
| `.env` | DATABASE_URL | `postgresql+asyncpg://localhost:5432/postgres` | `postgresql+asyncpg://...pooler.supabase.com:6543/postgres?sslmode=require` |
| `.env` | POSTGRES_HOST | `localhost` | `aws-0-us-east-1.pooler.supabase.com` |
| `.env` | POSTGRES_PORT | `5432` | `6543` |
| `.env` | POSTGRES_USER | `postgres` | `postgres.xxxxxxxxxxxxx` |
| `docker-compose.yml` | postgres service | Activo | ⚠️ Comentado (opcional keep for local dev) |
| `app/core/settings.py` | (Sin cambios) | Auto-detección asyncpg | Auto-detección asyncpg |

---

## 🚀 FASES DE EJECUCIÓN

### FASE 0: Pre-Validación (15 min)

**Objetivo:** Confirmar que el entorno está listo

**TÚ EJECUTAS:**
```bash
# 1. Crear/verificar proyecto Supabase (manual en dashboard)
# Ver sección "Pre-requisitos Críticos" arriba

# 2. Proporcionar credenciales (copiar de Supabase Dashboard)
# Ver formato en "Pre-requisitos Críticos"
```

**YO EJECUTO:**
```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

# 1. Verificar estado del repo
git status
git log --oneline -5

# 2. Verificar herramientas
python --version
poetry --version
psql --version

# 3. Backup de configuración actual
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
cp app/core/settings.py app/core/settings.py.backup

# 4. Verificar tests actuales
make test-unit | tee test-results-pre-migration.log
```

**Criterios de Éxito:**
- ✅ Proyecto Supabase creado y accesible
- ✅ Credenciales proporcionadas y validadas
- ✅ Herramientas instaladas y funcionando
- ✅ Backup de configuración creado
- ✅ Tests baseline documentados

**Tiempo Estimado:** 15 minutos  
**Risk Level:** Bajo

---

### FASE 1: Configuración Supabase Project (30 min)

**Objetivo:** Preparar el proyecto Supabase con schema y configuración

#### 1.1 Validar Conexión (YO EJECUTO)

```bash
# Test connection con psql
psql "postgresql://postgres.xxxxx:PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require" \
  -c "SELECT version();"

# Expected output:
# PostgreSQL 14.x on x86_64-pc-linux-gnu, compiled by gcc ...

# Si falla con SSL error, diagnosticar:
psql "..." -c "\conninfo"
```

**Troubleshooting común:**
- ❌ `connection refused` → Verificar puerto 6543 (NO 5432)
- ❌ `SSL connection closed` → Agregar `?sslmode=require`
- ❌ `password authentication failed` → Verificar password y username con project ref

#### 1.2 Deploy Schema (YO EJECUTO)

**Opción A: Via psql CLI (Recomendado para automatización)**

```bash
cd docs/supabase

# Dry-run: Validar SQL sin ejecutar
psql "postgresql://..." \
  -f schema.sql \
  --dry-run  # Si psql lo soporta

# Ejecutar schema
psql "postgresql://postgres.xxxxx:PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require" \
  -f schema.sql \
  2>&1 | tee schema-deployment.log

# Verificar tablas creadas
psql "postgresql://..." -c "\dt"
```

**Expected Output:**
```
                List of relations
 Schema |          Name          | Type  |  Owner   
--------+------------------------+-------+----------
 public | lock_audit             | table | postgres
 public | password_history       | table | postgres
 public | tenant_user_identifiers| table | postgres
 public | tenants                | table | postgres
 public | user_sessions          | table | postgres
 public | users                  | table | postgres
(6 rows)
```

**Opción B: Via Supabase SQL Editor (Fallback manual)**

```sql
-- TÚ EJECUTAS en Supabase Dashboard → SQL Editor:
-- 1. Copiar contenido completo de docs/supabase/schema.sql
-- 2. Pegar en SQL Editor
-- 3. Click "Run" (Ctrl+Enter)
-- 4. Verificar "Success" sin errores
```

#### 1.3 Validar Schema (YO EJECUTO)

```bash
# Verificar estructura de cada tabla
psql "postgresql://..." -c "
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;
" > schema-validation.txt

# Verificar índices
psql "postgresql://..." -c "
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
" > indexes-validation.txt

# Verificar foreign keys
psql "postgresql://..." -c "
SELECT
    tc.table_name, 
    tc.constraint_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
ORDER BY tc.table_name;
" > fk-validation.txt
```

**Criterios de Éxito:**
- ✅ Conexión exitosa con psql
- ✅ 6 tablas creadas sin errores
- ✅ Todos los índices creados
- ✅ Foreign keys configuradas correctamente
- ✅ Triggers de updated_at funcionando

**Tiempo Estimado:** 30 minutos  
**Risk Level:** Medio (requiere credenciales correctas)

---

### FASE 2: Configuración Backend (45 min)

**Objetivo:** Actualizar configuración del backend para usar Supabase

#### 2.1 Actualizar Variables de Entorno (YO EJECUTO)

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

# Crear nuevo .env con configuración Supabase
cat > .env.supabase << 'EOF'
# ============================================================================
# SUPABASE INTEGRATION - DATABASE CONFIGURATION
# ============================================================================
# Generated: $(date +%Y-%m-%d)
# Project: agente-hotel-api

# Supabase Connection (Transaction Pooling)
DATABASE_URL=postgresql://postgres.PROJECTREF:PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require

# Component-based (alternative - settings.py will construct URL)
POSTGRES_HOST=aws-0-us-east-1.pooler.supabase.com
POSTGRES_PORT=6543
POSTGRES_DB=postgres
POSTGRES_USER=postgres.PROJECTREF
POSTGRES_PASSWORD=PASSWORD
POSTGRES_POOL_SIZE=10
POSTGRES_MAX_OVERFLOW=10

# Supabase Project Info (for future Supabase client SDK if needed)
SUPABASE_PROJECT_URL=https://PROJECTREF.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Redis (sin cambios)
REDIS_URL=redis://localhost:6379/0

# PMS (sin cambios)
PMS_TYPE=mock
PMS_BASE_URL=http://localhost:8080

# ... resto de configuración existente ...
EOF

# IMPORTANTE: Reemplazar placeholders con tus valores reales
# TÚ ME PROPORCIONARÁS: PROJECTREF, PASSWORD, etc.
```

#### 2.2 Validar Settings.py (YO VALIDO)

```bash
# Verificar que settings.py detecta correctamente la URL
python -c "
from app.core.settings import settings
print('✅ Postgres URL:', settings.postgres_url)
print('✅ Pool Size:', settings.postgres_pool_size)
print('✅ Driver detected:', 'asyncpg' if 'asyncpg' in settings.postgres_url else 'WRONG')
print('✅ SSL mode:', 'sslmode=require' if 'sslmode=require' in settings.postgres_url else 'MISSING SSL')
"
```

**Expected Output:**
```
✅ Postgres URL: postgresql+asyncpg://postgres.xxxxx:***@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
✅ Pool Size: 10
✅ Driver detected: asyncpg
✅ SSL mode: sslmode=require
```

#### 2.3 Actualizar docker-compose.yml (YO EJECUTO)

**Opción A: Comentar postgres service (mantener para local dev)**

```yaml
# docker-compose.yml

services:
  agente-api:
    # ... sin cambios ...
    environment:
      # Usar Supabase (desde .env)
      - POSTGRES_URL=${DATABASE_URL}
    depends_on:
      - redis
      # - postgres  # ⚠️ Comentado: usando Supabase remoto

  redis:
    # ... sin cambios ...

  # ⚠️ LOCAL POSTGRES COMENTADO (opcional mantener para dev local)
  # postgres:
  #   image: postgres:14-alpine
  #   environment:
  #     POSTGRES_PASSWORD: postgres
  #   volumes:
  #     - postgres_data:/var/lib/postgresql/data
  #   ports:
  #     - "5432:5432"

volumes:
  redis_data:
  # postgres_data:  # Comentado si no se usa
```

**Opción B: Mantener ambos con perfiles**

```yaml
services:
  postgres:
    profiles: ["local-db"]  # Solo si se activa explícitamente
    # ... resto de configuración ...
```

```bash
# Uso:
docker-compose up                           # Solo Redis + Agente-API (usa Supabase)
docker-compose --profile local-db up        # Redis + Postgres local + Agente-API
```

#### 2.4 Test Connection Programático (YO EJECUTO)

```python
# scripts/test_supabase_connection.py (crear si no existe)
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.settings import settings

async def test_connection():
    engine = create_async_engine(settings.postgres_url, echo=True)
    
    async with engine.begin() as conn:
        result = await conn.execute("SELECT version();")
        version = result.fetchone()[0]
        print(f"✅ PostgreSQL Version: {version}")
        
        result = await conn.execute("SELECT COUNT(*) FROM users;")
        count = result.fetchone()[0]
        print(f"✅ Users table accessible: {count} records")
        
    await engine.dispose()
    print("✅ Connection test PASSED")

if __name__ == "__main__":
    asyncio.run(test_connection())
```

```bash
# Ejecutar test
python scripts/test_supabase_connection.py
```

**Criterios de Éxito:**
- ✅ Variables de entorno actualizadas correctamente
- ✅ settings.py detecta asyncpg driver
- ✅ SSL mode presente en connection string
- ✅ docker-compose.yml actualizado sin errores de sintaxis
- ✅ Test de conexión programático exitoso

**Tiempo Estimado:** 45 minutos  
**Risk Level:** Medio-Alto (configuración crítica)

---

### FASE 3: Testing & Validación (60 min)

**Objetivo:** Verificar que todo funciona correctamente con Supabase

#### 3.1 Unit Tests (YO EJECUTO)

```bash
# Tests que usan in-memory SQLite (no afectados)
make test-unit

# Debe pasar todos los tests existentes
# Tests usan aiosqlite en memoria, no Supabase
```

#### 3.2 Integration Tests con Supabase (YO EJECUTO)

```bash
# Tests de integración que SÍ usan la DB real
pytest tests/integration/ -v --tb=short

# Tests específicos de database
pytest tests/integration/test_database.py -v
pytest tests/integration/test_tenant_service.py -v
pytest tests/integration/test_session_manager.py -v
```

**Si fallan tests, diagnosticar:**

```bash
# Ver logs detallados
pytest tests/integration/ -vv -s --log-cli-level=DEBUG

# Test individual con trace
pytest tests/integration/test_database.py::test_create_user -vv -s
```

#### 3.3 Health Checks (YO EJECUTO)

```bash
# Iniciar servicios
docker-compose up -d

# Esperar startup
sleep 10

# Health check liveness (siempre debe pasar)
curl http://localhost:8002/health/live | jq .
# Expected: {"status": "healthy"}

# Health check readiness (valida Postgres + Redis)
curl http://localhost:8002/health/ready | jq .
# Expected: {
#   "status": "healthy",
#   "postgres": "ok",
#   "redis": "ok",
#   "timestamp": "..."
# }
```

**Si readiness falla:**

```bash
# Ver logs del backend
docker logs agente-api --tail 100

# Buscar errores de conexión
docker logs agente-api | grep -i "error\|exception\|failed"

# Test manual de Postgres
docker exec agente-api python -c "
from app.core.database import test_connection
import asyncio
asyncio.run(test_connection())
"
```

#### 3.4 CRUD Operations Test (YO EJECUTO)

```bash
# Script de test completo
cat > scripts/test_supabase_crud.py << 'EOF'
import asyncio
from app.core.database import AsyncSessionFactory
from app.models.tenant import Tenant, TenantUserIdentifier
from datetime import datetime, UTC

async def test_crud():
    async with AsyncSessionFactory() as session:
        # CREATE
        tenant = Tenant(
            tenant_id="test-hotel",
            name="Test Hotel",
            status="active"
        )
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)
        print(f"✅ CREATE: Tenant ID {tenant.id} created")
        
        # READ
        from sqlalchemy import select
        stmt = select(Tenant).where(Tenant.tenant_id == "test-hotel")
        result = await session.execute(stmt)
        tenant_read = result.scalar_one()
        print(f"✅ READ: Tenant {tenant_read.name} retrieved")
        
        # UPDATE
        tenant_read.name = "Test Hotel Updated"
        await session.commit()
        print(f"✅ UPDATE: Tenant name updated")
        
        # DELETE
        await session.delete(tenant_read)
        await session.commit()
        print(f"✅ DELETE: Tenant deleted")
        
    print("\n✅ ALL CRUD OPERATIONS PASSED")

if __name__ == "__main__":
    asyncio.run(test_crud())
EOF

python scripts/test_supabase_crud.py
```

#### 3.5 Performance Baseline (YO EJECUTO)

```bash
# Medir latencia de queries
python -c "
import asyncio
import time
from app.core.database import AsyncSessionFactory
from sqlalchemy import select, text

async def benchmark():
    times = []
    async with AsyncSessionFactory() as session:
        for i in range(100):
            start = time.time()
            await session.execute(select(text('1')))
            times.append(time.time() - start)
    
    import statistics
    print(f'Queries: 100')
    print(f'Min: {min(times)*1000:.2f}ms')
    print(f'Max: {max(times)*1000:.2f}ms')
    print(f'Avg: {statistics.mean(times)*1000:.2f}ms')
    print(f'P95: {statistics.quantiles(times, n=20)[18]*1000:.2f}ms')

asyncio.run(benchmark())
"

# Baseline esperado con Supabase:
# - P95 latency: 50-150ms (depende de región)
# - Avg latency: 30-80ms
```

**Criterios de Éxito:**
- ✅ Unit tests pasan (100% de los que pasaban antes)
- ✅ Integration tests pasan (al menos 90%)
- ✅ Health checks retornan `postgres: ok`
- ✅ CRUD operations funcionan correctamente
- ✅ Performance baseline documentada (P95 < 200ms)

**Tiempo Estimado:** 60 minutos  
**Risk Level:** Alto (validación crítica)

---

### FASE 4: Documentación & Cierre (30 min)

**Objetivo:** Actualizar documentación y cerrar el proyecto

#### 4.1 Actualizar README (YO EJECUTO)

```bash
# Actualizar README.md principal
# Agregar sección "Database: Supabase"
# Actualizar instrucciones de setup

# Actualizar docs/00-DOCUMENTATION-CENTRAL-INDEX.md
# Agregar referencia a docs/supabase/
```

#### 4.2 Crear Migration Notes (YO CREO)

```markdown
# docs/supabase/MIGRATION-NOTES.md

## Migration to Supabase - 2025-11-06

### Changes Made
- [x] Schema deployed to Supabase
- [x] Connection string updated in .env
- [x] docker-compose.yml modified (postgres commented)
- [x] Tests validated against Supabase
- [x] Health checks passing

### Performance Baseline
- P95 latency: XXms
- Connection pool: 10
- Region: us-east-1

### Rollback Instructions
See: docs/supabase/ROLLBACK.md
```

#### 4.3 Git Commit (YO EJECUTO)

```bash
git add -A
git commit -m "feat(infra): migrate database from local Postgres to Supabase

- Deploy schema (6 tables) to Supabase managed Postgres
- Update DATABASE_URL to use Supabase pooler (port 6543 with SSL)
- Comment out local postgres service in docker-compose.yml
- Validate connection with asyncpg + SSL
- All tests passing (unit + integration)
- Health checks validated (postgres: ok, redis: ok)
- Performance baseline: P95 XXms latency

BREAKING CHANGE: Requires Supabase project and credentials.
See docs/supabase/EXECUTION-PLAN.md for setup instructions.

Migration validated:
- Schema deployment: ✅
- Connection test: ✅
- CRUD operations: ✅
- Integration tests: ✅
- Health checks: ✅

Refs: docs/supabase/EXECUTION-PLAN.md
"

git push origin main
```

**Criterios de Éxito:**
- ✅ README actualizado con instrucciones Supabase
- ✅ MIGRATION-NOTES.md creado con detalles
- ✅ Commit descriptivo pusheado a main
- ✅ Documentación indexada en 00-DOCUMENTATION-CENTRAL-INDEX.md

**Tiempo Estimado:** 30 minutos  
**Risk Level:** Bajo

---

## ✅ CHECKLIST COMPLETO

### Pre-Ejecución

```bash
[ ] Proyecto Supabase creado
[ ] Credenciales de Supabase obtenidas
    [ ] Project URL
    [ ] Project Reference
    [ ] Database Password
    [ ] Connection String (pooling mode)
    [ ] API Keys (anon + service role)
[ ] Herramientas instaladas (python, psql, docker)
[ ] Backup de .env actual creado
[ ] Backup de settings.py creado
[ ] Tests baseline documentados
```

### Fase 1: Supabase Setup

```bash
[ ] Conexión validada con psql
[ ] Schema SQL deployado sin errores
[ ] 6 tablas creadas y verificadas:
    [ ] users
    [ ] user_sessions
    [ ] password_history
    [ ] tenants
    [ ] tenant_user_identifiers
    [ ] lock_audit
[ ] Índices creados correctamente
[ ] Foreign keys configuradas
[ ] Triggers de updated_at funcionando
[ ] Validación SQL ejecutada y guardada
```

### Fase 2: Backend Configuration

```bash
[ ] .env actualizado con DATABASE_URL de Supabase
[ ] Variables de entorno validadas:
    [ ] POSTGRES_HOST (pooler.supabase.com)
    [ ] POSTGRES_PORT (6543)
    [ ] POSTGRES_USER (postgres.PROJECTREF)
    [ ] POSTGRES_PASSWORD (correcto)
[ ] settings.py detecta asyncpg driver
[ ] SSL mode presente (?sslmode=require)
[ ] docker-compose.yml actualizado
[ ] Test de conexión programático exitoso
```

### Fase 3: Testing

```bash
[ ] Unit tests pasando (make test-unit)
[ ] Integration tests pasando (pytest tests/integration/)
[ ] Health check liveness: 200 OK
[ ] Health check readiness: postgres=ok, redis=ok
[ ] CRUD operations test exitoso
[ ] Performance baseline documentada:
    [ ] P95 latency: ___ms
    [ ] Avg latency: ___ms
    [ ] Connection pool working
```

### Fase 4: Documentación

```bash
[ ] README.md actualizado con Supabase setup
[ ] MIGRATION-NOTES.md creado
[ ] 00-DOCUMENTATION-CENTRAL-INDEX.md actualizado
[ ] Performance metrics documentadas
[ ] Git commit creado con mensaje descriptivo
[ ] Cambios pusheados a main
```

### Post-Ejecución

```bash
[ ] Supabase Dashboard monitoreado (sin errores)
[ ] Logs del backend revisados (sin warnings críticos)
[ ] Prometheus metrics validadas (postgres_connections_active)
[ ] Grafana dashboard funcional (si aplicable)
[ ] Team notificado de migración exitosa
[ ] Rollback plan documentado y entendido
```

---

## 🔄 ROLLBACK PLAN

### Si algo falla durante la migración

#### Escenario 1: Schema deployment falla

```bash
# Drop tables parciales en Supabase
psql "postgresql://..." -c "
DROP TABLE IF EXISTS lock_audit CASCADE;
DROP TABLE IF EXISTS tenant_user_identifiers CASCADE;
DROP TABLE IF EXISTS password_history CASCADE;
DROP TABLE IF EXISTS user_sessions CASCADE;
DROP TABLE IF EXISTS tenants CASCADE;
DROP TABLE IF EXISTS users CASCADE;
"

# Re-ejecutar schema.sql completo
psql "postgresql://..." -f docs/supabase/schema.sql
```

#### Escenario 2: Backend no conecta a Supabase

```bash
# Restaurar configuración anterior
cp .env.backup.TIMESTAMP .env

# Descomentar postgres en docker-compose.yml
# Reiniciar servicios
docker-compose down
docker-compose up -d

# Verificar health
curl http://localhost:8002/health/ready
```

#### Escenario 3: Tests fallan post-migración

```bash
# Revertir cambios en .env
cp .env.backup.TIMESTAMP .env

# Revertir docker-compose.yml
git checkout docker-compose.yml

# Reiniciar con configuración anterior
docker-compose down
docker-compose up -d

# Verificar tests
make test
```

#### Rollback Completo (Emergencia)

```bash
# 1. Revertir todos los cambios
git reset --hard HEAD~1  # Si ya committeaste
# O
git checkout .  # Si no committeaste

# 2. Restaurar backups
cp .env.backup.TIMESTAMP .env
cp app/core/settings.py.backup app/core/settings.py

# 3. Reiniciar servicios con Postgres local
docker-compose down -v  # Eliminar volúmenes
docker-compose up -d

# 4. Verificar funcionamiento
make health
make test
```

---

## 🎯 SUCCESS CRITERIA

### Criterios Técnicos

- ✅ **Schema Deployed:** 6 tablas en Supabase sin errores
- ✅ **Connection Working:** Health check `postgres: ok` consistente
- ✅ **Tests Passing:** 100% unit tests, 90%+ integration tests
- ✅ **Performance:** P95 latency < 200ms para queries simples
- ✅ **SSL Enabled:** Connection string con `sslmode=require`
- ✅ **Pooling Active:** Connection pooler (port 6543) usado correctamente

### Criterios de Calidad

- ✅ **Documentation:** README y guías actualizadas
- ✅ **Monitoring:** Prometheus metrics funcionando
- ✅ **Logging:** Sin errores críticos en logs del backend
- ✅ **Rollback Tested:** Procedimiento de rollback documentado y validado

### Criterios de Negocio

- ✅ **Zero Downtime:** Migración sin impacto en servicios (si hay prod)
- ✅ **Data Integrity:** Todos los datos migrados correctamente (si aplica)
- ✅ **SLA Improvement:** Uptime esperado 99.9% (Supabase SLA)
- ✅ **Cost Justified:** Free tier suficiente para dev/staging

---

## 📊 TRACKING & REPORTING

### Daily Standup Updates

```markdown
## Supabase Migration - Day X

**Status:** 🟢 On Track / 🟡 At Risk / 🔴 Blocked

**Completed Today:**
- [ ] Phase X completed
- [ ] Y tests passing
- [ ] Z issues resolved

**Blockers:**
- None / [Describe blocker]

**Next Steps:**
- [ ] Start Phase Y
- [ ] Resolve issue Z

**ETA:** On schedule for [date]
```

### Final Report Template

```markdown
## Supabase Migration - Final Report

**Date:** 2025-11-06  
**Duration:** X hours  
**Status:** ✅ SUCCESS / ⚠️ PARTIAL / ❌ FAILED

### Metrics
- Schema deployment: XX minutes
- Backend configuration: XX minutes
- Testing: XX minutes
- Total time: XX hours

### Performance
- P95 latency: XXms (before: XXms)
- Connection pool: 10
- SSL: Enabled
- Region: us-east-1

### Issues Encountered
1. [Issue description] - RESOLVED
2. [Issue description] - MITIGATED

### Lessons Learned
1. [Lesson 1]
2. [Lesson 2]

### Recommendations
1. [Recommendation 1]
2. [Recommendation 2]
```

---

## 🆘 NEED HELP?

### Contactos de Soporte

| Recurso | Cuándo Usar | Link |
|---------|------------|------|
| **Supabase Docs** | Errores de conexión, SSL | https://supabase.com/docs/guides/database |
| **Supabase Support** | Issues con el proyecto | Dashboard → Support |
| **asyncpg Docs** | Errores de driver | https://magicstack.github.io/asyncpg/ |
| **Project Issues** | Bugs del backend | GitHub Issues |
| **Team Chat** | Consultas rápidas | Slack #agente-hotel-dev |

### Comandos de Diagnóstico

```bash
# Ver logs detallados del backend
docker logs agente-api --tail 100 --follow

# Test manual de conexión
psql "postgresql://..." -c "SELECT 1;"

# Ver queries activas en Supabase
psql "postgresql://..." -c "
SELECT pid, usename, application_name, state, query
FROM pg_stat_activity
WHERE datname = 'postgres';
"

# Monitorear pool de conexiones
python -c "
from app.core.database import engine
print(f'Pool size: {engine.pool.size()}')
print(f'Pool checked out: {engine.pool.checkedout()}')
"
```

---

## 📝 NOTAS FINALES

### Consideraciones Importantes

1. **Backup Strategy:** Supabase Free tier tiene 7 días de retención. Para staging/prod, considerar upgrade a Pro (30 días + PITR).

2. **Cost Monitoring:** Free tier incluye 500MB DB + 2GB bandwidth. Monitorear uso en Dashboard → Settings → Usage.

3. **Connection Limits:** Free tier = 60 conexiones directas. Usando pooler (6543) no hay límite práctico.

4. **SSL Certificate:** Supabase usa Let's Encrypt. Auto-renovación sin acción requerida.

5. **Future Scaling:** Si se necesita más rendimiento, considerar:
   - Upgrade a Pro plan ($25/mo)
   - Habilitar read replicas (Pro plan)
   - Implementar Redis como query cache

### Próximos Pasos Post-Migración

1. **Monitoreo Continuo:**
   - Configurar alertas en Supabase Dashboard
   - Integrar métricas Supabase con Prometheus
   - Dashboard Grafana para DB metrics

2. **Optimización:**
   - Analizar slow queries en Supabase Dashboard
   - Agregar índices adicionales si es necesario
   - Optimizar pool size según carga real

3. **Backups:**
   - Configurar backups adicionales (pg_dump scheduled)
   - Documentar restore procedures
   - Test de recovery point objective (RPO)

4. **Security:**
   - Rotar passwords periódicamente
   - Implementar IP allowlist en Supabase (Pro plan)
   - Audit logs review mensual

---

**¿LISTO PARA COMENZAR?**

Cuando me proporciones las credenciales de Supabase, procederé con la ejecución siguiendo este plan paso a paso. Te mantendré informado en cada fase y validaré contigo antes de cambios críticos.

**Necesito de ti:**
1. ✅ Proyecto Supabase creado (o indicación para crearlo juntos)
2. ✅ Connection String completo con password
3. ✅ Confirmación para proceder con Fase 0

**Tiempo total estimado:** 4-6 horas  
**Puntos de sincronización:** Después de cada fase  
**Rollback siempre disponible:** Sí, documentado arriba
