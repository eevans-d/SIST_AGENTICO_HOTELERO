# 🚀 ROADMAP DE EJECUCIÓN - Sistema Agente Hotelero IA

**Versión**: 1.0.0  
**Fecha**: 2025-11-14  
**Estado Actual**: Post-H1 (Trace Enrichment completado y funcional)  
**Próximo Milestone**: Sprint 2 - High Availability & Performance  

---

## 📊 ESTADO ACTUAL DEL PROYECTO

### ✅ Completado (Sprint 1)
- **C1: Multi-Tenant Dynamic Resolution** (100%) → Commit 2c9bda8
- **C2: Feature Flags Service** (100%) → Commit 2c9bda8
- **H1: Trace Enrichment** (100%) → Commit 8c29bc5 (PARCHES APLICADOS)
  - ✅ FastAPIInstrumentor activado
  - ✅ Sampler configurado (ParentBased + TraceIdRatioBased)
  - ✅ Config externalizada (OTEL_SERVICE_NAME, TRACE_SAMPLING_RATE)
  - ✅ Tests de integración (13 tests, 12 passed + 1 xfail)

### 📈 Métricas Actuales
- **Tests**: 891 tests totales (28 passing actualmente)
- **Coverage**: 31% (Target: 70% overall, 85% en servicios críticos)
- **CVE Status**: ✅ 0 CRITICAL (python-jose 3.5.0 actualizado)
- **Linting**: ✅ 0 errores (Ruff + gitleaks)
- **Deployment Readiness**: 8.9/10 (staging-ready)

---

## 🎯 HOJA DE RUTA ESTRATÉGICA

### **FASE 1: HIGH AVAILABILITY & RESILIENCE** (Prioridad: CRITICAL)
**Duración Estimada**: 2-3 semanas  
**Objetivo**: Sistema tolerante a fallos con manejo automático de errores

| ID | Tarea | Estimación | Prioridad | Dependencias | Riesgo |
|----|-------|------------|-----------|--------------|--------|
| H2 | Dead Letter Queue (DLQ) | 6-8h | P0 | Redis, Orchestrator | Bajo |
| H3 | Circuit Breaker Metrics Dashboard | 4-6h | P1 | Grafana, Prometheus | Bajo |
| H4 | Async Task Queue (Celery) | 8-12h | P1 | Redis, Docker Compose | Medio |

### **FASE 2: CORE FUNCTIONALITY HARDENING** (Prioridad: HIGH)
**Duración Estimada**: 2-3 semanas  
**Objetivo**: Completar funcionalidad core con aislamiento de datos y configuración dinámica

| ID | Tarea | Estimación | Prioridad | Dependencias | Riesgo |
|----|-------|------------|-----------|--------------|--------|
| C3 | Multi-Tenant Database Isolation | 12-16h | P1 | PostgreSQL, Alembic | Alto |
| C4 | Feature Flag UI Admin Panel | 6-8h | P2 | FastAPI, JWT Auth | Bajo |

### **FASE 3: PERFORMANCE OPTIMIZATION** (Prioridad: MEDIUM)
**Duración Estimada**: 2 semanas  
**Objetivo**: Optimizar latencia y throughput para soportar producción

| ID | Tarea | Estimación | Prioridad | Dependencias | Riesgo |
|----|-------|------------|-----------|--------------|--------|
| P1 | Load Testing con Locust | 6-8h | P1 | Locust, staging env | Bajo |
| P2 | Database Query Optimization | 8-12h | P1 | pg_stat_statements | Medio |
| F1 | Audio Processing Optimization | 8-10h | P2 | Whisper, Redis cache | Medio |
| F2 | NLP Intent Confidence Tuning | 6-8h | P2 | NLP Engine, A/B testing | Medio |

### **FASE 4: SECURITY HARDENING** (Prioridad: HIGH)
**Duración Estimada**: 1-2 semanas  
**Objetivo**: Reforzar seguridad para compliance y auditorías

| ID | Tarea | Estimación | Prioridad | Dependencias | Riesgo |
|----|-------|------------|-----------|--------------|--------|
| S1 | Secrets Management con Vault | 10-12h | P1 | HashiCorp Vault, Docker | Medio |
| S2 | API Rate Limiting por Tenant | 6-8h | P1 | Redis, slowapi | Bajo |

### **FASE 5: DEPLOYMENT AUTOMATION** (Prioridad: HIGH)
**Duración Estimada**: 2-3 semanas  
**Objetivo**: CI/CD completo con deployment a staging/producción automatizado

| ID | Tarea | Estimación | Prioridad | Dependencias | Riesgo |
|----|-------|------------|-----------|--------------|--------|
| D1 | Automated Deployment Pipeline (CI/CD) | 12-16h | P0 | GitHub Actions | Medio |
| D2 | Kubernetes Manifests + Helm Charts | 16-20h | P2 | K8s cluster, Helm | Alto |

### **FASE 6: OBSERVABILITY & MONITORING** (Prioridad: MEDIUM)
**Duración Estimada**: 1-2 semanas  
**Objetivo**: Visibilidad completa del sistema con SLOs y alertas

| ID | Tarea | Estimación | Prioridad | Dependencias | Riesgo |
|----|-------|------------|-----------|--------------|--------|
| M1 | SLO Dashboard + Alerting | 8-10h | P1 | Grafana, AlertManager | Bajo |
| M2 | Log Aggregation con ELK/Loki | 10-12h | P2 | Loki/ElasticSearch | Medio |

### **FASE 7: TESTING AUTOMATION** (Prioridad: MEDIUM)
**Duración Estimada**: 2 semanas  
**Objetivo**: Coverage 70%+ con tests automatizados

| ID | Tarea | Estimación | Prioridad | Dependencias | Riesgo |
|----|-------|------------|-----------|--------------|--------|
| T1 | E2E Tests con Playwright | 12-16h | P1 | Playwright, mock PMS | Medio |
| T2 | Contract Testing con Pact | 8-10h | P2 | Pact framework | Medio |

### **FASE 8: OPERATIONS & MAINTENANCE** (Prioridad: MEDIUM)
**Duración Estimada**: 1 semana  
**Objetivo**: Procedimientos operacionales para incidentes y recuperación

| ID | Tarea | Estimación | Prioridad | Dependencias | Riesgo |
|----|-------|------------|-----------|--------------|--------|
| O1 | Database Backup & Recovery | 6-8h | P1 | S3, pg_dump scripts | Bajo |
| O2 | Incident Response Runbooks | 4-6h | P1 | docs/runbooks/ | Bajo |

---

## 🔷 BLUEPRINT TÉCNICO DETALLADO

### **H2: DEAD LETTER QUEUE (DLQ)** 🎯 PRÓXIMA TAREA

#### Objetivo
Implementar cola de mensajes fallidos con retry automático para manejar errores transitorios en procesamiento de mensajes (WhatsApp, Gmail, SMS).

#### Arquitectura
```
MessageGateway → Orchestrator
       ↓ (error)
   DLQService
       ↓
   Redis List (dlq:messages)
       ↓ (retry worker cada 5min)
   RetryWorker → Orchestrator (reintento)
       ↓ (3 fallos)
   Permanent Failure Store (PostgreSQL)
```

#### Componentes Nuevos

**1. DLQService** (`app/services/dlq_service.py`)
```python
class DLQService:
    """Redis-backed Dead Letter Queue para mensajes fallidos."""
    
    async def enqueue_failed_message(
        self,
        message: UnifiedMessage,
        error: Exception,
        retry_count: int = 0
    ) -> str:
        """Agrega mensaje fallido a DLQ con metadata de error."""
        
    async def get_retry_candidates(self) -> List[DLQEntry]:
        """Obtiene mensajes listos para retry (backoff exponencial)."""
        
    async def retry_message(self, dlq_id: str) -> bool:
        """Reintenta procesar mensaje desde DLQ."""
        
    async def mark_permanent_failure(self, dlq_id: str) -> None:
        """Marca mensaje como fallido permanentemente (→ PostgreSQL)."""
```

**2. RetryWorker** (background task en `app/main.py` lifespan)
```python
async def dlq_retry_worker():
    """Worker que reintenta mensajes de DLQ cada 5 minutos."""
    while True:
        candidates = await dlq_service.get_retry_candidates()
        for entry in candidates:
            await dlq_service.retry_message(entry.id)
        await asyncio.sleep(300)  # 5 minutos
```

**3. DLQ Model** (`app/models/dlq.py`)
```python
class DLQEntry(Base):
    __tablename__ = "dlq_permanent_failures"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    message_data: Mapped[dict] = mapped_column(JSON)
    error_message: Mapped[str]
    error_traceback: Mapped[str]
    retry_count: Mapped[int] = mapped_column(default=0)
    first_failed_at: Mapped[datetime]
    last_retry_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

#### Configuración

**Env Vars**:
- `DLQ_MAX_RETRIES=3` - Máximo de reintentos antes de fallo permanente
- `DLQ_RETRY_BACKOFF_BASE=60` - Backoff base en segundos (60 → 120 → 240)
- `DLQ_TTL_DAYS=7` - TTL de mensajes en Redis antes de expirar
- `DLQ_WORKER_INTERVAL=300` - Intervalo del retry worker en segundos

**Redis Keys**:
- `dlq:messages:{message_id}` - Hash con message data + metadata
- `dlq:retry_schedule` - Sorted set (score = timestamp retry)
- `dlq:stats:total` - Counter total mensajes en DLQ
- `dlq:stats:permanent` - Counter fallos permanentes

#### Métricas Prometheus
```python
dlq_messages_total = Counter("dlq_messages_total", "Total mensajes en DLQ", ["reason"])
dlq_retries_total = Counter("dlq_retries_total", "Total reintentos", ["result"])
dlq_permanent_failures_total = Counter("dlq_permanent_failures_total", "Fallos permanentes")
dlq_retry_latency_seconds = Histogram("dlq_retry_latency_seconds", "Latencia de reintentos")
dlq_queue_size = Gauge("dlq_queue_size", "Tamaño actual de DLQ")
```

#### Tests

**Unit Tests** (`tests/unit/test_dlq.py`):
- `test_enqueue_failed_message` - Valida que mensaje se agrega a Redis
- `test_retry_with_exponential_backoff` - Valida backoff 60s → 120s → 240s
- `test_max_retries_triggers_permanent_failure` - Valida que 3 fallos → PostgreSQL
- `test_retry_success_removes_from_dlq` - Valida que éxito elimina de cola
- `test_dlq_ttl_expiration` - Valida que mensajes expiran después de 7 días

**Integration Tests** (`tests/integration/test_dlq_integration.py`):
- `test_orchestrator_failure_enqueues_to_dlq` - Valida flujo completo error → DLQ
- `test_retry_worker_processes_candidates` - Valida worker automático
- `test_permanent_failure_stored_in_db` - Valida PostgreSQL storage

#### Integración con Orchestrator

**Modificación en `app/services/orchestrator.py`**:
```python
async def process_message(self, message: UnifiedMessage) -> dict:
    try:
        # ... lógica actual
        return await self._handle_intent(message, intent)
    except Exception as e:
        logger.error("message_processing_failed", error=str(e))
        
        # Enqueue to DLQ para retry automático
        await self.dlq_service.enqueue_failed_message(
            message=message,
            error=e,
            retry_count=0
        )
        
        # Return graceful degradation response
        return {
            "response_type": "text",
            "content": {
                "text": "⚠️ Estamos experimentando dificultades técnicas. "
                        "Tu mensaje ha sido guardado y lo procesaremos pronto."
            }
        }
```

#### Criterios de Aceptación
- ✅ Mensajes fallidos se encolan automáticamente en Redis
- ✅ Retry automático con backoff exponencial (60s, 120s, 240s)
- ✅ Después de 3 fallos → PostgreSQL (permanent failure)
- ✅ Worker background procesa cola cada 5 minutos
- ✅ Métricas Prometheus: dlq_queue_size, dlq_retries_total, dlq_permanent_failures_total
- ✅ Tests unitarios: 5 tests passing
- ✅ Tests integración: 3 tests passing
- ✅ Documentación: README-DLQ.md con ejemplos de uso

#### Riesgos y Mitigaciones
| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Redis memory overflow con DLQ grande | Media | Alto | TTL 7 días + monitoring de redis_memory_used |
| Retry storm si muchos mensajes fallan | Baja | Medio | Rate limiting en retry worker (max 10/min) |
| Mensaje corrupto causa loop infinito | Baja | Medio | Schema validation antes de retry |

#### Estimación Detallada
- **Implementación DLQService**: 2-3h
- **RetryWorker + background task**: 1-2h
- **Integración con Orchestrator**: 1h
- **Tests unitarios (5 tests)**: 1-2h
- **Tests integración (3 tests)**: 1-2h
- **Métricas Prometheus**: 30min
- **Documentación**: 1h
- **Testing manual + debugging**: 1h
- **TOTAL**: 6-8h

---

### **H3: CIRCUIT BREAKER METRICS DASHBOARD**

#### Objetivo
Dashboard Grafana para visualizar estado en tiempo real de circuit breakers (PMS, WhatsApp, Gmail) con alertas automáticas cuando se abren.

#### Componentes

**1. Dashboard Grafana** (`docker/grafana/dashboards/circuit_breakers.json`)

**Panels**:
1. **Circuit Breaker States** (Gauge)
   - Query: `pms_circuit_breaker_state` (0=closed, 1=open, 2=half-open)
   - Color: Verde (closed), Rojo (open), Amarillo (half-open)

2. **Circuit Breaker Transitions** (Time Series)
   - Query: `rate(pms_circuit_breaker_calls_total[5m])`
   - Labels: state (closed, open, half_open), result (success, failure)

3. **Failure Rate** (Stat)
   - Query: `rate(pms_circuit_breaker_calls_total{result="failure"}[5m]) / rate(pms_circuit_breaker_calls_total[5m])`
   - Threshold: > 10% = warning, > 30% = critical

4. **Recovery Time** (Histogram)
   - Query: `histogram_quantile(0.95, pms_api_latency_seconds)`
   - Muestra P95 latency durante recovery (half-open → closed)

5. **Open Circuit Breaker Alert** (Alert Panel)
   - Condition: `pms_circuit_breaker_state == 1`
   - Alert: "PMS Circuit Breaker is OPEN - all requests are being rejected"

**2. AlertManager Rules** (`docker/alertmanager/rules/circuit_breakers.yml`)
```yaml
groups:
  - name: circuit_breakers
    interval: 30s
    rules:
      - alert: CircuitBreakerOpen
        expr: pms_circuit_breaker_state == 1
        for: 1m
        labels:
          severity: critical
          component: pms_adapter
        annotations:
          summary: "Circuit Breaker is OPEN"
          description: "PMS circuit breaker has been open for >1 minute. All PMS calls are failing."
          
      - alert: CircuitBreakerHighFailureRate
        expr: rate(pms_circuit_breaker_calls_total{result="failure"}[5m]) > 0.3
        for: 5m
        labels:
          severity: warning
          component: pms_adapter
        annotations:
          summary: "High failure rate detected"
          description: "Circuit breaker failure rate >30% for 5 minutes."
```

#### Integración
- Dashboard auto-importado al iniciar Grafana (via provisioning)
- Alertas enviadas a AlertManager → Slack/Email (configurar webhook)
- Métricas ya existentes en `pms_adapter.py` (implementado en H1)

#### Criterios de Aceptación
- ✅ Dashboard muestra estado de CB en tiempo real
- ✅ Alerta automática cuando CB se abre (>1 min)
- ✅ Historial de transiciones visible en panel time series
- ✅ Documentación con screenshots en README-Infra.md

#### Estimación
- Dashboard JSON + provisioning: 2h
- AlertManager rules: 1h
- Testing con circuit breaker simulado: 1-2h
- Documentación + screenshots: 1h
- **TOTAL**: 4-6h

---

### **H4: ASYNC TASK QUEUE CON CELERY**

#### Objetivo
Implementar Celery + Redis para tareas asíncronas (notificaciones email, recordatorios de reserva, reportes periódicos) que no bloquean el request HTTP.

#### Arquitectura
```
FastAPI Endpoint → Celery Task (async)
                        ↓
                   Redis (broker)
                        ↓
                 Celery Worker(s)
                        ↓
          Gmail/SMTP (notificaciones)
```

#### Componentes

**1. Celery App** (`app/tasks/__init__.py`)
```python
from celery import Celery

celery_app = Celery(
    "agente-hotel-tasks",
    broker="redis://redis:6379/1",
    backend="redis://redis:6379/2"
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutos max
    worker_prefetch_multiplier=4,
)
```

**2. Task Definitions** (`app/tasks/notifications.py`)
```python
from app.tasks import celery_app
from app.services.gmail_client import GmailClient

@celery_app.task(bind=True, max_retries=3)
def send_reservation_confirmation(self, guest_email: str, reservation_data: dict):
    """Envía email de confirmación de reserva."""
    try:
        gmail = GmailClient()
        gmail.send_confirmation_email(guest_email, reservation_data)
    except Exception as exc:
        # Retry con backoff exponencial
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@celery_app.task
def send_check_in_reminder(guest_email: str, check_in_date: str):
    """Envía recordatorio 24h antes del check-in."""
    gmail = GmailClient()
    gmail.send_reminder_email(guest_email, check_in_date)

@celery_app.task
def generate_daily_report():
    """Genera reporte diario de reservas (ejecutado por Celery Beat)."""
    # ... lógica de reporte
```

**3. Celery Worker Service** (agregar a `docker-compose.yml`)
```yaml
celery-worker:
  build:
    context: .
    dockerfile: Dockerfile
  command: celery -A app.tasks worker --loglevel=info --concurrency=4
  depends_on:
    - redis
    - postgres
  environment:
    - REDIS_URL=redis://redis:6379/1
    - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/agente_db
  volumes:
    - ./app:/app/app
  networks:
    - agente-network

celery-beat:
  build:
    context: .
    dockerfile: Dockerfile
  command: celery -A app.tasks beat --loglevel=info
  depends_on:
    - redis
  environment:
    - REDIS_URL=redis://redis:6379/1
  networks:
    - agente-network
```

**4. Integración con Orchestrator** (`app/services/orchestrator.py`)
```python
from app.tasks.notifications import send_reservation_confirmation

async def _handle_reservation_confirmed(self, message: UnifiedMessage, reservation: dict):
    # ... lógica de reserva
    
    # Enviar confirmación async (no bloquea response)
    send_reservation_confirmation.delay(
        guest_email=message.sender_id,
        reservation_data=reservation
    )
    
    return {
        "response_type": "text",
        "content": {
            "text": f"✅ Reserva confirmada! Te enviaremos un email a {message.sender_id}."
        }
    }
```

**5. Scheduled Tasks** (`app/tasks/beat_schedule.py`)
```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'send-check-in-reminders': {
        'task': 'app.tasks.notifications.send_check_in_reminder',
        'schedule': crontab(hour=10, minute=0),  # Diario 10:00 AM
    },
    'generate-daily-report': {
        'task': 'app.tasks.notifications.generate_daily_report',
        'schedule': crontab(hour=23, minute=0),  # Diario 11:00 PM
    },
}
```

#### Métricas Prometheus

**Celery Exporter** (agregar a `docker-compose.yml`):
```yaml
celery-exporter:
  image: danihodovic/celery-exporter:latest
  command: --broker-url=redis://redis:6379/1
  ports:
    - "9808:9808"
  depends_on:
    - redis
  networks:
    - agente-network
```

**Métricas disponibles**:
- `celery_tasks_total{state="SUCCESS|FAILURE|RETRY"}` - Counter de tareas
- `celery_task_latency_seconds` - Histogram de latencia
- `celery_workers_active` - Gauge de workers activos
- `celery_queue_length` - Gauge de tareas pendientes

#### Tests

**Unit Tests** (`tests/unit/test_tasks.py`):
- `test_send_reservation_confirmation_success` - Valida que task envía email
- `test_send_reservation_confirmation_retry_on_failure` - Valida retry con backoff
- `test_scheduled_task_runs_at_correct_time` - Valida crontab schedule

**Integration Tests** (`tests/integration/test_celery_integration.py`):
- `test_task_enqueued_and_processed` - Valida flujo completo FastAPI → Celery
- `test_task_failure_retries_exponentially` - Valida retry logic

#### Criterios de Aceptación
- ✅ Celery worker procesa tareas async (no bloquea HTTP response)
- ✅ Retry automático con backoff exponencial (60s, 120s, 240s)
- ✅ Celery Beat ejecuta tareas programadas (recordatorios, reportes)
- ✅ Métricas en Prometheus: celery_tasks_total, celery_task_latency_seconds
- ✅ 2 workers concurrentes mínimo (configurable)
- ✅ Tests: 3 unit + 2 integration passing

#### Estimación
- Celery setup + config: 2h
- Task definitions (3 tasks): 2-3h
- Docker Compose integration: 1-2h
- Celery Beat schedule: 1h
- Tests (5 tests): 2-3h
- Métricas + monitoring: 1h
- Documentación: 1h
- **TOTAL**: 8-12h

---

## 📋 CHECKLIST DE EJECUCIÓN

### ✅ Pre-requisitos (Validar Antes de Comenzar)
- [ ] Git branch `main` actualizado (pull latest)
- [ ] Docker Compose UP (7 servicios running)
- [ ] Tests H1 passing (13 tests, 12 passed + 1 xfail)
- [ ] Redis disponible en localhost:6379
- [ ] PostgreSQL disponible en localhost:5432
- [ ] Poetry dependencies instaladas (`poetry install`)

### 🎯 H2: Dead Letter Queue (Checklist Ejecutable)

#### Paso 1: Implementación DLQService (2-3h)
- [ ] Crear `app/services/dlq_service.py`
- [ ] Implementar `DLQService` class con métodos:
  - [ ] `enqueue_failed_message(message, error, retry_count)`
  - [ ] `get_retry_candidates()` - Query Redis sorted set
  - [ ] `retry_message(dlq_id)` - Reintentar mensaje
  - [ ] `mark_permanent_failure(dlq_id)` - Mover a PostgreSQL
- [ ] Implementar backoff exponencial: 60s → 120s → 240s
- [ ] Agregar Redis keys:
  - [ ] `dlq:messages:{message_id}` - Hash
  - [ ] `dlq:retry_schedule` - Sorted set (score = retry timestamp)
  - [ ] `dlq:stats:total` - Counter

#### Paso 2: DLQ Model (30min)
- [ ] Crear `app/models/dlq.py`
- [ ] Implementar `DLQEntry` SQLAlchemy model:
  - [ ] Campos: id, message_data (JSON), error_message, retry_count, timestamps
  - [ ] Index en `created_at` para queries
- [ ] Crear migración Alembic: `alembic revision -m "add_dlq_table"`
- [ ] Aplicar migración: `alembic upgrade head`

#### Paso 3: RetryWorker (1-2h)
- [ ] Modificar `app/main.py` lifespan:
  - [ ] Agregar `dlq_retry_worker()` async task
  - [ ] Background task ejecuta cada 5 minutos
- [ ] Implementar worker logic:
  - [ ] Query `get_retry_candidates()`
  - [ ] Retry cada candidato con `retry_message()`
  - [ ] Logging de resultados

#### Paso 4: Integración con Orchestrator (1h)
- [ ] Modificar `app/services/orchestrator.py`:
  - [ ] Agregar `self.dlq_service = DLQService()`
  - [ ] Try/except en `process_message()`:
    - [ ] On error → `dlq_service.enqueue_failed_message()`
    - [ ] Return graceful degradation response
- [ ] Validar que orchestrator no lanza excepciones sin capturar

#### Paso 5: Configuración (30min)
- [ ] Agregar env vars a `app/core/settings.py`:
  - [ ] `DLQ_MAX_RETRIES: int = 3`
  - [ ] `DLQ_RETRY_BACKOFF_BASE: int = 60`
  - [ ] `DLQ_TTL_DAYS: int = 7`
  - [ ] `DLQ_WORKER_INTERVAL: int = 300`
- [ ] Actualizar `.env.example` con valores por defecto
- [ ] Documentar env vars en README-DLQ.md

#### Paso 6: Métricas Prometheus (30min)
- [ ] Crear `app/monitoring/dlq_metrics.py`:
  - [ ] `dlq_messages_total` Counter (label: reason)
  - [ ] `dlq_retries_total` Counter (label: result=success|failure)
  - [ ] `dlq_permanent_failures_total` Counter
  - [ ] `dlq_retry_latency_seconds` Histogram
  - [ ] `dlq_queue_size` Gauge
- [ ] Integrar métricas en `DLQService` methods
- [ ] Validar que Prometheus scrape las métricas (http://localhost:9090)

#### Paso 7: Tests Unitarios (1-2h)
- [ ] Crear `tests/unit/test_dlq.py`
- [ ] Implementar tests:
  - [ ] `test_enqueue_failed_message` - Valida Redis hash created
  - [ ] `test_retry_with_exponential_backoff` - Valida 60s → 120s → 240s
  - [ ] `test_max_retries_triggers_permanent_failure` - Valida 3 fallos → DB
  - [ ] `test_retry_success_removes_from_dlq` - Valida cleanup
  - [ ] `test_dlq_ttl_expiration` - Valida TTL 7 días
- [ ] Ejecutar: `pytest tests/unit/test_dlq.py -v`
- [ ] Target: 5/5 tests passing

#### Paso 8: Tests Integración (1-2h)
- [ ] Crear `tests/integration/test_dlq_integration.py`
- [ ] Implementar tests:
  - [ ] `test_orchestrator_failure_enqueues_to_dlq` - Flujo completo
  - [ ] `test_retry_worker_processes_candidates` - Worker automático
  - [ ] `test_permanent_failure_stored_in_db` - PostgreSQL persistence
- [ ] Ejecutar: `pytest tests/integration/test_dlq_integration.py -v`
- [ ] Target: 3/3 tests passing

#### Paso 9: Documentación (1h)
- [ ] Crear `agente-hotel-api/README-DLQ.md`:
  - [ ] Arquitectura con diagrama
  - [ ] Configuración env vars
  - [ ] Ejemplos de uso
  - [ ] Troubleshooting común
- [ ] Actualizar `docs/VALIDACION_H2_DLQ.md` con evidencia
- [ ] Agregar sección DLQ a `.github/copilot-instructions.md`

#### Paso 10: Testing Manual + Debugging (1h)
- [ ] Iniciar sistema: `make docker-up`
- [ ] Simular fallo:
  - [ ] Detener servicio PMS temporalmente
  - [ ] Enviar mensaje WhatsApp test
  - [ ] Validar que mensaje entra en DLQ
- [ ] Verificar retry automático:
  - [ ] Reiniciar PMS
  - [ ] Esperar 60s (primer retry)
  - [ ] Validar que mensaje se procesa exitosamente
- [ ] Verificar métricas:
  - [ ] Prometheus: `dlq_messages_total`, `dlq_queue_size`
  - [ ] Logs: Buscar "dlq_message_enqueued"

#### Paso 11: Commit & Push (15min)
- [ ] Commit con mensaje descriptivo:
  ```bash
  git add .
  git commit -m "feat(H2): Implement Dead Letter Queue with retry logic
  
  - DLQService with Redis-backed queue
  - Exponential backoff retry (60s → 120s → 240s)
  - Permanent failure storage in PostgreSQL
  - Background retry worker (5min interval)
  - Prometheus metrics: dlq_queue_size, dlq_retries_total
  - Tests: 5 unit + 3 integration (8/8 passing)
  
  Closes #H2"
  ```
- [ ] Push a main: `git push origin main`
- [ ] Validar CI/CD (si configurado)

#### Paso 12: Actualizar Roadmap (5min)
- [ ] Marcar H2 como ✅ Completado en `ROADMAP_EXECUTION_BLUEPRINT.md`
- [ ] Actualizar métricas de progreso:
  - [ ] Tests totales: 891 + 8 = 899
  - [ ] Coverage estimado: 31% → 34%
- [ ] Commit roadmap: `git commit -m "docs: Update roadmap - H2 completed"`

---

## 🚦 CRITERIOS DE CALIDAD (Aplicar a Cada Tarea)

### Code Quality
- [ ] Linting: `make lint` → 0 errores
- [ ] Format: `make fmt` → código formateado
- [ ] Type hints: Todas las funciones tipadas (mypy compatible)
- [ ] Docstrings: Todas las clases/métodos documentados (Google style)

### Testing
- [ ] Unit tests: Coverage ≥ 80% del código nuevo
- [ ] Integration tests: Flujos end-to-end validados
- [ ] All tests passing: `make test` → 100% success rate
- [ ] Performance: Tests ejecutan en < 10s (excluir E2E)

### Security
- [ ] Secret scan: `make lint` (gitleaks) → 0 secrets expuestos
- [ ] CVE scan: `make security-fast` → 0 CRITICAL
- [ ] Input validation: Todos los inputs validados (Pydantic)
- [ ] Error handling: Excepciones capturadas, no exponen detalles internos

### Observability
- [ ] Logging: Structured logs (JSON) con correlation_id
- [ ] Metrics: Prometheus counters/histograms/gauges
- [ ] Tracing: OpenTelemetry spans con business context
- [ ] Alerting: AlertManager rules para errores críticos

### Documentation
- [ ] README actualizado con nueva funcionalidad
- [ ] Validation docs con evidencia (screenshots, logs)
- [ ] Copilot instructions actualizadas
- [ ] Inline comments en código complejo

---

## 📊 MÉTRICAS DE PROGRESO

### Objetivos de Cobertura
```
ACTUAL:      ████░░░░░░░░░░░░░░░░ 31%
TARGET:      ██████████████░░░░░░ 70%
CRÍTICOS:    █████████████████░░░ 85%
```

### Distribución de Esfuerzo por Fase
| Fase | Estimación | Prioridad | % Total |
|------|------------|-----------|---------|
| FASE 1: High Availability | 18-26h | CRITICAL | 20% |
| FASE 2: Core Hardening | 18-24h | HIGH | 18% |
| FASE 3: Performance | 28-38h | MEDIUM | 30% |
| FASE 4: Security | 16-20h | HIGH | 16% |
| FASE 5: Deployment | 28-36h | HIGH | 28% |
| FASE 6: Observability | 18-22h | MEDIUM | 18% |
| FASE 7: Testing | 20-26h | MEDIUM | 20% |
| FASE 8: Operations | 10-14h | MEDIUM | 11% |
| **TOTAL** | **156-206h** | - | **100%** |

### Timeline Proyectado
```
Semana 1-2:   FASE 1 (H2, H3, H4)                    [██████████░░░░░░░░░░░░]
Semana 3-4:   FASE 2 (C3, C4)                        [░░░░░░░░░░██████████░░]
Semana 5-6:   FASE 3 (P1, P2, F1, F2)                [░░░░░░░░░░░░░░░░░░████]
Semana 7:     FASE 4 (S1, S2)                        [██████░░░░░░░░░░░░░░░░]
Semana 8-10:  FASE 5 (D1, D2)                        [░░░░░░████████████░░░░]
Semana 11:    FASE 6 (M1, M2)                        [░░░░░░░░░░░░██████░░░░]
Semana 12-13: FASE 7 (T1, T2)                        [░░░░░░░░░░░░░░░░██████]
Semana 14:    FASE 8 (O1, O2) + BUFFER               [░░░░░░░░░░░░░░░░░░░███]
```

---

## 🎯 PRÓXIMA ACCIÓN INMEDIATA

### **COMENZAR CON: H2 - DEAD LETTER QUEUE**

**Comando de inicio**:
```bash
cd agente-hotel-api

# 1. Crear branch de feature
git checkout -b feature/h2-dead-letter-queue

# 2. Crear estructura de archivos
mkdir -p app/services app/models tests/unit tests/integration app/monitoring
touch app/services/dlq_service.py
touch app/models/dlq.py
touch tests/unit/test_dlq.py
touch tests/integration/test_dlq_integration.py
touch app/monitoring/dlq_metrics.py

# 3. Validar que tests actuales pasan
make test

# 4. Comenzar implementación
```

**Primera tarea técnica**:
Implementar `DLQService` class con método `enqueue_failed_message()` que:
1. Genera UUID para `dlq_id`
2. Serializa `UnifiedMessage` a JSON
3. Crea Redis hash: `dlq:messages:{dlq_id}`
4. Agrega a sorted set: `dlq:retry_schedule` (score = current_time + backoff)
5. Incrementa counter: `dlq:stats:total`
6. Log structured: `logger.info("dlq_message_enqueued", dlq_id=..., reason=...)`

**Archivo a crear primero**: `app/services/dlq_service.py` (líneas 1-50)

---

## 📞 SOPORTE Y ESCALACIÓN

### Si encuentras bloqueadores:
1. **Redis connection issues**: Verificar `docker-compose ps` → redis debe estar UP
2. **PostgreSQL migration errors**: `alembic downgrade -1` → fix → `alembic upgrade head`
3. **Tests failing**: Aislar test con `pytest -k test_name -vv` → revisar traceback
4. **Performance degradation**: `make docker-logs` → buscar slow queries/errors

### Contactos:
- **Backend Lead**: Para decisiones arquitectónicas
- **DevOps**: Para issues de Docker/deployment
- **QA**: Para validación de tests E2E

---

**Documento creado**: 2025-11-14  
**Próxima revisión**: Después de completar FASE 1 (H2, H3, H4)  
**Mantenido por**: Backend AI Team
