# 🤖 AI Agent Contribution Guidelines

Esta guía define cómo los agentes IA deben contribuir código al proyecto Agente Hotelero IA.

## 🎯 Principios de Contribución

### 1. **Prioridad: No Romper Nada**
- ✅ Siempre ejecuta `make test` antes de cualquier commit
- ✅ Mantén o mejora la cobertura (target: 70%+, críticos: 85%+)
- ✅ Ejecuta `make lint` para evitar errores de estilo
- ✅ Verifica `make security-fast` para vulnerabilidades

### 2. **Prioridad: Código Observable**
- ✅ Agrega structured logging: `logger.info("action", key=value)`
- ✅ Incluye correlation_id en todos los calls externos
- ✅ Define métricas Prometheus para operaciones críticas
- ✅ Documenta comportamiento en docstrings

### 3. **Prioridad: Resilencia de Integración**
- ✅ Implementa circuit breaker para llamadas a PMS
- ✅ Agrega caching con TTL apropiado
- ✅ Maneja excepciones específicas (no bare `except`)
- ✅ Fallback response cuando servicio externo falla

### 4. **Prioridad: Testing Comprehensivo**
- ✅ Unit tests para lógica pura
- ✅ Integration tests para flujos multi-servicio
- ✅ Mock externos (PMS, WhatsApp, Gmail)
- ✅ Pruebas de error cases y edge cases

---

## 📝 Pre-Commit Checklist

**Antes de hacer cualquier commit:**

```bash
# 1. Format & Lint
make fmt    # Ruff format + Prettier
make lint   # Ruff check --fix + gitleaks

# 2. Tests
make test   # pytest con coverage
# Resultado esperado: Tests passing, 70%+ coverage

# 3. Security
make security-fast  # Trivy scan + gitleaks

# 4. Pre-deploy
make pre-deploy-check  # Combined checks

# 5. Verify
make health  # Salud de servicios Docker
```

**Si algo falla:**
- ❌ NO hagas push sin resolver
- ✅ Corre comando de debug
- ✅ Arregla el issue
- ✅ Re-ejecuta `make` command

---

## 🏗️ Arquitectura de Cambios

### Cambios en `app/services/`
**Patrón**: Servicio con métodos async, métricas, logging, error handling

```python
# app/services/my_service.py
from prometheus_client import Counter, Histogram
from app.core.logging import logger
from app.exceptions.my_exceptions import MyServiceError

operation_counter = Counter(
    "my_service_operations_total",
    "Total operations",
    ["operation", "status"]
)

operation_latency = Histogram(
    "my_service_latency_seconds",
    "Operation latency",
    ["operation"]
)

class MyService:
    async def my_operation(self, param: str) -> dict:
        """
        Perform my operation.
        
        Args:
            param: Operation parameter
            
        Returns:
            Result dict with status and data
            
        Raises:
            MyServiceError: If operation fails
        """
        logger.info("operation_started", operation="my_op", param=param)
        
        try:
            with operation_latency.labels(operation="my_op").time():
                result = await self._do_work(param)
                
            operation_counter.labels(operation="my_op", status="success").inc()
            logger.info("operation_completed", operation="my_op", result=result)
            
            return result
            
        except Exception as e:
            operation_counter.labels(operation="my_op", status="error").inc()
            logger.error("operation_failed", operation="my_op", error=str(e))
            raise MyServiceError(f"Failed to do work: {e}") from e
```

**Checklist**:
- ✅ Async methods
- ✅ Type hints (args + return)
- ✅ Docstring with Args/Returns/Raises
- ✅ Prometheus metrics (counter + histogram)
- ✅ Structured logging
- ✅ Specific exception handling
- ✅ No bare `except` clauses

### Cambios en `app/routers/`
**Patrón**: Endpoint con validación, rate limiting, error response

```python
# app/routers/my_router.py
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from app.core.logging import logger
from app.services.orchestrator import get_orchestrator

router = APIRouter(prefix="/api/my", tags=["my"])

class MyRequest(BaseModel):
    """Request model with validation"""
    param1: str
    param2: int = Field(..., gt=0)  # Validation

class MyResponse(BaseModel):
    """Response model"""
    status: str
    data: dict

@router.post("/endpoint", response_model=MyResponse)
@router.state.limiter.limit("120/minute")  # Rate limit
async def my_endpoint(
    request: MyRequest,
    x_request_id: str = Header(...),  # Correlation ID
) -> MyResponse:
    """
    My endpoint handler.
    
    Args:
        request: Validated request
        x_request_id: Correlation ID from header
        
    Returns:
        Response with status and data
        
    Raises:
        HTTPException: If processing fails
    """
    logger.info("endpoint_called", endpoint="my_endpoint", x_request_id=x_request_id)
    
    try:
        orchestrator = await get_orchestrator()
        result = await orchestrator.process(request.param1)
        
        return MyResponse(status="success", data=result)
        
    except Exception as e:
        logger.error("endpoint_error", endpoint="my_endpoint", error=str(e), x_request_id=x_request_id)
        raise HTTPException(status_code=500, detail="Processing failed") from e
```

**Checklist**:
- ✅ Request/Response Pydantic models
- ✅ Rate limit decorator
- ✅ Correlation ID handling
- ✅ Type hints
- ✅ Docstring with Args/Returns/Raises
- ✅ Error handling with logging
- ✅ HTTPException (no bare exceptions)

### Cambios en `app/models/`
**Patrón**: Pydantic schema con validación, ORM model con async

```python
# app/models/my_model.py
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Pydantic schema for API
class MySchema(BaseModel):
    """API request/response schema"""
    name: str = Field(..., min_length=1, max_length=100)
    count: int = Field(..., ge=0)
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError("Name must be alphanumeric")
        return v.lower()

# SQLAlchemy ORM model
class MyRecord(Base):
    """Database record"""
    __tablename__ = "my_records"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    count = Column(Integer, default=0)
```

**Checklist**:
- ✅ Pydantic v2 with `field_validator`
- ✅ Field validation (min/max length, ranges, etc.)
- ✅ Docstrings
- ✅ SQLAlchemy with proper column types
- ✅ Database constraints (unique, nullable, etc.)

### Cambios en `tests/`
**Patrón**: Async tests with fixtures, mocks, assertions

```python
# tests/integration/test_my_feature.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient
from app.main import app
from app.services.orchestrator import get_orchestrator

@pytest.fixture
async def test_client():
    """Test client with rate limiting disabled"""
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    
    app.state.limiter = Limiter(
        key_func=get_remote_address,
        storage_uri="memory://"
    )
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_my_feature(test_client):
    """Test my feature end-to-end"""
    # Arrange
    request_data = {"param1": "value1", "param2": 5}
    
    # Act
    response = await test_client.post("/api/my/endpoint", json=request_data)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data

@pytest.mark.asyncio
async def test_my_feature_error_handling(test_client):
    """Test error handling"""
    # Mock orchestrator to raise error
    orchestrator_mock = AsyncMock()
    orchestrator_mock.process.side_effect = Exception("Service error")
    
    # ... test error response
    response = await test_client.post("/api/my/endpoint", json={})
    assert response.status_code == 500
```

**Checklist**:
- ✅ `@pytest.mark.asyncio` decorator
- ✅ Fixtures for setup/teardown
- ✅ Rate limiting disabled in tests
- ✅ Mocks for external services
- ✅ Both happy path + error cases
- ✅ Assertions with meaningful messages
- ✅ Clear Arrange-Act-Assert pattern

---

## 📊 Metrics Contribution Guidelines

### Agregar Nueva Métrica
1. **Define en service**:
   ```python
   from prometheus_client import Counter, Histogram, Gauge
   
   my_counter = Counter(
       "my_metric_total",
       "Description",
       ["label1", "label2"]
   )
   ```

2. **Use consistentemente**:
   ```python
   my_counter.labels(label1="value1", label2="value2").inc()
   ```

3. **Documenta en README-Infra.md**:
   ```markdown
   ### my_metric_total
   - Type: Counter
   - Labels: label1, label2
   - Query example: `sum(my_metric_total) by (label1)`
   ```

4. **Añade alerta si crítica**:
   - Edita `docker/alertmanager/config.yml`
   - Define condición de alerta en Prometheus

### Cardinality Limits
- ⚠️ Máximo 1000 combinaciones de labels
- ⚠️ No uses user IDs directamente como label
- ✅ Usa categorías: `["status", "endpoint"]`
- ✅ Agrega `limit` en labels si es necesario

---

## 🔍 Code Review Checklist

**Cuando hagas PR, verifica:**

- ✅ Código formateado (`make fmt`)
- ✅ Linting pasado (`make lint`)
- ✅ Tests pasados (`make test`)
- ✅ Coverage mejorado o igual
- ✅ No secrets committeados (`make lint` + gitleaks)
- ✅ Docstrings en nuevas funciones
- ✅ Structured logging añadido
- ✅ Métricas Prometheus si operación importante
- ✅ Error handling específico (no bare except)
- ✅ Changelog actualizado si user-facing
- ✅ Descripción de PR clara y concisa

---

## 🚨 Common Mistakes to Avoid

### ❌ Mistake 1: Async/Await Confusion
```python
# WRONG
result = pms_adapter.check_availability()  # ← Missing await

# RIGHT
result = await pms_adapter.check_availability()
```

### ❌ Mistake 2: Import Cycles
```python
# WRONG - In message_gateway.py
from app.services.feature_flag_service import get_feature_flag_service

# RIGHT - Use DEFAULT_FLAGS
from app.services.feature_flag_service import DEFAULT_FLAGS
```

### ❌ Mistake 3: Hardcoded Values
```python
# WRONG
TIMEOUT = 30

# RIGHT
TIMEOUT = settings.pms_timeout_seconds
```

### ❌ Mistake 4: Missing Correlation IDs
```python
# WRONG
response = await http_client.get("/api/endpoint")

# RIGHT
response = await http_client.get(
    "/api/endpoint",
    headers={"X-Request-ID": correlation_id}
)
```

### ❌ Mistake 5: Insufficient Logging
```python
# WRONG
result = await do_something()

# RIGHT
logger.info("operation_started", operation="do_something")
try:
    result = await do_something()
    logger.info("operation_success", operation="do_something", result=result)
except Exception as e:
    logger.error("operation_failed", operation="do_something", error=str(e))
    raise
```

### ❌ Mistake 6: No Error Handling
```python
# WRONG
response = await pms_client.get_availability()  # Might fail!

# RIGHT
try:
    response = await pms_client.get_availability()
except PMSError as e:
    logger.error("pms_error", error=str(e))
    return fallback_response()
```

### ❌ Mistake 7: Bare Except Clauses
```python
# WRONG
try:
    result = await operation()
except:  # ← Catches everything, including KeyboardInterrupt!
    pass

# RIGHT
try:
    result = await operation()
except (ValueError, TypeError) as e:
    logger.error("error", error=str(e))
    raise SpecificError(f"Operation failed: {e}") from e
```

---

## 🎓 Learning Resources

### Para Entender la Arquitectura
- `.github/copilot-instructions.md` - Comprehensive technical guide
- `.github/AI-AGENT-QUICKSTART.md` - Task-focused starter guide
- `app/main.py` - Entry point y lifespan manager
- `README-Infra.md` - Infrastructure y monitoring

### Para Entender Code Patterns
- `app/services/orchestrator.py` - Intent handler pattern
- `app/services/pms_adapter.py` - Circuit breaker + cache pattern
- `tests/unit/` - Unit testing patterns
- `tests/integration/` - Integration testing patterns

### Para Debugging
- `docker/alertmanager/config.yml` - Alert rules
- `docs/runbooks/` - Operations manuals
- `Makefile` - Available commands

---

## 🚀 Escalation Paths

### Cuando Necesites Ayuda
1. **Documentación**: Revisa `.github/copilot-instructions.md` primero
2. **Ejemplos**: Busca en `app/services/` archivo similar
3. **Tests**: Mira `tests/` para ver patterns
4. **Code Search**: Usa `grep_search` con palabras clave
5. **Semantic Search**: Usa `semantic_search` para conceptos

### Cuando Encuentres un Bug
1. Añade test que reproduzca el bug
2. Arregla el código
3. Verifica test pasa
4. Corre `make test` completo
5. Commit con mensaje descriptivo

### Cuando Hagas Feature Grande
1. Crea branch feature: `git checkout -b feature/my-feature`
2. Implementa incrementalmente
3. Commit frecuente con mensajes claros
4. Verifica tests después de cada cambio
5. PR cuando todo pase

---

## 📋 Commit Message Format

**Formato**:
```
[TYPE]: Brief description (< 50 chars)

Extended description if needed (< 72 chars per line)

- Bullet point 1
- Bullet point 2

Fixes: #123 (if applicable)
```

**Types**:
- `FEAT`: Nueva funcionalidad
- `FIX`: Bug fix
- `REFACTOR`: Cambio de código sin cambiar comportamiento
- `TEST`: Añadir/mejorar tests
- `DOCS`: Documentación
- `PERF`: Mejoras de performance
- `SECURITY`: Cambios de seguridad
- `CHORE`: Maintenance

**Ejemplos**:
```
FEAT: Add sentiment analysis to guest feedback

- Integrates Hugging Face transformers for NLP
- Stores sentiment scores in session context
- Metrics: sentiment_score_histogram

Fixes: #456
```

```
FIX: Circuit breaker not resetting after recovery

- Fixed HALF_OPEN → CLOSED transition logic
- Added test case for full CB cycle
- Verified with chaos test

Fixes: #789
```

---

## ✅ Final Checklist para Cualquier PR

- [ ] `make fmt` ejecutado sin errores
- [ ] `make lint` ejecutado sin errores
- [ ] `make test` ejecutado con coverage >= 70%
- [ ] `make security-fast` sin CRITICAL issues
- [ ] Docstrings en nuevas funciones/clases
- [ ] Structured logging agregado
- [ ] Métricas Prometheus si operación importante
- [ ] Tests escritos (unit + integration)
- [ ] Error handling específico
- [ ] Correlation ID incluido en API calls
- [ ] No secrets hardcodeados
- [ ] README actualizado si user-facing
- [ ] Commit messages claros y descriptivos
- [ ] Branch limpio antes de PR (rebase si necesario)

---

**Last Updated**: 2025-10-17  
**Maintained By**: Backend AI Team  
**Status**: ✅ Ready for AI agent contributions  
**Next Review**: After first AI-contributed feature
