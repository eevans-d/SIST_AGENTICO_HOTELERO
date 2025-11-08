import pytest

from app.core.circuit_breaker import CircuitBreaker, CircuitState
from app.exceptions.pms_exceptions import CircuitBreakerOpenError


@pytest.mark.unit
@pytest.mark.asyncio
async def test_circuit_breaker_opens_and_blocks_calls():
    # Configure breaker to open after 2 failures and keep OPEN for a while
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60, expected_exception=RuntimeError)

    async def failing():
        raise RuntimeError("boom")

    # Trip the breaker
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.call(failing)

    assert cb.state == CircuitState.OPEN

    # While OPEN and without recovery window, it should reject immediately
    with pytest.raises(CircuitBreakerOpenError):
        await cb.call(failing)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_circuit_breaker_half_open_and_recovers_on_success():
    # Immediate recovery timeout to transition to HALF_OPEN on next attempt
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0, expected_exception=RuntimeError)

    async def failing():
        raise RuntimeError("boom")

    async def success():
        return "ok"

    # First failure should open the breaker
    with pytest.raises(RuntimeError):
        await cb.call(failing)
    assert cb.state == CircuitState.OPEN

    # With recovery_timeout=0, next call attempts HALF_OPEN and succeeds -> CLOSES
    result = await cb.call(success)
    assert result == "ok"
    assert cb.state == CircuitState.CLOSED
