# 🎯 BLUEPRINT OPTIMIZACIÓN "0 KILÓMETROS" - PROYECTO AGENTE HOTELERO

**Fecha Creación**: 2025-11-10  
**Objetivo**: Llevar el proyecto al estado óptimo para producción  
**Estado Inicial**: 8.9/10 readiness | 31% coverage | 28/891 tests passing  
**Estado Objetivo**: 9.5+/10 readiness | 85%+ coverage | 100% tests passing  

---

## 📊 ANÁLISIS DEL ESTADO ACTUAL

### ✅ Fortalezas Actuales
- ✅ **Seguridad**: 0 CRITICAL CVEs (python-jose 3.5.0 actualizado)
- ✅ **Linting**: 0 errores Ruff + gitleaks
- ✅ **Infraestructura**: 7 servicios Docker Compose funcionando
- ✅ **Secrets**: Auto-generados y seguros (.env.staging)
- ✅ **Observabilidad**: Stack completo (Prometheus/Grafana/Jaeger/AlertManager)
- ✅ **Arquitectura**: Patrones sólidos (Circuit Breaker, Caching, Locks)
- ✅ **Documentación Base**: Guías operacionales + runbooks

### ⚠️ Áreas Críticas de Mejora
- ❌ **Coverage**: 31% (objetivo: 85%+) - **CRÍTICO**
- ❌ **Tests Passing**: 28/891 (3.1%) - **BLOQUEANTE**
- ⚠️ **Performance**: No baseline establecido
- ⚠️ **Database**: Índices sin optimizar
- ⚠️ **Caching**: Estrategia básica implementada
- ⚠️ **Observability**: Dashboards incompletos
- ⚠️ **Documentation**: Gaps en docs técnicas

### 📈 Métricas Clave

| Métrica | Actual | Objetivo | Gap |
|---------|--------|----------|-----|
| **Test Coverage** | 31% | 85% | -54% |
| **Tests Passing** | 28/891 (3.1%) | 100% | -97% |
| **P95 Latency** | No medido | <200ms | TBD |
| **CVEs CRITICAL** | 0 | 0 | ✅ |
| **Code Quality** | 0 errors | 0 errors | ✅ |
| **Docs Coverage** | ~60% | 95% | -35% |

---

## 🗺️ ARQUITECTURA DEL BLUEPRINT

### Estructura por Módulos

```
MÓDULO 1: FOUNDATION (Tests + Coverage)          ← PRIORIDAD MÁXIMA
├── 1.1 Análisis de tests existentes
├── 1.2 Identificar tests rotos
├── 1.3 Reparar tests críticos
├── 1.4 Aumentar coverage al 70%
└── 1.5 Validar CI/CD pipeline

MÓDULO 2: PERFORMANCE OPTIMIZATION              ← ALTA PRIORIDAD
├── 2.1 Establecer baseline de performance
├── 2.2 Optimizar queries de base de datos
├── 2.3 Implementar índices estratégicos
├── 2.4 Optimizar caching Redis
└── 2.5 Reducir latencia P95 < 200ms

MÓDULO 3: DATABASE EXCELLENCE                   ← ALTA PRIORIDAD
├── 3.1 Diseño de índices (B-tree, GiST, BRIN)
├── 3.2 Particionamiento de tablas
├── 3.3 Migraciones con Alembic
├── 3.4 Backup y recovery procedures
└── 3.5 Connection pooling optimization

MÓDULO 4: OBSERVABILITY & MONITORING            ← MEDIA PRIORIDAD
├── 4.1 Dashboards Grafana completos
├── 4.2 Alertas Prometheus configuradas
├── 4.3 Tracing distribuido Jaeger
├── 4.4 Log aggregation (JSON structured)
└── 4.5 SLIs/SLOs/SLAs definidos

MÓDULO 5: RESILIENCE & CHAOS ENGINEERING        ← MEDIA PRIORIDAD
├── 5.1 Tests de chaos engineering
├── 5.2 Validación de circuit breakers
├── 5.3 Fault injection scenarios
├── 5.4 Recovery time testing
└── 5.5 Disaster recovery drills

MÓDULO 6: DOCUMENTATION & KNOWLEDGE TRANSFER    ← MEDIA PRIORIDAD
├── 6.1 Architecture Decision Records (ADRs)
├── 6.2 API documentation (OpenAPI)
├── 6.3 Developer onboarding guide
├── 6.4 Operational runbooks completos
└── 6.5 Troubleshooting guides

MÓDULO 7: DEPLOYMENT & AUTOMATION               ← BAJA PRIORIDAD
├── 7.1 CI/CD pipeline optimization
├── 7.2 Canary deployment automation
├── 7.3 Blue-green deployment
├── 7.4 Rollback automation
└── 7.5 Post-deployment validation

MÓDULO 8: SECURITY HARDENING                    ← BAJA PRIORIDAD
├── 8.1 Penetration testing
├── 8.2 OWASP Top 10 validation
├── 8.3 Dependency scanning automation
├── 8.4 Secret rotation procedures
└── 8.5 Security audit trail

MÓDULO 9: CODE QUALITY & REFACTORING            ← CONTINUO
├── 9.1 Code smell detection
├── 9.2 Technical debt reduction
├── 9.3 Design patterns enforcement
├── 9.4 Type hints al 100%
└── 9.5 Docstrings compliance

MÓDULO 10: FINAL VALIDATION & CERTIFICATION     ← ÚLTIMA FASE
├── 10.1 Load testing (1000+ RPS)
├── 10.2 Stress testing (peak capacity)
├── 10.3 Pre-production smoke tests
├── 10.4 Security penetration tests
└── 10.5 Production readiness review
```

---

## 📋 MÓDULO 1: FOUNDATION (Tests + Coverage) - FASE CRÍTICA

**Objetivo**: Lograr 70%+ coverage y 100% tests passing  
**Duración Estimada**: 6-8 horas  
**Prioridad**: 🔴 CRÍTICA (BLOQUEANTE)

### 1.1 Análisis de Tests Existentes

**Tareas**:
```bash
✅ T1.1.1 - Ejecutar test discovery completo
  Comando: pytest --collect-only tests/
  Output: Lista de todos los tests disponibles

✅ T1.1.2 - Generar reporte de coverage actual
  Comando: pytest --cov=app --cov-report=html tests/
  Output: htmlcov/index.html con coverage detallado

✅ T1.1.3 - Identificar módulos sin coverage
  Análisis: grep para encontrar archivos en app/ sin tests

✅ T1.1.4 - Analizar tests rotos (failures + errors)
  Comando: pytest tests/ --tb=short 2>&1 | tee test_failures.log
  Output: Log con todos los fallos
```

**Criterios de Éxito**:
- [x] Inventario completo de 891 tests
- [ ] Reporte HTML de coverage generado
- [ ] Lista de módulos sin coverage (>30% del código)
- [ ] Log de tests rotos con stack traces

**Entregables**:
- `reports/test_inventory.txt` - Lista completa de tests
- `htmlcov/index.html` - Coverage visual
- `reports/modules_without_tests.txt` - Gaps de coverage
- `reports/test_failures.log` - Tests rotos con detalles

---

### 1.2 Identificar y Categorizar Tests Rotos

**Tareas**:
```bash
✅ T1.2.1 - Clasificar fallos por tipo
  Categorías:
    - Import errors (dependencias faltantes)
    - Fixture errors (conftest.py issues)
    - Assertion errors (lógica de tests)
    - Timeout errors (performance issues)
    - Mock errors (mocks mal configurados)

✅ T1.2.2 - Priorizar por criticidad
  P0 (Bloqueante): Tests de servicios core (orchestrator, pms_adapter)
  P1 (Alto): Tests de integración
  P2 (Medio): Tests E2E
  P3 (Bajo): Tests de performance (no afectan funcionalidad)

✅ T1.2.3 - Crear matriz de dependencias
  Mapear qué tests dependen de qué fixtures/mocks
```

**Criterios de Éxito**:
- [ ] Tests categorizados por tipo de fallo
- [ ] Prioridad asignada a cada test roto
- [ ] Matriz de dependencias entre tests y fixtures

**Entregables**:
- `reports/test_failures_categorized.csv` - Fallos categorizados
- `reports/test_priorities.md` - Prioridades P0-P3
- `reports/test_dependencies_matrix.txt` - Mapa de dependencias

---

### 1.3 Reparar Tests Críticos (P0 + P1)

**Tareas**:
```bash
✅ T1.3.1 - Reparar import errors
  Acción: Instalar dependencias faltantes
  Validación: pytest --collect-only sin errores

✅ T1.3.2 - Reparar fixture errors en conftest.py
  Acción: Revisar y corregir fixtures AsyncSession, test_app, etc.
  Validación: Tests usando fixtures pasan

✅ T1.3.3 - Reparar tests de orchestrator (P0)
  Archivos:
    - tests/unit/test_orchestrator_basic.py
    - tests/integration/test_orchestrator_circuit_breaker.py
  Validación: pytest tests/unit/test_orchestrator*.py -v

✅ T1.3.4 - Reparar tests de PMS adapter (P0)
  Archivos:
    - tests/unit/test_pms_circuit_breaker_state_flow.py
    - tests/unit/test_circuit_breaker.py
  Validación: pytest tests/unit/test_pms*.py -v

✅ T1.3.5 - Reparar tests de session manager (P0)
  Archivos:
    - tests/unit/test_session_manager_ttl.py
    - tests/unit/test_session_cleanup.py
  Validación: pytest tests/unit/test_session*.py -v

✅ T1.3.6 - Reparar tests de lock service (P0)
  Archivos:
    - tests/unit/test_lock_service.py
    - tests/unit/test_lock_audit_trail.py
  Validación: pytest tests/unit/test_lock*.py -v
```

**Criterios de Éxito**:
- [ ] 0 import errors
- [ ] Fixtures en conftest.py funcionan
- [ ] Tests P0 (core services) passing al 100%
- [ ] Tests P1 (integración) passing al 80%+

**Entregables**:
- Tests P0 reparados y passing
- Coverage de servicios core >80%
- Commit: "fix(tests): repair P0 critical tests - orchestrator, pms, sessions, locks"

---

### 1.4 Aumentar Coverage al 70%+

**Estrategia por Módulo**:

#### 1.4.1 Orchestrator Service (Objetivo: 85%)
```python
# Nuevos tests necesarios:
✅ test_orchestrator_all_intent_handlers()
✅ test_orchestrator_nlp_confidence_thresholds()
✅ test_orchestrator_fallback_responses()
✅ test_orchestrator_audio_processing_integration()
✅ test_orchestrator_session_state_management()
✅ test_orchestrator_error_handling_all_paths()
```

#### 1.4.2 PMS Adapter (Objetivo: 90%)
```python
# Nuevos tests necesarios:
✅ test_pms_adapter_all_endpoints_mock()
✅ test_pms_adapter_cache_hit_ratio()
✅ test_pms_adapter_cache_invalidation()
✅ test_pms_adapter_retry_logic()
✅ test_pms_adapter_timeout_handling()
✅ test_pms_adapter_metrics_accuracy()
```

#### 1.4.3 Session Manager (Objetivo: 85%)
```python
# Nuevos tests necesarios:
✅ test_session_manager_concurrent_updates()
✅ test_session_manager_ttl_enforcement()
✅ test_session_manager_cleanup_edge_cases()
✅ test_session_manager_metrics_consistency()
```

#### 1.4.4 Message Gateway (Objetivo: 80%)
```python
# Nuevos tests necesarios:
✅ test_message_gateway_all_channels()
✅ test_message_gateway_normalization()
✅ test_message_gateway_tenant_resolution()
✅ test_message_gateway_error_handling()
```

#### 1.4.5 Feature Flag Service (Objetivo: 75%)
```python
# Nuevos tests necesarios:
✅ test_feature_flags_redis_fallback()
✅ test_feature_flags_default_values()
✅ test_feature_flags_cache_refresh()
```

**Criterios de Éxito**:
- [ ] Coverage global ≥ 70%
- [ ] Coverage servicios críticos ≥ 85%
- [ ] Coverage handlers ≥ 80%
- [ ] Coverage utils ≥ 70%

**Entregables**:
- 100+ nuevos tests implementados
- Coverage report HTML >70%
- Commit: "test(coverage): increase coverage to 70%+ across all critical modules"

---

### 1.5 Validar CI/CD Pipeline

**Tareas**:
```bash
✅ T1.5.1 - Configurar pytest en CI
  Crear: .github/workflows/tests.yml
  Incluir: pytest, coverage, reports

✅ T1.5.2 - Badge de coverage en README
  Integrar: codecov.io o coveralls.io

✅ T1.5.3 - Quality gates
  Configurar: Minimum 70% coverage to pass CI
```

**Criterios de Éxito**:
- [ ] CI ejecuta tests automáticamente
- [ ] Coverage reportado en PR
- [ ] Quality gates enforced (70% min)

---

## 📋 MÓDULO 2: PERFORMANCE OPTIMIZATION

**Objetivo**: P95 latency <200ms, throughput >500 RPS  
**Duración Estimada**: 4-6 horas  
**Prioridad**: 🟠 ALTA

### 2.1 Establecer Baseline de Performance

**Tareas**:
```bash
✅ T2.1.1 - Instrumentar endpoints críticos
  Endpoints:
    - POST /api/webhooks/whatsapp
    - POST /api/orchestrator/process
    - GET /api/pms/availability

✅ T2.1.2 - Ejecutar load testing
  Herramienta: locust o k6
  Escenario: 100 RPS durante 5 minutos
  Métricas: P50, P95, P99 latency

✅ T2.1.3 - Identificar bottlenecks
  Herramientas: py-spy, memory_profiler
  Análisis: CPU, memoria, I/O
```

**Criterios de Éxito**:
- [ ] Baseline documentado (latencias actuales)
- [ ] Bottlenecks identificados
- [ ] Plan de optimización priorizado

**Entregables**:
- `reports/performance_baseline.md` - Métricas actuales
- `reports/bottlenecks_analysis.md` - Análisis detallado
- `reports/optimization_plan.md` - Plan priorizado

---

### 2.2 Optimizar Queries de Base de Datos

**Tareas**:
```bash
✅ T2.2.1 - Identificar N+1 queries
  Herramienta: SQLAlchemy logging + EXPLAIN ANALYZE

✅ T2.2.2 - Implementar eager loading
  Técnicas: joinedload(), selectinload()

✅ T2.2.3 - Optimizar queries lentas (>100ms)
  Acción: Refactorizar queries, agregar índices

✅ T2.2.4 - Implementar query result caching
  Estrategia: Redis cache para queries frecuentes
```

**Criterios de Éxito**:
- [ ] 0 N+1 queries en hot paths
- [ ] Queries críticas <50ms (P95)
- [ ] Cache hit ratio >80% en queries frecuentes

---

### 2.3 Implementar Índices Estratégicos

**Análisis de Queries Frecuentes**:
```sql
-- Identificar queries sin índices
SELECT schemaname, tablename, seq_scan, idx_scan
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan
ORDER BY seq_scan DESC;
```

**Índices Propuestos**:
```sql
-- Session Manager (búsquedas por sender_id + timestamp)
CREATE INDEX CONCURRENTLY idx_sessions_sender_updated 
ON sessions(sender_id, last_activity DESC);

-- Lock Service (búsquedas por resource_id)
CREATE INDEX CONCURRENTLY idx_locks_resource_status 
ON reservation_locks(resource_id, status) 
WHERE status = 'active';

-- Tenant Resolution (búsquedas frecuentes)
CREATE INDEX CONCURRENTLY idx_tenant_identifiers_lookup 
ON tenant_user_identifiers(identifier_value, channel);
```

**Criterios de Éxito**:
- [ ] Índices B-tree en columnas de búsqueda
- [ ] Índices parciales en queries condicionales
- [ ] idx_scan > seq_scan en todas las tablas críticas

---

### 2.4 Optimizar Caching Redis

**Estrategia Avanzada**:
```python
# Cache layers:
# L1: In-memory (Python dict) - TTL 60s
# L2: Redis - TTL 5-60min (dependiendo del dato)
# L3: PostgreSQL - Source of truth

✅ T2.4.1 - Implementar cache hierarchy
✅ T2.4.2 - Cache warming para datos frecuentes
✅ T2.4.3 - Cache invalidation patterns
✅ T2.4.4 - Monitorear hit ratio (objetivo: 85%+)
```

**Datos a Cachear**:
```python
# PMS Adapter (TTL 5min)
- Availability data
- Room types

# Feature Flags (TTL 60s)
- Flag values (in-memory + Redis)

# Tenant Resolution (TTL 300s)
- Tenant mappings (dynamic resolution)
```

**Criterios de Éxito**:
- [ ] Cache hit ratio >85%
- [ ] Invalidación funciona correctamente
- [ ] Métricas de cache tracked en Prometheus

---

### 2.5 Reducir Latencia P95 < 200ms

**Optimizaciones Finales**:
```bash
✅ T2.5.1 - Connection pooling (asyncpg + Redis)
  Configuración: pool_size=10, max_overflow=10

✅ T2.5.2 - Async everywhere (no blocking I/O)
  Audit: Buscar operaciones síncronas en hot paths

✅ T2.5.3 - Background tasks (Celery/arq)
  Tareas: Emails, notificaciones, cleanup

✅ T2.5.4 - CDN para assets estáticos
  Considerar: CloudFlare o similar
```

**Criterios de Éxito**:
- [ ] P95 latency <200ms en todos los endpoints
- [ ] P99 latency <500ms
- [ ] No blocking I/O en request handlers

---

## 📋 MÓDULO 3: DATABASE EXCELLENCE

**Objetivo**: DB optimizada, migraciones seguras, backups automatizados  
**Duración Estimada**: 3-4 horas  
**Prioridad**: 🟠 ALTA

### 3.1 Diseño de Índices Avanzados

**Índices Especializados**:
```sql
-- GiST para búsquedas de rangos de fechas
CREATE INDEX idx_reservations_date_range ON reservations 
USING gist (daterange(check_in, check_out));

-- BRIN para tablas grandes con datos ordenados temporalmente
CREATE INDEX idx_sessions_created_brin ON sessions 
USING brin (created_at);

-- Hash index para igualdades exactas (UUID lookups)
CREATE INDEX idx_sessions_id_hash ON sessions 
USING hash (id);
```

**Criterios de Éxito**:
- [ ] Índices especializados para cada tipo de query
- [ ] EXPLAIN ANALYZE muestra uso de índices
- [ ] Query performance mejorado >3x

---

### 3.2 Particionamiento de Tablas

**Tablas Candidatas**:
```sql
-- Sessions (particionar por created_at - mensual)
CREATE TABLE sessions_2025_11 PARTITION OF sessions
FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

-- Lock Audit (particionar por timestamp - mensual)
CREATE TABLE lock_audit_2025_11 PARTITION OF lock_audit
FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
```

**Criterios de Éxito**:
- [ ] Tablas grandes (>1M rows) particionadas
- [ ] Queries usan partition pruning
- [ ] Mantenimiento simplificado (drop old partitions)

---

### 3.3 Migraciones con Alembic

**Setup**:
```bash
✅ T3.3.1 - Configurar Alembic
  alembic init alembic

✅ T3.3.2 - Generar migración inicial
  alembic revision --autogenerate -m "initial schema"

✅ T3.3.3 - Validar migración up/down
  alembic upgrade head
  alembic downgrade -1

✅ T3.3.4 - Documentar proceso de migraciones
  Crear: docs/DATABASE_MIGRATIONS.md
```

**Criterios de Éxito**:
- [ ] Alembic configurado y funcionando
- [ ] Migración inicial generada
- [ ] Procedimiento de rollback validado

---

### 3.4 Backup y Recovery

**Estrategia**:
```bash
✅ T3.4.1 - Script de backup automático
  Herramienta: pg_dump con compresión
  Frecuencia: Daily (0:00 UTC)

✅ T3.4.2 - Retention policy
  Retención: 7 daily, 4 weekly, 12 monthly

✅ T3.4.3 - Test de recovery
  Procedimiento: Restaurar backup en DB de test
  Frecuencia: Mensual

✅ T3.4.4 - RPO/RTO definidos
  RPO: <24 horas
  RTO: <1 hora
```

**Criterios de Éxito**:
- [ ] Backups automáticos funcionando
- [ ] Recovery testado y documentado
- [ ] RPO/RTO cumplidos en tests

---

### 3.5 Connection Pooling Optimization

**Configuración Óptima**:
```python
# PostgreSQL (asyncpg)
POSTGRES_POOL_SIZE = 10
POSTGRES_MAX_OVERFLOW = 10
POSTGRES_POOL_TIMEOUT = 30
POSTGRES_POOL_RECYCLE = 3600  # 1 hora

# Redis (aioredis)
REDIS_POOL_SIZE = 20
REDIS_POOL_MIN_SIZE = 5
```

**Monitoreo**:
```python
# Métricas a trackear:
- db_connections_active
- db_connections_idle
- db_pool_exhausted_total
- db_connection_wait_time_seconds
```

**Criterios de Éxito**:
- [ ] Pool nunca se agota bajo load normal
- [ ] Connections reutilizadas eficientemente
- [ ] Métricas de pool en Grafana

---

## 📋 MÓDULO 4: OBSERVABILITY & MONITORING

**Objetivo**: Visibilidad completa del sistema en producción  
**Duración Estimada**: 3-4 horas  
**Prioridad**: 🟡 MEDIA

### 4.1 Dashboards Grafana Completos

**Dashboards a Crear**:
```yaml
Dashboard 1: Overview del Sistema
  - Request rate (RPS)
  - Error rate (%)
  - P95/P99 latency
  - Active connections (DB, Redis)

Dashboard 2: PMS Adapter
  - Circuit breaker state
  - PMS API latency
  - Cache hit ratio
  - Error breakdown por endpoint

Dashboard 3: Orchestrator
  - Intents detectados (pie chart)
  - Confidence scores (histogram)
  - Fallback rate
  - Processing latency

Dashboard 4: Database
  - Query latency
  - Connection pool usage
  - Slow queries (>100ms)
  - Index usage

Dashboard 5: Redis
  - Hit ratio
  - Memory usage
  - Evictions
  - Command latency
```

**Criterios de Éxito**:
- [ ] 5 dashboards completos y funcionales
- [ ] Datos en tiempo real (<30s refresh)
- [ ] Alertas visuales en dashboards

---

### 4.2 Alertas Prometheus

**Reglas de Alerta**:
```yaml
# alerts/critical.yml
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Error rate >5% for 5 minutes"

- alert: CircuitBreakerOpen
  expr: pms_circuit_breaker_state == 1
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "PMS circuit breaker is OPEN"

- alert: DatabaseConnectionPoolExhausted
  expr: db_pool_exhausted_total > 10
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "DB pool exhausted >10 times in 1 min"

- alert: HighLatency
  expr: histogram_quantile(0.95, http_request_duration_seconds) > 0.5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "P95 latency >500ms for 5 minutes"
```

**Criterios de Éxito**:
- [ ] 10+ alertas configuradas
- [ ] Alertas enviadas a Slack/Email
- [ ] Runbooks vinculados a cada alerta

---

### 4.3 Tracing Distribuido (Jaeger)

**Configuración**:
```python
# Instrumentar spans en:
✅ HTTP requests (entrada/salida)
✅ PMS API calls
✅ Database queries
✅ Redis operations
✅ NLP processing
```

**Criterios de Éxito**:
- [ ] Traces visibles en Jaeger UI
- [ ] Correlación entre servicios
- [ ] Identificación de cuellos de botella

---

### 4.4 Log Aggregation

**Estrategia**:
```python
# Structured logging (JSON)
logger.info("pms_call_success", 
    endpoint="availability",
    latency_ms=150,
    cache_hit=True,
    correlation_id="abc123"
)
```

**Criterios de Éxito**:
- [ ] Logs en formato JSON estructurado
- [ ] Correlation IDs en todos los logs
- [ ] Logs indexables (Loki/Elasticsearch)

---

### 4.5 SLIs/SLOs/SLAs

**Definiciones**:
```yaml
SLI (Service Level Indicators):
  - Availability: % de uptime
  - Latency: P95 de request duration
  - Error rate: % de requests con 5xx

SLO (Service Level Objectives):
  - Availability: ≥99.5% mensual
  - P95 Latency: ≤200ms
  - Error rate: ≤0.5%

SLA (Service Level Agreements):
  - Availability: ≥99% mensual (con penalizaciones)
  - Support response: <4 horas para P0
```

**Criterios de Éxito**:
- [ ] SLIs medidos automáticamente
- [ ] SLOs tracked en dashboards
- [ ] Alertas cuando SLO en riesgo

---

## 📋 MÓDULO 5: RESILIENCE & CHAOS ENGINEERING

**Objetivo**: Sistema resistente a fallos  
**Duración Estimada**: 2-3 horas  
**Prioridad**: 🟡 MEDIA

### 5.1 Chaos Engineering Tests

**Escenarios**:
```python
✅ Scenario 1: PMS API timeout
  - Simular: Inyectar delay de 10s en PMS calls
  - Validar: Circuit breaker abre, fallback funciona

✅ Scenario 2: Redis down
  - Simular: docker stop redis
  - Validar: Sistema degrada gracefully, usa defaults

✅ Scenario 3: PostgreSQL connection loss
  - Simular: Matar conexiones activas
  - Validar: Reconnection automático funciona

✅ Scenario 4: Spike de tráfico (10x normal)
  - Simular: locust con 1000 RPS
  - Validar: Rate limiting funciona, no crashes
```

**Criterios de Éxito**:
- [ ] 4+ escenarios de chaos ejecutados
- [ ] Sistema se recupera automáticamente
- [ ] No data loss en ningún escenario

---

### 5.2 Fault Injection

**Herramienta**: Implementar fault injector
```python
class FaultInjector:
    async def inject_latency(self, delay_ms: int):
        """Inyecta latencia artificial"""
        await asyncio.sleep(delay_ms / 1000)
    
    async def inject_error(self, error_rate: float):
        """Inyecta errores aleatorios"""
        if random.random() < error_rate:
            raise Exception("Injected error")
```

**Criterios de Éxito**:
- [ ] Fault injection framework implementado
- [ ] Tests automáticos con faults
- [ ] Métricas de resilience tracked

---

## 📋 MÓDULO 6: DOCUMENTATION

**Objetivo**: Documentación completa y actualizada  
**Duración Estimada**: 2-3 horas  
**Prioridad**: 🟡 MEDIA

### 6.1 Architecture Decision Records (ADRs)

**Template ADR**:
```markdown
# ADR-001: Use PostgreSQL for Session Storage

## Status
Accepted

## Context
Need persistent, ACID-compliant storage for user sessions.

## Decision
Use PostgreSQL with asyncpg for async operations.

## Consequences
+ ACID guarantees
+ Rich query capabilities
+ Mature tooling
- Higher latency than Redis for reads
```

**Criterios de Éxito**:
- [ ] 10+ ADRs documentados
- [ ] Decisiones arquitectónicas justificadas
- [ ] Template estandarizado usado

---

### 6.2 API Documentation (OpenAPI)

**Generación Automática**:
```python
# FastAPI auto-genera /docs (Swagger UI)
# Mejorar con:
✅ Descripciones detalladas en endpoints
✅ Ejemplos de requests/responses
✅ Error codes documentados
```

**Criterios de Éxito**:
- [ ] Swagger UI completo y navegable
- [ ] Todos los endpoints documentados
- [ ] Ejemplos funcionales en /docs

---

### 6.3 Developer Onboarding Guide

**Contenido**:
```markdown
# Developer Onboarding Guide

## Day 1: Environment Setup
- Clone repo
- Install dependencies
- Run docker-compose up
- Execute tests

## Day 2: Architecture Understanding
- Read ADRs
- Review system diagram
- Understand key patterns

## Day 3: First Contribution
- Pick "good first issue"
- Make PR with tests
- Code review process
```

**Criterios de Éxito**:
- [ ] Onboarding guide completo
- [ ] New developer can be productive in <3 days
- [ ] Feedback loop para mejorar guía

---

### 6.4 Runbooks Operacionales

**Runbooks Críticos**:
```markdown
✅ Runbook 1: Circuit Breaker Abierto
✅ Runbook 2: Database Slow Queries
✅ Runbook 3: High Memory Usage
✅ Runbook 4: Rate Limit Exceeded
✅ Runbook 5: Deployment Rollback
```

**Criterios de Éxito**:
- [ ] 5+ runbooks completos
- [ ] Vinculados a alertas Prometheus
- [ ] Procedimientos probados en drills

---

## 📋 MÓDULO 7: DEPLOYMENT AUTOMATION

**Objetivo**: Deployments seguros y automatizados  
**Duración Estimada**: 2 horas  
**Prioridad**: 🟢 BAJA

### 7.1 CI/CD Pipeline

**GitHub Actions Workflow**:
```yaml
name: CI/CD Pipeline

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: make test
      - name: Coverage
        run: make test-coverage
      - name: Quality gates
        run: |
          coverage report --fail-under=70

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Ruff
        run: make lint
      - name: Security scan
        run: make security-fast

  deploy-staging:
    needs: [test, lint]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to staging
        run: make deploy-staging
```

**Criterios de Éxito**:
- [ ] CI ejecuta en cada PR
- [ ] Quality gates enforcement
- [ ] Auto-deploy a staging en merge

---

### 7.2 Canary Deployment

**Proceso**:
```bash
✅ Step 1: Deploy canary (10% traffic)
✅ Step 2: Monitor metrics (5 min)
✅ Step 3: Compare baseline vs canary
✅ Step 4: Promote or rollback
```

**Criterios de Éxito**:
- [ ] Script de canary deployment
- [ ] Métricas comparadas automáticamente
- [ ] Rollback automático en anomalías

---

## 📋 MÓDULO 8: SECURITY HARDENING

**Objetivo**: Sistema hardened contra ataques  
**Duración Estimada**: 2 horas  
**Prioridad**: 🟢 BAJA

### 8.1 OWASP Top 10 Validation

**Checklist**:
```bash
✅ A01 Broken Access Control
  - Rate limiting implementado
  - JWT validation correcta

✅ A02 Cryptographic Failures
  - Secrets en .env, no hardcoded
  - HTTPS enforced

✅ A03 Injection
  - SQLAlchemy ORM (parametrized queries)
  - Input validation

✅ A04 Insecure Design
  - Circuit breakers
  - Fail-safe defaults

✅ A05 Security Misconfiguration
  - Debug=False en prod
  - Security headers (CSP, HSTS)
```

**Criterios de Éxito**:
- [ ] OWASP Top 10 auditado
- [ ] Vulnerabilidades mitigadas
- [ ] Scan automático en CI

---

### 8.2 Dependency Scanning

**Automatización**:
```bash
# Trivy scan en CI/CD
trivy filesystem --severity HIGH,CRITICAL .

# Safety check (Python packages)
poetry export | safety check --stdin
```

**Criterios de Éxito**:
- [ ] 0 CRITICAL vulnerabilities
- [ ] Auto-scan en cada PR
- [ ] Alertas en nuevas CVEs

---

## 📋 MÓDULO 9: CODE QUALITY

**Objetivo**: Código limpio y mantenible  
**Duración Estimada**: Continuo  
**Prioridad**: 🟢 BAJA (Continuo)

### 9.1 Code Smell Detection

**Herramientas**:
```bash
✅ pylint (code smells)
✅ mypy (type checking)
✅ radon (complexity metrics)
```

**Criterios de Éxito**:
- [ ] Pylint score >8.5/10
- [ ] mypy strict mode passing
- [ ] Cyclomatic complexity <10

---

### 9.2 Type Hints al 100%

**Objetivo**:
```python
# ANTES:
def process_message(msg):
    return orchestrator.handle(msg)

# DESPUÉS:
async def process_message(msg: UnifiedMessage) -> Dict[str, Any]:
    return await orchestrator.handle(msg)
```

**Criterios de Éxito**:
- [ ] Type hints en 100% de funciones públicas
- [ ] mypy --strict sin errores

---

## 📋 MÓDULO 10: FINAL VALIDATION

**Objetivo**: Certificación de producción  
**Duración Estimada**: 3-4 horas  
**Prioridad**: 🔴 FINAL (BLOQUEANTE para producción)

### 10.1 Load Testing (1000 RPS)

**Escenario**:
```python
# locust configuration
class LoadTest(HttpUser):
    @task
    def webhook_whatsapp(self):
        self.client.post("/api/webhooks/whatsapp", json=payload)
    
    # Target: 1000 RPS durante 10 minutos
```

**Criterios de Éxito**:
- [ ] Sistema maneja 1000 RPS sin crashes
- [ ] P95 latency <500ms bajo load
- [ ] Error rate <0.5%

---

### 10.2 Stress Testing

**Objetivo**: Encontrar límites del sistema
```bash
✅ Incrementar load hasta fallo
✅ Identificar punto de ruptura
✅ Validar recovery automático
```

**Criterios de Éxito**:
- [ ] Capacidad máxima documentada
- [ ] Sistema se recupera después de stress
- [ ] Alertas funcionan correctamente

---

### 10.3 Production Readiness Checklist

```markdown
## Infrastructure
- [ ] 7 servicios Docker corriendo
- [ ] Health checks passing
- [ ] Backups configurados

## Testing
- [ ] Coverage ≥85%
- [ ] 100% tests passing
- [ ] E2E tests validados

## Performance
- [ ] P95 latency <200ms
- [ ] Throughput >500 RPS
- [ ] Database optimizada

## Observability
- [ ] 5 dashboards Grafana
- [ ] 10+ alertas Prometheus
- [ ] Tracing funcionando

## Security
- [ ] 0 CRITICAL CVEs
- [ ] OWASP Top 10 mitigado
- [ ] Secrets rotados

## Documentation
- [ ] README completo
- [ ] Runbooks operacionales
- [ ] API docs en /docs
```

---

## 🎯 PLAN DE EJECUCIÓN

### Semana 1: Foundation (CRÍTICO)
```
Día 1-2: MÓDULO 1 (Tests + Coverage)
  - Reparar tests rotos
  - Aumentar coverage a 70%+

Día 3-4: MÓDULO 2 (Performance)
  - Baseline + optimizaciones
  - P95 <200ms

Día 5: MÓDULO 3 (Database)
  - Índices + migraciones
```

### Semana 2: Refinamiento
```
Día 6-7: MÓDULO 4 (Observability)
  - Dashboards + alertas

Día 8: MÓDULO 5 (Resilience)
  - Chaos engineering

Día 9: MÓDULO 6 (Documentation)
  - ADRs + runbooks

Día 10: MÓDULO 10 (Validation)
  - Load testing + checklist final
```

---

## 📊 MÉTRICAS DE ÉXITO

### KPIs Principales

| Métrica | Baseline | Objetivo | Status |
|---------|----------|----------|--------|
| Test Coverage | 31% | 85% | 🔴 |
| Tests Passing | 3.1% | 100% | 🔴 |
| P95 Latency | TBD | <200ms | 🟡 |
| CVEs CRITICAL | 0 | 0 | ✅ |
| Docs Coverage | 60% | 95% | 🟡 |
| Uptime | TBD | 99.5% | 🟡 |

### Definition of Done (DoD)

```markdown
✅ Sistema considera "0 kilómetros" cuando:

1. Tests
   - [ ] Coverage ≥85% en servicios críticos
   - [ ] Coverage ≥70% global
   - [ ] 100% tests passing

2. Performance
   - [ ] P95 latency <200ms
   - [ ] P99 latency <500ms
   - [ ] Throughput >500 RPS

3. Database
   - [ ] Índices optimizados
   - [ ] Migraciones funcionando
   - [ ] Backups automáticos

4. Observability
   - [ ] 5 dashboards Grafana
   - [ ] 10+ alertas configuradas
   - [ ] Tracing end-to-end

5. Resilience
   - [ ] Circuit breakers validados
   - [ ] Chaos tests passing
   - [ ] Recovery automático

6. Documentation
   - [ ] 10+ ADRs
   - [ ] API docs completa
   - [ ] 5+ runbooks

7. Security
   - [ ] 0 CRITICAL/HIGH CVEs
   - [ ] OWASP Top 10 mitigado
   - [ ] Secrets management

8. Deployment
   - [ ] CI/CD funcionando
   - [ ] Canary deployment
   - [ ] Rollback automático
```

---

## 🚀 INICIO DE EJECUCIÓN

**Comando de Inicio**:
```bash
# Crear directorio de trabajo
mkdir -p .playbook/blueprint_0km
cd .playbook/blueprint_0km

# Inicializar tracking
cat > progress.md << EOF
# Blueprint 0KM - Progress Tracking

## Fecha Inicio: 2025-11-10

### MÓDULO 1: FOUNDATION (Tests + Coverage)
- [ ] T1.1.1 - Test discovery
- [ ] T1.1.2 - Coverage report
...

EOF

# Ejecutar primera tarea
make test --collect-only > test_inventory.txt
```

---

**Próximo Paso**: Comenzar ejecución MÓDULO 1.1 (Análisis de Tests) 🚀
