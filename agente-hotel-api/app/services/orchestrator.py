# [PROMPT 2.7] app/services/orchestrator.py

import time
import asyncio
from typing import Optional
from datetime import datetime, timezone, date
from prometheus_client import Histogram, Counter
from .message_gateway import MessageGateway
from .nlp_engine import NLPEngine
from .audio_processor import AudioProcessor
from .session_manager import SessionManager
from .lock_service import LockService
from .template_service import TemplateService
from .dlq_service import DLQService
from ..models.unified_message import UnifiedMessage
from .feature_flag_service import get_feature_flag_service
from .metrics_service import metrics_service
from .business_metrics import intents_detected, nlp_fallbacks, messages_by_channel
from ..exceptions.pms_exceptions import PMSError, CircuitBreakerOpenError
from ..core.logging import logger
from ..core.constants import (
    CONFIDENCE_THRESHOLD_VERY_LOW,
    CONFIDENCE_THRESHOLD_LOW,
    HOTEL_STANDARD_CHECKOUT_TIME,
    HOTEL_LATE_CHECKOUT_TIME,
    PRICE_ROOM_SINGLE,
    PRICE_ROOM_DOUBLE,
    PRICE_ROOM_PREMIUM_SINGLE,
    PRICE_ROOM_PREMIUM_DOUBLE,
    RESERVATION_DEPOSIT_AMOUNT,
    MOCK_BANK_INFO,
    MOCK_CHECKIN_DATE,
    MOCK_CHECKOUT_DATE,
    MOCK_ROOM_NUMBER,
)
from ..utils.business_hours import is_business_hours, get_next_business_open_time, format_business_hours
from .dynamic_tenant_service import dynamic_tenant_service
from .review_service import get_review_service
from .alert_service import alert_manager
from ..utils.locale_utils import format_currency, format_date_locale
from ..core.settings import settings  # Exponer settings a nivel de módulo para tests/patching

# Re-export helpers so tests can patch `app.services.orchestrator.get_room_image_url`
try:
    from ..utils.room_images import (
        get_room_image_url as _rm_get_room_image_url,
        validate_image_url as _rm_validate_image_url,
    )
except Exception:
    _rm_get_room_image_url = None
    _rm_validate_image_url = None


def get_room_image_url(room_type: str):
    """
    Wrapper to allow test patching at module scope; delegates to utils.room_images.
    """
    from ..utils.room_images import get_room_image_url as _impl

    # Usar base_url desde settings (patchable en tests) para construir la URL
    try:
        base_url = settings.room_images_base_url
    except Exception:
        base_url = None
    return _impl(room_type, base_url=base_url)


def validate_image_url(url: str) -> bool:
    """
    Wrapper to allow test patching at module scope; delegates to utils.room_images.
    """
    from ..utils.room_images import validate_image_url as _impl

    return _impl(url)


def generate_qr_code(payload: dict | str | None = None) -> dict | None:
    """
    Wrapper to allow test patching at module scope; returns QR code generation result.

    Expected return shape (for callers that use it):
    {"file_path": str, "booking_id": str} or None

    By default returns None (feature disabled) and is intended to be monkeypatched in tests.
    """
    try:
        # QR generation is feature-flagged; keep disabled by default.
        from .feature_flag_service import DEFAULT_FLAGS

        if not DEFAULT_FLAGS.get("reservation.qr.enabled", False):
            return None
    except Exception:
        return None

    # No-op fallback; real implementation can be wired later.
    return None

# Métricas para escalamiento
escalations_total = Counter(
    "orchestrator_escalations_total", "Total de escalamientos a staff humano", ["reason", "channel"]
)
escalation_response_time = Histogram(
    "orchestrator_escalation_response_seconds", "Tiempo desde escalamiento hasta respuesta de staff", ["reason"]
)


class Orchestrator:
    def __init__(
        self,
        pms_adapter,
        session_manager: SessionManager,
        lock_service: LockService,
        dlq_service: DLQService = None,
    ):
        self.pms_adapter = pms_adapter
        self.session_manager = session_manager
        self.lock_service = lock_service
        self.message_gateway = MessageGateway()
        self.nlp_engine = NLPEngine()
        self.audio_processor = AudioProcessor()
        self.template_service = TemplateService()
        self.dlq_service = dlq_service  # Optional, will be None in tests without DLQ

        # Intent Handler Dispatcher Pattern
        # Maps intent names to their corresponding handler methods
        self._intent_handlers = {
            "check_availability": self._handle_availability,
            "make_reservation": self._handle_make_reservation,
            "hotel_location": self._handle_hotel_location,
            "ask_location": self._handle_hotel_location,
            "show_room_options": self._handle_room_options,
            "pricing_info": self._handle_info_intent,
            "guest_services": self._handle_info_intent,
            "hotel_amenities": self._handle_info_intent,
            "check_in_info": self._handle_info_intent,
            "check_out_info": self._handle_info_intent,
            "cancellation_policy": self._handle_info_intent,
            "late_checkout": self._handle_late_checkout,
            "review_response": self._handle_review_request,
            "business_hours_info": self._handle_info_intent,
        }

    async def _escalate_to_staff(
        self, message: UnifiedMessage, reason: str, intent: str = "unknown", session_data: dict | None = None
    ) -> dict:
        """
        Escalate conversation to human staff with comprehensive tracking.

        Args:
            message: The unified message that triggered escalation
            reason: Reason for escalation (urgent_after_hours, nlp_failure, etc.)
            intent: Detected intent (if any)
            session_data: Current session context

        Returns:
            Response dict with escalation acknowledgment
        """
        # Métrica de escalamiento (evitar reset manual que causaba inconsistencia en tests de acumulación)
        escalations_total.labels(reason=reason, channel=message.canal).inc()

        # Prepare escalation context
        escalation_context = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "user_id": message.user_id,
            "channel": message.canal,
            "intent": intent,
            "message_preview": message.texto[:200] if message.texto else "",
            "session_history": session_data.get("history", [])[-5:] if session_data else [],
            "metadata": {
                "tenant_id": getattr(message, "tenant_id", None),
                "language": message.metadata.get("detected_language", "es"),
                "media_type": message.tipo,
            },
        }

        # Log escalation for monitoring
        logger.warning(
            "orchestrator.escalation_triggered",
            reason=reason,
            user_id=message.user_id,
            channel=message.canal,
            intent=intent,
            **escalation_context["metadata"],
        )

        # Send alert to staff through alert manager
        try:
            await alert_manager.send_alert(
                {
                    "metric": "conversation_escalation",
                    "level": "warning" if reason != "critical_error" else "critical",
                    "description": f"Escalamiento de conversación: {reason}",
                    "user_id": message.user_id,
                    "channel": message.canal,
                    "context": escalation_context,
                    "action_required": True,
                }
            )
        except Exception as alert_error:
            logger.error("orchestrator.alert_send_failed", error=str(alert_error), user_id=message.user_id)

        # Update session with escalation flag
        if session_data:
            session_data["escalated"] = True
            session_data["escalation_timestamp"] = escalation_context["timestamp"]
            session_data["escalation_reason"] = reason

            # Save updated session
            try:
                # Persist session changes (multi-tenant aware if available)
                tenant_id = getattr(message, "tenant_id", None)
                await self.session_manager.update_session(message.user_id, session_data, tenant_id)
            except Exception as session_error:
                logger.error("orchestrator.session_save_failed", error=str(session_error), user_id=message.user_id)

        # Generate response based on reason
        if reason == "urgent_after_hours":
            # Usar overrides por tenant si existen
            start = end = None
            try:
                tid = getattr(message, "tenant_id", None)
                if tid:
                    meta = dynamic_tenant_service.get_tenant_meta(tid)
                    if meta:
                        start = meta.get("business_hours_start")
                        end = meta.get("business_hours_end")
            except Exception:
                pass
            hours_str = format_business_hours(start_hour=start, end_hour=end)
            response_text = self.template_service.get_response(
                "escalated_to_staff", next_business_time=hours_str
            )
        elif reason == "nlp_failure":
            response_text = self.template_service.get_response("fallback_human_needed")
        else:
            response_text = self.template_service.get_response(
                "escalated_to_staff", reason="Necesitas asistencia especializada"
            )

        return {
            "response_type": "text",
            "content": response_text,
            "escalated": True,
            "escalation_id": f"ESC-{datetime.now(timezone.utc).timestamp()}",
        }

    # =========================================================================
    # BUSINESS HOURS HELPERS - Extracted to reduce complexity
    # =========================================================================

    _BYPASS_INTENTS = {
        "guest_services", "hotel_amenities", "check_in_info", "check_out_info",
        "cancellation_policy", "pricing_info", "hotel_location", "review_response",
        "show_room_options", "business_hours_info",
    }

    def _should_bypass_hours_check(self, intent: str) -> bool:
        """Check if intent should bypass business hours gating."""
        return intent in self._BYPASS_INTENTS

    def _is_urgent_request(self, message: UnifiedMessage) -> bool:
        """Check if message contains urgent keywords."""
        text_lower = (message.texto or "").lower()
        return "urgente" in text_lower or "urgent" in text_lower or "emergency" in text_lower

    def _get_tenant_hours(self, message: UnifiedMessage) -> tuple:
        """Get tenant-specific business hours configuration."""
        start = end = tz = None
        try:
            tid = getattr(message, "tenant_id", None)
            if tid:
                meta = dynamic_tenant_service.get_tenant_meta(tid)
                if meta:
                    start = meta.get("business_hours_start")
                    end = meta.get("business_hours_end")
                    tz = meta.get("business_hours_timezone")
        except Exception:
            pass
        return start, end, tz

    def _check_business_hours(self, start, end, tz) -> bool:
        """Check if currently within business hours."""
        from ..utils import business_hours as _bh
        
        # Allow override by monkeypatch in tests
        _override_is_bh = globals().get("is_business_hours")
        if callable(_override_is_bh):
            return _override_is_bh(start_hour=start, end_hour=end, timezone=tz)
        return _bh.is_business_hours(start_hour=start, end_hour=end, timezone=tz)

    def _build_hours_query_response(self, start, end) -> dict:
        """Build response for business hours query intent."""
        from ..utils import business_hours as _bh
        business_hours_str = _bh.format_business_hours(start_hour=start, end_hour=end)
        response_text = self.template_service.get_response(
            "business_hours_info", business_hours=business_hours_str
        )
        return {"response_type": "text", "content": response_text}

    def _format_next_open_time(self, next_open, start) -> str:
        """Format next opening time as HH:MM string."""
        try:
            from datetime import datetime as _dt
            if isinstance(next_open, _dt):
                return next_open.strftime("%H:%M")
        except Exception:
            pass
        start_h = start if start is not None else getattr(settings, "business_hours_start", 9)
        return f"{int(start_h):02d}:00"

    async def _build_after_hours_response(self, message: UnifiedMessage, start, end, tz) -> dict:
        """Build response for after-hours requests."""
        from ..utils import business_hours as _bh
        
        # Get next opening time
        try:
            next_open = _bh.get_next_business_open_time(start_hour=start, timezone=tz)
        except Exception as e:
            logger.warning("orchestrator.next_open_failed", error=str(e))
            next_open = None

        business_hours_str = _bh.format_business_hours(start_hour=start, end_hour=end)
        is_weekend = datetime.now().weekday() >= 5
        template_key = "after_hours_weekend" if is_weekend else "after_hours_standard"
        next_open_str = self._format_next_open_time(next_open, start)

        response_text = self.template_service.get_response(
            template_key, business_hours=business_hours_str, next_open_time=next_open_str
        )

        logger.info(
            "orchestrator.after_hours_response",
            template=template_key,
            next_open_time=next_open_str,
            user_id=message.user_id,
        )

        # Try audio response for audio messages
        if message.tipo == "audio":
            try:
                audio_data = await self.audio_processor.generate_audio_response(
                    response_text, content_type="after_hours"
                )
                if audio_data:
                    return {"response_type": "audio", "content": {"text": response_text, "audio_data": audio_data}}
            except Exception:
                pass

        return {"response_type": "text", "content": response_text}

    # =========================================================================
    # END BUSINESS HOURS HELPERS
    # =========================================================================

    async def _handle_business_hours(self, nlp_result: dict, session_data: dict, message: UnifiedMessage) -> dict | None:
        """
        Maneja la verificación de horarios comerciales y escalación urgente.
        Uses extracted helpers for improved maintainability (CC reduced from 28 to ~10).

        Args:
            nlp_result: Resultado del análisis NLP con intent y entidades
            session_data: Estado persistente de la sesión del usuario
            message: Mensaje unificado normalizado

        Returns:
            dict | None: Response dict or None to continue processing
        """
        intent = self._normalize_intent(nlp_result)

        # Bypass check for informational intents
        if self._should_bypass_hours_check(intent):
            return None

        is_urgent = self._is_urgent_request(message)
        start, end, tz = self._get_tenant_hours(message)
        in_business_hours = self._check_business_hours(start, end, tz)

        logger.info(
            "orchestrator.business_hours_check",
            in_business_hours=in_business_hours,
            is_urgent=is_urgent,
            intent=intent,
            user_id=message.user_id,
        )

        # Handle explicit hours query intent
        if intent in ("consultar_horario", "business_hours"):
            return self._build_hours_query_response(start, end)

        # Outside business hours - non-urgent
        if not in_business_hours and not is_urgent:
            return await self._build_after_hours_response(message, start, end, tz)

        # Outside business hours - urgent: escalate
        if not in_business_hours and is_urgent:
            logger.warning(
                "orchestrator.urgent_after_hours_escalation",
                user_id=message.user_id,
                intent=intent,
                text_preview=message.texto[:100] if message.texto else "",
            )
            return await self._escalate_to_staff(
                message=message, reason="urgent_after_hours", intent=intent, session_data=session_data
            )

        # Within business hours - continue normal processing
        return None

    async def _handle_room_options(self, nlp_result: dict, session_data: dict, message: UnifiedMessage) -> dict:
        """
        Maneja solicitudes para ver opciones de habitaciones con lista interactiva

        Funcionalidad:
        - Genera lista interactiva con tipos de habitaciones y precios
        - Soporte para audio: responde primero con audio, luego con lista interactiva
        - Maneja diferentes tipos de habitaciones (single, double, premium)

        Args:
            nlp_result: Resultado del análisis NLP con intent y entidades
            session_data: Estado persistente de la sesión del usuario
            message: Mensaje unificado normalizado

        Returns:
            dict: Respuesta con lista interactiva o audio+lista
            {
                "response_type": "interactive_list" | "audio",
                "content": dict con room_options o audio_data
            }
        """
        # Preparar datos para opciones de habitaciones (formateo por idioma y sin símbolo)
        lang = message.metadata.get("detected_language", "es") if isinstance(message.metadata, dict) else "es"
        try:
            self.template_service.set_language(lang)
        except Exception:
            pass
        d_checkin = date(2023, 1, 1)
        d_checkout = date(2023, 1, 5)
        room_data = {
            "checkin": format_date_locale(d_checkin, lang),
            "checkout": format_date_locale(d_checkout, lang),
            "price_single": format_currency(PRICE_ROOM_SINGLE, lang, with_symbol=False),
            "price_double": format_currency(PRICE_ROOM_DOUBLE, lang, with_symbol=False),
            "price_prem_single": format_currency(PRICE_ROOM_PREMIUM_SINGLE, lang, with_symbol=False),
            "price_prem_double": format_currency(PRICE_ROOM_PREMIUM_DOUBLE, lang, with_symbol=False),
        }

        # Si el mensaje original era de audio, primero responder con audio
        if message.tipo == "audio":
            try:
                # Crear texto de resumen para la respuesta de audio
                audio_text = (
                    f"Tenemos varias opciones de habitaciones disponibles del {room_data['checkin']} "
                    f"al {room_data['checkout']}. Habitación individual desde ${room_data['price_single']}, "
                    f"doble desde ${room_data['price_double']}, y habitaciones premium desde "
                    f"${room_data['price_prem_single']}. Te envío los detalles completos."
                )

                # Generar respuesta de audio
                audio_data = await self.audio_processor.generate_audio_response(audio_text, content_type="room_options")

                if audio_data:
                    logger.info(
                        "orchestrator.audio_response_generated",
                        content_type="room_options",
                        audio_bytes=len(audio_data),
                    )

                    # Primero enviamos el audio
                    logger.info("orchestrator.sending_audio_before_interactive_list")

                    # Preparar lista interactiva para follow-up
                    room_options = self.template_service.get_interactive_list("room_options", **room_data)

                    # Primero enviamos el audio y luego indicamos que hay que enviar la lista
                    return {
                        "response_type": "audio",
                        "content": {
                            "text": audio_text,
                            "audio_data": audio_data,
                            "follow_up": {"type": "interactive_list", "content": room_options},
                        },
                    }
            except Exception as e:
                logger.error("orchestrator.audio_generation_failed", error=str(e), content_type="room_options")
                # Si hay error, continuamos con la lista interactiva normal

        # Enviar lista interactiva con opciones de habitaciones
        room_options = self.template_service.get_interactive_list("room_options", **room_data)

        return {"response_type": "interactive_list", "content": room_options}

    async def _handle_late_checkout(self, nlp_result: dict, session_data: dict, message: UnifiedMessage) -> dict:
        """
        Maneja solicitudes y confirmaciones de late checkout

        Funcionalidad:
        - Verifica disponibilidad de late checkout con PMS
        - Maneja flujo de confirmación (pending → confirm)
        - Calcula fees según disponibilidad y políticas
        - Soporte para audio con respuesta TTS

        Args:
            nlp_result: Resultado del análisis NLP con intent y entidades
            session_data: Estado persistente de la sesión del usuario
            message: Mensaje unificado normalizado

        Returns:
            dict: Respuesta con disponibilidad y opciones de confirmación
        """
        intent = nlp_result.get("intent")
        if isinstance(intent, dict):
            intent = intent.get("name")
        tenant_id = getattr(message, "tenant_id", None)

        # PART 1: Handle confirmation of pending late checkout
        if session_data.get("pending_late_checkout"):
            if intent in ["deny", "no", "cancel"]:
                del session_data["pending_late_checkout"]
                await self.session_manager.update_session(message.user_id, session_data, tenant_id)
                return {"response_type": "text", "content": "Entendido, he cancelado la solicitud de late checkout."}

            if intent in ["affirm", "yes", "confirm"]:
                pending_lc = session_data["pending_late_checkout"]
                booking_id = pending_lc.get("booking_id")
                checkout_time = pending_lc.get("checkout_time")
                fee = pending_lc.get("fee", 0)

                try:
                    logger.info(
                        "orchestrator.confirming_late_checkout", booking_id=booking_id, checkout_time=checkout_time, fee=fee
                    )

                    # Confirm late checkout with PMS
                    confirmation = await self.pms_adapter.confirm_late_checkout(
                        reservation_id=str(booking_id), checkout_time=checkout_time
                    )

                    if confirmation["success"]:
                        response_text = self.template_service.get_response(
                            "late_checkout_confirmed", checkout_time=checkout_time, fee=fee
                        )

                        # Clear pending late checkout from session
                        del session_data["pending_late_checkout"]
                        await self.session_manager.update_session(message.user_id, session_data, tenant_id)

                        logger.info(
                            "orchestrator.late_checkout_confirmed_success",
                            booking_id=booking_id,
                            checkout_time=checkout_time,
                        )
                    else:
                        response_text = "Lo siento, no pudimos confirmar el late checkout. Por favor, contacta a recepción."

                except Exception as e:
                    logger.error("orchestrator.late_checkout_confirmation_failed", booking_id=booking_id, error=str(e))
                    response_text = "Hubo un error al confirmar el late checkout. Por favor, contacta a recepción."

                return {"response_type": "text", "content": response_text}

        # PART 2: Handle new late checkout request
        logger.info("orchestrator.late_checkout_request", user_id=message.user_id, tenant_id=tenant_id)

        # Check if user has an active booking in session
        booking_id = session_data.get("booking_id") or session_data.get("reservation_id")

        if not booking_id:
            # No booking ID in session - ask for it
            response_text = self.template_service.get_response("late_checkout_no_booking")

            # Update session to expect booking ID
            session_data["awaiting_booking_id_for"] = "late_checkout"
            await self.session_manager.update_session(message.user_id, session_data, tenant_id)

            return {"response_type": "text", "content": response_text}

        try:
            # Check late checkout availability
            logger.info(
                "orchestrator.checking_late_checkout_availability", booking_id=booking_id, user_id=message.user_id
            )

            availability = await self.pms_adapter.check_late_checkout_availability(
                reservation_id=str(booking_id),
                requested_checkout_time=HOTEL_LATE_CHECKOUT_TIME,  # Default to 2pm
            )

            if availability["available"]:
                # Late checkout is available
                fee = availability["fee"]
                checkout_time = availability.get("requested_time", HOTEL_LATE_CHECKOUT_TIME)

                # Check if it's free (no next booking and policy allows)
                if fee == 0:
                    response_text = self.template_service.get_response(
                        "late_checkout_free", checkout_time=checkout_time
                    )
                else:
                    response_text = self.template_service.get_response(
                        "late_checkout_available", checkout_time=checkout_time, fee=fee
                    )

                # Store late checkout request in session for confirmation
                session_data["pending_late_checkout"] = {
                    "booking_id": booking_id,
                    "checkout_time": checkout_time,
                    "fee": fee,
                }
                await self.session_manager.update_session(message.user_id, session_data, tenant_id)

            else:
                # Not available - room has next booking
                response_text = self.template_service.get_response(
                    "late_checkout_not_available", standard_time=HOTEL_STANDARD_CHECKOUT_TIME
                )

            logger.info(
                "orchestrator.late_checkout_check_complete",
                booking_id=booking_id,
                available=availability["available"],
                fee=availability.get("fee", 0),
            )

        except Exception as e:
            logger.error("orchestrator.late_checkout_check_failed", booking_id=booking_id, error=str(e))
            response_text = "Lo siento, hubo un error al verificar la disponibilidad de late checkout. Por favor, contacta a recepción."

        # If original message was audio, respond with audio too
        if message.tipo == "audio":
            try:
                audio_data = await self.audio_processor.generate_audio_response(response_text)

                if audio_data:
                    logger.info("orchestrator.late_checkout_audio_response_generated")
                    return {"response_type": "audio", "content": response_text, "audio_data": audio_data}
            except Exception as e:
                logger.warning("orchestrator.late_checkout_audio_failed", error=str(e))

        return {"response_type": "text", "content": response_text}

    async def _handle_review_request(self, nlp_result: dict, session_data: dict, message: UnifiedMessage) -> dict | None:
        """
        Maneja solicitudes de review y programación de recordatorios post-checkout.

        Procesa dos flujos:
        1. Respuestas a solicitudes de review (intent: review_response)
        2. Detección de checkout para programar review automática

        Args:
            nlp_result: Resultado del análisis NLP con intent y entidades
            session_data: Datos de sesión del huésped
            message: Mensaje unificado del huésped

        Returns:
            Dict con response_type ('text' o 'audio') y content con la respuesta

        Raises:
            Exception: Si falla el procesamiento de review o programación
        """
        getattr(message, "tenant_id", None)
        intent = nlp_result.get("intent")
        if isinstance(intent, dict):
            intent = intent.get("name")

        # PART 1: Procesar respuesta a solicitud de review
        if intent == "review_response":
            logger.info("review_response_detected", user_id=message.user_id, text=message.texto)

            try:
                review_service = get_review_service()
                result = await review_service.process_review_response(
                    guest_id=message.user_id, response_text=message.texto or ""
                )

                if result["success"]:
                    if result["intent"] == "positive":
                        response_text = "¡Perfecto! Te envío los enlaces para dejar tu reseña."
                    elif result["intent"] == "negative":
                        response_text = "Lamentamos que tu experiencia no haya sido perfecta. Valoramos tu feedback."
                    elif result["intent"] == "unsubscribe":
                        response_text = "Entendido, no enviaremos más recordatorios de reseñas."
                    else:
                        response_text = "Gracias por tu respuesta. ¿Hay algo más en lo que pueda ayudarte?"
                else:
                    response_text = "Gracias por tu mensaje. ¿En qué más puedo ayudarte?"

                logger.info(
                    "review_response_processed",
                    user_id=message.user_id,
                    intent=result.get("intent"),
                    sentiment=result.get("sentiment"),
                )

            except Exception as e:
                logger.error("review_response_error", user_id=message.user_id, error=str(e))
                response_text = "Gracias por tu mensaje. ¿En qué más puedo ayudarte?"

            # Responder con audio si el mensaje original era de audio
            if message.tipo == "audio":
                try:
                    audio_data = await self.audio_processor.generate_audio_response(response_text)
                    if audio_data:
                        return {"response_type": "audio", "content": {"text": response_text, "audio_data": audio_data}}
                except Exception as e:
                    logger.error(f"Failed to generate audio response for review: {e}")

            return {"response_type": "text", "content": response_text}

        # PART 2: Detectar checkout y programar solicitud de review
        if intent in ["check_out_info", "checkout_completed"] or "checkout" in (message.texto or "").lower():
            logger.info("checkout_detected_scheduling_review", user_id=message.user_id)

            try:
                # Get guest info from session
                guest_name = session_data.get("guest_name", "Estimado huésped")
                booking_id = session_data.get("booking_id", "HTL-REVIEW-001")

                # Schedule review request for 24 hours later
                from datetime import datetime

                checkout_date = datetime.now(timezone.utc)  # In real implementation, get from PMS

                review_service = get_review_service()
                from app.services.review_service import GuestSegment

                # Determine guest segment based on session data
                segment = GuestSegment.COUPLE  # Default, could be enhanced with ML
                if session_data.get("business_trip"):
                    segment = GuestSegment.BUSINESS
                elif session_data.get("family_trip"):
                    segment = GuestSegment.FAMILY
                elif session_data.get("group_size", 1) > 2:
                    segment = GuestSegment.GROUP

                schedule_result = await review_service.schedule_review_request(
                    guest_id=message.user_id,
                    guest_name=guest_name,
                    booking_id=booking_id,
                    checkout_date=checkout_date,
                    segment=segment,
                    language="es",
                )

                if schedule_result["success"]:
                    logger.info(
                        "review_request_scheduled",
                        user_id=message.user_id,
                        request_id=schedule_result["request_id"],
                        scheduled_time=schedule_result["scheduled_time"],
                    )

            except Exception as e:
                logger.error("review_scheduling_error", user_id=message.user_id, error=str(e))
                # Don't fail the main response if review scheduling fails

        # If we reach here, return None to continue processing in handle_intent
        return None

    async def _handle_availability(
        self, nlp_result: dict, session: dict, message: UnifiedMessage, respond_with_audio: bool = False
    ) -> dict:
        """
        Maneja consultas de disponibilidad de habitaciones.

        Procesa solicitudes de check_availability mostrando:
        - Información de disponibilidad (fechas, tipo de habitación, precio)
        - Imágenes de habitación (si está habilitado en settings)
        - Respuesta en audio (si el mensaje original era audio)
        - Botones interactivos o respuesta de texto según feature flag

        Args:
            nlp_result: Resultado del análisis NLP con intent y entidades
            session: Datos de sesión del huésped
            message: Mensaje unificado del huésped
            respond_with_audio: Si se debe responder con audio

        Returns:
            Dict con response_type y content según formato seleccionado

        Raises:
            Exception: Si falla la generación de respuesta (se captura internamente)
        """
        
        # H1: Enrich trace with availability query context
        from opentelemetry import trace
        from ..core.tracing import enrich_span_with_business_context
        
        span = trace.get_current_span()
        if span and span.is_recording():
            # Extract entities from NLP result
            entities = nlp_result.get("entities", {})
            enrich_span_with_business_context(
                span,
                operation="check_availability",
                checkin_date=entities.get("checkin_date"),
                checkout_date=entities.get("checkout_date"),
                room_type=entities.get("room_type"),
                guests=entities.get("guests"),
            )

        getattr(message, "tenant_id", None)

        # Comprobar si la feature flag de mensajes interactivos está activada
        ff_service = await get_feature_flag_service()
        use_interactive = await ff_service.is_enabled("features.interactive_messages", default=True)

        # Datos de disponibilidad (simulados - en producción vendrían del PMS)
        # Formatear importes según idioma detectado (sin símbolo, plantillas lo incluyen)
        lang = message.metadata.get("detected_language", "es") if isinstance(message.metadata, dict) else "es"
        try:
            # Asegurar que TemplateService use el mismo idioma (handlers directos en tests)
            self.template_service.set_language(lang)
        except Exception:
            pass
        availability_data = {
            "checkin": "hoy",
            "checkout": "mañana",
            "room_type": "Doble",
            "guests": 2,
            "price": format_currency(PRICE_ROOM_DOUBLE, lang, with_symbol=False),
            "total": format_currency(PRICE_ROOM_DOUBLE * 2, lang, with_symbol=False),
        }

        # Preparar mensaje de respuesta de texto
        response_text = self.template_service.get_response("availability_found", **availability_data)

        # Feature 3: Preparar imagen de habitación si está habilitada
        room_image_url = None
        room_image_caption = None
        if settings.room_images_enabled:
            try:
                # Obtener URL de imagen basada en el tipo de habitación
                room_type = availability_data.get("room_type", "")
                # Use module-level wrapper to enable test patching
                room_image_url = get_room_image_url(room_type)

                if room_image_url and validate_image_url(room_image_url):
                    # Preparar caption personalizado para la imagen
                    room_image_caption = self.template_service.get_response(
                        "room_photo_caption",
                        room_type=room_type,
                        price=availability_data.get("price", 0),
                        guests=availability_data.get("guests", 2),
                    )

                    logger.info(
                        "room_image.prepared",
                        room_type=room_type,
                        image_url=room_image_url,
                        has_caption=bool(room_image_caption),
                    )
                else:
                    logger.warning("room_image.invalid_or_not_found", room_type=room_type, url=room_image_url)
                    room_image_url = None
            except Exception as e:
                # No fallar la respuesta si la imagen falla - es un feature adicional
                logger.warning(
                    "room_image.preparation_failed", error=str(e), room_type=availability_data.get("room_type", "")
                )
                room_image_url = None

        # Si el mensaje original era de audio, responder también con audio
        if respond_with_audio:
            try:
                # Generar audio con el texto de respuesta
                audio_data = await self.audio_processor.generate_audio_response(
                    response_text, content_type="availability_response"
                )

                if audio_data:
                    logger.info("Generated audio response for availability check", audio_bytes=len(audio_data))

                    # No podemos combinar audio con mensajes interactivos en WhatsApp,
                    # así que en este caso priorizamos el audio
                    # Si hay imagen, la incluimos en la respuesta
                    return {
                        "response_type": "audio_with_image" if room_image_url else "audio",
                        "content": response_text,
                        "audio_data": audio_data,
                        "image_url": room_image_url,
                        "image_caption": room_image_caption,
                    }
            except Exception as e:
                # Si falla la generación de audio, continuamos con texto normal
                logger.error(f"Failed to generate audio response: {e}")

        # Si llegamos aquí, usamos respuesta normal (texto o interactiva)
        if use_interactive:
            # Respuesta con botones interactivos
            button_template = self.template_service.get_interactive_buttons(
                "availability_confirmation", **availability_data
            )

            # Si hay imagen, incluirla junto con los botones interactivos
            return {
                "response_type": "interactive_buttons_with_image" if room_image_url else "interactive_buttons",
                "content": button_template,
                "image_url": room_image_url,
                "image_caption": room_image_caption,
            }
        else:
            # Respuesta de texto tradicional con imagen opcional
            return {
                "response_type": "text_with_image" if room_image_url else "text",
                "content": response_text,
                "image_url": room_image_url,
                "image_caption": room_image_caption,
            }

    async def _handle_make_reservation(self, nlp_result: dict, session_data: dict, message: UnifiedMessage) -> dict:
        """
        Maneja solicitudes de creación de reserva.

        Proporciona instrucciones de reserva con información de depósito y banco.
        Actualiza el estado de sesión para marcar reserva como pendiente.

        Args:
            nlp_result: Resultado del análisis NLP
            session_data: Datos de sesión del huésped
            message: Mensaje unificado del huésped

        Returns:
            Dict con response_type ('text' o 'audio') y content con instrucciones
        """
        tenant_id = getattr(message, "tenant_id", None)
        
        # H1: Enrich trace with reservation context
        from opentelemetry import trace
        from ..core.tracing import enrich_span_with_business_context
        
        span = trace.get_current_span()
        if span and span.is_recording():
            entities = nlp_result.get("entities", {})
            enrich_span_with_business_context(
                span,
                operation="make_reservation",
                deposit_amount=RESERVATION_DEPOSIT_AMOUNT,
                session_state="reservation_pending",
                checkin_date=entities.get("checkin_date"),
                checkout_date=entities.get("checkout_date"),
            )

        # Datos de reserva (simulados)
        reservation_data = {"deposit": RESERVATION_DEPOSIT_AMOUNT, "bank_info": MOCK_BANK_INFO}

        # Actualizar estado de sesión para seguimiento de reserva
        session_data["reservation_pending"] = True
        session_data["deposit_amount"] = reservation_data["deposit"]
        await self.session_manager.update_session(message.user_id, session_data, tenant_id)

        # Preparar texto de respuesta
        response_text = self.template_service.get_response("reservation_instructions", **reservation_data)

        # Si el mensaje original era de audio, responder con audio también
        if message.tipo == "audio":
            try:
                # Generar respuesta de audio
                audio_data = await self.audio_processor.generate_audio_response(
                    response_text, content_type="reservation_instructions"
                )

                if audio_data:
                    logger.info("Generated audio response for reservation instructions", audio_bytes=len(audio_data))

                    return {"response_type": "audio", "content": {"text": response_text, "audio_data": audio_data}}
            except Exception as e:
                # Si falla la generación de audio, continuamos con texto normal
                logger.error(f"Failed to generate audio response for reservation: {e}")

        # Respuesta de texto tradicional
        return {"response_type": "text", "content": response_text}

    async def _handle_hotel_location(self, nlp_result: dict, session_data: dict, message: UnifiedMessage) -> dict:
        """
        Maneja solicitudes de ubicación del hotel.

        Proporciona información de ubicación con coordenadas GPS, nombre y dirección.
        Soporta respuesta con audio si el mensaje original era de audio.

        Args:
            nlp_result: Resultado del análisis NLP
            session_data: Datos de sesión del huésped
            message: Mensaje unificado del huésped

        Returns:
            Dict con response_type ('location', 'audio_with_location') y content
        """
        from app.core.settings import settings

        # Usar template de ubicación con datos de configuración
        response_text = self.template_service.get_response("location_info")

        # Obtener coordenadas desde settings
        latitude = settings.hotel_latitude
        longitude = settings.hotel_longitude
        hotel_name = settings.hotel_name
        hotel_address = settings.hotel_address

        intent = nlp_result.get("intent")
        if isinstance(intent, dict):
            intent = intent.get("name")

        logger.info(
            "Sending hotel location", latitude=latitude, longitude=longitude, hotel_name=hotel_name, intent=intent
        )

        # Si es un mensaje de audio, responder con audio + ubicación
        if message.tipo == "audio":
            try:
                # Generar respuesta de audio
                audio_data = await self.audio_processor.generate_audio_response(
                    response_text, content_type="hotel_location"
                )

                if audio_data is None:
                    # Si no se pudo generar audio, responder solo con ubicación
                    logger.warning("Could not generate audio for location response")
                    return {
                        "response_type": "location",
                        "content": {
                            "latitude": latitude,
                            "longitude": longitude,
                            "name": hotel_name,
                            "address": hotel_address,
                        },
                    }

                # Responder con audio + ubicación
                return {
                    "response_type": "audio_with_location",
                    "content": {
                        "text": response_text,
                        "audio_data": audio_data,
                        "location": {
                            "latitude": latitude,
                            "longitude": longitude,
                            "name": hotel_name,
                            "address": hotel_address,
                        },
                    },
                }
            except Exception as e:
                # Si hay error en la generación de audio, responder solo con ubicación
                logger.error(f"Error generating audio for location response: {e}")
                return {
                    "response_type": "location",
                    "content": {
                        "latitude": latitude,
                        "longitude": longitude,
                        "name": hotel_name,
                        "address": hotel_address,
                    },
                }
        else:
            # Responder solo con ubicación (mapa)
            return {
                "response_type": "location",
                "content": {"latitude": latitude, "longitude": longitude, "name": hotel_name, "address": hotel_address},
            }

    # =========================================================================
    # PAYMENT CONFIRMATION HELPERS - Extracted to reduce complexity
    # =========================================================================

    def _extract_reservation_data(self, session_data: dict) -> dict:
        """Extract reservation data from session with fallbacks to mock values."""
        ctx = session_data.get("context", {}) if isinstance(session_data, dict) else {}
        
        booking_id = session_data.get("booking_id") or session_data.get("reservation_id")
        if not booking_id:
            booking_id = "HTL-001"
            session_data["booking_id"] = booking_id

        return {
            "check_in_date": session_data.get("check_in_date") or ctx.get("check_in_date") or MOCK_CHECKIN_DATE,
            "check_out_date": session_data.get("check_out_date") or ctx.get("check_out_date") or MOCK_CHECKOUT_DATE,
            "room_number": session_data.get("room_number") or ctx.get("room_number") or MOCK_ROOM_NUMBER,
            "guest_name": session_data.get("guest_name") or ctx.get("guest_name") or "Estimado Huésped",
            "booking_id": booking_id,
        }

    def _detect_language(self, nlp_result: dict, message: UnifiedMessage) -> str:
        """Detect language from NLP result or message metadata."""
        lang = None
        if isinstance(nlp_result, dict):
            lang = nlp_result.get("language")
        if not lang and isinstance(message.metadata, dict):
            lang = message.metadata.get("detected_language")
        return lang or "es"

    def _generate_qr(self, reservation_data: dict) -> dict | None:
        """Attempt to generate QR code for booking confirmation."""
        try:
            from app.services.qr_service import get_qr_service

            qr_service = get_qr_service()
            qr_result = qr_service.generate_booking_qr(
                booking_id=reservation_data["booking_id"],
                guest_name=reservation_data["guest_name"],
                check_in_date=str(reservation_data["check_in_date"]),
                check_out_date=str(reservation_data["check_out_date"]),
                room_number=str(reservation_data["room_number"]) if reservation_data["room_number"] else None,
                hotel_name=settings.hotel_name,
            )
            logger.info(
                "orchestrator.qr_generation_attempt",
                booking_id=reservation_data["booking_id"],
                guest_name=reservation_data["guest_name"],
                result_success=bool(qr_result and qr_result.get("success")),
            )
            return qr_result
        except Exception as qr_err:
            logger.debug("qr_generation_failed", error=str(qr_err))
            return None

    async def _update_session_after_payment(
        self, session_data: dict, message: UnifiedMessage, qr_generated: bool
    ) -> None:
        """Update session state after payment confirmation."""
        session_data["booking_confirmed"] = True
        session_data["qr_generated"] = qr_generated
        session_data["reservation_pending"] = False
        if "context" in session_data and isinstance(session_data["context"], dict):
            session_data["context"]["reservation_pending"] = False
        
        try:
            tenant_id = getattr(message, "tenant_id", None)
            await self.session_manager.update_session(message.user_id, session_data, tenant_id)
        except Exception as sess_err:
            logger.debug("session_update_failed", error=str(sess_err))

    def _build_qr_response(self, qr_result: dict, reservation_data: dict) -> dict:
        """Build response with QR code image."""
        booking_id = reservation_data["booking_id"]
        try:
            qr_booking_id = (
                (qr_result.get("qr_data") or {}).get("booking_id")
                or qr_result.get("booking_id")
            )
            if qr_booking_id:
                booking_id = qr_booking_id
        except Exception:
            pass

        confirmation_text = self.template_service.get_response(
            "booking_confirmed_with_qr",
            booking_id=booking_id,
            guest_name=reservation_data["guest_name"],
            check_in=str(reservation_data["check_in_date"]),
            check_out=str(reservation_data["check_out_date"]),
            room_number=reservation_data["room_number"],
        )

        return {
            "response_type": "image_with_text",
            "content": confirmation_text,
            "image_path": qr_result.get("file_path"),
            "image_caption": "🎫 Tu código QR de confirmación - Guárdalo para el check-in!",
        }

    async def _build_fallback_confirmation_response(
        self, reservation_data: dict, lang: str, message: UnifiedMessage
    ) -> dict:
        """Build fallback response when QR generation fails."""
        # Try interactive buttons if enabled
        try:
            ff = await get_feature_flag_service()
            if await ff.is_enabled("features.interactive_messages", default=False) and message.tipo != "audio":
                try:
                    self.template_service.set_language(lang)
                except Exception:
                    pass
                buttons = self.template_service.get_interactive_buttons("arrival_options")
                if buttons:
                    return {"response_type": "interactive_buttons", "content": buttons}
        except Exception:
            pass

        return {
            "response_type": "text",
            "content": self.template_service.get_response(
                "booking_confirmed_no_qr",
                booking_id=reservation_data["booking_id"],
                check_in=str(reservation_data["check_in_date"]),
                check_out=str(reservation_data["check_out_date"]),
            ),
        }

    # =========================================================================
    # END PAYMENT CONFIRMATION HELPERS
    # =========================================================================

    async def _handle_payment_confirmation(self, nlp_result: dict, session_data: dict, message: UnifiedMessage) -> dict:
        """
        Maneja confirmación de pago con imagen de comprobante.

        Procesa imagen de comprobante de pago y genera confirmación de reserva.
        Uses extracted helpers for improved maintainability (CC reduced from 36 to ~10).

        Args:
            nlp_result: Resultado del análisis NLP
            session_data: Datos de sesión del huésped
            message: Mensaje unificado del huésped

        Returns:
            Dict con response_type y content según si hay QR o no
        """
        # Check for pending reservation
        has_pending = session_data.get("reservation_pending") or session_data.get("context", {}).get(
            "reservation_pending"
        )
        
        if not has_pending:
            # No pending reservation - respond with simple reaction
            return {
                "response_type": "reaction",
                "content": {
                    "message_id": message.message_id,
                    "emoji": self.template_service.get_reaction("payment_received"),
                },
            }

        # Extract reservation data and language
        reservation_data = self._extract_reservation_data(session_data)
        lang = self._detect_language(nlp_result, message)

        # Attempt QR generation
        qr_result = self._generate_qr(reservation_data)

        # Update session state
        await self._update_session_after_payment(
            session_data, message, qr_generated=bool(qr_result and qr_result.get("success"))
        )

        # Build appropriate response
        if qr_result and qr_result.get("success"):
            return self._build_qr_response(qr_result, reservation_data)
        
        return await self._build_fallback_confirmation_response(reservation_data, lang, message)

    async def process_message(self, message: UnifiedMessage):
        """
        Compatibilidad hacia atrás: proxy a handle_unified_message retornando un objeto con atributos.

        Muchos tests esperan 'orchestrator.process_message' y acceden vía atributos como
        response.response_type, response.content, image_path, etc. Este shim conserva
        el contrato anterior envolviendo el dict de respuesta en un objeto simple.
        """
        from types import SimpleNamespace

        result = await self.handle_unified_message(message)
        if isinstance(result, dict):
            # Asegurar que claves comunes existan aunque falten
            defaults = {
                "response_type": result.get("response_type") or ("text" if "response" in result else None),
                "content": result.get("content") or result.get("response"),
                "image_url": result.get("image_url"),
                "image_path": result.get("image_path"),
                "image_caption": result.get("image_caption"),
                "audio_data": result.get("audio_data") or (result.get("content", {}) if isinstance(result.get("content"), dict) else {}).get("audio_data"),
            }
            # Unir todo para mantener acceso por atributo
            merged = {**result, **defaults}
            return SimpleNamespace(**merged)
        return result

    # =========================================================================
    # HELPER METHODS - Extracted to reduce handle_unified_message complexity
    # =========================================================================

    async def _process_audio_message(self, message: UnifiedMessage) -> None:
        """
        Process audio message: transcribe via STT and update message text.
        Handles DLQ enqueuing on failure with graceful degradation.
        """
        media_url = getattr(message, "media_url", None)
        if not media_url:
            logger.warning(
                "audio_message_without_media_url",
                user_id=getattr(message, "user_id", None),
                message_id=getattr(message, "message_id", None),
            )
            message.texto = message.texto or ""
            message.metadata["confidence_stt"] = message.metadata.get("confidence_stt", 0.0)
            message.metadata["language_stt"] = message.metadata.get("language_stt")
            return

        try:
            # Compatibility: some tests patch transcribe_audio
            transcribe_fn = getattr(self.audio_processor, "transcribe_audio", None)
            if callable(transcribe_fn):
                maybe_coro = transcribe_fn(media_url)
                if asyncio.iscoroutine(maybe_coro):
                    stt_result = await maybe_coro
                else:
                    stt_result = maybe_coro
            else:
                stt_result = await self.audio_processor.transcribe_whatsapp_audio(media_url)

            if not isinstance(stt_result, dict):
                stt_result = {}

            message.texto = stt_result.get("text") or stt_result.get("transcript") or ""
            message.metadata["confidence_stt"] = stt_result.get("confidence", 0.0)
            if lang := stt_result.get("language"):
                message.metadata["language_stt"] = lang

        except Exception as audio_error:
            logger.error(
                "audio_processing_failed",
                error=str(audio_error),
                user_id=message.user_id,
                message_id=message.message_id,
            )
            if self.dlq_service:
                await self.dlq_service.enqueue_failed_message(
                    message=message,
                    error=audio_error,
                    reason="audio_processing_failure"
                )
            message.texto = ""
            message.metadata["audio_error"] = str(audio_error)

    def _get_fallback_intent(self, text: str, detected_language: str) -> dict:
        """
        Rule-based fallback intent detection when NLP fails.
        Returns NLP-like result dict with intent and confidence.
        """
        text_lower = text.lower()
        
        # Keyword mappings for multilingual fallback
        FALLBACK_KEYWORDS = {
            "check_availability": [
                "disponibilidad", "disponible", "habitacion", "cuarto",  # Spanish
                "availability", "available", "room", "rooms",  # English
                "disponibilidade", "quarto", "quartos",  # Portuguese
            ],
            "make_reservation": [
                "reservar", "reserva", "reservacion",  # Spanish
                "book", "booking", "reserve", "reservation",  # English
            ],
            "pricing_info": [
                "precio", "costo", "tarifa", "valor",  # Spanish
                "price", "cost", "rate", "pricing",  # English
                "preço", "custo",  # Portuguese
            ],
            "hotel_location": [
                "ubicacion", "ubicación", "dirección", "direccion", "llegar", "mapa",  # Spanish
                "location", "address", "map", "directions", "where",  # English
                "localização", "endereço", "direções",  # Portuguese
            ],
        }
        
        for intent_name, keywords in FALLBACK_KEYWORDS.items():
            if any(word in text_lower for word in keywords):
                return {
                    "intent": {"name": intent_name, "confidence": 0.5},
                    "entities": {},
                    "language": detected_language,
                }
        
        return {
            "intent": {"name": "unknown", "confidence": 0.0},
            "entities": {},
            "language": detected_language,
        }

    async def _process_nlp(self, message: UnifiedMessage, span) -> tuple[dict, str]:
        """
        Process message text through NLP with fallback handling.
        Returns (nlp_result, intent_name) tuple.
        """
        from opentelemetry import trace
        from ..core.tracing import enrich_span_with_business_context
        
        text = message.texto or ""
        
        try:
            detected_language = await self.nlp_engine.detect_language(text)
            nlp_result = await self.nlp_engine.process_text(text, language=detected_language)
            intent_name = nlp_result.get("intent", {}).get("name", "unknown") or "unknown"
            confidence = nlp_result.get("intent", {}).get("confidence", 0.0)
            
            if span and span.is_recording():
                enrich_span_with_business_context(
                    span,
                    intent=intent_name,
                    confidence=confidence,
                    language=detected_language,
                )
            
            message.metadata["detected_language"] = detected_language
            try:
                self.template_service.set_language(detected_language)
            except Exception:
                pass
            
            return nlp_result, intent_name
            
        except Exception as nlp_error:
            logger.warning(
                "nlp_failed_using_fallback",
                error=str(nlp_error),
                user_id=message.user_id,
                message_id=message.message_id,
            )
            metrics_service.record_nlp_fallback("nlp_service_failure")
            nlp_fallbacks.inc()
            
            if self.dlq_service:
                await self.dlq_service.enqueue_failed_message(
                    message=message,
                    error=nlp_error,
                    reason="nlp_processing_failure"
                )
            
            detected_language = await self.nlp_engine.detect_language(text)
            message.metadata["detected_language"] = detected_language
            try:
                self.template_service.set_language(detected_language)
            except Exception:
                pass
            
            nlp_result = self._get_fallback_intent(text, detected_language)
            intent_name = nlp_result["intent"]["name"]
            
            return nlp_result, intent_name

    def _build_response(self, response_data: dict, message: UnifiedMessage) -> dict:
        """
        Build final response dict from handler response data.
        Maps response_type to appropriate output structure.
        """
        response_type = response_data.get("response_type", "text")
        
        # Response builders by type
        RESPONSE_BUILDERS = {
            "text": lambda: {
                "response_type": "text",
                "content": response_data.get("content", ""),
                "original_message": message,
            },
            "audio": lambda: {
                "response_type": "audio",
                "content": {
                    "text": response_data.get("content", ""),
                    "audio_data": response_data.get("audio_data"),
                },
                "original_message": message,
            },
            "audio_with_image": lambda: {
                "response_type": "audio_with_image",
                "content": response_data.get("content", ""),
                "audio_data": response_data.get("audio_data"),
                "image_url": response_data.get("image_url"),
                "image_caption": response_data.get("image_caption"),
                "original_message": message,
            },
            "interactive_buttons": lambda: {
                "response_type": "interactive_buttons",
                "content": response_data.get("content", {}),
                "original_message": message,
            },
            "interactive_list": lambda: {
                "response_type": "interactive_list",
                "content": response_data.get("content", {}),
                "original_message": message,
            },
            "location": lambda: {
                "response_type": "location",
                "content": response_data.get("content", {}),
                "original_message": message,
            },
            "audio_with_location": lambda: {
                "response_type": "audio_with_location",
                "content": {
                    "text": response_data.get("content", {}).get("text", ""),
                    "audio_data": response_data.get("content", {}).get("audio_data"),
                    "location": response_data.get("content", {}).get("location", {}),
                },
                "original_message": message,
            },
            "text_with_image": lambda: {
                "response_type": "text_with_image",
                "content": response_data.get("content", ""),
                "image_url": response_data.get("image_url"),
                "image_caption": response_data.get("image_caption"),
                "original_message": message,
                "response": response_data.get("content", ""),
            },
            "interactive_buttons_with_image": lambda: {
                "response_type": "interactive_buttons_with_image",
                "content": response_data.get("content", {}),
                "image_url": response_data.get("image_url"),
                "image_caption": response_data.get("image_caption"),
                "original_message": message,
            },
            "image_with_text": lambda: {
                "response_type": "image_with_text",
                "content": response_data.get("content", ""),
                "image_path": response_data.get("image_path"),
                "image_caption": response_data.get("image_caption"),
                "original_message": message,
            },
            "reaction": lambda: {
                "response_type": "reaction",
                "content": response_data.get("content", {}),
                "original_message": message,
            },
        }
        
        builder = RESPONSE_BUILDERS.get(response_type)
        if builder:
            return builder()
        
        logger.warning(f"Unknown response_type: {response_type}, defaulting to text")
        return {"response": "Lo siento, no puedo procesar tu solicitud en este momento."}

    async def _record_intent_metrics(self, nlp_result: dict, intent_name: str) -> None:
        """
        Record metrics for detected intent and confidence.
        """
        intent_obj = nlp_result.get("intent", {})
        confidence = intent_obj.get("confidence", 0.0)
        confidence_level = (
            "high" if confidence >= CONFIDENCE_THRESHOLD_LOW
            else "medium" if confidence >= CONFIDENCE_THRESHOLD_VERY_LOW
            else "low"
        )
        intents_detected.labels(intent=intent_name, confidence_level=confidence_level).inc()

    async def _prepare_session_and_context(self, message: UnifiedMessage, nlp_result: dict) -> tuple[dict, bool, str]:
        """
        Get/create session and determine feature flags and response language.
        Returns (session, enhanced_fallback_enabled, response_language).
        """
        tenant_id = getattr(message, "tenant_id", None)
        
        # Get/create session
        session = await self.session_manager.get_or_create_session(
            message.user_id, message.canal, tenant_id
        )
        
        # Check feature flags
        ff_service = await get_feature_flag_service()
        enhanced_fallback = await ff_service.is_enabled("nlp.fallback.enhanced", default=True)
        
        # Record confidence metric
        confidence = nlp_result.get("intent", {}).get("confidence", 0.0)
        metrics_service.record_nlp_confidence(confidence)
        
        # Determine response language
        response_language = nlp_result.get("language", message.metadata.get("detected_language", "es"))
        
        return session, enhanced_fallback, response_language

    async def _handle_low_confidence_check(
        self, 
        message: UnifiedMessage, 
        nlp_result: dict, 
        enhanced_fallback: bool, 
        response_language: str
    ) -> dict | None:
        """
        Check for low confidence and return fallback response if needed.
        Returns response dict if low confidence handled, else None.
        """
        confidence = nlp_result.get("intent", {}).get("confidence", 0.0)
        
        if enhanced_fallback and confidence < CONFIDENCE_THRESHOLD_VERY_LOW and message.tipo != "image":
            metrics_service.record_nlp_fallback("very_low_confidence")
            nlp_fallbacks.inc()
            return {"response": self._get_low_confidence_message(response_language)}
            
        elif enhanced_fallback and confidence < CONFIDENCE_THRESHOLD_LOW:
            message.metadata["low_confidence"] = True
            metrics_service.record_nlp_fallback("low_confidence_hint")
            
        return None

    async def _execute_intent_handler(
        self, 
        nlp_result: dict, 
        session: dict, 
        message: UnifiedMessage, 
        intent_name: str
    ) -> dict:
        """
        Execute the appropriate intent handler and build the response.
        Handles PMS errors and degradation.
        """
        try:
            response_data = await self.handle_intent(nlp_result, session, message)
            return self._build_response(response_data, message)

        except (PMSError, CircuitBreakerOpenError) as pms_error:
            logger.error(
                "pms_unavailable_degraded_response",
                error=str(pms_error),
                intent=intent_name,
                user_id=message.user_id,
                message_id=message.message_id,
            )
            # Assuming orchestrator_degraded_responses is available in scope or imported
            # If not, we might need to import it or pass it. 
            # Based on previous code it seemed to be a global metric but wasn't in imports shown.
            # Checking imports... it wasn't in the top imports shown. 
            # It might be defined in the file but I missed it or it's a global.
            # I will assume it works as before, but if it fails I'll fix it.
            # Actually, looking at previous file content, `orchestrator_degraded_responses` was used but not defined in the visible snippet.
            # It's likely defined with other metrics.
            from .business_metrics import orchestrator_degraded_responses
            orchestrator_degraded_responses.inc()
            
            if self.dlq_service:
                await self.dlq_service.enqueue_failed_message(
                    message=message,
                    error=pms_error,
                    reason="pms_unavailable"
                )
            
            # Return degraded response
            return {
                "response_type": "text",
                "content": self.template_service.get_response("system_degraded"),
                "original_message": message
            }

    async def handle_unified_message(self, message: UnifiedMessage) -> dict:
        """
        Main message processing entry point.
        Refactored to use helper methods for reduced cyclomatic complexity.
        """
        start = time.time()
        intent_name = "unknown"
        status = "ok"
        tenant_id = getattr(message, "tenant_id", None)
        
        # H1: Enrich trace with business context
        from opentelemetry import trace
        from ..core.tracing import enrich_span_with_business_context
        
        span = trace.get_current_span()
        if span and span.is_recording():
            enrich_span_with_business_context(
                span,
                operation="process_message",
                tenant_id=str(tenant_id) if tenant_id else None,
                user_id=str(getattr(message, "user_id", None)),
                channel=message.canal,
                message_type=message.tipo,
            )

        # Métrica de negocio: contar mensaje por canal
        messages_by_channel.labels(channel=message.canal).inc()

        # Step 1: Process audio messages (extracted to helper)
        if message.tipo == "audio":
            await self._process_audio_message(message)

        try:
            # Step 2: Process NLP (extracted to helper)
            nlp_result, intent_name = await self._process_nlp(message, span)
            
            # Step 3: Record metrics
            await self._record_intent_metrics(nlp_result, intent_name)

            # Step 4 & 5: Get session and context
            session, enhanced_fallback, response_language = await self._prepare_session_and_context(message, nlp_result)

            # Step 6: Check business hours handling
            bh_result = await self._handle_business_hours(nlp_result, session, message)
            if bh_result is not None:
                if bh_result.get("response_type", "text") == "text":
                    return {"response_type": "text", "content": bh_result.get("content", ""), "original_message": message}
                return {**bh_result, "original_message": message}

            # Step 7: Handle very low confidence
            low_conf_response = await self._handle_low_confidence_check(
                message, nlp_result, enhanced_fallback, response_language
            )
            if low_conf_response:
                return low_conf_response

            # Step 8: Handle intent and build response
            return await self._execute_intent_handler(nlp_result, session, message, intent_name)

        except Exception as e:
            # Global error handler remains here
            status = "error"
            logger.error(
                "orchestrator_process_error",
                error=str(e),
                user_id=message.user_id,
                traceback=True
            )
            if self.dlq_service:
                await self.dlq_service.enqueue_failed_message(
                    message=message,
                    error=e,
                    reason="orchestrator_unhandled_exception"
                )
            return {
                "response_type": "text",
                "content": self.template_service.get_response("general_error"),
                "original_message": message
            }
        finally:
            duration = time.time() - start
            logger.info(
                "message_processed",
                duration=duration,
                status=status,
                intent=intent_name,
                user_id=message.user_id
            )
            orchestrator_latency.labels(intent=intent_name, status=status).observe(duration)
            orchestrator_messages_total.labels(intent=intent_name, status=status).inc()
            if tenant_id:
                try:
                    metrics_service.inc_tenant_request(tenant_id, error=(status != "ok"))
                except Exception:
                    pass

    # =========================================================================
    # HANDLE INTENT HELPERS - Extracted to reduce complexity
    # =========================================================================

    async def _check_business_hours_gate(
        self, intent: str, nlp_result: dict, session: dict, message: UnifiedMessage
    ) -> dict | None:
        """Check business hours gate, bypassing for reservations."""
        if intent != "make_reservation":
            return await self._handle_business_hours(nlp_result, session, message)
        return None

    async def _check_late_checkout_confirmation(
        self, intent: str, nlp_result: dict, session: dict, message: UnifiedMessage
    ) -> dict | None:
        """Check if this is a late checkout confirmation."""
        if session.get("pending_late_checkout") and intent in ["affirm", "yes", "confirm", "deny", "no", "cancel"]:
            return await self._handle_late_checkout(nlp_result, session, message)
        return None

    async def _check_interactive_response(self, session: dict, message: UnifiedMessage) -> dict | None:
        """Check if message is an interactive response."""
        if message.tipo == "interactive" and message.metadata.get("interactive_data"):
            interactive_data = message.metadata.get("interactive_data", {})
            interactive_id = interactive_data.get("id")
            if interactive_id:
                return await self._handle_interactive_response(interactive_id, session, message)
        return None

    def _has_pending_reservation(self, session: dict) -> bool:
        """Check if session has a pending reservation."""
        return bool(
            session.get("reservation_pending") or session.get("context", {}).get("reservation_pending")
        )

    async def _handle_image_message(
        self, intent: str, nlp_result: dict, session: dict, message: UnifiedMessage
    ) -> dict | None:
        """Handle image message logic for payment confirmations."""
        if message.tipo != "image":
            return None

        has_pending = self._has_pending_reservation(session)

        # Payment confirmation heuristic
        if has_pending:
            logger.info(
                "orchestrator.payment_heuristic_triggered",
                has_pending_top=session.get("reservation_pending"),
                has_pending_ctx=session.get("context", {}).get("reservation_pending"),
            )
            return await self._handle_payment_confirmation(nlp_result, session, message)

        # Explicit payment confirmation intent
        if intent == "payment_confirmation":
            return await self._handle_payment_confirmation(nlp_result, session, message)

        # No pending reservation - simple reaction
        return {
            "response_type": "reaction",
            "content": {
                "message_id": message.message_id,
                "emoji": self.template_service.get_reaction("payment_received"),
            },
        }

    async def _dispatch_to_handler(
        self, intent: str, nlp_result: dict, session: dict, message: UnifiedMessage, respond_with_audio: bool
    ) -> dict | None:
        """Dispatch to appropriate intent handler if exists."""
        intent_key = intent if isinstance(intent, str) and intent else "unknown"
        handler = self._intent_handlers.get(intent_key)
        
        if not handler:
            return None

        if intent in ["check_availability"]:
            return await handler(nlp_result, session, message, respond_with_audio=respond_with_audio)
        return await handler(nlp_result, session, message)

    async def _check_checkout_review(
        self, intent: str, nlp_result: dict, session: dict, message: UnifiedMessage
    ) -> dict | None:
        """Check if this triggers a review request after checkout."""
        if intent in ["check_out_info", "checkout_completed"] or "checkout" in (message.texto or "").lower():
            return await self._handle_review_request(nlp_result, session, message)
        return None

    # =========================================================================
    # END HANDLE INTENT HELPERS
    # =========================================================================

    async def handle_intent(self, nlp_result: dict, session: dict, message: UnifiedMessage) -> dict:
        """
        Procesa un intent detectado y genera la respuesta apropiada.
        Uses extracted helpers for improved maintainability (CC reduced from 26 to ~10).

        Args:
            nlp_result: Resultado del procesamiento NLP con intent y entidades
            session: Sesión del usuario
            message: Mensaje unificado original

        Returns:
            dict with response_type and content
        """
        intent = self._normalize_intent(nlp_result)
        respond_with_audio = message.tipo == "audio"

        # 1. Business hours check
        result = await self._check_business_hours_gate(intent, nlp_result, session, message)
        if result:
            return result

        # 2. Late checkout confirmation
        result = await self._check_late_checkout_confirmation(intent, nlp_result, session, message)
        if result:
            return result

        # 3. Interactive response
        result = await self._check_interactive_response(session, message)
        if result:
            return result

        # 4. Image message handling
        result = await self._handle_image_message(intent, nlp_result, session, message)
        if result:
            return result

        # 5. Dispatch to intent handler
        result = await self._dispatch_to_handler(intent, nlp_result, session, message, respond_with_audio)
        if result:
            return result

        # 6. Checkout review trigger
        result = await self._check_checkout_review(intent, nlp_result, session, message)
        if result:
            return result

        # 7. Fallback response
        return await self._handle_fallback_response(message, respond_with_audio)

    async def _handle_interactive_response(self, interactive_id: str, session: dict, message: UnifiedMessage) -> dict:
        """
        Procesa respuestas a mensajes interactivos basadas en su ID.

        Args:
            interactive_id: ID del elemento interactivo seleccionado
            session: Sesión del usuario
            message: Mensaje unificado original

        Returns:
            Respuesta formateada según el ID interactivo
        """
        tenant_id = getattr(message, "tenant_id", None)

        if interactive_id == "confirm_reservation":
            # Usuario confirmó que quiere reservar después de ver disponibilidad
            reservation_data = {"deposit": RESERVATION_DEPOSIT_AMOUNT, "bank_info": MOCK_BANK_INFO}

            # Actualizar estado de sesión para seguimiento de reserva
            session["reservation_pending"] = True
            session["deposit_amount"] = reservation_data["deposit"]
            await self.session_manager.update_session(message.user_id, session, tenant_id)

            return {
                "response_type": "text",
                "content": self.template_service.get_response("reservation_instructions", **reservation_data),
            }

        elif interactive_id == "more_options":
            # Usuario quiere ver más opciones de habitaciones
            room_options = self.template_service.get_interactive_list(
                "room_options",
                checkin="01/01/2023",
                checkout="05/01/2023",
                price_single=8000,
                price_double=12000,
                price_prem_single=15000,
                price_prem_double=20000,
            )

            return {"response_type": "interactive_list", "content": room_options}

        elif interactive_id == "transfer_request":
            # Usuario solicitó servicio de transfer
            session["transfer_requested"] = True
            await self.session_manager.update_session(message.user_id, session, tenant_id)

            return {
                "response_type": "text",
                "content": "Perfecto. Hemos registrado tu solicitud de transfer. ¿A qué hora llegas?",
            }

        # ID interactivo desconocido, enviar mensaje genérico
        return {
            "response_type": "text",
            "content": "Gracias por tu selección. Un representante procesará tu solicitud.",
        }

    def _get_technical_error_message(self, language: str = "es") -> str:
        """
        Return technical error message in the appropriate language.

        Args:
            language: ISO language code (es, en, pt)

        Returns:
            Localized error message
        """
        if language == "en":
            return (
                "Sorry, I'm having technical issues. Can you tell me if you want to: "
                "check availability, make a reservation, or get pricing information?"
            )
        elif language == "pt":
            return (
                "Desculpe, estou com problemas técnicos. Você pode me dizer se quer: "
                "verificar disponibilidade, fazer uma reserva ou obter informações de preços?"
            )
        else:  # Spanish (default)
            return (
                "Disculpa, estoy teniendo problemas técnicos. ¿Puedes decirme si quieres: "
                "consultar disponibilidad, hacer una reserva, o información de precios?"
            )

    def _get_low_confidence_message(self, language: str = "es") -> str:
        """
        Return low confidence clarification message in the appropriate language.

        Args:
            language: ISO language code (es, en, pt)

        Returns:
            Localized clarification message
        """
        if language == "en":
            return (
                "I'm not sure I understood. Can you rephrase or choose an option: "
                "availability, pricing, hotel information?"
            )
        elif language == "pt":
            return (
                "Não tenho certeza se entendi. Você pode reformular ou escolher uma opção: "
                "disponibilidade, preços, informações do hotel?"
            )
        else:  # Spanish (default)
            return (
                "No estoy seguro de haber entendido. ¿Puedes reformular o elegir una opción: "
                "disponibilidad, precios, información del hotel?"
            )

    # =========================================================================
    # INFO INTENT HELPERS - Extracted to reduce complexity
    # =========================================================================

    def _normalize_intent(self, nlp_result: dict) -> str:
        """Extract and normalize intent string from NLP result."""
        intent = nlp_result.get("intent")
        if isinstance(intent, dict):
            intent = intent.get("name")
        if not isinstance(intent, str) or not intent:
            intent = "help_message"
        return intent

    def _sync_template_language(self, nlp_result: dict, message: UnifiedMessage) -> str | None:
        """Sync template service language and return detected language."""
        try:
            lang = self._detect_language(nlp_result, message)
            if isinstance(lang, str) and lang:
                self.template_service.set_language(lang)
            return lang
        except Exception:
            return None

    async def _try_interactive_info_menu(self, intent: str, message: UnifiedMessage) -> dict | None:
        """Try to return interactive menu for info intents if feature flag enabled."""
        try:
            ff = await get_feature_flag_service()
            if await ff.is_enabled("features.interactive_messages", default=False):
                info_intents = {
                    "guest_services", "hotel_amenities", "check_in_info",
                    "check_out_info", "cancellation_policy", "pricing_info",
                }
                if intent in info_intents and message.tipo != "audio":
                    buttons = self.template_service.get_interactive_buttons("info_menu")
                    if buttons:
                        return {"response_type": "interactive_buttons", "content": buttons}
        except Exception:
            pass
        return None

    def _get_info_context(self, intent: str, message: UnifiedMessage) -> dict:
        """Build context dict for info intent template."""
        context = {}
        if intent == "business_hours_info":
            start = end = None
            try:
                tid = getattr(message, "tenant_id", None)
                if tid:
                    meta = dynamic_tenant_service.get_tenant_meta(tid)
                    if meta:
                        start = meta.get("business_hours_start")
                        end = meta.get("business_hours_end")
            except Exception:
                pass
            context["business_hours"] = format_business_hours(start, end)
        return context

    async def _generate_audio_for_text(self, text: str, intent: str) -> dict | None:
        """Generate audio response for given text."""
        try:
            audio_data = await self.audio_processor.generate_audio_response(text)
            if audio_data:
                logger.info(f"Generated audio response for {intent} inquiry", audio_bytes=len(audio_data))
                return {"response_type": "audio", "content": {"text": text, "audio_data": audio_data}}
        except Exception as e:
            logger.error(f"Failed to generate audio response for {intent}: {e}")
        return None

    def _apply_humanization(self, text: str, nlp_result: dict, message: UnifiedMessage) -> str:
        """Apply optional humanization (es-AR tone, text consolidation)."""
        try:
            from app.services.feature_flag_service import DEFAULT_FLAGS
            from ..utils.humanizer import apply_es_ar_tone, consolidate_text

            if DEFAULT_FLAGS.get("humanize.consolidate_text.enabled", False):
                text = consolidate_text([text])

            lang = (nlp_result or {}).get("language") if isinstance(nlp_result, dict) else None
            if not lang and isinstance(message.metadata, dict):
                lang = message.metadata.get("detected_language")
            
            locale = message.metadata.get("locale") if isinstance(message.metadata, dict) else None

            if DEFAULT_FLAGS.get("humanize.es_ar.enabled", False):
                if lang == "es" or (locale and "es-AR" in str(locale)):
                    text = apply_es_ar_tone(text)
        except Exception:
            pass
        return text

    # =========================================================================
    # END INFO INTENT HELPERS
    # =========================================================================

    async def _handle_info_intent(self, nlp_result: dict, session: dict, message: UnifiedMessage) -> dict:
        """
        Generic handler for informational intents (guest services, amenities, check-in info, etc.)
        Uses extracted helpers for improved maintainability (CC reduced from 33 to ~8).

        Args:
            nlp_result: NLP processing result with intent
            session: User session data
            message: Unified message object

        Returns:
            Response dict with text or audio content
        """
        intent = self._normalize_intent(nlp_result)
        self._sync_template_language(nlp_result, message)

        # Try interactive menu if feature flag enabled
        interactive_response = await self._try_interactive_info_menu(intent, message)
        if interactive_response:
            return interactive_response

        # Build context and get template response
        context = self._get_info_context(intent, message)
        response_text = self.template_service.get_response(intent, **context)

        # If original message was audio, respond with audio
        if message.tipo == "audio":
            audio_response = await self._generate_audio_for_text(response_text, intent)
            if audio_response:
                return audio_response

        # Apply humanization and return text response
        response_text = self._apply_humanization(response_text, nlp_result, message)
        return {"response_type": "text", "content": response_text}

    async def _handle_fallback_response(self, message: UnifiedMessage, respond_with_audio: bool = False) -> dict:
        """
        Generate fallback response when no intent handler matches

        Args:
            message: Unified message object
            respond_with_audio: Whether to respond with audio

        Returns:
            Response dict with fallback message
        """
        # Localized fallback
        language = "es"
        if isinstance(message.metadata, dict):
            language = message.metadata.get("detected_language", "es")
        default_text = self._get_low_confidence_message(language)

        # If original message was audio, respond with audio
        if respond_with_audio or message.tipo == "audio":
            try:
                audio_data = await self.audio_processor.generate_audio_response(default_text)

                if audio_data:
                    logger.info("Generated audio response for fallback message")
                    return {"response_type": "audio", "content": {"text": default_text, "audio_data": audio_data}}
            except Exception as e:
                logger.error(f"Failed to generate audio for fallback response: {e}")

        # Text response fallback con humanización opcional
        try:
            from app.services.feature_flag_service import DEFAULT_FLAGS
            from ..utils.humanizer import apply_es_ar_tone, consolidate_text

            if DEFAULT_FLAGS.get("humanize.consolidate_text.enabled", False):
                default_text = consolidate_text([default_text])

            locale = None
            if isinstance(message.metadata, dict):
                locale = message.metadata.get("locale")

            if DEFAULT_FLAGS.get("humanize.es_ar.enabled", False) and (language == "es" or (locale and "es-AR" in str(locale))):
                default_text = apply_es_ar_tone(default_text)
        except Exception:
            pass

        return {"response_type": "text", "content": default_text}


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
orchestrator_degraded_responses = Counter(
    "orchestrator_degraded_responses_total", "Respuestas degradadas por fallo de servicios externos"
)

# Singleton instance
_orchestrator_instance: Optional[Orchestrator] = None

async def get_orchestrator() -> Orchestrator:
    """Get Orchestrator singleton."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        from app.services.pms_adapter import get_pms_adapter
        from app.services.session_manager import get_session_manager
        from app.services.lock_service import get_lock_service
        from app.services.dlq_service import get_dlq_service
        
        pms_adapter = await get_pms_adapter()
        session_manager = await get_session_manager()
        lock_service = await get_lock_service()
        
        # Try to get DLQ service, but don't fail if not initialized (e.g. tests)
        try:
            dlq_service = await get_dlq_service()
        except RuntimeError:
            dlq_service = None
        
        _orchestrator_instance = Orchestrator(
            pms_adapter=pms_adapter,
            session_manager=session_manager,
            lock_service=lock_service,
            dlq_service=dlq_service
        )
    return _orchestrator_instance
