"""
Tests de robustez para SessionManager con retry logic.

Valida:
- Retry con exponential backoff en fallos de Redis
- Manejo de ConnectionError, TimeoutError
- Fallo después de MAX_RETRIES_DEFAULT intentos
- Delays correctos (1s, 2s, 4s)
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError
from app.services.session_manager import SessionManager
from app.core.constants import MAX_RETRIES_DEFAULT, RETRY_DELAY_BASE


@pytest.mark.asyncio
async def test_update_session_retries_on_connection_error():
    """
    Debe reintentar 3 veces en ConnectionError y completar en el 3er intento.
    
    Escenario:
    - 1er intento: ConnectionError
    - 2do intento: ConnectionError  
    - 3er intento: Éxito
    
    Resultado esperado:
    - No debe lanzar excepción
    - Debe completar exitosamente
    - Redis.set debe ser llamado 3 veces
    """
    redis_mock = AsyncMock()
    redis_mock.set.side_effect = [
        RedisConnectionError("Connection lost"),
        RedisConnectionError("Connection lost"),
        None,  # Tercer intento exitoso
    ]
    
    session_manager = SessionManager(
        redis_mock,
        max_retries=3,
        retry_delay_base=0.01,  # Delays rápidos para testing
    )
    
    # No debe fallar, debe completar en el 3er intento
    await session_manager.update_session(
        "user123",
        {"state": "test", "canal": "whatsapp"},
        tenant_id="hotel_abc"
    )
    
    assert redis_mock.set.call_count == 3, "Debe intentar 3 veces antes de éxito"


@pytest.mark.asyncio
async def test_update_session_fails_after_max_retries():
    """
    Debe fallar después de MAX_RETRIES_DEFAULT intentos.
    
    Escenario:
    - Todos los intentos fallan con ConnectionError
    
    Resultado esperado:
    - Debe lanzar RedisConnectionError
    - Redis.set debe ser llamado MAX_RETRIES_DEFAULT veces
    """
    redis_mock = AsyncMock()
    redis_mock.set.side_effect = RedisConnectionError("Persistent failure")
    
    session_manager = SessionManager(
        redis_mock,
        max_retries=3,
        retry_delay_base=0.01,
    )
    
    with pytest.raises(RedisConnectionError, match="Persistent failure"):
        await session_manager.update_session(
            "user123",
            {"state": "test", "canal": "whatsapp"}
        )
    
    assert redis_mock.set.call_count == 3, f"Debe intentar {MAX_RETRIES_DEFAULT} veces"


@pytest.mark.asyncio
async def test_exponential_backoff_delays():
    """
    Debe usar delays exponenciales: 1s, 2s, 4s.
    
    Con retry_delay_base=0.01:
    - 1er retry: 0.01s delay
    - 2do retry: 0.02s delay
    Total mínimo: 0.03s
    
    Resultado esperado:
    - Tiempo total >= 0.03s
    - Tiempo total < 0.1s (con margen de error)
    """
    redis_mock = AsyncMock()
    redis_mock.set.side_effect = [
        RedisConnectionError(),
        RedisConnectionError(),
        None,  # Éxito en 3er intento
    ]
    
    session_manager = SessionManager(
        redis_mock,
        max_retries=3,
        retry_delay_base=0.01,  # 10ms base
    )
    
    start = time.time()
    
    await session_manager.update_session(
        "user123",
        {"state": "test", "canal": "whatsapp"}
    )
    
    elapsed = time.time() - start
    
    # Delays: 0.01 + 0.02 = 0.03s (con margen de error del sistema)
    assert 0.02 < elapsed < 0.1, f"Elapsed time {elapsed}s debe estar entre 0.02-0.1s"
    assert redis_mock.set.call_count == 3


@pytest.mark.asyncio
async def test_timeout_error_triggers_retry():
    """
    TimeoutError debe activar retry logic igual que ConnectionError.
    
    Escenario:
    - 1er intento: TimeoutError
    - 2do intento: Éxito
    
    Resultado esperado:
    - No debe fallar
    - Debe completar en 2do intento
    """
    redis_mock = AsyncMock()
    redis_mock.set.side_effect = [
        RedisTimeoutError("Timeout"),
        None,  # Éxito
    ]
    
    session_manager = SessionManager(
        redis_mock,
        max_retries=3,
        retry_delay_base=0.01,
    )
    
    await session_manager.update_session(
        "user123",
        {"state": "test", "canal": "whatsapp"}
    )
    
    assert redis_mock.set.call_count == 2


@pytest.mark.asyncio
async def test_create_session_retries_on_failure():
    """
    get_or_create_session debe reintentar al crear nueva sesión.
    
    Escenario:
    - No existe sesión previa (get devuelve None)
    - 1er intento de crear: ConnectionError
    - 2do intento: Éxito
    
    Resultado esperado:
    - Debe devolver la sesión creada
    - Redis.set debe ser llamado 2 veces
    """
    redis_mock = AsyncMock()
    redis_mock.get.return_value = None  # No existe sesión
    redis_mock.set.side_effect = [
        RedisConnectionError("Connection lost"),
        None,  # Éxito
    ]
    
    session_manager = SessionManager(
        redis_mock,
        max_retries=3,
        retry_delay_base=0.01,
    )
    
    session = await session_manager.get_or_create_session(
        user_id="user123",
        canal="whatsapp",
        tenant_id="hotel_abc"
    )
    
    assert session is not None
    assert session["user_id"] == "user123"
    assert session["canal"] == "whatsapp"
    assert redis_mock.set.call_count == 2


@pytest.mark.asyncio
async def test_successful_operation_no_retry():
    """
    Operación exitosa en 1er intento no debe reintentar.
    
    Resultado esperado:
    - Redis.set llamado solo 1 vez
    - Sin delays
    """
    redis_mock = AsyncMock()
    redis_mock.set.return_value = None  # Éxito inmediato
    
    session_manager = SessionManager(
        redis_mock,
        max_retries=3,
        retry_delay_base=0.01,
    )
    
    start = time.time()
    
    await session_manager.update_session(
        "user123",
        {"state": "test", "canal": "whatsapp"}
    )
    
    elapsed = time.time() - start
    
    assert redis_mock.set.call_count == 1, "Solo debe intentar 1 vez en éxito"
    assert elapsed < 0.02, "No debe haber delays en operación exitosa"


@pytest.mark.asyncio
async def test_get_existing_session_no_retry_needed():
    """
    get_or_create_session no debe reintentar si sesión ya existe.
    
    Escenario:
    - Sesión existe (get devuelve datos)
    
    Resultado esperado:
    - Redis.get llamado 1 vez
    - Redis.set NO llamado (no crea nueva sesión)
    """
    redis_mock = AsyncMock()
    existing_session = '{"user_id": "user123", "canal": "whatsapp", "state": "existing"}'
    redis_mock.get.return_value = existing_session
    
    session_manager = SessionManager(redis_mock)
    
    session = await session_manager.get_or_create_session(
        user_id="user123",
        canal="whatsapp"
    )
    
    assert session["state"] == "existing"
    assert redis_mock.get.call_count == 1
    assert redis_mock.set.call_count == 0, "No debe crear nueva sesión si ya existe"


@pytest.mark.asyncio
async def test_concurrent_retries_independent():
    """
    Múltiples operaciones concurrentes deben tener retry logic independiente.
    
    Escenario:
    - 2 operaciones paralelas de update_session
    - Una falla 2 veces, otra falla 1 vez
    
    Resultado esperado:
    - Ambas deben completar
    - Cada una con su propio contador de reintentos
    """
    redis_mock = AsyncMock()
    
    # Tracking de llamadas para cada operación
    call_count_user1 = 0
    call_count_user2 = 0
    
    async def set_side_effect(key, value, ex):
        nonlocal call_count_user1, call_count_user2
        
        if "user1" in key:
            call_count_user1 += 1
            if call_count_user1 < 3:  # Falla 2 veces
                raise RedisConnectionError("Fail user1")
        else:  # user2
            call_count_user2 += 1
            if call_count_user2 < 2:  # Falla 1 vez
                raise RedisConnectionError("Fail user2")
        
        return None  # Éxito
    
    redis_mock.set.side_effect = set_side_effect
    
    session_manager = SessionManager(
        redis_mock,
        max_retries=3,
        retry_delay_base=0.01,
    )
    
    # Ejecutar en paralelo
    await asyncio.gather(
        session_manager.update_session("user1", {"state": "test1", "canal": "whatsapp"}),
        session_manager.update_session("user2", {"state": "test2", "canal": "whatsapp"}),
    )
    
    assert call_count_user1 == 3, "user1 debe intentar 3 veces"
    assert call_count_user2 == 2, "user2 debe intentar 2 veces"


@pytest.mark.asyncio
async def test_retry_updates_last_activity_timestamp():
    """
    Cada retry debe actualizar el timestamp de last_activity.
    
    Resultado esperado:
    - last_activity debe estar actualizado al tiempo final
    - No debe usar timestamp del primer intento
    """
    redis_mock = AsyncMock()
    redis_mock.set.side_effect = [
        RedisConnectionError(),
        None,  # Éxito en 2do intento
    ]
    
    session_manager = SessionManager(
        redis_mock,
        max_retries=3,
        retry_delay_base=0.05,  # 50ms delay para ver diferencia en timestamp
    )
    
    session_data = {"state": "test", "canal": "whatsapp", "last_activity": "2024-01-01T00:00:00"}
    
    await session_manager.update_session("user123", session_data)
    
    # Verificar que last_activity fue actualizado
    assert "last_activity" in session_data
    assert session_data["last_activity"] != "2024-01-01T00:00:00", \
        "last_activity debe actualizarse en cada intento"
