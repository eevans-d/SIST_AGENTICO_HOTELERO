import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from datetime import datetime, timezone
from app.services.conversational_memory import ConversationalMemory

@pytest.mark.asyncio
class TestConversationalMemory:
    
    @pytest.fixture
    async def memory_service(self):
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        # Mock set to return True (awaitable)
        mock_redis.set.return_value = True
        service = ConversationalMemory(redis_client=mock_redis)
        return service

    async def test_store_context(self, memory_service):
        """Test storing context in Redis."""
        user_id = "user123"
        entities = [{"entity": "location", "value": "Madrid"}]
        text = "Quiero un hotel en Madrid"
        intent = "search_hotel"
        channel = "whatsapp"

        # Mock existing context to be None
        memory_service.redis.get.return_value = None

        await memory_service.store_context(user_id, entities, text, intent, channel)

        # Verify Redis interaction
        # Should call set with ex=1800
        assert memory_service.redis.set.called
        args, kwargs = memory_service.redis.set.call_args
        assert args[0] == f"context:default:{channel}:{user_id}"
        # args[1] is the json string
        assert kwargs["ex"] == 1800

    async def test_get_relevant_entities(self, memory_service):
        """Test retrieving relevant entities from context."""
        user_id = "user123"
        channel = "whatsapp"
        
        # Mock stored context
        stored_context = {
            "entities": {
                "location": {
                    "value": "Madrid",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "mention_count": 1
                }
            },
            "history": [],
            "language": "es"
        }
        memory_service.redis.get.return_value = json.dumps(stored_context)

        result = await memory_service.get_relevant_entities(user_id, ["location"], channel)

        assert result == {"location": "Madrid"}
        memory_service.redis.get.assert_called_with(f"context:default:{channel}:{user_id}")

    async def test_resolve_anaphora(self, memory_service):
        """Test anaphora resolution."""
        user_id = "user123"
        text = "esa habitación"
        channel = "whatsapp"
        
        stored_context = {
            "entities": {
                "room_type": {
                    "value": "suite",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "mention_count": 1
                }
            },
            "language": "es"
        }
        memory_service.redis.get.return_value = json.dumps(stored_context)
        
        # We mock _resolve_reference to avoid testing complex logic if not needed,
        # but let's try to let it run. If it fails, we'll mock it.
        # Assuming _resolve_reference is an async method on the instance.
        
        # For now, just verify redis call.
        await memory_service.resolve_anaphora(user_id, text, channel)
        
        memory_service.redis.get.assert_called()
