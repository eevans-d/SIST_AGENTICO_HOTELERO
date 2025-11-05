"""
Business Metrics for Hotel Operations
Métricas de negocio específicas del dominio hotelero
"""

from prometheus_client import Counter, Histogram, Gauge

# ============================================================================
# MÉTRICAS DE RESERVAS
# ============================================================================

# Contador de reservas totales por estado y canal
reservations_total = Counter(
    "hotel_reservations_total", "Total de reservas creadas", ["status", "channel", "room_type"]
)

# Histograma del valor de las reservas
reservation_value = Histogram(
    "hotel_reservation_value_euros",
    "Valor de la reserva en euros",
    buckets=[50, 100, 200, 500, 1000, 2000, 5000, 10000],
)

# Duración de estadía (noches)
reservation_nights = Histogram(
    "hotel_reservation_nights", "Número de noches por reserva", buckets=[1, 2, 3, 5, 7, 10, 14, 21, 30]
)

# Lead time (días entre reserva y check-in)
reservation_lead_time = Histogram(
    "hotel_reservation_lead_time_days", "Días entre reserva y check-in", buckets=[0, 1, 3, 7, 14, 30, 60, 90, 180]
)

# ============================================================================
# MÉTRICAS DE CONVERSACIÓN
# ============================================================================

# Gauge de conversaciones activas
active_conversations = Gauge("hotel_active_conversations", "Número de conversaciones activas con huéspedes")

# Duración de conversaciones
conversation_duration = Histogram(
    "hotel_conversation_duration_seconds",
    "Duración de conversaciones con huéspedes",
    buckets=[30, 60, 120, 300, 600, 1200, 1800],
)

# Mensajes por conversación
messages_per_conversation = Histogram(
    "hotel_messages_per_conversation", "Número de mensajes en una conversación", buckets=[1, 2, 5, 10, 15, 20, 30, 50]
)

# ============================================================================
# MÉTRICAS DE SATISFACCIÓN
# ============================================================================

# Satisfacción del huésped (escala 1-5)
guest_satisfaction = Histogram(
    "hotel_guest_satisfaction_score", "Puntuación de satisfacción del huésped (1-5)", buckets=[1, 2, 3, 4, 5]
)

# Net Promoter Score (NPS)
guest_nps = Histogram("hotel_guest_nps_score", "Net Promoter Score (-100 a 100)", buckets=list(range(-100, 101, 20)))

# ============================================================================
# MÉTRICAS DE OPERACIONES
# ============================================================================

# Tasa de ocupación (gauge actualizado periódicamente)
occupancy_rate = Gauge("hotel_occupancy_rate", "Tasa de ocupación del hotel (%)")

# Habitaciones disponibles
available_rooms = Gauge("hotel_available_rooms", "Número de habitaciones disponibles", ["room_type"])

# Revenue diario
daily_revenue = Gauge("hotel_daily_revenue_euros", "Revenue diario en euros")

# ADR (Average Daily Rate)
average_daily_rate = Gauge("hotel_adr_euros", "Precio promedio por habitación/noche")

# RevPAR (Revenue Per Available Room)
revpar = Gauge("hotel_revpar_euros", "Revenue por habitación disponible")

# ============================================================================
# MÉTRICAS DE INTENTS/NLP
# ============================================================================

# Intents detectados
intents_detected = Counter(
    "hotel_intents_detected_total",
    "Intents detectados por el NLP",
    ["intent", "confidence_level"],  # confidence_level: high/medium/low
)

# Fallbacks del NLP
nlp_fallbacks = Counter("hotel_nlp_fallbacks_total", "Casos donde el NLP no pudo determinar el intent")

# ============================================================================
# MÉTRICAS DE CANALES
# ============================================================================

# Mensajes por canal
messages_by_channel = Counter(
    "hotel_messages_by_channel_total",
    "Mensajes recibidos por canal",
    ["channel"],  # whatsapp, gmail, web, etc.
)

# Tiempo de respuesta por canal
response_time_by_channel = Histogram(
    "hotel_response_time_by_channel_seconds",
    "Tiempo de respuesta por canal",
    ["channel"],
    buckets=[1, 2, 5, 10, 30, 60, 120, 300],
)

# ============================================================================
# MÉTRICAS DE ERRORES DE NEGOCIO
# ============================================================================

# Reservas fallidas
# Nota de compatibilidad con tests:
# - Algunas pruebas acceden a failed_reservations._value.get() y llaman
#   failed_reservations.inc() sin labels. Para soportar ambos usos y mantener
#   el diseño con labels en producción, exponemos un wrapper ligero que:
#   * mantiene un contador interno para ._value.get() (solo para inc() sin labels)
#   * delega .labels(...) al Counter real con label "reason"
class _SimpleValue:
    def __init__(self):
        self._v = 0

    def get(self):
        return self._v

    def add(self, n: float):
        self._v += n


class _CounterWithDefaultAndTestValue:
    def __init__(self, prom_counter: Counter, default_labels: dict | None = None):
        self._counter = prom_counter
        self._default_labels = default_labels or {"reason": "unspecified"}
        # Expuesto para compatibilidad con tests: failed_reservations._value.get()
        self._value = _SimpleValue()

    def labels(self, **kwargs):
        return self._counter.labels(**kwargs)

    def inc(self, amount: float = 1.0):
        # Soporta incremento sin labels (tests) usando labels por defecto
        try:
            self._counter.labels(**self._default_labels).inc(amount)
        finally:
            # Actualiza contador de compatibilidad usado por tests
            self._value.add(amount)


_failed_reservations_counter = Counter(
    "hotel_failed_reservations_total",
    "Reservas que fallaron",
    ["reason"],  # payment_failed, no_availability, validation_error, etc.
)

failed_reservations = _CounterWithDefaultAndTestValue(_failed_reservations_counter)

# Cancelaciones
cancellations = Counter(
    "hotel_cancellations_total",
    "Reservas canceladas",
    ["cancellation_type"],  # guest_initiated, hotel_initiated, no_show
)

# ============================================================================
# FUNCIONES HELPER PARA ACTUALIZAR MÉTRICAS
# ============================================================================


def record_reservation(status: str, channel: str, room_type: str, value: float, nights: int, lead_time_days: int):
    """
    Registra una reserva con todas sus métricas asociadas.

    Args:
        status: confirmed, pending, failed
        channel: whatsapp, gmail, web
        room_type: deluxe, standard, suite
        value: Valor total en euros
        nights: Número de noches
        lead_time_days: Días entre reserva y check-in
    """
    reservations_total.labels(status=status, channel=channel, room_type=room_type).inc()

    if status == "confirmed":
        reservation_value.observe(value)
        reservation_nights.observe(nights)
        reservation_lead_time.observe(lead_time_days)


def record_conversation_metrics(duration_seconds: float, message_count: int, satisfaction_score: int | None = None):
    """
    Registra métricas de una conversación completada.

    Args:
        duration_seconds: Duración total de la conversación
        message_count: Número de mensajes intercambiados
        satisfaction_score: Puntuación de satisfacción (1-5), opcional
    """
    conversation_duration.observe(duration_seconds)
    messages_per_conversation.observe(message_count)

    if satisfaction_score is not None:
        guest_satisfaction.observe(satisfaction_score)


def update_operational_metrics(current_occupancy: float, rooms_available: dict, daily_rev: float, adr: float):
    """
    Actualiza métricas operacionales del hotel.

    Args:
        current_occupancy: Tasa de ocupación actual (0-100)
        rooms_available: Dict {room_type: count}
        daily_rev: Revenue del día actual
        adr: Average Daily Rate
    """
    occupancy_rate.set(current_occupancy)
    daily_revenue.set(daily_rev)
    average_daily_rate.set(adr)

    # RevPAR = ADR * Occupancy Rate
    revpar.set(adr * (current_occupancy / 100))

    # Actualizar habitaciones disponibles por tipo
    for room_type, count in rooms_available.items():
        available_rooms.labels(room_type=room_type).set(count)


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

"""
# En el código del orchestrator o PMS adapter:

from app.services.business_metrics import record_reservation, record_conversation_metrics

# Al confirmar una reserva:
record_reservation(
    status="confirmed",
    channel="whatsapp",
    room_type="deluxe",
    value=450.00,
    nights=3,
    lead_time_days=15
)

# Al finalizar una conversación:
record_conversation_metrics(
    duration_seconds=245,
    message_count=12,
    satisfaction_score=5
)

# Actualización periódica (cronjob o background task):
update_operational_metrics(
    current_occupancy=75.5,
    rooms_available={"standard": 5, "deluxe": 2, "suite": 1},
    daily_rev=12500.00,
    adr=165.50
)
"""
