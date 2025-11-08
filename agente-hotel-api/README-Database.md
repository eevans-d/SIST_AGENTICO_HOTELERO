# Database Optimization Guide

## Overview

This document provides comprehensive guidance on database optimization for the Agente Hotelero IA system, including index management, connection pooling, query optimization, and monitoring strategies.

## Table of Contents

1. [Database Architecture](#database-architecture)
2. [Index Management](#index-management)
3. [Connection Pooling](#connection-pooling)
4. [Query Optimization](#query-optimization)
5. [Monitoring & Analysis](#monitoring--analysis)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)
8. [Supabase Cost Control](#supabase-cost-control)

---

## Database Architecture

### PostgreSQL Configuration

**Version:** PostgreSQL 14+  
**Driver:** asyncpg (async)  
**ORM:** SQLAlchemy 2.0 (async)

### Core Tables

| Table | Purpose | Critical Indexes | Row Estimate |
|-------|---------|------------------|--------------|
| `sessions` | Guest conversation state | tenant_id, user_id, created_at | 10K-100K |
| `audit_logs` | Security audit trail | tenant_id+timestamp, user_id+timestamp, event_type+timestamp | 100K-1M+ |
| `locks` | Distributed locks | resource+tenant_id, acquired_at | 1K-10K |
| `tenants` | Multi-tenant configuration | id (PK) | 100-1000 |
| `tenant_user_identifiers` | User identity mapping | identifier_value+platform, tenant_id | 10K-100K |

### Schema Considerations

- **Multi-tenancy:** All tables include `tenant_id` for data isolation
- **Soft deletes:** Use `deleted_at` timestamp instead of hard deletes
- **Audit trails:** All mutations logged to `audit_logs`
- **Timestamps:** `created_at`, `updated_at` on all tables

---

## Index Management

### Validation Script

**Location:** `scripts/validate_indexes.sh`

**Purpose:** Comprehensive index analysis tool that identifies missing, unused, and duplicate indexes.

#### Usage

```bash
# Basic usage (uses .env for credentials)
./scripts/validate_indexes.sh

# Custom database connection
./scripts/validate_indexes.sh \
  --host db-prod.example.com \
  --port 5432 \
  --user admin \
  --password secret \
  --database agente_hotel_prod

# Custom output location
./scripts/validate_indexes.sh --output custom_report.json

# Show help
./scripts/validate_indexes.sh --help
```

#### Output

**Report Location:** `.playbook/index_analysis.json`

**Sections:**
1. **Summary:** Total indexes, unused count, missing count, duplicate count
2. **Existing Indexes:** Complete list with definitions
3. **Unused Indexes:** Indexes with `idx_scan = 0` (never used)
4. **Table Statistics:** Row counts, sizes, operation counts
5. **Missing Indexes:** Recommended composite indexes for critical tables
6. **Recommendations:** Prioritized action items (HIGH/MEDIUM/INFO)

#### Example Output

```json
{
  "summary": {
    "total_indexes": 15,
    "unused_indexes": 2,
    "missing_indexes": 3,
    "duplicate_indexes": 0,
    "tables_analyzed": 8
  },
  "missing_indexes": [
    {
      "table": "audit_logs",
      "columns": "tenant_id, timestamp",
      "index_name": "idx_audit_logs_tenant_id_timestamp",
      "sql": "CREATE INDEX idx_audit_logs_tenant_id_timestamp ON audit_logs(tenant_id, timestamp);",
      "priority": "high",
      "reason": "Frequently filtered/joined columns without composite index"
    }
  ],
  "recommendations": [
    {
      "severity": "high",
      "category": "missing_indexes",
      "message": "Add missing composite indexes on critical tables to improve query performance",
      "action": "Review missing_indexes section and execute CREATE INDEX statements"
    }
  ]
}
```

### Critical Indexes

#### 1. `sessions` Table

```sql
-- Multi-tenant session queries
CREATE INDEX idx_sessions_tenant_id_created_at ON sessions(tenant_id, created_at DESC);

-- User session lookup
CREATE INDEX idx_sessions_user_id_created_at ON sessions(user_id, created_at DESC);

-- Active session queries (if state column exists)
CREATE INDEX idx_sessions_state ON sessions(state) WHERE state = 'active';
```

**Rationale:**
- `tenant_id + created_at`: Most queries filter by tenant and sort by recency
- `user_id + created_at`: User-specific session history lookups
- Partial index on `state`: Only indexes active sessions, reduces index size

#### 2. `audit_logs` Table

```sql
-- Primary audit query pattern (tenant + time range)
CREATE INDEX idx_audit_logs_tenant_id_timestamp ON audit_logs(tenant_id, timestamp DESC);

-- User audit trail
CREATE INDEX idx_audit_logs_user_id_timestamp ON audit_logs(user_id, timestamp DESC);

-- Event type analysis
CREATE INDEX idx_audit_logs_event_type_timestamp ON audit_logs(event_type, timestamp DESC);

-- Severity-based alerting
CREATE INDEX idx_audit_logs_severity_timestamp ON audit_logs(severity, timestamp DESC) 
  WHERE severity IN ('critical', 'error');
```

**Rationale:**
- **Composite indexes:** Critical for pagination queries (see `get_audit_logs()` method)
- **DESC ordering:** Matches query ORDER BY for index-only scans
- **Partial index on severity:** High-severity events are rare, partial index is efficient

#### 3. `locks` Table

```sql
-- Distributed lock acquisition
CREATE INDEX idx_locks_resource_tenant_id ON locks(resource, tenant_id);

-- Lock expiration cleanup
CREATE INDEX idx_locks_acquired_at ON locks(acquired_at) WHERE released_at IS NULL;
```

**Rationale:**
- `resource + tenant_id`: Lookup pattern for lock acquisition
- Partial index on unreleased locks: Cleanup queries only scan active locks

#### 4. `tenant_user_identifiers` Table

```sql
-- Identity resolution (primary lookup)
CREATE INDEX idx_tenant_user_identifiers_value_platform ON tenant_user_identifiers(identifier_value, platform);

-- Tenant-specific user listing
CREATE INDEX idx_tenant_user_identifiers_tenant_id ON tenant_user_identifiers(tenant_id);
```

**Rationale:**
- `identifier_value + platform`: Used in dynamic tenant resolution (high frequency)
- `tenant_id`: Admin queries listing all users per tenant

### Index Maintenance

#### Drop Unused Indexes

```bash
# Identify unused indexes
./scripts/validate_indexes.sh

# Review unused_indexes section in output
# Example DROP statement:
DROP INDEX idx_old_unused_index;
```

**Warning:** Do NOT drop primary key indexes (`*_pkey`) or unique constraint indexes.

#### Monitor Index Size

```sql
-- Check index sizes
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC;
```

**Threshold:** Indexes >100MB should be reviewed for necessity.

---

## Connection Pooling

### Configuration

**Location:** `app/core/settings.py`

```python
class Settings(BaseSettings):
    postgres_pool_size: int = Field(default=10, description="SQLAlchemy pool size")
    postgres_max_overflow: int = Field(default=20, description="Max overflow connections")
    postgres_pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
```

**Total Capacity:** `pool_size + max_overflow = 10 + 20 = 30 connections`

### Monitoring Script

**Location:** `scripts/monitor_connections.py`

#### Usage

```bash
# Single analysis
python scripts/monitor_connections.py

# Continuous monitoring (10s interval, 60s duration)
python scripts/monitor_connections.py --watch

# Custom pool settings for analysis
python scripts/monitor_connections.py --pool-size 20 --max-overflow 40

# Alert on 80% threshold + export Prometheus metrics
python scripts/monitor_connections.py --threshold 80 --prometheus

# Custom credentials
python scripts/monitor_connections.py \
  --host db-prod \
  --user admin \
  --password secret \
  --database agente_hotel
```

#### Output

**Report Location:** `.playbook/connection_pool_report.json`

**Metrics:**
- `total_connections`: Current active + idle connections
- `active_connections`: Executing queries
- `idle_connections`: Available in pool
- `idle_in_transaction`: Connections with open transaction (leak indicator)
- `long_running_queries`: Queries >30s (configurable)
- `pool_utilization_percent`: `(total / capacity) * 100`
- `overflow_in_use`: Connections beyond base pool size

**Prometheus Metrics:** `.playbook/connection_pool_metrics.prom`

```
db_pool_active_connections 8
db_pool_idle_connections 12
db_pool_total_connections 20
db_pool_utilization_percent 66.67
db_pool_overflow 0
db_pool_long_running_queries 1
db_pool_idle_in_transaction 0
db_pool_size_configured 10
db_pool_max_overflow_configured 20
```

### Recommendations

#### 🚨 CRITICAL: Pool >90% Utilization

**Symptom:** `pool_utilization_percent > 90`

**Impact:** New connections will timeout, causing 500 errors

**Solution:**
1. Increase `postgres_pool_size` (e.g., 10 → 20)
2. Increase `postgres_max_overflow` (e.g., 20 → 40)
3. Deploy with `make docker-up`

**Example:**
```bash
# .env
POSTGRES_POOL_SIZE=20
POSTGRES_MAX_OVERFLOW=40
```

#### ⚠️ WARNING: Idle-in-Transaction Connections

**Symptom:** `idle_in_transaction > 3`

**Impact:** Connections holding locks, blocking other queries

**Root Cause:** Transactions not committed/rolled back properly

**Solution:**
1. Review code for missing `await session.commit()` or `await session.rollback()`
2. Add exception handling with rollback in service methods
3. Use context managers for automatic cleanup

**Example Fix:**
```python
# BAD: Transaction leak
async def create_session(data):
    async with AsyncSessionFactory() as session:
        new_session = Session(**data)
        session.add(new_session)
        # Missing commit!
        return new_session

# GOOD: Proper transaction handling
async def create_session(data):
    async with AsyncSessionFactory() as session:
        try:
            new_session = Session(**data)
            session.add(new_session)
            await session.commit()
            await session.refresh(new_session)
            return new_session
        except Exception as e:
            await session.rollback()
            raise
```

#### ⚠️ WARNING: Long-Running Queries

**Symptom:** `long_running_queries > 0` (>30s threshold)

**Impact:** Connection pool exhaustion, slow API responses

**Solution:**
1. Identify slow queries in connection pool report
2. Add missing indexes (use `validate_indexes.sh`)
3. Optimize N+1 queries with eager loading
4. Add LIMIT clauses to unbounded queries

**Example:**
```python
# BAD: N+1 query problem
sessions = await db.execute(select(Session).filter_by(tenant_id=tenant_id))
for session in sessions:
    user = await db.execute(select(User).filter_by(id=session.user_id))  # N queries!

# GOOD: Eager loading with joinedload
from sqlalchemy.orm import joinedload
sessions = await db.execute(
    select(Session)
    .options(joinedload(Session.user))
    .filter_by(tenant_id=tenant_id)
)  # Single query with JOIN
```

---

## Query Optimization

### Pagination Pattern

**Implementation:** `app/services/security/audit_logger.py::get_audit_logs()`

**Key Technique:** Subquery for count to avoid loading data twice

```python
async def get_audit_logs(
    self,
    tenant_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[AuditLog], int]:
    # Step 1: Count query (does not load rows)
    count_query = select(func.count()).select_from(AuditLog)
    if tenant_id:
        count_query = count_query.where(AuditLog.tenant_id == tenant_id)
    
    total = await session.scalar(count_query)
    
    # Step 2: Data query with LIMIT/OFFSET
    offset = (page - 1) * page_size
    data_query = (
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(page_size)
        .offset(offset)
    )
    
    results = await session.execute(data_query)
    return results.scalars().all(), total
```

**Benefits:**
- Prevents OOM on large datasets (100K+ rows)
- Efficient for frontend pagination UI
- Enables "total pages" calculation

### Query Performance Checklist

- [ ] **Indexed columns:** All WHERE/JOIN columns have indexes
- [ ] **Limit results:** Use LIMIT for unbounded queries
- [ ] **Eager loading:** Use `joinedload()` to avoid N+1
- [ ] **Projection:** Select specific columns, not `SELECT *`
- [ ] **Pagination:** Use offset/limit for large result sets
- [ ] **Avoid LIKE '%term%':** Use full-text search or trigram indexes
- [ ] **Connection reuse:** Use pool, don't create new connections

---

## Monitoring & Analysis

### Redis Cache Analysis

**Script:** `scripts/analyze_redis_cache.py`

**Purpose:** Audit Redis cache efficiency and identify optimization opportunities

#### Usage

```bash
python scripts/analyze_redis_cache.py
python scripts/analyze_redis_cache.py --host redis-prod --port 6379 --password secret
python scripts/analyze_redis_cache.py --output custom_report.json
```

**Output:** `.playbook/redis_analysis.json`

**Key Metrics:**
- **Hit Ratio:** `hits / (hits + misses)` (target: >70%)
- **TTL Statistics:** Avg/min/max TTL per pattern
- **Keys Without TTL:** Risk of infinite growth
- **Memory Usage:** Bytes per pattern
- **Evictions:** Keys evicted due to maxmemory

**Patterns Analyzed:**
- `availability:*` (hotel room availability cache)
- `session:*` (user sessions)
- `lock:*` (distributed locks)
- `rate_limit:*` (rate limiting counters)
- `circuit_breaker:*` (circuit breaker states)
- `tenant:*` (tenant configurations)
- `pms_cache:*` (PMS API response cache)

### Prometheus Metrics

**Endpoint:** `http://localhost:8000/metrics`

**Key Metrics:**
- `db_pool_utilization_percent`: Connection pool usage
- `db_pool_active_connections`: Currently executing queries
- `pms_api_latency_seconds`: PMS API response time (histogram)
- `pms_circuit_breaker_state`: 0=closed, 1=open, 2=half-open
- `redis_hit_ratio`: Cache hit percentage

**Grafana Dashboards:** See `README-Infra.md` for setup

---

## Best Practices

### 1. Always Use Indexes for Filters

❌ **Bad:**
```python
# No index on user_id
sessions = await db.execute(
    select(Session).where(Session.user_id == user_id)
)
```

✅ **Good:**
```python
# Index: CREATE INDEX idx_sessions_user_id ON sessions(user_id);
sessions = await db.execute(
    select(Session).where(Session.user_id == user_id)
)
```

### 2. Paginate Large Result Sets

❌ **Bad:**
```python
# Loads ALL audit logs into memory (OOM risk)
all_logs = await db.execute(select(AuditLog))
```

✅ **Good:**
```python
# Pagination prevents OOM
logs, total = await audit_logger.get_audit_logs(page=1, page_size=50)
```

### 3. Use Connection Pooling

❌ **Bad:**
```python
# Creates new connection every request
async with asyncpg.connect(dsn) as conn:
    result = await conn.fetch("SELECT * FROM sessions")
```

✅ **Good:**
```python
# Reuses pooled connections
async with AsyncSessionFactory() as session:
    result = await session.execute(select(Session))
```

### 4. Close Transactions Properly

❌ **Bad:**
```python
async with AsyncSessionFactory() as session:
    session.add(new_record)
    # Missing commit - transaction leak!
```

✅ **Good:**
```python
async with AsyncSessionFactory() as session:
    try:
        session.add(new_record)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
```

### 5. Monitor Database Performance

**Weekly Tasks:**
- [ ] Run `validate_indexes.sh` to check for missing/unused indexes
- [ ] Run `monitor_connections.py --watch` to check pool utilization
- [ ] Review `.playbook/index_analysis.json` for recommendations
- [ ] Check Prometheus metrics for anomalies

**Monthly Tasks:**
- [ ] Review slow query logs (`pg_stat_statements`)
- [ ] Analyze table bloat and vacuum status
- [ ] Update index strategies based on query patterns
- [ ] Review connection pool size for production load

---

## Troubleshooting

### Issue: "Database connection pool exhausted"

**Symptoms:**
- 500 errors with "TimeoutError: QueuePool limit exceeded"
- `pool_utilization_percent > 90`

**Diagnosis:**
```bash
python scripts/monitor_connections.py
```

**Solutions:**
1. Increase pool size: `POSTGRES_POOL_SIZE=20` (default 10)
2. Increase max overflow: `POSTGRES_MAX_OVERFLOW=40` (default 20)
3. Fix connection leaks (check `idle_in_transaction`)
4. Optimize slow queries (check `long_running_queries`)

### Issue: "Query too slow"

**Symptoms:**
- API response time >2s
- `pms_api_latency_seconds P95 > 2.0`

**Diagnosis:**
```bash
# Check for missing indexes
./scripts/validate_indexes.sh

# Check active queries
python scripts/monitor_connections.py
```

**Solutions:**
1. Add missing indexes from `missing_indexes` report
2. Optimize N+1 queries with eager loading
3. Add LIMIT clauses to unbounded queries
4. Review `long_running_queries` in connection report

### Issue: "Out of Memory (OOM)"

**Symptoms:**
- API crashes with memory errors
- Large result sets loaded into memory

**Diagnosis:**
```python
# Check query result size
result = await db.execute(select(AuditLog))
print(f"Loaded {len(result.all())} rows")  # Too many?
```

**Solutions:**
1. Implement pagination (see `get_audit_logs()` example)
2. Use `yield_per()` for streaming large result sets
3. Add LIMIT clause to queries
4. Filter by date range to reduce result size

### Issue: "Redis cache not effective"

**Symptoms:**
- High PMS API latency despite caching
- Low hit ratio (<50%)

**Diagnosis:**
```bash
python scripts/analyze_redis_cache.py
```

**Solutions:**
1. Increase TTL for stable data (e.g., availability: 300s → 600s)
2. Precache frequently accessed data
3. Review invalidation logic (too aggressive?)
4. Check for keys without TTL (infinite growth risk)

---

## Related Documentation

- **Infrastructure Monitoring:** `README-Infra.md`
- **Operations Manual:** `docs/OPERATIONS_MANUAL.md`
- **API Documentation:** `README.md`
- **Connection Pool Monitoring:** `scripts/monitor_connections.py --help`
- **Index Validation:** `scripts/validate_indexes.sh --help`
- **Redis Analysis:** `scripts/analyze_redis_cache.py --help`

---

## Changelog

- **2025-10-14:** Initial version with index validation, connection pooling, and monitoring scripts
- **2025-11-07:** Added Supabase cost control section (pool downsizing, compose profile, workflow concurrency)

---

## Supabase Cost Control

Cuando se utiliza Supabase en lugar de Postgres local, el objetivo es minimizar conexiones y operaciones que generan consumo innecesario. Este sistema incluye ya varios guardarraíles; se describen aquí junto con pasos recomendados.

### 1. Activación explícita

Por defecto en desarrollo se usa Postgres local (perfil `local-db` del `docker-compose.dev.yml`). Para usar Supabase:

```bash
export USE_SUPABASE=true
export DATABASE_URL="postgresql+asyncpg://USER:PASS@aws-0-sa-east-1.pooler.supabase.com:6543/postgres?sslmode=require"
# Levanta sólo lo necesario (sin Postgres local):
docker compose -f docker-compose.dev.yml up agente-api redis
```

Si olvidas el perfil, no se arranca Postgres local porque tiene `profiles: [local-db]`.

### 2. Pool reducido automático

Al detectar `USE_SUPABASE=true` y dominio `supabase.co`, el sistema fuerza:

| Ajuste | Valor reducido |
|--------|----------------|
| `postgres_pool_size` | 2 |
| `postgres_max_overflow` | 2 |
| `debug` (SQL echo) | desactivado |

Esto evita mantener docenas de conexiones abiertas que sumarían a límites de la plataforma.

### 3. Timeouts preventivos

El motor SQLAlchemy aplica `statement_timeout=15s` y `idle_in_transaction_session_timeout=10s` para:

- Cortar consultas largas accidentales.
- Prevenir sesiones abiertas o transacciones olvidadas que consuman recursos.

### 4. Evitar ejecución repetitiva de schema

El workflow `Supabase Schema Ops` sólo se ejecuta manualmente (`workflow_dispatch`). Además:

- Configuración `concurrency` cancela ejecuciones previas si lanzas otra.
- `timeout-minutes: 20` evita jobs colgados.
- Añade confirmación explícita: exige flag `--yes` (ver script si se implementa) antes de aplicar el schema.

### 5. Prácticas recomendadas

| Situación | Recomendación |
|-----------|---------------|
| Alta frecuencia de pruebas | Usa Postgres local para tests de carga, no Supabase. |
| Scripts de migraciones masivas | Ejecuta en ventana única y monitorea conexiones (no lo dejes en loop). |
| Jobs de background | Unifica operaciones batch en una sola transacción corta. |
| Debug de SQL | Mantén `DEBUG=false` en Supabase para evitar spam de logs. |
| Reintentos de API | Limita reintentos de DB a 2 con backoff (no loops agresivos). |

### 6. Checklist antes de usar Supabase

```text
☐ USE_SUPABASE=true exportado
☐ DATABASE_URL incluye sslmode=require
☐ Pool reducido aplicado (2/2) en logs de arranque
☐ Sin procesos en loop que ejecuten consultas cada <1s
☐ Sin verbose SQL echo
☐ Concurrency activa en workflow schema
```

### 7. Monitoreo ligero

Para controlar conexiones activas sin overhead:

```sql
SELECT state, COUNT(*)
FROM pg_stat_activity
WHERE application_name LIKE 'hotel_agent_%'
GROUP BY state;
```

Objetivo en Supabase (dev/staging): <= 4 conexiones totales (incluyendo proceso principal + overflow breve).

### 8. Qué NO hacer

- No ejecutar migraciones en loop cron cada pocos minutos.
- No mantener workers vacíos conectados permanentemente si no procesan cola.
- No activar profiling continuo (p.ej. logs de todas las consultas) en Supabase.

### 9. Próximos pasos sugeridos

Para más ahorro futuro:

1. Implementar auto-cierre de sesiones inactivas > 5min (middleware opcional).
2. Cachear lecturas meta (tenants, flags) con TTL más largo (actual 300s → 900s).
3. Agrupar operaciones de escritura en lotes pequeños (bulk insert con COPY si aplica).

---
