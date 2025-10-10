# Business Metrics - Sistema Hotelero IA

## Resumen Ejecutivo

Este documento describe las **métricas de negocio** implementadas en el sistema de agente hotelero IA. Estas métricas van más allá de las métricas técnicas (latencia, errores, throughput) y se centran en indicadores clave del negocio hotelero.

## Arquitectura de Métricas

### Ubicación de Archivos

- **Definición de métricas**: `app/services/business_metrics.py`
- **Integración en Orchestrator**: `app/services/orchestrator.py` (líneas ~30-50)
- **Integración en PMS Adapter**: `app/services/pms_adapter.py` (método `create_reservation`)
- **Alertas de negocio**: `docker/prometheus/business_alerts.yml`
- **Dashboard Grafana**: `docker/grafana/dashboards/business_metrics.json`

### Flujo de Registro

```
Mensaje WhatsApp → Orchestrator → messages_by_channel++
                      ↓
                  NLP Engine → intents_detected++ (con confidence_level)
                      ↓
                  PMS Adapter → create_reservation()
                      ↓
                  record_reservation() → hotel_reservations_total++
                                      → reservation_value.observe()
                                      → reservation_nights.observe()
                                      → reservation_lead_time.observe()
```

## Categorías de Métricas

### 1. Métricas de Reservas

#### `hotel_reservations_total` (Counter)
Contador total de reservas por estado, canal y tipo de habitación.

**Labels:**
- `status`: `confirmed`, `pending`, `failed`
- `channel`: `whatsapp`, `gmail`, `web`
- `room_type`: `deluxe`, `standard`, `suite`

**Queries PromQL útiles:**
```promql
# Reservas confirmadas en las últimas 24h
sum(increase(hotel_reservations_total{status="confirmed"}[24h]))

# Tasa de conversión por canal
rate(hotel_reservations_total{status="confirmed"}[1h]) 
/ 
rate(hotel_reservations_total[1h])
```

#### `hotel_reservation_value_euros` (Histogram)
Distribución del valor de las reservas en euros.

**Buckets:** [50, 100, 200, 500, 1000, 2000, 5000, 10000]

**Queries útiles:**
```promql
# Revenue total en las últimas 24h
sum(increase(hotel_reservation_value_euros_sum[24h]))

# Valor promedio de reserva (P50)
histogram_quantile(0.5, rate(hotel_reservation_value_euros_bucket[1h]))
```

#### `hotel_reservation_nights` (Histogram)
Número de noches por reserva.

**Buckets:** [1, 2, 3, 5, 7, 10, 14, 21, 30]

**Uso:** Identificar patrones de estancia (corta, media, larga).

#### `hotel_reservation_lead_time_days` (Histogram)
Días entre la fecha de reserva y el check-in.

**Buckets:** [0, 1, 3, 7, 14, 30, 60, 90, 180]

**Uso:** Optimizar pricing dinámico según anticipación de reserva.

---

### 2. Métricas de Conversación

#### `hotel_active_conversations` (Gauge)
Número de conversaciones activas en tiempo real.

**Uso:** Dimensionamiento de recursos, picos de demanda.

#### `hotel_conversation_duration_seconds` (Histogram)
Duración de cada conversación.

**Buckets:** [30, 60, 120, 300, 600, 1200, 1800]

**Alertas asociadas:**
- P95 > 600s (10 minutos) → Conversaciones muy largas

#### `hotel_messages_per_conversation` (Histogram)
Número de mensajes intercambiados en una conversación.

**Buckets:** [1, 2, 5, 10, 15, 20, 30, 50]

**Uso:** Medir eficiencia del bot (menos mensajes = más eficiente).

---

### 3. Métricas de Satisfacción

#### `hotel_guest_satisfaction_score` (Histogram)
Puntuación de satisfacción del huésped (escala 1-5).

**Alertas asociadas:**
- Mediana < 3.5 durante 30 min → Baja satisfacción

#### `hotel_guest_nps_score` (Histogram)
Net Promoter Score (-100 a 100).

**Alertas asociadas:**
- Mediana < 0 durante 1h → NPS negativo (crítico)

**Registro manual:** Estas métricas se registran al finalizar la conversación o en encuestas post-estancia.

---

### 4. Métricas Operacionales

#### `hotel_occupancy_rate` (Gauge)
Tasa de ocupación del hotel (%).

**Actualización:** Cronjob o tarea en background cada 1-6 horas.

**Alertas asociadas:**
- < 30% durante 1h → Ocupación crítica baja

#### `hotel_available_rooms` (Gauge)
Habitaciones disponibles por tipo.

**Label:** `room_type`

**Alertas asociadas:**
- Sum < 5 durante 30 min → Pocas habitaciones disponibles

#### `hotel_daily_revenue_euros` (Gauge)
Revenue diario total.

**Uso:** Dashboard ejecutivo, comparación vs forecast.

#### `hotel_adr_euros` (Gauge)
Average Daily Rate (precio promedio por habitación/noche).

**Fórmula:** `total_revenue / total_rooms_sold`

#### `hotel_revpar_euros` (Gauge)
Revenue Per Available Room.

**Fórmula:** `ADR * Occupancy_Rate` o `total_revenue / total_rooms_available`

**Alertas asociadas:**
- RevPAR decline > 15% vs mismo día semana anterior → Warning

---

### 5. Métricas de Intents/NLP

#### `hotel_intents_detected_total` (Counter)
Intents detectados por el NLP con nivel de confianza.

**Labels:**
- `intent`: `check_availability`, `make_reservation`, `cancel_reservation`, etc.
- `confidence_level`: `high` (≥0.75), `medium` (0.45-0.75), `low` (<0.45)

**Queries útiles:**
```promql
# Top 5 intents más frecuentes
topk(5, sum by (intent) (increase(hotel_intents_detected_total[24h])))

# Distribución de confianza
sum by (confidence_level) (rate(hotel_intents_detected_total[1h]))
```

#### `hotel_nlp_fallbacks_total` (Counter)
Casos donde el NLP no pudo determinar el intent.

**Alertas asociadas:**
- Tasa de fallback > 25% durante 10 min → Warning

---

### 6. Métricas de Canales

#### `hotel_messages_by_channel_total` (Counter)
Mensajes recibidos por canal.

**Label:** `channel` (`whatsapp`, `gmail`, `web`)

**Uso:** Identificar canal preferido por huéspedes.

#### `hotel_response_time_by_channel_seconds` (Histogram)
Tiempo de respuesta desde recepción de mensaje hasta envío de respuesta.

**Buckets:** [1, 2, 5, 10, 30, 60, 120, 300]

**Alertas asociadas:**
- P95 > 30s durante 15 min → Respuesta lenta

---

### 7. Métricas de Errores de Negocio

#### `hotel_failed_reservations_total` (Counter)
Reservas que fallaron con clasificación de causa.

**Label:** `reason`
- `payment_failed`: Fallo en pago
- `no_availability`: No hay habitaciones
- `validation_error`: Datos inválidos
- `timeout`: Timeout del PMS
- `unknown_error`: Error no clasificado

**Alertas asociadas:**
- Tasa > 15% durante 5 min → Crítica

#### `hotel_cancellations_total` (Counter)
Reservas canceladas con tipo de cancelación.

**Label:** `cancellation_type`
- `guest_initiated`: Cancelada por huésped
- `hotel_initiated`: Cancelada por hotel
- `no_show`: No show

**Alertas asociadas:**
- Tasa > 20% durante 1h → Warning

---

## Funciones Helper

### `record_reservation()`
Registra una reserva con todas sus métricas asociadas.

**Parámetros:**
```python
record_reservation(
    status="confirmed",      # confirmed, pending, failed
    channel="whatsapp",      # whatsapp, gmail, web
    room_type="deluxe",      # deluxe, standard, suite
    value=450.00,            # Valor total en euros
    nights=3,                # Número de noches
    lead_time_days=15        # Días entre reserva y check-in
)
```

**Ubicación:** Llamada en `pms_adapter.py:create_reservation()`

### `record_conversation_metrics()`
Registra métricas de una conversación completada.

**Parámetros:**
```python
record_conversation_metrics(
    duration_seconds=245,
    message_count=12,
    satisfaction_score=5  # Opcional
)
```

**Ubicación:** Llamar al finalizar conversación (webhook de cierre o timeout).

### `update_operational_metrics()`
Actualiza métricas operacionales del hotel.

**Parámetros:**
```python
update_operational_metrics(
    current_occupancy=75.5,
    rooms_available={"standard": 5, "deluxe": 2, "suite": 1},
    daily_rev=12500.00,
    adr=165.50
)
```

**Ubicación:** Cronjob o background task cada 1-6 horas.

---

## Alertas de Negocio

### Alertas Críticas

1. **HighReservationFailureRate**
   - Condición: Tasa de fallos > 15% durante 5 min
   - Acción: Verificar PMS y pasarelas de pago

2. **NegativeNPS**
   - Condición: NPS mediana < 0 durante 1h
   - Acción: Revisión inmediata de experiencia del huésped

### Alertas de Warning

1. **HighNLPFallbackRate**
   - Condición: > 25% de mensajes con fallback NLP durante 10 min
   - Acción: Revisar entrenamiento del modelo

2. **LongConversationDuration**
   - Condición: P95 > 10 minutos durante 10 min
   - Acción: Revisar flujos de conversación

3. **LowGuestSatisfaction**
   - Condición: Satisfacción mediana < 3.5/5 durante 30 min
   - Acción: Revisar interacciones recientes

4. **RevPARDecline**
   - Condición: RevPAR < 85% vs mismo día semana pasada durante 2h
   - Acción: Revisar estrategia de precios

### Alertas Informativas

1. **HighValueReservation**
   - Condición: Reserva > €2000
   - Acción: Considerar atención VIP

2. **FullOccupancy**
   - Condición: Ocupación ≥ 95%
   - Acción: Preparar servicios adicionales

---

## Dashboard Grafana

### Paneles Principales

**Fila 1 - KPIs Principales:**
- Reservas Confirmadas (24h)
- Revenue Diario
- Ocupación Actual (gauge)
- RevPAR

**Fila 2 - Distribuciones:**
- Reservas por Estado (pie chart)
- Revenue por Tipo de Habitación (time series)
- Habitaciones Disponibles (bar gauge)

**Fila 3 - Calidad del Servicio:**
- Tasa de Fallos en Reservas (con alertas)
- Satisfacción del Huésped (promedio móvil 1h)

**Fila 4 - Conversaciones:**
- Duración de Conversaciones (P50, P95, P99)
- Mensajes por Canal (24h)
- Intents Más Frecuentes (top 5)

**Fila 5 - Operaciones:**
- Lead Time Promedio
- Noches Promedio por Reserva
- Tasa de Cancelaciones
- Fallbacks del NLP

**Fila 6 - Trends:**
- Conversaciones Activas (time series)
- ADR Trend (7 días)

### Importar Dashboard

```bash
# Copiar dashboard a volumen de Grafana
cp docker/grafana/dashboards/business_metrics.json /path/to/grafana/provisioning/dashboards/

# O importar manualmente en Grafana UI:
# Dashboard → Import → Copiar JSON desde business_metrics.json
```

---

## Queries PromQL Útiles

### Revenue Total (24h)
```promql
sum(increase(hotel_reservation_value_euros_sum[24h]))
```

### Tasa de Conversión Global
```promql
rate(hotel_reservations_total{status="confirmed"}[1h]) 
/ 
rate(hotel_reservations_total[1h])
```

### Top 3 Canales por Mensajes
```promql
topk(3, sum by (channel) (increase(hotel_messages_by_channel_total[24h])))
```

### Tiempo de Respuesta P95 por Canal
```promql
histogram_quantile(0.95, 
  sum by (channel, le) (rate(hotel_response_time_by_channel_seconds_bucket[10m]))
)
```

### Ocupación Trend (7 días)
```promql
avg_over_time(hotel_occupancy_rate[7d])
```

### Reservas por Hora del Día (heatmap)
```promql
sum by (hour) (
  increase(hotel_reservations_total{status="confirmed"}[1h])
)
```

---

## Integración con Código

### En `orchestrator.py`

```python
from .business_metrics import (
    intents_detected,
    nlp_fallbacks,
    messages_by_channel,
    active_conversations
)

# Al recibir mensaje:
messages_by_channel.labels(channel=message.canal).inc()

# Al detectar intent:
confidence_level = "high" if confidence >= 0.75 else "medium" if confidence >= 0.45 else "low"
intents_detected.labels(intent=intent_name, confidence_level=confidence_level).inc()

# Al detectar fallback:
nlp_fallbacks.inc()
```

### En `pms_adapter.py`

```python
from .business_metrics import record_reservation, failed_reservations

# Al confirmar reserva:
record_reservation(
    status="confirmed",
    channel=channel,
    room_type=room_type,
    value=price_per_night * nights,
    nights=nights,
    lead_time_days=lead_time_days
)

# Al fallar reserva:
failed_reservations.labels(reason=failure_reason).inc()
record_reservation(
    status="failed",
    channel=channel,
    room_type=room_type,
    value=0,
    nights=0,
    lead_time_days=0
)
```

---

## Roadmap de Métricas

### Fase 1 ✅ (Completado)
- Métricas básicas de reservas
- Intents y NLP
- Canales y conversaciones
- Dashboard Grafana básico

### Fase 2 🚧 (Próximo)
- Métricas de satisfacción (encuestas post-estancia)
- Integración con sistema de encuestas
- Recording rules para agregaciones complejas

### Fase 3 📋 (Futuro)
- Métricas de up-selling/cross-selling
- Customer Lifetime Value (CLV)
- Churn prediction metrics
- A/B testing metrics

---

## Mejores Prácticas

1. **Actualización de Métricas Operacionales**
   - Usar cronjob o background task cada 1-6 horas
   - No actualizar en hot-path de requests

2. **Manejo de Errores**
   - Siempre wrappear registro de métricas en try-except
   - Loggear warning si falla, no bloquear operación

3. **Cardinalidad**
   - Evitar labels de alta cardinalidad (user_id, reservation_id)
   - Usar labels categóricos (channel, status, room_type)

4. **Testing**
   - Verificar que métricas se registran en tests de integración
   - Mock `business_metrics` en tests unitarios

---

## Soporte y Troubleshooting

### No veo métricas en Grafana

1. Verificar que Prometheus está scrapeando `/metrics`:
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

2. Verificar que métricas existen:
   ```bash
   curl http://localhost:8000/metrics | grep hotel_
   ```

3. Verificar alertas en Prometheus:
   ```bash
   curl http://localhost:9090/api/v1/alerts
   ```

### Métricas no se actualizan

1. Verificar logs del servicio:
   ```bash
   docker logs agente-api --tail=100 | grep business_metrics
   ```

2. Verificar que funciones helper se llaman:
   ```python
   # En pms_adapter.py
   logger.info(f"Recording business reservation: {status}, {channel}, {room_type}")
   ```

---

## Referencias

- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)
- [Hotel KPIs & Metrics](https://www.revinate.com/blog/hotel-kpis/)
- [RevPAR vs ADR](https://www.hospitalitynet.org/opinion/4079841.html)

---

**Última actualización:** 2025-10-05  
**Autor:** Sistema Agente Hotelero IA  
**Versión:** 1.0.0
