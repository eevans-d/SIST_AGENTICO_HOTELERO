# [PROMPT 2.7] app/services/template_service.py

from typing import Dict, Any, List, Optional, Union

# Plantillas de texto simple
TEXT_TEMPLATES = {
    "availability_found": "Para {checkin}-{checkout}, {room_type} para {guests}: ${price}/noche. Total ${total}. ¿Querés reservar? 🏨",
    "reservation_instructions": "Perfecto! Reservé temporalmente la habitación.\n\nPara confirmar, enviá seña del 30%: ${deposit}\n\nDatos bancarios:\n🏦 {bank_info}\n\nEnviame el comprobante por acá 📄",
    "no_availability": "Lo siento, no hay disponibilidad para esas fechas. ¿Te sirven estas alternativas?\n\n{alternatives}",
    "confirmation_received": "¡Excelente! Hemos recibido tu confirmación. Tu reserva está completa.",
    "help_message": "Puedo ayudarte con lo siguiente:",
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
