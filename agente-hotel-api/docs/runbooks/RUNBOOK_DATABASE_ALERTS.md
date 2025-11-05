# Runbook: Database & Connection Pool Alerts

## Overview

Este runbook proporciona guías de diagnóstico y resolución para las alertas relacionadas con la base de datos PostgreSQL y el connection pool de SQLAlchemy.

---

## DatabasePoolExhaustionCritical

**Severity:** 🚨 CRITICAL  
**Threshold:** `db_pool_utilization_percent > 90%` por 1 minuto  
**Dashboard:** [Database & PMS Performance](http://localhost:3000/d/database-pms-performance) - Panel 1

### Síntomas

- Alta utilización del connection pool (>90%)
- Requests fallando con `TimeoutError: QueuePool limit exceeded`
- Aumento en latencia de API
- Errores 5xx correlacionados

### Diagnóstico Rápido

```bash
# 1. Ver estado actual del pool
python scripts/monitor_connections.py

# 2. Verificar conexiones activas
python scripts/monitor_connections.py --threshold 90

# 3. Revisar métricas Prometheus
curl -s 'http://localhost:9090/api/v1/query?query=db_pool_utilization_percent'
```

**Buscar en logs:**
```bash
# Errores de timeout en pool
docker compose logs agente-api | grep -i "QueuePool"

# Conexiones lentas
docker compose logs agente-api | grep -i "slow query"
```

### Causas Comunes

1. **Pool Size Insuficiente:** Carga de producción excede capacidad configurada
2. **Connection Leaks:** Conexiones no liberadas (idle-in-transaction)
3. **Slow Queries:** Queries lentos bloqueando conexiones
4. **Spike de Tráfico:** Aumento repentino de requests

### Resolución

#### Solución Inmediata (< 5 minutos)

1. **Incrementar Pool Size:**
   ```bash
   # Editar .env
   POSTGRES_POOL_SIZE=20  # default: 10
   POSTGRES_MAX_OVERFLOW=40  # default: 20
   
   # Reiniciar servicio
   docker compose restart agente-api
   ```

2. **Verificar transaction leaks:**
   ```bash
   python scripts/monitor_connections.py | jq '.connections[] | select(.state == "idle in transaction")'
   ```
   
   Si hay leaks, reiniciar servicio como medida temporal:
   ```bash
   docker compose restart agente-api
   ```

#### Solución a Mediano Plazo (< 1 hora)

1. **Analizar Slow Queries:**
   ```bash
   python scripts/monitor_connections.py --watch
   # Observar long_running_queries
   ```
   
   Optimizar queries identificados:
   - Agregar índices faltantes (ver `validate_indexes.sh`)
   - Implementar paginación
   - Optimizar N+1 queries con eager loading

2. **Revisar Connection Leaks:**
   ```sql
   -- Conectar a PostgreSQL
   psql -U agente_user -d agente_hotel
   
   -- Ver conexiones idle in transaction
   SELECT pid, usename, state, query_start, state_change, query
   FROM pg_stat_activity
   WHERE state = 'idle in transaction'
   ORDER BY state_change;
   ```
   
   Fix en código:
   ```python
   # Agregar try/finally en servicios
   async def my_service_method():
       async with AsyncSessionFactory() as session:
           try:
               # ... operations ...
               await session.commit()
           except Exception:
               await session.rollback()
               raise
   ```

3. **Ajustar Pool Basado en Capacidad:**
   
   Fórmula recomendada:
   ```
   pool_size = (num_cores * 2) + effective_spindle_count
   
   Ejemplo servidor 4 cores, SSD (spindle=0):
   pool_size = (4 * 2) + 0 = 8-12
   max_overflow = pool_size * 2 = 16-24
   ```

### Prevención

- **Monitoreo Continuo:** Revisar dashboard semanalmente
- **Capacity Planning:** Incrementar pool antes de llegar a 75%
- **Code Review:** Validar uso correcto de session.commit()/rollback()
- **Load Testing:** Simular carga de producción en staging

### Escalamiento

- Notificar a: Team Lead, DevOps
- Ventana de resolución: < 15 minutos
- Si no resuelve: Escalar a Database Admin

---

## DatabasePoolExhaustionWarning

**Severity:** ⚠️ WARNING  
**Threshold:** `db_pool_utilization_percent > 75%` por 5 minutos

### Diagnóstico

Similar a CRITICAL pero con más tiempo de respuesta.

### Acción

1. Revisar tendencia en Grafana (últimas 24h)
2. Planificar incremento de pool si tendencia es creciente
3. Ejecutar `monitor_connections.py` para baseline
4. Agendar revisión semanal de métricas

### Prevención

- Incrementar pool proactivamente si utilización promedio >60%
- Revisar crecimiento de usuarios/tráfico
- Planificar escalamiento horizontal si necesario

---

## DatabaseLongRunningQueries

**Severity:** ⚠️ WARNING  
**Threshold:** `db_pool_long_running_queries >= 3` por 2 minutos  
**Dashboard:** [Database & PMS Performance](http://localhost:3000/d/database-pms-performance) - Panel 3

### Síntomas

- 3 o más queries ejecutándose por >30 segundos
- Aumento en latencia P95/P99 de API
- Connection pool utilization alto
- Posibles timeouts en frontend

### Diagnóstico Rápido

```bash
# Ver queries lentos activos
python scripts/monitor_connections.py

# Detalles específicos
python scripts/monitor_connections.py --output /tmp/pool_report.json
cat /tmp/pool_report.json | jq '.connections[] | select(.duration_seconds > 30)'
```

**Query PostgreSQL directa:**
```sql
SELECT 
    pid,
    usename,
    query_start,
    now() - query_start AS duration,
    state,
    LEFT(query, 100) AS query_preview
FROM pg_stat_activity
WHERE state = 'active'
  AND now() - query_start > interval '30 seconds'
ORDER BY duration DESC;
```

### Causas Comunes

1. **Missing Indexes:** Queries sin índices realizan full table scans
2. **N+1 Queries:** Múltiples queries en loop
3. **Unbounded Queries:** SELECT sin LIMIT en tablas grandes
4. **Locks:** Query bloqueado esperando lock de otra transacción
5. **Cold Cache:** Primera ejecución sin cache warming

### Resolución

#### Identificar Query Problemático

```bash
# Ver query completo del PID más lento
psql -U agente_user -d agente_hotel -c "
SELECT query FROM pg_stat_activity WHERE pid = <PID>;
"
```

#### Solución por Tipo

**1. Missing Index:**
```bash
# Ejecutar análisis de índices
./scripts/validate_indexes.sh

# Ver recomendaciones
cat .playbook/index_analysis.json | jq '.missing_indexes'

# Crear índice recomendado
psql -U agente_user -d agente_hotel -c "
CREATE INDEX idx_audit_logs_tenant_timestamp ON audit_logs(tenant_id, timestamp DESC);
"
```

**2. N+1 Query:**
```python
# MAL: N+1
sessions = await db.execute(select(Session).filter_by(tenant_id=tenant_id))
for session in sessions:
    user = await db.execute(select(User).filter_by(id=session.user_id))  # N queries!

# BIEN: Eager loading
from sqlalchemy.orm import joinedload
sessions = await db.execute(
    select(Session)
    .options(joinedload(Session.user))
    .filter_by(tenant_id=tenant_id)
)
```

**3. Unbounded Query:**
```python
# MAL: Sin LIMIT
all_logs = await db.execute(select(AuditLog))  # Carga 100K+ rows!

# BIEN: Con paginación
logs, total = await audit_logger.get_audit_logs(page=1, page_size=50)
```

**4. Lock Blocker:**
```sql
-- Ver queries bloqueados y bloqueadores
SELECT 
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_query,
    blocking_activity.query AS blocking_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks 
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;

-- Opción: Matar query bloqueador (CUIDADO!)
-- SELECT pg_terminate_backend(<blocking_pid>);
```

#### Acción Inmediata

Si query está bloqueando producción:
```bash
# Matar query específico (solo si es seguro)
psql -U agente_user -d agente_hotel -c "SELECT pg_cancel_backend(<PID>);"

# Si no funciona, terminar proceso (más agresivo)
psql -U agente_user -d agente_hotel -c "SELECT pg_terminate_backend(<PID>);"
```

### Prevención

- **Validar índices semanalmente:** `./scripts/validate_indexes.sh`
- **Code review:** Revisar uso de LIMIT, eager loading
- **Query timeout:** Configurar `statement_timeout` en PostgreSQL
- **Monitoring:** Dashboard semanal de P95 query duration

### Escalamiento

- Notificar a: Backend Team
- Ventana de resolución: < 30 minutos
- Si persiste: Escalar a DBA para análisis de EXPLAIN ANALYZE

---

## DatabaseIdleInTransaction

**Severity:** ⚠️ WARNING  
**Threshold:** `db_pool_idle_in_transaction > 3` por 3 minutos  
**Dashboard:** [Database & PMS Performance](http://localhost:3000/d/database-pms-performance) - Panel 2

### Síntomas

- 3+ conexiones en estado `idle in transaction`
- Conexiones holding locks sin actividad
- Otros queries bloqueados esperando locks
- Pool utilization artificialmente alto

### Diagnóstico

```bash
# Ver idle in transaction connections
python scripts/monitor_connections.py | jq '.connections[] | select(.state == "idle in transaction")'

# Query PostgreSQL
psql -U agente_user -d agente_hotel -c "
SELECT 
    pid,
    usename,
    state,
    state_change,
    now() - state_change AS idle_duration,
    query
FROM pg_stat_activity
WHERE state = 'idle in transaction'
ORDER BY state_change;
"
```

### Causa Raíz

**Transaction Leak:** Transacción iniciada pero no committed ni rolled back.

**Código problemático:**
```python
# MAL: No commit ni rollback
async def bad_function():
    async with AsyncSessionFactory() as session:
        session.add(new_record)
        # Falta: await session.commit()
        return new_record  # Session queda idle in transaction!
```

### Resolución

#### Acción Inmediata

```bash
# Ver conexiones con >5 minutos idle
psql -U agente_user -d agente_hotel -c "
SELECT pid, usename, now() - state_change AS duration
FROM pg_stat_activity
WHERE state = 'idle in transaction'
  AND now() - state_change > interval '5 minutes';
"

# Matar conexiones viejas (>10 min)
psql -U agente_user -d agente_hotel -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle in transaction'
  AND now() - state_change > interval '10 minutes';
"
```

#### Fix en Código

Patrón correcto:
```python
# BIEN: Proper transaction handling
async def good_function():
    async with AsyncSessionFactory() as session:
        try:
            session.add(new_record)
            await session.commit()
            await session.refresh(new_record)
            return new_record
        except Exception as e:
            await session.rollback()
            logger.error(f"Transaction failed: {e}")
            raise
```

#### Buscar Transaction Leaks

```bash
# Buscar funciones sin commit/rollback
cd app/services
grep -r "AsyncSessionFactory" . | while read line; do
    file=$(echo $line | cut -d: -f1)
    if ! grep -q "session.commit()" "$file" && ! grep -q "session.rollback()" "$file"; then
        echo "Possible leak in: $file"
    fi
done
```

### Prevención

- **Code Template:** Usar template con try/except/rollback
- **Linting:** Agregar regla custom para detectar leaks
- **Testing:** Tests que validen session.commit() en servicios
- **Timeout:** Configurar `idle_in_transaction_session_timeout` en PostgreSQL

```sql
-- PostgreSQL config (postgresql.conf)
idle_in_transaction_session_timeout = 300000  -- 5 minutos en ms
```

### Escalamiento

- Notificar a: Backend Team Lead
- Ventana de resolución: < 1 hora
- Acción: Code review completo de servicios DB

---

## DatabasePoolOverflowHigh

**Severity:** ⚠️ WARNING  
**Threshold:** `db_pool_overflow > 15` por 5 minutos  
**Dashboard:** [Database & PMS Performance](http://localhost:3000/d/database-pms-performance) - Panel 9

### Síntomas

- Alto uso de overflow connections (>15)
- Pool base insuficiente para carga actual
- Latencia incrementada en peak hours
- Connection creation overhead

### Diagnóstico

```bash
# Ver métricas de overflow
curl -s 'http://localhost:9090/api/v1/query?query=db_pool_overflow' | jq '.data.result[0].value[1]'

# Ver utilización total
python scripts/monitor_connections.py
```

### Interpretación

**Overflow = Conexiones - Pool Base**

Ejemplo:
- Pool Size: 10
- Max Overflow: 20
- Total Connections: 25
- **Overflow in use: 15** ← Alerta!

Esto indica que el pool base (10) es constantemente insuficiente.

### Resolución

#### Ajustar Pool Size

```bash
# Calcular pool size óptimo
# Observar avg_connections en dashboard (últimas 24h)
avg_connections = 25
recommended_pool_size = avg_connections * 1.2  # +20% headroom
# = 30

# Actualizar .env
POSTGRES_POOL_SIZE=30
POSTGRES_MAX_OVERFLOW=20

# Reiniciar
docker compose restart agente-api
```

#### Validar Cambio

```bash
# Monitorear por 1 hora
python scripts/monitor_connections.py --watch --interval 60 --duration 3600

# Verificar overflow bajó
curl -s 'http://localhost:9090/api/v1/query?query=db_pool_overflow'
```

### Prevención

- **Baseline Mensual:** Revisar avg utilization cada mes
- **Growth Planning:** Incrementar pool 20% antes de llegar a límite
- **Alerting:** Alerta preventiva si overflow_avg_24h > 10

### Escalamiento

- Notificar a: DevOps
- Ventana de resolución: < 24 horas (no urgente)
- Acción: Capacity planning meeting

---

## HighErrorRate5xx

**Severity:** 🚨 CRITICAL  
**Threshold:** `error_rate_5xx > 5%` por 5 minutos  
**Dashboard:** [Database & PMS Performance](http://localhost:3000/d/database-pms-performance) - Panel 10

### Síntomas

- >5% de requests retornando 5xx
- Usuarios reportando errores
- Posible outage parcial

### Diagnóstico Multi-Layer

#### 1. Correlacionar con Pool
```bash
# Ver si pool está exhausted
curl -s 'http://localhost:9090/api/v1/query?query=db_pool_utilization_percent'

# Si >90%, el problema es pool exhaustion
```

#### 2. Verificar Circuit Breaker
```bash
# Ver estado PMS circuit breaker
curl -s 'http://localhost:9090/api/v1/query?query=pms_circuit_breaker_state'

# Si state=1 (OPEN), PMS no disponible
```

#### 3. Revisar Logs
```bash
# Errores recientes
docker compose logs agente-api --tail=100 | grep "ERROR\|CRITICAL"

# Stack traces
docker compose logs agente-api | grep -A 20 "Traceback"
```

### Resolución por Causa

**A. Pool Exhaustion:**
→ Ver runbook `DatabasePoolExhaustionCritical`

**B. PMS Circuit Breaker Open:**
```bash
# Verificar PMS upstream
curl -i http://qloapps/api/health

# Si PMS caído, esperar recovery automático (30s)
# Monitorear: cb_state debería pasar a HALF-OPEN → CLOSED
```

**C. Application Error:**
```bash
# Identificar endpoint problemático
curl -s 'http://localhost:9090/api/v1/query?query=sum(rate(http_requests_total{status_code=~"5.."}[5m])) by (endpoint)'

# Revisar código del endpoint
# Rollback si deploy reciente
```

### Escalamiento

- Notificar: On-Call Engineer, Team Lead
- Severidad: P1 (Outage)
- Ventana de resolución: < 10 minutos
- Acción: Incidente postmortem si duración >15 min

---

## Herramientas de Diagnóstico

### Scripts Disponibles

1. **monitor_connections.py** - Connection pool analysis
   ```bash
   python scripts/monitor_connections.py
   python scripts/monitor_connections.py --watch --threshold 80
   ```

2. **validate_indexes.sh** - Index validator
   ```bash
   ./scripts/validate_indexes.sh
   cat .playbook/index_analysis.json | jq '.missing_indexes'
   ```

3. **analyze_redis_cache.py** - Cache performance
   ```bash
   python scripts/analyze_redis_cache.py
   ```

### Prometheus Queries

```promql
# Pool utilization trend (1h)
db_pool_utilization_percent[1h]

# Active connections by state
db_pool_active_connections
db_pool_idle_connections
db_pool_idle_in_transaction

# Long queries count
db_pool_long_running_queries

# Error rate correlation
(sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))) * 100
```

### Grafana Dashboards

- **Database & PMS Performance:** http://localhost:3000/d/database-pms-performance
- **Agente Overview:** http://localhost:3000/d/agente-overview
- **SLO Health:** http://localhost:3000/d/slo-health

---

## Escalation Matrix

| Alert | Severity | Initial Response | Escalate To | Escalate If |
|-------|----------|------------------|-------------|-------------|
| DatabasePoolExhaustionCritical | 🚨 CRITICAL | On-Call Engineer | Team Lead | Not resolved in 15min |
| DatabaseLongRunningQueries | ⚠️ WARNING | Backend Developer | DBA | Query >5min or recurring |
| DatabaseIdleInTransaction | ⚠️ WARNING | Backend Developer | Team Lead | >10 connections or recurring |
| DatabasePoolOverflowHigh | ⚠️ WARNING | DevOps | N/A | Not urgent (24h window) |
| HighErrorRate5xx | 🚨 CRITICAL | On-Call Engineer | CTO | Not resolved in 10min |

---

## Post-Incident Actions

Después de resolver alerta CRITICAL:

1. **Documentar:**
   - Timestamp inicio/fin
   - Causa raíz
   - Pasos de resolución
   - Impacto en usuarios

2. **Postmortem (si duración >15min):**
   - Runbook meeting dentro de 48h
   - Identificar gaps en monitoreo
   - Crear tickets de mejora

3. **Prevención:**
   - Actualizar runbook con nuevos learnings
   - Agregar alertas preventivas
   - Mejorar documentación

4. **Comunicación:**
   - Notificar a stakeholders
   - Actualizar status page
   - Compartir learnings en Slack/Email

---

## Referencias

- **Database Optimization Guide:** README-Database.md
- **Infrastructure Docs:** README-Infra.md
- **Monitoring Scripts:** scripts/ directory
- **Grafana Dashboards:** http://localhost:3000
- **Prometheus Alerts:** http://localhost:9090/alerts
- **AlertManager:** http://localhost:9093
