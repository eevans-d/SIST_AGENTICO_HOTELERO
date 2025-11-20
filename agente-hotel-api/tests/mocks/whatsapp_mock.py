from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class SentMessage:
    to: str
    type: str
    content: Dict[str, Any]


class WhatsAppMockClient:
    """Cliente WhatsApp simulado para pruebas.

    Registra los mensajes enviados para poder hacer aserciones en tests.
    """

    def __init__(self) -> None:
        self.sent: List[SentMessage] = []

    async def send_text(self, to: str, text: str, **kwargs):
        self.sent.append(SentMessage(to=to, type="text", content={"text": text, **kwargs}))
        return {"success": True, "id": f"msg-{len(self.sent)}"}

    async def send_image(self, to: str, image_url: Optional[str] = None, image_path: Optional[str] = None, caption: str = "", **kwargs):
        payload = {"image_url": image_url, "image_path": image_path, "caption": caption}
        payload.update(kwargs)
        self.sent.append(SentMessage(to=to, type="image", content=payload))
        return {"success": True, "id": f"msg-{len(self.sent)}"}

    async def send_audio(self, to: str, audio_data: bytes, **kwargs):
        self.sent.append(SentMessage(to=to, type="audio", content={"bytes": len(audio_data), **kwargs}))
        return {"success": True, "id": f"msg-{len(self.sent)}"}

    async def send_location(self, to: str, latitude: float, longitude: float, name: str = "", address: str = "", **kwargs):
        self.sent.append(
            SentMessage(
                to=to,
                type="location",
                content={"latitude": latitude, "longitude": longitude, "name": name, "address": address, **kwargs},
            )
        )
        return {"success": True, "id": f"msg-{len(self.sent)}"}
