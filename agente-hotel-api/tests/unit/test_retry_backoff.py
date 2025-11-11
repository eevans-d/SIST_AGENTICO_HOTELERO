import pytest
import httpx

from app.core.retry import retry_with_backoff, retry_attempts


@pytest.mark.asyncio
async def test_retry_with_backoff_success_path():
    attempts = []

    async def flaky():
        attempts.append(len(attempts))
        # Fail first two then succeed
        if len(attempts) < 3:
            raise httpx.TimeoutException("timeout simulated")
        return "ok"

    result = await retry_with_backoff(flaky, max_attempts=5, operation_label="flaky_test")  # type: ignore[misc]
    assert result == "ok"
    # Should have recorded retry metrics for first two failures
    # Access internal counter value (prometheus_client) via _value
    metric_value = retry_attempts.labels(operation="flaky_test", exception="TimeoutException")._value.get()
    assert metric_value >= 2


@pytest.mark.asyncio
async def test_retry_with_backoff_failure_path():
    async def always_fail():
        raise httpx.ConnectError("conn fail")

    with pytest.raises(httpx.ConnectError):
        await retry_with_backoff(always_fail, max_attempts=3, operation_label="always_fail_test")  # type: ignore[misc]
    # Ensure metric increments
    metric_value = retry_attempts.labels(operation="always_fail_test", exception="ConnectError")._value.get()
    assert metric_value >= 2  # at least attempts-1


@pytest.mark.asyncio
async def test_retry_decorator_style():
    calls = []

    @retry_with_backoff(max_attempts=2, operation_label="decorator_op")  # type: ignore[misc]
    async def do_work(x):
        calls.append(x)
        if len(calls) == 1:
            raise httpx.TimeoutException("first")
        return x * 2

    result = await do_work(5)
    assert result == 10
    metric_value = retry_attempts.labels(operation="decorator_op", exception="TimeoutException")._value.get()
    assert metric_value >= 1
