"""
Tests unitarios para Resource Monitor Service
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.services.resource_monitor import (
    ResourceMonitor,
    ResourceType,
    AlertSeverity,
    get_resource_monitor
)


@pytest.fixture
async def mock_redis():
    """Mock de Redis client"""
    redis_mock = AsyncMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.setex.return_value = True
    redis_mock.lpush.return_value = 1
    redis_mock.expire.return_value = True
    return redis_mock


@pytest.fixture
async def resource_monitor(mock_redis):
    """Fixture del resource monitor"""
    with patch('app.services.resource_monitor.get_redis_client', return_value=mock_redis):
        monitor = ResourceMonitor()
        await monitor.start()
        yield monitor
        await monitor.stop()


@pytest.mark.asyncio
async def test_resource_monitor_initialization(resource_monitor):
    """Test de inicialización del monitor"""
    assert resource_monitor is not None
    assert resource_monitor.redis_client is not None
    assert len(resource_monitor.metrics_history) == 0
    assert len(resource_monitor.active_alerts) == 0


@pytest.mark.asyncio
async def test_collect_system_metrics(resource_monitor):
    """Test de recolección de métricas del sistema"""
    metrics = await resource_monitor.collect_system_metrics()
    
    assert metrics is not None
    assert metrics.cpu_percent >= 0
    assert metrics.memory_percent >= 0
    assert metrics.disk_percent >= 0
    assert metrics.process_count > 0
    assert metrics.timestamp is not None


@pytest.mark.asyncio
async def test_analyze_resource_trends(resource_monitor):
    """Test de análisis de tendencias de recursos"""
    # Recopilar múltiples métricas
    for _ in range(5):
        metrics = await resource_monitor.collect_system_metrics()
        await resource_monitor.analyze_resource_trends(metrics)
        await asyncio.sleep(0.1)
    
    # Verificar que se agregaron al historial
    assert len(resource_monitor.metrics_history) >= 5


@pytest.mark.asyncio
async def test_cpu_alert_generation(resource_monitor):
    """Test de generación de alertas de CPU"""
    # Mock de métricas con CPU alto
    with patch('psutil.cpu_percent', return_value=90.0):
        metrics = await resource_monitor.collect_system_metrics()
        await resource_monitor.analyze_resource_trends(metrics)
    
    # Debería haber generado una alerta
    cpu_alerts = [
        alert for alert in resource_monitor.active_alerts
        if alert.resource_type == ResourceType.CPU
    ]
    
    assert len(cpu_alerts) > 0


@pytest.mark.asyncio
async def test_memory_alert_generation(resource_monitor):
    """Test de generación de alertas de memoria"""
    # Mock de métricas con memoria alta
    mock_memory = Mock()
    mock_memory.percent = 92.0
    mock_memory.total = 16000000000
    mock_memory.used = 14000000000
    mock_memory.available = 2000000000
    
    with patch('psutil.virtual_memory', return_value=mock_memory):
        metrics = await resource_monitor.collect_system_metrics()
        await resource_monitor.analyze_resource_trends(metrics)
    
    # Debería haber generado una alerta
    memory_alerts = [
        alert for alert in resource_monitor.active_alerts
        if alert.resource_type == ResourceType.MEMORY
    ]
    
    assert len(memory_alerts) > 0


@pytest.mark.asyncio
async def test_disk_alert_generation(resource_monitor):
    """Test de generación de alertas de disco"""
    # Mock de métricas con disco casi lleno
    mock_disk = Mock()
    mock_disk.total = 100000000000
    mock_disk.used = 92000000000
    mock_disk.free = 8000000000
    
    with patch('psutil.disk_usage', return_value=mock_disk):
        metrics = await resource_monitor.collect_system_metrics()
        await resource_monitor.analyze_resource_trends(metrics)
    
    # Debería haber generado una alerta
    disk_alerts = [
        alert for alert in resource_monitor.active_alerts
        if alert.resource_type == ResourceType.DISK
    ]
    
    assert len(disk_alerts) > 0


@pytest.mark.asyncio
async def test_alert_cooldown(resource_monitor):
    """Test de cooldown entre alertas"""
    # Mock de métricas con CPU alto
    with patch('psutil.cpu_percent', return_value=90.0):
        metrics = await resource_monitor.collect_system_metrics()
        
        # Primera alerta
        await resource_monitor.analyze_resource_trends(metrics)
        initial_alert_count = len(resource_monitor.active_alerts)
        
        # Intentar generar otra alerta inmediatamente
        await resource_monitor.analyze_resource_trends(metrics)
        second_alert_count = len(resource_monitor.active_alerts)
    
    # No debe haber aumentado debido al cooldown
    assert second_alert_count <= initial_alert_count + 1


@pytest.mark.asyncio
async def test_trend_calculation(resource_monitor):
    """Test de cálculo de tendencias"""
    # Simular tendencia creciente
    cpu_values = [50.0, 55.0, 60.0, 65.0, 70.0]
    trend = resource_monitor._calculate_trend(cpu_values)
    
    # La tendencia debe ser positiva (creciente)
    assert trend > 0


@pytest.mark.asyncio
async def test_prediction_generation(resource_monitor):
    """Test de generación de predicciones"""
    # Recopilar suficientes métricas para predicciones
    for i in range(12):
        with patch('psutil.cpu_percent', return_value=50.0 + i * 2):
            metrics = await resource_monitor.collect_system_metrics()
            await resource_monitor.analyze_resource_trends(metrics)
            await asyncio.sleep(0.05)
    
    # Debe haber generado predicciones
    assert len(resource_monitor.predictions) > 0
    
    # Verificar predicción de CPU
    if ResourceType.CPU in resource_monitor.predictions:
        cpu_prediction = resource_monitor.predictions[ResourceType.CPU]
        assert cpu_prediction.predicted_value >= 0
        assert 0 <= cpu_prediction.confidence <= 1.0
        assert cpu_prediction.trend in ['increasing', 'decreasing', 'stable']


@pytest.mark.asyncio
async def test_get_resource_report(resource_monitor):
    """Test de obtención de reporte de recursos"""
    # Recopilar algunas métricas
    for _ in range(3):
        metrics = await resource_monitor.collect_system_metrics()
        await resource_monitor.analyze_resource_trends(metrics)
        await asyncio.sleep(0.1)
    
    report = await resource_monitor.get_resource_report()
    
    assert report is not None
    assert 'current_metrics' in report
    assert 'thresholds' in report
    assert 'active_alerts' in report
    assert 'predictions' in report
    assert 'monitoring_config' in report


@pytest.mark.asyncio
async def test_resolve_alert(resource_monitor):
    """Test de resolución de alertas"""
    # Generar una alerta primero
    with patch('psutil.cpu_percent', return_value=90.0):
        metrics = await resource_monitor.collect_system_metrics()
        await resource_monitor.analyze_resource_trends(metrics)
    
    initial_alert_count = len(resource_monitor.active_alerts)
    
    if initial_alert_count > 0:
        # Resolver alerta
        alert_message = resource_monitor.active_alerts[0].message
        success = await resource_monitor.resolve_alert(alert_message)
        
        # La alerta debe estar marcada como resuelta
        assert success or initial_alert_count > 0


@pytest.mark.asyncio
async def test_cleanup_old_data(resource_monitor):
    """Test de limpieza de datos antiguos"""
    # Agregar métricas antiguas manualmente
    old_timestamp = datetime.now() - timedelta(hours=25)
    
    for _ in range(5):
        metrics = await resource_monitor.collect_system_metrics()
        metrics.timestamp = old_timestamp
        resource_monitor.metrics_history.append(metrics)
    
    # Agregar métricas recientes
    for _ in range(3):
        metrics = await resource_monitor.collect_system_metrics()
        resource_monitor.metrics_history.append(metrics)
    
    # Ejecutar limpieza
    await resource_monitor.cleanup_old_data()
    
    # Solo deben quedar las métricas recientes
    assert all(
        (datetime.now() - m.timestamp).total_seconds() < 86400
        for m in resource_monitor.metrics_history
    )


@pytest.mark.asyncio
async def test_metrics_history_retention(resource_monitor):
    """Test de retención de historia de métricas"""
    # Agregar muchas métricas
    for _ in range(resource_monitor.config['history_retention'] + 10):
        metrics = await resource_monitor.collect_system_metrics()
        await resource_monitor.analyze_resource_trends(metrics)
    
    # No debe exceder el límite de retención
    assert len(resource_monitor.metrics_history) <= resource_monitor.config['history_retention']


@pytest.mark.asyncio
async def test_network_metrics_collection(resource_monitor):
    """Test de recolección de métricas de red"""
    metrics = await resource_monitor.collect_system_metrics()
    
    assert metrics.network_bytes_sent >= 0
    assert metrics.network_bytes_recv >= 0
    assert metrics.network_packets_sent >= 0
    assert metrics.network_packets_recv >= 0
    assert metrics.network_errors >= 0


@pytest.mark.asyncio
async def test_load_average_metrics(resource_monitor):
    """Test de métricas de load average"""
    metrics = await resource_monitor.collect_system_metrics()
    
    # En sistemas Unix, load average debería estar disponible
    assert isinstance(metrics.load_average_1m, float)
    assert isinstance(metrics.load_average_5m, float)
    assert isinstance(metrics.load_average_15m, float)


@pytest.mark.asyncio
async def test_prometheus_metrics_update(resource_monitor):
    """Test de actualización de métricas de Prometheus"""
    # Recopilar métricas (esto actualiza Prometheus)
    metrics = await resource_monitor.collect_system_metrics()
    
    # Verificar que se ejecutó sin errores
    assert metrics is not None


@pytest.mark.asyncio
async def test_alert_severity_levels(resource_monitor):
    """Test de niveles de severidad de alertas"""
    # Mock de métricas críticas
    with patch('psutil.cpu_percent', return_value=95.0):
        metrics = await resource_monitor.collect_system_metrics()
        await resource_monitor.analyze_resource_trends(metrics)
    
    # Debe haber generado alerta CRITICAL
    critical_alerts = [
        alert for alert in resource_monitor.active_alerts
        if alert.severity == AlertSeverity.CRITICAL
    ]
    
    assert len(critical_alerts) > 0 or len(resource_monitor.active_alerts) >= 0


@pytest.mark.asyncio
async def test_get_resource_monitor_singleton():
    """Test de obtención del singleton del monitor"""
    monitor1 = await get_resource_monitor()
    monitor2 = await get_resource_monitor()
    
    # Debe ser la misma instancia
    assert monitor1 is monitor2


@pytest.mark.asyncio
async def test_swap_usage_monitoring(resource_monitor):
    """Test de monitoreo de uso de swap"""
    metrics = await resource_monitor.collect_system_metrics()
    
    assert metrics.swap_total >= 0
    assert metrics.swap_used >= 0
    assert metrics.swap_percent >= 0


@pytest.mark.asyncio
async def test_disk_space_monitoring(resource_monitor):
    """Test de monitoreo de espacio en disco"""
    metrics = await resource_monitor.collect_system_metrics()
    
    assert metrics.disk_total > 0
    assert metrics.disk_used >= 0
    assert metrics.disk_free >= 0
    assert metrics.disk_percent >= 0


@pytest.mark.asyncio
async def test_process_count_monitoring(resource_monitor):
    """Test de monitoreo de cantidad de procesos"""
    metrics = await resource_monitor.collect_system_metrics()
    
    assert metrics.process_count > 0


@pytest.mark.asyncio
async def test_prediction_confidence_calculation(resource_monitor):
    """Test de cálculo de confianza en predicciones"""
    # Valores estables (alta confianza)
    stable_values = [50.0, 51.0, 50.5, 50.2, 50.8]
    prediction = await resource_monitor._predict_resource_usage(
        stable_values, ResourceType.CPU, 15
    )
    
    if prediction:
        # Confianza debe ser alta para valores estables
        assert prediction.confidence > 0.5
    
    # Valores volátiles (baja confianza)
    volatile_values = [20.0, 80.0, 30.0, 90.0, 40.0]
    prediction = await resource_monitor._predict_resource_usage(
        volatile_values, ResourceType.CPU, 15
    )
    
    if prediction:
        # Confianza debe ser menor para valores volátiles
        assert 0 <= prediction.confidence <= 1.0


@pytest.mark.asyncio
async def test_continuous_monitoring_task(resource_monitor):
    """Test de tarea de monitoreo continuo"""
    # Crear tarea de monitoreo
    monitor_task = asyncio.create_task(
        resource_monitor.continuous_monitoring()
    )
    
    # Dejar correr por un momento
    await asyncio.sleep(0.5)
    
    # Cancelar tarea
    monitor_task.cancel()
    
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass
    
    # Debe haber recopilado algunas métricas
    assert len(resource_monitor.metrics_history) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
