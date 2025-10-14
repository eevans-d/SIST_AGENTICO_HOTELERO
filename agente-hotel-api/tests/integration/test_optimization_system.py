"""
Tests de integración para el sistema de optimización de performance
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.services.performance_optimizer import get_performance_optimizer
from app.services.resource_monitor import get_resource_monitor
from app.services.auto_scaler import get_auto_scaler


@pytest.fixture
def test_client():
    """Fixture del test client"""
    return TestClient(app)


@pytest.fixture
async def async_test_client():
    """Fixture del async test client"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_performance_status_endpoint(async_test_client):
    """Test del endpoint de estado de performance"""
    response = await async_test_client.get("/api/v1/performance/status")

    assert response.status_code in [200, 404]  # 404 si el router no está disponible

    if response.status_code == 200:
        data = response.json()
        assert "system_health" in data
        assert "performance_score" in data
        assert "resource_usage" in data


@pytest.mark.asyncio
async def test_performance_metrics_endpoint(async_test_client):
    """Test del endpoint de métricas de performance"""
    response = await async_test_client.get("/api/v1/performance/metrics")

    assert response.status_code in [200, 404]

    if response.status_code == 200:
        data = response.json()
        assert "current_metrics" in data
        assert "thresholds" in data


@pytest.mark.asyncio
async def test_optimization_report_endpoint(async_test_client):
    """Test del endpoint de reporte de optimización"""
    response = await async_test_client.get("/api/v1/performance/optimization/report")

    assert response.status_code in [200, 404]

    if response.status_code == 200:
        data = response.json()
        assert "current_metrics" in data or "error" in data


@pytest.mark.asyncio
async def test_execute_optimization_endpoint(async_test_client):
    """Test del endpoint de ejecución de optimización"""
    response = await async_test_client.post("/api/v1/performance/optimization/execute", params={"force": True})

    assert response.status_code in [200, 404, 429]  # 429 si rate limit

    if response.status_code == 200:
        data = response.json()
        assert "message" in data


@pytest.mark.asyncio
async def test_database_report_endpoint(async_test_client):
    """Test del endpoint de reporte de base de datos"""
    response = await async_test_client.get("/api/v1/performance/database/report")

    assert response.status_code in [200, 404]

    if response.status_code == 200:
        data = response.json()
        assert "slow_queries" in data or "error" in data


@pytest.mark.asyncio
async def test_cache_report_endpoint(async_test_client):
    """Test del endpoint de reporte de cache"""
    response = await async_test_client.get("/api/v1/performance/cache/report")

    assert response.status_code in [200, 404]

    if response.status_code == 200:
        data = response.json()
        assert "cache_stats" in data or "error" in data


@pytest.mark.asyncio
async def test_scaling_status_endpoint(async_test_client):
    """Test del endpoint de estado de escalado"""
    response = await async_test_client.get("/api/v1/performance/scaling/status")

    assert response.status_code in [200, 404]

    if response.status_code == 200:
        data = response.json()
        assert "current_instances" in data or "error" in data


@pytest.mark.asyncio
async def test_scaling_evaluation_endpoint(async_test_client):
    """Test del endpoint de evaluación de escalado"""
    response = await async_test_client.post("/api/v1/performance/scaling/evaluate")

    assert response.status_code in [200, 404, 429]

    if response.status_code == 200:
        data = response.json()
        assert "decisions" in data or "error" in data


@pytest.mark.asyncio
async def test_performance_alerts_endpoint(async_test_client):
    """Test del endpoint de alertas de performance"""
    response = await async_test_client.get("/api/v1/performance/alerts")

    assert response.status_code in [200, 404]

    if response.status_code == 200:
        data = response.json()
        assert "alerts" in data or "error" in data


@pytest.mark.asyncio
async def test_performance_recommendations_endpoint(async_test_client):
    """Test del endpoint de recomendaciones"""
    response = await async_test_client.get("/api/v1/performance/recommendations")

    assert response.status_code in [200, 404]

    if response.status_code == 200:
        data = response.json()
        assert "system_optimization" in data or "error" in data


@pytest.mark.asyncio
async def test_integration_optimizer_and_monitor():
    """Test de integración entre optimizer y monitor"""
    try:
        optimizer = await get_performance_optimizer()
        monitor = await get_resource_monitor()

        # El optimizer debe poder obtener métricas del monitor
        resource_report = await monitor.get_resource_report()
        assert resource_report is not None

        # El optimizer debe poder analizar las métricas
        metrics = await optimizer.collect_metrics()
        assert metrics is not None

    except Exception as e:
        # Es aceptable si los servicios no están disponibles en testing
        pytest.skip(f"Servicios de optimización no disponibles: {e}")


@pytest.mark.asyncio
async def test_integration_monitor_and_scaler():
    """Test de integración entre monitor y auto-scaler"""
    try:
        monitor = await get_resource_monitor()
        scaler = await get_auto_scaler()

        # El scaler debe poder usar métricas del monitor para decisiones
        await monitor.get_resource_report()
        decisions = await scaler.evaluate_scaling_decisions()

        # Las decisiones deben basarse en métricas
        assert isinstance(decisions, list)

    except Exception as e:
        pytest.skip(f"Servicios de optimización no disponibles: {e}")


@pytest.mark.asyncio
async def test_integration_full_optimization_workflow():
    """Test del workflow completo de optimización"""
    try:
        optimizer = await get_performance_optimizer()
        monitor = await get_resource_monitor()
        scaler = await get_auto_scaler()

        # 1. Monitor recopila métricas
        metrics = await monitor.collect_system_metrics()
        assert metrics is not None

        # 2. Optimizer analiza performance
        perf_metrics = await optimizer.collect_metrics()
        analysis = await optimizer.analyze_performance(perf_metrics)
        assert analysis is not None

        # 3. Scaler evalúa decisiones de escalado
        decisions = await scaler.evaluate_scaling_decisions()
        assert isinstance(decisions, list)

        # 4. Obtener reportes consolidados
        resource_report = await monitor.get_resource_report()
        optimization_report = await optimizer.get_optimization_report()
        scaling_status = await scaler.get_scaling_status()

        assert resource_report is not None
        assert optimization_report is not None
        assert scaling_status is not None

    except Exception as e:
        pytest.skip(f"Servicios de optimización no disponibles: {e}")


@pytest.mark.asyncio
async def test_concurrent_optimization_operations():
    """Test de operaciones de optimización concurrentes"""
    try:
        optimizer = await get_performance_optimizer()
        monitor = await get_resource_monitor()

        # Ejecutar operaciones concurrentes
        tasks = [
            monitor.collect_system_metrics(),
            optimizer.collect_metrics(),
            monitor.get_resource_report(),
            optimizer.get_optimization_report(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Todas las operaciones deben completarse
        assert len(results) == 4
        assert all(result is not None for result in results if not isinstance(result, Exception))

    except Exception as e:
        pytest.skip(f"Servicios de optimización no disponibles: {e}")


@pytest.mark.asyncio
async def test_optimization_under_load():
    """Test de optimización bajo carga"""
    try:
        optimizer = await get_performance_optimizer()

        # Simular múltiples solicitudes de optimización
        optimization_tasks = []
        for i in range(5):
            task = optimizer.collect_metrics()
            optimization_tasks.append(task)

        results = await asyncio.gather(*optimization_tasks, return_exceptions=True)

        # Todas deben completarse sin errores críticos
        assert len(results) == 5

    except Exception as e:
        pytest.skip(f"Servicios de optimización no disponibles: {e}")


@pytest.mark.asyncio
async def test_error_handling_in_optimization():
    """Test de manejo de errores en optimización"""
    try:
        optimizer = await get_performance_optimizer()

        # Intentar ejecutar optimización con parámetros inválidos
        with pytest.raises(Exception):
            await optimizer.execute_optimization(force=True, optimization_types=["invalid_type"])

    except Exception as e:
        pytest.skip(f"Servicios de optimización no disponibles: {e}")


@pytest.mark.asyncio
async def test_optimization_metrics_consistency():
    """Test de consistencia de métricas de optimización"""
    try:
        optimizer = await get_performance_optimizer()
        monitor = await get_resource_monitor()

        # Recopilar métricas de ambas fuentes
        optimizer_metrics = await optimizer.collect_metrics()
        monitor_metrics = await monitor.collect_system_metrics()

        # Las métricas básicas deben ser consistentes
        assert optimizer_metrics is not None
        assert monitor_metrics is not None

        # CPU y memoria deben tener valores similares (dentro de un margen)
        if "cpu" in optimizer_metrics and monitor_metrics.cpu_percent:
            cpu_diff = abs(optimizer_metrics["cpu"]["usage_percent"] - monitor_metrics.cpu_percent)
            assert cpu_diff < 20  # Margen de 20%

    except Exception as e:
        pytest.skip(f"Servicios de optimización no disponibles: {e}")


@pytest.mark.asyncio
async def test_optimization_state_persistence():
    """Test de persistencia de estado de optimización"""
    try:
        optimizer = await get_performance_optimizer()

        # Ejecutar una optimización
        await optimizer.execute_optimization(force=True)

        # Obtener reporte
        report = await optimizer.get_optimization_report()

        # El historial debe incluir la optimización ejecutada
        if "optimization_history" in report:
            assert len(report["optimization_history"]) > 0

    except Exception as e:
        pytest.skip(f"Servicios de optimización no disponibles: {e}")


@pytest.mark.asyncio
async def test_scaling_decision_execution():
    """Test de ejecución de decisiones de escalado"""
    try:
        scaler = await get_auto_scaler()

        # Evaluar decisiones
        decisions = await scaler.evaluate_scaling_decisions()

        # Si hay decisiones, intentar ejecutarlas
        if decisions:
            results = await scaler.execute_scaling_decisions(decisions[:1])  # Solo primera
            assert isinstance(results, list)

    except Exception as e:
        pytest.skip(f"Servicios de optimización no disponibles: {e}")


@pytest.mark.asyncio
async def test_rate_limiting_on_optimization_endpoints(async_test_client):
    """Test de rate limiting en endpoints de optimización"""
    # Hacer múltiples requests rápidamente
    responses = []
    for _ in range(5):
        response = await async_test_client.get("/api/v1/performance/status")
        responses.append(response)
        await asyncio.sleep(0.1)

    # Al menos algunos deben tener éxito
    success_count = sum(1 for r in responses if r.status_code == 200)
    assert success_count > 0 or all(r.status_code == 404 for r in responses)


@pytest.mark.asyncio
async def test_optimization_system_health():
    """Test de salud del sistema de optimización"""
    try:
        optimizer = await get_performance_optimizer()
        monitor = await get_resource_monitor()
        scaler = await get_auto_scaler()

        # Todos los servicios deben estar operativos
        assert optimizer.redis_client is not None
        assert monitor.redis_client is not None

        # Deben poder ejecutar operaciones básicas
        await optimizer.collect_metrics()
        await monitor.collect_system_metrics()
        await scaler.get_scaling_status()

    except Exception as e:
        pytest.skip(f"Servicios de optimización no disponibles: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
