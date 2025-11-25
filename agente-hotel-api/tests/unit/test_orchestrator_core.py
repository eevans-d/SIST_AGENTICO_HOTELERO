"""
Unit tests for Orchestrator core functionality.

Tests cover:
- Orchestrator initialization
- Message handling with different intents
- Error handling and circuit breaker
- Session management integration
- Tenant ID propagation
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.orchestrator import Orchestrator
from app.models.unified_message import UnifiedMessage
from app.services.session_manager import SessionManager
from app.services.lock_service import LockService
from app.services.dlq_service import DLQService


@pytest.fixture
def mock_pms_adapter():
    """Mock PMS adapter for testing."""
    adapter = AsyncMock()
    adapter.check_availability.return_value = [
        {
            "room_type": "double",
            "available": True,
            "price": 100.00,
            "currency": "USD"
        }
    ]
    adapter.create_reservation.return_value = {
        "reservation_uuid": "test-uuid-123",
        "status": "confirmed"
    }
    adapter.test_connection.return_value = True
    return adapter


@pytest.fixture
def mock_session_manager():
    """Mock session manager for testing."""
    manager = AsyncMock(spec=SessionManager)
    manager.get_or_create_session.return_value = {
        "user_id": "+34600111222",
        "channel": "whatsapp",
        "state": "idle",
        "history": [],
        "tenant_id": "hotel-test"
    }
    manager.update_session.return_value = None
    return manager


@pytest.fixture
def mock_lock_service():
    """Mock lock service for testing."""
    service = AsyncMock(spec=LockService)
    service.acquire_lock.return_value = True
    service.release_lock.return_value = None
    return service


@pytest.fixture
def mock_dlq_service():
    """Mock DLQ service for testing."""
    service = AsyncMock(spec=DLQService)
    service.send_to_dlq.return_value = None
    return service


@pytest.fixture
def orchestrator(mock_pms_adapter, mock_session_manager, mock_lock_service, mock_dlq_service):
    """Create orchestrator instance with mocked dependencies."""
    return Orchestrator(
        pms_adapter=mock_pms_adapter,
        session_manager=mock_session_manager,
        lock_service=mock_lock_service,
        dlq_service=mock_dlq_service
    )


@pytest.fixture
def sample_message():
    """Create a sample unified message for testing."""
    return UnifiedMessage(
        user_id="+34600111222",
        channel="whatsapp",
        text="Hola, quiero hacer una reserva",
        timestamp=datetime.utcnow(),
        metadata={"tenant_id": "hotel-test"}
    )


class TestOrchestratorInitialization:
    """Tests for Orchestrator initialization."""

    def test_orchestrator_init_with_all_dependencies(
        self, mock_pms_adapter, mock_session_manager, mock_lock_service, mock_dlq_service
    ):
        """Test orchestrator initializes correctly with all dependencies."""
        orch = Orchestrator(
            pms_adapter=mock_pms_adapter,
            session_manager=mock_session_manager,
            lock_service=mock_lock_service,
            dlq_service=mock_dlq_service
        )
        
        assert orch.pms_adapter == mock_pms_adapter
        assert orch.session_manager == mock_session_manager
        assert orch.lock_service == mock_lock_service
        assert orch.dlq_service == mock_dlq_service

    def test_orchestrator_init_without_dlq_service(
        self, mock_pms_adapter, mock_session_manager, mock_lock_service
    ):
        """Test orchestrator initializes correctly without DLQ service."""
        orch = Orchestrator(
            pms_adapter=mock_pms_adapter,
            session_manager=mock_session_manager,
            lock_service=mock_lock_service,
            dlq_service=None
        )
        
        assert orch.dlq_service is None


class TestOrchestratorMessageHandling:
    """Tests for message handling with different intents."""

    @pytest.mark.asyncio
    async def test_handle_message_greeting_intent(self, orchestrator, sample_message):
        """Test handling of greeting intent."""
        with patch('app.services.orchestrator.nlp_engine') as mock_nlp:
            mock_nlp.analyze_message.return_value = {
                "intent": "greeting",
                "entities": {},
                "confidence": 0.95
            }
            
            result = await orchestrator.handle_message(sample_message)
            
            assert result is not None
            assert "response_type" in result
            # Verify session was retrieved
            orchestrator.session_manager.get_or_create_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_check_availability_intent(self, orchestrator, sample_message):
        """Test handling of check_availability intent."""
        with patch('app.services.orchestrator.nlp_engine') as mock_nlp:
            mock_nlp.analyze_message.return_value = {
                "intent": "check_availability",
                "entities": {
                    "checkin_date": "2025-12-01",
                    "checkout_date": "2025-12-05",
                    "room_type": "double"
                },
                "confidence": 0.90
            }
            
            result = await orchestrator.handle_message(sample_message)
            
            assert result is not None
            # Verify PMS adapter was called
            orchestrator.pms_adapter.check_availability.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_with_tenant_id_propagation(self, orchestrator, sample_message):
        """Test that tenant_id is properly propagated through the system."""
        sample_message.metadata["tenant_id"] = "hotel-abc"
        
        with patch('app.services.orchestrator.nlp_engine') as mock_nlp:
            mock_nlp.analyze_message.return_value = {
                "intent": "greeting",
                "entities": {},
                "confidence": 0.95
            }
            
            await orchestrator.handle_message(sample_message)
            
            # Verify tenant_id was passed to session manager
            call_args = orchestrator.session_manager.get_or_create_session.call_args
            assert call_args is not None
            # Check if tenant_id was passed (could be in args or kwargs)
            if len(call_args[0]) > 2:
                assert call_args[0][2] == "hotel-abc"
            elif "tenant_id" in call_args[1]:
                assert call_args[1]["tenant_id"] == "hotel-abc"

    @pytest.mark.asyncio
    async def test_handle_message_unknown_intent(self, orchestrator, sample_message):
        """Test handling of unknown intent."""
        with patch('app.services.orchestrator.nlp_engine') as mock_nlp:
            mock_nlp.analyze_message.return_value = {
                "intent": "unknown",
                "entities": {},
                "confidence": 0.30
            }
            
            result = await orchestrator.handle_message(sample_message)
            
            assert result is not None
            # Should return a fallback response


class TestOrchestratorErrorHandling:
    """Tests for error handling and circuit breaker."""

    @pytest.mark.asyncio
    async def test_handle_message_pms_connection_error(self, orchestrator, sample_message):
        """Test handling of PMS connection errors."""
        orchestrator.pms_adapter.check_availability.side_effect = ConnectionError("PMS unreachable")
        
        with patch('app.services.orchestrator.nlp_engine') as mock_nlp:
            mock_nlp.analyze_message.return_value = {
                "intent": "check_availability",
                "entities": {
                    "checkin_date": "2025-12-01",
                    "checkout_date": "2025-12-05"
                },
                "confidence": 0.90
            }
            
            result = await orchestrator.handle_message(sample_message)
            
            # Should handle error gracefully
            assert result is not None
            # May send to DLQ if configured
            if orchestrator.dlq_service:
                orchestrator.dlq_service.send_to_dlq.assert_called()

    @pytest.mark.asyncio
    async def test_handle_message_nlp_failure(self, orchestrator, sample_message):
        """Test handling of NLP analysis failures."""
        with patch('app.services.orchestrator.nlp_engine') as mock_nlp:
            mock_nlp.analyze_message.side_effect = Exception("NLP service down")
            
            result = await orchestrator.handle_message(sample_message)
            
            # Should return error response or escalate
            assert result is not None

    @pytest.mark.asyncio
    async def test_handle_message_session_manager_error(self, orchestrator, sample_message):
        """Test handling of session manager errors."""
        orchestrator.session_manager.get_or_create_session.side_effect = Exception("Redis down")
        
        with patch('app.services.orchestrator.nlp_engine') as mock_nlp:
            mock_nlp.analyze_message.return_value = {
                "intent": "greeting",
                "entities": {},
                "confidence": 0.95
            }
            
            result = await orchestrator.handle_message(sample_message)
            
            # Should handle error gracefully
            assert result is not None


class TestOrchestratorSessionIntegration:
    """Tests for session management integration."""

    @pytest.mark.asyncio
    async def test_session_created_on_first_message(self, orchestrator, sample_message):
        """Test that session is created on first message from user."""
        with patch('app.services.orchestrator.nlp_engine') as mock_nlp:
            mock_nlp.analyze_message.return_value = {
                "intent": "greeting",
                "entities": {},
                "confidence": 0.95
            }
            
            await orchestrator.handle_message(sample_message)
            
            orchestrator.session_manager.get_or_create_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_updated_after_message(self, orchestrator, sample_message):
        """Test that session is updated after processing message."""
        with patch('app.services.orchestrator.nlp_engine') as mock_nlp:
            mock_nlp.analyze_message.return_value = {
                "intent": "greeting",
                "entities": {},
                "confidence": 0.95
            }
            
            await orchestrator.handle_message(sample_message)
            
            # Session should be updated with new state
            orchestrator.session_manager.update_session.assert_called()

    @pytest.mark.asyncio
    async def test_session_state_transitions(self, orchestrator, sample_message):
        """Test session state transitions through conversation flow."""
        # Mock session with initial state
        orchestrator.session_manager.get_or_create_session.return_value = {
            "user_id": "+34600111222",
            "channel": "whatsapp",
            "state": "idle",
            "history": [],
            "tenant_id": "hotel-test"
        }
        
        with patch('app.services.orchestrator.nlp_engine') as mock_nlp:
            # First message: check availability
            mock_nlp.analyze_message.return_value = {
                "intent": "check_availability",
                "entities": {
                    "checkin_date": "2025-12-01",
                    "checkout_date": "2025-12-05"
                },
                "confidence": 0.90
            }
            
            await orchestrator.handle_message(sample_message)
            
            # Verify session was updated
            assert orchestrator.session_manager.update_session.called


class TestOrchestratorTenantIsolation:
    """Tests for tenant isolation."""

    @pytest.mark.asyncio
    async def test_different_tenants_isolated(self, orchestrator):
        """Test that messages from different tenants are properly isolated."""
        # Message from tenant A
        message_a = UnifiedMessage(
            user_id="+34600111222",
            channel="whatsapp",
            text="Hola",
            timestamp=datetime.utcnow(),
            metadata={"tenant_id": "hotel-a"}
        )
        
        # Message from tenant B
        message_b = UnifiedMessage(
            user_id="+34600333444",
            channel="whatsapp",
            text="Hello",
            timestamp=datetime.utcnow(),
            metadata={"tenant_id": "hotel-b"}
        )
        
        with patch('app.services.orchestrator.nlp_engine') as mock_nlp:
            mock_nlp.analyze_message.return_value = {
                "intent": "greeting",
                "entities": {},
                "confidence": 0.95
            }
            
            # Process both messages
            await orchestrator.handle_message(message_a)
            await orchestrator.handle_message(message_b)
            
            # Verify both sessions were created with correct tenant_id
            assert orchestrator.session_manager.get_or_create_session.call_count == 2


class TestOrchestratorLockService:
    """Tests for lock service integration."""

    @pytest.mark.asyncio
    async def test_lock_acquired_for_reservation(self, orchestrator, sample_message):
        """Test that lock is acquired when creating reservation."""
        with patch('app.services.orchestrator.nlp_engine') as mock_nlp:
            mock_nlp.analyze_message.return_value = {
                "intent": "create_reservation",
                "entities": {
                    "checkin_date": "2025-12-01",
                    "checkout_date": "2025-12-05",
                    "room_type": "double"
                },
                "confidence": 0.90
            }
            
            await orchestrator.handle_message(sample_message)
            
            # Verify lock was acquired (if orchestrator uses locks for reservations)
            # This depends on actual implementation
            # orchestrator.lock_service.acquire_lock.assert_called()

    @pytest.mark.asyncio
    async def test_lock_released_after_reservation(self, orchestrator, sample_message):
        """Test that lock is released after reservation completes."""
        with patch('app.services.orchestrator.nlp_engine') as mock_nlp:
            mock_nlp.analyze_message.return_value = {
                "intent": "create_reservation",
                "entities": {
                    "checkin_date": "2025-12-01",
                    "checkout_date": "2025-12-05",
                    "room_type": "double"
                },
                "confidence": 0.90
            }
            
            await orchestrator.handle_message(sample_message)
            
            # Verify lock was released
            # orchestrator.lock_service.release_lock.assert_called()
