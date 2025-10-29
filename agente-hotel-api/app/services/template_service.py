# [PROMPT 2.7] app/services/template_service.py

from typing import Dict, Any

"""
Servicio de plantillas con soporte básico de i18n.

- Idioma por defecto: 'es'
- Fallback: si una clave no existe en el idioma actual, usa 'es'
- Compatibilidad retro: si no se configura idioma, retorna en español
"""


# Plantillas de texto simple (ES)
TEXT_TEMPLATES_ES = {
    "availability_found": "Para {checkin}-{checkout}, {room_type} para {guests}: ${price}/noche. Total ${total}. ¿Querés reservar? 🏨",
    "reservation_instructions": "Perfecto! Reservé temporalmente la habitación.\n\nPara confirmar, enviá seña del 30%: ${deposit}\n\nDatos bancarios:\n🏦 {bank_info}\n\nEnviame el comprobante por acá 📄",
    "no_availability": "Lo siento, no hay disponibilidad para esas fechas. ¿Te sirven estas alternativas?\n\n{alternatives}",
    "confirmation_received": "¡Excelente! Hemos recibido tu confirmación. Tu reserva está completa.",
    "help_message": "Puedo ayudarte con lo siguiente:",
    "guest_services": "Nuestros servicios para huéspedes incluyen: WiFi gratuito, desayuno continental de 7:00 a 10:00, servicio de limpieza diario, recepción 24 horas, y servicio de lavandería. ¿Necesitas información específica sobre algún servicio?",
    "hotel_amenities": "Nuestras amenidades incluyen: piscina al aire libre, gimnasio con equipos modernos, restaurante con comida internacional, bar, centro de negocios, estacionamiento gratuito, y spa con tratamientos relajantes. ¿Te interesa conocer más detalles de alguna?",
    "check_in_info": "El check-in es a partir de las 15:00 horas. Necesitarás tu documento de identidad y la confirmación de reserva. Si llegas antes, podemos guardar tu equipaje sin costo adicional. ¿Tienes alguna consulta específica?",
    "check_out_info": "El check-out es hasta las 12:00 horas. Puedes solicitar extensión hasta las 14:00 por un cargo adicional del 50% de la tarifa diaria. También ofrecemos servicio de guardado de equipaje si tu vuelo es más tarde.",
    "cancellation_policy": "Nuestra política de cancelación permite cancelación gratuita hasta 24 horas antes del check-in. Cancelaciones posteriores tienen un cargo del 50% de la primera noche. Para reservas no reembolsables, no se permiten cancelaciones.",
    # NEW: After-hours templates
    "after_hours_standard": "Gracias por contactarnos. 🌙\n\nActualmente estamos fuera de horario de atención.\nNuestro horario es: {business_hours}\n\nTe responderemos mañana a las {next_open_time}.\n\n¿Es urgente? Responde 'URGENTE' y te derivamos con personal de guardia.",
    "after_hours_weekend": "Gracias por tu mensaje. 😊\n\nHoy es fin de semana y nuestro horario es reducido.\nTe responderemos el lunes a primera hora.\n\nPara emergencias, responde 'URGENTE'.",
    "escalated_to_staff": "Entendido, derivando tu consulta al personal de guardia. ⚡\nAlguien te contactará en breve.",
    # NEW: Location request response
    "location_info": "📍 Aquí está nuestra ubicación:",
    # NEW: Image sending
    "room_photo_caption": "✨ {room_type}\n💰 ${price}/noche\n👥 Capacidad: {guests} persona(s)\n\n¿Te gusta? ¡Reservala ahora!",
    # NEW: Late checkout templates
    "late_checkout_available": "¡Perfecto! Late checkout disponible hasta las {checkout_time} ✅\n\n💰 Cargo adicional: ${fee} (50% tarifa diaria)\n\n¿Confirmas el late checkout?",
    "late_checkout_not_available": "Lo siento, no hay disponibilidad para late checkout. 😔\n\nLa habitación está reservada para otro huésped.\n\nHorario estándar de checkout: {standard_time}\n\n¿Necesitas guardar equipaje? Ofrecemos servicio gratuito.",
    "late_checkout_confirmed": "¡Listo! ✅ Late checkout confirmado hasta las {checkout_time}.\n\n💰 Cargo: ${fee}\n\nSe agregará a tu cuenta. ¡Disfruta tu estadía extendida!",
    "late_checkout_no_booking": "Para solicitar late checkout, necesito tu número de reserva.\n\n¿Podrías compartirlo?",
    "late_checkout_already_day": "El horario de checkout ya pasó. 😅\n\nPara extensiones de último momento, contacta a recepción directamente al [TELÉFONO].",
    "late_checkout_free": "¡Buenas noticias! 🎉\n\nLate checkout hasta las {checkout_time} sin cargo adicional.\n\n¿Lo confirmas?",
    # NEW: QR Code confirmation templates
    "booking_confirmed_with_qr": "🎉 ¡RESERVA CONFIRMADA! 🎉\n\n📋 Detalles de tu reserva:\n• Reserva: {booking_id}\n• Huésped: {guest_name}\n• Check-in: {check_in}\n• Check-out: {check_out}\n• Habitación: {room_number}\n\n🎫 Te enviamos tu código QR de confirmación.\n¡Guárdalo para facilitar tu check-in!",
    "booking_confirmed_no_qr": "🎉 ¡RESERVA CONFIRMADA! 🎉\n\n📋 Detalles de tu reserva:\n• Reserva: {booking_id}\n• Check-in: {check_in}\n• Check-out: {check_out}\n\n✅ Tu reserva está confirmada.\nRecibirás más detalles por email.",
    # NEW: Review request templates - Feature 6
    "review_request_couple": "¡Hola {guest_name}! 👋\n\nEsperamos que hayan disfrutado muchísimo su estadía en {hotel_name}.\n\nNos encantaría conocer su experiencia 💭 Sus comentarios nos ayudan a seguir mejorando para futuros huéspedes.\n\n¿Podrían tomarse unos minutos para dejarnos una reseña? ⭐\n\n¡Muchas gracias! 🙏\nReserva: {booking_id}",
    "review_request_business": "Estimado/a {guest_name},\n\nEsperamos que su estadía en {hotel_name} haya cumplido con sus expectativas profesionales.\n\nValoramos mucho su feedback sobre nuestros servicios empresariales. Sus comentarios nos permiten optimizar la experiencia para ejecutivos como usted.\n\n¿Podría dedicar unos minutos a compartir su experiencia? Su opinión es muy importante para nosotros.\n\nSaludos cordiales,\nEquipo {hotel_name}\nRef: {booking_id}",
    "review_request_family": "¡Hola familia {guest_name}! 👨‍👩‍👧‍👦\n\n¡Esperamos que todos hayan pasado momentos increíbles en {hotel_name}!\n\nNos hace muy felices cuando las familias disfrutan de su tiempo con nosotros 😊\n\n¿Les gustaría contarnos sobre su experiencia? Sus comentarios nos ayudan a crear mejores momentos familiares.\n\n¡Mil gracias! 🌟\nReserva: {booking_id}",
    "review_request_solo": "Hola {guest_name}!\n\nEsperamos que hayas disfrutado tu estadía en {hotel_name} y que haya sido exactamente lo que necesitabas.\n\nNos importa mucho la experiencia de cada viajero individual. ¿Podrías contarnos cómo fue tu estadía?\n\nTu opinión nos ayuda a mejorar para futuros huéspedes que viajan solos como tú.\n\n¡Gracias! ✨\nReserva: {booking_id}",
    "review_request_group": "¡Hola a todo el grupo de {guest_name}! 🎉\n\n¡Esperamos que hayan tenido una experiencia fantástica en {hotel_name}!\n\nLos grupos como el suyo traen mucha energía positiva al hotel. ¿Les gustaría compartir cómo fue su experiencia con nosotros?\n\nSus comentarios nos ayudan a seguir siendo el lugar perfecto para reuniones especiales.\n\n¡Muchas gracias por elegirnos! 🙌\nReserva: {booking_id}",
    "review_request_vip": "Estimado/a {guest_name},\n\nHa sido un verdadero placer tenerle como huésped VIP en {hotel_name}.\n\nComo miembro de nuestro círculo exclusivo, su opinión tiene un valor especial para nosotros. Nos encantaría conocer su experiencia con nuestros servicios premium.\n\n¿Podría dedicar unos momentos a compartir sus impresiones? Su feedback nos permite mantener la excelencia en cada detalle.\n\nCon nuestro mayor respeto y gratitud,\nEquipo VIP {hotel_name}\nReserva: {booking_id}",
    "review_request_couple_reminder": "Hola de nuevo {guest_name}! 😊\n\nSolo queríamos recordarles gentilmente sobre la reseña de su estadía en {hotel_name}.\n\nEntendemos que están ocupados, pero su opinión realmente marca la diferencia para nosotros y para otros huéspedes.\n\n¿Podrían ayudarnos con una reseña rápida? ⭐\n\n¡Gracias por su tiempo!\nReserva: {booking_id}",
    "review_request_business_reminder": "Estimado/a {guest_name},\n\nRecordatorio amable sobre su estadía en {hotel_name} (Ref: {booking_id}).\n\nSabemos que su agenda es muy ajustada, pero agradeceríamos enormemente su feedback profesional sobre nuestros servicios.\n\nUna breve reseña nos ayudaría mucho a seguir mejorando para ejecutivos como usted.\n\nCordiales saludos,\nEquipo {hotel_name}",
    "review_platform_links": "¡Perfecto {guest_name}! 🌟\n\nAquí están los enlaces donde puede dejarnos su reseña:\n\n{platform_links}\n\nSolo toma unos minutos y nos ayuda enormemente. ¡Mil gracias por tomarse el tiempo! 🙏\n\nSi necesita ayuda con algún enlace, no dude en escribirnos.",
    "review_negative_feedback": "Hola {guest_name},\n\nLamentamos que su experiencia en {hotel_name} no haya sido completamente satisfactoria.\n\nSu feedback es muy valioso para nosotros. ¿Podría contarnos más detalles sobre lo que podríamos haber hecho mejor?\n\nNos tomamos muy en serio todos los comentarios y trabajamos constantemente para mejorar.\n\nSi hay algo específico que podamos resolver, estaremos encantados de ayudarle.\n\nSaludos cordiales,\nGerencia {hotel_name}",
    # Fallback cuando NLP falla gravemente
    "fallback_human_needed": "Estoy teniendo dificultades para entender tu solicitud ahora mismo. Derivaré tu consulta a un agente humano para ayudarte mejor.",
    # Información de tarifas
    "pricing_info": "Nuestras tarifas varían según temporada y tipo de habitación. ¿Te interesan opciones estándar o premium? También puedo verificar disponibilidad para tus fechas.",
}

# Plantillas de texto simple (EN)
TEXT_TEMPLATES_EN = {
    "availability_found": "For {checkin}-{checkout}, {room_type} for {guests}: ${price}/night. Total ${total}. Would you like to book? 🏨",
    "reservation_instructions": "Great! I've held the room temporarily.\n\nTo confirm, please send a 30% deposit: ${deposit}\n\nBank details:\n🏦 {bank_info}\n\nSend me the receipt here 📄",
    "no_availability": "Sorry, there's no availability for those dates. Do these alternatives work?\n\n{alternatives}",
    "confirmation_received": "Excellent! We've received your confirmation. Your reservation is complete.",
    "help_message": "I can help you with the following:",
    "guest_services": "Our guest services include: Free WiFi, continental breakfast from 7:00 to 10:00, daily housekeeping, 24-hour reception, and laundry service. Do you need details about any service?",
    "hotel_amenities": "Our amenities include: outdoor pool, gym with modern equipment, restaurant with international cuisine, bar, business center, free parking, and a spa with relaxing treatments. Interested in more details about any of them?",
    "check_in_info": "Check-in starts at 15:00. You'll need your ID and the reservation confirmation. If you arrive earlier, we can store your luggage at no extra cost. Any specific questions?",
    "check_out_info": "Check-out is until 12:00. You can request an extension until 14:00 for an additional 50% of the daily rate. We also offer luggage storage if your flight is later.",
    "cancellation_policy": "Our cancellation policy allows free cancellation up to 24 hours before check-in. Later cancellations have a 50% charge of the first night. Non-refundable reservations cannot be canceled.",
    "after_hours_standard": "Thanks for contacting us. 🌙\n\nWe're currently outside business hours.\nOur hours are: {business_hours}\n\nWe'll reply tomorrow at {next_open_time}.\n\nIs it urgent? Reply 'URGENT' and we'll escalate to on-call staff.",
    "after_hours_weekend": "Thanks for your message. 😊\n\nIt's the weekend and our hours are reduced.\nWe'll get back to you on Monday first thing.\n\nFor emergencies, reply 'URGENT'.",
    "escalated_to_staff": "Understood, escalating your request to on-call staff. ⚡ Someone will contact you shortly.",
    "location_info": "📍 Here is our location:",
    "room_photo_caption": "✨ {room_type}\n💰 ${price}/night\n👥 Capacity: {guests} guest(s)\n\nDo you like it? Book now!",
    "late_checkout_available": "Perfect! Late checkout available until {checkout_time} ✅\n\n💰 Extra fee: ${fee} (50% of daily rate)\n\nDo you confirm the late checkout?",
    "late_checkout_not_available": "Sorry, late checkout is not available. 😔\n\nThe room is reserved for another guest.\n\nStandard checkout time: {standard_time}\n\nNeed luggage storage? We offer it for free.",
    "late_checkout_confirmed": "Done! ✅ Late checkout confirmed until {checkout_time}.\n\n💰 Fee: ${fee}\n\nIt will be added to your account. Enjoy your extended stay!",
    "late_checkout_no_booking": "To request a late checkout, I need your reservation number.\n\nCould you share it?",
    "late_checkout_already_day": "Checkout time has already passed. 😅\n\nFor last-minute extensions, please contact reception directly at [PHONE].",
    "late_checkout_free": "Good news! 🎉\n\nLate checkout until {checkout_time} at no extra cost.\n\nDo you confirm?",
    "booking_confirmed_with_qr": "🎉 RESERVATION CONFIRMED! 🎉\n\n📋 Your reservation details:\n• Reservation: {booking_id}\n• Guest: {guest_name}\n• Check-in: {check_in}\n• Check-out: {check_out}\n• Room: {room_number}\n\n🎫 We sent you your confirmation QR code.\nPlease keep it for faster check-in!",
    "booking_confirmed_no_qr": "🎉 RESERVATION CONFIRMED! 🎉\n\n📋 Your reservation details:\n• Reservation: {booking_id}\n• Check-in: {check_in}\n• Check-out: {check_out}\n\n✅ Your reservation is confirmed.\nYou'll receive more details by email.",
    "review_platform_links": "Perfect {guest_name}! 🌟\n\nHere are the links where you can leave your review:\n\n{platform_links}\n\nIt only takes a few minutes and helps us a lot. Thank you so much! 🙏\n\nIf you need help with any link, just let us know.",
    "review_negative_feedback": "Hello {guest_name},\n\nWe're sorry your experience at {hotel_name} wasn't fully satisfactory.\n\nYour feedback is very valuable. Could you tell us more details about what we could have done better?\n\nWe take all comments seriously and constantly work to improve.\n\nIf there's anything specific we can resolve, we'll be happy to help.\n\nKind regards,\nManagement {hotel_name}",
    # Fallback when NLP fails badly
    "fallback_human_needed": "I'm having trouble understanding your request right now. I'll escalate your conversation to a human agent to assist you.",
    # Pricing information
    "pricing_info": "Our rates vary by season and room type. Are you interested in standard or premium options? I can also check availability for your dates.",
}

# Mapa de idiomas soportados
_TEXT_TEMPLATES_BY_LANG: Dict[str, Dict[str, str]] = {
    "es": TEXT_TEMPLATES_ES,
    "en": TEXT_TEMPLATES_EN,
}

# Plantillas para botones interactivos (i18n)
INTERACTIVE_BUTTON_TEMPLATES_ES = {
    "availability_confirmation": {
        "header_text": "Disponibilidad encontrada",
        "body_text": "Para {checkin}-{checkout}, {room_type} para {guests}: ${price}/noche. Total ${total}.",
        "footer_text": "Hotel Ejemplo - Reserva con nosotros",
        "action_buttons": [
            {"id": "confirm_reservation", "title": "✅ Reservar ahora"},
            {"id": "more_options", "title": "🔍 Ver más opciones"},
        ],
    },
    "arrival_options": {
        "header_text": "¡Tu reserva está confirmada!",
        "body_text": "Para coordinar tu llegada, ¿necesitas alguno de estos servicios?",
        "footer_text": "Hotel Ejemplo - A tu servicio",
        "action_buttons": [
            {"id": "transfer_request", "title": "🚗 Transfer desde aeropuerto"},
            {"id": "late_checkin", "title": "🌙 Check-in tardío"},
        ],
    },
    "info_menu": {
        "header_text": "Información del hotel",
        "body_text": "¿Sobre qué te gustaría saber más?",
        "footer_text": "Elige una opción para continuar",
        "action_buttons": [
            {"id": "hotel_amenities", "title": "🏨 Amenidades"},
            {"id": "guest_services", "title": "🛎️ Servicios"},
            {"id": "check_in_info", "title": "🕒 Check-in"},
            {"id": "check_out_info", "title": "🕛 Check-out"},
            {"id": "cancellation_policy", "title": "❗ Cancelación"},
        ],
    },
}

INTERACTIVE_BUTTON_TEMPLATES_EN = {
    "availability_confirmation": {
        "header_text": "Availability found",
        "body_text": "For {checkin}-{checkout}, {room_type} for {guests}: ${price}/night. Total ${total}.",
        "footer_text": "Sample Hotel - Book with us",
        "action_buttons": [
            {"id": "confirm_reservation", "title": "✅ Book now"},
            {"id": "more_options", "title": "🔍 See more options"},
        ],
    },
    "arrival_options": {
        "header_text": "Your reservation is confirmed!",
        "body_text": "To coordinate your arrival, do you need any of these services?",
        "footer_text": "Sample Hotel - At your service",
        "action_buttons": [
            {"id": "transfer_request", "title": "🚗 Airport transfer"},
            {"id": "late_checkin", "title": "🌙 Late check-in"},
        ],
    },
    "info_menu": {
        "header_text": "Hotel information",
        "body_text": "What would you like to know more about?",
        "footer_text": "Choose an option to continue",
        "action_buttons": [
            {"id": "hotel_amenities", "title": "🏨 Amenities"},
            {"id": "guest_services", "title": "🛎️ Services"},
            {"id": "check_in_info", "title": "🕒 Check-in"},
            {"id": "check_out_info", "title": "🕛 Check-out"},
            {"id": "cancellation_policy", "title": "❗ Cancellation"},
        ],
    },
}

# Plantillas para listas interactivas (i18n)
INTERACTIVE_LIST_TEMPLATES_ES = {
    "room_options": {
        "header_text": "Habitaciones disponibles",
        "body_text": "Estas son las opciones disponibles para tu estadía del {checkin} al {checkout}:",
        "footer_text": "Hotel Ejemplo - Selecciona tu opción preferida",
        "list_button_text": "Ver habitaciones",
        "list_sections": [
            {
                "title": "Habitaciones estándar",
                "rows": [
                    {"id": "std_single", "title": "Individual", "description": "${price_single}/noche - 1 persona"},
                    {"id": "std_double", "title": "Doble", "description": "${price_double}/noche - 2 personas"},
                ],
            },
            {
                "title": "Habitaciones premium",
                "rows": [
                    {"id": "prem_single", "title": "Premium individual", "description": "${price_prem_single}/noche - 1 persona"},
                    {"id": "prem_double", "title": "Premium doble", "description": "${price_prem_double}/noche - 2 personas"},
                ],
            },
        ],
    }
}

INTERACTIVE_LIST_TEMPLATES_EN = {
    "room_options": {
        "header_text": "Available rooms",
        "body_text": "These are the available options for your stay from {checkin} to {checkout}:",
        "footer_text": "Sample Hotel - Choose your preferred option",
        "list_button_text": "See rooms",
        "list_sections": [
            {
                "title": "Standard rooms",
                "rows": [
                    {"id": "std_single", "title": "Single", "description": "${price_single}/night - 1 guest"},
                    {"id": "std_double", "title": "Double", "description": "${price_double}/night - 2 guests"},
                ],
            },
            {
                "title": "Premium rooms",
                "rows": [
                    {"id": "prem_single", "title": "Premium single", "description": "${price_prem_single}/night - 1 guest"},
                    {"id": "prem_double", "title": "Premium double", "description": "${price_prem_double}/night - 2 guests"},
                ],
            },
        ],
    }
}

# Plantillas para ubicaciones
LOCATION_TEMPLATES = {
    "hotel_location": {
        "latitude": -34.6037,  # Ejemplo para Buenos Aires
        "longitude": -58.3816,
        "name": "Hotel Ejemplo",
        "address": "Av. 9 de Julio 1000, Buenos Aires, Argentina",
    }
}

# Plantillas para reacciones
REACTION_TEMPLATES = {"payment_received": "👍", "reservation_confirmed": "✅", "message_understood": "👌"}


class TemplateService:
    def __init__(self, default_language: str = "es"):
        self._language = default_language if default_language in _TEXT_TEMPLATES_BY_LANG else "es"

    def set_language(self, language: str) -> None:
        """Define el idioma por defecto para las respuestas."""
        self._language = language if language in _TEXT_TEMPLATES_BY_LANG else "es"

    def get_response(self, template_name: str, **kwargs) -> str:
        """Obtiene respuestas de texto simple con i18n y fallback a 'es'."""
        lang = self._language
        # 1) Intentar idioma actual
        template = _TEXT_TEMPLATES_BY_LANG.get(lang, {}).get(template_name)
        # 2) Fallback a español
        if template is None:
            template = _TEXT_TEMPLATES_BY_LANG.get("es", {}).get(template_name, "")
        return template.format(**kwargs)

    def get_interactive_buttons(self, template_name: str, **kwargs) -> Dict[str, Any]:
        """Obtiene una plantilla para mensaje interactivo con botones (i18n con fallback)."""
        lang = self._language
        lang_map = {"es": INTERACTIVE_BUTTON_TEMPLATES_ES, "en": INTERACTIVE_BUTTON_TEMPLATES_EN}
        template = lang_map.get(lang, {}).get(template_name) or INTERACTIVE_BUTTON_TEMPLATES_ES.get(template_name)
        if not template:
            return {}

        result = {k: (v.copy() if isinstance(v, list) else v) for k, v in template.items()}

        # Formatear textos con los parámetros
        body = result.get("body_text")
        if isinstance(body, str):
            result["body_text"] = body.format(**kwargs)
        header = result.get("header_text")
        if isinstance(header, str):
            result["header_text"] = header.format(**kwargs)
        footer = result.get("footer_text")
        if isinstance(footer, str):
            result["footer_text"] = footer.format(**kwargs)

        return result

    def get_interactive_list(self, template_name: str, **kwargs) -> Dict[str, Any]:
        """Obtiene una plantilla para mensaje interactivo con lista (i18n con fallback)."""
        lang = self._language
        lang_map = {"es": INTERACTIVE_LIST_TEMPLATES_ES, "en": INTERACTIVE_LIST_TEMPLATES_EN}
        template = lang_map.get(lang, {}).get(template_name) or INTERACTIVE_LIST_TEMPLATES_ES.get(template_name)
        if not template:
            return {}

        # Copia superficial con manejo de listas/estructuras
        result = {k: (v.copy() if isinstance(v, list) else v) for k, v in template.items()}

        # Formatear textos con los parámetros
        body = result.get("body_text")
        if isinstance(body, str):
            result["body_text"] = body.format(**kwargs)
        header = result.get("header_text")
        if isinstance(header, str):
            result["header_text"] = header.format(**kwargs)
        footer = result.get("footer_text")
        if isinstance(footer, str):
            result["footer_text"] = footer.format(**kwargs)

        return result

    def get_location(self, template_name: str, **kwargs) -> Dict[str, Any]:
        """Obtiene una plantilla de ubicación."""
        template = LOCATION_TEMPLATES.get(template_name, {})
        if not template:
            return {}

        result = template.copy()

        # Permitir sobrescribir valores predeterminados
        for key, value in kwargs.items():
            if key in result:
                result[key] = value

        return result

    def get_reaction(self, template_name: str) -> str:
        """Obtiene un emoji para reacción."""
        return REACTION_TEMPLATES.get(template_name, "👍")

    def get_audio_with_location(self, location_template: str, text: str, audio_data: bytes, **kwargs) -> Dict[str, Any]:
        """
        Obtiene una plantilla combinada de audio y ubicación.

        Args:
            location_template: Nombre de la plantilla de ubicación
            text: Texto descriptivo (se enviará junto con el audio)
            audio_data: Datos binarios del audio
            **kwargs: Parámetros adicionales para la plantilla de ubicación

        Returns:
            Dict con la estructura para respuesta combinada audio+ubicación
        """
        # Obtener datos de ubicación de la plantilla
        location_data = self.get_location(location_template, **kwargs)

        # Construir respuesta combinada
        return {"text": text, "audio_data": audio_data, "location": location_data}


# Singleton y factory para compatibilidad con dependencias existentes
_TEMPLATE_SERVICE_SINGLETON: TemplateService | None = None

def get_template_service() -> TemplateService:
    global _TEMPLATE_SERVICE_SINGLETON
    if _TEMPLATE_SERVICE_SINGLETON is None:
        _TEMPLATE_SERVICE_SINGLETON = TemplateService()
    return _TEMPLATE_SERVICE_SINGLETON
