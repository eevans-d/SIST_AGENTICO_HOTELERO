# [PROMPT 2.4] app/models/unified_message.py

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UnifiedMessage:
    message_id: str
    canal: str  # "whatsapp" | "gmail"
    user_id: str  # teléfono o email
    timestamp_iso: str
    tipo: str  # "text" | "audio" | "image"
    texto: Optional[str]
    media_url: Optional[str] = None
    metadata: dict = field(default_factory=dict)  # confidence_stt, duration_sec
