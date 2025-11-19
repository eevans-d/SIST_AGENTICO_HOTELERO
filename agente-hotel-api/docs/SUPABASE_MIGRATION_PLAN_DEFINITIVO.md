# 🚀 PLAN DEFINITIVO: MIGRACIÓN A SUPABASE

**Fecha**: 2025-11-15  
**Proyecto**: SIST_AGENTICO_HOTELERO  
**Estado Actual**: Listo para producción (8.9/10), 28 tests passing, 41% coverage  
**Objetivo**: Migración controlada de PostgreSQL local → Supabase (staging/producción)

---

## 📋 RESUMEN EJECUTIVO

### Veredicto: ✅ LISTO PARA MIGRAR (95% compatible)

- **Compatibilidad técnica**: Alta - `asyncpg` + SQLAlchemy 2.0 ya configurado
- **Esfuerzo estimado**: 6-10 horas (preparación + migración + validación)
- **Riesgo**: BAJO con rollback documentado
- **Costo mensual**: $30-45 (Supabase Pro + Redis externo)

---

## 🎯 ESTADO ACTUAL vs SUPABASE

### ✅ YA IMPLEMENTADO (No requiere cambios)

| Componente | Estado | Evidencia |
|------------|--------|-----------|
| **Driver asyncpg** | ✅ Configurado | `app/core/database.py` usa `create_async_engine` |
| **Settings multi-env** | ✅ Preparado | `AliasChoices(DATABASE_URL, POSTGRES_URL, postgres_url)` |
| **Auto-ajuste pool** | ✅ Implementado | Detecta `supabase.co` y ajusta límites (líneas 336-343) |
| **Timeouts configurados** | ✅ Activo | `statement_timeout=15s`, `idle_in_transaction_session_timeout=10s` |
| **Migraciones Alembic** | ✅ Preparadas | `alembic/env.py` lee `ALEMBIC_DB_URL` desde entorno |

### ⚠️ REQUIERE AJUSTE (Crítico)

| Componente | Estado Actual | Acción Requerida | Prioridad |
|------------|---------------|------------------|-----------|
| **Redis externo** | Local Docker | Configurar Upstash/Redis Cloud | 🔴 P0 |
| **RLS multi-tenant** | No habilitado | Políticas SQL + middleware SET LOCAL | 🔴 P0* |
| **Variables .env** | Local apunta a localhost | Crear `.env.supabase` con credenciales | 🔴 P0 |
| **Dashboard Grafana** | Métrica obsoleta | Verificar `session_active_total` | 🟡 P1 |
| **Índices performance** | Básicos | Añadir índices específicos Supabase | 🟡 P1 |

*P0 solo si multi-tenant en producción; P1 si single-tenant inicial.

---

## 🛠️ FASE 1: PREPARACIÓN (2-3 horas)

### 1.1. Crear Proyecto Supabase

```bash
# 1. Ir a https://supabase.com/dashboard
# 2. New Project:
#    - Name: agente-hotelero-staging (o -prod)
#    - Region: South America (São Paulo) - sa-east-1
#    - Plan: Pro ($25/mes) - incluye backups, PITR
#    - Database Password: [generar seguro - 32 caracteres]
```

**Guardar credenciales**:
```bash
# Anotar en gestor de secretos (1Password, Bitwarden, etc.):
PROJECT_REF=xxxxx
DB_PASSWORD=yyyyy
ANON_KEY=zzzzz
SERVICE_ROLE_KEY=wwwww
```

### 1.2. Configurar Redis Externo (Upstash - RECOMENDADO)

```bash
# 1. Ir a https://upstash.com/
# 2. Crear cuenta (GitHub OAuth)
# 3. Create Database:
#    - Name: agente-hotelero-redis
#    - Region: South America (São Paulo)
#    - Type: Regional (más barato que Global)
#    - Eviction: allkeys-lru
```

**Obtener URL**:
```bash
# Dashboard → Database → Redis Connect
REDIS_URL=rediss://default:[password]@sa-east-1-xxxxx.upstash.io:6379
```

**Alternativa - Redis Cloud**:
```bash
# Si prefieres Redis Cloud: https://redis.com/try-free/
# Ventajas: SLA 99.99%, soporte enterprise
# Costo: desde $5/mes
```

### 1.3. Crear `.env.supabase`

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

cat > .env.supabase << 'EOF'
# ============================================================================
# SUPABASE STAGING - Variables de Entorno
# ============================================================================

# Environment
ENVIRONMENT=staging
DEBUG=false
USE_SUPABASE=true

# Database (Supabase PostgreSQL 15)
POSTGRES_URL=postgresql+asyncpg://postgres.[REF]:[DB_PASSWORD]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
DATABASE_URL=${POSTGRES_URL}

# Alembic (para migraciones)
ALEMBIC_DB_URL=${POSTGRES_URL}

# Redis (Upstash)
REDIS_URL=rediss://default:[REDIS_PASSWORD]@sa-east-1-xxxxx.upstash.io:6379

# Pool de conexiones (auto-ajustado por settings.py)
# No necesitas configurar POSTGRES_POOL_SIZE - se detecta automáticamente

# PMS (Mock para staging inicial)
PMS_TYPE=mock
PMS_BASE_URL=http://localhost:8080

# Observabilidad (local - sin cambios)
PROMETHEUS_URL=http://localhost:9090
GRAFANA_ADMIN_PASSWORD=[cambiar]

# Tracing (local Jaeger)
OTLP_ENDPOINT=http://jaeger:4317
TRACE_SAMPLING_RATE=0.1  # 10% en staging

# Secrets (cambiar todos)
SECRET_KEY=[generar con: openssl rand -hex 32]
WHATSAPP_ACCESS_TOKEN=[tu token Meta]
WHATSAPP_VERIFY_TOKEN=[generar aleatorio]
GMAIL_APP_PASSWORD=[app password Gmail]
PMS_API_KEY=[si usas PMS real]

# Multi-tenancy
TENANCY_DYNAMIC_ENABLED=true

# Feature Flags
# (Redis fallback a defaults si no disponible)

EOF
```

**Reemplazar placeholders**:
```bash
# Editar .env.supabase y reemplazar:
# [REF] → tu project ref de Supabase
# [DB_PASSWORD] → password de Supabase
# [REDIS_PASSWORD] → password de Upstash
# [cambiar] → valores reales de secrets
```

### 1.4. Validar Variables

```bash
# Script de validación (ya existe)
python scripts/validate_env.py --env-file .env.supabase
```

---

## 🔄 FASE 2: MIGRACIÓN (2-3 horas)

### 2.1. Ejecutar Migraciones Alembic

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

# 1. Cargar variables de Supabase
export $(cat .env.supabase | xargs)

# 2. Verificar conexión
psql "$POSTGRES_URL" -c "SELECT version();"
# Debe mostrar: PostgreSQL 15.x

# 3. Ejecutar migraciones
poetry run alembic upgrade head

# Verificar migraciones aplicadas:
psql "$POSTGRES_URL" -c "SELECT version_num FROM alembic_version;"
```

**Salida esperada**:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial, initial schema
INFO  [alembic.runtime.migration] Running upgrade 0001_initial -> 0002_add_tenants, multi-tenancy
INFO  [alembic.runtime.migration] Running upgrade 0002_add_tenants -> 0003_add_lock_audit, lock audit
INFO  [alembic.runtime.migration] Running upgrade 0003_add_lock_audit -> 0004_add_dlq, dead letter queue
```

### 2.2. Habilitar Extensiones PostgreSQL

```bash
# Conectar al SQL Editor de Supabase Dashboard
# https://supabase.com/dashboard/project/[REF]/sql

# Ejecutar:
```

```sql
-- Extensiones requeridas
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;  -- Query performance
CREATE EXTENSION IF NOT EXISTS pgcrypto;            -- Encryption
CREATE EXTENSION IF NOT EXISTS pg_trgm;             -- Fuzzy search (opcional)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";         -- UUID generation

-- Verificar
SELECT extname, extversion FROM pg_extension WHERE extname IN (
  'pg_stat_statements', 'pgcrypto', 'pg_trgm', 'uuid-ossp'
);
```

### 2.3. Crear Datos Iniciales

```bash
# Opción A: Script Python (recomendado)
python scripts/seed_supabase_minimal.py --env-file .env.supabase

# Opción B: SQL directo
psql "$POSTGRES_URL" << 'EOF'
-- Tenant default
INSERT INTO tenants (tenant_id, name, status, created_at)
VALUES ('default', 'Hotel Default', 'active', NOW())
ON CONFLICT (tenant_id) DO NOTHING;

-- Usuario admin inicial (ajustar email/password)
INSERT INTO users (email, hashed_password, role, tenant_id, is_active)
VALUES (
  'admin@hotel.example.com',
  crypt('ChangeMe123!', gen_salt('bf')),  -- bcrypt hash
  'admin',
  'default',
  true
)
ON CONFLICT (email) DO NOTHING;
EOF
```

### 2.4. Crear Índices de Performance

```sql
-- Conectar a Supabase SQL Editor

-- Índices para tenant resolution (crítico)
CREATE INDEX IF NOT EXISTS idx_tenant_user_identifiers_identifier 
  ON tenant_user_identifiers(identifier);
  
CREATE INDEX IF NOT EXISTS idx_tenant_user_identifiers_tenant_id 
  ON tenant_user_identifiers(tenant_id);

-- Índices para lock service
CREATE INDEX IF NOT EXISTS idx_lock_audit_resource_id 
  ON lock_audit(resource_id);
  
CREATE INDEX IF NOT EXISTS idx_lock_audit_acquired_at 
  ON lock_audit(acquired_at DESC);

-- Índices para DLQ
CREATE INDEX IF NOT EXISTS idx_dlq_permanent_failures_channel 
  ON dlq_permanent_failures(channel);
  
CREATE INDEX IF NOT EXISTS idx_dlq_permanent_failures_created_at 
  ON dlq_permanent_failures(created_at DESC);

-- Índices para usuarios
CREATE INDEX IF NOT EXISTS idx_users_tenant_id 
  ON users(tenant_id) WHERE is_active = true;

-- Verificar índices creados
SELECT schemaname, tablename, indexname 
FROM pg_indexes 
WHERE schemaname = 'public' 
ORDER BY tablename, indexname;
```

### 2.5. Habilitar RLS (Row Level Security)

**Solo si multi-tenant en producción** (P0). Si single-tenant inicial, posponer a P1.

```sql
-- 1. Habilitar RLS en tablas multi-tenant
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_user_identifiers ENABLE ROW LEVEL SECURITY;
ALTER TABLE lock_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE dlq_permanent_failures ENABLE ROW LEVEL SECURITY;

-- 2. Crear políticas (ejemplo para 'users')
CREATE POLICY tenant_isolation_users ON users
  FOR ALL
  USING (
    tenant_id = current_setting('app.current_tenant_id', TRUE)::TEXT
    OR current_setting('app.current_tenant_id', TRUE) IS NULL  -- Permite queries sin tenant
  );

-- Replicar para otras tablas...
-- (Ver sección 2.6 para lista completa)
```

### 2.6. Middleware SET LOCAL (si RLS habilitado)

**Archivo**: `app/core/middleware.py`

Añadir nuevo middleware **después** de `correlation_id_middleware`:

```python
@app.middleware("http")
async def set_tenant_context_middleware(request: Request, call_next):
    """
    Set tenant context for Row Level Security.
    
    IMPORTANTE: Solo activo si RLS está habilitado en Supabase.
    Si no usas RLS, este middleware no hace nada.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    
    if tenant_id and settings.use_supabase:
        # Inyectar tenant_id en sesión PostgreSQL para RLS
        from app.core.database import AsyncSessionFactory
        from sqlalchemy import text
        
        async with AsyncSessionFactory() as session:
            try:
                await session.execute(
                    text("SET LOCAL app.current_tenant_id = :tid"),
                    {"tid": tenant_id}
                )
            except Exception as e:
                logger.warning(
                    "set_tenant_context_failed",
                    tenant_id=tenant_id,
                    error=str(e)
                )
    
    response = await call_next(request)
    return response
```

**Registrar en `app/main.py`**:
```python
# Después de correlation_id_middleware
app.middleware("http")(set_tenant_context_middleware)
```

---

## ✅ FASE 3: VALIDACIÓN (1-2 horas)

### 3.1. Health Checks

```bash
# 1. Levantar aplicación con Supabase
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

# Cargar .env.supabase
export $(cat .env.supabase | xargs)

# Iniciar FastAPI
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8002

# 2. Verificar health endpoints (otra terminal)
curl http://localhost:8002/health/live
# Esperado: {"status": "healthy"}

curl http://localhost:8002/health/ready
# Esperado: {"status": "ready", "dependencies": {"postgres": true, "redis": true}}
```

### 3.2. Tests de Integración

```bash
# Suite específica Supabase (si existe)
pytest tests/integration/test_supabase_*.py -vv

# Tests generales de database
pytest tests/integration/test_database.py -vv

# Tests de tenant resolution
pytest tests/unit/test_dynamic_tenant_service.py -vv
```

### 3.3. Flujo End-to-End

```bash
# Test de mensaje completo (WhatsApp mock → orchestrator → respuesta)
curl -X POST http://localhost:8002/api/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "5491112345678",
            "text": {"body": "Hola, necesito disponibilidad para este fin de semana"},
            "timestamp": "1700000000"
          }]
        }
      }]
    }]
  }'

# Verificar en logs:
# - Tenant resuelto correctamente
# - Query a Supabase exitoso
# - Respuesta generada
```

### 3.4. Métricas y Observabilidad

```bash
# 1. Verificar métricas Prometheus
curl http://localhost:8002/metrics | grep -E "(postgres|redis|tenant)"

# Buscar:
# - postgres_connections_active
# - redis_cache_hits_total
# - tenant_resolution_total

# 2. Grafana dashboards
# http://localhost:3000
# Verificar:
# - Agente Overview → panel de DB queries
# - Session Metrics → sesiones activas
```

### 3.5. Script de Validación Automatizado

```bash
# Script de validación completo
./scripts/validate_supabase_setup.sh

# O manualmente:
python scripts/validate_supabase_schema.py --check-indexes --check-rls
```

---

## 📊 FASE 4: MONITOREO Y OPTIMIZACIÓN (30 min)

### 4.1. Configurar Alertas Supabase

```bash
# Supabase Dashboard → Settings → Billing
# Configurar alertas:
# - Database size > 7GB (80% del límite Plan Pro)
# - Bandwidth > 200GB/mes
# - API requests > 1M/día
```

### 4.2. Validar PITR (Point-in-Time Recovery)

```bash
# Supabase Dashboard → Database → Backups
# Verificar:
# ✅ Daily backups enabled
# ✅ PITR window: 7 días (Plan Pro)

# Test de restore (STAGING ONLY):
# 1. Crear restore point manual
# 2. Modificar datos de prueba
# 3. Restore desde punto anterior
# 4. Validar datos restaurados
```

### 4.3. Optimización de Queries

```sql
-- Analizar queries lentas
SELECT 
  calls,
  total_exec_time / 1000 as total_time_s,
  mean_exec_time / 1000 as mean_time_s,
  LEFT(query, 100) as query_preview
FROM pg_stat_statements
WHERE calls > 100
ORDER BY total_exec_time DESC
LIMIT 20;

-- Si encuentras queries lentas:
-- 1. Añadir índices específicos
-- 2. Revisar uso de joins/subqueries
-- 3. Considerar vistas materializadas
```

---

## 🔥 ROLLBACK PLAN (si algo falla)

### Escenario 1: Migración Falla

```bash
# 1. Volver a configuración local
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

# 2. Restaurar .env original
cp .env.backup .env

# 3. Levantar stack local
docker-compose up -d postgres redis

# 4. Aplicar migraciones locales
poetry run alembic upgrade head

# 5. Reiniciar app
docker-compose restart agente-api
```

### Escenario 2: Performance Issues

```bash
# 1. Ajustar pool de conexiones manualmente
# En .env.supabase:
POSTGRES_POOL_SIZE=5
POSTGRES_MAX_OVERFLOW=2

# 2. Habilitar logs de queries lentas
# Supabase Dashboard → Database → Settings
# Log min duration: 1000ms

# 3. Analizar con pg_stat_statements (ver sección 4.3)
```

### Escenario 3: Costos Inesperados

```bash
# 1. Revisar uso actual
# Supabase Dashboard → Settings → Usage

# 2. Reducir bandwidth:
# - Implementar cache adicional (Redis)
# - Reducir polling frequency
# - Optimizar queries (menos SELECT *)

# 3. Downgrade temporal a Free tier
# (solo si <500MB DB y <2GB bandwidth)
```

---

## 💰 ANÁLISIS DE COSTOS (Actualizado)

### Desglose Mensual - Staging

| Servicio | Plan | Costo |
|----------|------|-------|
| Supabase | Pro | $25 |
| Upstash Redis | Free tier | $0 |
| **TOTAL** | | **$25/mes** |

### Desglose Mensual - Producción

| Servicio | Plan | Costo Estimado |
|----------|------|----------------|
| Supabase | Pro | $25 |
| Upstash Redis | Pay-as-you-go (~1M req/mes) | $10-15 |
| **TOTAL** | | **$35-40/mes** |

### Comparativa

| Opción | Costo/mes | Pros | Contras |
|--------|-----------|------|---------|
| **Docker local** | $0 | Gratis, control total | No escalable, sin backups |
| **AWS EC2 + RDS** | $80-150 | Control total, VPC | Gestión manual, caro |
| **Supabase + Upstash** | $35-40 | Backups, PITR, escalable | Redis externo |
| **Railway** | $20-60 | Deploy auto, Redis incluido | Límites free tier |

**Recomendación**: Supabase + Upstash para staging/producción.

---

## 🚨 RIESGOS Y MITIGACIONES (Actualizado)

### 🔴 CRÍTICOS (P0)

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| **Redis no disponible** | Media | Alto | Upstash free tier ($0) + fallback a defaults feature flags |
| **Credenciales expuestas** | Baja | Crítico | `.env.supabase` en `.gitignore`, secretos en gestor |
| **Migraciones fallan** | Baja | Alto | Backup de Supabase antes de `alembic upgrade` |

### 🟡 IMPORTANTES (P1)

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| **Queries lentas** | Media | Medio | Índices adicionales + `pg_stat_statements` |
| **Costos inesperados** | Media | Medio | Alertas billing + monitoring uso |
| **RLS mal configurado** | Baja | Alto | Tests específicos multi-tenant |

### 🟢 MENORES (P2-P3)

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| **Downtime Supabase** | Muy baja | Bajo | SLA 99.9% Plan Pro + fallback local |
| **Latencia región** | Baja | Bajo | Región sa-east-1 (São Paulo) cercana |

---

## 📚 DOCUMENTACIÓN ADICIONAL

### Scripts Útiles

```bash
# Backup manual de Supabase
./scripts/backup-restore.sh --backup --supabase

# Validar índices
python scripts/validate_indexes.sh

# Monitorear conexiones
python scripts/monitor_connections.py --supabase

# Test de carga (k6)
k6 run scripts/load-test-supabase.js
```

### Logs y Debugging

```bash
# Logs de Supabase (últimas 100 líneas)
# Dashboard → Database → Logs

# Logs de aplicación con contexto Supabase
docker logs agente-api | grep -i "supabase\|postgres\|tenant"

# Verificar pool de conexiones
psql "$POSTGRES_URL" -c "
  SELECT count(*) as active_connections 
  FROM pg_stat_activity 
  WHERE datname = 'postgres';
"
```

---

## ✅ CHECKLIST FINAL DE MIGRACIÓN

### Pre-Migración
- [ ] Proyecto Supabase creado (Plan Pro, región sa-east-1)
- [ ] Upstash Redis configurado
- [ ] `.env.supabase` creado con credenciales reales
- [ ] Variables validadas con `validate_env.py`
- [ ] Backup local actual creado
- [ ] Rollback plan revisado

### Migración
- [ ] Migraciones ejecutadas: `alembic upgrade head`
- [ ] Tablas verificadas en Supabase SQL Editor
- [ ] Extensiones habilitadas (pg_stat_statements, pgcrypto, pg_trgm)
- [ ] Datos iniciales insertados (tenant, usuarios)
- [ ] Índices de performance creados
- [ ] RLS habilitado (si multi-tenant)
- [ ] Middleware SET LOCAL añadido (si RLS)

### Validación
- [ ] `/health/live` responde OK
- [ ] `/health/ready` muestra todas dependencias OK
- [ ] Tests de integración pasan
- [ ] Flujo end-to-end funciona
- [ ] Métricas Prometheus visibles
- [ ] Dashboards Grafana actualizados
- [ ] No hay queries lentas (>1s)

### Post-Migración
- [ ] Alertas Supabase configuradas
- [ ] Alertas billing configuradas
- [ ] PITR validado (restore test en staging)
- [ ] Monitoreo activo (24h mínimo)
- [ ] Documentación actualizada
- [ ] Equipo notificado de nueva infraestructura

---

## 🎯 PRÓXIMOS PASOS INMEDIATOS

1. **HOY** (15 minutos):
   - Crear proyecto Supabase staging
   - Obtener credenciales y guardar en gestor de secretos

2. **MAÑANA** (2-3 horas):
   - Configurar Upstash Redis
   - Crear `.env.supabase`
   - Ejecutar migraciones

3. **PRÓXIMA SEMANA** (1-2 horas):
   - Validación completa
   - Monitoreo 48h
   - Ajustes de performance si necesario

---

**Última Actualización**: 2025-11-15  
**Autor**: Equipo Técnico SST_AGENTE_HOTELERO  
**Versión**: 1.0 (Definitiva)
