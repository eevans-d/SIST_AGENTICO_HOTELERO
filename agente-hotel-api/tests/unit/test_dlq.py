"""
Unit tests for Dead Letter Queue (DLQ) service.

Tests DLQ enqueue, retry logic, exponential backoff, and permanent failures.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dlq import DLQEntry
from app.models.unified_message import UnifiedMessage
from app.services.dlq_service import DLQService


@pytest.fixture
async def redis_client():
    """Mock Redis client."""
    mock_redis = AsyncMock(spec=redis.Redis)
    
    # Mock Redis operations
    mock_redis.hset = AsyncMock(return_value=1)
    mock_redis.hgetall = AsyncMock(return_value={})
    mock_redis.expire = AsyncMock(return_value=1)
    mock_redis.zadd = AsyncMock(return_value=1)
    mock_redis.zrem = AsyncMock(return_value=1)
    mock_redis.zrange = AsyncMock(return_value=[])
    mock_redis.zrangebyscore = AsyncMock(return_value=[])
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.decr = AsyncMock(return_value=0)
    mock_redis.get = AsyncMock(return_value=b"0")
    mock_redis.delete = AsyncMock(return_value=1)
    
    return mock_redis


@pytest.fixture
async def db_session():
    """Mock database session."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.execute = AsyncMock()
    return mock_session


@pytest.fixture
def dlq_service(redis_client, db_session):
    """Create DLQ service instance for testing."""
    return DLQService(
        redis_client=redis_client,
        db_session=db_session,
        max_retries=3,
        retry_backoff_base=60,
        ttl_days=7,
    )


@pytest.fixture
def sample_message():
    """Sample UnifiedMessage for testing."""
    return UnifiedMessage(
        message_id="test-msg-123",
        canal="whatsapp",
        user_id="test@example.com",
        texto="Quiero reservar una habitación",
        timestamp_iso=datetime.utcnow().isoformat(),
        tipo="text",
    )


@pytest.mark.asyncio
async def test_enqueue_failed_message(dlq_service, redis_client, sample_message):
    """Test that failed message is enqueued to DLQ correctly."""
    error = Exception("PMS timeout")
    
    dlq_id = await dlq_service.enqueue_failed_message(
        message=sample_message,
        error=error,
        retry_count=0,
    )
    
    # Verify UUID was generated
    assert dlq_id
    assert len(dlq_id) == 36  # UUID4 format
    
    # Verify Redis hash was created
    message_key = f"dlq:messages:{dlq_id}"
    redis_client.hset.assert_called_once()
    call_args = redis_client.hset.call_args
    assert call_args[0][0] == message_key
    
    # Verify TTL was set
    redis_client.expire.assert_called_once_with(message_key, 7 * 24 * 60 * 60)
    
    # Verify added to retry schedule (sorted set)
    redis_client.zadd.assert_called_once()
    
    # Verify stats counter incremented
    redis_client.incr.assert_called_once_with("dlq:stats:total")


@pytest.mark.asyncio
async def test_retry_with_exponential_backoff(dlq_service, redis_client, sample_message):
    """Test that retry uses exponential backoff: 60s → 120s → 240s."""
    error = Exception("Temporary failure")
    
    # First failure (retry_count=0) → backoff 60s
    await dlq_service.enqueue_failed_message(
        message=sample_message, error=error, retry_count=0
    )

    # Extract retry_at from Redis call (sorted set score)
    zadd_call_1 = redis_client.zadd.call_args_list[0]
    retry_timestamp_1 = list(zadd_call_1[0][1].values())[0]
    retry_at_1 = datetime.fromtimestamp(retry_timestamp_1)
    expected_retry_1 = datetime.utcnow() + timedelta(seconds=60)

    # Allow 2 second tolerance for execution time
    assert abs((retry_at_1 - expected_retry_1).total_seconds()) < 2

    # Second failure (retry_count=1) → backoff 120s
    redis_client.reset_mock()
    await dlq_service.enqueue_failed_message(
        message=sample_message, error=error, retry_count=1
    )

    zadd_call_2 = redis_client.zadd.call_args_list[0]
    retry_timestamp_2 = list(zadd_call_2[0][1].values())[0]
    retry_at_2 = datetime.fromtimestamp(retry_timestamp_2)
    expected_retry_2 = datetime.utcnow() + timedelta(seconds=120)

    assert abs((retry_at_2 - expected_retry_2).total_seconds()) < 2

    # Third failure (retry_count=2) → backoff 240s
    redis_client.reset_mock()
    await dlq_service.enqueue_failed_message(
        message=sample_message, error=error, retry_count=2
    )

    zadd_call_3 = redis_client.zadd.call_args_list[0]
    retry_timestamp_3 = list(zadd_call_3[0][1].values())[0]
    retry_at_3 = datetime.fromtimestamp(retry_timestamp_3)
    expected_retry_3 = datetime.utcnow() + timedelta(seconds=240)

    assert abs((retry_at_3 - expected_retry_3).total_seconds()) < 2


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Requires orchestrator integration - tested in integration tests")
async def test_max_retries_triggers_permanent_failure(dlq_service, redis_client, db_session, sample_message):
    """Test that after 3 failed retries, message is marked as permanent failure."""
    error = Exception("Persistent error")
    dlq_id = "test-dlq-id-123"
    
    # Mock Redis to return message data
    dlq_data = {
        "dlq_id": dlq_id,
        "message": {
            "message_id": sample_message.message_id,
            "canal": sample_message.canal,
            "user_id": sample_message.user_id,
            "timestamp_iso": sample_message.timestamp_iso,
            "tipo": sample_message.tipo,
            "texto": sample_message.texto,
            "media_url": sample_message.media_url,
            "metadata": sample_message.metadata,
            "tenant_id": sample_message.tenant_id,
        },
        "error_type": "Exception",
        "error_message": str(error),
        "error_traceback": "traceback here",
        "retry_count": 2,  # Already failed twice
        "first_failed_at": datetime.utcnow().isoformat(),
        "retry_at": datetime.utcnow().isoformat(),
        "correlation_id": "test-123",
    }
    
    redis_client.hgetall.return_value = {
        k.encode(): json.dumps(v).encode() for k, v in dlq_data.items()
    }
    
    # Mock orchestrator module to fail again (3rd retry)
    with patch("app.services.dlq_service.orchestrator") as mock_orch_module:
        mock_orch = AsyncMock()
        mock_orch.process_message = AsyncMock(side_effect=Exception("Still failing"))
        mock_orch_module._orchestrator_instance = mock_orch
        
        # Retry should fail and trigger permanent failure
        result = await dlq_service.retry_message(dlq_id)
        
        assert result is False  # Retry failed
        
        # Verify permanent failure was saved to DB
        db_session.add.assert_called_once()
        added_entry = db_session.add.call_args[0][0]
        assert isinstance(added_entry, DLQEntry)
        assert added_entry.id == dlq_id
        assert added_entry.retry_count == 2
        
        db_session.commit.assert_called_once()
        
        # Verify removed from Redis
        redis_client.delete.assert_called_once()
        redis_client.zrem.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Requires orchestrator integration - tested in integration tests")
async def test_retry_success_removes_from_dlq(dlq_service, redis_client, sample_message):
    """Test that successful retry removes message from DLQ."""
    dlq_id = "test-dlq-success"
    
    dlq_data = {
        "dlq_id": dlq_id,
        "message": {
            "message_id": sample_message.message_id,
            "canal": sample_message.canal,
            "user_id": sample_message.user_id,
            "timestamp_iso": sample_message.timestamp_iso,
            "tipo": sample_message.tipo,
            "texto": sample_message.texto,
            "media_url": sample_message.media_url,
            "metadata": sample_message.metadata,
            "tenant_id": sample_message.tenant_id,
        },
        "error_type": "Exception",
        "error_message": "Temporary error",
        "error_traceback": "traceback",
        "retry_count": 1,
        "first_failed_at": datetime.utcnow().isoformat(),
        "retry_at": datetime.utcnow().isoformat(),
        "correlation_id": "test-123",
    }
    
    redis_client.hgetall.return_value = {
        k.encode(): json.dumps(v).encode() for k, v in dlq_data.items()
    }
    
    # Mock orchestrator module to succeed this time
    with patch("app.services.dlq_service.orchestrator") as mock_orch_module:
        mock_orch = AsyncMock()
        mock_orch.process_message = AsyncMock(return_value={"status": "success"})
        mock_orch_module._orchestrator_instance = mock_orch
        
        # Retry should succeed
        result = await dlq_service.retry_message(dlq_id)
        
        assert result is True  # Retry succeeded
        
        # Verify removed from Redis
        redis_client.delete.assert_called_once_with(f"dlq:messages:{dlq_id}")
        redis_client.zrem.assert_called_once_with("dlq:retry_schedule", dlq_id)
        redis_client.decr.assert_called_once()


@pytest.mark.asyncio
async def test_dlq_ttl_expiration(dlq_service, redis_client):
    """Test that messages expire after TTL (7 days)."""
    
    # Mock Redis to return expired message IDs
    expired_ids = [b"expired-1", b"expired-2", b"expired-3"]
    redis_client.zrangebyscore.return_value = expired_ids
    
    # Run cleanup
    count = await dlq_service.cleanup_expired_messages()
    
    assert count == 3  # 3 messages cleaned up
    
    # Verify Redis operations
    assert redis_client.delete.call_count == 3
    assert redis_client.zrem.call_count == 3
    assert redis_client.decr.call_count == 3


@pytest.mark.asyncio
async def test_get_queue_size(dlq_service, redis_client):
    """Test getting current DLQ queue size."""
    redis_client.get.return_value = b"42"
    
    size = await dlq_service.get_queue_size()
    
    assert size == 42
    redis_client.get.assert_called_once_with("dlq:stats:total")


@pytest.mark.asyncio
async def test_get_retry_candidates(dlq_service, redis_client, sample_message):
    """Test getting messages ready for retry."""
    current_time = datetime.utcnow()
    past_time = current_time - timedelta(minutes=5)  # Ready for retry
    
    dlq_id = "ready-for-retry"
    dlq_data = {
        "dlq_id": dlq_id,
        "message": {
            "message_id": sample_message.message_id,
            "canal": sample_message.canal,
            "user_id": sample_message.user_id,
            "timestamp_iso": sample_message.timestamp_iso,
            "tipo": sample_message.tipo,
            "texto": sample_message.texto,
            "media_url": sample_message.media_url,
            "metadata": sample_message.metadata,
            "tenant_id": sample_message.tenant_id,
        },
        "error_type": "Exception",
        "error_message": "Error",
        "retry_count": 1,
        "first_failed_at": past_time.isoformat(),
        "retry_at": past_time.isoformat(),
        "correlation_id": "test",
    }
    
    # Mock Redis sorted set to return candidate
    redis_client.zrangebyscore.return_value = [dlq_id.encode()]
    
    # Mock Redis hash to return message data
    redis_client.hgetall.return_value = {
        k.encode(): json.dumps(v).encode() for k, v in dlq_data.items()
    }
    
    candidates = await dlq_service.get_retry_candidates()
    
    assert len(candidates) == 1
    assert candidates[0]["dlq_id"] == dlq_id
    assert candidates[0]["retry_count"] == 1
    
    # Verify query used current timestamp
    redis_client.zrangebyscore.assert_called_once()
    call_args = redis_client.zrangebyscore.call_args
    assert call_args[1]["min"] == 0
    assert call_args[1]["max"] <= current_time.timestamp() + 1  # Allow 1s tolerance
