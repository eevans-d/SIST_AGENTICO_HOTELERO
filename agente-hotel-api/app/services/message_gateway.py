# [PROMPT 2.4] app/services/message_gateway.py

from datetime import datetime, timezone
from ..models.unified_message import UnifiedMessage


class MessageGateway:
    def normalize_whatsapp_message(self, webhook_payload: dict) -> UnifiedMessage:
        """Convierte un payload de WhatsApp en UnifiedMessage (texto y audio básicos).

        Estructura esperada (simplificada):
        {
          "entry": [
            { "changes": [ { "value": { "messages": [ { ... } ], "contacts": [ {"wa_id": "..."} ] } } ] }
          ]
        }
        """
        entry = (webhook_payload or {}).get("entry", [])
        if not entry:
            raise ValueError("Payload sin 'entry'")

        changes = entry[0].get("changes", [])
        if not changes:
            raise ValueError("Payload sin 'changes'")

        value = changes[0].get("value", {})
        messages = value.get("messages", []) or []
        contacts = value.get("contacts", []) or []

        if not messages:
            raise ValueError("Payload sin 'messages'")

        msg = messages[0]
        msg_type = msg.get("type", "text")
        msg_id = msg.get("id", "")
        user_id = msg.get("from") or (contacts[0].get("wa_id") if contacts else "")

        # WhatsApp envía timestamp en segundos (string)
        ts = msg.get("timestamp") or value.get("timestamp")
        try:
            ts_iso = (
                datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
                if ts is not None
                else datetime.now(timezone.utc).isoformat()
            )
        except Exception:
            ts_iso = datetime.now(timezone.utc).isoformat()

        text = None
        media_url = None
        if msg_type == "text":
            text = (msg.get("text") or {}).get("body")
        elif msg_type == "audio":
            # En producción habría que resolver el media_url con el API de Meta
            # Aquí sólo marcamos el tipo y dejamos media_url en None.
            media_url = None
        else:
            text = (msg.get("text") or {}).get("body")

        return UnifiedMessage(
            message_id=msg_id or user_id or "",
            canal="whatsapp",
            user_id=user_id or "",
            timestamp_iso=ts_iso,
            tipo="audio" if msg_type == "audio" else "text",
            texto=text,
            media_url=media_url,
            metadata={},
        )

    def normalize_gmail_message(self, email_object) -> UnifiedMessage:
        # Lógica para convertir un objeto de email
        # en un objeto UnifiedMessage
        raise NotImplementedError("normalize_gmail_message no implementado")
