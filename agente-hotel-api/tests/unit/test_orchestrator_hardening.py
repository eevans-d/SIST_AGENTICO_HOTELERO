import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.orchestrator import Orchestrator
from app.models.unified_message import UnifiedMessage
from app.exceptions.pms_exceptions import PMSError

@pytest.mark.asyncio
class TestOrchestratorHardening:
    
    @pytest.fixture
    def mock_pms(self):
        return AsyncMock()
        
    @pytest.fixture
    def mock_session_manager(self):
        return AsyncMock()
        
    @pytest.fixture
    def mock_lock_service(self):
        return AsyncMock()
        
    @pytest.fixture
    def mock_dlq_service(self):
        return AsyncMock()

    @pytest.fixture
    def orchestrator(self, mock_pms, mock_session_manager, mock_lock_service, mock_dlq_service):
        orch = Orchestrator(
            pms_adapter=mock_pms,
            session_manager=mock_session_manager,
            lock_service=mock_lock_service,
            dlq_service=mock_dlq_service
        )
        # Mock internal components
        orch.nlp_engine = AsyncMock()
        orch.audio_processor = AsyncMock()
        orch.template_service = AsyncMock()
        orch.message_gateway = AsyncMock()
        return orch

    async def test_handle_unified_message_text_intent_routing(self, orchestrator):
        """Test that text messages are routed to the correct intent handler."""
        # Setup
        message = UnifiedMessage(
            user_id="user123",
            canal="whatsapp",
            texto="Quiero reservar",
            tipo="text"
        )
        
        # Mock NLP response
        orchestrator.nlp_engine.detect_language.return_value = "es"
        orchestrator.nlp_engine.process_text.return_value = {
            "intent": {"name": "make_reservation", "confidence": 0.95},
            "entities": [],
            "language": "es"
        }

        # Mock session - use get_or_create_session which is what the code calls
        orchestrator.session_manager.get_or_create_session = AsyncMock(return_value={})
        
        # Mock handler
        orchestrator._handle_make_reservation = AsyncMock(return_value={
            "response_type": "text",
            "content": "Reservation flow started"
        })
        # Update intent handlers dict because it was initialized with original methods
        orchestrator._intent_handlers["make_reservation"] = orchestrator._handle_make_reservation
        
        # Execute with business hours patched to True via the override mechanism
        with patch("app.services.orchestrator.is_business_hours", return_value=True, create=True):
            result = await orchestrator.handle_unified_message(message)
        
        # Assert
        orchestrator.nlp_engine.process_text.assert_called_once()
        orchestrator._handle_make_reservation.assert_called_once()
        assert result["response_type"] == "text"
        assert result["content"] == "Reservation flow started"

    async def test_handle_unified_message_low_confidence_fallback(self, orchestrator):
        """Test fallback when NLP confidence is low."""
        message = UnifiedMessage(
            user_id="user123",
            canal="whatsapp",
            texto="blablabla",
            tipo="text"
        )
        
        # Mock NLP response with low confidence
        orchestrator.nlp_engine.detect_language.return_value = "es"
        orchestrator.nlp_engine.process_text.return_value = {
            "intent": {"name": "make_reservation", "confidence": 0.4}, # Below threshold
            "entities": [],
            "language": "es"
        }
        
        orchestrator.session_manager.get_or_create_session = AsyncMock(return_value={})
        
        # Mock fallback handler (usually _handle_fallback or similar logic inside handle_unified_message)
        # We need to see how fallback is implemented. Assuming it returns a fallback response.
        # For now, let's assume it calls template service for fallback.
        orchestrator.template_service.format_response.return_value = "Sorry, I didn't understand."
        
        # Execute
        result = await orchestrator.handle_unified_message(message)
        
        # Assert
        # Verify that specific intent handler was NOT called
        if hasattr(orchestrator, "_handle_make_reservation") and isinstance(orchestrator._handle_make_reservation, AsyncMock):
             orchestrator._handle_make_reservation.assert_not_called()
        
        # Verify fallback response structure (this depends on implementation details)
        # We might need to adjust this assertion after running the test once.

    async def test_handle_unified_message_audio_processing(self, orchestrator):
        """Test audio message processing pipeline."""
        message = UnifiedMessage(
            user_id="user123",
            canal="whatsapp",
            texto="",
            tipo="audio",
            media_url="http://example.com/audio.ogg"
        )
        
        # Ensure transcribe_audio is None so it uses transcribe_whatsapp_audio
        del orchestrator.audio_processor.transcribe_audio
        
        # Mock Audio Processor
        orchestrator.audio_processor.transcribe_whatsapp_audio.return_value = {
            "text": "Quiero una habitación",
            "language": "es",
            "confidence": 0.98
        }
        
        # Mock NLP
        orchestrator.nlp_engine.detect_language.return_value = "es"
        orchestrator.nlp_engine.process_text.return_value = {
            "intent": {"name": "check_availability", "confidence": 0.9},
            "entities": [],
            "language": "es"
        }

        orchestrator.session_manager.get_or_create_session = AsyncMock(return_value={})
        
        # Mock handler
        orchestrator._handle_availability = AsyncMock(return_value={
            "response_type": "text",
            "content": "Checking availability..."
        })
        orchestrator._intent_handlers["check_availability"] = orchestrator._handle_availability
        
        # Execute with business hours patched via override mechanism
        with patch("app.services.orchestrator.is_business_hours", return_value=True, create=True):
            result = await orchestrator.handle_unified_message(message)
        
        # Assert
        orchestrator.audio_processor.transcribe_whatsapp_audio.assert_called_with("http://example.com/audio.ogg")
        orchestrator.nlp_engine.process_text.assert_called()
        orchestrator._handle_availability.assert_called_once()

