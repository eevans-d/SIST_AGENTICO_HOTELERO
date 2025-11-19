# Supabase Integration Guide - Agente Hotel API

**Versión:** 2.0.0 CONSOLIDADA  
**Última Actualización:** 2025-11-17  
**Estado:** ✅ Documento Maestro Consolidado  
**Fuente:** Fusión de 15+ documentos de /docs/supabase/

---

## 📋 Tabla de Contenidos

1. [Overview y Arquitectura](#overview-y-arquitectura)
2. [Pre-requisitos](#pre-requisitos)
3. [Configuración Inicial](#configuración-inicial)
4. [Deployment del Schema](#deployment-del-schema)
5. [Configuración del Backend](#configuración-del-backend)
6. [Plan de Ejecución Completo](#plan-de-ejecución-completo)
7. [Testing y Validación](#testing-y-validación)
8. [Troubleshooting](#troubleshooting)
9. [Operación y Mantenimiento](#operación-y-mantenimiento)
10. [Rollback Plan](#rollback-plan)
11. [FAQ](#faq)

---

## Overview y Arquitectura

### Propósito

Integración de **Supabase Managed PostgreSQL** como capa de persistencia del backend, manteniendo Redis para caché/sesiones y QloApps PMS para dominio hotelero.

### Arquitectura de Datos

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

### ⚠️ IMPORTANTE: Separación de Responsabilidades

**✅ EN SUPABASE:**
- Autenticación JWT y usuarios
- Multi-tenancy (configuración de tenants)
- Auditoría de seguridad (sesiones, locks)
- Configuración de negocio (tenant settings)

**❌ NO EN SUPABASE:**
- ❌ Tablas del dominio hotelero (rooms, reservations, pricing) → Ya existen en QloApps PMS
- ❌ Conversation sessions → SessionManager usa Redis (TTL 30min)
- ❌ Feature flags → FeatureFlagService usa Redis hash
- ❌ Supabase Auth (goAuth) → Backend usa JWT custom con python-jose

---

## Pre-requisitos

### 1. Cuenta de Supabase

- ✅ Proyecto creado en [supabase.com](https://supabase.com)
- ✅ Plan Free (desarrollo/staging) o Pro (producción)
- ✅ Región seleccionada: `us-east-1` o más cercana

**Crear Nuevo Proyecto:**
```bash
1. Ir a: https://supabase.com/dashboard
2. Click "New Project"
3. Completar:
   - Project Name: agente-hotel-api-[env]  # dev, staging, prod
   - Database Password: [generar segura con: python -c "import secrets; print(secrets.token_urlsafe(32))"]
   - Region: us-east-1
   - Plan: Free (para dev/staging)

# Tiempo estimado: 2-3 minutos de provisioning
```

### 2. Herramientas Locales

```bash
# PostgreSQL client (para testing)
sudo apt-get install postgresql-client  # Ubuntu/Debian
brew install postgresql                 # macOS

# Python 3.12+ con Poetry
python --version  # debe ser >= 3.12.3
poetry --version

# Validar conexión asyncpg
poetry add asyncpg  # Si no está instalado
```

### 3. Información Requerida

Desde tu **Supabase Dashboard → Project Settings → Database**:

```bash
# 1. Connection String (Connection Pooling - Transaction mode)
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# 2. Project Reference
SUPABASE_PROJECT_REF=xxxxxxxxxxxxx

# 3. API Keys (Settings → API) - Opcional, no usado en backend JWT custom
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## Configuración Inicial

### Paso 1: Obtener Connection String

1. Ir a: **Supabase Dashboard → Project Settings → Database**
2. Sección **Connection String**
3. Seleccionar **"Connection pooling"** (modo Transaction)
4. Copiar el string completo

**Formato esperado:**
```
postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

**⚠️ NOTA IMPORTANTE sobre formato del pooler:**
- ✅ **Correcto**: `aws-0-us-east-1.pooler.supabase.com:6543`
- ❌ **Incorrecto**: `aws-1-us-east-1.pooler.supabase.com:6543` (formato antiguo)
- Verificar endpoint exacto en Dashboard (puede variar por región)

### Paso 2: Agregar SSL Obligatorio

```bash
# CRÍTICO: Agregar ?sslmode=require al final
DATABASE_URL=postgresql://postgres.xxxxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
```

**Por qué SSL es obligatorio:**
- Supabase requiere conexiones encriptadas en todos los planes
- Sin `sslmode=require`, la conexión fallará con error SSL
- `asyncpg` soporta SSL nativamente

### Paso 3: Configurar Variables de Entorno

Editar `.env` en `agente-hotel-api/`:

```bash
# Environment
ENVIRONMENT=staging  # o development, production
DEBUG=false
USE_SUPABASE=true

# Database (Supabase PostgreSQL 15)
POSTGRES_URL=postgresql://postgres.ofbsjfmnladfzbjmcxhx:PgSQL%402025_SecurePassw0rd!@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
DATABASE_URL=${POSTGRES_URL}

# Alembic (usa misma URL)
ALEMBIC_DB_URL=${POSTGRES_URL}

# Pool de conexiones (auto-ajustado por settings.py cuando USE_SUPABASE=true)
# NO necesitas cambiar estos - se ajustan a 2/2 automáticamente
# POSTGRES_POOL_SIZE=2
# POSTGRES_MAX_OVERFLOW=2

# Redis (Upstash o local)
REDIS_URL=rediss://default:TOKEN@needed-bulldog-8077.upstash.io:6379

# PMS Configuration
PMS_TYPE=mock  # o qloapps en staging/prod
PMS_BASE_URL=http://localhost:8080
```

**⚠️ NOTA sobre URL encoding:**
- Si tu password contiene caracteres especiales (`@`, `#`, `%`, etc.)
- Debes URL-encodearlos:
  - `@` → `%40`
  - `#` → `%23`
  - `%` → `%25`

---

## Deployment del Schema

### Schema DDL Canónico

El schema completo está en: `agente-hotel-api/docs/supabase/schema.sql`

**Tablas incluidas:**
1. `users` - Autenticación JWT y profiles
2. `user_sessions` - Tracking de tokens activos
3. `password_history` - Prevención de password reuse
4. `tenants` - Configuración multi-tenant
5. `tenant_user_identifiers` - Mapeo phone/email → tenant
6. `lock_audit` - Auditoría de locks distribuidos

### Método 1: Supabase SQL Editor (Recomendado)

```bash
1. Abrir: agente-hotel-api/docs/supabase/schema.sql
2. Ir a: Supabase Dashboard → SQL Editor → New Query
3. Copiar y pegar TODO el contenido
4. Click "Run" (o Ctrl+Enter)
5. Verificar que no haya errores
```

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
cd agente-hotel-api/docs/supabase

# Ejecutar contra Supabase
psql "postgresql://postgres.xxxxx:pass@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require" \
  -f schema.sql

# Validar
psql "..." -c "\dt"  # Listar tablas
```

### Método 3: Script Automatizado

```bash
cd agente-hotel-api

# Usando script de deployment
python scripts/deploy_supabase_schema.py \
  --connection-string "$DATABASE_URL" \
  --schema-file docs/supabase/schema.sql \
  --dry-run  # Primero validar sin ejecutar

# Si dry-run exitoso, ejecutar real
python scripts/deploy_supabase_schema.py \
  --connection-string "$DATABASE_URL" \
  --schema-file docs/supabase/schema.sql
```

---

## Configuración del Backend

### Paso 1: Validar Configuración

El backend detecta automáticamente Supabase cuando `USE_SUPABASE=true`:

```python
# app/core/settings.py ajusta automáticamente:
if self.use_supabase:
    self.postgres_pool_size = 2
    self.postgres_max_overflow = 2
    # Convierte postgresql:// a postgresql+asyncpg://
```

### Paso 2: Test de Conexión

```bash
cd agente-hotel-api

# Script de test de conexión
python scripts/test_supabase_connection.py

# Output esperado:
# ✅ Connection successful
# ✅ SSL enabled: True
# ✅ Server version: PostgreSQL 15.x
# ✅ Tables found: 6
```

### Paso 3: Ejecutar Migraciones Alembic (Opcional)

```bash
# Solo si usas Alembic para versioning de schema
poetry run alembic upgrade head

# Validar estado
poetry run alembic current
```

### Paso 4: Iniciar Backend

```bash
# Con Docker Compose
docker compose up -d

# Validar health
curl http://localhost:8002/health/ready | jq .

# Output esperado:
{
  "status": "healthy",
  "postgres": "connected",
  "redis": "connected"
}
```

---

## Plan de Ejecución Completo

### FASE 1: PRE-DEPLOYMENT (30 min)

**1.1 Validar Pre-requisitos**
```bash
# Checklist
[ ] Proyecto Supabase creado
[ ] Connection string obtenido
[ ] Variables en .env configuradas
[ ] Herramientas locales instaladas (psql, poetry)
[ ] Backup de datos existentes (si hay producción)
```

**1.2 Dry-Run del Schema**
```bash
# Test local del schema SQL
cd agente-hotel-api/docs/supabase
psql "postgres://localhost:5432/test_db" -f schema.sql  # Test local primero
```

**1.3 Crear Branch de Feature**
```bash
git checkout -b feature/supabase-integration
git status  # Validar limpieza
```

### FASE 2: DEPLOYMENT (1-2 horas)

**2.1 Deployment del Schema**
```bash
# Método SQL Editor (recomendado)
1. Copiar schema.sql completo
2. Pegar en Supabase SQL Editor
3. Ejecutar
4. Validar 6 tablas creadas
```

**2.2 Configurar Backend**
```bash
# Editar .env
USE_SUPABASE=true
DATABASE_URL=postgresql://...?sslmode=require

# Test de conexión
python scripts/test_supabase_connection.py
```

**2.3 Ejecutar Tests de Integración**
```bash
# Suite completa
poetry run pytest tests/integration/ -v

# Específicos de DB
poetry run pytest tests/integration/test_database.py -v
poetry run pytest tests/integration/test_user_repository.py -v
```

### FASE 3: VALIDACIÓN (1 hora)

**3.1 Smoke Tests**
```bash
# Levantar servicios
docker compose up -d

# Validar health endpoints
curl http://localhost:8002/health/live
curl http://localhost:8002/health/ready

# Validar métricas
curl http://localhost:9090/api/v1/query?query=up
```

**3.2 Tests End-to-End**
```bash
# Flujo completo de usuario
poetry run pytest tests/e2e/test_user_flow.py -v

# Verificar logs
docker compose logs agente_hotel_api | grep -i supabase
```

**3.3 Validar Métricas**
```bash
# Prometheus queries
# - postgres_connections_active
# - postgres_query_latency_seconds
# - postgres_errors_total

# Grafana dashboards
open http://localhost:3000  # Dashboard de Database
```

### FASE 4: POST-DEPLOYMENT (30 min)

**4.1 Documentar Deployment**
```bash
# Crear reporte
cat > .playbook/SUPABASE_DEPLOYMENT_REPORT.md << EOF
# Supabase Deployment Report
Fecha: $(date)
Connection String: [REDACTED]
Tables Deployed: 6
Tests Status: PASSING
EOF
```

**4.2 Commit y Push**
```bash
git add .env agente-hotel-api/docs/integrations/SUPABASE.md
git commit -m "feat: integrate Supabase as managed PostgreSQL backend"
git push origin feature/supabase-integration
```

**4.3 Monitoreo Inicial (24h)**
```bash
# Validar métricas cada 6h por 24h
# - Connection pool exhaustion
# - Query latency spikes
# - Error rate anomalies
```

---

## Testing y Validación

### Tests de Conexión

```bash
# Test básico de conexión
python scripts/test_supabase_connection.py

# Test con SSL debug
python scripts/test_supabase_connection.py --debug

# Test modo insecure (solo local, NO producción)
python scripts/test_supabase_connection.py --insecure  # Pide confirmación YES
```

### Tests de Integración

```bash
# Suite completa
poetry run pytest tests/integration/ -v --cov=app --cov-report=term-missing

# Tests específicos de repositorios
poetry run pytest tests/integration/test_user_repository.py -v
poetry run pytest tests/integration/test_tenant_repository.py -v
```

### Tests End-to-End

```bash
# Flujo completo de reservación
poetry run pytest tests/e2e/test_reservation_flow.py -v

# Validar multi-tenancy
poetry run pytest tests/e2e/test_multitenancy.py -v
```

### Validación Manual

```sql
-- Conectar a Supabase
psql "postgresql://postgres.xxxxx:pass@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require"

-- Listar tablas
\dt

-- Validar estructura
\d users
\d tenants

-- Test de inserción
INSERT INTO tenants (tenant_id, name) 
VALUES ('test-hotel', 'Test Hotel') 
RETURNING *;

-- Limpiar test
DELETE FROM tenants WHERE tenant_id = 'test-hotel';
```

---

## Troubleshooting

### Error: SSL connection required

**Síntoma:**
```
asyncpg.exceptions.InvalidAuthorizationSpecificationError: 
  FATAL: SSL connection is required
```

**Solución:**
```bash
# Agregar ?sslmode=require al connection string
DATABASE_URL=postgresql://...@host:6543/postgres?sslmode=require
```

### Error: Connection pool exhausted

**Síntoma:**
```
asyncpg.exceptions.TooManyConnectionsError: 
  too many clients already
```

**Solución:**
```bash
# En .env, reducir pool size cuando USE_SUPABASE=true
POSTGRES_POOL_SIZE=2  # Ya configurado automáticamente
POSTGRES_MAX_OVERFLOW=2

# Verificar que settings.py detecta USE_SUPABASE=true
python -c "from app.core.settings import get_settings; print(get_settings().postgres_pool_size)"
# Debe imprimir: 2
```

### Error: Relation does not exist

**Síntoma:**
```
asyncpg.exceptions.UndefinedTableError: 
  relation "users" does not exist
```

**Solución:**
```bash
# Validar que schema fue deployado
psql "$DATABASE_URL" -c "\dt"

# Si no hay tablas, re-ejecutar schema.sql
psql "$DATABASE_URL" -f docs/supabase/schema.sql
```

### Error: Password authentication failed

**Síntoma:**
```
asyncpg.exceptions.InvalidPasswordError: 
  password authentication failed
```

**Solución:**
```bash
# Validar URL encoding de password
# Si password es: MyP@ss123
# Debe ser: MyP%40ss123

# Regenerar connection string desde Dashboard
# Copiar exactamente como aparece
```

### Error: asyncpg SSL certificate verify failed

**Síntoma:**
```
ssl.SSLCertVerificationError: certificate verify failed
```

**Solución:**
```bash
# Actualizar certificados del sistema
sudo apt-get update && sudo apt-get install --reinstall ca-certificates

# O agregar parámetro a connection string
DATABASE_URL=postgresql://...?sslmode=require&sslrootcert=system
```

---

## Operación y Mantenimiento

### Monitoreo Diario

**Métricas Clave:**
```promql
# Connection pool usage
rate(postgres_connections_active[5m])

# Query latency P95
histogram_quantile(0.95, postgres_query_latency_seconds_bucket)

# Error rate
rate(postgres_errors_total[5m])
```

**Alertas Recomendadas:**
```yaml
# prometheus/alerts.yml
- alert: SupabaseConnectionPoolHigh
  expr: postgres_connections_active > 8
  for: 5m
  annotations:
    summary: "Supabase pool usage >80%"

- alert: SupabaseQueryLatencyHigh
  expr: histogram_quantile(0.95, postgres_query_latency_seconds_bucket) > 1
  for: 10m
  annotations:
    summary: "Supabase P95 latency >1s"
```

### Limpieza de Sesiones Expiradas

```sql
-- Job diario (ejecutar vía cron o Supabase Functions)
DELETE FROM user_sessions 
WHERE expires_at < NOW() - INTERVAL '7 days';

-- Auditoría de locks antiguos
DELETE FROM lock_audit 
WHERE created_at < NOW() - INTERVAL '30 days';
```

### Backups

**Automático (Supabase):**
- Daily backups: Incluido en Free tier (7 días)
- PITR (Point-in-Time Recovery): Solo en Pro tier

**Manual (On-demand):**
```bash
# Backup completo
pg_dump "$DATABASE_URL" > backup_$(date +%Y%m%d).sql

# Backup solo schema
pg_dump "$DATABASE_URL" --schema-only > schema_backup.sql

# Backup solo datos
pg_dump "$DATABASE_URL" --data-only > data_backup.sql
```

### Índices y Optimización

```sql
-- Validar uso de índices
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;

-- Encontrar queries lentos (requiere pg_stat_statements)
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Analizar tamaño de tablas
SELECT 
  schemaname, 
  tablename, 
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Rollback Plan

### Escenario 1: Deployment Fallido (Pre-Tests)

```bash
# 1. Detener backend
docker compose down agente_hotel_api

# 2. Revertir configuración
git checkout .env
git checkout agente-hotel-api/app/core/settings.py

# 3. Limpiar schema Supabase (si se deployó parcialmente)
psql "$DATABASE_URL" << EOF
DROP TABLE IF EXISTS lock_audit CASCADE;
DROP TABLE IF EXISTS password_history CASCADE;
DROP TABLE IF EXISTS user_sessions CASCADE;
DROP TABLE IF EXISTS tenant_user_identifiers CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS tenants CASCADE;
EOF

# 4. Restart con PostgreSQL local
docker compose up -d
```

### Escenario 2: Tests Fallando (Post-Deployment)

```bash
# 1. Capturar logs de error
docker compose logs agente_hotel_api > error_logs.txt

# 2. Dump de datos Supabase (si hay datos importantes)
pg_dump "$DATABASE_URL" > emergency_backup_$(date +%Y%m%d_%H%M%S).sql

# 3. Rollback a PostgreSQL local (temporal)
# Editar .env:
USE_SUPABASE=false
DATABASE_URL=postgresql+asyncpg://localhost:5432/postgres

# 4. Restart
docker compose restart agente_hotel_api

# 5. Analizar logs y reintentar deployment corregido
```

### Escenario 3: Producción Crítica (Fallback Inmediato)

```bash
# 1. Activar Blue-Green deployment (si disponible)
# Switch DNS/LB a instancia anterior

# 2. Notificar stakeholders
# Email/Slack con status y ETA de fix

# 3. Investigar root cause
# - Revisar Supabase Dashboard → Logs
# - Revisar métricas de Prometheus
# - Analizar error traces en Jaeger

# 4. Preparar hotfix
git checkout -b hotfix/supabase-rollback
# Aplicar correcciones
git commit -m "hotfix: revert Supabase integration temporarily"

# 5. Deploy hotfix
# Seguir procedimiento de deployment crítico
```

---

## FAQ

### ¿Puedo usar Supabase Auth en vez de JWT custom?

**No recomendado.** El backend ya tiene sistema JWT maduro con `python-jose`. Migrar a Supabase Auth requeriría:
- Reescribir `app/security/auth.py`
- Cambiar todos los endpoints protegidos
- Actualizar tests (500+ tests afectados)
- Riesgo alto de regresiones

**Recomendación:** Mantener JWT custom, usar Supabase solo como DB.

### ¿Cómo manejar migraciones de schema?

**Opción 1: Alembic (Recomendado)**
```bash
# Generar migración
poetry run alembic revision --autogenerate -m "add new column"

# Aplicar
poetry run alembic upgrade head
```

**Opción 2: SQL Migrations Manual**
```bash
# Crear archivo: migrations/2025_11_17_add_column.sql
ALTER TABLE users ADD COLUMN phone VARCHAR(20);

# Ejecutar
psql "$DATABASE_URL" -f migrations/2025_11_17_add_column.sql
```

### ¿Cuánto cuesta Supabase?

**Free Tier:**
- 500 MB database storage
- 1 GB bandwidth
- 2 GB file storage
- Daily backups (7 días)
- Community support
- **Costo:** $0/mes

**Pro Tier:**
- 8 GB database storage
- 250 GB bandwidth
- 100 GB file storage
- PITR backups
- Email support
- **Costo:** $25/mes

**Recomendación para proyecto:**
- Development: Free tier
- Staging: Free tier (con límite de uso controlado)
- Production: Pro tier ($25/mes)

### ¿Cómo escalar conexiones?

**Límites por tier:**
- Free: 60 conexiones simultáneas
- Pro: 120 conexiones
- Team/Enterprise: Custom

**Estrategia:**
1. Usar Connection Pooler (puerto 6543) → PgBouncer incluido
2. Configurar `POSTGRES_POOL_SIZE` bajo (2-5 por instancia)
3. Escalar horizontalmente (más instancias backend)
4. Monitorear `postgres_connections_active` metric

### ¿Qué pasa si Supabase tiene downtime?

**Mitigación:**
1. **Circuit Breaker:** Ya implementado en `app/core/database.py`
2. **Retry Logic:** Exponential backoff en queries críticos
3. **Fallback:** Mostrar mensaje de mantenimiento al usuario
4. **Alerting:** Prometheus alerta si DB unreachable >5min

**SLA de Supabase:**
- Free tier: Best-effort (sin SLA)
- Pro tier: 99.9% uptime (~43 min downtime/mes)

---

## Recursos Adicionales

**Documentación Oficial:**
- [Supabase Docs](https://supabase.com/docs)
- [PostgreSQL 15 Docs](https://www.postgresql.org/docs/15/)
- [asyncpg Docs](https://magicstack.github.io/asyncpg/)

**Scripts Útiles:**
- `scripts/test_supabase_connection.py` - Test de conexión
- `scripts/deploy_supabase_schema.py` - Deployment automatizado
- `scripts/backup_supabase.sh` - Backup manual

**Archivos de Referencia:**
- `docs/supabase/schema.sql` - DDL canónico
- `.env.supabase` - Ejemplo de configuración
- `app/core/settings.py` - Configuración de Supabase

**Contacto:**
- Supabase Support: support@supabase.com
- Community: [Discord](https://discord.supabase.com)

---

**Última revisión:** 2025-11-17  
**Mantenido por:** Backend Team  
**Changelog:** Ver `docs/integrations/SUPABASE_CHANGELOG.md`
