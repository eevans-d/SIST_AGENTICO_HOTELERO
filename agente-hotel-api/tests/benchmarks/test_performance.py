"""Performance benchmarks for critical paths."""

# Skip completo si el plugin de benchmark no está disponible en el entorno
try:  # pragma: no cover
    import pytest_benchmark  # type: ignore  # noqa: F401
except Exception:  # pragma: no cover
    import pytest
    pytest.skip("pytest-benchmark no instalado", allow_module_level=True)

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.benchmark(group="api")
def test_health_endpoint_performance(benchmark):
    """Benchmark health endpoint response time."""
    import asyncio
    from app.main import app

    async def health_check():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/live")
            assert response.status_code == 200
            return response

    result = benchmark(lambda: asyncio.run(health_check()))
    assert result is not None


@pytest.mark.benchmark(group="metrics")
def test_metrics_endpoint_performance(benchmark):
    """Benchmark metrics endpoint response time."""
    import asyncio
    from app.main import app

    async def get_metrics():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/metrics")
            assert response.status_code == 200
            return response

    result = benchmark(lambda: asyncio.run(get_metrics()))
    assert result is not None


@pytest.mark.benchmark(group="validation")
def test_pydantic_validation_performance(benchmark):
    """Benchmark Pydantic model validation."""
    from app.models.unified_message import UnifiedMessage
    from datetime import datetime

    def validate_message():
        return UnifiedMessage(
            message_id="bench_msg_123",
            canal="test",
            user_id="test_user_123",
            timestamp_iso=datetime.now().isoformat(),
            tipo="text",
            texto="Hola, quiero hacer una reserva para 2 personas",
            metadata={"tenant_id": "default"},
        )

    result = benchmark(validate_message)
    assert result.user_id == "test_user_123"
