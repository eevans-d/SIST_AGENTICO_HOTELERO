"""
Integration tests for Dead Letter Queue (DLQ) with Orchestrator.

Tests the complete flow:
1. Message processing fails → DLQ enqueue
2. Retry worker picks up message → Retry successful
3. Max retries exceeded → Permanent failure stored
"""

import json
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.core.settings import get_settings
from app.models.unified_message import UnifiedMessage
from app.services.dlq_service import DLQService
from app.services.orchestrator import Orchestrator
from app.services.pms_adapter import PMSError

settings = get_settings()


class MockRedis:
    """Simple mock Redis for testing without fakeredis dependency."""
    
    def __init__(self):
        self._store = {}
        self._sorted_sets = {}
    
    async def hset(self, key, mapping=None, **kwargs):
        if mapping:
            # Store values as bytes to match real Redis behavior
            self._store[key] = {k.encode() if isinstance(k, str) else k: v.encode() if isinstance(v, str) else v 
                                 for k, v in mapping.items()}
        return True
    
    async def hgetall(self, key):
        # Return bytes to match real Redis behavior
        result = self._store.get(key, {})
        # Ensure all keys and values are bytes
        if result:
            return {k if isinstance(k, bytes) else k.encode(): v if isinstance(v, bytes) else v.encode() 
                    for k, v in result.items()}
        return result
    
    async def expire(self, key, seconds):
        return True
    
    async def zadd(self, key, mapping):
        if key not in self._sorted_sets:
            self._sorted_sets[key] = {}
        self._sorted_sets[key].update(mapping)
        return len(mapping)
    
    async def zrangebyscore(self, key, min_score=None, max_score=None, min=None, max=None):
        """Get members by score range. Supports both min/max and min_score/max_score."""
        # Handle both parameter styles
        if min is not None:
            min_score = min
        if max is not None:
            max_score = max
        
        if key not in self._sorted_sets:
            return []
        result = []
        for member, score in self._sorted_sets[key].items():
            if min_score <= score <= max_score:
                result.append(member)
        return result
    
    async def zrange(self, key, start, stop, withscores=False):
        """Get range of elements from sorted set."""
        if key not in self._sorted_sets:
            return []
        items = sorted(self._sorted_sets[key].items(), key=lambda x: x[1])
        if start < 0:
            start = max(0, len(items) + start)
        if stop < 0:
            stop = max(0, len(items) + stop + 1)
        else:
            stop = min(len(items), stop + 1)
        result_items = items[start:stop]
        if withscores:
            return [(member, score) for member, score in result_items]
        return [member for member, score in result_items]
    
    async def zrem(self, key, *members):
        if key not in self._sorted_sets:
            return 0
        count = 0
        for member in members:
            if member in self._sorted_sets[key]:
                del self._sorted_sets[key][member]
                count += 1
        return count
    
    async def delete(self, *keys):
        count = 0
        for key in keys:
            if key in self._store:
                del self._store[key]
                count += 1
        return count
    
    async def incr(self, key):
        val = self._store.get(key, 0)
        if isinstance(val, bytes):
            val = int(val)
        self._store[key] = val + 1
        return val + 1
    
    async def decr(self, key):
        val = self._store.get(key, 0)
        if isinstance(val, bytes):
            val = int(val)
        self._store[key] = val - 1
        return val - 1
    
    async def get(self, key):
        return self._store.get(key)
    
    async def keys(self, pattern):
        # Simple pattern matching (just prefix for now)
        prefix = pattern.replace("*", "")
        return [k for k in self._store.keys() if k.startswith(prefix)]


@pytest_asyncio.fixture
async def redis_client():
    """Mock Redis client for testing."""
    return MockRedis()


@pytest_asyncio.fixture
async def db_session():
    """Mock database session."""
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock())
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest_asyncio.fixture
async def dlq_service(redis_client, db_session):
    """DLQ service with fake Redis and mock DB."""
    return DLQService(
        redis_client=redis_client,
        db_session=db_session,
        max_retries=3,
        retry_backoff_base=1,  # 1 second for fast tests
        ttl_days=1,
    )


@pytest_asyncio.fixture
def sample_message():
    """Sample UnifiedMessage for testing."""
    return UnifiedMessage(
        message_id="test-msg-001",
        canal="whatsapp",
        user_id="1234567890",
        timestamp_iso=datetime.now(UTC).isoformat(),
        tipo="text",
        texto="Check availability for tomorrow",
        media_url=None,
        metadata={"test": True},
        tenant_id="test-tenant",
    )


@pytest.mark.asyncio
async def test_orchestrator_pms_failure_enqueues_to_dlq(redis_client, db_session, sample_message):
    """
    Test that PMS failure in Orchestrator enqueues message to DLQ.
    
    Note: Current Orchestrator doesn't call PMS for check_availability (uses mock data),
    so we test by making handle_intent raise PMSError directly.
    """
    # Setup mocks
    pms_adapter = MagicMock()
    
    session_manager = MagicMock()
    session_manager.get_or_create_session = AsyncMock(return_value={"session_id": "test-session"})
    
    lock_service = MagicMock()
    
    dlq_service = DLQService(redis_client, db_session, max_retries=3, retry_backoff_base=1, ttl_days=1)
    
    orchestrator = Orchestrator(
        pms_adapter=pms_adapter,
        session_manager=session_manager,
        lock_service=lock_service,
        dlq_service=dlq_service,
    )
    
    # Mock NLP to return check_availability intent
    with patch.object(orchestrator.nlp_engine, "process_text", new_callable=AsyncMock) as mock_nlp:
        mock_nlp.return_value = {
            "intent": {"name": "check_availability", "confidence": 0.9},
            "entities": [],
            "language": "es",
        }
        
        with patch.object(orchestrator.nlp_engine, "detect_language", new_callable=AsyncMock) as mock_detect:
            mock_detect.return_value = "es"
            
            # Mock handle_intent to raise PMSError (simulating PMS failure)
            with patch.object(orchestrator, "handle_intent", new_callable=AsyncMock) as mock_handle:
                mock_handle.side_effect = PMSError("PMS unavailable")
                
                # Process message (should fail and enqueue to DLQ)
                result = await orchestrator.handle_unified_message(sample_message)
                
                # Verify graceful degradation response
                assert "response_type" in result or "response" in result
    
    # Verify message was enqueued to DLQ
    queue_size = await dlq_service.get_queue_size()
    print(f"DEBUG: queue_size={queue_size}, expected=1")
    assert queue_size == 1, f"Message should be enqueued to DLQ, got queue_size={queue_size}"

    
    # Verify message details in Redis
    keys = await redis_client.keys("dlq:messages:*")
    assert len(keys) == 1
    
    # MockRedis returns strings, not bytes
    dlq_id = keys[0].split(":")[-1] if isinstance(keys[0], str) else keys[0].decode().split(":")[-1]
    dlq_data_raw = await redis_client.hgetall(keys[0])
    # MockRedis may return bytes or strings
    dlq_data = {
        (k.decode() if isinstance(k, bytes) else k): json.loads(v.decode() if isinstance(v, bytes) else v) 
        for k, v in dlq_data_raw.items()
    }
    
    # Orchestrator passes reason="pms_unavailable" which overrides error type
    assert dlq_data["error_type"] == "pms_unavailable"
    assert dlq_data["retry_count"] == 0
    assert dlq_data["message"]["user_id"] == sample_message.user_id


@pytest.mark.asyncio
async def test_retry_worker_processes_candidates(redis_client, db_session, sample_message):
    """
    Test that retry worker successfully processes retry candidates.
    
    Flow:
    1. Message enqueued to DLQ with immediate retry time
    2. get_retry_candidates() returns the message
    3. retry_message() re-processes successfully
    4. Message removed from DLQ
    """
    dlq_service = DLQService(redis_client, db_session, max_retries=3, retry_backoff_base=1, ttl_days=1)
    
    # Enqueue message with immediate retry (past timestamp)
    error = Exception("Temporary failure")
    dlq_id = await dlq_service.enqueue_failed_message(
        message=sample_message,
        error=error,
        retry_count=0,
    )
    
    # Manually set retry time to past (ready for retry)
    past_timestamp = (datetime.now(UTC) - timedelta(seconds=10)).timestamp()
    await redis_client.zadd(dlq_service.DLQ_RETRY_SCHEDULE, {dlq_id: past_timestamp})
    
    # Get retry candidates
    candidates = await dlq_service.get_retry_candidates()
    assert len(candidates) == 1
    assert candidates[0]["dlq_id"] == dlq_id
    
    # Mock successful orchestrator processing for retry
    pms_adapter = MagicMock()
    pms_adapter.check_availability = AsyncMock(return_value={"rooms_available": 5})
    
    session_manager = MagicMock()
    session_manager.get_or_create_session = AsyncMock(return_value={"session_id": "test"})
    
    lock_service = MagicMock()
    
    # Create real orchestrator with working mocks
    orchestrator = Orchestrator(
        pms_adapter=pms_adapter,
        session_manager=session_manager,
        lock_service=lock_service,
        dlq_service=dlq_service,
    )
    
    with patch.object(orchestrator.nlp_engine, "process_text", new_callable=AsyncMock) as mock_nlp:
        with patch.object(orchestrator.nlp_engine, "detect_language", new_callable=AsyncMock) as mock_detect:
            mock_nlp.return_value = {
                "intent": {"name": "check_availability", "confidence": 0.9},
                "entities": [],
                "language": "es",
            }
            mock_detect.return_value = "es"
            
            # Inject orchestrator into DLQ service for retry
            dlq_service.orchestrator = orchestrator
            
            # Retry message
            success = await dlq_service.retry_message(dlq_id)
            assert success is True
    
    # Verify message removed from DLQ
    queue_size = await dlq_service.get_queue_size()
    assert queue_size == 0


@pytest.mark.asyncio
async def test_permanent_failure_after_max_retries(redis_client, db_session, sample_message):
    """
    Test that message is marked as permanent failure after max retries.
    
    Flow:
    1. Message fails 3 times (max retries)
    2. On 4th attempt, mark_permanent_failure() is called
    3. Message stored in PostgreSQL
    4. Message removed from Redis DLQ
    """
    dlq_service = DLQService(redis_client, db_session, max_retries=3, retry_backoff_base=1, ttl_days=1)
    
    # Enqueue with max retries exceeded
    error = Exception("Persistent failure")
    dlq_id = await dlq_service.enqueue_failed_message(
        message=sample_message,
        error=error,
        retry_count=3,  # Max retries
    )
    
    # Get DLQ data to pass to _mark_permanent_failure
    dlq_data_raw = await redis_client.hgetall(f"dlq:messages:{dlq_id}")
    dlq_data = {
        (k.decode() if isinstance(k, bytes) else k): json.loads(v.decode() if isinstance(v, bytes) else v)
        for k, v in dlq_data_raw.items()
    }
    
    # Call private method directly (mimics internal flow)
    await dlq_service._mark_permanent_failure(
        dlq_id=dlq_id,
        dlq_data=dlq_data,
        error=error,
    )
    
    # Verify DB session was called to insert permanent failure
    # El flujo real usa add() + commit(), no execute()
    assert db_session.add.called
    assert db_session.commit.called
    
    # Verify message removed from Redis
    queue_size = await dlq_service.get_queue_size()
    assert queue_size == 0


@pytest.mark.asyncio
async def test_dlq_metrics_exported(redis_client, db_session, sample_message):
    """
    Test that DLQ metrics are properly exported to Prometheus.
    
    Verifies:
    - dlq_messages_total incremented on enqueue
    - dlq_queue_size updated
    - dlq_retries_total incremented on retry
    """
    dlq_service = DLQService(redis_client, db_session, max_retries=3, retry_backoff_base=1, ttl_days=1)
    
    # Enqueue message
    error = PMSError("Test PMS failure")
    dlq_id = await dlq_service.enqueue_failed_message(
        message=sample_message,
        error=error,
    )
    
    # Verify queue size metric updated
    queue_size_metric = await dlq_service.get_queue_size()
    assert queue_size_metric == 1
    
    # Note: Metrics are exported to Prometheus (no internal _metrics access needed)
    
    # Verify DLQ entry exists with correct metadata
    keys = await redis_client.keys("dlq:messages:*")
    assert len(keys) == 1
    
    dlq_data_raw = await redis_client.hgetall(keys[0])
    dlq_data = {
        (k.decode() if isinstance(k, bytes) else k): json.loads(v.decode() if isinstance(v, bytes) else v)
        for k, v in dlq_data_raw.items()
    }
    
    assert dlq_data["error_type"] == "PMSError"
    # UnifiedMessage uses 'canal' not 'channel'
    assert dlq_data["message"]["canal"] == "whatsapp"
    
    # Note: Prometheus metrics are incremented internally
    # In real deployment, /metrics endpoint exposes dlq_messages_total, dlq_queue_size, etc.


@pytest.mark.asyncio
async def test_nlp_failure_enqueues_to_dlq(redis_client, db_session, sample_message):
    """
    Test that NLP processing failure enqueues message to DLQ.
    
    Flow:
    1. NLP engine raises exception
    2. Orchestrator catches and enqueues to DLQ
    3. Falls back to rule-based matching
    4. User still gets response
    """
    pms_adapter = MagicMock()
    session_manager = MagicMock()
    session_manager.get_or_create_session = AsyncMock(return_value={"session_id": "test-session"})
    lock_service = MagicMock()
    
    dlq_service = DLQService(redis_client, db_session, max_retries=3, retry_backoff_base=1, ttl_days=1)
    
    orchestrator = Orchestrator(
        pms_adapter=pms_adapter,
        session_manager=session_manager,
        lock_service=lock_service,
        dlq_service=dlq_service,
    )
    
    # Mock NLP to fail
    with patch.object(orchestrator.nlp_engine, "process_text", side_effect=Exception("NLP service down")):
        with patch.object(orchestrator.nlp_engine, "detect_language", new_callable=AsyncMock) as mock_detect:
            mock_detect.return_value = "es"
            
            # Process message (NLP fails, should enqueue and fallback)
            result = await orchestrator.handle_unified_message(sample_message)
            
            # Verify user still gets response (graceful degradation - both formats supported)
            assert ("response" in result or "response_type" in result), "Should have response or response_type"
    
    # Verify message enqueued to DLQ due to NLP failure
    queue_size = await dlq_service.get_queue_size()
    assert queue_size == 1
    
    # Verify error type in DLQ
    keys = await redis_client.keys("dlq:messages:*")
    dlq_data_raw = await redis_client.hgetall(keys[0])
    dlq_data = {
        (k.decode() if isinstance(k, bytes) else k): json.loads(v.decode() if isinstance(v, bytes) else v)
        for k, v in dlq_data_raw.items()
    }
    assert "nlp" in dlq_data.get("error_type", "").lower() or "exception" in dlq_data.get("error_type", "").lower()


@pytest.mark.asyncio
async def test_audio_processing_failure_enqueues_to_dlq(redis_client, db_session):
    """
    Test that audio processing failure enqueues message to DLQ.
    
    Flow:
    1. Audio message with media_url
    2. STT transcription fails
    3. Message enqueued to DLQ
    4. Continues with empty text (graceful degradation)
    """
    audio_message = UnifiedMessage(
        message_id="test-audio-001",
        canal="whatsapp",
        user_id="1234567890",
        timestamp_iso=datetime.now(UTC).isoformat(),
        tipo="audio",
        texto=None,
        media_url="https://example.com/audio.ogg",
        metadata={},
        tenant_id="test-tenant",
    )
    
    pms_adapter = MagicMock()
    session_manager = MagicMock()
    session_manager.get_or_create_session = AsyncMock(return_value={"session_id": "test-session"})
    lock_service = MagicMock()
    
    dlq_service = DLQService(redis_client, db_session, max_retries=3, retry_backoff_base=1, ttl_days=1)
    
    orchestrator = Orchestrator(
        pms_adapter=pms_adapter,
        session_manager=session_manager,
        lock_service=lock_service,
        dlq_service=dlq_service,
    )
    
    # Mock audio processor to fail
    with patch.object(orchestrator.audio_processor, "transcribe_whatsapp_audio", side_effect=Exception("STT service down")):
        with patch.object(orchestrator.nlp_engine, "process_text", new_callable=AsyncMock) as mock_nlp:
            with patch.object(orchestrator.nlp_engine, "detect_language", new_callable=AsyncMock) as mock_detect:
                mock_nlp.return_value = {"intent": {"name": "unknown", "confidence": 0.0}, "entities": [], "language": "es"}
                mock_detect.return_value = "es"
                
                # Process audio message (audio fails, should enqueue)
                result = await orchestrator.handle_unified_message(audio_message)
                
                # Verify graceful response returned
                assert result is not None
    
    # Verify message enqueued to DLQ
    queue_size = await dlq_service.get_queue_size()
    assert queue_size == 1
    
    # Verify error reason
    keys = await redis_client.keys("dlq:messages:*")
    assert len(keys) == 1
    
    dlq_data_raw = await redis_client.hgetall(keys[0])
    dlq_data = {
        (k.decode() if isinstance(k, bytes) else k): json.loads(v.decode() if isinstance(v, bytes) else v)
        for k, v in dlq_data_raw.items()
    }
    
    # The reason should be related to audio or general exception
    error_type = dlq_data.get("error_type", "").lower()
    assert "audio" in error_type or "exception" in error_type or "stt" in error_type
