import pytest
from app.core.celery_app import celery_app

def test_celery_config():
    """Verify Celery application configuration."""
    assert celery_app.conf.broker_url is not None
    assert celery_app.conf.result_backend is not None
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]
    assert celery_app.main == "worker"
