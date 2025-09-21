# [PROMPT 2.7] app/services/template_service.py

TEMPLATES = {
    "availability_found": "Para {checkin}-{checkout}, {room_type} para {guests}: ${price}/noche. Total ${total}. ¿Querés reservar? 🏨",
    "reservation_instructions": "Perfecto! Reservé temporalmente la habitación.\n\nPara confirmar, enviá seña del 30%: ${deposit}\n\nDatos bancarios:\n🏦 {bank_info}\n\nEnviame el comprobante por acá 📄",
    "no_availability": "Lo siento, no hay disponibilidad para esas fechas. ¿Te sirven estas alternativas?\n\n{alternatives}",
}


class TemplateService:
    def get_response(self, template_name: str, **kwargs) -> str:
        return TEMPLATES.get(template_name, "").format(**kwargs)
