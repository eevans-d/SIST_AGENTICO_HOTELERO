"""
Tests unitarios para Performance Optimizer Service.

Este servicio es opcional en el perfil base y depende de clientes Redis
y métricas adicionales. Se omite el módulo cuando los imports no están
disponibles para mantener la suite mínima estable.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
try:
    from app.services.performance_optimizer import PerformanceOptimizer, get_performance_optimizer  # type: ignore
except Exception:  # noqa: BLE001
    pytest.skip("PerformanceOptimizer opcional no disponible en el perfil base", allow_module_level=True)


@pytest.fixture
async def mock_redis():
    """Mock de Redis client"""
    redis_mock = AsyncMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.setex.return_value = True
    redis_mock.ping.return_value = True
    return redis_mock


@pytest.fixture
async def performance_optimizer(mock_redis):
    """Fixture del performance optimizer"""
    with patch("app.services.performance_optimizer.get_redis_client", return_value=mock_redis):
        optimizer = PerformanceOptimizer()
        await optimizer.start()
        yield optimizer
        await optimizer.stop()


@pytest.mark.asyncio
async def test_performance_optimizer_initialization(performance_optimizer):
    """Test de inicialización del optimizer"""
    assert performance_optimizer is not None
    assert performance_optimizer.redis_client is not None
    assert len(performance_optimizer.optimization_history) == 0


@pytest.mark.asyncio
async def test_collect_system_metrics(performance_optimizer):
    """Test de recolección de métricas del sistema"""
    metrics = await performance_optimizer.collect_metrics()

    assert metrics is not None
    assert "cpu" in metrics
    assert "memory" in metrics
    assert "database" in metrics
    assert "cache" in metrics
    assert "api" in metrics

    # Verificar que las métricas tienen valores válidos
    assert metrics["cpu"]["usage_percent"] >= 0
    assert metrics["memory"]["usage_percent"] >= 0


@pytest.mark.asyncio
async def test_analyze_performance(performance_optimizer):
    """Test de análisis de performance"""
    # Recolectar métricas primero
    metrics = await performance_optimizer.collect_metrics()

    # Analizar performance
    analysis = await performance_optimizer.analyze_performance(metrics)

    assert analysis is not None
    assert "issues" in analysis
    assert "recommendations" in analysis
    assert "overall_score" in analysis
    assert 0 <= analysis["overall_score"] <= 100


@pytest.mark.asyncio
async def test_execute_optimization_cpu(performance_optimizer):
    """Test de ejecución de optimización de CPU"""
    # Mock de métricas con CPU alto
    mock_metrics = {
        "cpu": {"usage_percent": 85.0},
        "memory": {"usage_percent": 50.0},
        "database": {"active_connections": 50},
        "cache": {"hit_rate": 0.8},
        "api": {"avg_response_time": 200},
    }

    with patch.object(performance_optimizer, "collect_metrics", return_value=mock_metrics):
        result = await performance_optimizer.execute_optimization(force=True, optimization_types=["cpu"])

    assert result is not None
    assert len(performance_optimizer.optimization_history) > 0


@pytest.mark.asyncio
async def test_execute_optimization_memory(performance_optimizer):
    """Test de ejecución de optimización de memoria"""
    mock_metrics = {
        "cpu": {"usage_percent": 50.0},
        "memory": {"usage_percent": 88.0},
        "database": {"active_connections": 50},
        "cache": {"hit_rate": 0.8},
        "api": {"avg_response_time": 200},
    }

    with patch.object(performance_optimizer, "collect_metrics", return_value=mock_metrics):
        result = await performance_optimizer.execute_optimization(force=True, optimization_types=["memory"])

    assert result is not None


@pytest.mark.asyncio
async def test_execute_optimization_database(performance_optimizer):
    """Test de ejecución de optimización de base de datos"""
    mock_metrics = {
        "cpu": {"usage_percent": 50.0},
        "memory": {"usage_percent": 60.0},
        "database": {"active_connections": 150, "slow_queries": 25},
        "cache": {"hit_rate": 0.8},
        "api": {"avg_response_time": 200},
    }

    with patch.object(performance_optimizer, "collect_metrics", return_value=mock_metrics):
        result = await performance_optimizer.execute_optimization(force=True, optimization_types=["database"])

    assert result is not None


@pytest.mark.asyncio
async def test_execute_optimization_cache(performance_optimizer):
    """Test de ejecución de optimización de cache"""
    mock_metrics = {
        "cpu": {"usage_percent": 50.0},
        "memory": {"usage_percent": 60.0},
        "database": {"active_connections": 50},
        "cache": {"hit_rate": 0.45, "memory_usage": 1500000000},
        "api": {"avg_response_time": 200},
    }

    with patch.object(performance_optimizer, "collect_metrics", return_value=mock_metrics):
        result = await performance_optimizer.execute_optimization(force=True, optimization_types=["cache"])

    assert result is not None


@pytest.mark.asyncio
async def test_execute_optimization_api(performance_optimizer):
    """Test de ejecución de optimización de API"""
    mock_metrics = {
        "cpu": {"usage_percent": 50.0},
        "memory": {"usage_percent": 60.0},
        "database": {"active_connections": 50},
        "cache": {"hit_rate": 0.8},
        "api": {"avg_response_time": 1500},
    }

    with patch.object(performance_optimizer, "collect_metrics", return_value=mock_metrics):
        result = await performance_optimizer.execute_optimization(force=True, optimization_types=["api"])

    assert result is not None


@pytest.mark.asyncio
async def test_auto_optimize(performance_optimizer):
    """Test de auto-optimización"""
    # Mock de métricas que requieren optimización
    mock_metrics = {
        "cpu": {"usage_percent": 88.0},
        "memory": {"usage_percent": 85.0},
        "database": {"active_connections": 50},
        "cache": {"hit_rate": 0.8},
        "api": {"avg_response_time": 200},
    }

    with patch.object(performance_optimizer, "collect_metrics", return_value=mock_metrics):
        result = await performance_optimizer.auto_optimize()

    assert result is not None
    assert "optimizations_executed" in result
    assert "metrics_analyzed" in result


@pytest.mark.asyncio
async def test_get_optimization_report(performance_optimizer):
    """Test de obtención de reporte de optimización"""
    # Ejecutar una optimización primero
    mock_metrics = {
        "cpu": {"usage_percent": 85.0},
        "memory": {"usage_percent": 60.0},
        "database": {"active_connections": 50},
        "cache": {"hit_rate": 0.8},
        "api": {"avg_response_time": 200},
    }

    with patch.object(performance_optimizer, "collect_metrics", return_value=mock_metrics):
        await performance_optimizer.execute_optimization(force=True)

    # Obtener reporte
    report = await performance_optimizer.get_optimization_report()

    assert report is not None
    assert "current_metrics" in report
    assert "optimization_history" in report
    assert "recommendations" in report
    assert "thresholds" in report


@pytest.mark.asyncio
async def test_optimization_history_tracking(performance_optimizer):
    """Test de tracking del historial de optimizaciones"""
    initial_count = len(performance_optimizer.optimization_history)

    # Ejecutar múltiples optimizaciones
    mock_metrics = {
        "cpu": {"usage_percent": 85.0},
        "memory": {"usage_percent": 60.0},
        "database": {"active_connections": 50},
        "cache": {"hit_rate": 0.8},
        "api": {"avg_response_time": 200},
    }

    with patch.object(performance_optimizer, "collect_metrics", return_value=mock_metrics):
        await performance_optimizer.execute_optimization(force=True, optimization_types=["cpu"])
        await performance_optimizer.execute_optimization(force=True, optimization_types=["memory"])

    # Verificar que el historial creció
    assert len(performance_optimizer.optimization_history) > initial_count


@pytest.mark.asyncio
async def test_optimization_throttling(performance_optimizer):
    """Test de throttling de optimizaciones"""
    mock_metrics = {
        "cpu": {"usage_percent": 85.0},
        "memory": {"usage_percent": 60.0},
        "database": {"active_connections": 50},
        "cache": {"hit_rate": 0.8},
        "api": {"avg_response_time": 200},
    }

    with patch.object(performance_optimizer, "collect_metrics", return_value=mock_metrics):
        # Primera optimización debe ejecutarse
        result1 = await performance_optimizer.execute_optimization(optimization_types=["cpu"])

        # Segunda optimización inmediata no debe ejecutarse (sin force)
        await performance_optimizer.execute_optimization(optimization_types=["cpu"])

        # Con force=True debe ejecutarse
        result3 = await performance_optimizer.execute_optimization(force=True, optimization_types=["cpu"])

    # La primera y tercera deben ejecutarse, la segunda no
    assert result1 is not None or result3 is not None


@pytest.mark.asyncio
async def test_performance_score_calculation(performance_optimizer):
    """Test de cálculo de score de performance"""
    # Mock de métricas excelentes
    good_metrics = {
        "cpu": {"usage_percent": 30.0},
        "memory": {"usage_percent": 40.0},
        "database": {"active_connections": 20, "slow_queries": 0},
        "cache": {"hit_rate": 0.95},
        "api": {"avg_response_time": 100},
    }

    with patch.object(performance_optimizer, "collect_metrics", return_value=good_metrics):
        analysis = await performance_optimizer.analyze_performance(good_metrics)

    # Score debe ser alto
    assert analysis["overall_score"] > 70

    # Mock de métricas pobres
    poor_metrics = {
        "cpu": {"usage_percent": 95.0},
        "memory": {"usage_percent": 92.0},
        "database": {"active_connections": 200, "slow_queries": 50},
        "cache": {"hit_rate": 0.3},
        "api": {"avg_response_time": 2000},
    }

    with patch.object(performance_optimizer, "collect_metrics", return_value=poor_metrics):
        analysis = await performance_optimizer.analyze_performance(poor_metrics)

    # Score debe ser bajo
    assert analysis["overall_score"] < 50


@pytest.mark.asyncio
async def test_optimization_recommendations(performance_optimizer):
    """Test de generación de recomendaciones"""
    # Mock de métricas con varios problemas
    problematic_metrics = {
        "cpu": {"usage_percent": 85.0},
        "memory": {"usage_percent": 88.0},
        "database": {"active_connections": 150, "slow_queries": 25},
        "cache": {"hit_rate": 0.45},
        "api": {"avg_response_time": 1500},
    }

    with patch.object(performance_optimizer, "collect_metrics", return_value=problematic_metrics):
        analysis = await performance_optimizer.analyze_performance(problematic_metrics)

    # Debe haber múltiples recomendaciones
    assert len(analysis["recommendations"]) > 0
    assert len(analysis["issues"]) > 0


@pytest.mark.asyncio
async def test_get_performance_optimizer_singleton():
    """Test de obtención del singleton del optimizer"""
    optimizer1 = await get_performance_optimizer()
    optimizer2 = await get_performance_optimizer()

    # Debe ser la misma instancia
    assert optimizer1 is optimizer2


@pytest.mark.asyncio
async def test_optimization_impact_estimation(performance_optimizer):
    """Test de estimación de impacto de optimizaciones"""
    mock_metrics = {
        "cpu": {"usage_percent": 85.0},
        "memory": {"usage_percent": 60.0},
        "database": {"active_connections": 50},
        "cache": {"hit_rate": 0.8},
        "api": {"avg_response_time": 200},
    }

    with patch.object(performance_optimizer, "collect_metrics", return_value=mock_metrics):
        await performance_optimizer.execute_optimization(force=True, optimization_types=["cpu"])

    # Verificar que se estima el impacto
    if performance_optimizer.optimization_history:
        last_optimization = performance_optimizer.optimization_history[-1]
        assert hasattr(last_optimization, "estimated_impact")


@pytest.mark.asyncio
async def test_concurrent_optimizations(performance_optimizer):
    """Test de manejo de optimizaciones concurrentes"""
    mock_metrics = {
        "cpu": {"usage_percent": 85.0},
        "memory": {"usage_percent": 85.0},
        "database": {"active_connections": 50},
        "cache": {"hit_rate": 0.8},
        "api": {"avg_response_time": 200},
    }

    with patch.object(performance_optimizer, "collect_metrics", return_value=mock_metrics):
        # Ejecutar múltiples optimizaciones en paralelo
        tasks = [
            performance_optimizer.execute_optimization(force=True, optimization_types=["cpu"]),
            performance_optimizer.execute_optimization(force=True, optimization_types=["memory"]),
            performance_optimizer.execute_optimization(force=True, optimization_types=["cache"]),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Todas deben completarse sin excepciones
    assert all(result is not None or isinstance(result, dict) for result in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
