# [PROMPT GA-03] app/core/retry.py

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


async def retry_with_backoff(
    func,
    max_attempts=3,
    backoff_sequence=[1, 2, 4],
    retriable_exceptions=(httpx.TimeoutException, httpx.ConnectError),
    operation_label: str | None = None,
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
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time} seconds...")
                # Registrar métrica de reintento
                retry_attempts.labels(operation=operation_label or "unknown", exception=e.__class__.__name__).inc()
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"All {max_attempts} attempts failed")

    # Seguridad: si por alguna razón no se capturó una excepción específica, lanzar una genérica
    if last_exception is None:
        raise httpx.HTTPError("Operation failed without specific exception")
    raise last_exception
