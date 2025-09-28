import httpx
import pytest

from app.core.circuit_breaker import CircuitBreaker, pms_circuit_breaker_calls_total, pms_circuit_breaker_failure_streak


@pytest.mark.asyncio
async def test_circuit_breaker_success_resets_streak():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1, expected_exception=httpx.HTTPError)

    async def ok():
        return 42

    # Inducir una falla previa para incrementar racha
    async def fail():
        raise httpx.HTTPError("boom")

    with pytest.raises(httpx.HTTPError):
        await cb.call(fail)
    assert pms_circuit_breaker_failure_streak._value.get() == 1

    # Llamada exitosa resetea
    result = await cb.call(ok)
    assert result == 42
    assert pms_circuit_breaker_failure_streak._value.get() == 0


@pytest.mark.asyncio
async def test_circuit_breaker_calls_metrics_labelled():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1, expected_exception=httpx.HTTPError)

    async def fail():
        raise httpx.HTTPError("boom")

    async def ok():
        return "ok"

    # 1 fallo
    with pytest.raises(httpx.HTTPError):
        await cb.call(fail)
    # 1 éxito
    assert await cb.call(ok) == "ok"

    # Inspeccionar métricas internas del counter (estructura internal de prometheus_client)
    internal = getattr(pms_circuit_breaker_calls_total, '_metrics')
    labels_seen = set()
    for k in internal.keys():  # k es tupla de label values en orden definido
        # Orden de labels: state, result
        labels_seen.add(k)
    assert ('CLOSED', 'failure') in labels_seen
    assert ('CLOSED', 'success') in labels_seen


@pytest.mark.asyncio
async def test_circuit_breaker_open_after_threshold():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1, expected_exception=httpx.HTTPError)

    async def fail():
        raise httpx.HTTPError("boom")

    # Dos fallos -> abre
    with pytest.raises(httpx.HTTPError):
        await cb.call(fail)
    with pytest.raises(httpx.HTTPError):
        await cb.call(fail)

    # Tercer intento inmediato debe lanzar CircuitBreakerOpenError
    from app.exceptions.pms_exceptions import CircuitBreakerOpenError
    with pytest.raises(CircuitBreakerOpenError):
        await cb.call(fail)
