# [PROMPT 3.5] app/services/alert_manager.py (Refinado + Robustez)

import asyncio
import time
from typing import Dict, Optional, Union
from ..core.logging import logger
from ..core.constants import (
    HTTP_TIMEOUT_DEFAULT,
    MAX_RETRIES_DEFAULT,
    RETRY_DELAY_BASE,
)
# import aiosmtplib
# import httpx


class AlertManager:
    """
    Gestor de alertas del sistema con cooldown, timeout y retry logic.

    Maneja el envío de alertas críticas a través de múltiples canales
    (email, SMS, Slack) con protección contra spam mediante cooldown.

    Attributes:
        alert_cooldown (dict): Cache de alertas recientes para prevenir spam
        cooldown_seconds (int): Tiempo de cooldown entre alertas duplicadas (default: 1800s = 30min)
        timeout_seconds (float): Timeout para operaciones de envío de alertas
    """

    def __init__(self, cooldown_seconds: int = 1800, timeout_seconds: float = HTTP_TIMEOUT_DEFAULT):
        """
        Inicializa el gestor de alertas.

        Args:
            cooldown_seconds: Tiempo mínimo entre alertas duplicadas (default: 1800s)
            timeout_seconds: Timeout para operaciones de alerta (default: 30s)
        """
        # Usamos time.monotonic() (float) para evitar problemas si el reloj del sistema
        # cambia (NTP adjustments, leap seconds) y reducir flakiness en tests de cooldown.
        # El dict guarda timestamps monotónicos (float seconds).
        self.alert_cooldown: Dict[str, float] = {}
        self.cooldown_seconds = cooldown_seconds
        self.timeout_seconds = timeout_seconds
        logger.info("alert_manager.initialized", cooldown_seconds=cooldown_seconds, timeout_seconds=timeout_seconds)

    async def send_alert(self, violation: dict) -> bool:
        """
        Envía alerta con timeout, retry y cooldown protection.

        Args:
            violation: Diccionario con información de la alerta:
                - metric: Métrica que generó la alerta
                - type: Tipo de alerta (alternativa a metric)
                - level: Nivel de severidad (info, warning, critical)
                - description: Descripción del problema
                - context: Contexto adicional

        Returns:
            bool: True si la alerta se envió exitosamente, False en caso contrario

        Raises:
            asyncio.TimeoutError: Si el envío excede el timeout (capturada internamente)
        """
        # Generate alert key based on type/metric and level
        # Prioritize 'type' field for backward compatibility with tests
        alert_type = violation.get("type") or violation.get("metric", "unknown")
        alert_level = violation.get("level", "unknown")
        alert_key = f"{alert_type}:{alert_level}"

        # Check cooldown to prevent alert spam
        if self._is_in_cooldown(alert_key):
            logger.debug(
                "alert_manager.cooldown_active",
                alert_key=alert_key,
                remaining_seconds=self._get_cooldown_remaining(alert_key),
            )
            return False

        # Retry logic with exponential backoff (only for non-timeout errors)
        for attempt in range(MAX_RETRIES_DEFAULT):
            try:
                # Send alert with timeout protection
                result = await asyncio.wait_for(self._send_alert_internal(violation), timeout=self.timeout_seconds)

                # Update cooldown cache only if send was successful
                if result:
                    self.alert_cooldown[alert_key] = time.monotonic()

                logger.info(
                    "alert_manager.alert_sent",
                    alert_key=alert_key,
                    level=violation.get("level"),
                    metric=violation.get("metric"),
                    type=violation.get("type"),
                    success=result,
                    attempt=attempt + 1,
                )

                return result

            except asyncio.TimeoutError:
                # Timeout is a hard limit - do NOT retry
                logger.error(
                    "alert_manager.timeout",
                    alert_key=alert_key,
                    timeout_seconds=self.timeout_seconds,
                    metric=violation.get("metric"),
                )
                return False

            except Exception as e:
                logger.error(
                    "alert_manager.send_failed",
                    alert_key=alert_key,
                    error=str(e),
                    error_type=type(e).__name__,
                    metric=violation.get("metric"),
                    attempt=attempt + 1,
                )
                if attempt < MAX_RETRIES_DEFAULT - 1:
                    delay = RETRY_DELAY_BASE * (2**attempt)
                    logger.warning(
                        "alert_manager.retry_after_error",
                        attempt=attempt + 1,
                        max_retries=MAX_RETRIES_DEFAULT,
                        retry_delay=delay,
                        error=str(e),
                    )
                    await asyncio.sleep(delay)
                else:
                    return False

        return False

    async def _send_alert_internal(self, violation: dict) -> bool:
        """
        Lógica interna de envío de alertas (sin retry - manejado por send_alert).

        Args:
            violation: Diccionario con información de la alerta

        Returns:
            bool: True si se envió exitosamente

        Raises:
            Exception: Si falla el envío (será capturado por send_alert para retry)
        """
        # TODO: Implementar envío real por email/SMS/Slack
        # await self._send_to_email(violation)
        # await self._send_to_slack(violation)

        logger.info(
            "alert_manager.send_attempt",
            metric=violation.get("metric"),
            type=violation.get("type"),
            level=violation.get("level"),
        )

        # Simulated success for now
        return True

    def _is_in_cooldown(self, alert_key: str) -> bool:
        """
        Verifica si una alerta está en cooldown.

        Args:
            alert_key: Clave única de la alerta

        Returns:
            bool: True si está en cooldown, False si puede enviarse
        """
        last_sent = self.alert_cooldown.get(alert_key)
        if last_sent is None:
            return False
        elapsed = time.monotonic() - last_sent
        return elapsed < self.cooldown_seconds

    def _get_cooldown_remaining(self, alert_key: str) -> float:
        """
        Calcula segundos restantes de cooldown con precisión decimal.

        Args:
            alert_key: Clave única de la alerta

        Returns:
            float: Segundos restantes de cooldown (0.0 si no hay cooldown activo)
        """
        last_sent = self.alert_cooldown.get(alert_key)
        if last_sent is None:
            return 0.0
        elapsed = time.monotonic() - last_sent
        return max(0.0, self.cooldown_seconds - elapsed)

    def clear_cooldown(self, alert_key: Optional[str] = None):
        """
        Limpia el cooldown de alertas.

        Args:
            alert_key: Clave específica a limpiar, o None para limpiar todo
        """
        if alert_key:
            self.alert_cooldown.pop(alert_key, None)
            logger.info("alert_manager.cooldown_cleared", alert_key=alert_key)
        else:
            self.alert_cooldown.clear()
            logger.info("alert_manager.all_cooldowns_cleared")


# Global singleton instance
alert_manager = AlertManager()
