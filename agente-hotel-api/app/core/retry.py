"""
[PROMPT GA-03] app/core/retry.py

Retry utilities supporting both decorator and function-call styles.

Usage:
  # Function-call style (existing code)
  await retry_with_backoff(fetch_fn, operation_label="check_availability")

  # Decorator style (compatibility for legacy code)
  @retry_with_backoff(max_retries=3)
  async def fragile_op(...):
      ...
"""

import asyncio
import httpx
from prometheus_client import Counter
from .logging import logger

# Métricas de reintentos
retry_attempts = Counter(
    "retry_attempts_total",
    "Total de reintentos ejecutados",
    labelnames=["operation", "exception"],
)


def retry_with_backoff(
    func=None,
    *,
    max_attempts: int = 3,
    max_retries: int | None = None,
    backoff_sequence: list[int] | None = None,
    base_delay: float | None = None,
    retriable_exceptions=(httpx.TimeoutException, httpx.ConnectError),
    operation_label: str | None = None,
):
    """Dual-mode retry helper.

    - If called with a callable as first argument, returns an awaitable that executes the callable with retries.
    - If called with only keyword arguments, returns a decorator to wrap an async function.

    Compatibility:
      - Accepts max_retries as alias of max_attempts
      - Accepts base_delay to generate an exponential backoff sequence if backoff_sequence is not provided
    """

    # Normalize parameters
    if max_retries is not None and max_attempts == 3:
        max_attempts = max_retries

    if backoff_sequence is None:
        if base_delay is not None:
            # simple exponential backoff sequence of 3 steps
            backoff_sequence = [int(base_delay * (2**i)) for i in range(3)]
        else:
            backoff_sequence = [1, 2, 4]

    async def _run(call):
        last_exception = None
        for attempt in range(max_attempts):
            try:
                return await call()
            except retriable_exceptions as e:
                last_exception = e
                if attempt < max_attempts - 1:
                    wait_time = backoff_sequence[min(attempt, len(backoff_sequence) - 1)]
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time} seconds..."
                    )
                    retry_attempts.labels(
                        operation=operation_label or "unknown", exception=e.__class__.__name__
                    ).inc()
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All {max_attempts} attempts failed")

        if last_exception is None:
            raise httpx.HTTPError("Operation failed without specific exception")
        raise last_exception

    # Function-call style: retry_with_backoff(func, ...)
    if callable(func):
        return _run(func)

    # Decorator style: @retry_with_backoff(...)
    def _decorator(target_func):
        async def _wrapped(*args, **kwargs):
            async def call():
                return await target_func(*args, **kwargs)

            # If operation_label not set, use function name
            label = operation_label or getattr(target_func, "__name__", "unknown")
            return await retry_with_backoff(call, max_attempts=max_attempts, backoff_sequence=backoff_sequence, retriable_exceptions=retriable_exceptions, operation_label=label)

        return _wrapped

    return _decorator
