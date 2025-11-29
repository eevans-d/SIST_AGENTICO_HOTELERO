# [PROMPT 3.5] app/services/alert_manager.py (Refinado + Robustez + Envío Real)

import asyncio
import time
from typing import Dict, Optional, List
from ..core.logging import logger
from ..core.settings import settings
from ..core.constants import (
    HTTP_TIMEOUT_DEFAULT,
    MAX_RETRIES_DEFAULT,
    RETRY_DELAY_BASE,
)

# Importaciones opcionales para envío real
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


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
        self.alert_cooldown: Dict[str, float] = {}
        self.cooldown_seconds = cooldown_seconds
        self.timeout_seconds = timeout_seconds
        
        # Configuración de canales de alerta
        self._email_enabled = self._check_email_config()
        self._slack_enabled = self._check_slack_config()
        
        logger.info(
            "alert_manager.initialized",
            cooldown_seconds=cooldown_seconds,
            timeout_seconds=timeout_seconds,
            email_enabled=self._email_enabled,
            slack_enabled=self._slack_enabled,
        )

    def _check_email_config(self) -> bool:
        """Verifica si la configuración de email está disponible."""
        try:
            return bool(
                getattr(settings, "gmail_username", None)
                and getattr(settings, "gmail_app_password", None)
                and getattr(settings, "alert_email_recipients", None)
            )
        except Exception:
            return False

    def _check_slack_config(self) -> bool:
        """Verifica si la configuración de Slack está disponible."""
        try:
            webhook = getattr(settings, "slack_alert_webhook_url", None)
            return bool(webhook and str(webhook).startswith("http"))
        except Exception:
            return False

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
        """
        alert_type = violation.get("type") or violation.get("metric", "unknown")
        alert_level = violation.get("level", "unknown")
        alert_key = f"{alert_type}:{alert_level}"

        if self._is_in_cooldown(alert_key):
            logger.debug(
                "alert_manager.cooldown_active",
                alert_key=alert_key,
                remaining_seconds=self._get_cooldown_remaining(alert_key),
            )
            return False

        for attempt in range(MAX_RETRIES_DEFAULT):
            try:
                result = await asyncio.wait_for(
                    self._send_alert_internal(violation),
                    timeout=self.timeout_seconds
                )

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
                logger.error(
                    "alert_manager.timeout",
                    alert_key=alert_key,
                    timeout_seconds=self.timeout_seconds,
                )
                return False

            except Exception as e:
                logger.error(
                    "alert_manager.send_failed",
                    alert_key=alert_key,
                    error=str(e),
                    attempt=attempt + 1,
                )
                if attempt < MAX_RETRIES_DEFAULT - 1:
                    delay = RETRY_DELAY_BASE * (2**attempt)
                    await asyncio.sleep(delay)
                else:
                    return False

        return False

    async def _send_alert_internal(self, violation: dict) -> bool:
        """
        Lógica interna de envío de alertas a múltiples canales.

        Args:
            violation: Diccionario con información de la alerta

        Returns:
            bool: True si al menos un canal envió exitosamente
        """
        results: List[bool] = []

        # Enviar a Slack (prioritario por velocidad)
        if self._slack_enabled:
            slack_result = await self._send_to_slack(violation)
            results.append(slack_result)

        # Enviar por email
        if self._email_enabled:
            email_result = await self._send_to_email(violation)
            results.append(email_result)

        # Si ningún canal está configurado, log y retornar True (degradación controlada)
        if not results:
            logger.warning(
                "alert_manager.no_channels_configured",
                metric=violation.get("metric"),
                type=violation.get("type"),
                level=violation.get("level"),
            )
            return True  # No fallar si no hay canales configurados

        # Éxito si al menos un canal envió correctamente
        return any(results)

    async def _send_to_slack(self, violation: dict) -> bool:
        """
        Envía alerta a Slack via webhook.

        Args:
            violation: Diccionario con información de la alerta

        Returns:
            bool: True si se envió exitosamente
        """
        if not HTTPX_AVAILABLE:
            logger.warning("alert_manager.slack.httpx_not_available")
            return False

        try:
            webhook_url = str(getattr(settings, "slack_alert_webhook_url", ""))
            if not webhook_url:
                return False

            # Construir mensaje de Slack
            level = violation.get("level", "info")
            emoji = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(level, "📢")
            color = {"critical": "#FF0000", "warning": "#FFA500", "info": "#0000FF"}.get(level, "#808080")

            payload = {
                "attachments": [{
                    "color": color,
                    "title": f"{emoji} Alert: {violation.get('type') or violation.get('metric', 'System')}",
                    "text": violation.get("description", "No description provided"),
                    "fields": [
                        {"title": "Level", "value": level.upper(), "short": True},
                        {"title": "Metric", "value": violation.get("metric", "N/A"), "short": True},
                    ],
                    "footer": f"Agente Hotel API | {settings.environment}",
                    "ts": int(time.time()),
                }]
            }

            # Añadir contexto si existe
            if violation.get("context"):
                payload["attachments"][0]["fields"].append({
                    "title": "Context",
                    "value": str(violation["context"])[:500],
                    "short": False,
                })

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(webhook_url, json=payload)
                success = response.status_code == 200

                logger.info(
                    "alert_manager.slack.sent",
                    success=success,
                    status_code=response.status_code,
                    level=level,
                )
                return success

        except Exception as e:
            logger.error("alert_manager.slack.error", error=str(e))
            return False

    async def _send_to_email(self, violation: dict) -> bool:
        """
        Envía alerta por email usando GmailIMAPClient.

        Args:
            violation: Diccionario con información de la alerta

        Returns:
            bool: True si se envió exitosamente
        """
        try:
            from .gmail_client import GmailIMAPClient

            recipients = getattr(settings, "alert_email_recipients", [])
            if not recipients:
                logger.warning("alert_manager.email.no_recipients")
                return False

            # Construir email
            level = violation.get("level", "info")
            subject = f"[{level.upper()}] Alert: {violation.get('type') or violation.get('metric', 'System')}"

            body = f"""
Sistema de Agente Hotelero IA - Alerta de Sistema

Nivel: {level.upper()}
Tipo: {violation.get('type', 'N/A')}
Métrica: {violation.get('metric', 'N/A')}

Descripción:
{violation.get('description', 'Sin descripción')}

Contexto:
{violation.get('context', 'Sin contexto adicional')}

---
Entorno: {settings.environment}
Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}
"""

            # Enviar a cada destinatario
            gmail_client = GmailIMAPClient()
            success_count = 0

            for recipient in recipients:
                try:
                    result = gmail_client.send_response(
                        to=recipient,
                        subject=subject,
                        body=body,
                        html=False,
                    )
                    if result:
                        success_count += 1
                except Exception as e:
                    logger.error(
                        "alert_manager.email.send_failed",
                        recipient=recipient,
                        error=str(e),
                    )

            logger.info(
                "alert_manager.email.sent",
                recipients_count=len(recipients),
                success_count=success_count,
                level=level,
            )

            return success_count > 0

        except Exception as e:
            logger.error("alert_manager.email.error", error=str(e))
            return False

    def _is_in_cooldown(self, alert_key: str) -> bool:
        """Verifica si una alerta está en cooldown."""
        last_sent = self.alert_cooldown.get(alert_key)
        if last_sent is None:
            return False
        elapsed = time.monotonic() - last_sent
        return elapsed < self.cooldown_seconds

    def _get_cooldown_remaining(self, alert_key: str) -> float:
        """Calcula segundos restantes de cooldown."""
        last_sent = self.alert_cooldown.get(alert_key)
        if last_sent is None:
            return 0.0
        elapsed = time.monotonic() - last_sent
        return max(0.0, self.cooldown_seconds - elapsed)

    def clear_cooldown(self, alert_key: Optional[str] = None):
        """Limpia el cooldown de alertas."""
        if alert_key:
            self.alert_cooldown.pop(alert_key, None)
            logger.info("alert_manager.cooldown_cleared", alert_key=alert_key)
        else:
            self.alert_cooldown.clear()
            logger.info("alert_manager.all_cooldowns_cleared")


# Global singleton instance
alert_manager = AlertManager()
