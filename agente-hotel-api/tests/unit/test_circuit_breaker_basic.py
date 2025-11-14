import pytest
from app.core.circuit_breaker import CircuitBreaker, CircuitState

class DummyError(Exception):
    pass

@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold():
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1, expected_exception=DummyError)

    async def failing_call():
        raise DummyError("boom")

    # 3 fallos disparan estado OPEN
    for _ in range(3):
        with pytest.raises(DummyError):
            await breaker.call(failing_call)
    assert breaker.state == CircuitState.OPEN

@pytest.mark.asyncio
async def test_circuit_breaker_half_open_and_reset():
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0, expected_exception=DummyError)

    async def failing_call():
        raise DummyError("boom")

    async def success_call():
        return "ok"

    # Producir apertura
    for _ in range(2):
        with pytest.raises(DummyError):
            await breaker.call(failing_call)
    assert breaker.state == CircuitState.OPEN

    # Forzar intento de reset (recovery_timeout=0)
    # La primera llamada tras timeout pasa a HALF_OPEN y como es exitosa vuelve a CLOSED
    result = await breaker.call(success_call)
    assert result == "ok"
    assert breaker.state == CircuitState.CLOSED

@pytest.mark.asyncio
async def test_circuit_breaker_raises_open_error_before_recovery():
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=5, expected_exception=DummyError)

    async def failing_call():
        raise DummyError("boom")

    with pytest.raises(DummyError):
        await breaker.call(failing_call)
    assert breaker.state == CircuitState.OPEN

    # Intento inmediato debe lanzar CircuitBreakerOpenError
    from app.exceptions.pms_exceptions import CircuitBreakerOpenError
    with pytest.raises(CircuitBreakerOpenError):
        await breaker.call(failing_call)
