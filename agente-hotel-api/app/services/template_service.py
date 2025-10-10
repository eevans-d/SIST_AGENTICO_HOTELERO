# [PROMPT 2.7] app/services/template_service.py

from typing import Dict, Any

# Plantillas de texto simple
TEXT_TEMPLATES = {
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
}

# Plantillas para botones interactivos
INTERACTIVE_BUTTON_TEMPLATES = {
    "availability_confirmation": {
        "header_text": "Disponibilidad encontrada",
        "body_text": "Para {checkin}-{checkout}, {room_type} para {guests}: ${price}/noche. Total ${total}.",
        "footer_text": "Hotel Ejemplo - Reserva con nosotros",
        "action_buttons": [
            {"id": "confirm_reservation", "title": "✅ Reservar ahora"},
            {"id": "more_options", "title": "🔍 Ver más opciones"}
        ]
    },
    "arrival_options": {
        "header_text": "¡Tu reserva está confirmada!",
        "body_text": "Para coordinar tu llegada, ¿necesitas alguno de estos servicios?",
        "footer_text": "Hotel Ejemplo - A tu servicio",
        "action_buttons": [
            {"id": "transfer_request", "title": "🚗 Transfer desde aeropuerto"},
            {"id": "late_checkin", "title": "🌙 Check-in tardío"}
        ]
    }
}

# Plantillas para listas interactivas
INTERACTIVE_LIST_TEMPLATES = {
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
                    {"id": "std_double", "title": "Doble", "description": "${price_double}/noche - 2 personas"}
                ]
            },
            {
                "title": "Habitaciones premium",
                "rows": [
                    {"id": "prem_single", "title": "Premium individual", "description": "${price_prem_single}/noche - 1 persona"},
                    {"id": "prem_double", "title": "Premium doble", "description": "${price_prem_double}/noche - 2 personas"}
                ]
            }
        ]
    }
}

# Plantillas para ubicaciones
LOCATION_TEMPLATES = {
    "hotel_location": {
        "latitude": -34.6037,  # Ejemplo para Buenos Aires
        "longitude": -58.3816,
        "name": "Hotel Ejemplo",
        "address": "Av. 9 de Julio 1000, Buenos Aires, Argentina"
    }
}

# Plantillas para reacciones
REACTION_TEMPLATES = {
    "payment_received": "👍",
    "reservation_confirmed": "✅",
    "message_understood": "👌"
}


class TemplateService:
    def get_response(self, template_name: str, **kwargs) -> str:
        """Método original para obtener respuestas de texto simple."""
        return TEXT_TEMPLATES.get(template_name, "").format(**kwargs)
    
    def get_interactive_buttons(self, template_name: str, **kwargs) -> Dict[str, Any]:
        """Obtiene una plantilla para mensaje interactivo con botones."""
        template = INTERACTIVE_BUTTON_TEMPLATES.get(template_name, {})
        if not template:
            return {}
        
        result = template.copy()
        
        # Formatear textos con los parámetros
        if "body_text" in result:
            result["body_text"] = result["body_text"].format(**kwargs)
        if "header_text" in result:
            result["header_text"] = result["header_text"].format(**kwargs)
        if "footer_text" in result:
            result["footer_text"] = result["footer_text"].format(**kwargs)
            
        return result
    
    def get_interactive_list(self, template_name: str, **kwargs) -> Dict[str, Any]:
        """Obtiene una plantilla para mensaje interactivo con lista."""
        template = INTERACTIVE_LIST_TEMPLATES.get(template_name, {})
        if not template:
            return {}
        
        result = template.copy()
        
        # Formatear textos con los parámetros
        if "body_text" in result:
            result["body_text"] = result["body_text"].format(**kwargs)
        if "header_text" in result:
            result["header_text"] = result["header_text"].format(**kwargs)
        if "footer_text" in result:
            result["footer_text"] = result["footer_text"].format(**kwargs)
            
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
        return {
            "text": text,
            "audio_data": audio_data,
            "location": location_data
        }
