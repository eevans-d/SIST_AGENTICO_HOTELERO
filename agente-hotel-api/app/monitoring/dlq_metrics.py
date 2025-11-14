"""
Dead Letter Queue (DLQ) Prometheus Metrics.

Métricas para monitorear el estado y performance del DLQ system.
"""

from prometheus_client import Counter, Gauge, Histogram

# Total de mensajes encolados en DLQ por razón de fallo
dlq_messages_total = Counter(
    "dlq_messages_total",
    "Total number of messages enqueued to DLQ",
    ["reason"],  # error_type, pms_timeout, nlp_failure, etc.
)

# Total de reintentos ejecutados
dlq_retries_total = Counter(
    "dlq_retries_total",
    "Total number of retry attempts from DLQ",
    ["result"],  # success, failure, max_retries_exceeded
)

# Total de fallos permanentes (movidos a DB)
dlq_permanent_failures_total = Counter(
    "dlq_permanent_failures_total",
    "Total number of permanent failures (max retries exceeded)",
    ["reason"],
)

# Latencia de procesamiento de retry
dlq_retry_latency_seconds = Histogram(
    "dlq_retry_latency_seconds",
    "Time taken to process a retry from DLQ",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# Tamaño actual de la cola DLQ
dlq_queue_size = Gauge(
    "dlq_queue_size",
    "Current number of messages in DLQ awaiting retry",
)

# Edad del mensaje más antiguo en DLQ (segundos)
dlq_oldest_message_age_seconds = Gauge(
    "dlq_oldest_message_age_seconds",
    "Age of the oldest message in DLQ in seconds",
)

# Total de mensajes expirados por TTL
dlq_messages_expired_total = Counter(
    "dlq_messages_expired_total",
    "Total number of messages expired due to TTL",
)
