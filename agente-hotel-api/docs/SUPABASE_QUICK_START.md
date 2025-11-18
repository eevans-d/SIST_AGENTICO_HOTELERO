# ⚡ SUPABASE QUICK START - Checklist Ejecutable

**Tiempo estimado total**: 4-6 horas  
**Prerequisito**: Tener cuenta en Supabase y Upstash

---

## 📋 FASE 1: SETUP INICIAL (30 min)

### Paso 1: Crear Proyecto Supabase

```bash
# 1. Ir a: https://supabase.com/dashboard
# 2. Click "New Project"
# 3. Configuración:
#    - Organization: [tu org]
#    - Name: agente-hotelero-staging
#    - Database Password: [GENERAR SEGURO - 32 caracteres]
#    - Region: South America (São Paulo)
#    - Pricing Plan: Pro ($25/mes)
```

**✅ Checkpoint**: Anotar credenciales en gestor de secretos:
```
PROJECT_REF: xxxxx
DB_PASSWORD: yyyyy  
ANON_KEY: zzzzz
SERVICE_ROLE_KEY: wwwww
CONNECTION_STRING: postgresql://postgres.[REF]:[PASS]@...
```

### Paso 2: Crear Redis Upstash

```bash
# 1. Ir a: https://upstash.com/
# 2. Crear cuenta con GitHub
# 3. "Create Database"
#    - Name: agente-hotelero-redis
#    - Type: Regional
#    - Region: South America (São Paulo)
#    - Eviction: allkeys-lru
#    - TLS: Enabled
```

**✅ Checkpoint**: Copiar URL Redis:
```
REDIS_URL: rediss://default:[PASSWORD]@sa-east-1-xxxxx.upstash.io:6379
```

### Paso 3: Crear `.env.supabase`

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

# Copiar template
cp .env.example .env.supabase

# Editar manualmente y reemplazar:
nano .env.supabase
```

**Variables críticas a configurar**:
```bash
# OBLIGATORIO cambiar:
ENVIRONMENT=staging
USE_SUPABASE=true
POSTGRES_URL=postgresql+asyncpg://postgres.[REF]:[DB_PASSWORD]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
REDIS_URL=rediss://default:[REDIS_PASSWORD]@sa-east-1-xxxxx.upstash.io:6379
SECRET_KEY=[generar con: openssl rand -hex 32]

# Opcional ajustar:
PMS_TYPE=mock
TRACE_SAMPLING_RATE=0.1
DEBUG=false
```

---

## 🔄 FASE 2: MIGRACIÓN (1-2 horas)

### Paso 4: Ejecutar Migraciones

```bash
cd /home/eevan/SIST_AGENTICO_HOTELERO/agente-hotel-api

# Cargar variables
export $(cat .env.supabase | grep -v '^#' | xargs)

# Verificar conexión
psql "$POSTGRES_URL" -c "SELECT version();"

# Ejecutar migraciones
poetry run alembic upgrade head
```

**✅ Checkpoint**: Verificar tablas creadas:
```bash
psql "$POSTGRES_URL" -c "\dt"
# Debe listar: tenants, users, tenant_user_identifiers, lock_audit, dlq_permanent_failures, alembic_version
```

### Paso 5: Habilitar Extensiones

```bash
# Ir a Supabase Dashboard → SQL Editor
# Ejecutar este SQL:
```

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verificar
SELECT extname FROM pg_extension WHERE extname IN (
  'pg_stat_statements', 'pgcrypto', 'pg_trgm', 'uuid-ossp'
);
```

### Paso 6: Crear Índices

```sql
-- En Supabase SQL Editor:

-- Tenant resolution (CRÍTICO)
CREATE INDEX IF NOT EXISTS idx_tenant_user_identifiers_identifier 
  ON tenant_user_identifiers(identifier);
CREATE INDEX IF NOT EXISTS idx_tenant_user_identifiers_tenant_id 
  ON tenant_user_identifiers(tenant_id);

-- Lock service
CREATE INDEX IF NOT EXISTS idx_lock_audit_resource_id ON lock_audit(resource_id);
CREATE INDEX IF NOT EXISTS idx_lock_audit_acquired_at ON lock_audit(acquired_at DESC);

-- DLQ
CREATE INDEX IF NOT EXISTS idx_dlq_permanent_failures_channel ON dlq_permanent_failures(channel);
CREATE INDEX IF NOT EXISTS idx_dlq_permanent_failures_created_at ON dlq_permanent_failures(created_at DESC);

-- Users
CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users(tenant_id) WHERE is_active = true;
```

### Paso 7: Datos Iniciales

```bash
# Opción A: Script Python
python scripts/seed_supabase_minimal.py

# Opción B: SQL manual
psql "$POSTGRES_URL" << 'EOF'
INSERT INTO tenants (tenant_id, name, status, created_at)
VALUES ('default', 'Hotel Default', 'active', NOW())
ON CONFLICT (tenant_id) DO NOTHING;
EOF
```

---

## ✅ FASE 3: VALIDACIÓN (30-60 min)

### Paso 8: Health Checks

```bash
# Terminal 1: Iniciar app con Supabase
export $(cat .env.supabase | grep -v '^#' | xargs)
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8002

# Terminal 2: Probar endpoints
curl http://localhost:8002/health/live
# Esperado: {"status":"healthy"}

curl http://localhost:8002/health/ready | jq .
# Esperado: {"status":"ready","dependencies":{"postgres":true,"redis":true}}
```

**✅ Checkpoint**: Ambos endpoints responden 200 OK.

### Paso 9: Test Básico de DB

```bash
# Verificar conexión desde Python
python -c "
import asyncio
from app.core.database import AsyncSessionFactory
from sqlalchemy import text

async def test():
    async with AsyncSessionFactory() as session:
        result = await session.execute(text('SELECT COUNT(*) FROM tenants'))
        count = result.scalar()
        print(f'✅ Tenants count: {count}')

asyncio.run(test())
"
```

### Paso 10: Test de Redis

```bash
# Verificar Redis Upstash
redis-cli -u "$REDIS_URL" PING
# Esperado: PONG

# Test desde Python
python -c "
import redis
import os
r = redis.from_url(os.getenv('REDIS_URL'))
r.set('test', 'ok')
print('✅ Redis:', r.get('test').decode())
"
```

---

## 📊 FASE 4: MONITOREO (15-30 min)

### Paso 11: Configurar Alertas Supabase

```bash
# 1. Dashboard → Settings → Billing → Usage alerts
# 2. Configurar:
#    - Database size > 7GB (aviso)
#    - Bandwidth > 200GB/mes (aviso)
#    - Database size > 8GB (crítico)
```

### Paso 12: Verificar Métricas Prometheus

```bash
# Con la app corriendo, verificar métricas:
curl http://localhost:8002/metrics | grep -E "(postgres|redis|tenant)" | head -20

# Buscar:
# postgres_connections_active
# redis_cache_hits_total
# tenant_resolution_total
```

### Paso 13: Validación Final

```bash
# Script de validación automatizado
./scripts/validate_supabase_setup.sh

# O manualmente:
python scripts/validate_supabase_schema.py
```

---

## 🎯 CHECKLIST FINAL

Marca cada item al completarlo:

### Setup
- [ ] Proyecto Supabase creado (Plan Pro)
- [ ] Upstash Redis configurado
- [ ] `.env.supabase` creado y validado
- [ ] Credenciales guardadas en gestor seguro

### Migración
- [ ] `alembic upgrade head` ejecutado sin errores
- [ ] Tablas verificadas en Supabase SQL Editor
- [ ] Extensiones habilitadas
- [ ] Índices creados
- [ ] Datos iniciales insertados

### Validación
- [ ] `/health/live` → 200 OK
- [ ] `/health/ready` → 200 OK (postgres: true, redis: true)
- [ ] Conexión PostgreSQL desde Python OK
- [ ] Conexión Redis desde Python OK
- [ ] Métricas Prometheus visibles

### Monitoreo
- [ ] Alertas Supabase configuradas
- [ ] Grafana dashboards funcionando
- [ ] Sin queries lentas (verificar `pg_stat_statements`)

---

## 🚨 TROUBLESHOOTING RÁPIDO

### Error: "Connection refused" en Postgres

```bash
# Verificar URL correcta
echo $POSTGRES_URL

# Debe contener:
# - postgres.[REF]
# - aws-0-sa-east-1.pooler.supabase.com:6543
# - postgresql+asyncpg:// (no postgresql://)

# Si falla, probar sin pooler:
POSTGRES_URL_DIRECT="postgresql+asyncpg://postgres.[REF]:[PASS]@db.[REF].supabase.co:5432/postgres"
```

### Error: "SSL required" en Redis

```bash
# Asegurar que REDIS_URL empieza con rediss:// (con doble 's')
echo $REDIS_URL | grep "^rediss://"

# Si usa redis:// (sin TLS), corregir:
REDIS_URL="rediss://..."
```

### Error: Migraciones fallan

```bash
# Ver detalle del error
poetry run alembic upgrade head --verbose

# Rollback a versión anterior
poetry run alembic downgrade -1

# Verificar estado
poetry run alembic current
```

---

## 📞 SIGUIENTE PASO

Una vez completado este checklist:

1. **Dejar correr 24-48 horas** en staging
2. **Monitorear costos** en Supabase Dashboard
3. **Revisar performance** en Grafana
4. **Documentar issues** encontrados

Luego repetir proceso para **producción** con ajustes según aprendizajes de staging.

---

**Última Actualización**: 2025-11-15  
**Tiempo de ejecución estimado**: 4-6 horas  
**Nivel de dificultad**: Intermedio
