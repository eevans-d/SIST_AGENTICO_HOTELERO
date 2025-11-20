import pytest

from app.services.session_manager import SessionManager


@pytest.mark.asyncio
async def test_set_and_get_session_data_top_level_and_context():
    sm = SessionManager()  # in-memory fallback
    user_id = "user-xyz"

    # set single field
    await sm.set_session_data(user_id, "reservation_pending", True)

    # fetch raw session
    session = await sm.get_session_data(user_id)

    # both top-level and context should reflect the value
    assert session.get("reservation_pending") is True
    assert session.get("context", {}).get("reservation_pending") is True

    # update entire session and ensure persistence
    session["some_key"] = "value"
    await sm.update_session(user_id, session)
    new_session = await sm.get_session_data(user_id)
    assert new_session.get("some_key") == "value"
