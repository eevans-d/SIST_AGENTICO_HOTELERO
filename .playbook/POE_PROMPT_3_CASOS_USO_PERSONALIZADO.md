# 🎯 PROMPT 3 DEFINITIVO: Batería de Casos de Uso Enterprise
## PERSONALIZADO PARA: SIST_AGENTICO_HOTELERO

**OBJETIVO**: Crear un conjunto EXHAUSTIVO de casos de uso realistas para validar, entrenar y documentar el comportamiento del bot o3-pro especializado en **SIST_AGENTICO_HOTELERO**.

**PROYECTO**: Sistema multi-servicio de recepcionista hotelero AI  
**Stack**: Python 3.12.3, FastAPI, Docker Compose (7 servicios)  
**Status**: Staging-ready (8.9/10 deployment readiness, 31% coverage)  
**Commit**: 97676bcc27f7f999f602432a07383ce09c5dee68  

═══════════════════════════════════════════════════════════════════════════════
## ESTRUCTURA DE CADA CASO DE USO
═══════════════════════════════════════════════════════════════════════════════

Cada caso debe incluir:

📋 **METADATA**:
├─ ID: UC-XXX (para referencia)
├─ Categoría: [BUG|FEATURE|OPTIMIZATION|ARCHITECTURE|SECURITY|OBSERVABILITY]
├─ Complejidad: [SIMPLE|MEDIUM|COMPLEX|EXPERT]
├─ Módulos involucrados: [lista de archivos/servicios]
└─ Tiempo estimado de resolución: [5min|15min|1h|4h]

💬 **CONVERSACIÓN**:
├─ 1. Mensaje inicial del usuario (natural, contexto realista)
├─ 2. Respuesta esperada del bot (estructurada según formato del prompt 2)
├─ 3. Follow-up 1 (profundización técnica)
├─ 4. Respuesta a follow-up 1
├─ 5. Follow-up 2 (aspecto alternativo/edge case)
└─ 6. Respuesta final con síntesis

✅ **CRITERIOS DE ÉXITO**:
└─ Métricas objetivas para validar si el bot respondió correctamente

═══════════════════════════════════════════════════════════════════════════════
## CATEGORÍA 1: DEBUGGING DE BUGS CRÍTICOS (5 CASOS)
═══════════════════════════════════════════════════════════════════════════════

### UC-001: Race Condition en Session Manager 🔴

**METADATA**:
- ID: UC-001
- Categoría: BUG (Concurrency)
- Complejidad: EXPERT
- Módulos: `app/services/session_manager.py`, `app/core/middleware.py`
- Tiempo estimado: 4h (debugging + testing concurrente)

**CONVERSACIÓN**:

**[USER - Mensaje inicial]**
```
Estamos viendo un bug muy extraño en producción desde que escalamos a 1000 req/s. 
A veces (5% de casos aprox) los usuarios pierden el contexto de su conversación 
a mitad del flujo de reserva. Los logs muestran esto:

[ERROR] session_manager.update_failed key=tenant_abc:user_xyz:whatsapp conflict_version

Parece que hay algún tipo de race condition cuando 2 requests del mismo usuario 
llegan casi simultáneos (ej: usuario envía mensaje rápido + imagen). 

¿Puedes investigar qué está pasando en session_manager.py?
```

**[BOT - Respuesta esperada]**
```markdown
# 🐛 ANÁLISIS DE BUG: Race Condition en Session Updates

## 🔍 Investigación Inicial

📍 **Localización**:
- Archivo: `app/services/session_manager.py`
- Método: `update_session()` (líneas 200-250 aprox)
- Infraestructura: Redis sin optimistic locking

🧠 **RAZONAMIENTO PASO A PASO**:

**Paso 1: Reproducción del escenario**
Usuario envía mensaje de texto + imagen casi simultáneamente:
- Request A (texto): Lee session @ t=0, modifica, escribe @ t=50ms
- Request B (imagen): Lee session @ t=10ms, modifica, escribe @ t=60ms
- Resultado: Request B sobrescribe los cambios de Request A ❌

**Paso 2: Revisión del código actual**
```python
# session_manager.py línea ~200 (CÓDIGO ACTUAL PROBLEMÁTICO)
async def update_session(self, user_id: str, data: dict, tenant_id: str = None):
    session_key = self._build_key(user_id, tenant_id)
    
    # ⚠️ PROBLEMA: Read-Modify-Write sin atomic operation
    current_raw = await self.redis.get(session_key)
    current = json.loads(current_raw) if current_raw else {}
    
    # Merge de cambios
    current.update(data)
    
    await self.redis.setex(session_key, self.ttl, json.dumps(current))
    #    ^^^^^^^^ No hay verificación de que 'current' no cambió desde el GET
```

**Paso 3: Identificación del anti-pattern**
Este es el clásico problema de "Lost Update" en bases de datos:
- Thread-unsafe read-modify-write cycle
- No hay versioning ni compare-and-swap (CAS)
- Redis se usa como KV simple sin aprovechar atomic operations

**ROOT CAUSE**:  
Session updates no son atómicas. Múltiples requests concurrentes del mismo usuario 
causan overwrites en lugar de merges incrementales.

## ✅ SOLUCIÓN: Queue-based Updates + Micro-batching

```python
# ✅ CÓDIGO REFACTORIZADO - session_manager.py

import asyncio
from typing import Dict
from collections import defaultdict

class SessionManager:
    def __init__(self, redis_client, ttl=1800):
        self.redis = redis_client
        self.ttl = ttl
        # Queue per session para serializar updates
        self._update_queues: Dict[str, asyncio.Queue] = {}
        self._update_workers: Dict[str, asyncio.Task] = {}
        self._workers_lock = asyncio.Lock()
    
    async def update_session(
        self, 
        user_id: str, 
        data: dict, 
        tenant_id: str = None
    ) -> bool:
        """
        Update session con garantía de serialización por usuario.
        Usa queue-based architecture para evitar race conditions.
        
        Returns:
            bool: True if update succeeded
        """
        session_key = self._build_key(user_id, tenant_id)
        
        # Crear queue y worker si no existe para este usuario
        async with self._workers_lock:
            if session_key not in self._update_queues:
                self._update_queues[session_key] = asyncio.Queue()
                self._update_workers[session_key] = asyncio.create_task(
                    self._session_update_worker(session_key)
                )
        
        # Encolar update (non-blocking para el caller)
        update_future = asyncio.Future()
        await self._update_queues[session_key].put((data, update_future))
        
        # Esperar resultado del worker
        return await update_future
    
    async def _session_update_worker(self, session_key: str):
        """
        Worker dedicado por session_key que procesa updates serialmente.
        Implementa micro-batching: si llegan N updates en <50ms, los fusiona.
        """
        queue = self._update_queues[session_key]
        
        while True:
            try:
                # Esperar primer update
                first_data, first_future = await queue.get()
                
                # Micro-batch: esperar 50ms por updates adicionales
                batch_data = [first_data]
                batch_futures = [first_future]
                
                try:
                    while len(batch_data) < 10:  # Max 10 updates por batch
                        data, future = await asyncio.wait_for(
                            queue.get(), 
                            timeout=0.05  # 50ms window
                        )
                        batch_data.append(data)
                        batch_futures.append(future)
                except asyncio.TimeoutError:
                    pass  # No más updates, procesar batch
                
                # Fusionar todos los updates del batch
                merged_update = {}
                for data in batch_data:
                    merged_update = self._deep_merge(merged_update, data)
                
                # Aplicar update atómico (ahora serial, no hay race)
                try:
                    current_raw = await self.redis.get(session_key)
                    current = json.loads(current_raw) if current_raw else {}
                    final = self._deep_merge(current, merged_update)
                    
                    await self.redis.setex(
                        session_key, 
                        self.ttl, 
                        json.dumps(final)
                    )
                    
                    # Resolver todos los futures del batch
                    for fut in batch_futures:
                        fut.set_result(True)
                    
                    logger.info(
                        "session_manager.batch_update_success",
                        session_key=session_key,
                        batch_size=len(batch_data)
                    )
                    
                except Exception as e:
                    # Marcar todos los updates como fallidos
                    for fut in batch_futures:
                        fut.set_exception(e)
                    
                    logger.error(
                        "session_manager.batch_update_failed",
                        error=str(e),
                        session_key=session_key
                    )
                
            except asyncio.CancelledError:
                # Worker shutdown graceful
                break
    
    def _deep_merge(self, base: dict, updates: dict) -> dict:
        """Merge nested dictionaries recursively"""
        result = base.copy()
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    async def cleanup_idle_workers(self):
        """
        Cleanup workers de sesiones inactivas (llamar periódicamente).
        """
        # TODO: Implementar TTL de workers (cerrar después de 5min sin updates)
        pass
```

## 🧪 TESTING EXHAUSTIVO

```python
# tests/integration/test_session_concurrency.py

import pytest
import asyncio
from app.services.session_manager import SessionManager

@pytest.mark.asyncio
async def test_concurrent_updates_dont_lose_data(redis_client):
    """
    Simular 10 updates concurrentes del mismo usuario.
    Verificar que TODOS los cambios se apliquen (no se pierda ninguno).
    """
    session_mgr = SessionManager(redis_client)
    user_id = "concurrent_test_user"
    tenant_id = "tenant_abc"
    
    # Función que actualiza un campo específico
    async def update_field(field_name: str, value: any):
        return await session_mgr.update_session(
            user_id, 
            {field_name: value},
            tenant_id
        )
    
    # Lanzar 10 updates concurrentes con campos diferentes
    tasks = [
        update_field(f"field_{i}", f"value_{i}")
        for i in range(10)
    ]
    results = await asyncio.gather(*tasks)
    
    # ASSERT: Todos los updates deben haber tenido éxito
    assert all(results), "Some updates failed"
    
    # ASSERT: Verificar que todos los campos están presentes
    final_session = await session_mgr.get_session(user_id, tenant_id)
    for i in range(10):
        assert f"field_{i}" in final_session
        assert final_session[f"field_{i}"] == f"value_{i}"

@pytest.mark.asyncio
async def test_micro_batching_reduces_redis_writes(redis_client, mocker):
    """
    Verificar que micro-batching fusiona múltiples updates en 1 write.
    """
    session_mgr = SessionManager(redis_client)
    mock_setex = mocker.patch.object(redis_client, "setex")
    
    user_id = "batch_test_user"
    
    # Enviar 5 updates casi simultáneos
    tasks = [
        session_mgr.update_session(user_id, {f"field_{i}": i})
        for i in range(5)
    ]
    await asyncio.gather(*tasks)
    
    # ASSERT: Solo 1 write a Redis (todos batcheados)
    # (puede ser 2 si el timing no es perfecto, pero nunca 5)
    assert mock_setex.call_count <= 2, f"Expected ≤2 writes, got {mock_setex.call_count}"
```

## 📊 IMPACTO ANALYSIS

**Severidad**: 🔴 CRÍTICA
- Pérdida de contexto en conversaciones activas
- Afecta ~5% de usuarios en alta concurrencia (>500 req/s)
- Impacto en UX: Usuario debe re-autenticar o perder progreso de reserva

**Performance Impact**:
- Best case (sin contención): +0ms (async queueing)
- Micro-batching: -40ms promedio (5x menos writes a Redis)
- Memory overhead: 1 queue + 1 task por sesión activa (~2KB/session)

**Deployment Strategy**:
```yaml
Phase 1 (Day 1-2): 
  - Deploy con feature flag "session.queue_updates.enabled" = false
  
Phase 2 (Day 3-4):
  - Activar flag al 10% de usuarios (canary)
  - Monitorear: session_update_latency, batch_size_distribution
  
Phase 3 (Day 5-7):
  - 50% rollout si métricas estables
  
Phase 4 (Week 2):
  - 100% rollout + remover flag
```

## 📈 MÉTRICAS REQUERIDAS

```python
# Nuevas métricas Prometheus
session_batch_size = Histogram(
    "session_manager_batch_size",
    "Number of updates per batch",
    buckets=[1, 2, 5, 10, 20]
)

session_update_latency = Histogram(
    "session_manager_update_latency_seconds",
    "Time to process session update",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1]
)

session_workers_active = Gauge(
    "session_manager_workers_active",
    "Number of active session update workers"
)
```

✅ ¿Esta solución resuelve tu caso? ¿Necesitas profundizar en algún aspecto específico?
```

**CRITERIOS DE ÉXITO para UC-001**:
- [ ] Bot identifica el problema en session_manager.py con líneas exactas
- [ ] Menciona "race condition" y "lost update problem" explícitamente
- [ ] Propone solución con código completo (Queue pattern + micro-batching)
- [ ] Incluye ≥2 test cases (concurrencia, batching)
- [ ] Considera performance impact (memory, latency)
- [ ] Proporciona métricas Prometheus
- [ ] Timeline realista de deployment con feature flags

═══════════════════════════════════════════════════════════════════════════════

### UC-002: Circuit Breaker Flapping en PMS Adapter 🟠

**METADATA**:
- ID: UC-002
- Categoría: BUG (Resilience Pattern)
- Complejidad: COMPLEX
- Módulos: `app/services/pms_adapter.py`, `app/core/circuit_breaker.py`
- Tiempo estimado: 2h

**CONVERSACIÓN**:

**[USER]**
```
El circuit breaker del PMS está "flappeando" - abre y cierra cada 30 segundos.
Los usuarios ven errores intermitentes tipo "PMS temporarily unavailable".

Logs:
[WARN] pms_circuit_breaker.state_change state=OPEN failures=5 window=30s
[INFO] pms_circuit_breaker.state_change state=HALF_OPEN attempt=1
[INFO] pms_circuit_breaker.state_change state=CLOSED success=true
... (30s después)
[WARN] pms_circuit_breaker.state_change state=OPEN failures=5 window=30s

El PMS tiene latency spikes normales de 2-3s, pero no está "caído".
¿El threshold es muy sensible?
```

**[BOT - Respuesta esperada]**
```markdown
# 🐛 ANÁLISIS: Circuit Breaker Flapping

## 📍 Localización
- Archivo: `app/services/pms_adapter.py`
- Circuit Breaker: líneas ~50-120 (init + wrapper)
- Config: `app/core/circuit_breaker.py`

## 🧠 RAZONAMIENTO

**Paso 1: Revisar configuración actual**
```python
# pms_adapter.py (línea ~60)
self.circuit_breaker = CircuitBreaker(
    failure_threshold=5,        # 5 failures → OPEN
    recovery_timeout=30,        # 30s para intentar HALF_OPEN
    expected_exception=httpx.HTTPError
)
```

**Paso 2: Análisis del problema**
- Threshold=5 es muy bajo para API externa con variabilidad normal
- No distingue entre "timeout por latency" vs "error real 500"
- No considera percentiles (P95, P99) sino raw failures

**Paso 3: Comportamiento observado**
```
t=0s:    5 requests con timeout 2-3s → marcados como "failures"
t=30s:   CB → OPEN
t=60s:   CB → HALF_OPEN, 1 request succeed → CLOSED
t=90s:   Otro spike → 5 failures → OPEN nuevamente
```

**ROOT CAUSE**: Threshold fijo + no considera latency como métrica separada

## ✅ SOLUCIÓN: Adaptive Circuit Breaker

```python
# ✅ app/core/circuit_breaker.py - REFACTOR

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import deque
import statistics

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass
class CircuitBreakerMetrics:
    """Métricas en ventana deslizante"""
    window_size: int = 60  # segundos
    requests: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def record_request(self, success: bool, latency_ms: float):
        self.requests.append({
            "timestamp": datetime.now(),
            "success": success,
            "latency_ms": latency_ms
        })
    
    def get_error_rate_last_window(self) -> float:
        """Error rate en últimos 60s"""
        now = datetime.now()
        recent = [
            r for r in self.requests 
            if (now - r["timestamp"]).total_seconds() < self.window_size
        ]
        if not recent:
            return 0.0
        failures = sum(1 for r in recent if not r["success"])
        return failures / len(recent)
    
    def get_latency_p95(self) -> float:
        """P95 latency en últimos 60s"""
        now = datetime.now()
        recent_latencies = [
            r["latency_ms"] for r in self.requests
            if (now - r["timestamp"]).total_seconds() < self.window_size
        ]
        if not recent_latencies:
            return 0.0
        return statistics.quantiles(recent_latencies, n=20)[18]  # P95

class AdaptiveCircuitBreaker:
    """
    Circuit Breaker con thresholds adaptativos basados en métricas.
    
    Criterios para OPEN:
    - Error rate >20% en última ventana (vs threshold fijo de 5 failures)
    - P95 latency >5000ms (indica degradación seria)
    - Consecutive failures ≥10 (indica outage total)
    """
    
    def __init__(
        self,
        error_rate_threshold=0.20,      # 20% error rate → OPEN
        latency_p95_threshold_ms=5000,  # P95 >5s → OPEN
        consecutive_failure_threshold=10,
        recovery_timeout=60,            # Más tiempo para recovery
        half_open_max_requests=3        # Test con 3 requests antes de CLOSED
    ):
        self.error_rate_threshold = error_rate_threshold
        self.latency_p95_threshold_ms = latency_p95_threshold_ms
        self.consecutive_failure_threshold = consecutive_failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_requests = half_open_max_requests
        
        self.state = CircuitState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self.consecutive_failures = 0
        self.last_opened_at = None
        self.half_open_requests_count = 0
    
    async def call(self, func, *args, **kwargs):
        """Wrapper para ejecutar función con circuit breaker"""
        
        # 1. Check state
        if self.state == CircuitState.OPEN:
            # Verificar si es tiempo de intentar HALF_OPEN
            if (datetime.now() - self.last_opened_at).total_seconds() >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_requests_count = 0
                logger.info("circuit_breaker.state_transition", from_state="OPEN", to_state="HALF_OPEN")
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")
        
        # 2. Execute request
        start_time = datetime.now()
        try:
            result = await func(*args, **kwargs)
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Record success
            self.metrics.record_request(success=True, latency_ms=latency_ms)
            self.consecutive_failures = 0
            
            # Si estábamos en HALF_OPEN, verificar si cerrar
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_requests_count += 1
                if self.half_open_requests_count >= self.half_open_max_requests:
                    self.state = CircuitState.CLOSED
                    logger.info("circuit_breaker.state_transition", from_state="HALF_OPEN", to_state="CLOSED")
            
            return result
            
        except Exception as e:
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Record failure
            self.metrics.record_request(success=False, latency_ms=latency_ms)
            self.consecutive_failures += 1
            
            # Check if should OPEN
            should_open = (
                self.metrics.get_error_rate_last_window() > self.error_rate_threshold or
                self.metrics.get_latency_p95() > self.latency_p95_threshold_ms or
                self.consecutive_failures >= self.consecutive_failure_threshold
            )
            
            if should_open and self.state != CircuitState.OPEN:
                self.state = CircuitState.OPEN
                self.last_opened_at = datetime.now()
                logger.warning(
                    "circuit_breaker.opened",
                    error_rate=self.metrics.get_error_rate_last_window(),
                    p95_latency=self.metrics.get_latency_p95(),
                    consecutive_failures=self.consecutive_failures
                )
            
            # Si estábamos en HALF_OPEN y falla, volver a OPEN
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.last_opened_at = datetime.now()
                logger.warning("circuit_breaker.half_open_failed", to_state="OPEN")
            
            raise
```

## 🧪 TESTING

```python
@pytest.mark.asyncio
async def test_adaptive_cb_tolerates_latency_spikes(mocker):
    """
    Verificar que latency spikes ocasionales NO abren el CB.
    """
    cb = AdaptiveCircuitBreaker()
    
    # Simular 95 requests exitosos con latency normal (200ms)
    async def fast_request():
        await asyncio.sleep(0.2)
        return "ok"
    
    for _ in range(95):
        await cb.call(fast_request)
    
    # Simular 5 requests con latency spike (3000ms) pero exitosos
    async def slow_but_successful():
        await asyncio.sleep(3.0)
        return "ok"
    
    for _ in range(5):
        await cb.call(slow_but_successful)
    
    # ASSERT: CB debe estar CLOSED (toleró el spike)
    assert cb.state == CircuitState.CLOSED
    
    # Error rate debe ser 0% (todos exitosos)
    assert cb.metrics.get_error_rate_last_window() == 0.0

@pytest.mark.asyncio
async def test_adaptive_cb_opens_on_sustained_degradation():
    """
    Verificar que CB abre cuando error rate >20% sostenido.
    """
    cb = AdaptiveCircuitBreaker(error_rate_threshold=0.20)
    
    # Simular 80 requests exitosos + 20 fallidos (25% error rate)
    async def failing_request():
        if random.random() < 0.25:  # 25% failure
            raise Exception("Simulated failure")
        return "ok"
    
    for _ in range(100):
        try:
            await cb.call(failing_request)
        except:
            pass
    
    # ASSERT: CB debe abrir (error rate >20%)
    assert cb.state == CircuitState.OPEN
```

## 📊 MÉTRICAS

```python
circuit_breaker_state = Gauge(
    "pms_circuit_breaker_state",
    "Circuit breaker state (0=CLOSED, 1=OPEN, 2=HALF_OPEN)"
)

circuit_breaker_error_rate = Gauge(
    "pms_circuit_breaker_error_rate",
    "Current error rate in sliding window"
)

circuit_breaker_latency_p95 = Gauge(
    "pms_circuit_breaker_latency_p95_ms",
    "P95 latency in sliding window"
)
```

✅ ¿Esta solución resuelve el flapping? ¿Necesitas ajustar algún threshold?
```

**CRITERIOS DE ÉXITO para UC-002**:
- [ ] Bot identifica configuración actual del circuit breaker
- [ ] Explica por qué threshold fijo causa flapping
- [ ] Propone adaptive thresholds con métricas (error rate, P95 latency)
- [ ] Código completo del adaptive circuit breaker
- [ ] Tests específicos (latency spikes, sustained degradation)
- [ ] Nuevas métricas para monitoreo

═══════════════════════════════════════════════════════════════════════════════

### UC-003: Memoria Redis Crece Sin Control 🔴

**METADATA**:
- ID: UC-003
- Categoría: BUG (Resource Leak)
- Complejidad: MEDIUM
- Módulos: `app/services/session_manager.py`, `app/services/feature_flag_service.py`
- Tiempo estimado: 1h

**[USER]**
```
Redis está creciendo de 2GB a 15GB en 1 semana. Tuvimos que reiniciar porque llegó a OOM.

redis-cli INFO memory:
used_memory_human:15.2G
maxmemory_human:16.0G

KEYS command muestra millones de keys con patrón "session:*" que parecen abandonadas.
¿No estamos limpiando sesiones viejas?
```

**[BOT - Respuesta]**
```markdown
# 🐛 ANÁLISIS: Memory Leak en Redis Sessions

## 📍 Localización
- `app/services/session_manager.py` - TTL configuration
- `app/core/constants.py` - SESSION_TTL_DEFAULT

## 🧠 ROOT CAUSE ANALYSIS

```python
# session_manager.py línea ~100
await self.redis.setex(session_key, self.ttl, json.dumps(session_data))
# TTL es correcto (1800s = 30min) ✅

# PERO...
# Si usuario abandona conversación antes de 30min, la key persiste igual
# Con 10k usuarios/día abandonando a mitad de flow → 10k sessions huérfanas
```

**Problema identificado**: Sessions no se limpian proactivamente cuando usuario no vuelve.

## ✅ SOLUCIÓN: Aggressive Cleanup + Monitoring

```python
# session_manager.py - AÑADIR

async def cleanup_abandoned_sessions(self):
    """
    Background task para limpiar sesiones abandonadas.
    Criteria: última actividad >1 hora
    """
    cursor = 0
    cleaned_count = 0
    
    while True:
        # Scan con cursor para no bloquear Redis
        cursor, keys = await self.redis.scan(
            cursor, 
            match="session:*", 
            count=100
        )
        
        for key in keys:
            try:
                ttl = await self.redis.ttl(key)
                
                # Si TTL >25 min (usuario no activo en 5+ min), forzar expiración
                if ttl > 1500:
                    session_data = json.loads(await self.redis.get(key))
                    last_activity = session_data.get("last_activity_timestamp")
                    
                    if last_activity:
                        inactive_seconds = (datetime.now() - datetime.fromisoformat(last_activity)).total_seconds()
                        
                        if inactive_seconds > 3600:  # 1 hora inactivo
                            await self.redis.delete(key)
                            cleaned_count += 1
                            logger.info("session_cleanup.deleted", key=key, inactive_seconds=inactive_seconds)
            
            except Exception as e:
                logger.error("session_cleanup.error", key=key, error=str(e))
        
        if cursor == 0:
            break  # Scan completo
    
    logger.info("session_cleanup.completed", cleaned=cleaned_count)
    return cleaned_count

# Iniciar cleanup task en startup
async def start_cleanup_task(self):
    async def periodic_cleanup():
        while True:
            await asyncio.sleep(3600)  # Cada hora
            await self.cleanup_abandoned_sessions()
    
    asyncio.create_task(periodic_cleanup())
```

## 🧪 TEST

```python
@pytest.mark.asyncio
async def test_abandoned_sessions_are_cleaned(redis_client):
    session_mgr = SessionManager(redis_client)
    
    # Crear session abandonada (last_activity hace 2 horas)
    old_timestamp = (datetime.now() - timedelta(hours=2)).isoformat()
    await redis_client.setex(
        "session:tenant_a:user_old:whatsapp",
        1800,
        json.dumps({"last_activity_timestamp": old_timestamp})
    )
    
    # Cleanup
    cleaned = await session_mgr.cleanup_abandoned_sessions()
    
    # ASSERT
    assert cleaned == 1
    assert not await redis_client.exists("session:tenant_a:user_old:whatsapp")
```

✅ ¿Implemento esto o prefieres una estrategia diferente?
```

═══════════════════════════════════════════════════════════════════════════════

### UC-004: NLP Confidence Baja después de 3 Meses 🟡

**METADATA**:
- ID: UC-004
- Categoría: BUG (Model Drift)
- Complejidad: COMPLEX
- Módulos: `app/services/nlp_engine.py`, `app/services/enhanced_nlp_engine.py`
- Tiempo estimado: 3h

**[USER]**
```
El NLP engine que tenía 95% accuracy en julio ahora está en 75%. 
Usuarios usan frases nuevas que no vio en training: "quiero una cama king", "habitación con vista al mar".

¿Cómo re-entrenar el modelo sin downtime?
```

**[BOT - Respuesta]**
```markdown
# 🐛 ANÁLISIS: Model Drift en NLP

## 📍 Localización
- `app/services/nlp_engine.py` - Model loading
- Training data: posiblemente en `rasa_nlu/` (si usa Rasa)

## 🧠 ROOT CAUSE
Training data estático → usuarios evolucionan vocabulario → model drift

## ✅ SOLUCIÓN: Continuous Learning Pipeline

```python
# scripts/retrain_nlp_model.py

async def retrain_with_production_data():
    """
    1. Export low-confidence predictions de últimos 30 días
    2. Human labeling (usar Labelbox o similar)
    3. Retrain model
    4. A/B test nuevo model vs viejo
    5. Rollout gradual con feature flag
    """
    pass
```

[Implementación completa con pipeline de retraining]
```

═══════════════════════════════════════════════════════════════════════════════

### UC-005: Audio Transcription Timeout para >2min Files 🟠

**METADATA**:
- ID: UC-005
- Categoría: BUG (External API)
- Complejidad: MEDIUM
- Módulos: `app/services/audio_processor.py`, `app/services/dlq_service.py`
- Tiempo estimado: 1h

**[USER]**
```
Usuarios reportan que mensajes de voz >2 minutos no se transcriben.
Logs: "OpenAI Whisper API timeout after 120s"

¿Timeout hardcoded?
```

**[BOT - Respuesta]**
```markdown
# 🐛 ANÁLISIS: Audio Timeout

## 📍 Localización
`app/services/audio_processor.py` línea ~165

```python
async with httpx.AsyncClient(timeout=120.0) as client:  # ⚠️ Fixed timeout
```

## ✅ SOLUCIÓN: Adaptive Timeout + DLQ Retry

```python
# Calcular timeout basado en duración estimada
duration_sec = await self._estimate_audio_duration(media_url)
timeout = min(30 + (duration_sec / 60 * 45), 300)  # Max 5 min

# Si timeout igual, encolar a DLQ para retry async
```

[Implementación completa con DLQ service]
```

═══════════════════════════════════════════════════════════════════════════════
## CATEGORÍA 2: NUEVAS FEATURES (3 CASOS)
═══════════════════════════════════════════════════════════════════════════════

### UC-006: Implementar Intent "modify_reservation" 🎨

**METADATA**:
- ID: UC-006
- Categoría: FEATURE
- Complejidad: COMPLEX
- Módulos: `orchestrator.py`, `pms_adapter.py`, `nlp_engine.py`
- Tiempo estimado: 6h

**[USER]**
```
Necesitamos implementar la funcionalidad de modificar reservas existentes.
Usuario debería poder decir "quiero cambiar mi reserva del 20 al 25 de diciembre".

¿Cómo estructuro esto siguiendo los patterns existentes?
```

**[BOT - Respuesta]**
```markdown
# 🎨 DISEÑO: Intent "modify_reservation"

## 🏗️ ARQUITECTURA

```python
# orchestrator.py - AÑADIR al _intent_handlers dict

self._intent_handlers["modify_reservation"] = self._handle_modify_reservation

async def _handle_modify_reservation(self, nlp_result: dict, session_data: dict, message: UnifiedMessage) -> dict:
    """
    Flow:
    1. Extract booking_id de entities o session
    2. Validate con PMS que booking existe
    3. Extract new dates/room_type
    4. Check availability
    5. Calculate price diff (upgrade/downgrade)
    6. Request confirmation
    7. Update booking con PMS
    """
    
    # Paso 1: Extract booking_id
    booking_id = nlp_result["entities"].get("booking_id") or session_data.get("last_booking_id")
    
    if not booking_id:
        return {
            "response_type": "text",
            "content": "¿Cuál es el número de tu reserva? Lo encuentras en el email de confirmación."
        }
    
    # Paso 2: Validate booking exists
    try:
        booking = await self.pms_adapter.get_booking(booking_id)
    except PMSError:
        return {
            "response_type": "text",
            "content": f"No encuentro la reserva {booking_id}. ¿Estás seguro del número?"
        }
    
    # Paso 3: Extract new parameters
    new_checkin = nlp_result["entities"].get("checkin_date")
    new_checkout = nlp_result["entities"].get("checkout_date")
    new_room_type = nlp_result["entities"].get("room_type")
    
    # Paso 4: Check availability
    availability = await self.pms_adapter.check_availability(
        new_checkin or booking["checkin_date"],
        new_checkout or booking["checkout_date"]
    )
    
    if not availability["available"]:
        return {
            "response_type": "text",
            "content": "Lo siento, no hay disponibilidad para esas fechas. ¿Quieres intentar otras?"
        }
    
    # Paso 5: Calculate price difference
    original_price = booking["total_price"]
    new_price = await self.pms_adapter.calculate_price(
        new_checkin or booking["checkin_date"],
        new_checkout or booking["checkout_date"],
        new_room_type or booking["room_type"]
    )
    price_diff = new_price - original_price
    
    # Paso 6: Request confirmation
    session_data["pending_modification"] = {
        "booking_id": booking_id,
        "new_params": {...},
        "price_diff": price_diff
    }
    
    return {
        "response_type": "text",
        "content": f"Perfecto, puedo cambiar tu reserva. {'Deberás pagar ${price_diff} adicional' if price_diff > 0 else f'Te reembolsaré ${-price_diff}'}. ¿Confirmas el cambio?",
        "actions": ["confirm", "cancel"]
    }
```

## 🧪 TESTS

```python
@pytest.mark.asyncio
async def test_modify_reservation_happy_path(orchestrator, mock_pms):
    # Arrange
    mock_pms.get_booking.return_value = {"id": "B123", "checkin_date": "2025-12-20", "total_price": 500}
    mock_pms.check_availability.return_value = {"available": True}
    mock_pms.calculate_price.return_value = 550
    
    nlp_result = {
        "intent": {"name": "modify_reservation"},
        "entities": {"booking_id": "B123", "checkin_date": "2025-12-25"}
    }
    
    # Act
    response = await orchestrator._handle_modify_reservation(nlp_result, {}, mock_message)
    
    # Assert
    assert "Deberás pagar $50 adicional" in response["content"]
    assert response["actions"] == ["confirm", "cancel"]
```

[Más tests: sin booking_id, sin disponibilidad, downgrade, etc.]
```

═══════════════════════════════════════════════════════════════════════════════

### UC-007: Soporte Multiidioma (Inglés/Portugués) 🌍

**METADATA**:
- ID: UC-007
- Categoría: FEATURE
- Complejidad: MEDIUM
- Módulos: `nlp_engine.py`, `template_service.py`, `app/utils/i18n_helpers.py`
- Tiempo estimado: 4h

[Diseño completo de i18n con detección de idioma + templates multiidioma]

═══════════════════════════════════════════════════════════════════════════════

### UC-008: Notificaciones Push para Confirmaciones 📲

**METADATA**:
- ID: UC-008
- Categoría: FEATURE
- Complejidad: MEDIUM
- Módulos: `app/services/whatsapp_client.py`, nuevo `notification_service.py`
- Tiempo estimado: 3h

[Implementación de webhook reverse + queue de notificaciones]

═══════════════════════════════════════════════════════════════════════════════
## CATEGORÍA 3: OPTIMIZATION (2 CASOS)
═══════════════════════════════════════════════════════════════════════════════

### UC-009: Reducir Latencia NLP de 800ms a <300ms ⚡

**METADATA**:
- ID: UC-009
- Categoría: OPTIMIZATION
- Complejidad: EXPERT
- Módulos: `nlp_engine.py`, caching layer
- Tiempo estimado: 3h

[Profiling + modelo cuantizado + caching de embeddings]

═══════════════════════════════════════════════════════════════════════════════

### UC-010: Refactorizar Orchestrator (Extraer Business Logic) 🔧

**METADATA**:
- ID: UC-010
- Categoría: OPTIMIZATION (Refactoring)
- Complejidad: COMPLEX
- Módulos: `orchestrator.py` (2,030 líneas), nuevos services
- Tiempo estimado: 8h

[Extracción a BusinessHoursService, EscalationService, IntentRouter]

═══════════════════════════════════════════════════════════════════════════════
## CATEGORÍA 4: ARQUITECTURA (2 CASOS)
═══════════════════════════════════════════════════════════════════════════════

### UC-011: Añadir Nuevo Canal (Telegram) sin Romper Abstracción 🏗️

**METADATA**:
- ID: UC-011
- Categoría: ARCHITECTURE
- Complejidad: COMPLEX
- Módulos: nuevo `telegram_client.py`, `message_gateway.py`
- Tiempo estimado: 6h

[Diseño de TelegramAdapter implementando MessageGateway interface]

═══════════════════════════════════════════════════════════════════════════════

### UC-012: Migrar de Redis a PostgreSQL para Sessions 🔄

**METADATA**:
- ID: UC-012
- Categoría: ARCHITECTURE
- Complejidad: EXPERT
- Módulos: `session_manager.py`, migrations
- Tiempo estimado: 12h

[Análisis pros/cons + migration path: dual-write → validate → switch → cleanup]

═══════════════════════════════════════════════════════════════════════════════

## ✅ ENTREGABLE FINAL

Total de **12 casos de uso** enterprise-grade con:
- Conversaciones completas (user → bot → follow-ups)
- Código production-ready
- Tests comprehensivos
- Métricas y observabilidad
- Deployment strategy
- Runbooks cuando aplique

**FORMATO**: Markdown estructurado de ~600-800 líneas por caso de uso  
**Total esperado**: ~8,000-10,000 líneas de documentación ejecutable

---

**Creado**: 2025-11-18  
**Personalizado para**: SIST_AGENTICO_HOTELERO  
**Commit hash**: 97676bcc27f7f999f602432a07383ce09c5dee68  
**Versión**: 1.0 (Personalizada)
