# [PROMPT 3.5] app/services/alert_manager.py (Refinado)

from datetime import datetime
# import aiosmtplib
# import httpx


class AlertManager:
    def __init__(self):
        self.alert_cooldown = {}

    async def send_alert(self, violation: dict):
        alert_key = f"{violation['metric']}:{violation['level']}"
        if alert_key in self.alert_cooldown and (datetime.now() - self.alert_cooldown[alert_key]).seconds < 1800:
            return

        # Lógica de envío de alertas por email/SMS/Slack
        self.alert_cooldown[alert_key] = datetime.now()


alert_manager = AlertManager()
