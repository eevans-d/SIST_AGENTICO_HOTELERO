# [PROMPT 2.4] app/services/whatsapp_client.py

from typing import Optional

import httpx
from ..core.settings import settings


class WhatsAppMetaClient:
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v18.0"
        self.access_token = settings.whatsapp_access_token.get_secret_value()
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.client = httpx.AsyncClient()

    async def send_message(self, to: str, text: str) -> bool:
        payload = {"messaging_product": "whatsapp", "to": to, "text": {"body": text}}
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = await self.client.post(
            f"{self.base_url}/{self.phone_number_id}/messages", json=payload, headers=headers
        )
        return response.status_code == 200

    async def download_media(self, media_id: str) -> Optional[bytes]:
        # Lógica para obtener la URL del medio y descargarlo
        pass
