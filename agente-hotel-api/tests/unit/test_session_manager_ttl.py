import pytest
from app.services.session_manager import SessionManager, active_sessions


@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_create_updates_active_sessions_metric():
    sm = SessionManager()  # In-memory Redis fallback
    # Métrica inicial debería ser 0 o lo que esté; capturamos valor previo
    initial = active_sessions._value.get() if hasattr(active_sessions, "_value") else None

    s1 = await sm.get_or_create_session("user-a", canal="whatsapp")
    assert s1["user_id"] == "user-a"
    s2 = await sm.get_or_create_session("user-b", canal="gmail")
    assert s2["user_id"] == "user-b"

    # Después de dos sesiones activas el gauge debe reflejar >=2
    current = active_sessions._value.get()
    assert current >= 2
    if initial is not None:
        assert current >= initial


@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_update_preserves_core_fields_and_refreshes_last_activity():
    sm = SessionManager()
    session = await sm.get_or_create_session("user-x", canal="whatsapp")
    before_last_activity = session["last_activity"]

    # Modificar contexto y actualizar
    session["context"]["intent_history"] = ["check_availability"]
    await sm.update_session("user-x", session)

    # Recuperar y validar persistencia
    stored = await sm.get_session_data("user-x")
    assert stored["context"]["intent_history"] == ["check_availability"]
    assert stored["last_activity"] != before_last_activity

    # TTL en backend in-memory es fijo (600). Verificamos método ttl indirectamente
    # No accedemos a redis.ttl porque implementación in-memory devuelve 600 sin expiración real.
    # Aseguramos que la sesión sigue accesible y campos base intactos.
    assert stored["state"] == "initial"
    assert "created_at" in stored

