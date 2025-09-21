# [PROMPT 3.1] app/services/reminder_service.py (FINAL)

from enum import Enum
import redis.asyncio as redis
from ..core.logging import logger


class ReminderType(Enum):
    PRE_ARRIVAL_7D = "pre_arrival_7d"
    PRE_ARRIVAL_1D = "pre_arrival_1d"


REMINDER_TEMPLATES = {
    "pre_arrival_7d": "Hola {guest_name}! Tu estadía está confirmada.",
    "pre_arrival_1d": "Hola {guest_name}! Mañana te esperamos.",
}


class ReminderService:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client


async def send_reminder(reminder_data: dict):
    template = REMINDER_TEMPLATES.get(reminder_data["type"], "")
    message = template.format(**reminder_data.get("template_data", {}))
    logger.info(f"Sending reminder: {message}")
