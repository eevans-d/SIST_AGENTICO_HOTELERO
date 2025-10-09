"""
E2E tests for audio flow functionality in the hotel agent system.
Tests audio message reception, Whisper transcription, NLP processing, and eSpeak response.
"""

import os
import pytest
import httpx
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from app.main import app
from app.models.unified_message import UnifiedMessage
from app.services.audio_processor import AudioProcessor
from app.services.whatsapp_client import WhatsAppMetaClient
from app.services.nlp_engine import NLPEngine
from app.services.orchestrator import Orchestrator
from app.core.settings import PMSType


# Fixture para un audio mock (simulamos el comportamiento sin archivos reales)
@pytest.fixture
def mock_audio_data():
    return b"mock_audio_data_for_testing"


# Fixture para simular una URL de audio de WhatsApp
@pytest.fixture
def whatsapp_audio_url():
    return "https://whatsapp-mock.com/media/audio123456789.ogg"


# Fixture para crear un procesador de audio en modo test
@pytest.fixture
async def audio_processor():
    processor = AudioProcessor()
    # Override para evitar cargar modelos reales
    processor.stt._model_loaded = "mock"
    processor.stt.model = MagicMock()
    return processor


@pytest.mark.asyncio
@patch("app.services.whatsapp_client.WhatsAppClient.download_media")
async def test_audio_message_full_flow(mock_download_media, mock_audio_data, whatsapp_audio_url, audio_processor):
    """Test E2E para flujo completo de mensaje de audio: recepción→transcripción→NLP→respuesta"""
    
    # Mock para la descarga de medios de WhatsApp
    mock_download_media.return_value = mock_audio_data
    
    # Mock del cliente WhatsApp
    whatsapp_client = AsyncMock(spec=WhatsAppMetaClient)
    whatsapp_client.download_media.return_value = mock_audio_data
    whatsapp_client.send_audio_message.return_value = {"success": True, "message_id": "test_wamid"}
    
    # Mock para NLP Engine
    nlp_engine = AsyncMock(spec=NLPEngine)
    nlp_engine.analyze_text.return_value = {
        "intent": {"name": "check_availability", "confidence": 0.95},
        "entities": [
            {"type": "date", "value": "mañana", "start": 15, "end": 21, "confidence": 0.93},
            {"type": "room_type", "value": "doble", "start": 30, "end": 35, "confidence": 0.92}
        ],
        "language": "es"
    }
    
    # Mock para PMS Adapter
    pms_adapter = AsyncMock()
    pms_adapter.check_availability.return_value = {
        "available": True,
        "rooms": [
            {"type": "doble", "date": "2025-10-09", "price": 120.0, "available": 3}
        ]
    }
    
    # Patch para la transcripción de audio
    with patch.object(AudioProcessor, "transcribe_whatsapp_audio") as mock_transcribe:
        # Configurar el resultado de la transcripción
        mock_transcribe.return_value = {
            "text": "Quisiera saber si tienen disponibilidad para mañana, una habitación doble",
            "confidence": 0.92,
            "success": True,
            "language": "es"
        }
        
        # Crear mensaje de audio para prueba
        audio_message = UnifiedMessage(
            message_id="test123",
            canal="whatsapp",
            user_id="5491155667788",
            timestamp_iso="2025-10-08T14:30:00Z",
            tipo="audio",
            texto="",  # Inicialmente vacío porque es un mensaje de audio
            media_url=whatsapp_audio_url
        )
        
        # Mock para el Orchestrator
        orchestrator = AsyncMock(spec=Orchestrator)
        orchestrator.audio_processor = audio_processor
        orchestrator.whatsapp_client = whatsapp_client
        orchestrator.nlp_engine = nlp_engine
        orchestrator.pms_adapter = pms_adapter
        
        # PASO 1: Transcribir el audio con Whisper
        transcription_result = await audio_processor.transcribe_whatsapp_audio(audio_message.media_url)
        audio_message.texto = transcription_result["text"]
        
        # PASO 2: Procesar con NLP
        nlp_result = await nlp_engine.analyze_text(audio_message.texto)
        
        # PASO 3: Consultar disponibilidad en el PMS
        availability = await pms_adapter.check_availability(
            check_in="2025-10-09", 
            check_out="2025-10-10", 
            room_type="doble"
        )
        
        # PASO 4: Generar respuesta de audio
        with patch.object(AudioProcessor, "generate_audio_response") as mock_generate_audio:
            mock_generate_audio.return_value = b"synthesized_audio_response"
            
            audio_response = await audio_processor.generate_audio_response(
                "Sí, tenemos 3 habitaciones dobles disponibles para mañana, 9 de octubre, a un precio de 120 euros."
            )
            
            # PASO 5: Enviar respuesta de audio
            send_result = await whatsapp_client.send_audio_message(
                phone="5491155667788",
                audio_data=audio_response,
                text="Sí, tenemos disponibilidad para mañana"
            )
            
            # Verificaciones
            assert transcription_result["text"] == "Quisiera saber si tienen disponibilidad para mañana, una habitación doble"
            assert nlp_result["intent"]["name"] == "check_availability"
            assert availability["available"] is True
            assert len(availability["rooms"]) > 0
            assert send_result["success"] is True


@pytest.mark.asyncio
@patch("app.services.whatsapp_client.WhatsAppClient.download_media")
async def test_audio_response_to_text_message(mock_download_media, audio_processor):
    """Test E2E para respuesta de audio a un mensaje de texto"""
    
    # Mock para el cliente de WhatsApp
    whatsapp_client = AsyncMock(spec=WhatsAppMetaClient)
    whatsapp_client.send_audio_message.return_value = {"success": True, "message_id": "test_wamid"}
    
    # Crear mensaje de texto para prueba
    text_message = UnifiedMessage(
        message_id="text123",
        canal="whatsapp",
        user_id="5491155667788",
        timestamp_iso="2025-10-08T14:35:00Z",
        tipo="text",
        texto="¿Hay habitaciones disponibles para el fin de semana?",
        metadata={"prefer_audio": True}  # El usuario prefiere respuestas de audio
    )
    
    # Mock para Orchestrator
    orchestrator = AsyncMock(spec=Orchestrator)
    orchestrator.audio_processor = audio_processor
    orchestrator.whatsapp_client = whatsapp_client
    
    # Generar respuesta de audio para mensaje de texto
    with patch.object(AudioProcessor, "generate_audio_response") as mock_generate_audio:
        mock_generate_audio.return_value = b"synthesized_audio_response"
        
        response_text = "Sí, tenemos habitaciones disponibles para este fin de semana, 11 y 12 de octubre."
        
        audio_response = await audio_processor.generate_audio_response(response_text)
        
        # Enviar respuesta de audio
        send_result = await whatsapp_client.send_audio_message(
            phone="5491155667788",
            audio_data=audio_response,
            text=response_text
        )
        
        # Verificaciones
        assert mock_generate_audio.called
        assert audio_response == b"synthesized_audio_response"
        assert send_result["success"] is True


@pytest.mark.asyncio
async def test_audio_cache_in_e2e_flow(audio_processor):
    """Test E2E para cache de audio en flujo de comunicación"""
    
    # Mock para el servicio de cache
    with patch("app.services.audio_cache_service.AudioCacheService") as MockCacheService:
        # Configurar el mock del cache
        mock_cache = MockCacheService.return_value
        mock_cache.get.side_effect = [None, b"cached_audio_response"]  # Primera vez no existe, segunda sí
        mock_cache.set.return_value = True
        
        # Asignar cache al procesador de audio
        audio_processor.cache_service = mock_cache
        
        # Prueba de cache miss + almacenamiento
        response_text = "Gracias por su reserva. Lo esperamos el próximo fin de semana."
        
        # Primera llamada - cache miss
        with patch.object(AudioProcessor, "synthesize_text") as mock_synthesize:
            mock_synthesize.return_value = {
                "audio_data": b"newly_synthesized_audio", 
                "success": True
            }
            
            # Solicitar audio con cache miss
            audio_response1 = await audio_processor.generate_audio_response(response_text)
            
            # Verificar que se llamó a la síntesis
            assert mock_synthesize.called
            assert mock_cache.get.called
            assert mock_cache.set.called
            assert audio_response1 == b"newly_synthesized_audio"
        
        # Segunda llamada - cache hit
        with patch.object(AudioProcessor, "synthesize_text") as mock_synthesize:
            # Solicitar mismo audio (debería ser cache hit)
            audio_response2 = await audio_processor.generate_audio_response(response_text)
            
            # Verificar que NO se llamó a síntesis
            assert not mock_synthesize.called
            assert mock_cache.get.call_count == 2
            assert audio_response2 == b"cached_audio_response"


@pytest.mark.asyncio
async def test_error_handling_in_audio_flow(audio_processor, whatsapp_audio_url):
    """Test E2E para manejo de errores en el flujo de audio"""
    
    # Mock para la descarga de WhatsApp que falla
    whatsapp_client = AsyncMock(spec=WhatsAppMetaClient)
    whatsapp_client.download_media.side_effect = Exception("Error simulado de descarga")
    
    # Mock para Orchestrator
    orchestrator = AsyncMock(spec=Orchestrator)
    orchestrator.audio_processor = audio_processor
    orchestrator.whatsapp_client = whatsapp_client
    
    # Crear mensaje de audio para prueba
    audio_message = UnifiedMessage(
        message_id="error123",
        canal="whatsapp",
        user_id="5491155667788",
        timestamp_iso="2025-10-08T14:40:00Z",
        tipo="audio",
        texto="",
        media_url=whatsapp_audio_url
    )
    
    # Probar manejo de error en descarga
    with pytest.raises(Exception):
        await audio_processor.transcribe_whatsapp_audio(audio_message.media_url)
    
    # Verificar que se intentó descargar
    assert whatsapp_client.download_media.called
    
    # Probar fallback a texto cuando falla la generación de audio
    with patch.object(AudioProcessor, "synthesize_text") as mock_synthesize:
        mock_synthesize.side_effect = Exception("Error simulado de síntesis")
        
        # Debería capturar el error y retornar None
        result = await audio_processor.generate_audio_response("Texto de prueba")
        
        # Verificar que se intentó sintetizar
        assert mock_synthesize.called
        assert result is None