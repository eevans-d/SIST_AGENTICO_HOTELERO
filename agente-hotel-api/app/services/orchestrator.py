# [PROMPT 2.7] app/services/orchestrator.py

from .message_gateway import MessageGateway
from .nlp_engine import NLPEngine
from .audio_processor import AudioProcessor
from .pms_adapter import QloAppsAdapter
from .session_manager import SessionManager
from .lock_service import LockService
from .template_service import TemplateService
from ..models.unified_message import UnifiedMessage


class Orchestrator:
    def __init__(self, pms_adapter: QloAppsAdapter, session_manager: SessionManager, lock_service: LockService):
        self.pms_adapter = pms_adapter
        self.session_manager = session_manager
        self.lock_service = lock_service
        self.message_gateway = MessageGateway()
        self.nlp_engine = NLPEngine()
        self.audio_processor = AudioProcessor()
        self.template_service = TemplateService()

    async def handle_unified_message(self, message: UnifiedMessage) -> dict:
        if message.tipo == "audio":
            stt_result = await self.audio_processor.transcribe_whatsapp_audio(message.media_url)
            message.texto = stt_result["text"]
            message.metadata["confidence_stt"] = stt_result["confidence"]

        nlp_result = await self.nlp_engine.process_message(message.texto)
        session = await self.session_manager.get_or_create_session(message.user_id, message.canal)

        response_text = await self.handle_intent(nlp_result, session, message)

        return {"response": response_text}

    async def handle_intent(self, nlp_result: dict, session: dict, message: UnifiedMessage) -> str:
        intent = nlp_result.get("intent", {}).get("name")

        if intent == "check_availability":
            # Lógica para extraer entidades y llamar a pms_adapter.check_availability
            # ...
            return self.template_service.get_response(
                "availability_found",
                checkin="hoy",
                checkout="mañana",
                room_type="Doble",
                guests=2,
                price=10000,
                total=20000,
            )

        elif intent == "make_reservation":
            # Lógica para validar datos, llamar a lock_service.acquire_lock
            # ...
            return self.template_service.get_response(
                "reservation_instructions", deposit=6000, bank_info="CBU 12345..."
            )

        else:
            return "No entendí tu consulta. ¿Podrías reformularla?"
