# [PROMPT 2.4] app/services/message_gateway.py

from ..models.unified_message import UnifiedMessage


class MessageGateway:
    def normalize_whatsapp_message(self, webhook_payload: dict) -> UnifiedMessage:
        # Lógica para convertir el payload de un webhook de WhatsApp
        # en un objeto UnifiedMessage
        pass

    def normalize_gmail_message(self, email_object) -> UnifiedMessage:
        # Lógica para convertir un objeto de email
        # en un objeto UnifiedMessage
        pass
