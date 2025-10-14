"""
Tests unitarios para el servicio de contexto conversacional.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch

from app.services.conversation_context import ConversationContext, get_conversation_context_service


@pytest.fixture
async def mock_redis():
    """Mock para cliente Redis."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.setex.return_value = True
    mock_redis.delete.return_value = 1
    return mock_redis


@pytest.fixture
async def context_service(mock_redis):
    """Servicio de contexto conversacional con Redis mockeado."""
    service = ConversationContext()
    service.redis = mock_redis
    service.CONTEXT_TTL_SECONDS = 300  # Reducir TTL para tests
    return service


class TestConversationContext:
    """Tests unitarios para ConversationContext."""

    async def test_store_context_new(self, context_service, mock_redis):
        """Test para almacenar contexto nuevo."""
        user_id = "user123"
        channel = "whatsapp"
        intent = "check_availability"
        entities = [{"entity": "check_in_date", "value": "2023-12-25", "confidence": 0.9}]
        text = "Quiero reservar para Navidad"

        # Mock para simular que no hay contexto previo
        mock_redis.get.return_value = None

        # Ejecutar
        context_id = await context_service.store_context(user_id, channel, intent, entities, text)

        # Verificar
        assert context_id == f"{user_id}:{channel}"

        # Verificar llamada a redis.setex con contexto correcto
        assert mock_redis.setex.called

        # Obtener argumentos de la llamada
        args, kwargs = mock_redis.setex.call_args

        # Verificar key de redis
        assert args[0] == f"context:{user_id}:{channel}"

        # Verificar TTL
        assert args[1] == 300

        # Verificar contenido serializado
        context_data = json.loads(args[2])
        assert context_data["last_intent"] == intent
        assert context_data["turns"] == 1
        assert "check_in_date" in context_data["entity_history"]
        assert context_data["entity_history"]["check_in_date"][0]["value"] == "2023-12-25"

    async def test_store_context_with_existing(self, context_service, mock_redis):
        """Test para almacenar contexto con contexto previo."""
        user_id = "user123"
        channel = "whatsapp"
        intent = "make_reservation"
        entities = [{"entity": "num_guests", "value": 3, "confidence": 0.95}]
        text = "Reserva para 3 personas"

        # Mock para simular contexto previo
        existing_context = {
            "last_updated": "2023-01-01T12:00:00",
            "last_intent": "check_availability",
            "last_text": "Hay disponibilidad para el 25?",
            "turns": 1,
            "entity_history": {
                "check_in_date": [
                    {
                        "value": "2023-12-25",
                        "turn": 1,
                        "timestamp": "2023-01-01T12:00:00",
                        "confidence": 0.9,
                        "is_correction": False,
                    }
                ]
            },
            "intent_history": ["check_availability"],
        }
        mock_redis.get.return_value = json.dumps(existing_context)

        # Ejecutar
        await context_service.store_context(user_id, channel, intent, entities, text)

        # Verificar
        assert mock_redis.setex.called

        # Obtener argumentos de la llamada
        args, kwargs = mock_redis.setex.call_args

        # Verificar datos serializados
        context_data = json.loads(args[2])
        assert context_data["turns"] == 2
        assert context_data["last_intent"] == intent
        assert "check_in_date" in context_data["entity_history"]
        assert "num_guests" in context_data["entity_history"]
        assert context_data["entity_history"]["check_in_date"][0]["value"] == "2023-12-25"
        assert context_data["entity_history"]["num_guests"][0]["value"] == 3
        assert context_data["intent_history"] == ["check_availability", "make_reservation"]

    async def test_get_context_empty(self, context_service, mock_redis):
        """Test para obtener contexto cuando no hay ninguno."""
        user_id = "user123"
        channel = "whatsapp"

        mock_redis.get.return_value = None

        # Ejecutar
        context = await context_service.get_context(user_id, channel)

        # Verificar
        assert context["has_context"] is False
        assert context["turns"] == 0
        assert context["current_entities"] == {}

    async def test_get_context_with_data(self, context_service, mock_redis):
        """Test para obtener contexto con datos."""
        user_id = "user123"
        channel = "whatsapp"

        # Mock para simular contexto existente
        existing_context = {
            "last_updated": "2023-01-01T12:00:00",
            "last_intent": "check_availability",
            "last_text": "Hay disponibilidad para el 25?",
            "turns": 2,
            "entity_history": {
                "check_in_date": [
                    {
                        "value": "2023-12-24",
                        "turn": 1,
                        "timestamp": "2023-01-01T12:00:00",
                        "confidence": 0.9,
                        "is_correction": False,
                    },
                    {
                        "value": "2023-12-25",
                        "turn": 2,
                        "timestamp": "2023-01-01T12:10:00",
                        "confidence": 0.95,
                        "is_correction": True,
                    },
                ],
                "num_guests": [
                    {
                        "value": 2,
                        "turn": 2,
                        "timestamp": "2023-01-01T12:10:00",
                        "confidence": 0.98,
                        "is_correction": False,
                    }
                ],
            },
            "intent_history": ["greeting", "check_availability"],
        }
        mock_redis.get.return_value = json.dumps(existing_context)

        # Ejecutar
        context = await context_service.get_context(user_id, channel)

        # Verificar
        assert context["has_context"] is True
        assert context["turns"] == 2
        assert context["last_intent"] == "check_availability"
        assert context["current_entities"]["check_in_date"] == "2023-12-25"  # valor corregido
        assert context["current_entities"]["num_guests"] == 2
        assert context["intent_history"] == ["greeting", "check_availability"]

    async def test_resolve_anaphora(self, context_service, mock_redis):
        """Test para resolución de referencias anafóricas."""
        user_id = "user123"
        channel = "whatsapp"
        text = "quiero reservar esa habitación para la misma fecha"

        # Mock para simular contexto existente
        existing_context = {
            "last_updated": "2023-01-01T12:00:00",
            "last_intent": "check_availability",
            "turns": 2,
            "entity_history": {
                "check_in_date": [
                    {
                        "value": "2023-12-25",
                        "turn": 2,
                        "timestamp": "2023-01-01T12:10:00",
                        "confidence": 0.95,
                        "is_correction": False,
                    }
                ],
                "room_type": [
                    {
                        "value": "suite",
                        "turn": 1,
                        "timestamp": "2023-01-01T12:00:00",
                        "confidence": 0.9,
                        "is_correction": False,
                    }
                ],
            },
        }
        mock_redis.get.return_value = json.dumps(existing_context)

        # Ejecutar
        result = await context_service.resolve_anaphora(text, user_id, channel)

        # Verificar
        assert "check_in_date" in result["resolutions"]
        assert result["resolutions"]["check_in_date"] == "2023-12-25"
        assert "room_type" in result["resolutions"]
        assert result["resolutions"]["room_type"] == "suite"
        assert "esa habitación (suite)" in result["resolved_text"]
        assert "misma fecha (2023-12-25)" in result["resolved_text"]

    async def test_clear_context(self, context_service, mock_redis):
        """Test para eliminar contexto."""
        user_id = "user123"
        channel = "whatsapp"

        # Ejecutar
        result = await context_service.clear_context(user_id, channel)

        # Verificar
        assert result is True
        mock_redis.delete.assert_called_once_with(f"context:{user_id}:{channel}")

    async def test_is_correction_true(self, context_service):
        """Test para detectar correcciones."""
        text = "No, me equivoqué, son 3 personas, no 2"
        entity_type = "num_guests"
        new_value = 3
        previous_entries = [
            {"value": 2, "turn": 1, "timestamp": "2023-01-01T12:00:00", "confidence": 0.9, "is_correction": False}
        ]

        # Ejecutar
        result = context_service._is_correction(text, entity_type, new_value, previous_entries)

        # Verificar
        assert result is True

    async def test_is_correction_false(self, context_service):
        """Test para verificar que no es corrección."""
        text = "Y quiero agregar el desayuno"
        entity_type = "breakfast"
        new_value = True
        previous_entries = []

        # Ejecutar
        result = context_service._is_correction(text, entity_type, new_value, previous_entries)

        # Verificar
        assert result is False

    async def test_tenant_specific_context(self, context_service, mock_redis):
        """Test para contexto específico por tenant."""
        user_id = "user123"
        channel = "whatsapp"
        tenant_id = "hotel456"
        intent = "greeting"
        entities = []
        text = "Hola"

        # Ejecutar
        context_id = await context_service.store_context(user_id, channel, intent, entities, text, tenant_id)

        # Verificar
        assert context_id == f"{tenant_id}:{user_id}:{channel}"

        # Verificar key de Redis
        args, kwargs = mock_redis.setex.call_args
        assert args[0] == f"context:{tenant_id}:{user_id}:{channel}"


@pytest.mark.asyncio
async def test_get_conversation_context_service():
    """Test para el getter global del servicio."""
    with patch("app.services.conversation_context.ConversationContext") as MockConversationContext:
        mock_instance = MockConversationContext.return_value
        mock_instance.redis = None

        # Ejecutar
        service = await get_conversation_context_service()

        # Verificar
        assert service == mock_instance
        assert mock_instance.initialize.called
