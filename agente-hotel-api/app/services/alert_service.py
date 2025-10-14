# [PROMPT 3.5] app/services/alert_manager.py (Refinado + Robustez)

import asyncio
from datetime import datetime
from typing import Dict, Optional
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
        self.alert_cooldown: Dict[str, datetime] = {}
        self.cooldown_seconds = cooldown_seconds
        self.timeout_seconds = timeout_seconds
        logger.info("alert_manager.initialized", cooldown_seconds=cooldown_seconds, timeout_seconds=timeout_seconds)

    async def send_alert(self, violation: dict) -> bool:
        """
        Envía alerta con timeout, retry y cooldown protection.

        Args:
            violation: Diccionario con información de la alerta:
                - metric: Métrica que generó la alerta
                - level: Nivel de severidad (info, warning, critical)
                - description: Descripción del problema
                - context: Contexto adicional

        Returns:
            bool: True si la alerta se envió exitosamente, False en caso contrario

        Raises:
            asyncio.TimeoutError: Si el envío excede el timeout (capturada internamente)
        """
        alert_key = f"{violation.get('metric', 'unknown')}:{violation.get('level', 'unknown')}"

        # Check cooldown to prevent alert spam
        if self._is_in_cooldown(alert_key):
            logger.debug(
                "alert_manager.cooldown_active",
                alert_key=alert_key,
                remaining_seconds=self._get_cooldown_remaining(alert_key),
            )
            return False

        try:
            # Send alert with timeout protection
            result = await asyncio.wait_for(self._send_alert_internal(violation), timeout=self.timeout_seconds)

            # Update cooldown cache
            self.alert_cooldown[alert_key] = datetime.now()

            logger.info(
                "alert_manager.alert_sent",
                alert_key=alert_key,
                level=violation.get("level"),
                metric=violation.get("metric"),
                success=result,
            )

            return result

        except asyncio.TimeoutError:
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
            )
            return False

    async def _send_alert_internal(self, violation: dict) -> bool:
        """
        Lógica interna de envío de alertas con retry automático.

        Args:
            violation: Diccionario con información de la alerta

        Returns:
            bool: True si se envió exitosamente
        """
        # Retry logic with exponential backoff
        for attempt in range(MAX_RETRIES_DEFAULT):
            try:
                # TODO: Implementar envío real por email/SMS/Slack
                # await self._send_to_email(violation)
                # await self._send_to_slack(violation)

                logger.info(
                    "alert_manager.send_attempt",
                    attempt=attempt + 1,
                    max_retries=MAX_RETRIES_DEFAULT,
                    metric=violation.get("metric"),
                    level=violation.get("level"),
                )

                # Simulated success for now
                return True

            except Exception as e:
                if attempt < MAX_RETRIES_DEFAULT - 1:
                    delay = RETRY_DELAY_BASE * (2**attempt)  # Exponential backoff
                    logger.warning(
                        "alert_manager.retry",
                        attempt=attempt + 1,
                        max_retries=MAX_RETRIES_DEFAULT,
                        retry_delay=delay,
                        error=str(e),
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("alert_manager.all_retries_failed", attempts=MAX_RETRIES_DEFAULT, error=str(e))
                    raise

        return False

    def _is_in_cooldown(self, alert_key: str) -> bool:
        """
        Verifica si una alerta está en cooldown.

        Args:
            alert_key: Clave única de la alerta

        Returns:
            bool: True si está en cooldown, False si puede enviarse
        """
        if alert_key not in self.alert_cooldown:
            return False

        last_sent = self.alert_cooldown[alert_key]
        elapsed = (datetime.now() - last_sent).total_seconds()
        return elapsed < self.cooldown_seconds

    def _get_cooldown_remaining(self, alert_key: str) -> int:
        """
        Calcula segundos restantes de cooldown.

        Args:
            alert_key: Clave única de la alerta

        Returns:
            int: Segundos restantes de cooldown
        """
        if alert_key not in self.alert_cooldown:
            return 0

        last_sent = self.alert_cooldown[alert_key]
        elapsed = (datetime.now() - last_sent).total_seconds()
        remaining = max(0, self.cooldown_seconds - elapsed)
        return int(remaining)

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
