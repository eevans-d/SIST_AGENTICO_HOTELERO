import pytest

from app.services.orchestrator import Orchestrator
from app.services.session_manager import SessionManager
from app.services.lock_service import LockService
from tests.factories import unified_message


class _DummyPMS:
    pass


@pytest.mark.asyncio
async def test_image_without_pending_returns_reaction():
    orch = Orchestrator(_DummyPMS(), SessionManager(), LockService())
    msg = unified_message(tipo="image", texto=None, message_id="mid-1")

    result = await orch.handle_unified_message(msg)

    assert result["response_type"] == "reaction"
    assert result["content"]["message_id"] == "mid-1"
    assert result["content"]["emoji"] == "👍"


@pytest.mark.asyncio
async def test_payment_confirmation_with_qr_success(monkeypatch, tmp_path):
    sm = SessionManager()
    orch = Orchestrator(_DummyPMS(), sm, LockService())

    user_id = "user-qr"
    # Preparar sesión con reserva pendiente
    await sm.set_session_data(user_id, "reservation_pending", True)
    await sm.set_session_data(user_id, "guest_name", "Juan Perez")
    await sm.set_session_data(user_id, "check_in_date", "2025-11-01")
    await sm.set_session_data(user_id, "check_out_date", "2025-11-03")
    await sm.set_session_data(user_id, "room_number", "205")

    # Stub del servicio de QR
    class _StubQR:
        def generate_booking_qr(self, **kwargs):
            file_path = tmp_path / "qr.png"
            file_path.write_bytes(b"png")
            return {
                "success": True,
                "file_path": str(file_path),
                "qr_data": {"booking_id": "HTL-555"},
            }

    import app.services.qr_service as qr_module

    monkeypatch.setattr(qr_module, "get_qr_service", lambda: _StubQR(), raising=True)

    # Mensaje de imagen (comprobante)
    msg = unified_message(user_id=user_id, tipo="image", texto=None, message_id="mid-qr")

    res = await orch.handle_unified_message(msg)

    assert res["response_type"] == "image_with_text"
    assert isinstance(res.get("image_path"), str)
    # Debe incluir booking id del QR en el texto de confirmación
    assert "HTL-555" in res["content"]
