from celery import Celery
from app.core.settings import settings

celery_app = Celery(
    "worker",
    broker=str(settings.redis_url),
    backend=str(settings.redis_url)
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)
