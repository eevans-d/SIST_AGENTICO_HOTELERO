"""
Tests de integración para métricas de seguridad y database.

Estos tests verifican que las métricas están correctamente definidas e instrumentadas,
sin depender de valores específicos en runtime (que requieren background tasks activos).
"""
import pytest


@pytest.mark.asyncio
async def test_security_metrics_are_defined():
    """
    Verifica que todas las métricas de seguridad están definidas en metrics_service.
    
    Este test importa directamente el servicio y verifica que los objetos métrica existen.
    """
    from app.services.metrics_service import metrics_service
    
    # Verificar que las métricas existen como atributos
    assert hasattr(metrics_service, "jwt_sessions_active"), "jwt_sessions_active debe estar definida"
    assert hasattr(metrics_service, "db_connections_active"), "db_connections_active debe estar definida"
    assert hasattr(metrics_service, "password_rotations_total"), "password_rotations_total debe estar definida"
    assert hasattr(metrics_service, "db_statement_timeouts_total"), "db_statement_timeouts_total debe estar definida"
    
    # Verificar que los helpers existen
    assert hasattr(metrics_service, "set_jwt_sessions_active"), "Helper set_jwt_sessions_active debe existir"
    assert hasattr(metrics_service, "set_db_connections_active"), "Helper set_db_connections_active debe existir"
    assert hasattr(metrics_service, "inc_password_rotation"), "Helper inc_password_rotation debe existir"


@pytest.mark.asyncio
async def test_password_rotation_metric_instrumentation():
    """
    Verifica que el endpoint /change-password está instrumentado con password_rotations_total.
    
    Este test verifica que el código de instrumentación está presente leyendo el archivo fuente.
    """
    # Leer el archivo fuente directamente para evitar imports de dependencias opcionales
    with open("app/routers/security.py", "r") as f:
        source = f.read()
    
    assert "inc_password_rotation" in source, "/change-password debe llamar a inc_password_rotation"
    assert 'inc_password_rotation("success")' in source or 'inc_password_rotation(result="success")' in source
    assert 'inc_password_rotation("failed")' in source or 'inc_password_rotation(result="failed")' in source


@pytest.mark.asyncio
async def test_background_tasks_implementation():
    """
    Verifica que app/main.py tiene implementación de background tasks para actualizar métricas.
    """
    # Leer el archivo fuente directamente
    with open("app/main.py", "r") as f:
        source = f.read()
    
    # Verificar que los background tasks están definidos
    assert "_update_jwt_sessions_periodically" in source, "Background task para JWT sessions debe existir"
    assert "_update_db_connections_periodically" in source, "Background task para DB connections debe existir"
    
    # Verificar que se crean con asyncio.create_task
    assert "asyncio.create_task(_update_jwt_sessions_periodically())" in source or "create_task(_update_jwt_sessions_periodically" in source
    assert "asyncio.create_task(_update_db_connections_periodically())" in source or "create_task(_update_db_connections_periodically" in source
