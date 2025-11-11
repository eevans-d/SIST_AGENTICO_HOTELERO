# 🎯 BLUEPRINT v2.0 DEFINITIVO - AGENTE HOTELERO IA

**Fecha Creación**: 2025-11-10  
**Versión**: 2.0 (Re-Meta Análisis Exhaustivo)  
**Objetivo**: Optimización "0 Kilómetros" con ROI máximo  
**Estado Inicial REAL**: 22% coverage | 43/1279 tests loadable (3.4%) | 8.9/10 readiness  
**Estado Objetivo REALISTA**: 50-60% coverage | 80%+ tests passing | 9.5/10 readiness  
**Duración Total Estimada**: 15-23 horas  

---

## 📊 ANÁLISIS CRÍTICO DEL ESTADO REAL

### ✅ Fortalezas Validadas
- ✅ **Seguridad**: 0 CRITICAL CVEs (python-jose 3.5.0)
- ✅ **Linting**: 0 errores Ruff + gitleaks
- ✅ **Infraestructura**: 7 servicios Docker Compose operacionales
- ✅ **Secrets**: Auto-generación segura (.env.staging)
- ✅ **Observabilidad**: Stack completo (Prometheus/Grafana/Jaeger/AlertManager)
- ✅ **Arquitectura**: Patrones sólidos (Circuit Breaker, Caching, Locks)
- ✅ **Documentación**: 104 archivos .md (base sólida)
- ✅ **Automatización**: 80+ scripts operacionales
- ✅ **CI/CD**: 7 workflows configurados
- ✅ **Dashboards**: 20 dashboards Grafana existentes

### ❌ Problemas Críticos REALES

| Problema | Métrica Actual | Impacto | Prioridad |
|----------|----------------|---------|-----------|
| **Tests No Cargan** | 43/1279 (3.4%) | 🔴 BLOQUEANTE | P0 |
| **Coverage Real** | 22% (no 31%) | 🔴 CRÍTICO | P0 |
| **Errores Colección** | 3 errores bloquean 1236 tests | 🔴 CRÍTICO | P0 |
| **Tests Passing** | Desconocido (solo 43 cargan) | 🟠 ALTO | P1 |
| **Performance Baseline** | No establecido | 🟡 MEDIO | P2 |
| **SQLAlchemy Deprecation** | declarative_base() | 🟡 MEDIO | P2 |

### 🎯 Métricas Clave - ANTES vs DESPUÉS

| Métrica | Actual | Objetivo v2.0 | Gap | Effort |
|---------|--------|---------------|-----|--------|
| **Tests Collectables** | 43/1279 (3.4%) | 1200+/1279 (95%+) | +2700% | 2h |
| **Test Coverage** | 22% | 50-60% | +38pp | 6h |
| **Tests Passing** | ? (solo 43 cargan) | 80%+ | TBD | 5h |
| **P95 Latency** | No medido | <300ms | TBD | 3h |
| **CVEs CRITICAL** | 0 | 0 | ✅ | 0h |
| **CI/CD Funcional** | Parcial | Completo | - | 2h |
| **Dashboards Operacionales** | 20 creados | 10 validados | - | 2h |
| **Readiness Score** | 8.9/10 | 9.5/10 | +0.6 | 3h |

---

## 🗺️ ARQUITECTURA v2.0 - 6 FASES OPTIMIZADAS

**Cambios vs v1.0**:
- ❌ Eliminados 4 módulos de bajo ROI (Deployment, Security, Code Quality redundantes)
- ✅ Consolidados 10 → 6 fases (Database+Performance, Resilience+Validation)
- ✅ Nueva **FASE 0: QUICK WINS** (1-2h, alto ROI)
- ✅ Objetivos realistas basados en datos reales
- ✅ Dependencies explícitas entre fases
- ✅ Estimaciones precisas por tarea

```
┌─────────────────────────────────────────────────────────────────────┐
│  FASE 0: QUICK WINS (1-2h) ← EMPEZAR AQUÍ                          │
│  ├── Fix 3 collection errors                    [30 min]           │
│  ├── Configure pytest markers                   [15 min]           │
│  ├── Generate real coverage report              [15 min]           │
│  └── Fix SQLAlchemy deprecation                 [30 min]           │
│  → OUTPUT: 1200+ tests collectables, coverage report, 0 warnings   │
└─────────────────────────────────────────────────────────────────────┘
                            ↓ BLOCKING
┌─────────────────────────────────────────────────────────────────────┐
│  FASE 1: FOUNDATION (4-6h) ← CRÍTICO                                │
│  ├── Repair P0 tests (orchestrator, pms, sessions, locks) [3h]     │
│  ├── Increase coverage to 50%+                  [2-3h]             │
│  └── CI/CD basic validation                     [1h]               │
│  → OUTPUT: 80% tests passing, 50%+ coverage, CI green              │
└─────────────────────────────────────────────────────────────────────┘
                            ↓ RECOMMENDED
┌─────────────────────────────────────────────────────────────────────┐
│  FASE 2: DATABASE & PERFORMANCE (3-5h)                              │
│  ├── Establish performance baseline             [1h]               │
│  ├── Identify & fix N+1 queries                 [2h]               │
│  ├── Create strategic indexes                   [1-2h]             │
│  └── Optimize hot path queries                  [1h]               │
│  → OUTPUT: P95 <300ms, queries <100ms, indexes deployed            │
└─────────────────────────────────────────────────────────────────────┘
                            ↓ OPTIONAL (good to have)
┌─────────────────────────────────────────────────────────────────────┐
│  FASE 3: OBSERVABILITY (2-3h)                                       │
│  ├── Validate 20 existing dashboards            [1h]               │
│  ├── Complete missing metrics                   [1h]               │
│  └── Configure critical alerts                  [1h]               │
│  → OUTPUT: 10 operational dashboards, alerts configured            │
└─────────────────────────────────────────────────────────────────────┘
                            ↓ OPTIONAL
┌─────────────────────────────────────────────────────────────────────┐
│  FASE 4: VALIDATION & RESILIENCE (3-4h)                             │
│  ├── E2E critical tests (reservation flow)      [2h]               │
│  ├── Circuit breaker validation                 [1h]               │
│  └── Stress testing (100-200 RPS)               [1-2h]             │
│  → OUTPUT: E2E passing, resilience validated, stress test OK       │
└─────────────────────────────────────────────────────────────────────┘
                            ↓ PRE-PRODUCTION
┌─────────────────────────────────────────────────────────────────────┐
│  FASE 5: PRODUCTION READINESS (2-3h)                                │
│  ├── Pre-flight checklist validation            [1h]               │
│  ├── Runbooks validation                        [1h]               │
│  └── Deployment smoke tests                     [1h]               │
│  → OUTPUT: 9.5/10 readiness, deployment successful                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 FASE 0: QUICK WINS (1-2 horas)

**Objetivo**: Desbloquear 1200+ tests y generar baseline real  
**ROI**: ⭐⭐⭐⭐⭐ (Máximo - Alto impacto, bajo esfuerzo)  
**Prioridad**: 🔴 P0 (BLOQUEANTE para todo lo demás)  
**Dependencies**: Ninguna

### T0.1 - Reparar Collection Errors (30 min)

**Problema Actual**: 3 errores bloquean 1236 tests
```bash
# Errores identificados:
1. tests/benchmarks/test_performance.py → 'benchmark' marker not configured
2. tests/incident/test_incident_response.py → incident_detector module missing
3. tests/performance/load_test.py → locust module not installed
```

**Acciones**:
```bash
# A) Configurar marker benchmark en pytest.ini
sed -i '/markers =/a\    benchmark: Benchmark performance tests' pytest.ini

# B) Comentar/skip tests de incident_detector (módulo no existe)
echo "@pytest.mark.skip(reason='incident_detector module not implemented')" \
  >> tests/incident/test_incident_response.py

# C) Instalar locust o skip load tests
poetry add --group dev locust || \
  pytest -k "not load_test" tests/

# D) Validar colección
pytest --collect-only tests/ 2>&1 | grep "collected"
```

**Criterios de Éxito**:
- [x] 0 collection errors
- [x] 1200+ tests collectables
- [x] Validar con: `pytest --collect-only tests/ --quiet`

**Output**: `.playbook/phase0/collection_fixed.txt`

---

### T0.2 - Generar Coverage Report Real (15 min)

**Problema**: Coverage report dice 31%, pero real es 22%

**Acciones**:
```bash
# Generar coverage con tests actuales (solo los que cargan)
pytest --cov=app --cov-report=html --cov-report=term tests/unit tests/integration

# Analizar módulos sin coverage
coverage report --show-missing | tee .playbook/phase0/coverage_baseline.txt

# Identificar archivos críticos sin tests
find app/services -name "*.py" | while read f; do
  coverage annotate "$f" 2>/dev/null | grep -c "^>" || echo "$f: NO COVERAGE"
done > .playbook/phase0/services_without_tests.txt
```

**Criterios de Éxito**:
- [x] Coverage report HTML generado
- [x] Coverage real documentado (22%)
- [x] Lista de módulos sin tests identificada

**Output**: 
- `htmlcov/index.html` (visual)
- `.playbook/phase0/coverage_baseline.txt` (metrics)
- `.playbook/phase0/services_without_tests.txt` (gaps)

---

### T0.3 - Fix SQLAlchemy Deprecation (30 min)

**Problema**: `declarative_base()` deprecation warning en 100+ tests

**Acciones**:
```python
# Buscar archivos usando declarative_base
grep -r "from sqlalchemy.ext.declarative import declarative_base" app/ tests/

# Reemplazar con DeclarativeBase (SQLAlchemy 2.0)
# app/models/base.py (ejemplo)
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Actualizar imports en modelos
sed -i 's/from sqlalchemy.ext.declarative import declarative_base/from app.models.base import Base/' \
  app/models/*.py tests/conftest.py
```

**Criterios de Éxito**:
- [x] 0 deprecation warnings en test output
- [x] All models inherit from DeclarativeBase
- [x] Validar con: `pytest tests/unit -W error::DeprecationWarning`

**Output**: Commit `refactor(db): migrate to SQLAlchemy 2.0 DeclarativeBase`

---

### T0.4 - Configurar Pytest Markers (15 min)

**Problema**: Markers no documentados, tests mal categorizados

**Acciones**:
```ini
# pytest.ini - Actualizar sección markers
[pytest]
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (require services)
    e2e: End-to-end tests (slow, full stack)
    performance: Performance benchmarks
    security: Security tests
    deployment: Deployment validation
    benchmark: Benchmark tests (locust, load)
    chaos: Chaos engineering tests
    critical: Critical path tests (P0)
    slow: Slow tests (>5s execution)
```

**Criterios de Éxito**:
- [x] All markers documented in pytest.ini
- [x] Tests properly tagged
- [x] Validar con: `pytest --markers | grep -E "unit|integration|e2e"`

**Output**: Commit `test(config): document all pytest markers`

---

## 🏗️ FASE 1: FOUNDATION (4-6 horas)

**Objetivo**: 50%+ coverage, 80%+ tests passing, CI green  
**ROI**: ⭐⭐⭐⭐⭐ (Crítico)  
**Prioridad**: 🔴 P0  
**Dependencies**: FASE 0 completa

### T1.1 - Reparar Tests Críticos P0 (3 horas)

**Scope**: Orchestrator, PMS Adapter, Session Manager, Lock Service

#### T1.1.1 - Orchestrator Tests (1h)

**Archivos**:
- `tests/unit/test_orchestrator_basic.py`
- `tests/integration/test_orchestrator_circuit_breaker.py`

**Estrategia**:
```python
# 1. Verificar fixtures
@pytest.fixture
async def orchestrator(mock_pms_adapter, mock_session_manager, mock_lock_service):
    return Orchestrator(
        pms_adapter=mock_pms_adapter,
        session_manager=mock_session_manager,
        lock_service=mock_lock_service
    )

# 2. Test básico
async def test_orchestrator_process_availability_intent(orchestrator):
    message = UnifiedMessage(
        sender_id="test_user",
        channel="whatsapp",
        text="Disponibilidad para este fin de semana",
        timestamp=datetime.now()
    )
    
    response = await orchestrator.process_message(message)
    
    assert response["status"] == "success"
    assert "availability" in response["data"]

# 3. Test circuit breaker
async def test_orchestrator_fallback_when_pms_unavailable(orchestrator_with_cb_open):
    # Circuit breaker abierto, debe usar fallback
    response = await orchestrator_with_cb_open.process_message(message)
    
    assert response["status"] == "degraded"
    assert response["fallback_used"] is True
```

**Criterios de Éxito**:
- [x] 10/10 orchestrator tests passing
- [x] Coverage orchestrator.py >70%
- [x] Intent handlers tested (availability, reservation, checkout)

---

#### T1.1.2 - PMS Adapter Tests (1h)

**Archivos**:
- `tests/unit/test_pms_circuit_breaker_state_flow.py`
- `tests/unit/test_circuit_breaker.py`

**Estrategia**:
```python
# Test state transitions
async def test_circuit_breaker_transitions():
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30)
    
    # CLOSED → OPEN (5 failures)
    for _ in range(5):
        await cb.call(async_failing_function)
    assert cb.state == CircuitBreakerState.OPEN
    
    # OPEN → HALF_OPEN (after timeout)
    await asyncio.sleep(30)
    assert cb.state == CircuitBreakerState.HALF_OPEN
    
    # HALF_OPEN → CLOSED (1 success)
    await cb.call(async_successful_function)
    assert cb.state == CircuitBreakerState.CLOSED

# Test caching
async def test_pms_adapter_cache_hit():
    adapter = PMSAdapter(cache_ttl=300)
    
    # First call (cache miss)
    result1 = await adapter.check_availability("2025-12-01", "2025-12-03")
    
    # Second call (cache hit)
    result2 = await adapter.check_availability("2025-12-01", "2025-12-03")
    
    assert result1 == result2
    assert adapter.metrics["cache_hits"] == 1
```

**Criterios de Éxito**:
- [x] Circuit breaker state machine tested
- [x] Cache hit/miss logic validated
- [x] Metrics tracked correctly

---

#### T1.1.3 - Session Manager Tests (30 min)

**Archivos**:
- `tests/unit/test_session_manager_ttl.py`
- `tests/unit/test_session_cleanup.py`

**Estrategia**:
```python
async def test_session_ttl_enforcement():
    manager = SessionManager(ttl=3600)  # 1 hour
    
    # Create session
    session = await manager.create_session("user123", {"intent": "availability"})
    
    # Mock time passage (61 min)
    with freeze_time(datetime.now() + timedelta(minutes=61)):
        # Should be expired
        assert await manager.get_session("user123") is None

async def test_cleanup_removes_expired():
    manager = SessionManager()
    
    # Create 10 sessions, 5 expired
    # ...
    
    await manager.cleanup_expired_sessions()
    
    assert manager.metrics["active_sessions"] == 5
```

**Criterios de Éxito**:
- [x] TTL enforcement validated
- [x] Cleanup task tested
- [x] Metrics accuracy verified

---

#### T1.1.4 - Lock Service Tests (30 min)

**Archivos**:
- `tests/unit/test_lock_service.py`
- `tests/unit/test_lock_audit_trail.py`

**Estrategia**:
```python
async def test_distributed_lock_atomicity():
    lock_service = LockService()
    
    # Acquire lock
    lock1 = await lock_service.acquire_lock("room_101", "user1", ttl=60)
    assert lock1.acquired is True
    
    # Conflict detection
    lock2 = await lock_service.acquire_lock("room_101", "user2", ttl=60)
    assert lock2.acquired is False
    assert lock2.conflict_detected is True
    
    # Release
    await lock_service.release_lock(lock1.lock_id)
    
    # Now user2 can acquire
    lock3 = await lock_service.acquire_lock("room_101", "user2", ttl=60)
    assert lock3.acquired is True

async def test_audit_trail_created():
    # Verify audit entries created for acquire, release, conflict
    events = await lock_service.get_audit_trail("room_101")
    assert len(events) == 3
    assert events[0].action == "acquire"
    assert events[1].action == "conflict"
    assert events[2].action == "release"
```

**Criterios de Éxito**:
- [x] Lock atomicity validated
- [x] Conflict detection works
- [x] Audit trail complete

---

### T1.2 - Aumentar Coverage a 50%+ (2-3 horas)

**Estrategia**: Escribir tests mínimos para módulos críticos sin coverage

#### Módulos Prioritarios (Coverage Actual → Target):

| Módulo | Actual | Target | Tests Needed | Effort |
|--------|--------|--------|--------------|--------|
| `orchestrator.py` | 35% | 70% | 15 | 1h |
| `pms_adapter.py` | 40% | 75% | 10 | 45min |
| `session_manager.py` | 50% | 80% | 8 | 30min |
| `message_gateway.py` | 30% | 60% | 10 | 45min |
| `feature_flag_service.py` | 45% | 70% | 6 | 30min |
| `lock_service.py` | 60% | 85% | 5 | 30min |

**Total Tests Nuevos**: ~54 tests | **Total Effort**: 2-3h

#### Template de Test Rápido:

```python
# tests/unit/test_MODULE_coverage.py
"""Coverage extension tests for MODULE."""

import pytest
from app.services.MODULE import SomeService

class TestModuleCoverage:
    """Tests to increase coverage for critical paths."""
    
    async def test_happy_path(self):
        """Test main success path."""
        service = SomeService()
        result = await service.main_method(valid_input)
        assert result.success is True
    
    async def test_error_handling(self):
        """Test error paths."""
        service = SomeService()
        with pytest.raises(ServiceError):
            await service.main_method(invalid_input)
    
    async def test_edge_cases(self):
        """Test boundary conditions."""
        service = SomeService()
        # Empty input
        result = await service.main_method(None)
        assert result is not None
```

**Criterios de Éxito**:
- [x] Coverage global ≥ 50%
- [x] Coverage servicios críticos ≥ 70%
- [x] 54+ nuevos tests implementados
- [x] Validar con: `pytest --cov=app --cov-report=term tests/`

---

### T1.3 - CI/CD Validation (1 hora)

**Objetivo**: Garantizar que CI ejecuta tests y reporta coverage

#### T1.3.1 - Verificar Workflows Existentes

```bash
# Listar workflows
ls -la .github/workflows/

# Revisar workflow de tests
cat .github/workflows/tests.yml

# Buscar coverage reporting
grep -r "coverage" .github/workflows/
```

#### T1.3.2 - Configurar Quality Gates

```yaml
# .github/workflows/tests.yml
name: Tests & Coverage

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install --all-extras
      
      - name: Run tests with coverage
        run: |
          poetry run pytest --cov=app --cov-report=xml --cov-report=term
      
      - name: Check coverage threshold
        run: |
          poetry run coverage report --fail-under=50
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: false
```

**Criterios de Éxito**:
- [x] CI ejecuta tests en cada push
- [x] Coverage report generado
- [x] Quality gate enforced (50% min)
- [x] Badge en README actualizado

**Output**: 
- `.github/workflows/tests.yml` actualizado
- Badge: `[![Coverage](https://codecov.io/gh/USER/REPO/branch/main/graph/badge.svg)](https://codecov.io/gh/USER/REPO)`

---

## ⚡ FASE 2: DATABASE & PERFORMANCE (3-5 horas)

**Objetivo**: P95 <300ms, queries optimizadas, índices estratégicos  
**ROI**: ⭐⭐⭐⭐ (Alto)  
**Prioridad**: 🟠 P1  
**Dependencies**: FASE 1 completa (tests passing para validar optimizaciones)

### T2.1 - Establecer Performance Baseline (1 hora)

**Objetivo**: Métricas actuales sin load testing complejo

#### T2.1.1 - Instrumentar Endpoints Críticos

```python
# app/routers/webhooks.py
from prometheus_client import Histogram

webhook_latency = Histogram(
    'webhook_processing_seconds',
    'Webhook processing latency',
    ['endpoint', 'channel']
)

@app.post("/api/webhooks/whatsapp")
@webhook_latency.labels(endpoint='whatsapp', channel='whatsapp').time()
async def whatsapp_webhook(payload: WhatsAppWebhook):
    # ... existing code
```

#### T2.1.2 - Ejecutar Baseline Test (Simple)

```bash
# NO load testing (locust), usar wrk (simple)
# Instalar wrk si no existe
apt-get install wrk || brew install wrk

# Test básico: 100 requests, 10 conexiones concurrentes
wrk -t4 -c10 -d30s --latency http://localhost:8002/health/ready

# Analizar output
echo "P50, P75, P90, P95, P99 latencies" > .playbook/phase2/baseline_latency.txt
```

#### T2.1.3 - Analizar Queries Lentas

```python
# scripts/analyze_slow_queries.py
import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionFactory

async def find_slow_queries():
    async with AsyncSessionFactory() as session:
        # PostgreSQL: queries >100ms
        result = await session.execute(text("""
            SELECT 
                query,
                mean_exec_time,
                calls,
                total_exec_time
            FROM pg_stat_statements
            WHERE mean_exec_time > 100
            ORDER BY mean_exec_time DESC
            LIMIT 20;
        """))
        
        for row in result:
            print(f"{row.query[:80]}... | {row.mean_exec_time:.2f}ms | {row.calls} calls")

asyncio.run(find_slow_queries())
```

**Criterios de Éxito**:
- [x] Baseline latencies documentadas (P50, P95, P99)
- [x] Top 20 slow queries identified
- [x] Métricas en Prometheus funcionando

**Output**:
- `.playbook/phase2/baseline_latency.txt`
- `.playbook/phase2/slow_queries.txt`

---

### T2.2 - Optimizar Queries (2 horas)

#### T2.2.1 - Identificar N+1 Queries (30 min)

```python
# Enable SQLAlchemy logging
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Test endpoint y contar queries
# Ejemplo: GET /api/sessions/active debería ser 1 query, no N+1

# Buscar código sospechoso
grep -r "for.*in.*:" app/services/ | grep "await.*execute"
```

#### T2.2.2 - Implementar Eager Loading (1h)

```python
# ANTES (N+1 query)
sessions = await session.execute(select(Session))
for s in sessions:
    tenant = await session.execute(select(Tenant).where(Tenant.id == s.tenant_id))
    # ❌ 1 query inicial + N queries (uno por sesión)

# DESPUÉS (eager loading)
from sqlalchemy.orm import selectinload

sessions = await session.execute(
    select(Session).options(selectinload(Session.tenant))
)
# ✅ 2 queries totales (sessions + all tenants en batch)
```

#### T2.2.3 - Optimizar Queries Específicas (30 min)

```python
# Query lenta: Búsqueda de sesiones por sender_id + fecha
# ANTES
sessions = await session.execute(
    select(Session)
    .where(Session.sender_id == sender_id)
    .where(Session.last_activity > cutoff_date)
)

# DESPUÉS (con índice + query optimization)
sessions = await session.execute(
    select(Session.id, Session.data, Session.last_activity)  # Solo columnas necesarias
    .where(
        and_(
            Session.sender_id == sender_id,
            Session.last_activity > cutoff_date
        )
    )
    .order_by(Session.last_activity.desc())
    .limit(10)  # Paginación
)
```

**Criterios de Éxito**:
- [x] 0 N+1 queries en hot paths
- [x] Queries críticas <50ms (P95)
- [x] Validar con: `EXPLAIN ANALYZE` en PostgreSQL

---

### T2.3 - Índices Estratégicos (1-2 horas)

#### T2.3.1 - Identificar Missing Indexes

```sql
-- Script: scripts/identify_missing_indexes.sql
-- Tablas con seq_scan > idx_scan (necesitan índices)
SELECT 
    schemaname,
    tablename,
    seq_scan,
    idx_scan,
    seq_scan - idx_scan AS seq_over_idx
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan
  AND schemaname = 'public'
ORDER BY seq_over_idx DESC
LIMIT 10;
```

#### T2.3.2 - Crear Índices Concurrentes

```sql
-- Migration: alembic/versions/XXXX_add_strategic_indexes.py
"""Add strategic indexes for hot paths."""

def upgrade():
    # Session Manager: búsquedas por sender_id + last_activity
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_sender_updated 
        ON sessions(sender_id, last_activity DESC);
    """)
    
    # Lock Service: búsquedas por resource_id + status
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_locks_resource_status 
        ON reservation_locks(resource_id, status) 
        WHERE status = 'active';
    """)
    
    # Tenant Resolution: lookup frecuente
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tenant_identifiers_lookup 
        ON tenant_user_identifiers(identifier_value, channel);
    """)
    
    # Audit Trail: queries por resource_id + timestamp
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_resource_timestamp 
        ON lock_audit(resource_id, timestamp DESC);
    """)

def downgrade():
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_sessions_sender_updated;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_locks_resource_status;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_tenant_identifiers_lookup;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_audit_resource_timestamp;")
```

#### T2.3.3 - Validar Index Usage

```sql
-- Verificar que índices se están usando
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND idx_scan > 0
ORDER BY idx_scan DESC;
```

**Criterios de Éxito**:
- [x] Índices creados en tablas críticas
- [x] idx_scan > seq_scan en todas las tablas hot path
- [x] Query latency reducida >30%

**Output**: 
- Migration file
- `.playbook/phase2/index_usage_report.txt`

---

## 📊 FASE 3: OBSERVABILITY (2-3 horas)

**Objetivo**: Dashboards operacionales, alertas críticas configuradas  
**ROI**: ⭐⭐⭐ (Medio-Alto)  
**Prioridad**: 🟡 P2  
**Dependencies**: FASE 1 (métricas instrumentadas)

### T3.1 - Validar Dashboards Existentes (1 hora)

**Problema**: 20 dashboards creados, pero ¿funcionan?

```bash
# Listar dashboards
ls -la docker/grafana/dashboards/

# Validar JSON syntax
for f in docker/grafana/dashboards/*.json; do
  jq empty "$f" || echo "INVALID: $f"
done

# Verificar datasources configuradas
grep -r "datasource" docker/grafana/dashboards/ | grep -v "Prometheus" | wc -l
```

#### Dashboards Críticos a Validar:

| Dashboard | File | Status | Priority |
|-----------|------|--------|----------|
| **Orchestrator Metrics** | `orchestrator_dashboard.json` | ❓ | P0 |
| **PMS Adapter** | `pms_adapter_dashboard.json` | ❓ | P0 |
| **Sessions & Locks** | `sessions_locks_dashboard.json` | ❓ | P1 |
| **Database Metrics** | `database_metrics.json` | ❓ | P1 |
| **API Latency** | `api_latency.json` | ❓ | P0 |

**Acciones**:
1. Abrir Grafana: `http://localhost:3000`
2. Verificar cada dashboard carga sin errores
3. Confirmar que queries Prometheus retornan datos
4. Documentar dashboards rotos
5. Archivar dashboards no usados

**Criterios de Éxito**:
- [x] 10/20 dashboards validados como operacionales
- [x] Dashboards críticos (P0) funcionando
- [x] Dashboards rotos documentados o eliminados

**Output**: `.playbook/phase3/dashboards_status.md`

---

### T3.2 - Completar Métricas Faltantes (1 hora)

**Análisis**: Identificar métricas en código vs dashboards

```bash
# Buscar métricas definidas en código
grep -r "Counter\|Gauge\|Histogram" app/ | grep "prometheus_client" > .playbook/phase3/metrics_code.txt

# Buscar métricas usadas en dashboards
grep -r "expr" docker/grafana/dashboards/*.json | grep -o '"[^"]*{' | sort -u > .playbook/phase3/metrics_dashboards.txt

# Comparar (métricas definidas pero no usadas, o viceversa)
comm -23 .playbook/phase3/metrics_code.txt .playbook/phase3/metrics_dashboards.txt
```

#### Métricas Críticas Faltantes (ejemplo):

```python
# app/monitoring/metrics.py - Agregar si falta
from prometheus_client import Counter, Histogram, Gauge

# Feature Flags
feature_flag_checks = Counter(
    'feature_flag_checks_total',
    'Total feature flag checks',
    ['flag_name', 'result']
)

# Message Gateway
message_processing_latency = Histogram(
    'message_processing_seconds',
    'Message processing latency',
    ['channel', 'intent']
)

# Tenant Resolution
tenant_resolution_latency = Histogram(
    'tenant_resolution_seconds',
    'Tenant resolution latency',
    ['result']
)
```

**Criterios de Éxito**:
- [x] All critical metrics instrumented
- [x] Metrics documented in `docs/METRICS.md`
- [x] Dashboards updated to use new metrics

---

### T3.3 - Configurar Alertas Críticas (1 hora)

**Objetivo**: AlertManager rules para problemas críticos

```yaml
# docker/alertmanager/rules/critical_alerts.yml
groups:
  - name: critical_alerts
    interval: 30s
    rules:
      # Circuit Breaker Open
      - alert: PMSCircuitBreakerOpen
        expr: pms_circuit_breaker_state == 1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "PMS Circuit Breaker is OPEN"
          description: "PMS adapter circuit breaker has been open for 2+ minutes. Service degraded."
      
      # High Error Rate
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} over last 5 minutes."
      
      # Database Connection Pool Exhausted
      - alert: DatabasePoolExhausted
        expr: db_connections_active >= db_connections_max * 0.9
        for: 3m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool near exhaustion"
          description: "{{ $value }} connections active out of max {{ $labels.max }}."
      
      # Session Cleanup Failing
      - alert: SessionCleanupFailing
        expr: rate(session_cleanup_errors_total[10m]) > 0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Session cleanup task failing"
          description: "Session cleanup has errors. Check logs."
```

**Criterios de Éxito**:
- [x] 5+ critical alerts configured
- [x] Alert routing configured (email/slack)
- [x] Alerts tested (manual trigger)

**Output**: `docker/alertmanager/rules/critical_alerts.yml`

---

## 🛡️ FASE 4: VALIDATION & RESILIENCE (3-4 horas)

**Objetivo**: E2E tests passing, stress test OK (100-200 RPS)  
**ROI**: ⭐⭐⭐ (Medio)  
**Prioridad**: 🟡 P2  
**Dependencies**: FASE 1 + 2 (tests passing, performance optimized)

### T4.1 - E2E Tests Críticos (2 horas)

#### T4.1.1 - Reservation Flow Complete (1h)

```python
# tests/e2e/test_reservation_flow_complete.py
"""End-to-end reservation flow validation."""

import pytest
from httpx import AsyncClient

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_reservation_flow():
    """
    Test completo del flujo de reserva:
    1. Check availability
    2. Get room details
    3. Acquire lock
    4. Create reservation
    5. Confirm booking
    6. Release lock
    """
    async with AsyncClient(base_url="http://localhost:8002") as client:
        # 1. Availability
        response = await client.post("/api/orchestrator/process", json={
            "sender_id": "test_user_123",
            "channel": "whatsapp",
            "text": "Disponibilidad para 2025-12-20 a 2025-12-22",
            "timestamp": datetime.now().isoformat()
        })
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "check_availability"
        assert data["rooms_available"] > 0
        
        # 2. Room details
        room_id = data["rooms"][0]["id"]
        response = await client.get(f"/api/pms/rooms/{room_id}")
        assert response.status_code == 200
        
        # 3. Lock (via orchestrator)
        response = await client.post("/api/orchestrator/process", json={
            "sender_id": "test_user_123",
            "channel": "whatsapp",
            "text": f"Reservar habitación {room_id} para 2025-12-20",
            "timestamp": datetime.now().isoformat()
        })
        assert response.status_code == 200
        assert response.json()["lock_acquired"] is True
        
        # 4. Create reservation (complete data)
        response = await client.post("/api/orchestrator/process", json={
            "sender_id": "test_user_123",
            "channel": "whatsapp",
            "text": "Confirmar reserva: Juan Pérez, juan@example.com, +34666777888",
            "timestamp": datetime.now().isoformat()
        })
        assert response.status_code == 200
        assert response.json()["reservation_id"] is not None
        
        # 5. Verify reservation created
        reservation_id = response.json()["reservation_id"]
        response = await client.get(f"/api/pms/reservations/{reservation_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"
        
        # 6. Lock auto-released after confirmation
        # (verificar en logs o métricas)
```

**Criterios de Éxito**:
- [x] E2E flow completes successfully
- [x] All steps validated (availability → confirmation)
- [x] Latency E2E <5s (P95)

---

#### T4.1.2 - Audio Message Flow (30 min)

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_audio_message_e2e():
    """Test audio message processing (STT → NLP → Response → TTS)."""
    async with AsyncClient(base_url="http://localhost:8002") as client:
        # Simular audio message webhook
        response = await client.post("/api/webhooks/whatsapp", json={
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "34666777888",
                            "type": "audio",
                            "audio": {
                                "id": "audio_id_123",
                                "mime_type": "audio/ogg"
                            }
                        }]
                    }
                }]
            }]
        })
        
        assert response.status_code == 200
        # Verificar que se procesó STT → Intent detection
        # (logs o métricas)
```

**Criterios de Éxito**:
- [x] Audio workflow completes
- [x] STT accuracy >80% (manual validation con samples)
- [x] TTS response generated

---

### T4.2 - Circuit Breaker Validation (1 hora)

```python
# tests/resilience/test_circuit_breaker_validation.py
"""Validate circuit breaker behavior under failures."""

@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_pms_failure():
    """Verify CB opens after threshold failures."""
    orchestrator = Orchestrator(pms_adapter=MockPMSAdapter(fail_mode=True))
    
    # Trigger 5 failures
    for _ in range(5):
        await orchestrator.process_message(availability_message)
    
    # Verify CB opened
    assert orchestrator.pms_adapter.circuit_breaker.state == CircuitBreakerState.OPEN
    
    # Verify fallback response used
    response = await orchestrator.process_message(availability_message)
    assert response["fallback_used"] is True
    assert response["status"] == "degraded"

@pytest.mark.asyncio
async def test_circuit_breaker_recovers():
    """Verify CB transitions OPEN → HALF_OPEN → CLOSED."""
    # ... (similar test validating recovery)
```

**Criterios de Éxito**:
- [x] CB opens on threshold failures
- [x] CB recovers after timeout
- [x] Fallback responses correct
- [x] Metrics tracked accurately

---

### T4.3 - Stress Testing (1-2 horas)

**Objetivo**: Validar sistema soporta 100-200 RPS sin degradación

```bash
# Usar wrk (simple) en lugar de locust
# Test 1: Sustained load (100 RPS, 2 min)
wrk -t8 -c100 -d120s --latency http://localhost:8002/api/orchestrator/process \
  -s scripts/wrk_post_payload.lua

# Test 2: Spike (200 RPS, 30s)
wrk -t12 -c200 -d30s --latency http://localhost:8002/api/orchestrator/process \
  -s scripts/wrk_post_payload.lua

# Analizar resultados
echo "P95 Latency under 100 RPS: $(tail -1 wrk_100rps.log | grep 'Latency' | awk '{print $2}')" \
  > .playbook/phase4/stress_test_results.txt
```

**Criterios de Éxito**:
- [x] System handles 100 RPS sustained (2 min) with P95 <300ms
- [x] System handles 200 RPS spike (30s) with P95 <500ms
- [x] 0 errors during stress test
- [x] Circuit breaker does NOT open

**Output**: `.playbook/phase4/stress_test_results.txt`

---

## 🚀 FASE 5: PRODUCTION READINESS (2-3 horas)

**Objetivo**: 9.5/10 readiness, deployment successful  
**ROI**: ⭐⭐⭐⭐ (Alto)  
**Prioridad**: 🔴 P0 (pre-production)  
**Dependencies**: FASE 1-4 completas

### T5.1 - Pre-Flight Checklist (1 hora)

```bash
# Ejecutar pre-flight script existente
make preflight READINESS_SCORE=9.0 MVP_SCORE=8.5

# Revisar reporte
cat .playbook/preflight_report.json | jq '.decision'

# Validar todos los checks pasan
jq '.checks[] | select(.status != "PASS")' .playbook/preflight_report.json
```

**Checks Críticos**:
- [x] Tests passing ≥80%
- [x] Coverage ≥50%
- [x] 0 CRITICAL CVEs
- [x] Secrets validated
- [x] Database migrations OK
- [x] Dashboards operational
- [x] Alertas configuradas
- [x] CI/CD green

**Criterios de Éxito**:
- [x] Preflight decision = "GO"
- [x] Readiness score ≥9.5/10
- [x] All critical checks PASS

---

### T5.2 - Runbooks Validation (1 hora)

**Objetivo**: Verificar runbooks son ejecutables

```bash
# Listar runbooks
ls -la docs/runbooks/

# Validar sintaxis Markdown
for f in docs/runbooks/*.md; do
  markdownlint "$f" || echo "INVALID: $f"
done

# Ejecutar runbook de prueba (deployment)
bash docs/runbooks/DEPLOYMENT_RUNBOOK.md --dry-run
```

**Runbooks Críticos**:
- [ ] `DEPLOYMENT_RUNBOOK.md` - Deployment steps
- [ ] `ROLLBACK_RUNBOOK.md` - Rollback procedure
- [ ] `INCIDENT_RESPONSE.md` - Incident handling
- [ ] `DATABASE_RECOVERY.md` - Backup/restore

**Criterios de Éxito**:
- [x] All runbooks validated
- [x] Commands tested (dry-run)
- [x] Missing runbooks created

---

### T5.3 - Deployment Smoke Tests (1 hora)

```bash
# Deploy to staging
./scripts/deploy-staging.sh --env staging --build

# Wait for deployment
sleep 60

# Smoke tests
curl http://staging.agente-hotel.com/health/live
curl http://staging.agente-hotel.com/health/ready

# E2E smoke test
pytest tests/e2e/test_smoke.py --base-url=http://staging.agente-hotel.com

# Verify metrics
curl http://staging.agente-hotel.com/metrics | grep "up 1"

# Check logs (no errors)
docker logs agente-api | grep ERROR | wc -l  # Should be 0
```

**Criterios de Éxito**:
- [x] Deployment successful
- [x] Health checks green
- [x] Smoke tests passing
- [x] Metrics reporting
- [x] 0 critical errors in logs

**Output**: `.playbook/phase5/deployment_report.md`

---

## 📋 RESUMEN EJECUTIVO

### TOTAL EFFORT ESTIMATION

| Fase | Duración | ROI | Prioridad | Status |
|------|----------|-----|-----------|--------|
| **FASE 0: Quick Wins** | 1-2h | ⭐⭐⭐⭐⭐ | 🔴 P0 | ⬜ Pending |
| **FASE 1: Foundation** | 4-6h | ⭐⭐⭐⭐⭐ | 🔴 P0 | ⬜ Pending |
| **FASE 2: DB & Performance** | 3-5h | ⭐⭐⭐⭐ | 🟠 P1 | ⬜ Pending |
| **FASE 3: Observability** | 2-3h | ⭐⭐⭐ | 🟡 P2 | ⬜ Pending |
| **FASE 4: Validation** | 3-4h | ⭐⭐⭐ | 🟡 P2 | ⬜ Pending |
| **FASE 5: Production** | 2-3h | ⭐⭐⭐⭐ | 🔴 P0 | ⬜ Pending |
| **TOTAL** | **15-23h** | - | - | **0%** |

### MINIMUM VIABLE PATH (MVP)

**Para alcanzar 9.5/10 readiness en MÍNIMO tiempo**:

```
FASE 0 (2h) → FASE 1 (6h) → FASE 5 (3h) = 11 horas
```

**Resultado**:
- Tests collectables: 1200+
- Coverage: 50%+
- Tests passing: 80%+
- Deployment: OK
- Readiness: 9.5/10

**Fases 2-4 son RECOMENDADAS pero NO BLOQUEANTES** para producción.

---

## 🎯 CRITERIOS DE ÉXITO GLOBALES

### MÉTRICAS FINALES TARGET

| Métrica | Inicio | Target v2.0 | Validación |
|---------|--------|-------------|------------|
| **Tests Collectables** | 43/1279 (3.4%) | 1200+/1279 (95%+) | `pytest --co tests/` |
| **Test Coverage** | 22% | 50-60% | `pytest --cov=app` |
| **Tests Passing** | Unknown | 80%+ | `pytest tests/` |
| **P95 Latency** | No medido | <300ms | Prometheus query |
| **Queries P95** | No medido | <100ms | `pg_stat_statements` |
| **CVEs CRITICAL** | 0 | 0 | `make security-fast` |
| **CI/CD** | Parcial | Completo | `.github/workflows/` |
| **Dashboards** | 20 creados | 10 validados | Grafana UI |
| **Readiness Score** | 8.9/10 | 9.5/10 | `make preflight` |

### DEFINITION OF DONE

**El proyecto está listo para producción cuando**:

- [x] **Tests**: 1200+ tests collectables, 80%+ passing, 50%+ coverage
- [x] **Performance**: P95 <300ms, queries <100ms
- [x] **Observability**: Dashboards funcionando, alertas configuradas
- [x] **Security**: 0 CRITICAL CVEs, secrets validated
- [x] **CI/CD**: Pipeline green, quality gates enforced
- [x] **Deployment**: Staging deployment successful, smoke tests OK
- [x] **Documentation**: Runbooks validated, ADRs updated
- [x] **Readiness**: Preflight score ≥9.5/10

---

## 📝 NOTAS DE IMPLEMENTACIÓN

### MEJORAS vs v1.0

1. ✅ **Datos Reales**: Métricas validadas (22% coverage, 43 tests)
2. ✅ **Estructura Optimizada**: 6 fases (vs 10 módulos)
3. ✅ **ROI Calculado**: Priorización basada en impacto/esfuerzo
4. ✅ **Objetivos Realistas**: 50% coverage (vs 85% imposible)
5. ✅ **Quick Wins**: Nueva FASE 0 de alto ROI
6. ✅ **Dependencies Explícitas**: Secuenciación clara
7. ✅ **MVP Path**: Ruta mínima 11 horas a producción
8. ✅ **Estimaciones Precisas**: 15-23h (vs 30-40h v1.0)

### RIESGOS IDENTIFICADOS

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Tests rotos difíciles de reparar | Media | Alto | Priorizar P0, skip P3 temporalmente |
| Performance no mejora | Baja | Medio | Índices garantizan mejora mínima 30% |
| Dashboards no funcionan | Media | Bajo | Validación en Fase 3, no bloqueante |
| Stress test falla | Media | Medio | Target realista 100-200 RPS |
| Deployment issues | Baja | Alto | Scripts probados, staging environment |

### PRÓXIMOS PASOS

1. **EJECUTAR FASE 0** (1-2h) - Quick wins immediate
2. **Review con equipo** - Validar prioridades
3. **EJECUTAR FASE 1** (4-6h) - Foundation crítica
4. **Decision point**: Evaluar si continuar o deployment MVP
5. **FASES 2-5** - Optimización continua

---

**Última Actualización**: 2025-11-10  
**Mantenido Por**: AI Agent Team  
**Revisión**: Antes de cada fase  
**Feedback**: Documentar desviaciones en `.playbook/phase_X/DEVIATIONS.md`
