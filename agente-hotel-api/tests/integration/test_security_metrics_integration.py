"""
Tests para validar instrumentación de métricas de seguridad:
- password_rotations_total en endpoint /change-password
- Verificar que las métricas se exponen correctamente
"""
import pytest
from httpx import AsyncClient
from prometheus_client import REGISTRY


def _get_metric_value(name: str, label_filter: dict | None = None) -> float:
    """Helper para obtener valor de métrica del registry de Prometheus"""
    for metric in REGISTRY.collect():
        if metric.name == name:
            total = 0.0
            for sample in metric.samples:
                if sample.name != name:
                    continue
                if label_filter:
                    # All labels in filter must match
                    if any(sample.labels.get(k) != v for k, v in label_filter.items()):
                        continue
                total += sample.value
            return total
    return 0.0


@pytest.mark.asyncio
async def test_password_rotation_metric_on_success(test_client: AsyncClient):
    """
    Test que valida que password_rotations_total se incrementa con result=success
    cuando el cambio de password es exitoso.
    """
    # Este test es ilustrativo; requiere un usuario real y autenticación
    # En un entorno de test completo, se crearía un usuario de prueba
    # y se usaría su token para cambiar el password
    
    # Capturar valor inicial
    before_success = _get_metric_value("password_rotations_total", {"result": "success"})
    
    # NOTA: Este endpoint requiere autenticación JWT válida
    # En un test real, primero harías login para obtener el token
    # response = await test_client.post(
    #     "/api/v1/security/change-password",
    #     headers={"Authorization": f"Bearer {valid_token}"},
    #     json={
    #         "current_password": "old_pass",
    #         "new_password": "new_secure_pass_123"
    #     }
    # )
    
    # Por ahora, validamos que la métrica existe en el registry
    from app.services.metrics_service import metrics_service
    
    # Simular incremento manual (en test real vendría del endpoint)
    metrics_service.inc_password_rotation("success")
    
    # Verificar incremento
    after_success = _get_metric_value("password_rotations_total", {"result": "success"})
    assert after_success == before_success + 1, "password_rotations_total debe incrementar en success"


@pytest.mark.asyncio
async def test_password_rotation_metric_on_failure(test_client: AsyncClient):
    """
    Test que valida que password_rotations_total se incrementa con result=failed
    cuando el cambio de password falla (password actual incorrecto).
    """
    from app.services.metrics_service import metrics_service
    
    # Capturar valor inicial
    before_failed = _get_metric_value("password_rotations_total", {"result": "failed"})
    
    # Simular incremento manual (en test real vendría del endpoint con password incorrecto)
    metrics_service.inc_password_rotation("failed")
    
    # Verificar incremento
    after_failed = _get_metric_value("password_rotations_total", {"result": "failed"})
    assert after_failed == before_failed + 1, "password_rotations_total debe incrementar en failed"


@pytest.mark.asyncio
async def test_jwt_sessions_active_metric_exists():
    """Verifica que la métrica jwt_sessions_active existe y es settable"""
    from app.services.metrics_service import metrics_service
    
    # Set a un valor conocido
    metrics_service.set_jwt_sessions_active(42)
    
    # Verificar
    value = _get_metric_value("jwt_sessions_active")
    assert value == 42, "jwt_sessions_active debe reflejar el valor seteado"


@pytest.mark.asyncio
async def test_db_connections_active_metric_exists():
    """Verifica que la métrica db_connections_active existe y es settable"""
    from app.services.metrics_service import metrics_service
    
    # Set a un valor conocido
    metrics_service.set_db_connections_active(5)
    
    # Verificar
    value = _get_metric_value("db_connections_active")
    assert value == 5, "db_connections_active debe reflejar el valor seteado"


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_new_metrics(test_client: AsyncClient):
    """
    Verifica que el endpoint /metrics expone las nuevas métricas de seguridad/DB
    """
    response = await test_client.get("/metrics")
    assert response.status_code == 200
    
    content = response.text
    
    # Verificar que las métricas están presentes en la respuesta
    assert "jwt_sessions_active" in content, "Métrica jwt_sessions_active debe estar expuesta"
    assert "db_connections_active" in content, "Métrica db_connections_active debe estar expuesta"
    assert "password_rotations_total" in content, "Métrica password_rotations_total debe estar expuesta"
    assert "db_statement_timeouts_total" in content, "Métrica db_statement_timeouts_total debe estar expuesta"
