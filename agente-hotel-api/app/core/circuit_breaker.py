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
    def __init__(self, failure_threshold=5, recovery_timeout=30, expected_exception=Exception, service_name="unknown"):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.service_name = service_name
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.last_error = None
        self.success_count_in_half_open = 0
        self.required_successes_to_close = 3  # Require 3 successes before closing

    async def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.success_count_in_half_open = 0
                logger.info(
                    "Circuit breaker transitioning to HALF_OPEN",
                    service=self.service_name,
                    failure_count=self.failure_count,
                    recovery_timeout=self.recovery_timeout,
                )
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN for {self.service_name}",
                    service_name=self.service_name,
                    failure_count=self.failure_count,
                    recovery_timeout=self.recovery_timeout,
                )

        pre_state = self.state.value
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            pms_circuit_breaker_calls_total.labels(state=pre_state, result="success").inc()
            return result
        except self.expected_exception as e:
            self.last_error = str(e)
            self._on_failure()
            pms_circuit_breaker_calls_total.labels(state=pre_state, result="failure").inc()
            raise
        except Exception as e:
            # Unexpected exceptions should also be tracked but not necessarily trip the breaker
            logger.error(
                "Unexpected exception in circuit breaker",
                service=self.service_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            pms_circuit_breaker_calls_total.labels(state=pre_state, result="unexpected_error").inc()
            raise

    def _should_attempt_reset(self):
        return self.last_failure_time and (datetime.now() - self.last_failure_time) > timedelta(
            seconds=self.recovery_timeout
        )

    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.success_count_in_half_open += 1
            if self.success_count_in_half_open >= self.required_successes_to_close:
                logger.info(
                    "Circuit breaker reset and closed after sufficient successes",
                    service=self.service_name,
                    success_count=self.success_count_in_half_open,
                    previous_failure_count=self.failure_count,
                )
                self.failure_count = 0
                self.state = CircuitState.CLOSED
                self.last_error = None
                pms_circuit_breaker_failure_streak.set(0)
        elif self.state == CircuitState.CLOSED:
            # Reset any partial failures
            if self.failure_count > 0:
                logger.debug(
                    "Circuit breaker success - resetting failure count",
                    service=self.service_name,
                    previous_failures=self.failure_count,
                )
                self.failure_count = 0
                pms_circuit_breaker_failure_streak.set(0)

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        pms_circuit_breaker_failure_streak.set(self.failure_count)

        if self.state == CircuitState.HALF_OPEN:
            # Immediate transition back to OPEN on any failure in HALF_OPEN
            self.state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker reopened from HALF_OPEN state",
                service=self.service_name,
                failure_count=self.failure_count,
                last_error=self.last_error,
            )
        elif self.failure_count >= self.failure_threshold and self.state != CircuitState.OPEN:
            self.state = CircuitState.OPEN
            logger.error(
                "Circuit breaker opened due to failure threshold reached",
                service=self.service_name,
                failure_count=self.failure_count,
                threshold=self.failure_threshold,
                last_error=self.last_error,
            )

    def get_state_info(self) -> dict:
        """Get current state information for monitoring/debugging."""
        return {
            "state": self.state.value,
            "service_name": self.service_name,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_error": self.last_error,
            "success_count_in_half_open": self.success_count_in_half_open
            if self.state == CircuitState.HALF_OPEN
            else None,
        }
