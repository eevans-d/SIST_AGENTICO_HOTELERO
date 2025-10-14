import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.asyncio
async def test_audio_with_location_handler():
    """Prueba que el endpoint de webhooks maneje correctamente las respuestas de tipo audio_with_location."""

    # Crear un mock para el orquestador
    mock_orchestrator = AsyncMock()
    mock_orchestrator.handle_unified_message.return_value = {
        "response_type": "audio_with_location",
        "content": {
            "text": "Nuestro hotel está ubicado en Av. Principal 123, Centro, Ciudad.",
            "audio_data": b"audio_data_bytes",
            "location": {
                "latitude": 19.4326,
                "longitude": -99.1332,
                "name": "Hotel Test",
                "address": "Av. Principal 123",
            },
        },
        "original_message": MagicMock(user_id="1234567890"),
    }

    # Crear un mock para WhatsAppMetaClient
    mock_whatsapp_client = AsyncMock()
    mock_whatsapp_client.send_audio_message = AsyncMock()
    mock_whatsapp_client.send_message = AsyncMock()
    mock_whatsapp_client.send_location_message = AsyncMock()
    mock_whatsapp_client.close = AsyncMock()

    # Parchar las dependencias
    with (
        patch("app.routers.webhooks.Orchestrator", return_value=mock_orchestrator),
        patch("app.routers.webhooks.WhatsAppMetaClient", return_value=mock_whatsapp_client),
        patch("app.routers.webhooks.verify_webhook_signature", return_value=True),
    ):
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
                                        "timestamp": "1234567890",
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
            "/webhooks/whatsapp", json=webhook_payload, headers={"X-Hub-Signature-256": "dummy-signature"}
        )

        # Verificar que la respuesta sea 200 OK
        assert response.status_code == 200

        # Verificar que se llamaron los métodos correctos en WhatsAppMetaClient
        mock_whatsapp_client.send_audio_message.assert_called_once_with(to="1234567890", audio_data=b"audio_data_bytes")

        mock_whatsapp_client.send_message.assert_called_once_with(
            to="1234567890", text="Nuestro hotel está ubicado en Av. Principal 123, Centro, Ciudad."
        )

        mock_whatsapp_client.send_location_message.assert_called_once_with(
            to="1234567890", latitude=19.4326, longitude=-99.1332, name="Hotel Test", address="Av. Principal 123"
        )

        # Verificar que se cerró el cliente
        mock_whatsapp_client.close.assert_called_once()
