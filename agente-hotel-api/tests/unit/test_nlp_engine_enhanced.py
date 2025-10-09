"""
Pruebas unitarias para el motor NLP mejorado.
Cubre los siguientes aspectos:
1. Procesamiento multilingüe
2. Resolución de contexto y anáforas
3. Caché de inferencia
4. Manejo de confianza baja
"""

import pytest
import json
from unittest.mock import AsyncMock

from app.services.conversational_memory import ConversationalMemory
from app.services.multilingual_processor import MultilingualProcessor
from app.services.nlp_engine_enhanced import EnhancedNLPEngine


@pytest.fixture
def mock_redis_client():
    """Mock para cliente Redis."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=True)
    
    return redis_mock


@pytest.fixture
def mock_multilingual_processor():
    """Mock para procesador multilingüe."""
    processor_mock = AsyncMock(spec=MultilingualProcessor)
    
    # Configurar respuestas de detección de idioma
    processor_mock.detect_language = AsyncMock(return_value={
        "language": "es", 
        "confidence": 0.9, 
        "method": "heuristic"
    })
    
    # Configurar respuestas de procesamiento
    processor_mock.process_text = AsyncMock(return_value={
        "intent": {"name": "check_availability", "confidence": 0.85},
        "entities": [
            {
                "entity": "check_in_date",
                "value": "2025-10-15",
                "start": 20,
                "end": 29,
                "confidence": 0.92,
                "extractor": "DIETClassifier"
            }
        ],
        "language": "es"
    })
    
    return processor_mock


@pytest.fixture
def mock_conversational_memory():
    """Mock para memoria conversacional."""
    memory_mock = AsyncMock(spec=ConversationalMemory)
    
    # Configurar respuestas
    memory_mock.get_conversation_language = AsyncMock(return_value="es")
    memory_mock.resolve_anaphora = AsyncMock(
        side_effect=lambda user_id, text, channel, tenant_id: text  # Devolver texto sin cambios por defecto
    )
    memory_mock.is_follow_up_question = AsyncMock(return_value=False)
    memory_mock.get_relevant_entities = AsyncMock(return_value={})
    memory_mock.store_context = AsyncMock(return_value=None)
    
    return memory_mock


@pytest.fixture
def nlp_engine(mock_redis_client, mock_multilingual_processor, mock_conversational_memory):
    """Crea una instancia de EnhancedNLPEngine con mocks."""
    engine = EnhancedNLPEngine(model_path="/fake/path/model.tar.gz", cache_enabled=True)
    
    # Inyectar dependencias mockeadas
    engine.redis = mock_redis_client
    engine._redis_initialized = True
    engine._multilingual_processor = mock_multilingual_processor
    engine._conversational_memory = mock_conversational_memory
    engine.model_version = "test-20251005"
    
    return engine


@pytest.mark.asyncio
async def test_process_message_basic(nlp_engine):
    """Prueba el procesamiento básico de mensajes."""
    # Configurar datos de prueba
    text = "¿Hay habitaciones disponibles?"
    
    # Ejecutar
    result = await nlp_engine.process_message(text)
    
    # Verificar
    assert result["intent"]["name"] == "check_availability"
    assert result["intent"]["confidence"] == 0.85
    assert len(result["entities"]) == 1
    assert result["entities"][0]["entity"] == "check_in_date"
    assert result["text"] == text
    assert result["model_version"] == "test-20251005"
    assert result["language"] == "es"


@pytest.mark.asyncio
async def test_process_message_with_cache(nlp_engine, mock_redis_client):
    """Prueba el procesamiento con caché."""
    # Configurar datos de prueba
    text = "¿Hay habitaciones disponibles?"
    cached_response = {
        "intent": {"name": "check_availability", "confidence": 0.92},
        "entities": [],
        "text": text,
        "model_version": "test-cache",
        "language": "es"
    }
    
    # Configurar mock de Redis para devolver respuesta cacheada
    mock_redis_client.get.return_value = json.dumps(cached_response)
    
    # Ejecutar
    result = await nlp_engine.process_message(text)
    
    # Verificar
    assert result["intent"]["name"] == "check_availability"
    assert result["intent"]["confidence"] == 0.92
    assert result["model_version"] == "test-cache"
    
    # Verificar que se consultó la caché
    mock_redis_client.get.assert_called_once()
    
    # Verificar que no se procesó el mensaje
    nlp_engine._multilingual_processor.process_text.assert_not_called()


@pytest.mark.asyncio
async def test_process_message_with_context(nlp_engine, mock_conversational_memory):
    """Prueba el procesamiento con contexto conversacional."""
    # Configurar datos de prueba
    text = "Y para esas fechas, ¿qué precio tiene?"
    user_id = "user123"
    channel = "whatsapp"
    
    # Configurar mock de memoria conversacional para simular resolución anafórica
    mock_conversational_memory.resolve_anaphora = AsyncMock(
        return_value="Y para el 10 al 15 de octubre, ¿qué precio tiene?"
    )
    mock_conversational_memory.is_follow_up_question = AsyncMock(return_value=True)
    mock_conversational_memory.get_relevant_entities = AsyncMock(return_value={
        "check_in_date": "2025-10-10",
        "check_out_date": "2025-10-15"
    })
    
    # Ejecutar
    result = await nlp_engine.process_message(text, user_id, channel)
    
    # Verificar
    assert "context_used" in result
    assert result["context_used"] is True
    
    # Verificar que se llamó al resolver anafórico
    mock_conversational_memory.resolve_anaphora.assert_called_once_with(
        user_id, text, channel, None
    )
    
    # Verificar que se guardó el contexto
    mock_conversational_memory.store_context.assert_called_once()


@pytest.mark.asyncio
async def test_process_message_with_language_detection(nlp_engine, mock_multilingual_processor):
    """Prueba la detección de idioma en el procesamiento."""
    # Configurar datos de prueba
    text = "Do you have any rooms available?"
    
    # Configurar mock para simular detección de inglés
    mock_multilingual_processor.detect_language = AsyncMock(return_value={
        "language": "en", 
        "confidence": 0.95, 
        "method": "fasttext"
    })
    
    # Configurar mock para resultado en inglés
    mock_multilingual_processor.process_text = AsyncMock(return_value={
        "intent": {"name": "check_availability", "confidence": 0.82},
        "entities": [],
        "language": "en"
    })
    
    # Ejecutar
    result = await nlp_engine.process_message(text)
    
    # Verificar
    assert result["language"] == "en"
    
    # Verificar que se llamó al detector de idioma
    mock_multilingual_processor.detect_language.assert_called_once_with(text)
    
    # Verificar que se procesó con el idioma detectado
    mock_multilingual_processor.process_text.assert_called_once()
    args, kwargs = mock_multilingual_processor.process_text.call_args
    assert kwargs.get("language") == "en" or args[1] == "en"


@pytest.mark.asyncio
async def test_handle_low_confidence(nlp_engine):
    """Prueba el manejo de confianza baja."""
    # Casos de prueba
    test_cases = [
        # Muy baja confianza → derivar a humano
        {
            "intent": {"name": "unknown", "confidence": 0.2},
            "language": "es",
            "expected": {
                "response": "Disculpa, no estoy seguro de entender tu consulta. ¿Podrías reformularla o te conecto con un representante?",
                "requires_human": True
            }
        },
        # Baja confianza → mostrar menú
        {
            "intent": {"name": "check_availability", "confidence": 0.6},
            "language": "es",
            "expected": {
                "response": "¿En qué puedo ayudarte?\n1️⃣ Consultar disponibilidad\n2️⃣ Hacer una reserva\n3️⃣ Modificar/cancelar reserva\n4️⃣ Información del hotel (precios, servicios, ubicación)\n5️⃣ Hablar con recepción",
                "requires_human": False
            }
        },
        # Alta confianza → ninguna acción especial
        {
            "intent": {"name": "check_availability", "confidence": 0.8},
            "language": "es",
            "expected": None
        },
    ]
    
    # Probar cada caso
    for case in test_cases:
        result = await nlp_engine.handle_low_confidence(case["intent"], case["language"])
        assert result == case["expected"]


@pytest.mark.asyncio
async def test_fallback_response(nlp_engine):
    """Prueba las respuestas de fallback basadas en reglas."""
    # Casos de prueba
    test_cases = [
        # Español - check_availability
        {
            "text": "necesito saber si hay habitaciones disponibles",
            "language": "es",
            "expected_intent": "check_availability"
        },
        # Español - make_reservation
        {
            "text": "quiero hacer una reserva para este fin de semana",
            "language": "es",
            "expected_intent": "make_reservation"
        },
        # Inglés - pricing_info
        {
            "text": "how much does it cost per night?",
            "language": "en",
            "expected_intent": "pricing_info"
        },
        # Portugués - ask_location
        {
            "text": "onde está localizado o hotel?",
            "language": "pt",
            "expected_intent": "ask_location"
        },
        # Sin coincidencia
        {
            "text": "xyz123",
            "language": "es",
            "expected_intent": "unknown"
        }
    ]
    
    # Probar cada caso
    for case in test_cases:
        result = nlp_engine._fallback_response(case["text"], case["language"])
        assert result["intent"]["name"] == case["expected_intent"]
        assert result["fallback"] is True
        assert result["language"] == case["language"]


@pytest.mark.asyncio
async def test_circuit_breaker_behavior(nlp_engine, mock_multilingual_processor):
    """Prueba el comportamiento del circuit breaker."""
    # Configurar mock para fallar
    mock_multilingual_processor.process_text = AsyncMock(side_effect=Exception("Test error"))
    
    # Ejecutar varias veces para disparar el circuit breaker
    for _ in range(4):  # Threshold es 3
        result = await nlp_engine.process_message("prueba")
        assert "fallback" in result
    
    # Verificar que el circuit breaker está abierto
    assert nlp_engine.circuit_breaker.state.name == "OPEN"
    
    # Verificar que ahora usa fallback directamente sin llamar al processor
    mock_multilingual_processor.process_text.reset_mock()
    result = await nlp_engine.process_message("otra prueba")
    
    assert "fallback" in result
    mock_multilingual_processor.process_text.assert_not_called()


@pytest.mark.asyncio
async def test_model_info(nlp_engine):
    """Prueba la obtención de información del modelo."""
    info = nlp_engine.get_model_info()
    
    # Verificar información básica
    assert info["model_path"] == "/fake/path/model.tar.gz"
    assert info["model_version"] == "test-20251005"
    assert info["multilingual_support"] is True
    assert "es" in info["languages"]
    assert "en" in info["languages"]
    assert "pt" in info["languages"]
    assert info["contextual_memory"] is True
    
    # Verificar estadísticas
    assert "stats" in info
    assert "processed_messages" in info["stats"]
    assert "cache_hits" in info["stats"]
    assert "languages_detected" in info["stats"]