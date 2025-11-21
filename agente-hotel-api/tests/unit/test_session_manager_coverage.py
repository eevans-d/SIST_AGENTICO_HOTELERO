import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError, RedisError
from app.services.session_manager import SessionManager

@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    # Default behaviors
    mock.set = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.delete = AsyncMock(return_value=1)
    mock.ttl = AsyncMock(return_value=1800)
    return mock

@pytest.fixture
def session_manager(mock_redis):
    return SessionManager(redis_client=mock_redis)

@pytest.mark.asyncio
async def test_init_fallback():
    """Test initialization without redis client falls back to in-memory"""
    manager = SessionManager(redis_client=None)
    assert manager.redis is not None
    # Verify in-memory redis behavior
    await manager.redis.set("test_key", "test_val")
    val = await manager.redis.get("test_key")
    assert val == "test_val"

@pytest.mark.asyncio
async def test_get_session_key(session_manager):
    """Test session key generation"""
    # Without tenant
    key = session_manager._get_session_key("user123")
    assert key == "session:user123"
    
    # With tenant
    key = session_manager._get_session_key("user123", "tenantABC")
    assert key == "session:tenantABC:user123"

@pytest.mark.asyncio
async def test_save_session_success(session_manager, mock_redis):
    """Test successful session save"""
    session_data = {"user_id": "u1", "state": "active"}
    result = await session_manager._save_session_with_retry("key1", session_data)
    
    assert result is True
    mock_redis.set.assert_called_once()
    args = mock_redis.set.call_args
    assert args[0][0] == "key1"
    assert json.loads(args[0][1]) == session_data
    assert args[1]['ex'] == session_manager.ttl

@pytest.mark.asyncio
async def test_save_session_retry_success(session_manager, mock_redis):
    """Test save succeeds after one failure"""
    # Fail first time, succeed second time
    mock_redis.set.side_effect = [RedisConnectionError("Connection lost"), True]
    
    # Reduce delay for test speed
    session_manager.retry_delay_base = 0.01
    
    result = await session_manager._save_session_with_retry("key1", {})
    
    assert result is True
    assert mock_redis.set.call_count == 2

@pytest.mark.asyncio
async def test_save_session_max_retries_exceeded(session_manager, mock_redis):
    """Test save fails after max retries"""
    mock_redis.set.side_effect = RedisConnectionError("Persistent failure")
    session_manager.retry_delay_base = 0.01
    
    with pytest.raises(RedisConnectionError):
        await session_manager._save_session_with_retry("key1", {})
    
    assert mock_redis.set.call_count == session_manager.max_retries

@pytest.mark.asyncio
async def test_save_session_non_transient_error(session_manager, mock_redis):
    """Test immediate failure on non-transient error"""
    mock_redis.set.side_effect = RedisError("Generic error")
    
    with pytest.raises(RedisError):
        await session_manager._save_session_with_retry("key1", {})
    
    assert mock_redis.set.call_count == 1

@pytest.mark.asyncio
async def test_get_or_create_existing_session(session_manager, mock_redis):
    """Test retrieving an existing session"""
    existing_session = {
        "user_id": "user123",
        "canal": "whatsapp",
        "state": "active"
    }
    mock_redis.get.return_value = json.dumps(existing_session)
    
    session = await session_manager.get_or_create_session("user123", "whatsapp")
    
    assert session == existing_session
    mock_redis.get.assert_called_once()
    # Should not save if just retrieving
    mock_redis.set.assert_not_called()

@pytest.mark.asyncio
async def test_get_or_create_new_session(session_manager, mock_redis):
    """Test creating a new session when none exists"""
    mock_redis.get.return_value = None
    
    session = await session_manager.get_or_create_session("user123", "whatsapp", "tenant1")
    
    assert session["user_id"] == "user123"
    assert session["canal"] == "whatsapp"
    assert session["tenant_id"] == "tenant1"
    assert session["state"] == "initial"
    
    # Should save the new session
    mock_redis.set.assert_called_once()

@pytest.mark.asyncio
async def test_get_or_create_redis_error_handled(session_manager, mock_redis):
    """Test error handling during get_or_create - read fails but write succeeds"""
    mock_redis.get.side_effect = RedisError("Read failed")
    
    # Should not raise, but return a new session
    session = await session_manager.get_or_create_session("user123", "whatsapp")
    assert session["user_id"] == "user123"
    assert session["state"] == "initial"
    
    # Verify it tried to save the new session
    mock_redis.set.assert_called_once()

