# [PROMPT 2.4] app/services/whatsapp_client.py

from typing import Optional

import httpx
from ..core.settings import settings


class WhatsAppMetaClient:
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v18.0"
        self.access_token = settings.whatsapp_access_token.get_secret_value()
        self.phone_number_id = settings.whatsapp_phone_number_id
        
        # Configuración de timeouts explícitos
        timeout_config = httpx.Timeout(
            connect=5.0,  # Timeout para establecer conexión
            read=30.0,    # Timeout para leer respuesta (permite mensajes largos)
            write=10.0,   # Timeout para enviar datos
            pool=30.0     # Timeout para obtener conexión del pool
        )
        
        # Límites de conexión
        limits = httpx.Limits(
            max_keepalive_connections=20,  # Conexiones keepalive máximas
            max_connections=100,            # Conexiones totales máximas
            keepalive_expiry=30.0           # Expiración de keepalive en segundos
        )
        
        self.client = httpx.AsyncClient(timeout=timeout_config, limits=limits)

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
