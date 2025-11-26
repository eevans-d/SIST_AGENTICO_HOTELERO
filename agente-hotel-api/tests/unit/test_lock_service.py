import pytest
from unittest.mock import patch, AsyncMock
from app.services.lock_service import LockService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lock_acquire_and_conflict_detection():
    """Verifica detección de conflictos de rangos de fechas para la misma habitación."""
    service = LockService()  # In-memory Redis fallback
    # Mock the audit function to avoid DB calls
    service._audit_lock_event = AsyncMock()

    key1 = await service.acquire_lock(
        room_id="101",
        check_in="2025-11-10T12:00:00Z",
        check_out="2025-11-12T12:00:00Z",
        session_id="s1",
        user_id="u1",
    )
    assert key1 is not None

    # Rango solapado → conflict
    key2 = await service.acquire_lock(
        room_id="101",
        check_in="2025-11-11T12:00:00Z",
        check_out="2025-11-13T12:00:00Z",
        session_id="s2",
        user_id="u2",
    )
    assert key2 is None

    # Rango que empieza exactamente cuando termina el anterior → debe permitir
    key3 = await service.acquire_lock(
        room_id="101",
        check_in="2025-11-12T12:00:00Z",
        check_out="2025-11-14T12:00:00Z",
        session_id="s3",
        user_id="u3",
    )
    assert key3 is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lock_extension_and_release():
    """Valida extensiones máximas y liberación de lock."""
    service = LockService()
    # Mock the audit function to avoid DB calls
    service._audit_lock_event = AsyncMock()
    
    key = await service.acquire_lock(
        room_id="202",
        check_in="2025-11-15T10:00:00Z",
        check_out="2025-11-16T10:00:00Z",
        session_id="sx",
        user_id="ux",
    )
    assert key is not None

    assert await service.extend_lock(key) is True
    assert await service.extend_lock(key) is True
    assert await service.extend_lock(key) is False  # max extensions

    assert await service.release_lock(key) is True
    assert await service.release_lock(key) is False  # ya liberado



    # (TTL avanzado y pruebas de concurrencia se cubrirán en otra suite si se requiere.)
