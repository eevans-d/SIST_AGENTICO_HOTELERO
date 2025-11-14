import pytest
import httpx
from unittest.mock import patch

from app.core.retry import retry_with_backoff

pytestmark = pytest.mark.asyncio


async def test_retry_function_call_success_after_retries():
    attempts = {"count": 0}

    async def fragile():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise httpx.TimeoutException("timeout")
        return "ok"

    with patch("asyncio.sleep", return_value=None):  # evitar esperas reales
        result = await retry_with_backoff(
            fragile,
            max_attempts=3,
            backoff_sequence=[0, 0, 0],
            retriable_exceptions=(httpx.TimeoutException,),
            operation_label="test_op",
        )
    assert result == "ok"
    assert attempts["count"] == 3


async def test_retry_decorator_style():
    attempts = {"count": 0}

    @retry_with_backoff(max_attempts=2, backoff_sequence=[0, 0], retriable_exceptions=(httpx.TimeoutException,))
    async def sometimes():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise httpx.TimeoutException("first fail")
        return 42

    with patch("asyncio.sleep", return_value=None):
        result = await sometimes()
    assert result == 42
    assert attempts["count"] == 2


async def test_retry_exhaustion():
    async def always_fail():
        raise httpx.TimeoutException("always")

    with patch("asyncio.sleep", return_value=None):
        with pytest.raises(httpx.TimeoutException):
            await retry_with_backoff(
                always_fail,
                max_attempts=2,
                backoff_sequence=[0, 0],
                retriable_exceptions=(httpx.TimeoutException,),
                operation_label="exhaust_op",
            )


async def test_retry_base_delay_generates_sequence():
    # Usamos base_delay para verificar generación automática de secuencia exponencial truncada a int
    seq_results = []
    attempts = {"count": 0}

    async def fail_once():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise httpx.TimeoutException("first")
        return "done"

    # base_delay=0.5 -> secuencia esperada [0,1,2]
    with patch("asyncio.sleep", side_effect=lambda s: seq_results.append(s)):
        result = await retry_with_backoff(
            fail_once,
            max_attempts=3,
            base_delay=0.5,
            retriable_exceptions=(httpx.TimeoutException,),
            operation_label="base_delay_op",
        )
    assert result == "done"
    # Debe haber registrado exactamente el primer tiempo de espera 0 (porque falla una vez)
    assert seq_results == [0]
