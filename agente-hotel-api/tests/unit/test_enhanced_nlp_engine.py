"""
Tests para EnhancedNLPEngine con características multilingües y contextuales.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.enhanced_nlp_engine import (
    EnhancedNLPEngine,
    get_enhanced_nlp_engine
)


@pytest.fixture
async def mock_redis():
    """Mock para cliente Redis."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.setex.return_value = True
    return mock_redis


@pytest.fixture
async def mock_conversation_context():
    """Mock para servicio de contexto conversacional."""
    mock = AsyncMock()
    mock.resolve_anaphora.return_value = {
        "resolved_text": "quiero reservar habitación doble",
        "resolutions": {}
    }
    mock.store_context.return_value = "user123:whatsapp"
    return mock


@pytest.fixture
async def mock_multilingual_service():
    """Mock para servicio multilingüe."""
    mock = AsyncMock()
    mock.process_with_language_detection.return_value = {
        "language_code": "es",
        "language_confidence": 0.95,
        "original_language": "es",
        "text": "quiero reservar habitación"
    }
    return mock


@pytest.fixture
async def nlp_engine(mock_redis, mock_conversation_context, mock_multilingual_service):
    """Engine NLP con dependencias mockeadas."""
    with patch('app.services.enhanced_nlp_engine.get_redis', return_value=mock_redis), \
         patch('app.services.enhanced_nlp_engine.get_conversation_context_service', 
               return_value=mock_conversation_context), \
         patch('app.services.enhanced_nlp_engine.get_multilingual_nlp_service',
               return_value=mock_multilingual_service):
        
        engine = EnhancedNLPEngine()
        engine._initialize_called = True
        engine.redis = mock_redis
        engine.conversation_context = mock_conversation_context
        engine.multilingual_service = mock_multilingual_service
        
        # Mock de agents para cada idioma
        mock_agent_es = AsyncMock()
        mock_agent_es.parse_message.return_value = {
            "intent": {"name": "make_reservation", "confidence": 0.9},
            "entities": [
                {"entity": "room_type", "value": "doble", "start": 16, "end": 21, 
                 "extractor": "DIETClassifier", "confidence_entity": 0.95}
            ],
            "text": "quiero reservar habitación doble"
        }
        
        mock_agent_en = AsyncMock()
        mock_agent_en.parse_message.return_value = {
            "intent": {"name": "make_reservation", "confidence": 0.85},
            "entities": [
                {"entity": "room_type", "value": "double", "start": 17, "end": 23,
                 "extractor": "DIETClassifier", "confidence_entity": 0.9}
            ],
            "text": "I want to book a double room"
        }
        
        engine.agents = {
            "es": mock_agent_es,
            "en": mock_agent_en
        }
        
        engine.model_versions = {
            "es": "20230101_120000",
            "en": "20230101_120000"
        }
        
        engine.default_language = "es"
        
        return engine


class TestEnhancedNLPEngine:
    """Tests para EnhancedNLPEngine."""
    
    async def test_process_message_spanish(self, nlp_engine, mock_conversation_context):
        """Test para procesar mensaje en español."""
        # Configurar
        text = "quiero reservar habitación"
        user_id = "user123"
        channel = "whatsapp"
        
        # Ejecutar
        result = await nlp_engine.process_message(text, user_id, channel)
        
        # Verificar
        assert result["intent"]["name"] == "make_reservation"
        assert result["intent"]["confidence"] == 0.9
        assert result["language"] == "es"
        assert len(result["entities"]) == 1
        assert result["entities"][0]["entity"] == "room_type"
        assert result["entities"][0]["value"] == "doble"
        
        # Verificar que se guardó el contexto
        mock_conversation_context.store_context.assert_called_once()
    
    async def test_process_message_english(self, nlp_engine, mock_multilingual_service):
        """Test para procesar mensaje en inglés."""
        # Configurar mock para detectar inglés
        mock_multilingual_service.process_with_language_detection.return_value = {
            "language_code": "en",
            "language_confidence": 0.92,
            "original_language": "en",
            "text": "I want to book a room"
        }
        
        text = "I want to book a room"
        
        # Ejecutar
        result = await nlp_engine.process_message(text)
        
        # Verificar
        assert result["intent"]["name"] == "make_reservation"
        assert result["intent"]["confidence"] == 0.85
        assert result["language"] == "en"
    
    async def test_process_message_with_context(self, nlp_engine, mock_conversation_context):
        """Test para procesar mensaje con contexto."""
        # Configurar mock para resolver anáfora
        mock_conversation_context.resolve_anaphora.return_value = {
            "resolved_text": "quiero reservarla para el 25",
            "resolutions": {
                "room_type": "suite"
            }
        }
        
        text = "quiero reservarla para el 25"
        user_id = "user123"
        channel = "whatsapp"
        
        # Ejecutar
        result = await nlp_engine.process_message(text, user_id, channel)
        
        # Verificar
        assert result["context_used"] == True
        assert result["resolutions"]["room_type"] == "suite"
    
    async def test_process_message_cache_hit(self, nlp_engine, mock_redis):
        """Test para caché de mensajes."""
        # Configurar mock para hit de caché
        cached_result = {
            "intent": {"name": "greeting", "confidence": 0.95},
            "entities": [],
            "language": "es",
            "text": "hola",
            "model_version": "20230101_120000"
        }
        mock_redis.get.return_value = json.dumps(cached_result)
        
        text = "hola"
        
        # Ejecutar
        result = await nlp_engine.process_message(text)
        
        # Verificar que se usó la caché
        assert result["intent"]["name"] == "greeting"
        assert result["language"] == "es"
        # Verificar que no se llamó al servicio multilingüe
        assert not nlp_engine.multilingual_service.process_with_language_detection.called
    
    async def test_handle_low_confidence_very_low(self, nlp_engine):
        """Test para manejo de confianza muy baja."""
        intent = {"name": "unknown", "confidence": 0.2}
        
        # Ejecutar
        result = await nlp_engine.handle_low_confidence(intent, "es")
        
        # Verificar
        assert result["requires_human"] == True
        assert "Disculpa, no estoy seguro" in result["response"]
    
    async def test_handle_low_confidence_medium(self, nlp_engine):
        """Test para manejo de confianza media."""
        intent = {"name": "make_reservation", "confidence": 0.5}
        
        # Ejecutar
        result = await nlp_engine.handle_low_confidence(intent, "es")
        
        # Verificar
        assert result["requires_human"] == False
        assert "¿En qué puedo ayudarte?" in result["response"]
        assert "Consultar disponibilidad" in result["response"]
    
    async def test_handle_low_confidence_high(self, nlp_engine):
        """Test para manejo de confianza alta."""
        intent = {"name": "make_reservation", "confidence": 0.8}
        
        # Ejecutar
        result = await nlp_engine.handle_low_confidence(intent, "es")
        
        # Verificar
        assert result is None
    
    async def test_process_message_circuit_breaker(self, nlp_engine):
        """Test para circuit breaker."""
        # Simular que el circuit breaker está abierto
        nlp_engine.circuit_breaker.call = AsyncMock(
            side_effect=CircuitBreakerOpenError("Circuit breaker open")
        )
        
        text = "quiero reservar"
        
        # Ejecutar
        result = await nlp_engine.process_message(text)
        
        # Verificar respuesta de fallback
        assert result["intent"]["name"] == "unknown"
        assert result["fallback"] == True
    
    async def test_get_models_info(self, nlp_engine):
        """Test para obtener info de modelos."""
        # Ejecutar
        result = await nlp_engine.get_models_info()
        
        # Verificar
        assert "models" in result
        assert "es" in result["models"]
        assert "en" in result["models"]
        assert result["models"]["es"]["model_version"] == "20230101_120000"
        assert result["default_language"] == "es"
        assert result["supported_languages"] == ["es", "en"]


@pytest.mark.asyncio
async def test_get_enhanced_nlp_engine():
    """Test para el getter global del servicio."""
    with patch('app.services.enhanced_nlp_engine.EnhancedNLPEngine') as MockEnhancedNLPEngine:
        mock_instance = MockEnhancedNLPEngine.return_value
        mock_instance._initialize_called = False
        
        # Ejecutar
        service = await get_enhanced_nlp_engine()
        
        # Verificar
        assert service == mock_instance
        assert mock_instance.initialize.called