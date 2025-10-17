# 🤖 AI Agent Quick Start Guide

Este documento es para agentes IA (como GitHub Copilot) trabajando en el proyecto Agente Hotelero IA.

## ⚡ 30 Segundos para Entender el Proyecto

**Qué es**: Sistema de recepción hotelera basado en IA que maneja reservas, consultas y servicio al cliente vía WhatsApp/Gmail.

**Stack**: Python 3.12 + FastAPI + PostgreSQL + Redis + Docker (7 servicios)

**Flujo Core**: WhatsApp → Normalizador → NLP (detección intento) → PMS Adapter (integración hotel) → Respuesta

**Estado**: 8.9/10 listo para staging, 31% cobertura de tests, 0 errores críticos

---

## 🎯 Primeros Pasos para AI Agents

### 1. Entender la Arquitectura (5 min)
- Lee: `.github/copilot-instructions.md` sección "Core Patterns"
- Clave: Orquestador coordina todo, PMS Adapter maneja resiliencia
- Patrón: Intent Handler Dispatcher → Async PMS calls → Template Response

### 2. Familiarizarse con la Estructura (5 min)
```
agente-hotel-api/
  app/core/         ← Settings, logging, circuit breaker
  app/services/     ← Orchestrator, PMS adapter, NLP engine
  app/routers/      ← Webhook endpoints
  app/models/       ← Pydantic schemas
  tests/            ← 891 tests (28 pasando)
  docker-compose.yml ← 7 servicios locales
```

### 3. Ejecutar Localmente (10 min)
```bash
cd agente-hotel-api
make dev-setup      # Creates .env
make docker-up      # Starts 7 services
make health         # Verify all healthy
curl http://localhost:8002/health/live  # ✅ 200
```

### 4. Explorar el Código Key
**Comienza aquí** (en orden):
1. `app/services/orchestrator.py` - Lee las líneas 48-100 (patrón dispatcher)
2. `app/services/pms_adapter.py` - Lee líneas 54-120 (circuit breaker)
3. `app/models/unified_message.py` - Schema unificado multi-canal
4. `app/core/settings.py` - Configuración validada

---

## 🚀 Common AI Agent Tasks

### ❌ Tarea: "Arregla el error en el test X"
**Dónde buscar**:
- `tests/` → categoría (unit/integration/e2e/chaos)
- Usa `grep_search` para encontrar referencias del error
- Lee `.github/copilot-instructions.md` sección "Testing Structure"

**Patrón**:
```python
@pytest.mark.asyncio
async def test_my_feature():
    # 1. Setup fixture
    mock_pms = MockPMSAdapter()
    
    # 2. Execute
    result = await orchestrator.handle_message(message)
    
    # 3. Assert
    assert result["response_type"] == "text"
```

### 🔧 Tarea: "Agrega una nueva intención NLP"
**Dónde hacer cambios**:
1. `app/services/orchestrator.py` - Agrega entrada en `_intent_handlers` dict
2. Implementa handler method: `async def _handle_my_intent(...)`
3. Añade tests en `tests/integration/test_orchestrator.py`

**Patrón**:
```python
# En orchestrator.py
self._intent_handlers = {
    "existing_intent": self._handle_existing,
    "my_new_intent": self._handle_my_intent,  # ← ADD HERE
}

async def _handle_my_intent(self, nlp_result, session_data, message):
    """Handle my new intent"""
    # Your logic here
    return {"response_type": "text", "content": response_text}
```

### 📊 Tarea: "Agrega métrica Prometheus"
**Dónde hacer cambios**:
1. Defínela en el service module (e.g., `pms_adapter.py`)
2. Usa labels para dimensiones
3. Documenta en `README-Infra.md`

**Patrón**:
```python
from prometheus_client import Counter, Histogram

my_metric = Counter(
    "my_operation_total",
    "Description of my metric",
    ["status", "endpoint"]  # Labels
)

# Usar:
my_metric.labels(status="success", endpoint="/api/x").inc()
```

### 🔐 Tarea: "Mejora la seguridad del endpoint"
**Dónde hacer cambios**:
1. `app/routers/webhooks.py` - Token validation
2. `app/core/security.py` - Reglas de autorización
3. Usa `@app.state.limiter.limit("120/minute")`

**Patrón**:
```python
@router.post("/api/webhooks/whatsapp")
@app.state.limiter.limit("120/minute")  # Rate limit
async def whatsapp_webhook(
    request: WhatsAppWebhook,
    x_webhook_token: str = Header(...)  # Validate token
):
    verify_signature(request, x_webhook_token)
    return await orchestrator.process_message(request)
```

### 🗄️ Tarea: "Arregla la persistencia de sesiones"
**Dónde buscar**:
1. `app/services/session_manager.py` - Lógica persistencia
2. `app/models/` - ORM models con SQLAlchemy
3. `tests/unit/test_session_manager.py` - Tests

**Key Pattern**: Usa `async with AsyncSessionFactory() as session:`

---

## ⚠️ Critical Anti-Patterns (Don't Do These!)

### ❌ Don't: Import cycles
```python
# BAD - Import cycles in message_gateway.py
from app.services.feature_flag_service import get_feature_flag_service

# GOOD - Use DEFAULT_FLAGS dict
from app.services.feature_flag_service import DEFAULT_FLAGS
use_dynamic = DEFAULT_FLAGS.get("tenancy.dynamic.enabled", True)
```

### ❌ Don't: Sync operations in async code
```python
# BAD - Blocks event loop
session = SessionLocal()
result = session.query(Tenant).first()

# GOOD - Use async
async with AsyncSessionFactory() as session:
    result = await session.execute(select(Tenant))
```

### ❌ Don't: Hardcode secrets
```python
# BAD
API_KEY = "sk_live_12345"

# GOOD - Use SecretStr
API_KEY: SecretStr = Field(default=SecretStr("change-me"))
```

### ❌ Don't: Forget correlation IDs
```python
# BAD - No tracking
response = await client.get("/api/endpoint")

# GOOD - Include correlation ID
response = await client.get(
    "/api/endpoint",
    headers={"X-Request-ID": correlation_id}
)
```

---

## 🧪 Testing Quick Reference

### Run Tests
```bash
make test                    # All tests
make test tests/unit/        # Just unit tests
poetry run pytest tests/integration/ -v  # Integration with verbose
```

### Add a Test
```python
@pytest.mark.asyncio
async def test_my_feature(test_client):  # test_client from conftest.py
    response = await test_client.post(
        "/api/webhook",
        json={"message": "test"}
    )
    assert response.status_code == 200
```

### Mock External Services
```python
from tests.mocks.pms_mock_server import MockPMSAdapter

@pytest.fixture
def mock_pms():
    return MockPMSAdapter()

@pytest.mark.asyncio
async def test_with_mock_pms(mock_pms):
    result = await mock_pms.check_availability(...)
    assert result is not None
```

---

## 🔍 Debugging Common Issues

### Health Check Fails
```bash
curl http://localhost:8002/health/ready | jq .
# Check: postgres, redis, pms status
# Fix: Make sure docker-compose services are running
make health
```

### Tests Failing
```bash
# Check test logs
make test --verbose

# Run specific test
poetry run pytest tests/unit/test_pms_adapter.py::test_circuit_breaker -v

# Check coverage
poetry run pytest --cov=app tests/
```

### Metrics Not Showing
```bash
# Check Prometheus is scraping
curl http://localhost:9090/api/v1/query?query=up

# Check metrics endpoint
curl http://localhost:8002/metrics | grep pms_

# Check Grafana
open http://localhost:3000/d/pms_adapter
```

### Linting Errors
```bash
# Auto-fix
make lint

# Check specific file
ruff check app/services/orchestrator.py --fix

# Format
make fmt
```

---

## 📚 Key Files Reference

| Archivo | Propósito | Líneas Key |
|---------|-----------|-----------|
| `app/main.py` | FastAPI app, lifespan, middleware | 1-50: setup |
| `app/services/orchestrator.py` | Intent routing core logic | 48-100: dispatcher, 200-300: handlers |
| `app/services/pms_adapter.py` | PMS resilience & caching | 54-120: CB setup, 200+: methods |
| `app/core/settings.py` | Configuration validation | 1-100: Pydantic schema |
| `app/models/unified_message.py` | Message normalization | 1-50: schema |
| `tests/conftest.py` | Test fixtures | test_client, mock_pms |
| `Makefile` | Dev commands | 46 targets |
| `.github/copilot-instructions.md` | Full architecture docs | 684 lines |

---

## 🚀 Pre-Deployment Checklist

Antes de hacer PR:
```bash
# 1. Format code
make fmt

# 2. Lint
make lint

# 3. Run tests
make test

# 4. Security scan
make security-fast

# 5. Pre-deploy checks
make pre-deploy-check

# 6. Check coverage (target: 70%+)
poetry run pytest --cov=app tests/ | tail -5
```

---

## 🎓 Learning Path for AI Agents

**Week 1**: Understand Architecture
- Read `.github/copilot-instructions.md` (30 min)
- Trace message flow in `orchestrator.py` (30 min)
- Run local setup and verify health (10 min)

**Week 2**: Make First Changes
- Fix 3 failing tests (find with `grep_search`)
- Add 1 new metric to existing service
- Add 1 new feature flag

**Week 3**: Contribute Features
- Implement new intent handler (3-4 hours)
- Full test coverage for new feature (85%+)
- Document in code + `.github/copilot-instructions.md`

**Week 4+**: Mastery
- Optimize circuit breaker tuning
- Implement resilience improvements
- Reduce test runtime
- Performance profiling

---

## 📞 Questions? Check These Files First

**"Cómo funciona X?"**
- 1. `.github/copilot-instructions.md` (comprehensive)
- 2. `app/main.py` (entry point)
- 3. `README-Infra.md` (infrastructure)
- 4. `docs/` folder (runbooks)

**"Dónde pongo Y?"**
- New service logic → `app/services/`
- New endpoint → `app/routers/`
- New model → `app/models/`
- New utility → `app/utils/`

**"Cómo testeo Z?"**
- Unit test → `tests/unit/test_*.py` (mock dependencies)
- Integration test → `tests/integration/test_*.py` (use fixtures)
- E2E test → `tests/e2e/test_*.py` (full flow)

---

**Last Updated**: 2025-10-17  
**Status**: ✅ Ready for AI collaboration  
**Next Phase**: Staging deployment (tomorrow 09:00)
