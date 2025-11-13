import pytest
from app.services.orchestrator import Orchestrator
from app.models.unified_message import UnifiedMessage


class DummyPMSAdapter:
    async def check_availability(self, *args, **kwargs):
        return {"rooms_available": 2}


@pytest.mark.asyncio
async def test_process_message_basic_availability(monkeypatch):
    """Happy path mínimo: mensaje de disponibilidad produce respuesta tipo text."""
    # Construir dependencias mínimas
    from app.services.session_manager import SessionManager
    from app.services.lock_service import LockService

    session_manager = SessionManager()  # usa Redis in-memory fallback
    lock_service = LockService()  # asumido simple para test
    orchestrator = Orchestrator(DummyPMSAdapter(), session_manager, lock_service)

    msg = UnifiedMessage(user_id="u1", canal="whatsapp", texto="¿Hay disponibilidad de habitaciones?", tipo="text")

    result = await orchestrator.process_message(msg)

    # La implementación puede devolver texto puro o texto con imagen; aceptamos ambos para el básico
    assert getattr(result, "response_type", None) in {"text", "text_with_image"}
    assert isinstance(getattr(result, "content", None), str)
    assert len(result.content) > 0
