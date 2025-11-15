# Plan de Ejecución: H3 + Tests H2 + M1

**Fecha**: 2025-11-14  
**Estado**: Listo para ejecutar  
**Duración estimada total**: 14-24 horas

---

## ✅ VERIFICACIÓN PREVIA COMPLETADA

### Métricas existentes confirmadas:
- ✅ `pms_circuit_breaker_state` (Gauge: 0/1/2)
- ✅ `pms_api_latency_seconds` (Histogram)
- ✅ `pms_circuit_breaker_calls_total{state, result}` (Counter)
- ✅ `pms_circuit_breaker_failure_streak` (Gauge)
- ✅ `orchestrator_latency_seconds` (Histogram)
- ✅ `http_requests_total{method, endpoint, status_code}` (Counter)
- ✅ Prometheus ya configurado (`docker/prometheus/prometheus.yml`)
- ✅ AlertManager operativo (`alert_rules.yml` existente)
- ✅ Grafana con dashboards base (`docker/grafana/dashboards/`)

---

## 🎯 OPCIÓN 1: H3 - Circuit Breaker Dashboard

**Objetivo**: Dashboard Grafana + alertas para visualizar estado del Circuit Breaker del PMS.  
**Duración**: 4-6h  
**Prioridad**: P0 (crítico)

### Tareas H3

#### 1. Dashboard Grafana (2-3h)
**Archivo**: `docker/grafana/dashboards/h3-circuit-breaker.json`

```json
{
  "title": "H3 - Circuit Breaker Dashboard",
  "panels": [
    {
      "title": "CB State",
      "targets": [{"expr": "pms_circuit_breaker_state"}],
      "type": "stat",
      "mappings": [
        {"value": 0, "text": "CLOSED", "color": "green"},
        {"value": 1, "text": "OPEN", "color": "red"},
        {"value": 2, "text": "HALF-OPEN", "color": "yellow"}
      ]
    },
    {
      "title": "CB State Timeline",
      "targets": [{"expr": "pms_circuit_breaker_state"}],
      "type": "timeseries"
    },
    {
      "title": "PMS Latency P95",
      "targets": [{
        "expr": "histogram_quantile(0.95, sum(rate(pms_api_latency_seconds_bucket[5m])) by (le, endpoint))"
      }],
      "type": "timeseries"
    },
    {
      "title": "PMS Error Rate",
      "targets": [{
        "expr": "sum(rate(pms_circuit_breaker_calls_total{result=\"failure\"}[5m])) / sum(rate(pms_circuit_breaker_calls_total[5m]))"
      }],
      "type": "timeseries"
    },
    {
      "title": "Failure Streak",
      "targets": [{"expr": "pms_circuit_breaker_failure_streak"}],
      "type": "graph"
    }
  ]
}
```

**Checklist Dashboard**:
- [ ] Crear archivo JSON completo
- [ ] Añadir a provisioning: `docker/grafana/provisioning/dashboards/default.yml`
- [ ] Restart Grafana: `docker compose restart grafana`
- [ ] Validar visualización en `http://localhost:3000`

#### 2. Alertas Prometheus (1-2h)
**Archivo**: `docker/prometheus/alert_rules.yml` (ya existe, añadir reglas)

**Reglas a añadir**:

```yaml
# H3: Circuit Breaker Alerts
- alert: PMSCircuitBreakerOpenExtended
  expr: pms_circuit_breaker_state == 1
  for: 5m
  labels:
    severity: critical
    component: pms_adapter
  annotations:
    summary: "PMS Circuit Breaker OPEN por >5min"
    
- alert: PMSHighFailureStreak
  expr: pms_circuit_breaker_failure_streak >= 3
  for: 2m
  labels:
    severity: warning
    component: pms_adapter

- alert: PMSLatencyP95High
  expr: histogram_quantile(0.95, sum(rate(pms_api_latency_seconds_bucket[5m])) by (le)) > 2
  for: 5m
  labels:
    severity: warning
```

**Checklist Alertas**:
- [ ] Editar `alert_rules.yml` (ya tiene alerta básica PMSCircuitBreakerOpen)
- [ ] Añadir reglas extendidas arriba
- [ ] Reload Prometheus: `curl -X POST http://localhost:9090/-/reload`
- [ ] Validar en `http://localhost:9090/alerts`

#### 3. Validación H3 (1h)
- [ ] Levantar stack: `make docker-up`
- [ ] Simular PMS failure (detener servicio PMS o inyectar errores)
- [ ] Confirmar `pms_circuit_breaker_state` → 1 (OPEN)
- [ ] Ver dashboard en Grafana
- [ ] Confirmar alerta dispara en AlertManager (`http://localhost:9093`)
- [ ] Documentar queries en `README-Infra.md`

---

## 🧪 OPCIÓN 2: Tests H2 - DLQ Integration

**Objetivo**: Completar tests de integración DLQ, subir coverage 22% → 25%+.  
**Duración**: 2-3h  
**Prioridad**: P1

### Estado Actual Tests
- Unit: 5/7 passing (2 xfail orchestrator-dependent)
- Integration: 1/6 passing (5 pendientes por mocking)

### Tareas Tests H2

#### 1. Fix Integration Tests (2h)
**Archivo**: `tests/integration/test_dlq_integration.py`

**Tests a arreglar**:

```python
# test_retry_worker_processes_candidates
# Fix: Mock orchestrator.process_message() para retorno exitoso

@pytest.mark.asyncio
async def test_retry_worker_processes_candidates(dlq_service, mock_redis):
    # Enqueue mensaje con retry_at pasado
    dlq_id = str(uuid4())
    await dlq_service.enqueue_failed_message(
        message=sample_message(),
        error="PMS timeout",
        retry_count=0
    )
    
    # Mock orchestrator
    with patch('app.services.orchestrator.Orchestrator.process_message') as mock_process:
        mock_process.return_value = {"response_type": "text", "content": {"text": "OK"}}
        
        # Ejecutar retry
        success = await dlq_service.retry_message(dlq_id)
        assert success is True
        
        # Verificar eliminado de cola
        candidates = await dlq_service.get_retry_candidates()
        assert len(candidates) == 0
```

**Checklist Integration Tests**:
- [ ] `test_retry_worker_processes_candidates` → Mock orchestrator
- [ ] `test_permanent_failure_after_max_retries` → Simular 3 fallos, verificar DB
- [ ] `test_dlq_metrics_exported` → AsyncClient GET /metrics, buscar `dlq_messages_total`
- [ ] `test_nlp_failure_enqueues_to_dlq` → Mock NLP exception
- [ ] `test_audio_processing_failure_enqueues_to_dlq` → Mock AudioProcessor exception

#### 2. Ejecutar Migración Alembic (15min)
```bash
alembic upgrade head  # Crea tabla dlq_permanent_failures
```

#### 3. Validación Coverage (30min)
```bash
poetry run pytest tests/unit/test_dlq.py tests/integration/test_dlq_integration.py -v --cov=app.services.dlq_service --cov=app.models.dlq --cov-report=term-missing
```

**Target**: DLQService ≥80%, Coverage global ≥25%

---

## 📊 OPCIÓN 3: M1 - SLO Dashboard + Alerting

**Objetivo**: Dashboard SLO con availability, latency, error rate + alertas.  
**Duración**: 8-10h  
**Prioridad**: P1

### SLOs Propuestos

| SLO | SLI | Umbral | Ventana |
|-----|-----|--------|---------|
| Availability | `(2xx requests) / total` | ≥99.5% | 30d |
| Latency P95 | `orchestrator_latency P95` | <1s | 5m |
| Error Rate PMS | `PMS failures / total` | <2% | 5m |

### Tareas M1

#### 1. Dashboard SLO Grafana (4-5h)
**Archivo**: `docker/grafana/dashboards/m1-slo-dashboard.json`

**Paneles clave**:

```promql
# SLO Availability (30d rolling)
1 - (
  sum(rate(http_requests_total{status_code!~"2.."}[30d])) 
  / 
  sum(rate(http_requests_total[30d]))
)

# SLO Latency P95 (5m window)
histogram_quantile(
  0.95, 
  sum(rate(orchestrator_latency_seconds_bucket[5m])) by (le)
)

# SLO Error Rate PMS
sum(rate(pms_circuit_breaker_calls_total{result="failure"}[5m])) 
/ 
sum(rate(pms_circuit_breaker_calls_total[5m]))
```

**Checklist Dashboard**:
- [ ] Panel 1: Availability 30d (gauge + timeline)
- [ ] Panel 2: Latency P95 (graph con threshold 1s)
- [ ] Panel 3: Error Rate PMS (graph con threshold 2%)
- [ ] Panel 4: SLO Budget Burn Rate (advanced)
- [ ] Añadir a provisioning Grafana

#### 2. Alertas SLO (2-3h)
**Archivo**: `docker/prometheus/slo_alerts.yml` (nuevo)

```yaml
groups:
  - name: slo_violations
    interval: 60s
    rules:
      - alert: SLOAvailabilityViolation
        expr: (1 - (sum(rate(http_requests_total{status_code!~"2.."}[5m])) / sum(rate(http_requests_total[5m])))) < 0.995
        for: 15m
        labels:
          severity: critical
          slo: availability
        annotations:
          summary: "SLO Availability <99.5% por 15min"
          
      - alert: SLOLatencyViolation
        expr: histogram_quantile(0.95, sum(rate(orchestrator_latency_seconds_bucket[5m])) by (le)) > 1
        for: 10m
        labels:
          severity: warning
          slo: latency
          
      - alert: SLOErrorRateViolation
        expr: sum(rate(pms_circuit_breaker_calls_total{result="failure"}[5m])) / sum(rate(pms_circuit_breaker_calls_total[5m])) > 0.02
        for: 10m
        labels:
          severity: warning
          slo: error_rate
```

**Checklist Alertas**:
- [ ] Crear `slo_alerts.yml`
- [ ] Añadir a `prometheus.yml` rule_files
- [ ] Reload Prometheus
- [ ] Validar en UI

#### 3. Documentación SLO (1-2h)
**Archivo**: `docs/SLO_DEFINITIONS.md` (nuevo)

Incluir:
- Definición de cada SLO
- Fórmula SLI (PromQL)
- Umbrales y justificación
- Procedimiento en caso de violación
- Error Budget tracking

#### 4. Validación M1 (1h)
- [ ] Dashboard visible en Grafana
- [ ] Alertas configuradas en Prometheus
- [ ] Simular carga (opcional: Locust)
- [ ] Confirmar métricas actualizan correctamente

---

## 📅 CRONOGRAMA DE EJECUCIÓN

### Semana 1 (14-16 Nov 2025)
- **Día 1**: H3 Dashboard + Alertas (4-6h)
- **Día 2**: H3 Validación + Tests H2 inicio (3h)

### Semana 2 (17-19 Nov 2025)  
- **Día 3**: Tests H2 completar (2h) + M1 inicio (3h)
- **Día 4**: M1 Dashboard + Alertas (5h)
- **Día 5**: M1 Documentación + Validación (2h)

**Total**: 19-22h distribuidas en 5 días laborales

---

## 🔧 COMANDOS RÁPIDOS

### Setup inicial
```bash
cd agente-hotel-api
make dev-setup
make docker-up
```

### Validar métricas
```bash
curl http://localhost:9090/api/v1/query?query=pms_circuit_breaker_state
curl http://localhost:8002/metrics | grep pms_
```

### Tests
```bash
poetry run pytest tests/unit/test_dlq.py -v
poetry run pytest tests/integration/test_dlq_integration.py -v
poetry run pytest --cov=app --cov-report=term-missing
```

### Reload servicios
```bash
curl -X POST http://localhost:9090/-/reload  # Prometheus
docker compose restart grafana                # Grafana
```

---

## ✅ CRITERIOS DE ACEPTACIÓN

### H3 (Circuit Breaker Dashboard)
- [ ] Dashboard operativo en Grafana
- [ ] 5 paneles funcionando (State, Timeline, Latency, Error Rate, Streak)
- [ ] 3 alertas configuradas (OPEN, Streak, Latency)
- [ ] Validación con simulación PMS failure

### Tests H2 (DLQ)
- [ ] 5 integration tests arreglados (6/6 passing)
- [ ] Coverage DLQService ≥80%
- [ ] Coverage global ≥25%
- [ ] Migración Alembic ejecutada

### M1 (SLO Dashboard)
- [ ] Dashboard SLO con 3 SLIs principales
- [ ] 3 alertas SLO configuradas
- [ ] Documentación SLO completa
- [ ] Métricas validadas en producción simulada

---

## 🚨 RIESGOS Y MITIGACIONES

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Métricas no existen | Baja | Alto | ✅ Verificadas previamente |
| Tests mock complejos | Media | Medio | Usar MockRedis existente |
| Grafana JSON inválido | Baja | Bajo | Validar con schema |
| AlertManager no dispara | Media | Medio | Test con silences temporales |
| Coverage no sube | Media | Medio | Priorizar tests críticos |

---

## 📋 CHECKLIST GENERAL

### Pre-requisitos
- [x] Métricas CB verificadas
- [x] Prometheus operativo
- [x] Grafana accesible
- [x] Tests DLQ revisados
- [ ] Branch feature creado

### Ejecución
- [ ] H3: Dashboard creado
- [ ] H3: Alertas configuradas
- [ ] H3: Validación completa
- [ ] Tests: 5 integration arreglados
- [ ] Tests: Coverage ≥25%
- [ ] M1: Dashboard SLO creado
- [ ] M1: Alertas SLO configuradas
- [ ] M1: Documentación escrita

### Validación Final
- [ ] Todos los dashboards visibles
- [ ] Todas las alertas funcionales
- [ ] Tests passing (≥90%)
- [ ] Coverage target alcanzado
- [ ] Documentación actualizada
- [ ] PR creado y aprobado

---

**Última actualización**: 2025-11-14  
**Responsable**: AI Agent  
**Revisión siguiente**: Post-ejecución H3
