"""
Review Request Service - Feature 6
Sistema automatizado de solicitud de reseñas post-estancia

Funcionalidades:
- Envío automático de solicitudes de reseñas 24h después del checkout
- Múltiples plataformas (Google, TripAdvisor, Booking.com)
- Personalización por tipo de huésped
- Sistema de recordatorios con backoff
- Analytics y seguimiento de conversión
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import structlog

from app.core.settings import settings
from app.services.session_manager import SessionManager
from app.services.template_service import TemplateService
from app.services.whatsapp_client import WhatsAppMetaClient as WhatsAppClient

logger = structlog.get_logger(__name__)


class ReviewPlatform(Enum):
    """Plataformas de reseñas soportadas."""

    GOOGLE = "google"
    TRIPADVISOR = "tripadvisor"
    BOOKING = "booking"
    EXPEDIA = "expedia"
    FACEBOOK = "facebook"


class GuestSegment(Enum):
    """Segmentos de huéspedes para personalización."""

    BUSINESS = "business"
    FAMILY = "family"
    COUPLE = "couple"
    SOLO = "solo"
    GROUP = "group"
    VIP = "vip"


@dataclass
class ReviewRequest:
    """Modelo de solicitud de reseña."""

    guest_id: str
    guest_name: str
    booking_id: str
    checkout_date: datetime
    platforms: List[ReviewPlatform]
    segment: GuestSegment
    language: str = "es"
    sent_count: int = 0
    last_sent: Optional[datetime] = None
    responded: bool = False
    review_submitted: bool = False
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class ReviewService:
    """Servicio de gestión de solicitudes de reseñas."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.session_manager = SessionManager()
        self.template_service = TemplateService()
        self.whatsapp_client = WhatsAppClient()

        # Configuration
        self.max_reminders = getattr(settings, "review_max_reminders", 3)
        self.initial_delay_hours = getattr(settings, "review_initial_delay_hours", 24)
        self.reminder_interval_hours = getattr(settings, "review_reminder_interval_hours", 72)

        # Platform URLs (configurable via settings)
        self.platform_urls = {
            ReviewPlatform.GOOGLE: getattr(settings, "google_review_url", "https://g.page/r/EXAMPLE/review"),
            ReviewPlatform.TRIPADVISOR: getattr(
                settings, "tripadvisor_review_url", "https://www.tripadvisor.com/UserReviewEdit-EXAMPLE"
            ),
            ReviewPlatform.BOOKING: getattr(
                settings, "booking_review_url", "https://www.booking.com/reviewcenter/EXAMPLE"
            ),
        }

        # Analytics storage
        self.analytics = {
            "requests_sent": 0,
            "responses_received": 0,
            "reviews_submitted": 0,
            "conversion_rate": 0.0,
            "platform_preferences": {},
            "segment_performance": {},
        }

        self._initialized = True
        logger.info(
            "review_service_initialized",
            max_reminders=self.max_reminders,
            initial_delay=self.initial_delay_hours,
            platforms=list(self.platform_urls.keys()),
        )

    async def schedule_review_request(
        self,
        guest_id: str,
        guest_name: str,
        booking_id: str,
        checkout_date: datetime,
        segment: GuestSegment = GuestSegment.COUPLE,
        language: str = "es",
    ) -> Dict:
        """
        Programa una solicitud de reseña para envío diferido.

        Args:
            guest_id: ID único del huésped (número WhatsApp)
            guest_name: Nombre del huésped
            booking_id: ID de la reserva
            checkout_date: Fecha de checkout
            segment: Segmento del huésped para personalización
            language: Idioma preferido

        Returns:
            dict: Resultado de la programación
        """
        try:
            # Determine platforms based on segment
            platforms = self._get_recommended_platforms(segment)

            # Create review request
            request = ReviewRequest(
                guest_id=guest_id,
                guest_name=guest_name,
                booking_id=booking_id,
                checkout_date=checkout_date,
                platforms=platforms,
                segment=segment,
                language=language,
            )

            # Schedule for initial delay after checkout
            send_time = checkout_date + timedelta(hours=self.initial_delay_hours)

            # Store in session for persistence
            await self._store_review_request(request)

            logger.info(
                "review_request_scheduled",
                guest_id=guest_id,
                booking_id=booking_id,
                send_time=send_time.isoformat(),
                platforms=[p.value for p in platforms],
                segment=segment.value,
            )

            return {
                "success": True,
                "request_id": f"REV_{booking_id}_{guest_id[-4:]}",
                "scheduled_time": send_time.isoformat(),
                "platforms": [p.value for p in platforms],
                "segment": segment.value,
            }

        except Exception as e:
            logger.error(
                "review_request_scheduling_failed",
                guest_id=guest_id,
                booking_id=booking_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return {"success": False, "error": str(e), "request_id": None}

    async def send_review_request(self, guest_id: str, force_send: bool = False) -> Dict:
        """
        Envía solicitud de reseña inmediata o programada.

        Args:
            guest_id: ID del huésped
            force_send: Forzar envío ignorando delays

        Returns:
            dict: Resultado del envío
        """
        try:
            # Get stored request
            request = await self._get_review_request(guest_id)
            if not request:
                return {"success": False, "error": "Review request not found"}

            # Check if ready to send (unless forced)
            if not force_send and not self._is_ready_to_send(request):
                time_until_ready = self._time_until_ready(request)
                return {"success": False, "error": "Not ready to send", "time_until_ready_hours": time_until_ready}

            # Check max reminders
            if request.sent_count >= self.max_reminders:
                return {"success": False, "error": "Max reminders reached", "sent_count": request.sent_count}

            # Generate personalized message
            message_content = await self._generate_review_message(request)

            # Send via WhatsApp
            result = await self.whatsapp_client.send_message(to=guest_id, text=message_content["text"])

            if result.get("success"):
                # Update request tracking
                request.sent_count += 1
                request.last_sent = datetime.utcnow()
                await self._update_review_request(request)

                # Update analytics
                self.analytics["requests_sent"] += 1
                self._update_segment_stats(request.segment, "sent")

                logger.info(
                    "review_request_sent",
                    guest_id=guest_id,
                    booking_id=request.booking_id,
                    sent_count=request.sent_count,
                    platforms=[p.value for p in request.platforms],
                )

                return {
                    "success": True,
                    "message_id": result.get("message_id"),
                    "sent_count": request.sent_count,
                    "platforms": [p.value for p in request.platforms],
                }
            else:
                logger.error("review_request_send_failed", guest_id=guest_id, whatsapp_error=result.get("error"))
                return {"success": False, "error": f"WhatsApp send failed: {result.get('error')}"}

        except Exception as e:
            logger.error("review_request_send_error", guest_id=guest_id, error=str(e), error_type=type(e).__name__)
            return {"success": False, "error": str(e)}

    async def process_review_response(self, guest_id: str, response_text: str) -> Dict:
        """
        Procesa respuesta del huésped a solicitud de reseña.

        Args:
            guest_id: ID del huésped
            response_text: Texto de respuesta

        Returns:
            dict: Resultado del procesamiento
        """
        try:
            request = await self._get_review_request(guest_id)
            if not request:
                return {"success": False, "error": "No review request found"}

            # Analyze response sentiment and intent
            response_analysis = self._analyze_response(response_text)

            # Update request based on response
            if response_analysis["intent"] == "positive":
                request.responded = True

                # Send platform links
                platform_message = await self._generate_platform_links_message(request)

                await self.whatsapp_client.send_message(to=guest_id, text=platform_message["text"])

                self.analytics["responses_received"] += 1
                self._update_segment_stats(request.segment, "responded")

                logger.info(
                    "review_positive_response",
                    guest_id=guest_id,
                    booking_id=request.booking_id,
                    sentiment=response_analysis["sentiment"],
                )

            elif response_analysis["intent"] == "negative":
                # Handle negative feedback privately
                request.responded = True

                feedback_message = await self._generate_feedback_message(request)
                await self.whatsapp_client.send_message(to=guest_id, text=feedback_message["text"])

                logger.info(
                    "review_negative_response",
                    guest_id=guest_id,
                    booking_id=request.booking_id,
                    sentiment=response_analysis["sentiment"],
                )

            elif response_analysis["intent"] == "unsubscribe":
                # Stop future reminders
                request.responded = True
                request.sent_count = self.max_reminders  # Prevent further sends

                logger.info("review_unsubscribe", guest_id=guest_id, booking_id=request.booking_id)

            await self._update_review_request(request)

            return {
                "success": True,
                "intent": response_analysis["intent"],
                "sentiment": response_analysis["sentiment"],
                "action_taken": response_analysis["intent"],
            }

        except Exception as e:
            logger.error(
                "review_response_processing_error", guest_id=guest_id, error=str(e), error_type=type(e).__name__
            )
            return {"success": False, "error": str(e)}

    async def mark_review_submitted(self, guest_id: str, platform: ReviewPlatform) -> Dict:
        """
        Marca reseña como enviada (llamado externamente por webhooks).

        Args:
            guest_id: ID del huésped
            platform: Plataforma donde se envió la reseña

        Returns:
            dict: Resultado de la actualización
        """
        try:
            request = await self._get_review_request(guest_id)
            if request:
                request.review_submitted = True
                await self._update_review_request(request)

                self.analytics["reviews_submitted"] += 1
                self._update_platform_stats(platform)
                self._update_conversion_rate()

                logger.info(
                    "review_submitted_confirmed",
                    guest_id=guest_id,
                    booking_id=request.booking_id,
                    platform=platform.value,
                )

                return {"success": True, "platform": platform.value}
            else:
                return {"success": False, "error": "Request not found"}

        except Exception as e:
            logger.error(
                "review_submission_marking_error",
                guest_id=guest_id,
                platform=platform.value if platform else "unknown",
                error=str(e),
            )
            return {"success": False, "error": str(e)}

    def get_review_analytics(self) -> Dict:
        """
        Obtiene analytics del sistema de reseñas.

        Returns:
            dict: Métricas y estadísticas
        """
        self._update_conversion_rate()

        return {
            "overview": {
                "requests_sent": self.analytics["requests_sent"],
                "responses_received": self.analytics["responses_received"],
                "reviews_submitted": self.analytics["reviews_submitted"],
                "conversion_rate": self.analytics["conversion_rate"],
            },
            "platform_performance": self.analytics["platform_preferences"],
            "segment_performance": self.analytics["segment_performance"],
            "generated_at": datetime.utcnow().isoformat(),
        }

    # Private helper methods

    def _get_recommended_platforms(self, segment: GuestSegment) -> List[ReviewPlatform]:
        """Recomienda plataformas basado en segmento."""
        platform_map = {
            GuestSegment.BUSINESS: [ReviewPlatform.GOOGLE, ReviewPlatform.TRIPADVISOR],
            GuestSegment.FAMILY: [ReviewPlatform.TRIPADVISOR, ReviewPlatform.BOOKING],
            GuestSegment.COUPLE: [ReviewPlatform.GOOGLE, ReviewPlatform.TRIPADVISOR],
            GuestSegment.SOLO: [ReviewPlatform.GOOGLE, ReviewPlatform.BOOKING],
            GuestSegment.GROUP: [ReviewPlatform.TRIPADVISOR, ReviewPlatform.FACEBOOK],
            GuestSegment.VIP: [ReviewPlatform.GOOGLE, ReviewPlatform.TRIPADVISOR, ReviewPlatform.BOOKING],
        }
        return platform_map.get(segment, [ReviewPlatform.GOOGLE])

    def _is_ready_to_send(self, request: ReviewRequest) -> bool:
        """Verifica si la solicitud está lista para envío."""
        now = datetime.utcnow()

        # First send: check initial delay after checkout
        if request.sent_count == 0:
            return now >= request.checkout_date + timedelta(hours=self.initial_delay_hours)

        # Subsequent sends: check reminder interval
        if request.last_sent:
            return now >= request.last_sent + timedelta(hours=self.reminder_interval_hours)

        return False

    def _time_until_ready(self, request: ReviewRequest) -> float:
        """Calcula horas hasta el próximo envío."""
        now = datetime.utcnow()

        if request.sent_count == 0:
            next_send = request.checkout_date + timedelta(hours=self.initial_delay_hours)
        elif request.last_sent:
            next_send = request.last_sent + timedelta(hours=self.reminder_interval_hours)
        else:
            return 0

        delta = next_send - now
        return max(0, delta.total_seconds() / 3600)

    async def _generate_review_message(self, request: ReviewRequest) -> Dict:
        """Genera mensaje personalizado de solicitud de reseña."""
        template_data = {
            "guest_name": request.guest_name,
            "hotel_name": settings.hotel_name,
            "booking_id": request.booking_id,
            "is_reminder": request.sent_count > 0,
            "segment": request.segment.value,
        }

        template_name = f"review_request_{request.segment.value}"
        if request.sent_count > 0:
            template_name += "_reminder"
        return await self.template_service.get_template_dict(template_name, template_data)

    async def _generate_platform_links_message(self, request: ReviewRequest) -> Dict:
        """Genera mensaje con links a plataformas."""
        links = []
        for platform in request.platforms:
            url = self.platform_urls.get(platform, "#")
            links.append(f"{platform.value.title()}: {url}")

        template_data = {"guest_name": request.guest_name, "platform_links": "\n".join(links)}
        return await self.template_service.get_template_dict("review_platform_links", template_data)

    async def _generate_feedback_message(self, request: ReviewRequest) -> Dict:
        """Genera mensaje para feedback negativo."""
        template_data = {"guest_name": request.guest_name, "hotel_name": settings.hotel_name}
        return await self.template_service.get_template_dict("review_negative_feedback", template_data)

    def _analyze_response(self, text: str) -> Dict:
        """Analiza respuesta del huésped."""
        text_lower = text.lower()

        # Positive indicators
        positive_words = ["sí", "si", "claro", "perfecto", "excelente", "bueno", "me gustó"]
        negative_words = ["no", "malo", "horrible", "problema", "queja", "molesto"]
        unsubscribe_words = ["no más", "basta", "no quiero", "déjame", "no molesten"]

        positive_score = sum(1 for word in positive_words if word in text_lower)
        negative_score = sum(1 for word in negative_words if word in text_lower)
        unsubscribe_score = sum(1 for word in unsubscribe_words if word in text_lower)

        if unsubscribe_score > 0:
            return {"intent": "unsubscribe", "sentiment": "negative"}
        elif positive_score > negative_score:
            return {"intent": "positive", "sentiment": "positive"}
        elif negative_score > positive_score:
            return {"intent": "negative", "sentiment": "negative"}
        else:
            return {"intent": "neutral", "sentiment": "neutral"}

    async def _store_review_request(self, request: ReviewRequest):
        """Almacena solicitud en sesión."""
        session_key = f"review_request_{request.guest_id}"
        data = {
            "guest_id": request.guest_id,
            "guest_name": request.guest_name,
            "booking_id": request.booking_id,
            "checkout_date": request.checkout_date.isoformat(),
            "platforms": [p.value for p in request.platforms],
            "segment": request.segment.value,
            "language": request.language,
            "sent_count": request.sent_count,
            "last_sent": request.last_sent.isoformat() if request.last_sent else None,
            "responded": request.responded,
            "review_submitted": request.review_submitted,
            "created_at": (request.created_at or datetime.utcnow()).isoformat(),
        }

        await self.session_manager.set_session_data(request.guest_id, session_key, data)

    async def _get_review_request(self, guest_id: str) -> Optional[ReviewRequest]:
        """Recupera solicitud de sesión."""
        session_key = f"review_request_{guest_id}"
        data = await self.session_manager.get_session_data(guest_id)
        context = data.get("context", {}) if isinstance(data, dict) else {}
        request_data = context.get(session_key)
        if not request_data:
            return None

        return ReviewRequest(
            guest_id=request_data["guest_id"],
            guest_name=request_data["guest_name"],
            booking_id=request_data["booking_id"],
            checkout_date=datetime.fromisoformat(request_data["checkout_date"]),
            platforms=[ReviewPlatform(p) for p in request_data["platforms"]],
            segment=GuestSegment(request_data["segment"]),
            language=request_data["language"],
            sent_count=request_data["sent_count"],
            last_sent=datetime.fromisoformat(request_data["last_sent"]) if request_data["last_sent"] else None,
            responded=request_data["responded"],
            review_submitted=request_data["review_submitted"],
            created_at=datetime.fromisoformat(request_data["created_at"]),
        )

    async def _update_review_request(self, request: ReviewRequest):
        """Actualiza solicitud en sesión."""
        await self._store_review_request(request)

    def _update_segment_stats(self, segment: GuestSegment, action: str):
        """Actualiza estadísticas por segmento."""
        if segment.value not in self.analytics["segment_performance"]:
            self.analytics["segment_performance"][segment.value] = {"sent": 0, "responded": 0, "submitted": 0}

        self.analytics["segment_performance"][segment.value][action] += 1

    def _update_platform_stats(self, platform: ReviewPlatform):
        """Actualiza estadísticas por plataforma."""
        platform_val = platform.value
        if platform_val not in self.analytics["platform_preferences"]:
            self.analytics["platform_preferences"][platform_val] = 0

        self.analytics["platform_preferences"][platform_val] += 1

    def _update_conversion_rate(self):
        """Actualiza tasa de conversión."""
        if self.analytics["requests_sent"] > 0:
            self.analytics["conversion_rate"] = (
                self.analytics["reviews_submitted"] / self.analytics["requests_sent"]
            ) * 100


# Singleton getter
def get_review_service() -> ReviewService:
    """Obtiene instancia singleton del servicio de reseñas."""
    return ReviewService()
