# 🎯 GUÍA DE MEJORAS DE ROBUSTEZ - Sistema Agente Hotelero IA

**Fecha:** 2025-01-09  
**Versión:** 1.0.0  
**Estado:** Recomendaciones Implementables

---

## 📋 ÍNDICE DE MEJORAS

1. [Mejoras de Testing](#1-mejoras-de-testing)
2. [Validaciones de Negocio](#2-validaciones-de-negocio)
3. [Seguridad Avanzada](#3-seguridad-avanzada)
4. [Performance Tuning](#4-performance-tuning)
5. [Observabilidad Mejorada](#5-observabilidad-mejorada)
6. [Resiliencia Adicional](#6-resiliencia-adicional)

---

## 1. MEJORAS DE TESTING

### 🎯 Objetivo: Alcanzar 85%+ de Cobertura

### 1.1 Tests de Integración Faltantes

#### Test: Multi-Tenant Scenarios
```python
# tests/integration/test_multi_tenant_scenarios.py
import pytest
from app.services.message_gateway import MessageGateway
from app.services.dynamic_tenant_service import get_dynamic_tenant_service

@pytest.mark.asyncio
async def test_tenant_isolation():
    """Verificar aislamiento entre tenants"""
    gateway = MessageGateway()
    tenant_service = await get_dynamic_tenant_service()
    
    # Crear mensajes de diferentes tenants
    message_tenant_a = {
        "from": "+1234567890",  # Pertenece a tenant A
        "text": "Disponibilidad"
    }
    
    message_tenant_b = {
        "from": "+0987654321",  # Pertenece a tenant B
        "text": "Disponibilidad"
    }
    
    # Procesar ambos mensajes
    result_a = await gateway.normalize("whatsapp", message_tenant_a)
    result_b = await gateway.normalize("whatsapp", message_tenant_b)
    
    # Verificar que cada uno resolvió a su tenant correcto
    assert result_a.tenant_id == "tenant-a"
    assert result_b.tenant_id == "tenant-b"
    
    # Verificar que no hay contaminación de datos
    # (las reservas de tenant A no son visibles para tenant B)

@pytest.mark.asyncio
async def test_tenant_fallback_to_default():
    """Verificar fallback cuando tenant no se encuentra"""
    gateway = MessageGateway()
    
    message_unknown = {
        "from": "+9999999999",  # No registrado
        "text": "Test"
    }
    
    result = await gateway.normalize("whatsapp", message_unknown)
    assert result.tenant_id == "default"
```

#### Test: Circuit Breaker Edge Cases
```python
# tests/unit/test_circuit_breaker_edge_cases.py
import pytest
from app.core.circuit_breaker import CircuitBreaker

@pytest.mark.asyncio
async def test_circuit_breaker_half_open_success():
    """Verificar recuperación desde half-open"""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
    
    async def failing_function():
        raise Exception("Error")
    
    async def successful_function():
        return "Success"
    
    # Forzar apertura del circuit breaker
    for _ in range(2):
        with pytest.raises(Exception):
            await cb.call(failing_function)
    
    assert cb.state == CircuitState.OPEN
    
    # Esperar recovery timeout
    await asyncio.sleep(1.1)
    
    # Probar con función exitosa - debería pasar a CLOSED
    result = await cb.call(successful_function)
    assert result == "Success"
    assert cb.state == CircuitState.CLOSED

@pytest.mark.asyncio
async def test_circuit_breaker_half_open_failure():
    """Verificar que falla nuevamente desde half-open"""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
    
    async def failing_function():
        raise Exception("Error")
    
    # Forzar apertura
    for _ in range(2):
        with pytest.raises(Exception):
            await cb.call(failing_function)
    
    # Esperar recovery
    await asyncio.sleep(1.1)
    
    # Fallar nuevamente - debe volver a OPEN
    with pytest.raises(Exception):
        await cb.call(failing_function)
    
    assert cb.state == CircuitState.OPEN
```

#### Test: Load Testing para Auto-Scaler
```python
# tests/load/test_auto_scaler_under_load.py
import pytest
import asyncio
from app.services.auto_scaler import get_auto_scaler

@pytest.mark.load
@pytest.mark.asyncio
async def test_autoscaler_handles_spike():
    """Verificar que autoscaler responde a picos de carga"""
    scaler = await get_auto_scaler()
    await scaler.start()
    
    # Simular métricas de alta carga
    metrics = {
        'cpu_usage': 85.0,
        'memory_usage': 80.0,
        'request_rate': 1200,  # > threshold
        'error_rate': 0.01
    }
    
    # Evaluar decisión de scaling
    decision = await scaler.evaluate_scaling(metrics)
    
    assert decision['action'] == 'scale_up'
    assert decision['target_instances'] > decision['current_instances']
    
    await scaler.stop()

@pytest.mark.load
@pytest.mark.asyncio
async def test_autoscaler_prevents_flapping():
    """Verificar que no hay flapping (scale up/down rápido)"""
    scaler = await get_auto_scaler()
    await scaler.start()
    
    # Alternar entre alta y baja carga rápidamente
    for i in range(5):
        metrics = {
            'cpu_usage': 85.0 if i % 2 == 0 else 20.0,
            'request_rate': 1200 if i % 2 == 0 else 50
        }
        
        decision = await scaler.evaluate_scaling(metrics)
        
        # Verificar que hay cooldown entre cambios
        if i > 0:
            assert scaler.last_scale_action_time is not None
            time_since_last = time.time() - scaler.last_scale_action_time
            assert time_since_last >= scaler.cooldown_period
    
    await scaler.stop()
```

### 1.2 Ejecutar Tests de Cobertura

```bash
# Ejecutar suite completa con cobertura
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api

# Tests unitarios
poetry run pytest tests/unit/ --cov=app --cov-report=html --cov-report=term

# Tests de integración
poetry run pytest tests/integration/ --cov=app --cov-append

# Tests E2E
poetry run pytest tests/e2e/ --cov=app --cov-append

# Generar reporte final
poetry run coverage report --show-missing
poetry run coverage html
```

---

## 2. VALIDACIONES DE NEGOCIO

### 2.1 Validaciones en Schemas

```python
# app/models/schemas.py
from pydantic import BaseModel, field_validator, model_validator
from datetime import date, datetime, timedelta
from typing import Optional

class ReservationRequest(BaseModel):
    """Request para crear reservación con validaciones robustas"""
    check_in: date
    check_out: date
    room_type: str
    guest_name: str
    guest_email: str
    guest_phone: str
    guests: int
    special_requests: Optional[str] = None
    
    @field_validator('check_in')
    @classmethod
    def validate_check_in_future(cls, v):
        """Check-in debe ser hoy o en el futuro"""
        if v < date.today():
            raise ValueError('Check-in no puede ser en el pasado')
        return v
    
    @field_validator('check_out')
    @classmethod
    def validate_checkout_after_checkin(cls, v, info):
        """Check-out debe ser después de check-in"""
        if 'check_in' in info.data and v <= info.data['check_in']:
            raise ValueError('Check-out debe ser posterior a check-in')
        return v
    
    @field_validator('guests')
    @classmethod
    def validate_guest_count(cls, v):
        """Número de huéspedes razonable"""
        if v < 1:
            raise ValueError('Debe haber al menos 1 huésped')
        if v > 10:
            raise ValueError('Máximo 10 huéspedes por reservación')
        return v
    
    @field_validator('guest_email')
    @classmethod
    def validate_email_format(cls, v):
        """Validar formato de email"""
        from app.core.input_validator import input_validator
        if not input_validator.validate_email(v):
            raise ValueError('Formato de email inválido')
        return v
    
    @field_validator('guest_phone')
    @classmethod
    def validate_phone_format(cls, v):
        """Validar formato de teléfono"""
        from app.core.input_validator import input_validator
        if not input_validator.validate_phone(v):
            raise ValueError('Formato de teléfono inválido')
        return v
    
    @field_validator('special_requests')
    @classmethod
    def sanitize_special_requests(cls, v):
        """Sanitizar texto libre"""
        if v:
            from app.core.input_validator import input_validator
            return input_validator.sanitize_string(v)
        return v
    
    @model_validator(mode='after')
    def validate_stay_duration(self):
        """Validar duración de estancia"""
        duration = (self.check_out - self.check_in).days
        
        if duration > 90:
            raise ValueError('Duración máxima de estancia: 90 días')
        
        if duration < 1:
            raise ValueError('Estancia mínima: 1 noche')
        
        # Validar anticipación de reserva
        days_advance = (self.check_in - date.today()).days
        if days_advance > 365:
            raise ValueError('Reservas máximo con 365 días de anticipación')
        
        return self

class AvailabilityRequest(BaseModel):
    """Request para consultar disponibilidad"""
    check_in: date
    check_out: date
    room_type: Optional[str] = None
    guests: int = 1
    
    @field_validator('check_in')
    @classmethod
    def validate_check_in(cls, v):
        if v < date.today():
            raise ValueError('Check-in no puede ser en el pasado')
        if v > date.today() + timedelta(days=730):  # 2 años
            raise ValueError('Consulta máxima: 2 años adelante')
        return v
    
    @model_validator(mode='after')
    def validate_dates(self):
        if self.check_out <= self.check_in:
            raise ValueError('Check-out debe ser después de check-in')
        
        duration = (self.check_out - self.check_in).days
        if duration > 90:
            raise ValueError('Consulta máxima: 90 días')
        
        return self
```

### 2.2 Validaciones en Orchestrator

```python
# app/services/orchestrator.py
from app.services.security.audit_logger import audit_logger, AuditEventType

async def process_reservation_request(
    self, 
    request: ReservationRequest,
    user_id: str,
    ip_address: str
) -> Dict:
    """Procesar solicitud de reserva con validaciones adicionales"""
    
    # 1. Auditar acceso
    await audit_logger.log_event(
        AuditEventType.DATA_ACCESS,
        user_id=user_id,
        ip_address=ip_address,
        resource="reservation_create",
        details={"room_type": request.room_type}
    )
    
    # 2. Validaciones de negocio adicionales
    
    # 2.1 Verificar blacklist de usuarios
    if await self._is_user_blacklisted(request.guest_email):
        await audit_logger.log_event(
            AuditEventType.ACCESS_DENIED,
            user_id=user_id,
            ip_address=ip_address,
            resource="reservation_create",
            details={"reason": "blacklisted_user"}
        )
        raise ValueError("Usuario no autorizado")
    
    # 2.2 Verificar límite de reservas activas por usuario
    active_reservations = await self._count_active_reservations(
        request.guest_email
    )
    if active_reservations >= 5:
        raise ValueError("Límite de reservas activas alcanzado (máx: 5)")
    
    # 2.3 Validar disponibilidad antes de procesar
    availability = await self.pms_adapter.check_availability(
        check_in=request.check_in,
        check_out=request.check_out,
        room_type=request.room_type
    )
    
    if not availability.get('available', False):
        return {
            'success': False,
            'message': 'Habitación no disponible para las fechas seleccionadas'
        }
    
    # 2.4 Verificar precio y aplicar reglas de negocio
    price = availability.get('price', 0)
    
    # Aplicar descuento por estadía larga
    duration = (request.check_out - request.check_in).days
    if duration >= 7:
        discount = 0.10  # 10% descuento
        price = price * (1 - discount)
    elif duration >= 30:
        discount = 0.20  # 20% descuento
        price = price * (1 - discount)
    
    # 3. Crear reserva
    try:
        result = await self.pms_adapter.create_reservation(
            check_in=request.check_in,
            check_out=request.check_out,
            room_type=request.room_type,
            guest_name=request.guest_name,
            guest_email=request.guest_email,
            guest_phone=request.guest_phone,
            guests=request.guests,
            total_price=price
        )
        
        # Auditar creación exitosa
        await audit_logger.log_event(
            AuditEventType.DATA_MODIFICATION,
            user_id=user_id,
            ip_address=ip_address,
            resource="reservation",
            details={
                "reservation_id": result.get('id'),
                "action": "create",
                "amount": price
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating reservation: {e}")
        raise

async def _is_user_blacklisted(self, email: str) -> bool:
    """Verificar si usuario está en blacklist"""
    # TODO: Implementar verificación contra base de datos
    # Por ahora, lista en memoria
    blacklist = []  # Cargar desde Redis o DB
    return email in blacklist

async def _count_active_reservations(self, email: str) -> int:
    """Contar reservas activas del usuario"""
    # TODO: Consultar base de datos
    # SELECT COUNT(*) FROM reservations 
    # WHERE guest_email = ? AND check_out >= NOW() AND status != 'cancelled'
    return 0  # Placeholder
```

---

## 3. SEGURIDAD AVANZADA

### 3.1 Implementar Auditoría

```python
# En app/routers/webhooks.py
from app.services.security.audit_logger import audit_logger, AuditEventType

@router.post("/whatsapp")
@limiter.limit("120/minute")
async def whatsapp_webhook(
    request: Request,
    payload: Dict = Body(...)
):
    """Webhook de WhatsApp con auditoría"""
    
    # Obtener IP del cliente
    ip_address = request.client.host
    
    try:
        # Procesar mensaje
        result = await orchestrator.process_message(payload)
        
        # Auditar acceso exitoso
        await audit_logger.log_event(
            AuditEventType.DATA_ACCESS,
            ip_address=ip_address,
            resource="whatsapp_webhook",
            details={"status": "success"}
        )
        
        return result
        
    except Exception as e:
        # Auditar error
        await audit_logger.log_event(
            AuditEventType.SUSPICIOUS_ACTIVITY,
            ip_address=ip_address,
            resource="whatsapp_webhook",
            details={"error": str(e)}
        )
        raise
```

### 3.2 Rotación Automática de Secrets

```python
# app/services/security/secret_rotation.py
"""
Sistema de Rotación Automática de Secrets
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class SecretRotationService:
    """Servicio para rotar secrets periódicamente"""
    
    def __init__(self):
        self.rotation_schedule = {
            'jwt_secret': timedelta(days=90),
            'api_key': timedelta(days=30),
            'webhook_secret': timedelta(days=60)
        }
        self.last_rotation: Dict[str, datetime] = {}
        self._task = None
    
    async def start(self):
        """Iniciar servicio de rotación"""
        self._task = asyncio.create_task(self._rotation_loop())
        logger.info("Secret rotation service started")
    
    async def stop(self):
        """Detener servicio"""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Secret rotation service stopped")
    
    async def _rotation_loop(self):
        """Loop de rotación"""
        while True:
            try:
                await asyncio.sleep(3600)  # Verificar cada hora
                
                for secret_name, rotation_period in self.rotation_schedule.items():
                    last_rotated = self.last_rotation.get(secret_name)
                    
                    if last_rotated is None or \
                       datetime.now() - last_rotated >= rotation_period:
                        await self._rotate_secret(secret_name)
                        self.last_rotation[secret_name] = datetime.now()
                        
            except Exception as e:
                logger.error(f"Error in rotation loop: {e}")
    
    async def _rotate_secret(self, secret_name: str):
        """Rotar un secret específico"""
        logger.info(f"Rotating secret: {secret_name}")
        
        # 1. Generar nuevo secret
        new_secret = self._generate_secret()
        
        # 2. Actualizar en sistema de secrets (AWS Secrets Manager, etc.)
        await self._update_secret_store(secret_name, new_secret)
        
        # 3. Notificar servicios que usan el secret
        await self._notify_secret_change(secret_name)
        
        # 4. Auditar rotación
        await audit_logger.log_event(
            AuditEventType.DATA_MODIFICATION,
            resource="secret_rotation",
            details={"secret_name": secret_name}
        )
        
        logger.info(f"Secret rotated successfully: {secret_name}")
    
    def _generate_secret(self) -> str:
        """Generar nuevo secret seguro"""
        import secrets
        return secrets.token_urlsafe(32)
    
    async def _update_secret_store(self, name: str, value: str):
        """Actualizar secret en store"""
        # TODO: Integrar con AWS Secrets Manager o similar
        pass
    
    async def _notify_secret_change(self, name: str):
        """Notificar cambio de secret"""
        # TODO: Notificar a servicios relevantes
        pass

# Instancia global
secret_rotation_service = SecretRotationService()

async def get_secret_rotation_service() -> SecretRotationService:
    return secret_rotation_service
```

---

## 4. PERFORMANCE TUNING

### 4.1 Cache Warming

```python
# app/services/cache_optimizer.py (agregar método)

async def warm_cache_on_startup(self):
    """Pre-cargar datos frecuentes al iniciar"""
    logger.info("Starting cache warming...")
    
    try:
        # 1. Cargar disponibilidad próximos 30 días
        today = date.today()
        for days_ahead in range(30):
            check_in = today + timedelta(days=days_ahead)
            check_out = check_in + timedelta(days=1)
            
            # Pre-cargar en cache
            cache_key = f"availability:{check_in}:{check_out}"
            availability = await self.pms_adapter.check_availability(
                check_in=check_in,
                check_out=check_out
            )
            await self.redis_client.setex(
                cache_key,
                3600,  # 1 hora
                json.dumps(availability)
            )
        
        # 2. Cargar tarifas actuales
        room_types = ['standard', 'deluxe', 'suite']
        for room_type in room_types:
            cache_key = f"rates:{room_type}"
            rates = await self.pms_adapter.get_room_rates(room_type)
            await self.redis_client.setex(
                cache_key,
                7200,  # 2 horas
                json.dumps(rates)
            )
        
        # 3. Cargar configuración de tenants
        tenants = await self.tenant_service.get_all_tenants()
        for tenant in tenants:
            cache_key = f"tenant:config:{tenant.id}"
            await self.redis_client.setex(
                cache_key,
                3600,
                json.dumps(tenant.config)
            )
        
        logger.info("Cache warming completed successfully")
        
    except Exception as e:
        logger.error(f"Error warming cache: {e}")
```

### 4.2 Database Index Optimization

```sql
-- scripts/db_indexes.sql
-- Índices optimizados para queries frecuentes

-- Índice para búsqueda de reservas por email
CREATE INDEX IF NOT EXISTS idx_reservations_guest_email 
ON reservations(guest_email);

-- Índice para búsqueda por rango de fechas
CREATE INDEX IF NOT EXISTS idx_reservations_dates 
ON reservations(check_in, check_out);

-- Índice compuesto para búsqueda de disponibilidad
CREATE INDEX IF NOT EXISTS idx_availability_room_dates 
ON room_availability(room_id, date, available);

-- Índice para tenant_id (multi-tenancy)
CREATE INDEX IF NOT EXISTS idx_reservations_tenant 
ON reservations(tenant_id);

-- Índice para estado de reserva
CREATE INDEX IF NOT EXISTS idx_reservations_status 
ON reservations(status) 
WHERE status IN ('confirmed', 'pending');

-- Índice parcial para reservas activas
CREATE INDEX IF NOT EXISTS idx_reservations_active 
ON reservations(check_in, check_out, status) 
WHERE status != 'cancelled' AND check_out >= CURRENT_DATE;

-- Estadísticas actualizadas
ANALYZE reservations;
ANALYZE room_availability;
```

---

## 5. OBSERVABILIDAD MEJORADA

### 5.1 Distributed Tracing

```python
# app/core/tracing.py
"""
Distributed Tracing con OpenTelemetry
"""

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

def setup_tracing(app, service_name: str = "agente-hotel-api"):
    """Configurar distributed tracing"""
    
    # Configurar proveedor de trazas
    resource = Resource(attributes={
        SERVICE_NAME: service_name
    })
    
    provider = TracerProvider(resource=resource)
    
    # Configurar exportador Jaeger
    jaeger_exporter = JaegerExporter(
        agent_host_name="localhost",
        agent_port=6831,
    )
    
    processor = BatchSpanProcessor(jaeger_exporter)
    provider.add_span_processor(processor)
    
    # Establecer proveedor global
    trace.set_tracer_provider(provider)
    
    # Instrumentar automáticamente
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    RedisInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()
    
    return trace.get_tracer(__name__)

# Usar en servicios
class ServiceWithTracing:
    def __init__(self):
        self.tracer = trace.get_tracer(__name__)
    
    async def important_operation(self):
        with self.tracer.start_as_current_span("important_operation"):
            # Operación trazada
            result = await self._do_work()
            return result
```

### 5.2 Business Metrics Dashboard

```python
# app/services/metrics_service.py (agregar métricas de negocio)

# Métricas de negocio
reservations_created = Counter(
    'business_reservations_created_total',
    'Total de reservas creadas',
    ['room_type', 'source']
)

reservation_value = Histogram(
    'business_reservation_value_usd',
    'Valor de reservas en USD',
    ['room_type']
)

guest_satisfaction = Gauge(
    'business_guest_satisfaction_score',
    'Score de satisfacción de huéspedes',
    ['rating_type']
)

occupancy_rate = Gauge(
    'business_occupancy_rate_percent',
    'Tasa de ocupación del hotel',
    ['room_type']
)

async def record_reservation_created(
    room_type: str,
    source: str,
    value: float
):
    """Registrar creación de reserva"""
    reservations_created.labels(
        room_type=room_type,
        source=source
    ).inc()
    
    reservation_value.labels(
        room_type=room_type
    ).observe(value)

async def update_occupancy_rate():
    """Actualizar tasa de ocupación"""
    # Calcular ocupación actual
    total_rooms = await get_total_rooms()
    occupied_rooms = await get_occupied_rooms()
    
    rate = (occupied_rooms / total_rooms) * 100
    
    occupancy_rate.labels(room_type='all').set(rate)
```

---

## 6. RESILIENCIA ADICIONAL

### 6.1 Graceful Degradation

```python
# app/services/orchestrator.py

async def process_message_with_fallback(
    self,
    message: UnifiedMessage
) -> Dict:
    """Procesar mensaje con degradación graciosa"""
    
    try:
        # Intentar flujo normal
        return await self.process_message(message)
        
    except PMSError as e:
        # Si PMS falla, ofrecer funcionalidad limitada
        logger.warning(f"PMS unavailable, using fallback: {e}")
        
        return await self._fallback_response(message)
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return await self._emergency_response(message)

async def _fallback_response(self, message: UnifiedMessage) -> Dict:
    """Respuesta cuando PMS no está disponible"""
    
    # Intentar responder desde cache
    cached_data = await self._get_cached_availability()
    
    if cached_data:
        return {
            'success': True,
            'message': 'Información basada en cache (última actualización hace 1 hora)',
            'data': cached_data,
            'degraded': True
        }
    
    # Si no hay cache, ofrecer contacto manual
    return {
        'success': False,
        'message': 'Sistema temporalmente no disponible. Por favor contacta: +1234567890',
        'degraded': True,
        'support_contact': '+1234567890'
    }

async def _emergency_response(self, message: UnifiedMessage) -> Dict:
    """Respuesta de emergencia para errores críticos"""
    
    # Notificar equipo de soporte
    await self.alert_service.send_critical_alert(
        "Orchestrator emergency mode",
        f"Critical error processing message from {message.sender}"
    )
    
    return {
        'success': False,
        'message': 'Disculpa las molestias. Hemos registrado tu solicitud y te contactaremos pronto.',
        'emergency_mode': True
    }
```

### 6.2 Bulkhead Pattern

```python
# app/core/bulkhead.py
"""
Bulkhead Pattern para aislamiento de fallas
"""

import asyncio
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)

class Bulkhead:
    """Limitar concurrencia para prevenir agotamiento de recursos"""
    
    def __init__(self, max_concurrent: int = 10, max_queue: int = 100):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.max_queue = max_queue
        self.current_queue = 0
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Ejecutar función con bulkhead"""
        
        # Verificar cola
        if self.current_queue >= self.max_queue:
            raise Exception("Bulkhead queue full")
        
        self.current_queue += 1
        
        try:
            async with self.semaphore:
                result = await func(*args, **kwargs)
                return result
        finally:
            self.current_queue -= 1

# Uso en PMS Adapter
pms_bulkhead = Bulkhead(max_concurrent=5, max_queue=50)

async def check_availability_with_bulkhead(self, **kwargs):
    """Verificar disponibilidad con bulkhead"""
    return await pms_bulkhead.call(
        self._check_availability_internal,
        **kwargs
    )
```

---

## 📝 CHECKLIST DE IMPLEMENTACIÓN

### Testing (Prioridad: ALTA)
- [ ] Crear tests multi-tenant scenarios
- [ ] Crear tests circuit breaker edge cases
- [ ] Crear tests de carga para auto-scaler
- [ ] Ejecutar suite completa con cobertura
- [ ] Alcanzar 85%+ de cobertura

### Validaciones (Prioridad: ALTA)
- [ ] Implementar validaciones Pydantic mejoradas
- [ ] Agregar validaciones de negocio en orchestrator
- [ ] Implementar validador de entrada robusto
- [ ] Agregar sanitización de texto libre

### Seguridad (Prioridad: MEDIA)
- [ ] Implementar sistema de auditoría
- [ ] Agregar input validator a todos los endpoints
- [ ] Configurar rotación automática de secrets
- [ ] Ejecutar security hardening script

### Performance (Prioridad: MEDIA)
- [ ] Implementar cache warming
- [ ] Aplicar índices de base de datos
- [ ] Optimizar queries N+1
- [ ] Configurar connection pooling

### Observabilidad (Prioridad: BAJA)
- [ ] Implementar distributed tracing
- [ ] Agregar business metrics
- [ ] Crear dashboards adicionales en Grafana
- [ ] Configurar alertas predictivas

### Resiliencia (Prioridad: BAJA)
- [ ] Implementar graceful degradation
- [ ] Agregar bulkhead pattern
- [ ] Configurar fallbacks automáticos
- [ ] Mejorar manejo de errores edge cases

---

## 🚀 CÓMO EJECUTAR MEJORAS

### Paso 1: Ejecutar Scripts Automáticos
```bash
cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api

# 1. Verificación de calidad actual
./scripts/run_quality_checks.sh

# 2. Hardening de seguridad
./scripts/security_hardening.sh

# 3. Validación de performance
./scripts/validate_performance_system.sh
```

### Paso 2: Implementar Tests
```bash
# Crear archivos de test
touch tests/integration/test_multi_tenant_scenarios.py
touch tests/unit/test_circuit_breaker_edge_cases.py
touch tests/load/test_auto_scaler_under_load.py

# Copiar código de esta guía

# Ejecutar tests
poetry run pytest tests/ --cov=app --cov-report=html
```

### Paso 3: Agregar Validaciones
```bash
# Editar archivos
vim app/models/schemas.py
vim app/services/orchestrator.py

# Ejecutar tests después de cambios
poetry run pytest tests/
```

### Paso 4: Verificar Todo
```bash
# Suite completa
make test
make lint
make security-fast
```

---

**Próximos Pasos:** Selecciona qué mejoras implementar primero según prioridad y recursos disponibles.

