import pytest
import pytest_asyncio

from app.services.lock_service import LockService
from app.models.lock_audit import LockAudit

# Marcar todo el módulo como pruebas unitarias para que sea recogido por el filtro de markers
pytestmark = pytest.mark.unit

# NOTA: Estos tests validan que _audit_lock_event se invoca y NO bloquea la operación
# aunque falle el commit. No verificamos persistencia real porque la factory AsyncSessionFactory
# crea sesiones contra la configuración global (en tests se usa SQLite in-memory normalmente).

@pytest_asyncio.fixture
async def lock_service():
    # Usa el Redis in-memory embebido en la clase para aislar pruebas
    return LockService()

@pytest.mark.asyncio
async def test_acquire_lock_creates_audit_entry(monkeypatch, lock_service):
    """Verifica que adquirir un lock exitoso dispara auditoría con event_type 'acquired'."""
    added_entries = []

    class DummySession:
        def __init__(self):
            self.committed = False
        def add(self, obj):
            added_entries.append(obj)
        async def commit(self):
            self.committed = True
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass

    monkeypatch.setattr("app.services.lock_service.AsyncSessionFactory", lambda: DummySession())

    lock_key = await lock_service.acquire_lock(
        room_id="101", check_in="2025-01-01T00:00:00+00:00", check_out="2025-01-03T00:00:00+00:00",
        session_id="sess-1", user_id="user-1", ttl=60
    )

    assert lock_key is not None, "Debe adquirir lock"
    # Debe haber registrado auditoría con event_type acquired
    assert any(isinstance(e, LockAudit) and e.event_type == "acquired" for e in added_entries), "No se registró auditoría 'acquired'"

@pytest.mark.asyncio
async def test_conflict_records_audit_event(monkeypatch, lock_service):
    """Conflicto al adquirir segundo lock sobre mismas fechas debe generar auditoría 'conflict'."""
    events = []

    class DummySession:
        def add(self, obj):
            events.append(obj)
        async def commit(self):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass

    monkeypatch.setattr("app.services.lock_service.AsyncSessionFactory", lambda: DummySession())

    # Primer lock exitoso
    first = await lock_service.acquire_lock(
        room_id="202", check_in="2025-02-01T00:00:00+00:00", check_out="2025-02-05T00:00:00+00:00",
        session_id="s-A", user_id="u-A", ttl=30
    )
    assert first is not None

    # Segundo lock con solapamiento debe fallar y registrar conflicto
    second = await lock_service.acquire_lock(
        room_id="202", check_in="2025-02-02T00:00:00+00:00", check_out="2025-02-04T00:00:00+00:00",
        session_id="s-B", user_id="u-B", ttl=30
    )
    assert second is None, "Debe detectar conflicto"

    assert any(isinstance(e, LockAudit) and e.event_type == "conflict" for e in events), "No se registró auditoría 'conflict'"

@pytest.mark.asyncio
async def test_audit_failure_does_not_break_lock(monkeypatch, lock_service, caplog):
    """Si la auditoría lanza excepción, la adquisición del lock no debe romperse (retorna key)."""

    class FailingSession:
        def add(self, obj):
            pass
        async def commit(self):
            raise RuntimeError("DB down")
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass

    monkeypatch.setattr("app.services.lock_service.AsyncSessionFactory", lambda: FailingSession())

    lock_key = await lock_service.acquire_lock(
        room_id="303", check_in="2025-03-01T00:00:00+00:00", check_out="2025-03-02T00:00:00+00:00",
        session_id="sess-X", user_id="user-X", ttl=45
    )

    assert lock_key is not None, "La operación principal no debe fallar aunque falle auditoría"
    # Verificar que se logueó el error
    assert any("audit_failed" in r.message for r in caplog.records), "Debe loguear fallo de auditoría"
