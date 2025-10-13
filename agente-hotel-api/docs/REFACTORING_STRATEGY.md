# Estrategia de Refactorización: Orchestrator.handle_intent()

**Estado**: 🔴 CRÍTICO - Refactorización requerida  
**Fecha creación**: 2025-01-13  
**Prioridad**: ALTA  
**Estimación**: 2-3 días de desarrollo

---

## 📊 Análisis del Problema

### Métrica actual
```
Método: handle_intent()
Líneas: 937 (94% del total del archivo)
Complejidad ciclomática: ~50+ (estimado)
Features integradas: 6+
Estado: CRÍTICO - Imposible mantener
```

### Comparación de métodos en orchestrator.py
```
Método                              Líneas    Estado
================================================
handle_intent                       937       🔴 CRÍTICO
handle_unified_message              208       ⚠️  Alto
_escalate_to_staff                  107       ✅ OK
_handle_interactive_response        63        ✅ OK
_get_low_confidence_message         42        ✅ OK
_get_technical_error_message        25        ✅ OK
__init__                            8         ✅ OK
```

### Features identificadas dentro de handle_intent()
1. **Business hours check** (FEATURE 2) - ~50 líneas
2. **Room images** (FEATURE 3) - ~60 líneas
3. **Late checkout** (FEATURE 4) - ~80 líneas
4. **QR code generation** (FEATURE 5) - ~40 líneas
5. **Review requests** (FEATURE 6) - ~70 líneas
6. **Availability checking** - ~150 líneas
7. **Reservation creation** - ~200 líneas
8. **Reservation modification** - ~100 líneas
9. **Cancellation** - ~80 líneas

### Problemas identificados
- ❌ **Mantenibilidad**: Cambios en una feature afectan a todas
- ❌ **Testabilidad**: Imposible testear features aisladas
- ❌ **Código duplicado**: Validaciones repetidas
- ❌ **Complejidad cognitiva**: >50 caminos de ejecución
- ❌ **Violación SRP**: Un método tiene 9 responsabilidades

---

## 🎯 Estrategia Propuesta: Strategy Pattern

### Arquitectura objetivo
```python
class Orchestrator:
    def __init__(self, pms_adapter, session_manager, lock_service):
        self.pms = pms_adapter
        self.sessions = session_manager
        self.locks = lock_service
        
        # Intent routing map
        self._intent_handlers = {
            "consultar_horario": self._handle_business_hours,
            "consultar_disponibilidad": self._handle_availability,
            "crear_reserva": self._handle_create_reservation,
            "modificar_reserva": self._handle_modify_reservation,
            "cancelar_reserva": self._handle_cancel_reservation,
            "solicitar_late_checkout": self._handle_late_checkout,
            "ver_imagenes_habitacion": self._handle_room_images,
            "generar_qr": self._handle_qr_generation,
            "solicitar_review": self._handle_review_request,
        }
    
    async def handle_intent(
        self, 
        nlp_result: dict, 
        session_data: dict, 
        message: UnifiedMessage
    ) -> dict:
        """
        Dispatcher principal de intents - Coordina routing a handlers específicos
        
        Target: <100 líneas
        Complejidad ciclomática: <10
        """
        intent = nlp_result.get("intent")
        confidence = nlp_result.get("confidence", 0.0)
        
        # Pre-validation: Confidence check
        if confidence < CONFIDENCE_THRESHOLD_VERY_LOW:
            return await self._escalate_to_staff(
                message, "low_confidence", intent, session_data
            )
        
        # Intent routing
        handler = self._intent_handlers.get(intent, self._handle_unknown_intent)
        
        try:
            # Execute specific handler
            return await handler(nlp_result, session_data, message)
        except PMSError as e:
            logger.error("pms_error_in_handler", intent=intent, error=str(e))
            return await self._escalate_to_staff(
                message, "pms_error", intent, session_data
            )
        except Exception as e:
            logger.error("handler_exception", intent=intent, error=str(e))
            return await self._escalate_to_staff(
                message, "technical_error", intent, session_data
            )
```

### Ventajas del Strategy Pattern
✅ **Separación de concerns**: Cada handler maneja una responsabilidad  
✅ **Testabilidad**: Cada handler es testeable aisladamente  
✅ **Extensibilidad**: Agregar intents sin modificar código existente (Open/Closed)  
✅ **Mantenibilidad**: Cambios en un handler no afectan otros  
✅ **Legibilidad**: Código auto-documentado por nombres de métodos  
✅ **Complejidad reducida**: Método principal <100 líneas, complejidad ciclomática <10

---

## 📋 Plan de Ejecución (4 Fases)

### Fase 1: Preparación (Safety Net) ✅ COMPLETADA
**Duración**: 4 horas  
**Estado**: ✅ COMPLETADO

**Tareas completadas**:
- ✅ Crear tests de integración exhaustivos (`test_handle_intent_integration.py`)
- ✅ Cubrir las 6+ features con 15+ test cases
- ✅ Documentar comportamiento actual
- ✅ Identificar dependencias entre features

**Artefactos creados**:
- `tests/integration/test_handle_intent_integration.py` (450+ líneas)
- `tests/unit/test_orchestrator_escalation.py` (300+ líneas)
- `tests/unit/test_audit_logger.py` (250+ líneas)

**Total**: 1000+ líneas de tests como safety net

---

### Fase 2: Extracción Incremental (Handler por Handler) ⏳ PENDIENTE
**Duración estimada**: 2 días  
**Estado**: ⏳ Pendiente

#### Orden de extracción (simple → complejo)

##### 2.1. Handler: Business Hours (Prioridad 1)
**Líneas**: ~50  
**Complejidad**: Baja  
**Test asociado**: `test_business_hours_check_during_hours`, `test_business_hours_check_after_hours`

```python
async def _handle_business_hours(
    self,
    nlp_result: dict,
    session_data: dict,
    message: UnifiedMessage
) -> dict:
    """
    Maneja consultas de horario comercial
    
    Args:
        nlp_result: Resultado del NLP engine
        session_data: Estado de la sesión del usuario
        message: Mensaje unificado del usuario
        
    Returns:
        dict: Response con información de horarios
        
    Raises:
        None (siempre retorna respuesta)
    """
    # Implementation extracted from handle_intent lines 400-450
    pass
```

**Pasos**:
1. Identificar líneas exactas en handle_intent() (grep "# FEATURE 2")
2. Copiar código a nuevo método
3. Reemplazar en handle_intent() con llamada al handler
4. Ejecutar tests: `pytest tests/integration/test_handle_intent_integration.py::TestBusinessHoursFeature -v`
5. Commit: `refactor(orchestrator): extract _handle_business_hours()`

---

##### 2.2. Handler: Room Images (Prioridad 2)
**Líneas**: ~60  
**Complejidad**: Baja  
**Test asociado**: `test_room_images_request`

```python
async def _handle_room_images(
    self,
    nlp_result: dict,
    session_data: dict,
    message: UnifiedMessage
) -> dict:
    """Maneja solicitudes de imágenes de habitaciones"""
    pass
```

---

##### 2.3. Handler: QR Generation (Prioridad 3)
**Líneas**: ~40  
**Complejidad**: Baja  
**Test asociado**: `test_qr_code_generation`

```python
async def _handle_qr_generation(
    self,
    nlp_result: dict,
    session_data: dict,
    message: UnifiedMessage
) -> dict:
    """Maneja generación de códigos QR para reservas"""
    pass
```

---

##### 2.4. Handler: Review Request (Prioridad 4)
**Líneas**: ~70  
**Complejidad**: Media  
**Test asociado**: `test_review_request_after_checkout`

```python
async def _handle_review_request(
    self,
    nlp_result: dict,
    session_data: dict,
    message: UnifiedMessage
) -> dict:
    """Maneja solicitudes de review post-checkout"""
    pass
```

---

##### 2.5. Handler: Late Checkout (Prioridad 5)
**Líneas**: ~80  
**Complejidad**: Media  
**Test asociado**: `test_late_checkout_request`

```python
async def _handle_late_checkout(
    self,
    nlp_result: dict,
    session_data: dict,
    message: UnifiedMessage
) -> dict:
    """Maneja solicitudes de late checkout"""
    pass
```

---

##### 2.6. Handler: Availability (Prioridad 6)
**Líneas**: ~150  
**Complejidad**: Alta  
**Tests asociados**: `test_availability_with_dates`, `test_availability_no_rooms_available`

```python
async def _handle_availability(
    self,
    nlp_result: dict,
    session_data: dict,
    message: UnifiedMessage
) -> dict:
    """
    Maneja consultas de disponibilidad
    
    Complex flow:
    1. Extract date entities from NLP result
    2. Validate date range
    3. Call PMS adapter with circuit breaker
    4. Format response with available rooms
    5. Update session with search context
    """
    pass
```

---

##### 2.7. Handler: Create Reservation (Prioridad 7 - MÁS COMPLEJO)
**Líneas**: ~200  
**Complejidad**: Muy alta  
**Tests asociados**: `test_create_reservation_complete_data`, `test_create_reservation_missing_data`

```python
async def _handle_create_reservation(
    self,
    nlp_result: dict,
    session_data: dict,
    message: UnifiedMessage
) -> dict:
    """
    Maneja creación de reservas - FLUJO MÁS COMPLEJO
    
    State machine:
    - GATHER_INFO: Solicitar datos faltantes
    - CONFIRM: Confirmar detalles con usuario
    - CREATE: Llamar PMS para crear reserva
    - FINALIZE: Enviar confirmación
    
    Required data:
    - check_in, check_out, room_type, guests
    - guest_name, guest_email, guest_phone
    
    Uses:
    - Distributed lock (avoid double booking)
    - Session state management
    - PMS adapter with retry
    """
    pass
```

**Nota**: Este handler puede dividirse en sub-handlers:
- `_gather_reservation_data()`
- `_confirm_reservation_details()`
- `_create_reservation_in_pms()`

---

### Checklist por cada extracción
Para cada handler extraído:

1. **Pre-extracción**:
   - [ ] Identificar líneas exactas en código actual
   - [ ] Documentar dependencias (servicios, session state)
   - [ ] Verificar tests existentes cubren el caso

2. **Extracción**:
   - [ ] Crear método `_handle_XXX()` con docstring completo
   - [ ] Copiar código del método gigante
   - [ ] Agregar type hints (nlp_result: dict, etc.)
   - [ ] Refactorizar validaciones repetidas

3. **Integración**:
   - [ ] Agregar handler al mapa `_intent_handlers`
   - [ ] Reemplazar código en handle_intent() con routing
   - [ ] Eliminar código duplicado

4. **Validación**:
   - [ ] Ejecutar tests específicos: `pytest tests/integration/...::TestXXX -v`
   - [ ] Ejecutar suite completa: `pytest tests/ -v`
   - [ ] Verificar cobertura: `pytest --cov=app.services.orchestrator`
   - [ ] Validar no hay regresión de performance

5. **Post-extracción**:
   - [ ] Commit atómico: `refactor(orchestrator): extract _handle_XXX()`
   - [ ] Actualizar métricas de complejidad
   - [ ] Documentar en CHANGELOG.md

---

### Fase 3: Refactorización del Método Principal ⏳ PENDIENTE
**Duración estimada**: 4 horas  
**Estado**: ⏳ Pendiente (después de Fase 2)

#### Transformación de handle_intent()

**Estado actual**: 937 líneas, complejidad ~50  
**Estado objetivo**: <100 líneas, complejidad <10

**Estructura objetivo**:
```python
async def handle_intent(
    self,
    nlp_result: dict,
    session_data: dict,
    message: UnifiedMessage
) -> dict:
    """
    Dispatcher principal de intents a handlers específicos
    
    Responsabilidades:
    1. Validación de confidence
    2. Routing a handler apropiado
    3. Error handling global
    4. Escalación en caso de fallo
    
    Args:
        nlp_result: Resultado del análisis NLP con intent y entidades
        session_data: Estado persistente de la sesión del usuario
        message: Mensaje unificado normalizado
        
    Returns:
        dict: Respuesta estructurada para el usuario
        {
            "response_type": "text|image|media",
            "content": str,
            "escalated": bool,
            "metadata": dict
        }
        
    Raises:
        None: Todos los errores se manejan internamente
    """
    intent = nlp_result.get("intent")
    confidence = nlp_result.get("confidence", 0.0)
    
    # Metrics
    intent_processing_start = time.time()
    
    # Pre-validation: Low confidence check
    if confidence < CONFIDENCE_THRESHOLD_VERY_LOW:
        logger.warning("low_confidence_intent", intent=intent, confidence=confidence)
        return await self._escalate_to_staff(
            message, "low_confidence", intent, session_data
        )
    
    # Intent routing
    handler = self._intent_handlers.get(intent)
    
    if not handler:
        logger.warning("unknown_intent", intent=intent)
        return await self._handle_unknown_intent(nlp_result, session_data, message)
    
    # Execute handler with error handling
    try:
        result = await handler(nlp_result, session_data, message)
        
        # Record success metric
        intent_processing_time.labels(
            intent=intent,
            status="success"
        ).observe(time.time() - intent_processing_start)
        
        return result
        
    except PMSError as e:
        logger.error("pms_error_in_handler", intent=intent, error=str(e))
        intent_processing_time.labels(intent=intent, status="pms_error").observe(
            time.time() - intent_processing_start
        )
        return await self._escalate_to_staff(
            message, "pms_error", intent, session_data, details={"error": str(e)}
        )
        
    except Exception as e:
        logger.exception("handler_exception", intent=intent)
        intent_processing_time.labels(intent=intent, status="error").observe(
            time.time() - intent_processing_start
        )
        return await self._escalate_to_staff(
            message, "technical_error", intent, session_data, details={"error": str(e)}
        )
```

**Líneas totales**: ~80 líneas  
**Complejidad ciclomática**: ~8

---

### Fase 4: Validación Post-Refactoring ⏳ PENDIENTE
**Duración estimada**: 4 horas  
**Estado**: ⏳ Pendiente (después de Fase 3)

#### Checklist de validación

**Tests**:
- [ ] Ejecutar suite completa: `pytest tests/ -v --cov`
- [ ] Cobertura ≥ baseline (registrar baseline antes de empezar)
- [ ] Todos los tests de integración pasan (15+ tests)
- [ ] Todos los tests unitarios pasan (25+ tests)

**Métricas de código**:
- [ ] handle_intent() <100 líneas ✅ Target: 80
- [ ] Cada handler <200 líneas ✅ Target: 50-150
- [ ] Complejidad ciclomática <10 por método
- [ ] Duplicación de código <3%

**Performance**:
- [ ] Ejecutar load testing: `locust -f tests/load/test_orchestrator.py`
- [ ] P50 latency: Sin cambios ±5%
- [ ] P95 latency: Sin cambios ±10%
- [ ] P99 latency: Sin cambios ±15%
- [ ] Throughput: Sin cambios ±5%

**Observabilidad**:
- [ ] Métricas Prometheus funcionando
- [ ] Dashboards Grafana actualizados con nuevos handlers
- [ ] Logs estructurados incluyen handler name
- [ ] Tracing distribuido funciona (si implementado)

**Documentación**:
- [ ] Docstrings completos en todos los handlers
- [ ] README actualizado con nueva arquitectura
- [ ] CHANGELOG.md con entry detallado
- [ ] Diagramas de arquitectura actualizados

---

## 🎯 Métricas de Éxito

### Antes del refactoring
```
handle_intent()
├── Líneas: 937
├── Complejidad: ~50
├── Features: 9 mezcladas
├── Testabilidad: ❌ Baja
├── Mantenibilidad: ❌ Crítica
└── Performance: Baseline
```

### Después del refactoring
```
handle_intent() (dispatcher)
├── Líneas: <100 ✅
├── Complejidad: <10 ✅
└── Handlers separados:
    ├── _handle_business_hours() (~50 líneas) ✅
    ├── _handle_room_images() (~60 líneas) ✅
    ├── _handle_qr_generation() (~40 líneas) ✅
    ├── _handle_review_request() (~70 líneas) ✅
    ├── _handle_late_checkout() (~80 líneas) ✅
    ├── _handle_availability() (~150 líneas) ✅
    ├── _handle_create_reservation() (~200 líneas) ✅
    ├── _handle_modify_reservation() (~100 líneas) ✅
    └── _handle_cancel_reservation() (~80 líneas) ✅

Testabilidad: ✅ Alta (handlers aislados)
Mantenibilidad: ✅ Excelente (SRP)
Performance: ✅ Sin regresión (<5%)
Cobertura: ✅ ≥baseline
```

---

## ⚠️ Riesgos y Mitigaciones

### Riesgo 1: Romper comportamiento existente
**Probabilidad**: Media  
**Impacto**: Alto  
**Mitigación**:
- ✅ Tests de integración exhaustivos ANTES de empezar
- ✅ Refactorización incremental (handler por handler)
- ✅ Ejecutar tests después de CADA cambio
- ✅ Commits atómicos para fácil rollback

### Riesgo 2: State compartido entre handlers
**Probabilidad**: Media  
**Impacto**: Alto  
**Mitigación**:
- ✅ Pasar session_data explícitamente a cada handler
- ✅ Evitar variables de instancia mutables
- ✅ Documentar side effects en docstrings
- ✅ Usar locks para operaciones críticas

### Riesgo 3: Regresión de performance
**Probabilidad**: Baja  
**Impacto**: Medio  
**Mitigación**:
- ✅ Profiling antes/después con py-spy
- ✅ Load testing con locust
- ✅ Monitoreo de métricas Prometheus (P95 latency)
- ✅ Comparación de flamegraphs

### Riesgo 4: Aumento de complejidad por abstracción
**Probabilidad**: Baja  
**Impacto**: Bajo  
**Mitigación**:
- ✅ Strategy pattern es simple y conocido
- ✅ Nombres de métodos auto-documentados
- ✅ Documentación exhaustiva
- ✅ Evitar sobre-ingeniería

---

## 📚 Referencias

### Patrones de diseño
- **Strategy Pattern**: Gang of Four Design Patterns
- **Command Pattern**: Alternativa considerada pero descartada (más overhead)

### Principios SOLID aplicados
- **SRP**: Cada handler tiene una única responsabilidad
- **OCP**: Extensible sin modificar handle_intent()
- **LSP**: Handlers comparten misma signature
- **ISP**: Interface mínima (3 parámetros)
- **DIP**: Dependencia de abstracciones (PMS adapter)

### Métricas de código limpio
- **Máximo líneas por método**: 200 (handler complejo), ideal 50-100
- **Complejidad ciclomática**: <10 (preferible <5)
- **Nivel de anidamiento**: <4 niveles
- **Duplicación**: <3%

---

## ✅ Checklist Final

### Antes de empezar refactoring
- [x] Tests de integración creados y passing
- [ ] Cobertura baseline medida y documentada
- [ ] Performance baseline capturado (P50, P95, P99)
- [ ] Branch creado: `refactor/orchestrator-handle-intent`

### Durante refactoring
- [ ] Cada handler extraído pasa sus tests
- [ ] Commits atómicos después de cada handler
- [ ] Métricas de complejidad mejoran incrementalmente
- [ ] Sin regresión de tests en cada paso

### Al finalizar refactoring
- [ ] handle_intent() <100 líneas
- [ ] Todos los handlers <200 líneas
- [ ] Suite completa de tests pasa
- [ ] Cobertura ≥ baseline
- [ ] Performance sin regresión
- [ ] Documentación completa
- [ ] Pull request con review detallado

---

## 📅 Timeline

| Fase | Duración | Dependencias |
|------|----------|--------------|
| Fase 1: Preparación | 4h | ✅ COMPLETADA |
| Fase 2: Extracción handlers | 2 días | Fase 1 |
| Fase 3: Refactor método principal | 4h | Fase 2 |
| Fase 4: Validación | 4h | Fase 3 |
| **TOTAL** | **2.5 días** | - |

**Fecha inicio planeada**: A definir con el equipo  
**Fecha fin estimada**: +2.5 días desde inicio  

---

**Última actualización**: 2025-01-13  
**Documento creado por**: GitHub Copilot (análisis automatizado)  
**Estado**: 📋 Plan aprobado, pendiente ejecución
