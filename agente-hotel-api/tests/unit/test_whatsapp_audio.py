import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from pathlib import Path

from app.services.whatsapp_client import WhatsAppMetaClient


@pytest.mark.asyncio
async def test_send_audio_message():
    """Test que el método send_audio_message funciona correctamente."""
    # Crear mocks
    client = WhatsAppMetaClient()
    client.client = AsyncMock()
    
    # Configurar respuestas para ambas llamadas API
    upload_response_mock = AsyncMock()
    upload_response_mock.status_code = 200
    upload_response_mock.json.return_value = {"id": "12345"}
    
    message_response_mock = AsyncMock()
    message_response_mock.status_code = 200
    message_response_mock.json.return_value = {"messages": [{"id": "msg_id_12345"}]}
    
    # Configurar las respuestas de los mocks
    client.client.post.side_effect = [upload_response_mock, message_response_mock]
    
    # Llamar al método
    result = await client.send_audio_message(
        to="5491100000000",
        audio_data=b"audio_test_data",
        filename="test.ogg"
    )
    
    # Verificar que se llamó a la API correctamente
    assert client.client.post.call_count == 2
    
    # Verificar primera llamada (upload)
    upload_call = client.client.post.call_args_list[0]
    assert "/media" in upload_call[0][0]
    assert upload_call[1]["content"] == b"audio_test_data"
    assert upload_call[1]["headers"]["Content-Type"] == "audio/ogg"
    
    # Verificar segunda llamada (message)
    message_call = client.client.post.call_args_list[1]
    assert "/messages" in message_call[0][0]
    assert message_call[1]["json"]["type"] == "audio"
    assert message_call[1]["json"]["audio"]["id"] == "12345"
    
    # Verificar resultado
    assert result["messages"][0]["id"] == "msg_id_12345"


@pytest.mark.asyncio
async def test_process_audio_message():
    """Test que process_audio_message transcribe correctamente."""
    # Crear mocks
    client = WhatsAppMetaClient()
    client.download_media = AsyncMock(return_value=b"audio_test_data")
    client.audio_processor._convert_to_wav = AsyncMock()
    client.audio_processor.stt.transcribe = AsyncMock(return_value={
        "text": "Texto transcrito de prueba",
        "confidence": 0.9,
        "success": True,
        "language": "es"
    })
    
    # Mock para el tempfile
    with patch("tempfile.NamedTemporaryFile") as mock_temp_file:
        # Configurar mock del archivo temporal
        mock_temp = Mock()
        mock_temp.name = "/tmp/test_audio.ogg"
        mock_temp.__enter__.return_value = mock_temp
        mock_temp_file.return_value = mock_temp
        
        # Mock para Path
        with patch("pathlib.Path") as mock_path:
            mock_path_instance = Mock()
            mock_path_instance.exists.return_value = True
            mock_path.return_value = mock_path_instance
            
            # Mock para os.unlink
            with patch("os.unlink") as mock_unlink:
                # Llamar al método
                result = await client.process_audio_message("media_id_12345")
                
                # Verificar resultados
                assert result["text"] == "Texto transcrito de prueba"
                assert result["confidence"] == 0.9
                assert result["success"] is True
                
                # Verificar que se llamaron los métodos correctos
                client.download_media.assert_called_once_with("media_id_12345")
                client.audio_processor._convert_to_wav.assert_called_once()
                client.audio_processor.stt.transcribe.assert_called_once()
                mock_unlink.assert_called()  # Verificar limpieza de archivos


@pytest.mark.asyncio
async def test_process_audio_message_download_error():
    """Test manejo de errores cuando falla la descarga del audio."""
    # Crear mocks
    client = WhatsAppMetaClient()
    client.download_media = AsyncMock(return_value=None)  # Simulamos fallo en descarga
    
    # Llamar al método
    result = await client.process_audio_message("media_id_12345")
    
    # Verificar resultados
    assert result["success"] is False
    assert result["text"] == ""
    assert "error" in result
    assert "No se pudo descargar" in result["error"]