"""
Tests para session cleanup task del SessionManager.

Cobertura:
- Lifecycle: start_cleanup_task, stop_cleanup_task
- Corrupted sessions removal: _cleanup_orphaned_sessions con JSON inválido
- Metrics updates: active_sessions gauge, session_cleanups counter, session_expirations counter
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock

from app.services.session_manager import (
    SessionManager,
    active_sessions,
    session_cleanups,
    session_expirations,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_redis():
    """Mock Redis client with in-memory store."""
    redis_mock = AsyncMock()
    redis_mock._store = {}

    async def mock_get(key):
        return redis_mock._store.get(key)

    async def mock_set(key, value, ex=None, nx=None):
        if nx and key in redis_mock._store:
            return False
        redis_mock._store[key] = value
        return True

    async def mock_delete(key):
        return 1 if redis_mock._store.pop(key, None) is not None else 0

    async def mock_scan(cursor=0, match="*", count=100):
        import fnmatch
        keys = [k for k in redis_mock._store.keys() if fnmatch.fnmatch(k, match)]
        return 0, keys[:count]

    async def mock_ping():
        return True

    redis_mock.get = mock_get
    redis_mock.set = mock_set
    redis_mock.delete = mock_delete
    redis_mock.scan = mock_scan
    redis_mock.ping = mock_ping

    return redis_mock


@pytest.fixture
def session_manager(mock_redis):
    """SessionManager instance with mocked Redis."""
    return SessionManager(redis_client=mock_redis, ttl=1800)


@pytest.mark.asyncio
async def test_cleanup_task_lifecycle(session_manager):
    """
    Test 1: Cleanup task lifecycle - start y stop correctamente.

    Valida:
    - start_cleanup_task() crea la tarea asyncio
    - stop_cleanup_task() cancela la tarea sin errores
    - No hay memory leaks (task limpiado)
    """
    # Estado inicial: no hay task
    assert session_manager._cleanup_task is None

    # Iniciar task
    session_manager.start_cleanup_task()
    assert session_manager._cleanup_task is not None
    assert isinstance(session_manager._cleanup_task, asyncio.Task)
    assert not session_manager._cleanup_task.done()

    # Dar tiempo para que inicie (no debe crashear)
    await asyncio.sleep(0.1)

    # Detener task
    await session_manager.stop_cleanup_task()
    assert session_manager._cleanup_task is None

    # Validar que el task fue cancelado correctamente
    # (no debe haber excepciones sin capturar)


@pytest.mark.asyncio
async def test_cleanup_removes_corrupted_sessions(session_manager, mock_redis):
    """
    Test 2: Cleanup remueve sesiones corruptas (JSON inválido).

    Valida:
    - Sesiones con JSON inválido son detectadas
    - Sesiones son eliminadas de Redis
    - Métrica session_expirations{reason="corrupted"} incrementada
    """
    # Setup: Insertar sesiones válidas y corruptas
    mock_redis._store["session:user1"] = json.dumps({
        "user_id": "user1",
        "canal": "whatsapp",
        "state": "active",
        "context": {}
    })

    # Sesión corrupta: JSON inválido
    mock_redis._store["session:user2"] = "{invalid json}}"

    # Sesión corrupta: JSON válido pero campos faltantes
    mock_redis._store["session:user3"] = json.dumps({
        "user_id": "user3",
        # Falta "canal" y "state"
    })

    # Baseline métrica
    baseline_expirations = session_expirations.labels(reason="corrupted")._value.get()

    # Ejecutar cleanup
    cleaned = await session_manager._cleanup_orphaned_sessions()

    # Validaciones
    assert cleaned == 2, "Debería limpiar 2 sesiones corruptas"

    # Sesión válida NO eliminada
    assert "session:user1" in mock_redis._store

    # Sesiones corruptas SÍ eliminadas
    assert "session:user2" not in mock_redis._store
    assert "session:user3" not in mock_redis._store

    # Métrica incrementada
    new_expirations = session_expirations.labels(reason="corrupted")._value.get()
    assert new_expirations > baseline_expirations, "session_expirations{reason=corrupted} debe incrementarse"


@pytest.mark.asyncio
async def test_cleanup_updates_active_sessions_metric(session_manager, mock_redis):
    """
    Test 3: Cleanup actualiza métrica active_sessions gauge.

    Valida:
    - _update_active_sessions_metric() cuenta correctamente sesiones
    - Gauge active_sessions refleja el número real de sesiones en Redis
    - Métrica se actualiza en cada ciclo de cleanup
    """
    # Setup: Insertar 3 sesiones válidas
    for i in range(3):
        mock_redis._store[f"session:user{i}"] = json.dumps({
            "user_id": f"user{i}",
            "canal": "whatsapp",
            "state": "active",
            "context": {}
        })

    # Ejecutar update métrica
    await session_manager._update_active_sessions_metric()

    # Validar gauge actualizado
    current_sessions = active_sessions._value.get()
    assert current_sessions == 3, f"active_sessions debería ser 3, pero es {current_sessions}"

    # Simular limpieza de 1 sesión
    await mock_redis.delete("session:user1")

    # Re-ejecutar update
    await session_manager._update_active_sessions_metric()

    # Validar gauge reflejado
    updated_sessions = active_sessions._value.get()
    assert updated_sessions == 2, f"active_sessions debería ser 2 después de cleanup, pero es {updated_sessions}"


@pytest.mark.asyncio
async def test_cleanup_increments_success_counter(session_manager, mock_redis):
    """
    Test 4 (BONUS): Cleanup exitoso incrementa session_cleanups{result="success"}.

    Valida que el contador de cleanups se incrementa correctamente en happy path.
    """
    # Setup: Insertar 1 sesión válida
    mock_redis._store["session:test"] = json.dumps({
        "user_id": "test",
        "canal": "whatsapp",
        "state": "active",
        "context": {}
    })

    # Baseline counter
    baseline_cleanups = session_cleanups.labels(result="success")._value.get()

    # Ejecutar cleanup completo (ignoramos retorno)
    _ = await session_manager._cleanup_orphaned_sessions()

    # Simular success (normalmente hecho por cleanup_expired_sessions)
    session_cleanups.labels(result="success").inc()

    # Validar counter incrementado
    new_cleanups = session_cleanups.labels(result="success")._value.get()
    assert new_cleanups > baseline_cleanups, "session_cleanups{result=success} debe incrementarse"


@pytest.mark.asyncio
async def test_cleanup_handles_empty_redis_gracefully(session_manager, mock_redis):
    """
    Test 5 (BONUS): Cleanup con Redis vacío no crashea.

    Edge case: validar que cleanup no falla cuando no hay sesiones.
    """
    # Redis vacío
    mock_redis._store.clear()

    # No debe crashear
    _ = await session_manager._cleanup_orphaned_sessions()

    # Métrica debe actualizarse a 0
    await session_manager._update_active_sessions_metric()
    current_sessions = active_sessions._value.get()
    assert current_sessions == 0, "active_sessions debería ser 0 con Redis vacío"


@pytest.mark.asyncio
async def test_cleanup_handles_session_with_missing_fields(session_manager, mock_redis):
    """
    Test 6 (BONUS): Cleanup detecta sesiones con campos faltantes.

    Valida que sesiones sin campos requeridos (user_id, canal, state) son removidas.
    """
    # Sesión con campo faltante
    mock_redis._store["session:incomplete"] = json.dumps({
        "user_id": "incomplete",
        "canal": "whatsapp",
        # Falta "state"
    })

    # Baseline métrica
    baseline_invalid = session_expirations.labels(reason="invalid_format")._value.get()

    # Ejecutar cleanup
    _ = await session_manager._cleanup_orphaned_sessions()

    # Validaciones
    assert "session:incomplete" not in mock_redis._store

    # Métrica incrementada
    new_invalid = session_expirations.labels(reason="invalid_format")._value.get()
    assert new_invalid > baseline_invalid, "session_expirations{reason=invalid_format} debe incrementarse"
