import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from fastapi import Request
from fastapi.testclient import TestClient

from app.main import app
from app.services.whatsapp_client import WhatsAppMetaClient


@pytest.mark.asyncio
async def test_audio_with_follow_up_handler():
    """Prueba que el endpoint de webhooks maneje correctamente las respuestas de audio con follow_up."""
    
    # Crear un mock para el orquestador
    mock_orchestrator = AsyncMock()
    mock_orchestrator.handle_unified_message.return_value = {
        "response_type": "audio",
        "content": {
            "text": "Tenemos varias opciones de habitaciones disponibles del 01/01/2023 al 05/01/2023.",
            "audio_data": b"audio_data_bytes",
            "follow_up": {
                "type": "interactive_list",
                "content": {
                    "header_text": "Opciones de Habitaciones",
                    "body_text": "Estas son nuestras opciones disponibles:",
                    "list_sections": [
                        {
                            "rows": [
                                {"id": "room_single", "title": "Individual"}
                            ]
                        }
                    ],
                    "list_button_text": "Ver opciones"
                }
            }
        },
        "original_message": MagicMock(user_id="1234567890")
    }
    
    # Crear un mock para WhatsAppMetaClient
    mock_whatsapp_client = AsyncMock()
    mock_whatsapp_client.send_audio_message = AsyncMock()
    mock_whatsapp_client.send_message = AsyncMock()
    mock_whatsapp_client.send_interactive_message = AsyncMock()
    mock_whatsapp_client.close = AsyncMock()
    
    # Parchar las dependencias
    with patch("app.routers.webhooks.Orchestrator", return_value=mock_orchestrator), \
         patch("app.routers.webhooks.WhatsAppMetaClient", return_value=mock_whatsapp_client), \
         patch("app.routers.webhooks.verify_webhook_signature", return_value=True):
        
        # Crear un cliente de prueba
        client = TestClient(app)
        
        # Simular un webhook de WhatsApp
        webhook_payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "id": "123",
                                        "from": "1234567890",
                                        "type": "audio",
                                        "audio": {"id": "1234", "mime_type": "audio/ogg"},
                                        "timestamp": "1234567890"
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        
        # Enviar la solicitud al endpoint
        response = client.post(
            "/webhooks/whatsapp", 
            json=webhook_payload,
            headers={"X-Hub-Signature-256": "dummy-signature"}
        )
        
        # Verificar que la respuesta sea 200 OK
        assert response.status_code == 200
        
        # Verificar que se llamaron los métodos correctos en WhatsAppMetaClient
        mock_whatsapp_client.send_audio_message.assert_called_once_with(
            to="1234567890",
            audio_data=b"audio_data_bytes"
        )
        
        mock_whatsapp_client.send_message.assert_called_once_with(
            to="1234567890",
            text="Tenemos varias opciones de habitaciones disponibles del 01/01/2023 al 05/01/2023."
        )
        
        # Verificar que se envió el mensaje interactivo de seguimiento
        mock_whatsapp_client.send_interactive_message.assert_called_once()
        # Verificar parámetros
        call_args = mock_whatsapp_client.send_interactive_message.call_args[1]
        assert call_args["to"] == "1234567890"
        assert call_args["header_text"] == "Opciones de Habitaciones"
        assert "Ver opciones" in call_args["list_button_text"]
        
        # Verificar que se cerró el cliente
        mock_whatsapp_client.close.assert_called_once()