# [INTENTS SPEC] docs/ORCHESTRATOR_INTENTS.md

## Especificación de Intents - Orchestrator

Documento living que detalla todos los intents manejados por el Orchestrator, con ejemplos, contratos de entrada/salida y políticas de fallback.

**Fecha de última actualización:** 2025-10-28  
**Versión:** 2.0  
**Estado:** Validación en desarrollo (staging)

---

## Intent Registry

| # | Intent | Handler | Confidence Requerida | Fallback | Feature Flag |
|---|--------|---------|----------------------|----------|--------------|
| 1 | `check_availability` | `_handle_availability` | 0.6+ | Escalada (info de horario) | `orchestrator.availability.enabled` |
| 2 | `make_reservation` | `_handle_make_reservation` | 0.65+ | Manual link + info de seña | N/A |
| 3 | `hotel_location` / `ask_location` | `_handle_hotel_location` | 0.55+ | Texto + ubicación fallida | N/A |
| 4 | `show_room_options` | `_handle_room_options` | 0.6+ | Lista de precios | N/A |
| 5 | `guest_services` | `_handle_info_intent` | 0.55+ | Resumen genérico + contacto | N/A |
| 6 | `hotel_amenities` | `_handle_info_intent` | 0.55+ | Resumen genérico + contacto | N/A |
| 7 | `check_in_info` | `_handle_info_intent` | 0.55+ | Info estándar | N/A |
| 8 | `check_out_info` | `_handle_info_intent` | 0.55+ | Info estándar | N/A |
| 9 | `cancellation_policy` | `_handle_info_intent` | 0.55+ | Policy estándar | N/A |
| 10 | `late_checkout` | `_handle_late_checkout` | 0.6+ | Escalada si no hay booking | N/A |
| 11 | `review_response` | `_handle_review_request` | 0.65+ | Links de review directos | N/A |

---

## Intent Detallado: `check_availability`

### Propósito
Responder consultas sobre disponibilidad de habitaciones en fechas específicas.

### Ejemplos de Triggers
- "¿Hay habitaciones disponibles para el 20 de octubre?"
- "¿Cuánto cuesta una doble para el 20-22 de octubre?"
- "Quiero reservar del 20 al 22"
- "What rooms do you have available next weekend?"

### Contrato de Entrada (NLP Output)

```python
nlp_result = {
    "intent": "check_availability",
    "confidence": 0.78,  # 0-1, threshold: 0.6
    "entities": {
        "checkin": "2025-10-20",        # YYYY-MM-DD (parsed)
        "checkout": "2025-10-22",       # YYYY-MM-DD (parsed)
        "guests": 2,                    # int (default: 1)
        "room_type": "double",          # single|double|premium (default: any)
    },
    "language": "es",
    "raw_text": "¿Hay doble disponible del 20 al 22?"
}
```

### Contrato de Salida (Orchestrator Response)

```python
response = {
    "status": "success|no_availability|error",
    "response_type": "text|interactive",
    "content": {
        "text": "Para 20/10-22/10, Doble para 2: $100/noche. Total $200. ¿Querés reservar?",
        "interactive": {
            "type": "button_menu",
            "buttons": [
                {"id": "confirm_reservation", "title": "✅ Reservar ahora"},
                {"id": "see_alternatives", "title": "🔍 Ver alternativas"},
            ]
        }
    },
    "session_update": {
        "last_availability_query": {
            "checkin": "2025-10-20",
            "checkout": "2025-10-22",
            "room_type": "double",
            "price_total": 200,
            "timestamp": "2025-10-28T15:30:00Z"
        }
    }
}
```

### Flujo de Ejecución
1. **Validar fechas**: checkin < checkout, ambas en futuro
2. **Query PMS**: `adapter.check_availability(checkin, checkout, room_type, guests)`
3. **Cache hit check**: `redis:availability:{checkin}:{checkout}` (TTL: 5min)
4. **Resultado**:
   - **Éxito**: Retornar disponibilidad + botones de reserva
   - **Sin disponibilidad**: Ofrecer alternativas (±1 día)
   - **Error PMS**: Fallback a escalada o manual link
5. **Sesión**: Guardar contexto de búsqueda para follow-ups

### Políticas de Fallback

| Condición | Acción |
|-----------|--------|
| Confidence < 0.6 | Pedir aclaración: "¿Qué fechas tienes en mente?" |
| Fechas inválidas/pasadas | Corregir: "No entendí las fechas. ¿Checkin: 20/10, Checkout: 22/10?" |
| PMS timeout | "Estamos con mucho tráfico. Intenta en 30seg o llama a recepción" |
| PMS circuit breaker OPEN | Escalada urgente + info manual |
| Cache miss spike | Throttle PMS (aumentar delay) + cache fallback |

### Métricas
- `intents_detected{intent=check_availability}` (counter)
- `availability_queries_total{status}` (counter)
- `availability_response_latency_seconds` (histogram)

---

## Intent Detallado: `make_reservation`

### Propósito
Confirmar una reservación basada en consulta de disponibilidad previa.

### Ejemplos de Triggers
- "Sí, reservo la doble"
- "Confirmo la reserva"
- "Book it"
- User hace clic en botón "✅ Reservar"

### Contrato de Entrada

```python
nlp_result = {
    "intent": "make_reservation",
    "confidence": 0.75,
    "entities": {
        "confirmation": True,           # explicit (button click) o implicit (NLP inference)
        "room_type": "double",
        "guest_name": "Juan García",    # optional, from session or NLP
        "email": "juan@example.com",    # optional
    },
    "language": "es",
}
# Context esperado en session:
session_context = {
    "last_availability_query": {
        "checkin": "2025-10-20",
        "checkout": "2025-10-22",
        "price_total": 200,
    },
    "guest_id": "guest_123",
}
```

### Contrato de Salida

```python
response = {
    "status": "success|error|requires_payment",
    "response_type": "text",
    "content": {
        "text": "¡Excelente! Reservé temporalmente la habitación.\n\nPara confirmar, enviá seña del 30%: $60\n\nDatos: ...",
        "payment_reference": "RES-2025-10-20-12345",
        "deposit_amount": 60.00,
        "bank_info": {...},
        "instructions_url": "https://hotel.com/payment/RES-2025-10-20-12345"
    },
    "session_update": {
        "reservation": {
            "id": "RES-2025-10-20-12345",
            "status": "pending_payment",
            "timestamp": "2025-10-28T15:31:00Z",
            "deposit_amount": 60.00,
        }
    }
}
```

### Flujo de Ejecución
1. **Verificar contexto**: ¿Hay `last_availability_query` válido en sesión?
2. **Acquirir lock**: `lock_service.acquire(user_id, room_id)` (atomic)
3. **Validar disponibilidad**: Re-query PMS para confirmar stock
4. **Crear reserva**: `pms_adapter.make_reservation(...)`
5. **Generar ref de pago**: Payment token + deposit calculation
6. **Guardar sesión**: Estado de reserva + ref de pago
7. **Responder**: Instrucciones de seña + datos bancarios

### Políticas de Fallback

| Condición | Acción |
|-----------|--------|
| Sin contexto previo | "Primero consultemos disponibilidad. ¿Qué fechas buscas?" |
| Lock adquisición falla | "Alguien está reservando esta habitación. Intenta otra." |
| PMS says "no stock" | "Lo siento, se ocupó. Opciones alternativas: ..." |
| PMS error | Escalar a staff manual |

---

## Intent Detallado: `late_checkout`

### Propósito
Permitir a huéspedes solicitar extensión de checkout.

### Ejemplos de Triggers
- "¿Puedo hacer late checkout?"
- "¿Hasta qué hora me quedo?"
- "Necesito más tiempo"

### Contrato de Entrada

```python
nlp_result = {
    "intent": "late_checkout",
    "confidence": 0.72,
    "entities": {
        "requested_time": "14:00",  # optional, default: standard + 2h
        "reason": "flight_delay",    # optional: flight_delay, extra_night, meeting, etc
    },
    "language": "es",
}
session_context = {
    "guest_id": "guest_123",
    "current_booking": {
        "reservation_id": "RES-2025-10-20-12345",
        "checkout_date": "2025-10-22",
    }
}
```

### Contrato de Salida

```python
response = {
    "status": "approved|denied|requires_payment",
    "response_type": "text",
    "content": {
        "text": "¡Perfecto! Late checkout disponible hasta las 14:00 ✅\n\n💰 Cargo: $50 (50% tarifa diaria)\n\n¿Confirmas?",
    },
    "session_update": {
        "late_checkout": {
            "status": "pending_confirmation",
            "requested_time": "14:00",
            "fee": 50.00,
        }
    }
}
```

### Políticas de Fallback

| Condición | Acción |
|-----------|--------|
| No hay booking en sesión | "Necesito tu número de reserva para procesar late checkout" |
| Habitación ya ocupada | "Lo siento, otra reserva comienza a las 12:00. No hay extensión." |
| Feature flag OFF | Responder con info genérica + teléfono recepción |

---

## Intent Detallado: `review_response`

### Propósito
Recopilar reseñas post-estadía de huéspedes.

### Ejemplos de Triggers
- User hace clic en link de reseña
- "¿Dónde dejo una reseña?"
- "Me gustaría dejar feedback"

### Contrato de Entrada

```python
nlp_result = {
    "intent": "review_response",
    "confidence": 0.80,
    "entities": {
        "action": "request_links|submit_feedback",
        "rating": 4.5,  # 1-5 stars (if submit_feedback)
        "comment": "Muy bueno, pero habitación fría"
    },
    "language": "es",
}
```

### Contrato de Salida

```python
response = {
    "status": "success|error",
    "response_type": "text|button_menu",
    "content": {
        "text": "¡Gracias por tu feedback! Aquí están los liens de reseña:",
        "review_links": {
            "google": "https://maps.google.com/...",
            "booking": "https://booking.com/...",
            "tripadvisor": "https://tripadvisor.com/..."
        }
    }
}
```

---

## Fallback General (Low Confidence / Unknown Intent)

### Trigger
- Confidence NLP < 0.55
- Intent no mappeado en `_intent_handlers`
- NLP engine error

### Estrategia (Feature Flag: `nlp.fallback.enhanced`)

**Si `nlp.fallback.enhanced = False` (default):**
```
❌ "No entendí bien. ¿Podrías reformular?"
[Mostrar menú de opciones]
  - 🔍 Ver disponibilidad
  - 🏨 Información del hotel
  - 📞 Hablar con recepción
```

**Si `nlp.fallback.enhanced = True`:**
```
1. Sugerir intent más probable:
   "Creo que querías consultar [INTENT]. ¿Es correcto?"

2. Si usuario rechaza sugerencia:
   → Escalada a staff humano

3. Si usuario no responde (timeout 30seg):
   → Logged como "auto_escalation_timeout"
   → Alert a staff
```

### Contrato de Salida (Fallback)

```python
fallback_response = {
    "status": "fallback",
    "response_type": "text|button_menu",
    "content": {
        "text": "No estoy seguro qué necesitas. ¿Cuál de estos temas te interesa?",
        "menu": [
            {"id": "availability_query", "title": "🔍 Consultar disponibilidad"},
            {"id": "info_request", "title": "🏨 Información del hotel"},
            {"id": "escalate", "title": "📞 Hablar con recepción"},
        ]
    },
    "telemetry": {
        "fallback_reason": "low_confidence|unknown_intent|nlp_error",
        "nlp_confidence": 0.42,
        "suggested_intents": ["check_availability", "guest_services"],
    }
}
```

### Métricas de Fallback
- `nlp_fallbacks_total{reason}` (counter)
- `fallback_escalation_rate` (gauge)
- `fallback_resolution_rate` (gauge: % que el user completa acción después de fallback)

---

## Cómo Añadir un Nuevo Intent

### Checklist
1. **Defina el intent** en `NLPEngine` (patrón + exemplos de training)
2. **Cree handler method** en `Orchestrator._intent_handlers`:
   ```python
   async def _handle_new_intent(self, nlp_result: dict, session_data: dict, message: UnifiedMessage) -> dict:
       """Handle new_intent with I/O contracts."""
       # Implementation
       return response_dict
   ```
3. **Registre en dispatcher**:
   ```python
   self._intent_handlers["new_intent"] = self._handle_new_intent
   ```
4. **Documente**:
   - Triggers en Rasa NLU
   - Contrato de entrada/salida aquí
   - Políticas de fallback
5. **Tests**:
   - Unit test: `test_handle_new_intent` (éxito, fallback, error)
   - Integration test: End-to-end con NLP mock
6. **Rollout**:
   - Feature flag: `orchestrator.new_intent.enabled = False` (default)
   - Validar en staging
   - Habilitar gradualmente en producción

---

## Próximas Mejoras Planeadas

| Mejora | Target | Impacto |
|--------|--------|---------|
| Multi-turn intent composition | Q4 2025 | Soportar: "Quiero doble, del 20 al 22, con late checkout" en 1 mensaje |
| Sentiment analysis | Q4 2025 | Detectar frustración → escalada más agresiva |
| Context carry-over | Q1 2026 | Mantener contexto entre intents (ej: disponibilidad → reserva automática) |
| A/B testing fallback messages | Q1 2026 | Medir engagement por variante de texto |
| Predictive upsell | Q2 2026 | Sugerir late checkout, upgrades basado en intent + perfil guest |

---

## Versionado de Intents

Este documento se versionará según cambios que afecten contratos públicos:

- **Versión 2.0** (2025-10-28): Especificación inicial, 11 intents
- **v2.1** (TBD): Añadir nuevo intent X
- **v3.0** (TBD): Refactor de fallback + sentiment analysis

---

## Referencias

- **NLP Engine**: `app/services/nlp_engine.py`
- **Orchestrator**: `app/services/orchestrator.py`
- **Tests**: `tests/integration/test_orchestrator.py`, `tests/unit/test_orchestrator_*.py`
- **Rasa NLU Config**: `rasa_nlu/domain.yml`, `rasa_nlu/data/nlu.yml`
