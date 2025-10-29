# [PROMPT 2.7] app/services/orchestrator.py

import time
from datetime import datetime, timezone, date
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

# Métricas para escalamiento
escalations_total = Counter(
    "orchestrator_escalations_total", "Total de escalamientos a staff humano", ["reason", "channel"]
)
escalation_response_time = Histogram(
    "orchestrator_escalation_response_seconds", "Tiempo desde escalamiento hasta respuesta de staff", ["reason"]
)


class Orchestrator:
    def __init__(self, pms_adapter, session_manager: SessionManager, lock_service: LockService):
        self.pms_adapter = pms_adapter
        self.session_manager = session_manager
        self.lock_service = lock_service
        self.message_gateway = MessageGateway()
        self.nlp_engine = NLPEngine()
        self.audio_processor = AudioProcessor()
        self.template_service = TemplateService()

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
        # Record escalation metric
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

    async def _handle_business_hours(self, nlp_result: dict, session_data: dict, message: UnifiedMessage) -> dict | None:
        """
        Maneja la verificación de horarios comerciales y escalación urgente

        Funcionalidad:
        - Detecta solicitudes urgentes (palabras clave: urgente, urgent, emergency)
        - Verifica si estamos dentro del horario comercial
        - Retorna mensaje de horario cerrado para requests no urgentes
        - Escala requests urgentes fuera de horario

        Args:
            nlp_result: Resultado del análisis NLP con intent y entidades
            session_data: Estado persistente de la sesión del usuario
            message: Mensaje unificado normalizado

        Returns:
            dict: Respuesta estructurada con tipo y contenido
            {
                "response_type": "text",
                "content": str,
                "escalated": bool (opcional)
            }
        """
        intent = nlp_result.get("intent", "unknown")
        text_lower = (message.texto or "").lower()
        is_urgent = "urgente" in text_lower or "urgent" in text_lower or "emergency" in text_lower

        # Check if we're within business hours (tenant overrides if available)
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

        in_business_hours = is_business_hours(start_hour=start, end_hour=end, timezone=tz)

        logger.info(
            "orchestrator.business_hours_check",
            in_business_hours=in_business_hours,
            is_urgent=is_urgent,
            intent=intent,
            user_id=message.user_id,
        )

        # If outside business hours and not an urgent request
        if not in_business_hours and not is_urgent:
            # Get next opening time for the message
            next_open = get_next_business_open_time(start_hour=start, timezone=tz)
            business_hours_str = format_business_hours(start_hour=start, end_hour=end)

            # Check if it's weekend
            current_time = datetime.now()
            is_weekend = current_time.weekday() >= 5  # Saturday=5, Sunday=6

            # Choose appropriate template
            template_key = "after_hours_weekend" if is_weekend else "after_hours_standard"

            # next_open puede ser datetime o un valor simple (tests pueden stubearlo a int)
            try:
                next_open_str = next_open.strftime("%H:%M")  # type: ignore[attr-defined]
            except Exception:
                next_open_str = str(next_open)

            response_text = self.template_service.get_response(
                template_key, business_hours=business_hours_str, next_open_time=next_open_str
            )

            logger.info(
                "orchestrator.after_hours_response",
                template=template_key,
                next_open_time=next_open_str,
                user_id=message.user_id,
            )

            # Return after-hours response
            return {"response_type": "text", "content": response_text}

        # If urgent request outside business hours, escalate
        if not in_business_hours and is_urgent:
            logger.warning(
                "orchestrator.urgent_after_hours_escalation",
                user_id=message.user_id,
                intent=intent,
                text_preview=message.texto[:100] if message.texto else "",
            )

            # Escalate to staff with comprehensive tracking and alerting
            return await self._escalate_to_staff(
                message=message, reason="urgent_after_hours", intent=intent, session_data=session_data
            )

        # If within business hours, return None to continue processing
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
        if session_data.get("pending_late_checkout") and intent in ["affirm", "yes", "confirm"]:
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
        from app.core.settings import settings
        from app.utils.room_images import get_room_image_url, validate_image_url

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

    async def _handle_payment_confirmation(self, nlp_result: dict, session_data: dict, message: UnifiedMessage) -> dict:
        """
        Maneja confirmación de pago con imagen de comprobante.

        Procesa imagen de comprobante de pago y genera confirmación de reserva.
        Feature 5 (QR generation) temporalmente deshabilitado.

        Args:
            nlp_result: Resultado del análisis NLP
            session_data: Datos de sesión del huésped
            message: Mensaje unificado del huésped

        Returns:
            Dict con response_type y content según si hay QR o no
        """
        import time

        getattr(message, "tenant_id", None)

        # Si el usuario envía una imagen de comprobante de pago y tiene una reserva pendiente
        if session_data.get("reservation_pending"):
            # Simular la confirmación del pago
            # En un caso real, procesaríamos la imagen y confirmaríamos con el PMS

            # FEATURE 5: Generate QR code for confirmed booking - TEMPORALMENTE DESHABILITADO
            qr_data = None
            # TEMPORAL FIX: QR generation deshabilitado hasta agregar qrcode
            logger.info("QR generation temporarily disabled")

            check_in_date = session_data.get("check_in_date", MOCK_CHECKIN_DATE)
            check_out_date = session_data.get("check_out_date", MOCK_CHECKOUT_DATE)
            room_number = session_data.get("room_number", MOCK_ROOM_NUMBER)

            # Locale-aware date formatting for confirmation message
            lang = None
            if isinstance(nlp_result, dict):
                lang = nlp_result.get("language")
            if not lang and isinstance(message.metadata, dict):
                lang = message.metadata.get("detected_language")
            lang = lang or "es"

            # Try to parse ISO strings to date for proper locale formatting
            def _to_date(val):
                from datetime import datetime, date as _date

                if isinstance(val, _date):
                    return val
                if isinstance(val, str):
                    try:
                        return datetime.fromisoformat(val).date()
                    except Exception:
                        return val
                return val

            ci_disp = format_date_locale(_to_date(check_in_date), lang)
            co_disp = format_date_locale(_to_date(check_out_date), lang)

            # Si tenemos QR code, enviar confirmación completa con QR
            if qr_data:
                guest_name = session_data.get("guest_name", "Estimado Huésped")
                confirmation_text = self.template_service.get_response(
                    "booking_confirmed_with_qr",
                    booking_id=qr_data["booking_id"],
                    guest_name=guest_name,
                    check_in=ci_disp,
                    check_out=co_disp,
                    room_number=room_number,
                )

                return {
                    "response_type": "image_with_text",
                    "content": confirmation_text,
                    "image_path": qr_data["file_path"],
                    "image_caption": "🎫 Tu código QR de confirmación - Guárdalo para el check-in!",
                }
            else:
                # Fallback: confirmation sin QR — si interactivos están habilitados, ofrecer opciones de llegada
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
                        booking_id=f"HTL-{int(time.time())}",
                        check_in=ci_disp,
                        check_out=co_disp,
                    ),
                }
        else:
            # No hay reserva pendiente, responder con reacción simple
            return {
                "response_type": "reaction",
                "content": {
                    "message_id": message.message_id,
                    "emoji": self.template_service.get_reaction("payment_received"),
                },
            }

    async def handle_unified_message(self, message: UnifiedMessage) -> dict:
        start = time.time()
        intent_name = "unknown"
        status = "ok"
        tenant_id = getattr(message, "tenant_id", None)

        # Métrica de negocio: contar mensaje por canal
        messages_by_channel.labels(channel=message.canal).inc()

        if message.tipo == "audio":
            if not message.media_url:
                raise ValueError("Missing media_url for audio message")
            stt_result = await self.audio_processor.transcribe_whatsapp_audio(message.media_url)
            message.texto = stt_result["text"]
            message.metadata["confidence_stt"] = stt_result["confidence"]

        try:
            text = message.texto or ""

            # Graceful degradation: Si NLP falla, usar reglas básicas
            try:
                # Detect language from the message if not specified
                detected_language = await self.nlp_engine.detect_language(text)

                # Process message with detected/specified language
                nlp_result = await self.nlp_engine.process_message(text, language=detected_language)
                intent_name = nlp_result.get("intent", {}).get("name", "unknown") or "unknown"

                # Store language info in session for continuity
                message.metadata["detected_language"] = detected_language
                # Establecer idioma por defecto en TemplateService
                try:
                    self.template_service.set_language(detected_language)
                except Exception:
                    pass

            except Exception as nlp_error:
                logger.warning(f"NLP failed, using rule-based fallback: {nlp_error}")
                metrics_service.record_nlp_fallback("nlp_service_failure")
                nlp_fallbacks.inc()

                # Language detection fallback for rule-based matching
                detected_language = await self.nlp_engine.detect_language(text)
                message.metadata["detected_language"] = detected_language
                # Establecer idioma por defecto en TemplateService (fallback)
                try:
                    self.template_service.set_language(detected_language)
                except Exception:
                    pass

                # Reglas básicas de fallback (multilingual)
                text_lower = text.lower()
                if any(
                    word in text_lower
                    for word in [
                        "disponibilidad",
                        "disponible",
                        "habitacion",
                        "cuarto",  # Spanish
                        "availability",
                        "available",
                        "room",
                        "rooms",  # English
                        "disponibilidade",
                        "quarto",
                        "quartos",  # Portuguese
                    ]
                ):
                    intent_name = "check_availability"
                    nlp_result = {
                        "intent": {"name": "check_availability", "confidence": 0.5},
                        "entities": [],
                        "language": detected_language,
                    }
                elif any(
                    word in text_lower
                    for word in [
                        "reservar",
                        "reserva",
                        "reservacion",  # Spanish
                        "book",
                        "booking",
                        "reserve",
                        "reservation",  # English
                        "reservar",
                        "reserva",  # Portuguese
                    ]
                ):
                    intent_name = "make_reservation"
                    nlp_result = {
                        "intent": {"name": "make_reservation", "confidence": 0.5},
                        "entities": [],
                        "language": detected_language,
                    }
                elif any(
                    word in text_lower
                    for word in [
                        "precio",
                        "costo",
                        "tarifa",
                        "valor",  # Spanish
                        "price",
                        "cost",
                        "rate",
                        "pricing",  # English
                        "preço",
                        "custo",
                        "tarifa",  # Portuguese
                    ]
                ):
                    intent_name = "pricing_info"
                    nlp_result = {
                        "intent": {"name": "pricing_info", "confidence": 0.5},
                        "entities": [],
                        "language": detected_language,
                    }
                elif any(
                    word in text_lower
                    for word in [
                        "ubicacion",
                        "ubicación",
                        "dirección",
                        "direccion",
                        "llegar",
                        "mapa",  # Spanish
                        "location",
                        "address",
                        "map",
                        "directions",
                        "where",  # English
                        "localização",
                        "endereço",
                        "mapa",
                        "direções",  # Portuguese
                    ]
                ):
                    intent_name = "hotel_location"
                    nlp_result = {
                        "intent": {"name": "hotel_location", "confidence": 0.5},
                        "entities": [],
                        "language": detected_language,
                    }
                else:
                    intent_name = "unknown"
                    nlp_result = {
                        "intent": {"name": "unknown", "confidence": 0.0},
                        "entities": [],
                        "language": detected_language,
                    }

                    # Return multilingual error message
                    return {"response": self._get_technical_error_message(detected_language)}

            # Métrica de negocio: registrar intent detectado
            intent_obj = nlp_result.get("intent", {})
            confidence = intent_obj.get("confidence", 0.0)
            confidence_level = (
                "high"
                if confidence >= CONFIDENCE_THRESHOLD_LOW
                else "medium"
                if confidence >= CONFIDENCE_THRESHOLD_VERY_LOW
                else "low"
            )
            intents_detected.labels(intent=intent_name, confidence_level=confidence_level).inc()

            session = await self.session_manager.get_or_create_session(message.user_id, message.canal, tenant_id)
            # Fallback dinámico según confianza + feature flag
            ff_service = await get_feature_flag_service()
            enhanced_fallback = await ff_service.is_enabled("nlp.fallback.enhanced", default=True)
            # Registrar categoría de confianza
            metrics_service.record_nlp_confidence(confidence)

            # Get language from NLP result or message metadata
            response_language = nlp_result.get("language", message.metadata.get("detected_language", "es"))

            if enhanced_fallback and confidence < CONFIDENCE_THRESHOLD_VERY_LOW:
                # Respuesta de bajo nivel de confianza agresiva
                metrics_service.record_nlp_fallback("very_low_confidence")
                nlp_fallbacks.inc()  # Métrica de negocio: fallback detectado
                return {"response": self._get_low_confidence_message(response_language)}
            elif enhanced_fallback and confidence < CONFIDENCE_THRESHOLD_LOW:
                message.metadata["low_confidence"] = True
                metrics_service.record_nlp_fallback("low_confidence_hint")

            # Graceful degradation: Manejar fallos de PMS
            try:
                response_data = await self.handle_intent(nlp_result, session, message)
                response_type = response_data.get("response_type", "text")

                if response_type == "text":
                    # Respuesta de texto simple, compatible con el formato anterior
                    return {"response": response_data.get("content", "")}

                elif response_type == "audio":
                    # Respuesta de audio (texto + audio)
                    return {
                        "response_type": "audio",
                        "content": {
                            "text": response_data.get("content", ""),
                            "audio_data": response_data.get("audio_data"),
                        },
                        "original_message": message,
                    }

                elif response_type == "interactive_buttons":
                    # Respuesta con botones interactivos
                    return {
                        "response_type": "interactive_buttons",
                        "content": response_data.get("content", {}),
                        "original_message": message,
                    }

                elif response_type == "interactive_list":
                    # Respuesta con lista interactiva
                    return {
                        "response_type": "interactive_list",
                        "content": response_data.get("content", {}),
                        "original_message": message,
                    }

                elif response_type == "location":
                    # Respuesta con ubicación
                    return {
                        "response_type": "location",
                        "content": response_data.get("content", {}),
                        "original_message": message,
                    }

                elif response_type == "audio_with_location":
                    # Respuesta combinada de audio + ubicación
                    # El router deberá manejar esto enviando primero el audio y luego la ubicación
                    content = response_data.get("content", {})
                    return {
                        "response_type": "audio_with_location",
                        "content": {
                            "text": content.get("text", ""),
                            "audio_data": content.get("audio_data"),
                            "location": content.get("location", {}),
                        },
                        "original_message": message,
                    }

                elif response_type == "text_with_image":
                    # Respuesta de texto con imagen opcional: preservar texto para compatibilidad
                    return {
                        "response": response_data.get("content", ""),
                        "response_type": "text_with_image",
                        "image_url": response_data.get("image_url"),
                        "image_caption": response_data.get("image_caption"),
                    }

                elif response_type == "interactive_buttons_with_image":
                    # Respuesta interactiva con imagen: exponer estructura completa para el router
                    return {
                        "response_type": "interactive_buttons_with_image",
                        "content": response_data.get("content", {}),
                        "image_url": response_data.get("image_url"),
                        "image_caption": response_data.get("image_caption"),
                        "original_message": message,
                    }

                elif response_type == "reaction":
                    # Respuesta con reacción a un mensaje
                    return {
                        "response_type": "reaction",
                        "content": response_data.get("content", {}),
                        "original_message": message,
                    }

                else:
                    # Tipo de respuesta desconocido, usar texto por defecto
                    logger.warning(f"Unknown response_type: {response_type}, defaulting to text")
                    return {"response": "Lo siento, no puedo procesar tu solicitud en este momento."}

            except (PMSError, CircuitBreakerOpenError) as pms_error:
                logger.error(f"PMS unavailable, degraded response: {pms_error}")
                orchestrator_degraded_responses.inc()

                # Respuesta degradada según el intent
                if intent_name == "check_availability":
                    response_text = "Lo siento, nuestro sistema de disponibilidad está temporalmente fuera de servicio. Por favor, contacta directamente con recepción al [TELÉFONO] o escribe a [EMAIL]."
                elif intent_name == "make_reservation":
                    response_text = "No puedo procesar reservas en este momento por mantenimiento del sistema. Por favor, contacta con recepción al [TELÉFONO] o intenta más tarde."
                else:
                    response_text = "Disculpa, estoy experimentando dificultades técnicas. ¿Puedes contactar directamente con recepción? Teléfono: [TELÉFONO]"

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

    async def handle_intent(self, nlp_result: dict, session: dict, message: UnifiedMessage) -> dict:
        """
        Procesa un intent detectado y genera la respuesta apropiada.

        Args:
            nlp_result: Resultado del procesamiento NLP con intent y entidades
            session: Sesión del usuario
            message: Mensaje unificado original

        Returns:
            Diccionario con tipo de respuesta y contenido:
            {
                "response_type": "text|audio|interactive|location|reaction",
                "content": { ... contenido específico del tipo ... }
            }
        """
        intent = nlp_result.get("intent")
        if isinstance(intent, dict):
            intent = intent.get("name")
        getattr(message, "tenant_id", None)

        # Verificar si el mensaje original era de audio
        respond_with_audio = message.tipo == "audio"

        # ============================================================
        # ============================================================
        # FEATURE 2: BUSINESS HOURS CHECK
        # ============================================================
        business_hours_result = await self._handle_business_hours(nlp_result, session, message)
        if business_hours_result is not None:
            return business_hours_result
        # ============================================================
        # END BUSINESS HOURS CHECK
        # ============================================================

        # ============================================================
        # FEATURE 4: LATE CHECKOUT CONFIRMATION
        # ============================================================
        # Check if user is confirming a pending late checkout
        if session.get("pending_late_checkout") and intent in ["affirm", "yes", "confirm"]:
            return await self._handle_late_checkout(nlp_result, session, message)
        # ============================================================
        # END LATE CHECKOUT CONFIRMATION
        # ============================================================

        # Detectar si es una respuesta a un mensaje interactivo
        interactive_id = None

        if message.tipo == "interactive" and message.metadata.get("interactive_data"):
            interactive_data = message.metadata.get("interactive_data", {})
            interactive_id = interactive_data.get("id")

            # Procesar respuesta interactiva según su ID
            if interactive_id:
                return await self._handle_interactive_response(interactive_id, session, message)

        # ============================================================
        # INTENT DISPATCH PATTERN
        # ============================================================
        # Handle payment confirmation with image (special case)
        if intent == "payment_confirmation" and message.tipo == "image":
            return await self._handle_payment_confirmation(nlp_result, session, message)

        # Dispatch to appropriate handler using the intent map
        intent_key = intent if isinstance(intent, str) and intent else "unknown"
        handler = self._intent_handlers.get(intent_key)
        if handler:
            # Check if handler needs audio response flag
            handler_params = {
                "nlp_result": nlp_result,
                "session": session,
                "message": message,
            }

            # Some handlers need respond_with_audio parameter
            if intent in ["check_availability"]:
                handler_params["respond_with_audio"] = respond_with_audio

            return await handler(**handler_params)

        # ============================================================
        # CHECKOUT TRIGGER FOR REVIEW SCHEDULING
        # ============================================================
        # Check if this is a checkout confirmation and schedule review request
        if intent in ["check_out_info", "checkout_completed"] or "checkout" in (message.texto or "").lower():
            result = await self._handle_review_request(nlp_result, session, message)
            if result:  # If handler returned a response, use it
                return result
            # Otherwise continue with normal flow

        # ============================================================
        # FALLBACK RESPONSE
        # ============================================================
        # Si llegamos aquí, devolver respuesta por defecto
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

    async def _handle_info_intent(self, nlp_result: dict, session: dict, message: UnifiedMessage) -> dict:
        """
        Generic handler for informational intents (guest services, amenities, check-in info, etc.)

        Args:
            nlp_result: NLP processing result with intent
            session: User session data
            message: Unified message object

        Returns:
            Response dict with text or audio content
        """
        intent = nlp_result.get("intent")
        if isinstance(intent, dict):
            intent = intent.get("name")
        if not isinstance(intent, str) or not intent:
            intent = "help_message"

        # Ensure TemplateService language aligns with detected language (for direct handler calls in tests)
        try:
            lang = None
            if isinstance(nlp_result, dict):
                lang = nlp_result.get("language")
            if not lang and isinstance(message.metadata, dict):
                lang = message.metadata.get("detected_language")
            if isinstance(lang, str) and lang:
                self.template_service.set_language(lang)
        except Exception:
            pass

        # Feature-flagged interactive menu for informational intents
        try:
            ff = await get_feature_flag_service()
            if await ff.is_enabled("features.interactive_messages", default=False):
                info_intents = {
                    "guest_services",
                    "hotel_amenities",
                    "check_in_info",
                    "check_out_info",
                    "cancellation_policy",
                    "pricing_info",
                }
                if intent in info_intents and message.tipo != "audio":
                    # Return interactive buttons menu guiding the user
                    buttons = self.template_service.get_interactive_buttons("info_menu")
                    if buttons:
                        return {"response_type": "interactive_buttons", "content": buttons}
        except Exception:
            # On any failure, fall back to text below
            pass

        # Get response template based on intent
        response_text = self.template_service.get_response(intent)

        # If original message was audio, respond with audio too
        if message.tipo == "audio":
            try:
                audio_data = await self.audio_processor.generate_audio_response(response_text)

                if audio_data:
                    logger.info(f"Generated audio response for {intent} inquiry", audio_bytes=len(audio_data))
                    return {"response_type": "audio", "content": {"text": response_text, "audio_data": audio_data}}
            except Exception as e:
                logger.error(f"Failed to generate audio response for {intent}: {e}")

        # Text response fallback
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

        # Text response fallback
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
