# [PROMPT GA-03] app/core/circuit_breaker.py

from datetime import datetime, timedelta
from enum import Enum

from prometheus_client import Counter, Gauge

from ..core.logging import logger
from ..exceptions.pms_exceptions import CircuitBreakerOpenError


class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


"""Circuit breaker simple con instrumentación Prometheus.

Métricas expuestas:
  - pms_circuit_breaker_calls_total{state, result}: Counter de llamadas envueltas
  - pms_circuit_breaker_failure_streak: Gauge con la racha actual de fallos consecutivos
  - pms_circuit_breaker_state (expuesta en el adaptador PMS): 0=closed,1=open,2=half-open

Nota: Se mantiene el nombre con prefijo pms_ porque actualmente sólo se usa para el PMS.
Si en el futuro se generaliza, considerar renombrar con un prefijo genérico y añadir label service.
"""


# Métricas Prometheus para el breaker
pms_circuit_breaker_calls_total = Counter(
    "pms_circuit_breaker_calls_total", "Total de llamadas envueltas por el Circuit Breaker PMS", ["state", "result"]
)
pms_circuit_breaker_failure_streak = Gauge(
    "pms_circuit_breaker_failure_streak", "Racha actual de fallos consecutivos antes de abrir el breaker"
)


class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=30, expected_exception=Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    async def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")

        pre_state = self.state.value
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            pms_circuit_breaker_calls_total.labels(state=pre_state, result="success").inc()
            return result
        except self.expected_exception:
            self._on_failure()
            pms_circuit_breaker_calls_total.labels(state=pre_state, result="failure").inc()
            raise

    def _should_attempt_reset(self):
        return self.last_failure_time and (datetime.now() - self.last_failure_time) > timedelta(
            seconds=self.recovery_timeout
        )

    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker reset and closed.")
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        # Reset racha de fallos
        pms_circuit_breaker_failure_streak.set(0)

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        # Actualizar racha de fallos
        pms_circuit_breaker_failure_streak.set(self.failure_count)
        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                self.state = CircuitState.OPEN
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")
