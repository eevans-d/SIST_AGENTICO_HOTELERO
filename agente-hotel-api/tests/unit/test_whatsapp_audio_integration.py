"""
Unit tests for WhatsApp integration with audio processing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import httpx
from app.services.whatsapp_client import WhatsAppMetaClient
from app.core.settings import settings


@pytest.fixture
def mock_audio_data():
    """Audio data mock para pruebas."""
    return b"mock_audio_data_for_testing"


@pytest.fixture
def mock_whatsapp_client():
    """Fixture para un cliente WhatsApp mockeado."""
    client = AsyncMock(spec=WhatsAppMetaClient)
    client.download_media.return_value = b"mock_audio_data_from_whatsapp"
    client.send_audio_message.return_value = {"success": True, "message_id": "test_wamid"}
    return client


@pytest.mark.asyncio
async def test_whatsapp_download_media():
    """Test de descarga de medios de WhatsApp."""
    
    # Preparar mocks de respuestas HTTP
    mock_url_response = MagicMock()
    mock_url_response.status_code = 200
    mock_url_response.json.return_value = {
        "url": "https://mock-whatsapp-media.com/audio.ogg"
    }
    
    mock_media_response = MagicMock()
    mock_media_response.status_code = 200
    mock_media_response.content = b"mock_audio_data_downloaded"
    
    # Patch para httpx.AsyncClient
    with patch("httpx.AsyncClient.post", return_value=mock_url_response), \
         patch("httpx.AsyncClient.get", return_value=mock_media_response):
        
        # Crear cliente real con configuración de prueba
        client = WhatsAppMetaClient()
        client._auth_token = "test_token"
        client._phone_number_id = "12345678"
        client._api_version = "v18.0"
        
        # Ejecutar la descarga
        result = await client.download_media("test_media_id")
        
        # Verificar resultado
        assert result == b"mock_audio_data_downloaded"
        assert mock_url_response.json.called
        assert mock_media_response.content is not None


@pytest.mark.asyncio
async def test_whatsapp_download_media_error():
    """Test de manejo de errores en descarga de medios."""
    
    # Respuesta de error para la URL
    mock_url_response = MagicMock()
    mock_url_response.status_code = 404
    mock_url_response.json.return_value = {
        "error": {
            "message": "Media not found",
            "code": 190
        }
    }
    
    # Patch para httpx.AsyncClient
    with patch("httpx.AsyncClient.post", return_value=mock_url_response):
        
        # Crear cliente real con configuración de prueba
        client = WhatsAppMetaClient()
        client._auth_token = "test_token"
        client._phone_number_id = "12345678"
        client._api_version = "v18.0"
        
        # Ejecutar la descarga y verificar que maneja el error
        result = await client.download_media("test_media_id")
        
        # Verificar resultado
        assert result is None
        assert mock_url_response.json.called


@pytest.mark.asyncio
async def test_whatsapp_send_audio_message():
    """Test de envío de mensaje de audio por WhatsApp."""
    
    # Mock para respuesta de carga de multimedia
    mock_upload_response = MagicMock()
    mock_upload_response.status_code = 200
    mock_upload_response.json.return_value = {
        "id": "test_media_id"
    }
    
    # Mock para respuesta de envío de mensaje
    mock_message_response = MagicMock()
    mock_message_response.status_code = 200
    mock_message_response.json.return_value = {
        "messages": [{"id": "wamid.test123"}]
    }
    
    # Patch para httpx.AsyncClient
    with patch("httpx.AsyncClient.post", side_effect=[mock_upload_response, mock_message_response]):
        
        # Crear cliente real con configuración de prueba
        client = WhatsAppMetaClient()
        client._auth_token = "test_token"
        client._phone_number_id = "12345678"
        client._api_version = "v18.0"
        
        # Ejecutar el envío de audio
        result = await client.send_audio_message(
            phone="5491155667788",
            audio_data=b"test_audio_bytes",
            text="Este es un mensaje de audio"
        )
        
        # Verificar resultado
        assert result["success"] is True
        assert result["message_id"] == "wamid.test123"
        assert mock_upload_response.json.called
        assert mock_message_response.json.called


@pytest.mark.asyncio
async def test_whatsapp_send_audio_message_upload_error():
    """Test de manejo de error en carga de audio."""
    
    # Mock para respuesta de error en carga de multimedia
    mock_upload_response = MagicMock()
    mock_upload_response.status_code = 400
    mock_upload_response.json.return_value = {
        "error": {
            "message": "Invalid file format",
            "code": 100
        }
    }
    
    # Patch para httpx.AsyncClient
    with patch("httpx.AsyncClient.post", return_value=mock_upload_response):
        
        # Crear cliente real con configuración de prueba
        client = WhatsAppMetaClient()
        client._auth_token = "test_token"
        client._phone_number_id = "12345678"
        client._api_version = "v18.0"
        
        # Ejecutar el envío de audio
        result = await client.send_audio_message(
            phone="5491155667788",
            audio_data=b"test_audio_bytes",
            text="Este es un mensaje de audio"
        )
        
        # Verificar resultado
        assert result["success"] is False
        assert "error" in result