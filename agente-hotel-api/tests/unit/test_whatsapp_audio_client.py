"""
Tests unitarios para la integración del cliente WhatsApp con mensajes de audio.
Este módulo prueba las funciones de audio de WhatsAppMetaClient.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
import os
from pathlib import Path
import tempfile
import json
import io

from app.services.whatsapp_client import WhatsAppMetaClient
from app.core.settings import settings
from app.exceptions.audio_exceptions import AudioDownloadError


@pytest.fixture
async def whatsapp_client():
    """Mock del cliente de WhatsApp."""
    client = WhatsAppMetaClient()
    
    # Configurar como mock
    client.base_url = "https://mock-api.whatsapp.com/v18.0"
    client.phone_number_id = "123456789"
    client.access_token = "mock_token"
    
    return client


@pytest.fixture
def mock_aiohttp_session():
    """Mock de la sesión aiohttp."""
    session_mock = MagicMock()
    
    # Mock respuesta para download_media
    response_mock = AsyncMock()
    response_mock.status = 200
    response_mock.content = AsyncMock()
    response_mock.content.read.return_value = b"mock_audio_data"
    
    session_mock.__aenter__.return_value = session_mock
    session_mock.get.return_value.__aenter__.return_value = response_mock
    
    # Mock respuesta para send_audio_message
    post_response = AsyncMock()
    post_response.status = 200
    post_response.json.return_value = {
        "messages": [{"id": "wamid.123456789"}]
    }
    
    session_mock.post.return_value.__aenter__.return_value = post_response
    
    return session_mock


@pytest.mark.asyncio
async def test_download_media_success(whatsapp_client, mock_aiohttp_session):
    """Test de descarga exitosa de audio de WhatsApp."""
    
    with patch("app.services.whatsapp_client.aiohttp.ClientSession", 
               return_value=mock_aiohttp_session):
        
        media_id = "123456789"
        file_path = await whatsapp_client.download_media(media_id)
        
        # Verificar que se llamó correctamente
        mock_aiohttp_session.get.assert_called_once()
        call_args = mock_aiohttp_session.get.call_args[0][0]
        
        # Verificar URL de descarga
        assert f"/media/{media_id}" in call_args
        assert "Bearer mock_token" in mock_aiohttp_session.get.call_args[1]["headers"]["Authorization"]
        
        # Verificar el archivo
        assert file_path.exists()
        assert os.path.getsize(file_path) > 0
        
        # Limpieza
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_download_media_error(whatsapp_client, mock_aiohttp_session):
    """Test manejo de errores en descarga de audio."""
    
    # Configurar response con error
    error_response = AsyncMock()
    error_response.status = 404
    error_response.text.return_value = json.dumps({
        "error": {
            "message": "Media not found",
            "code": 404
        }
    })
    mock_aiohttp_session.get.return_value.__aenter__.return_value = error_response
    
    with patch("app.services.whatsapp_client.aiohttp.ClientSession", 
               return_value=mock_aiohttp_session):
        
        # Verificar que se lanza excepción
        with pytest.raises(AudioDownloadError):
            await whatsapp_client.download_media("invalid_media_id")


@pytest.mark.asyncio
async def test_send_audio_message_success(whatsapp_client, mock_aiohttp_session):
    """Test de envío exitoso de mensaje de audio."""
    
    with patch("app.services.whatsapp_client.aiohttp.ClientSession",
               return_value=mock_aiohttp_session):
        
        # Datos de prueba
        recipient = "5491123456789"
        audio_data = b"test_audio_bytes" * 100
        
        # Enviar audio
        result = await whatsapp_client.send_audio_message(recipient, audio_data)
        
        # Verificaciones
        assert "message_id" in result
        assert result["message_id"] == "wamid.123456789"
        assert mock_aiohttp_session.post.call_count == 1
        
        # Verificar URL y payload
        post_args = mock_aiohttp_session.post.call_args
        assert whatsapp_client._api_url in post_args[0][0]
        assert "messages" in post_args[0][0]
        
        # Verificar que se usó multipart
        assert "data" in post_args[1]
        assert "files" in post_args[1]


@pytest.mark.asyncio
async def test_send_audio_message_error(whatsapp_client, mock_aiohttp_session):
    """Test manejo de errores en envío de audio."""
    
    # Configurar response con error
    error_response = AsyncMock()
    error_response.status = 400
    error_response.json.return_value = {
        "error": {
            "message": "Invalid audio format",
            "code": 400
        }
    }
    mock_aiohttp_session.post.return_value.__aenter__.return_value = error_response
    
    with patch("app.services.whatsapp_client.aiohttp.ClientSession",
               return_value=mock_aiohttp_session):
        
        # Verificar que se lanza excepción
        with pytest.raises(Exception):
            await whatsapp_client.send_audio_message("5491123456789", b"invalid_audio")


@pytest.mark.asyncio
async def test_audio_conversion_before_send(whatsapp_client):
    """Test que verifica la conversión de audio antes de enviar."""
    
    # Mock para el método privado de envío
    whatsapp_client._send_audio = AsyncMock(return_value={
        "message_id": "wamid.123456789",
        "status": "sent"
    })
    
    # Mock para función de conversión
    with patch("app.services.whatsapp_client.convert_audio_format") as mock_convert:
        # Simular que devuelve audio convertido
        mock_convert.return_value = (b"converted_audio_data", "audio/ogg")
        
        # Enviar audio en formato no soportado
        audio_data = b"audio_data_wav"
        await whatsapp_client.send_audio_message("5491123456789", audio_data)
        
        # Verificar que se llamó a convert_audio_format
        assert mock_convert.call_count == 1
        
        # Verificar que se usó el audio convertido
        call_args = whatsapp_client._send_audio.call_args
        assert call_args[0][1] == b"converted_audio_data"


@pytest.mark.asyncio
async def test_media_upload_flow(whatsapp_client, mock_aiohttp_session):
    """Test del flujo completo de subida de medios."""
    
    # Mock para respuesta de subida de medios
    upload_response = AsyncMock()
    upload_response.status = 200
    upload_response.json.return_value = {
        "id": "media_id_123456789"
    }
    mock_aiohttp_session.post.return_value.__aenter__.return_value = upload_response
    
    with patch("app.services.whatsapp_client.aiohttp.ClientSession",
               return_value=mock_aiohttp_session):
        
        # Simular flujo de upload + envío
        with patch.object(whatsapp_client, "_send_message") as mock_send:
            mock_send.return_value = {"message_id": "wamid.123456789"}
            
            # Enviar audio
            result = await whatsapp_client.send_audio_message("5491123456789", b"audio_data")
            
            # Verificar resultado
            assert result["message_id"] == "wamid.123456789"
            assert mock_aiohttp_session.post.call_count >= 1