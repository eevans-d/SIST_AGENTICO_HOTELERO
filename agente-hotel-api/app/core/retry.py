# [PROMPT GA-03] app/core/retry.py

import asyncio
import httpx
from .logging import logger


async def retry_with_backoff(
    func, max_attempts=3, backoff_sequence=[1, 2, 4], retriable_exceptions=(httpx.TimeoutException, httpx.ConnectError)
):
    """
    Ejecuta función con reintentos y backoff exponencial
    Secuencia por defecto: 1s, 2s, 4s
    """
    last_exception = None

    for attempt in range(max_attempts):
        try:
            return await func()
        except retriable_exceptions as e:
            last_exception = e
            if attempt < max_attempts - 1:
                wait_time = backoff_sequence[min(attempt, len(backoff_sequence) - 1)]
                logger.warning(f"Attempt {attempt + 1} failed: {e}. " f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"All {max_attempts} attempts failed")

    raise last_exception
