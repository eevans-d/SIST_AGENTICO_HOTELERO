import asyncio
import pytest
from app.core.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerOpenError


@pytest.mark.asyncio
async def test_circuit_breaker_full_state_flow_success_path():
    """Verifica transición CLOSED -> OPEN -> HALF_OPEN -> CLOSED (éxito en HALF_OPEN).

    Estrategia:
    - Configuramos failure_threshold bajo (3) y recovery_timeout corto (0.1s) para test rápido.
    - Forzamos 3 fallos seguidos -> estado OPEN.
    - Esperamos > recovery_timeout -> próximo call entra HALF_OPEN.
    - HALF_OPEN con éxito debe cerrar (CLOSED) y resetear failure_count.
    """
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1, expected_exception=ValueError)

    async def failing():
        raise ValueError("forced failure")

    async def succeeding():
        return "ok"

    # CLOSED inicialmente
    assert breaker.state == CircuitState.CLOSED

    # Forzar 3 fallos -> OPEN
    for i in range(3):
        with pytest.raises(ValueError):
            await breaker.call(failing)
    assert breaker.state == CircuitState.OPEN, "Debe estar OPEN tras alcanzar el threshold de fallos"

    # Antes del timeout debe seguir OPEN y rechazar llamadas
    with pytest.raises(CircuitBreakerOpenError):
        await breaker.call(succeeding)

    # Esperar a que venza recovery_timeout
    await asyncio.sleep(0.15)

    # Próxima llamada debe intentar HALF_OPEN y si success volver a CLOSED
    result = await breaker.call(succeeding)
    assert result == "ok"
    assert breaker.state == CircuitState.CLOSED, "Debe cerrar tras éxito en HALF_OPEN"
    assert breaker.failure_count == 0, "failure_count debe resetearse tras éxito"


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_failure_returns_to_open():
    """Verifica que un fallo en estado HALF_OPEN reabre el breaker (OPEN)."""
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, expected_exception=ValueError)

    async def failing():
        raise ValueError("forced failure")

    # Dos fallos -> OPEN
    for _ in range(2):
        with pytest.raises(ValueError):
            await breaker.call(failing)
    assert breaker.state == CircuitState.OPEN

    # Esperar para HALF_OPEN
    await asyncio.sleep(0.12)

    # HALF_OPEN intento que falla -> vuelve a OPEN
    with pytest.raises(ValueError):
        await breaker.call(failing)
    assert breaker.state == CircuitState.OPEN, "Debe permanecer/reabrirse en OPEN tras fallo en HALF_OPEN"
