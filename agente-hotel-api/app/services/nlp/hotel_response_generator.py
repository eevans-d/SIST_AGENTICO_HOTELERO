"""
Hotel Response Generator
Intelligent response generation with contextual awareness and multilingual support
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum
import random

from .enhanced_nlp_engine import IntentType
from .hotel_context_processor import ConversationContext, ConversationState, ReservationStatus

logger = logging.getLogger(__name__)


class ResponseType(Enum):
    """Types of responses"""

    GREETING = "greeting"
    INFORMATION_REQUEST = "information_request"
    CONFIRMATION = "confirmation"
    SUCCESS = "success"
    ERROR = "error"
    CLARIFICATION = "clarification"
    ESCALATION = "escalation"
    GOODBYE = "goodbye"


class ResponseTone(Enum):
    """Response tone options"""

    FORMAL = "formal"
    FRIENDLY = "friendly"
    URGENT = "urgent"
    EMPATHETIC = "empathetic"
    PROFESSIONAL = "professional"


@dataclass
class ResponseTemplate:
    """Template for generating responses"""

    intent: IntentType
    response_type: ResponseType
    templates: List[str]
    tone: ResponseTone = ResponseTone.FRIENDLY
    requires_entities: List[str] = None
    follow_up_questions: List[str] = None


class HotelResponseGenerator:
    """Advanced response generator for hotel conversations"""

    def __init__(self):
        self.response_templates = self._initialize_templates()
        self.business_info = self._initialize_business_info()
        self.multilingual_support = {"es": "spanish", "en": "english", "fr": "french"}

        logger.info("HotelResponseGenerator initialized")

    def _initialize_templates(self) -> Dict[Tuple[IntentType, ResponseType], ResponseTemplate]:
        """Initialize response templates"""
        templates = {}

        # Greeting responses
        templates[(IntentType.GREETING, ResponseType.GREETING)] = ResponseTemplate(
            intent=IntentType.GREETING,
            response_type=ResponseType.GREETING,
            templates=[
                "¡Hola! Bienvenido/a al Hotel Paradise. ¿En qué puedo ayudarle hoy?",
                "Buenos días. Soy su asistente virtual del Hotel Paradise. ¿Cómo puedo asistirle?",
                "¡Saludos! Estoy aquí para ayudarle con cualquier consulta sobre nuestro hotel.",
                "Hola, es un placer atenderle. ¿En qué puedo ser de utilidad?",
            ],
        )

        # Room booking - information request
        templates[(IntentType.BOOK_ROOM, ResponseType.INFORMATION_REQUEST)] = ResponseTemplate(
            intent=IntentType.BOOK_ROOM,
            response_type=ResponseType.INFORMATION_REQUEST,
            templates=[
                "Perfecto, le ayudo con su reserva. {missing_info}",
                "Será un placer gestionar su reserva. {missing_info}",
                "Excelente, procedamos con su reserva. {missing_info}",
            ],
            requires_entities=["checkin_date", "checkout_date", "guest_count", "guest_name"],
        )

        # Availability check
        templates[(IntentType.CHECK_AVAILABILITY, ResponseType.INFORMATION_REQUEST)] = ResponseTemplate(
            intent=IntentType.CHECK_AVAILABILITY,
            response_type=ResponseType.INFORMATION_REQUEST,
            templates=[
                "Con gusto verifico la disponibilidad para usted. {missing_info}",
                "Le consulto disponibilidad inmediatamente. {missing_info}",
                "Permítame revisar nuestras habitaciones disponibles. {missing_info}",
            ],
            requires_entities=["checkin_date"],
        )

        # Room service
        templates[(IntentType.ROOM_SERVICE, ResponseType.INFORMATION_REQUEST)] = ResponseTemplate(
            intent=IntentType.ROOM_SERVICE,
            response_type=ResponseType.INFORMATION_REQUEST,
            templates=[
                "Claro, le ayudo con room service. {missing_info}",
                "Perfecto, gestiono su pedido de room service. {missing_info}",
                "Será un placer atender su solicitud de room service. {missing_info}",
            ],
            requires_entities=["room_number", "service_type"],
        )

        # Complaints
        templates[(IntentType.COMPLAINT, ResponseType.EMPATHETIC)] = ResponseTemplate(
            intent=IntentType.COMPLAINT,
            response_type=ResponseType.ESCALATION,
            tone=ResponseTone.EMPATHETIC,
            templates=[
                "Lamento mucho el inconveniente. Su satisfacción es nuestra prioridad. {escalation_info}",
                "Disculpe las molestias causadas. Voy a resolver esto inmediatamente. {escalation_info}",
                "Entiendo su frustración y me haré cargo personalmente del problema. {escalation_info}",
            ],
        )

        # Confirmations
        templates[(IntentType.BOOK_ROOM, ResponseType.CONFIRMATION)] = ResponseTemplate(
            intent=IntentType.BOOK_ROOM,
            response_type=ResponseType.CONFIRMATION,
            templates=[
                "Perfecto, confirmo su reserva: {reservation_summary}. ¿Es correcto?",
                "Excelente, aquí está el resumen de su reserva: {reservation_summary}. ¿Procedo con la confirmación?",
                "Muy bien, estos son los detalles de su reserva: {reservation_summary}. ¿Todo está correcto?",
            ],
        )

        # Success responses
        templates[(IntentType.BOOK_ROOM, ResponseType.SUCCESS)] = ResponseTemplate(
            intent=IntentType.BOOK_ROOM,
            response_type=ResponseType.SUCCESS,
            templates=[
                "¡Excelente! Su reserva ha sido confirmada exitosamente. {confirmation_details}",
                "¡Perfecto! Hemos procesado su reserva. {confirmation_details}",
                "¡Fantástico! Su reserva está confirmada. {confirmation_details}",
            ],
        )

        # Information responses
        templates[(IntentType.HOTEL_INFO, ResponseType.INFORMATION_REQUEST)] = ResponseTemplate(
            intent=IntentType.HOTEL_INFO,
            response_type=ResponseType.INFORMATION_REQUEST,
            templates=[
                "Con gusto le proporciono información sobre nuestro hotel. {hotel_info}",
                "Será un placer contarle sobre nuestras instalaciones. {hotel_info}",
                "Le comparto la información que necesita sobre el hotel. {hotel_info}",
            ],
        )

        # Clarification requests
        templates[(IntentType.UNCLEAR, ResponseType.CLARIFICATION)] = ResponseTemplate(
            intent=IntentType.UNCLEAR,
            response_type=ResponseType.CLARIFICATION,
            templates=[
                "Disculpe, no logré entender completamente su solicitud. ¿Podría ser más específico?",
                "Perdón, ¿podría explicarme mejor qué necesita? Estoy aquí para ayudarle.",
                "Lo siento, no estoy seguro de haber comprendido. ¿Podría reformular su pregunta?",
            ],
        )

        # Goodbye responses
        templates[(IntentType.GOODBYE, ResponseType.GOODBYE)] = ResponseTemplate(
            intent=IntentType.GOODBYE,
            response_type=ResponseType.GOODBYE,
            templates=[
                "¡Gracias por contactarnos! Esperamos verle pronto en el Hotel Paradise.",
                "Ha sido un placer atenderle. ¡Que tenga un excelente día!",
                "Gracias por su confianza. Estamos siempre a su disposición.",
            ],
        )

        return templates

    def _initialize_business_info(self) -> Dict[str, Any]:
        """Initialize hotel business information"""
        return {
            "hotel_name": "Hotel Paradise",
            "address": "Avenida Principal 123, Ciudad Turística",
            "phone": "+1-555-0123",
            "email": "reservas@hotelparadise.com",
            "checkin_time": "15:00",
            "checkout_time": "12:00",
            "amenities": [
                "Piscina al aire libre",
                "Spa y centro de bienestar",
                "Gimnasio 24 horas",
                "Restaurante gourmet",
                "Bar en la azotea",
                "WiFi gratuito",
                "Estacionamiento",
                "Room service 24/7",
                "Servicio de lavandería",
                "Centro de negocios",
            ],
            "room_types": {
                "standard": {
                    "name": "Habitación Standard",
                    "capacity": 2,
                    "price": 150,
                    "amenities": ["TV", "WiFi", "Aire acondicionado", "Minibar"],
                },
                "deluxe": {
                    "name": "Habitación Deluxe",
                    "capacity": 2,
                    "price": 220,
                    "amenities": ["TV", "WiFi", "Aire acondicionado", "Minibar", "Balcón", "Vista al mar"],
                },
                "suite": {
                    "name": "Suite Junior",
                    "capacity": 4,
                    "price": 350,
                    "amenities": [
                        "Sala separada",
                        "TV",
                        "WiFi",
                        "Aire acondicionado",
                        "Minibar",
                        "Jacuzzi",
                        "Vista panorámica",
                    ],
                },
            },
            "services": {
                "room_service": "Disponible 24/7",
                "housekeeping": "Servicio diario de limpieza",
                "concierge": "Asistencia turística y reservas",
                "laundry": "Servicio de lavandería express",
                "transportation": "Transporte al aeropuerto",
            },
        }

    async def generate_response(
        self, context: ConversationContext, processing_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate contextual response based on conversation state"""

        # Determine response type based on context
        response_type = self._determine_response_type(context, processing_result)

        # Determine tone based on sentiment and urgency
        tone = self._determine_tone(context)

        # Generate main response
        main_response = await self._generate_main_response(context, processing_result, response_type, tone)

        # Generate follow-up questions if needed
        follow_up = await self._generate_follow_up(context, processing_result)

        # Add quick reply options
        quick_replies = self._generate_quick_replies(context, processing_result)

        # Format final response
        formatted_response = self._format_response(main_response, follow_up, quick_replies, tone)

        return {
            "text": formatted_response["text"],
            "quick_replies": formatted_response["quick_replies"],
            "metadata": {
                "response_type": response_type.value,
                "tone": tone.value,
                "confidence": processing_result.get("confidence", 0.0),
                "generated_at": datetime.now().isoformat(),
                "requires_human_intervention": processing_result.get("requires_escalation", False),
            },
        }

    def _determine_response_type(self, context: ConversationContext, processing_result: Dict[str, Any]) -> ResponseType:
        """Determine the appropriate response type"""

        # Check if escalation is needed
        if processing_result.get("requires_escalation", False):
            return ResponseType.ESCALATION

        # Check conversation state
        if context.state == ConversationState.INITIAL:
            return ResponseType.GREETING

        elif context.state == ConversationState.COLLECTING_INFO:
            if processing_result.get("missing_information", {}).get("required_entities"):
                return ResponseType.INFORMATION_REQUEST
            else:
                return ResponseType.CONFIRMATION

        elif context.state == ConversationState.CONFIRMING:
            return ResponseType.CONFIRMATION

        elif context.state == ConversationState.PROCESSING:
            return ResponseType.SUCCESS

        elif context.state == ConversationState.ESCALATED:
            return ResponseType.ESCALATION

        # Check intent-specific responses
        if context.current_intent == IntentType.UNCLEAR:
            return ResponseType.CLARIFICATION
        elif context.current_intent == IntentType.GOODBYE:
            return ResponseType.GOODBYE
        elif context.current_intent == IntentType.COMPLAINT:
            return ResponseType.ESCALATION

        return ResponseType.INFORMATION_REQUEST

    def _determine_tone(self, context: ConversationContext) -> ResponseTone:
        """Determine appropriate response tone"""

        if context.urgency_level == "high":
            return ResponseTone.URGENT

        if context.sentiment_score < -0.3:
            return ResponseTone.EMPATHETIC

        if context.current_intent in [IntentType.COMPLAINT, IntentType.EMERGENCY]:
            return ResponseTone.EMPATHETIC

        if context.current_intent in [IntentType.BOOK_ROOM, IntentType.CHECK_AVAILABILITY]:
            return ResponseTone.PROFESSIONAL

        return ResponseTone.FRIENDLY

    async def _generate_main_response(
        self,
        context: ConversationContext,
        processing_result: Dict[str, Any],
        response_type: ResponseType,
        tone: ResponseTone,
    ) -> str:
        """Generate the main response text"""

        # Get template
        template_key = (context.current_intent, response_type)
        template = self.response_templates.get(template_key)

        if not template:
            # Fallback to generic response
            return self._generate_fallback_response(context, response_type)

        # Select random template
        template_text = random.choice(template.templates)

        # Fill template placeholders
        filled_template = await self._fill_template_placeholders(template_text, context, processing_result)

        return filled_template

    async def _fill_template_placeholders(
        self, template: str, context: ConversationContext, processing_result: Dict[str, Any]
    ) -> str:
        """Fill template placeholders with actual data"""

        # Missing information placeholder
        if "{missing_info}" in template:
            missing_info = self._format_missing_info(processing_result)
            template = template.replace("{missing_info}", missing_info)

        # Reservation summary placeholder
        if "{reservation_summary}" in template:
            summary = self._format_reservation_summary(context)
            template = template.replace("{reservation_summary}", summary)

        # Hotel information placeholder
        if "{hotel_info}" in template:
            hotel_info = self._format_hotel_info(context)
            template = template.replace("{hotel_info}", hotel_info)

        # Confirmation details placeholder
        if "{confirmation_details}" in template:
            details = self._format_confirmation_details(context)
            template = template.replace("{confirmation_details}", details)

        # Escalation information placeholder
        if "{escalation_info}" in template:
            escalation_info = "Un especialista se contactará con usted en breve para resolver este inconveniente."
            template = template.replace("{escalation_info}", escalation_info)

        return template

    def _format_missing_info(self, processing_result: Dict[str, Any]) -> str:
        """Format missing information request"""
        missing_entities = processing_result.get("missing_information", {}).get("required_entities", [])

        if not missing_entities:
            return "Tengo toda la información necesaria."

        # Get the first missing entity
        first_missing = missing_entities[0]
        return first_missing.get("prompt", "¿Podría proporcionarme más información?")

    def _format_reservation_summary(self, context: ConversationContext) -> str:
        """Format reservation summary"""
        reservation = context.reservation_context

        summary_parts = []

        if "guest_name" in reservation:
            summary_parts.append(f"Huésped: {reservation['guest_name']}")

        if "checkin_date" in reservation:
            checkin = reservation["checkin_date"]
            if isinstance(checkin, date):
                summary_parts.append(f"Entrada: {checkin.strftime('%d/%m/%Y')}")
            else:
                summary_parts.append(f"Entrada: {checkin}")

        if "checkout_date" in reservation:
            checkout = reservation["checkout_date"]
            if isinstance(checkout, date):
                summary_parts.append(f"Salida: {checkout.strftime('%d/%m/%Y')}")
            else:
                summary_parts.append(f"Salida: {checkout}")

        if "guest_count" in reservation:
            summary_parts.append(f"Huéspedes: {reservation['guest_count']}")

        if "room_type" in reservation:
            summary_parts.append(f"Tipo: {reservation['room_type']}")

        return "; ".join(summary_parts) if summary_parts else "Procesando detalles de reserva"

    def _format_hotel_info(self, context: ConversationContext) -> str:
        """Format hotel information"""
        info_parts = [
            f"Estamos ubicados en {self.business_info['address']}",
            f"Check-in: {self.business_info['checkin_time']}",
            f"Check-out: {self.business_info['checkout_time']}",
        ]

        # Add amenities if relevant
        if context.current_intent == IntentType.AMENITIES:
            amenities = ", ".join(self.business_info["amenities"][:3])
            info_parts.append(f"Amenidades principales: {amenities}")

        return ". ".join(info_parts)

    def _format_confirmation_details(self, context: ConversationContext) -> str:
        """Format confirmation details"""
        details = [
            f"Número de confirmación: #RES{random.randint(100000, 999999)}",
            "Recibirá un email con todos los detalles",
            f"Para consultas: {self.business_info['phone']}",
        ]

        return ". ".join(details)

    def _generate_fallback_response(self, context: ConversationContext, response_type: ResponseType) -> str:
        """Generate fallback response when no template is found"""
        fallbacks = {
            ResponseType.GREETING: "Hola, ¿en qué puedo ayudarle?",
            ResponseType.INFORMATION_REQUEST: "¿Podría proporcionarme más información?",
            ResponseType.CONFIRMATION: "¿Es correcta esta información?",
            ResponseType.SUCCESS: "Perfecto, su solicitud ha sido procesada.",
            ResponseType.ERROR: "Disculpe, ha ocurrido un error. Inténtelo nuevamente.",
            ResponseType.CLARIFICATION: "¿Podría ser más específico en su solicitud?",
            ResponseType.ESCALATION: "Un especialista le atenderá en breve.",
            ResponseType.GOODBYE: "Gracias por contactarnos. ¡Que tenga un buen día!",
        }

        return fallbacks.get(response_type, "¿En qué más puedo ayudarle?")

    async def _generate_follow_up(
        self, context: ConversationContext, processing_result: Dict[str, Any]
    ) -> Optional[str]:
        """Generate follow-up questions or suggestions"""

        # If we need more information
        missing_entities = processing_result.get("missing_information", {}).get("required_entities", [])
        if len(missing_entities) > 1:
            second_missing = missing_entities[1]
            return f"También necesitaré saber: {second_missing.get('prompt', '')}"

        # Context-specific follow-ups
        if context.current_intent == IntentType.BOOK_ROOM:
            if context.reservation_status == ReservationStatus.READY_TO_BOOK:
                return "¿Le gustaría añadir algún servicio especial a su estadía?"

        elif context.current_intent == IntentType.CHECK_AVAILABILITY:
            return "¿Le interesa conocer nuestras tarifas y promociones actuales?"

        elif context.current_intent == IntentType.HOTEL_INFO:
            return "¿Le gustaría conocer más sobre algún servicio en particular?"

        return None

    def _generate_quick_replies(self, context: ConversationContext, processing_result: Dict[str, Any]) -> List[str]:
        """Generate quick reply options"""
        quick_replies = []

        # State-based quick replies
        if context.state == ConversationState.COLLECTING_INFO:
            if context.current_intent == IntentType.BOOK_ROOM:
                quick_replies = ["Habitación Standard", "Habitación Deluxe", "Suite", "Ver precios"]
            elif context.current_intent == IntentType.ROOM_SERVICE:
                quick_replies = ["Comida", "Bebidas", "Amenidades", "Servicio de limpieza"]

        elif context.state == ConversationState.CONFIRMING:
            quick_replies = ["Sí, confirmar", "No, modificar", "Cancelar"]

        elif context.state == ConversationState.INITIAL:
            quick_replies = ["Hacer reserva", "Consultar disponibilidad", "Room service", "Información del hotel"]

        # Intent-specific quick replies
        if context.current_intent == IntentType.HOTEL_INFO:
            quick_replies = ["Amenidades", "Ubicación", "Contacto", "Precios"]

        return quick_replies[:4]  # Limit to 4 options

    def _format_response(
        self, main_text: str, follow_up: Optional[str], quick_replies: List[str], tone: ResponseTone
    ) -> Dict[str, Any]:
        """Format the final response"""

        # Combine main text and follow-up
        full_text = main_text
        if follow_up:
            full_text += f"\n\n{follow_up}"

        # Add tone-appropriate ending
        if tone == ResponseTone.EMPATHETIC:
            full_text += "\n\nEstamos comprometidos con su satisfacción."
        elif tone == ResponseTone.URGENT:
            full_text += "\n\nLe atenderemos con la máxima prioridad."
        elif tone == ResponseTone.PROFESSIONAL:
            full_text += "\n\n¿En qué más puedo asistirle?"

        return {"text": full_text, "quick_replies": quick_replies}

    async def generate_error_response(self, error_type: str, context: Optional[ConversationContext] = None) -> str:
        """Generate error response"""
        error_responses = {
            "system_error": "Disculpe, tenemos un problema técnico. Por favor, inténtelo en unos momentos.",
            "timeout": "Su sesión ha expirado. Por favor, inicie una nueva conversación.",
            "invalid_input": "No pude procesar su mensaje. ¿Podría reformularlo?",
            "rate_limit": "Ha enviado demasiados mensajes. Por favor, espere un momento.",
            "maintenance": "Estamos en mantenimiento. El servicio estará disponible pronto.",
        }

        base_response = error_responses.get(error_type, "Ha ocurrido un error. Por favor, contacte a recepción.")

        # Add escalation if context shows frustration
        if context and context.sentiment_score < -0.5:
            base_response += " Un agente se comunicará con usted inmediatamente."

        return base_response


# Global instance
_response_generator = None


def get_response_generator() -> HotelResponseGenerator:
    """Get global response generator instance"""
    global _response_generator
    if _response_generator is None:
        _response_generator = HotelResponseGenerator()
    return _response_generator
