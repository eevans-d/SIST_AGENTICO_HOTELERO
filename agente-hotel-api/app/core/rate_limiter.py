# app/core/rate_limiter.py
# Rate limiter para llamadas al PMS (prevenir 429s)

import time
from collections import deque
from typing import Optional

from ..core.logging import logger


class SlidingWindowRateLimiter:
    """
    Rate limiter basado en sliding window.
    
    Útil para limitar requests al PMS y evitar 429 Too Many Requests.
    QloApps tiene límite de ~80 req/min según documentación.
    """

    def __init__(self, max_requests: int, window_seconds: int):
        """
        Args:
            max_requests: Cantidad máxima de requests permitidos en la ventana
            window_seconds: Tamaño de la ventana deslizante en segundos
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: deque[float] = deque()  # Timestamps de requests

    async def acquire(self, operation: str = "unknown") -> bool:
        """
        Intenta adquirir permiso para hacer request.
        
        Args:
            operation: Nombre de la operación (para logging)
            
        Returns:
            True si se permite el request, False si rate limit alcanzado
        """
        now = time.time()
        
        # Limpiar requests fuera de la ventana deslizante
        while self.requests and self.requests[0] < now - self.window_seconds:
            self.requests.popleft()
        
        # Verificar si hay espacio en la ventana
        if len(self.requests) >= self.max_requests:
            wait_time = self.requests[0] + self.window_seconds - now
            logger.warning(
                "rate_limit_reached",
                operation=operation,
                max_requests=self.max_requests,
                window_seconds=self.window_seconds,
                wait_time_seconds=wait_time,
            )
            return False
        
        # Registrar este request
        self.requests.append(now)
        return True

    async def wait_if_needed(self, operation: str = "unknown", max_wait: float = 5.0):
        """
        Espera hasta que el rate limiter permita el request.
        
        Args:
            operation: Nombre de la operación
            max_wait: Tiempo máximo de espera en segundos
            
        Raises:
            TimeoutError: Si max_wait es superado
        """
        import asyncio
        
        start = time.time()
        while not await self.acquire(operation):
            elapsed = time.time() - start
            if elapsed >= max_wait:
                raise TimeoutError(
                    f"Rate limit wait timeout after {max_wait}s for operation: {operation}"
                )
            # Esperar 100ms antes de reintentar
            await asyncio.sleep(0.1)
    
    def get_current_count(self) -> int:
        """Retorna cantidad de requests en la ventana actual."""
        now = time.time()
        # Limpiar requests expirados
        while self.requests and self.requests[0] < now - self.window_seconds:
            self.requests.popleft()
        return len(self.requests)
    
    def get_time_until_available(self) -> Optional[float]:
        """Retorna segundos hasta que esté disponible un slot, o None si ya disponible."""
        now = time.time()
        # Limpiar expirados
        while self.requests and self.requests[0] < now - self.window_seconds:
            self.requests.popleft()
        
        if len(self.requests) < self.max_requests:
            return None
        
        # Tiempo hasta que expire el request más viejo
        return self.requests[0] + self.window_seconds - now
