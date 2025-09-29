# [PROMPT GA-02] tests/test_metrics_readiness.py

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_readiness_metrics_update(test_app):
    app = test_app
    transport = ASGITransport(app=app)

    # Hacemos una llamada a /health/ready para actualizar métricas
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/health/ready")
        assert resp.status_code in (200, 503)

    # Ahora scrapeamos /metrics y verificamos presencia de gauges
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        metrics = (await ac.get("/metrics")).text

    assert "readiness_up" in metrics
    assert "readiness_last_check_timestamp" in metrics
    assert 'dependency_up{name="database"}' in metrics
    assert 'dependency_up{name="redis"}' in metrics
    assert 'dependency_up{name="pms"}' in metrics
