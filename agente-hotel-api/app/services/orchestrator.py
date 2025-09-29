# [PROMPT 2.7] app/services/orchestrator.py

import time
from prometheus_client import Histogram, Counter
from .message_gateway import MessageGateway
from .nlp_engine import NLPEngine
from .audio_processor import AudioProcessor
from .session_manager import SessionManager
from .lock_service import LockService
from .template_service import TemplateService
from ..models.unified_message import UnifiedMessage
from .feature_flag_service import get_feature_flag_service
from .metrics_service import metrics_service


class Orchestrator:
    def __init__(self, pms_adapter, session_manager: SessionManager, lock_service: LockService):
        self.pms_adapter = pms_adapter
        self.session_manager = session_manager
        self.lock_service = lock_service
        self.message_gateway = MessageGateway()
        self.nlp_engine = NLPEngine()
        self.audio_processor = AudioProcessor()
        self.template_service = TemplateService()

    async def handle_unified_message(self, message: UnifiedMessage) -> dict:
        start = time.time()
        intent_name = "unknown"
        status = "ok"
        tenant_id = getattr(message, "tenant_id", None)
        if message.tipo == "audio":
            if not message.media_url:
                raise ValueError("Missing media_url for audio message")
            stt_result = await self.audio_processor.transcribe_whatsapp_audio(message.media_url)
            message.texto = stt_result["text"]
            message.metadata["confidence_stt"] = stt_result["confidence"]

        try:
            text = message.texto or ""
            nlp_result = await self.nlp_engine.process_message(text)
            intent_name = nlp_result.get("intent", {}).get("name", "unknown") or "unknown"
            session = await self.session_manager.get_or_create_session(message.user_id, message.canal, tenant_id)
            # Fallback dinámico según confianza + feature flag
            intent_obj = nlp_result.get("intent", {})
            confidence = intent_obj.get("confidence", 0.0)
            ff_service = await get_feature_flag_service()
            enhanced_fallback = await ff_service.is_enabled("nlp.fallback.enhanced", default=True)
            if enhanced_fallback and confidence < 0.45:
                # Respuesta de bajo nivel de confianza agresiva
                return {
                    "response": "No estoy seguro de haber entendido. ¿Puedes reformular o elegir una opción: disponibilidad, precios, información del hotel?"
                }
            elif enhanced_fallback and confidence < 0.75:
                message.metadata["low_confidence"] = True
            response_text = await self.handle_intent(nlp_result, session, message)
            return {"response": response_text}
        except Exception as e:
            status = "error"
            orchestrator_errors_total.labels(intent=intent_name, error_type=type(e).__name__).inc()
            if tenant_id:
                try:
                    metrics_service.inc_tenant_request(tenant_id, error=True)
                except Exception:  # pragma: no cover
                    pass
            raise
        finally:
            duration = time.time() - start
            orchestrator_latency.labels(intent=intent_name, status=status).observe(duration)
            orchestrator_messages_total.labels(intent=intent_name, status=status).inc()
            if tenant_id:
                try:
                    metrics_service.inc_tenant_request(tenant_id, error=(status != "ok"))
                except Exception:  # pragma: no cover
                    pass

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


# Prometheus metrics (module-level)
orchestrator_latency = Histogram(
    "orchestrator_latency_seconds",
    "Tiempo para procesar un mensaje unificado por intent y estado",
    ["intent", "status"],
)
orchestrator_messages_total = Counter(
    "orchestrator_messages_total", "Mensajes procesados por intent y estado", ["intent", "status"]
)
orchestrator_errors_total = Counter(
    "orchestrator_errors_total", "Errores no controlados por intent y tipo", ["intent", "error_type"]
)
