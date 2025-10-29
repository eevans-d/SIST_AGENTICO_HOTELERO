# [PROMPT 2.4] app/models/unified_message.py

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UnifiedMessage:
    # Defaults para facilitar construcción en tests y rutas internas
    message_id: str = ""
    canal: str = "whatsapp"  # "whatsapp" | "gmail"
    user_id: str = ""  # teléfono o email
    timestamp_iso: str = ""
    # Compatibilidad con tests que usan timestamp UNIX
    timestamp: Optional[int] = None
    tipo: str = "text"  # "text" | "audio" | "image" | "interactive" | "location" | "reaction"
    texto: Optional[str] = None
    media_url: Optional[str] = None
    metadata: dict = field(default_factory=dict)  # confidence_stt, duration_sec, interactive_data
    # Groundwork multi-tenant (opcional, no obligatorio en fase actual)
    tenant_id: Optional[str] = None
