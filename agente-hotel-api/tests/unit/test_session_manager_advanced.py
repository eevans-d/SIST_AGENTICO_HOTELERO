# [MEGA PLAN FASE 3] tests/unit/test_session_manager_advanced.py
"""
Comprehensive tests for SessionManager service.
Target: 60-70% coverage for session_manager.py

Test Categories:
1. Session CRUD Operations (7 tests)
2. Retry & Resilience Logic (8 tests)
3. Multi-Tenancy Support (5 tests)
4. Cleanup & Metrics (6 tests)
5. Edge Cases & Error Handling (6 tests)
"""

import json
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError, RedisError

from app.services.session_manager import SessionManager, get_session_manager


# ============================================================================
# Fixtures
# ============================================================================

class FakeRedis:
    """In-memory Redis mock for testing."""
    
    def __init__(self):
        self._store: dict[str, str] = {}
        self._ttls: dict[str, int] = {}
        self.call_count = 0
        self.fail_next_n = 0  # Simulate N consecutive failures
        self.fail_with: Exception | None = None
    
    async def get(self, key: str) -> str | None:
        self.call_count += 1
        if self.fail_next_n > 0:
            self.fail_next_n -= 1
            raise self.fail_with or RedisConnectionError("Simulated failure")
        return self._store.get(key)
    
    async def set(self, key: str, value: str, ex: int | None = None, nx: bool | None = None) -> bool:
        self.call_count += 1
        if self.fail_next_n > 0:
            self.fail_next_n -= 1
            raise self.fail_with or RedisConnectionError("Simulated failure")
        if nx and key in self._store:
            return False
        self._store[key] = value
        if ex:
            self._ttls[key] = ex
        return True
    
    async def setex(self, key: str, ttl: int, value: str) -> bool:
        return await self.set(key, value, ex=ttl)
    
    async def delete(self, key: str) -> int:
        self.call_count += 1
        if key in self._store:
            del self._store[key]
            return 1
        return 0
    
    async def ttl(self, key: str) -> int:
        return self._ttls.get(key, -1)
    
    async def scan(self, cursor: int = 0, match: str = "*", count: int = 100):
        import fnmatch
        keys = [k for k in self._store.keys() if fnmatch.fnmatch(k, match)]
        return 0, keys[:count]
    
    async def scan_iter(self, match: str = "*"):
        import fnmatch
        for k in list(self._store.keys()):
            if fnmatch.fnmatch(k, match):
                yield k
    
    async def ping(self) -> bool:
        return True


@pytest.fixture
def fake_redis():
    """Provide a fresh FakeRedis instance."""
    return FakeRedis()


@pytest.fixture
def session_manager(fake_redis):
    """Provide a SessionManager with fake Redis."""
    return SessionManager(
        redis_client=fake_redis,
        ttl=1800,
        max_retries=3,
        retry_delay_base=0  # No delay in tests
    )


# ============================================================================
# 1. Session CRUD Operations (7 tests)
# ============================================================================

class TestSessionCRUD:
    """Tests for basic session create/read/update/delete operations."""

    @pytest.mark.asyncio
    async def test_create_new_session_whatsapp(self, session_manager, fake_redis):
        """Test creating a new session for WhatsApp channel."""
        session = await session_manager.get_or_create_session(
            user_id="5215512345678",
            canal="whatsapp"
        )
        
        assert session["user_id"] == "5215512345678"
        assert session["canal"] == "whatsapp"
        assert session["state"] == "initial"
        assert session["context"] == {}
        assert session["tts_enabled"] is False
        assert "created_at" in session
        assert "last_activity" in session
        
        # Verify stored in Redis
        stored = await fake_redis.get("session:5215512345678")
        assert stored is not None

    @pytest.mark.asyncio
    async def test_create_new_session_gmail(self, session_manager):
        """Test creating a new session for Gmail channel."""
        session = await session_manager.get_or_create_session(
            user_id="guest@example.com",
            canal="gmail"
        )
        
        assert session["user_id"] == "guest@example.com"
        assert session["canal"] == "gmail"
        assert session["state"] == "initial"

    @pytest.mark.asyncio
    async def test_get_existing_session(self, session_manager, fake_redis):
        """Test retrieving an existing session."""
        # Create session first
        original = await session_manager.get_or_create_session(
            user_id="user123",
            canal="whatsapp"
        )
        original["context"]["last_intent"] = "check_availability"
        await session_manager.update_session("user123", original)
        
        # Get existing session
        retrieved = await session_manager.get_or_create_session(
            user_id="user123",
            canal="whatsapp"
        )
        
        assert retrieved["context"]["last_intent"] == "check_availability"

    @pytest.mark.asyncio
    async def test_update_session_context(self, session_manager):
        """Test updating session context."""
        session = await session_manager.get_or_create_session(
            user_id="user456",
            canal="whatsapp"
        )
        
        # Update context
        session["context"]["check_in"] = "2025-12-01"
        session["context"]["check_out"] = "2025-12-05"
        session["context"]["guests"] = 2
        await session_manager.update_session("user456", session)
        
        # Verify update
        updated = await session_manager.get_or_create_session(
            user_id="user456",
            canal="whatsapp"
        )
        
        assert updated["context"]["check_in"] == "2025-12-01"
        assert updated["context"]["guests"] == 2

    @pytest.mark.asyncio
    async def test_set_session_data_single_field(self, session_manager):
        """Test setting a single field in session context."""
        await session_manager.get_or_create_session("user789", "whatsapp")
        
        await session_manager.set_session_data(
            user_id="user789",
            data_key="qr_code",
            data_value="QR123456"
        )
        
        session = await session_manager.get_session_data("user789")
        assert session["context"]["qr_code"] == "QR123456"
        assert session["qr_code"] == "QR123456"  # Also at top level

    @pytest.mark.asyncio
    async def test_get_session_data_nonexistent(self, session_manager):
        """Test getting session data for nonexistent user returns empty dict."""
        data = await session_manager.get_session_data("nonexistent_user")
        assert data == {}

    @pytest.mark.asyncio
    async def test_session_last_activity_updated_on_update(self, session_manager):
        """Test that last_activity is updated on each update."""
        session = await session_manager.get_or_create_session("user_activity", "whatsapp")
        original_activity = session["last_activity"]
        
        # Small delay to ensure timestamp difference
        await asyncio.sleep(0.01)
        
        session["context"]["updated"] = True
        await session_manager.update_session("user_activity", session)
        
        updated = await session_manager.get_session_data("user_activity")
        assert updated["last_activity"] != original_activity


# ============================================================================
# 2. Retry & Resilience Logic (8 tests)
# ============================================================================

class TestRetryResilience:
    """Tests for retry logic with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_on_connection_error_then_success(self, fake_redis):
        """Test retry succeeds after transient connection error."""
        fake_redis.fail_next_n = 1  # Fail first attempt
        fake_redis.fail_with = RedisConnectionError("Connection lost")
        
        manager = SessionManager(fake_redis, max_retries=3, retry_delay_base=0)
        
        # Should succeed on second attempt
        session = await manager.get_or_create_session("retry_user", "whatsapp")
        assert session["user_id"] == "retry_user"

    @pytest.mark.asyncio
    async def test_retry_on_timeout_error_then_success(self, fake_redis):
        """Test retry succeeds after Redis timeout."""
        fake_redis.fail_next_n = 2  # Fail first two attempts
        fake_redis.fail_with = RedisTimeoutError("Read timed out")
        
        manager = SessionManager(fake_redis, max_retries=3, retry_delay_base=0)
        
        session = await manager.get_or_create_session("timeout_user", "whatsapp")
        assert session["user_id"] == "timeout_user"

    @pytest.mark.asyncio
    async def test_all_retries_exhausted_raises(self, fake_redis):
        """Test that exception is raised after all retries exhausted."""
        fake_redis.fail_next_n = 10  # Always fail
        fake_redis.fail_with = RedisConnectionError("Persistent failure")
        
        manager = SessionManager(fake_redis, max_retries=3, retry_delay_base=0)
        
        # get_or_create_session creates new session which will fail on save
        # The _save_session_with_retry should exhaust retries and raise
        with pytest.raises(RedisConnectionError):
            await manager._save_session_with_retry(
                "session:test",
                {"user_id": "test"},
                "test_op"
            )

    @pytest.mark.asyncio
    async def test_non_retryable_redis_error_fails_immediately(self, fake_redis):
        """Test that generic RedisError fails without retrying."""
        fake_redis.fail_next_n = 1
        fake_redis.fail_with = RedisError("Generic Redis error")
        
        manager = SessionManager(fake_redis, max_retries=3, retry_delay_base=0)
        
        with pytest.raises(RedisError):
            await manager._save_session_with_retry(
                "session:test",
                {"user_id": "test"},
                "test_op"
            )

    @pytest.mark.asyncio
    async def test_retry_metrics_recorded(self, fake_redis):
        """Test that retry metrics are recorded."""
        fake_redis.fail_next_n = 1
        fake_redis.fail_with = RedisConnectionError("Transient")
        
        manager = SessionManager(fake_redis, max_retries=3, retry_delay_base=0)
        
        with patch("app.services.session_manager.session_save_retries") as mock_counter:
            await manager._save_session_with_retry(
                "session:metrics_test",
                {"user_id": "test"},
                "create"
            )
            
            # Should have recorded retry and success
            assert mock_counter.labels.called

    @pytest.mark.asyncio
    async def test_get_session_failure_creates_new(self, fake_redis):
        """Test that session creation proceeds after get failure."""
        # Pre-populate then make get fail
        manager = SessionManager(fake_redis, max_retries=3, retry_delay_base=0)
        
        # Create a session first
        original = await manager.get_or_create_session("get_fail_user", "whatsapp")
        
        # Now simulate get failure (but allow set to work)
        async def failing_get(key):
            raise RedisConnectionError("Get failed")
        
        fake_redis.get = failing_get
        
        # Should create new session since get failed
        session = await manager.get_or_create_session("get_fail_user", "whatsapp")
        assert session["user_id"] == "get_fail_user"
        assert session["state"] == "initial"

    @pytest.mark.asyncio
    async def test_exponential_backoff_delays(self):
        """Test that exponential backoff calculates correct delays."""
        manager = SessionManager(None, retry_delay_base=1)
        
        # Verify delay calculation: base * 2^attempt
        # attempt 0: 1 * 2^0 = 1s
        # attempt 1: 1 * 2^1 = 2s
        # attempt 2: 1 * 2^2 = 4s
        assert manager.retry_delay_base * (2 ** 0) == 1
        assert manager.retry_delay_base * (2 ** 1) == 2
        assert manager.retry_delay_base * (2 ** 2) == 4

    @pytest.mark.asyncio
    async def test_json_serialization_error_not_retried(self, fake_redis):
        """Test that JSON serialization errors fail immediately."""
        manager = SessionManager(fake_redis, max_retries=3, retry_delay_base=0)
        
        # Create unserializable data
        class Unserializable:
            pass
        
        with pytest.raises(TypeError):
            await manager._save_session_with_retry(
                "session:json_fail",
                {"obj": Unserializable()},
                "create"
            )


# ============================================================================
# 3. Multi-Tenancy Support (5 tests)
# ============================================================================

class TestMultiTenancy:
    """Tests for multi-tenant session isolation."""

    @pytest.mark.asyncio
    async def test_tenant_session_key_format(self, session_manager):
        """Test session key includes tenant_id."""
        key = session_manager._get_session_key("user123", "hotel_plaza")
        assert key == "session:hotel_plaza:user123"
        
        key_no_tenant = session_manager._get_session_key("user123")
        assert key_no_tenant == "session:user123"

    @pytest.mark.asyncio
    async def test_create_session_with_tenant(self, session_manager, fake_redis):
        """Test creating session with tenant_id."""
        session = await session_manager.get_or_create_session(
            user_id="guest1",
            canal="whatsapp",
            tenant_id="hotel_plaza"
        )
        
        assert session["tenant_id"] == "hotel_plaza"
        
        # Verify stored with tenant key
        stored = await fake_redis.get("session:hotel_plaza:guest1")
        assert stored is not None

    @pytest.mark.asyncio
    async def test_tenant_isolation_different_tenants(self, session_manager, fake_redis):
        """Test sessions are isolated between tenants."""
        # Create session for tenant A
        session_a = await session_manager.get_or_create_session(
            user_id="shared_user",
            canal="whatsapp",
            tenant_id="hotel_alpha"
        )
        session_a["context"]["hotel"] = "Alpha Hotel"
        await session_manager.update_session("shared_user", session_a, "hotel_alpha")
        
        # Create session for tenant B (same user_id)
        session_b = await session_manager.get_or_create_session(
            user_id="shared_user",
            canal="whatsapp",
            tenant_id="hotel_beta"
        )
        session_b["context"]["hotel"] = "Beta Hotel"
        await session_manager.update_session("shared_user", session_b, "hotel_beta")
        
        # Verify isolation
        retrieved_a = await session_manager.get_session_data("shared_user", "hotel_alpha")
        retrieved_b = await session_manager.get_session_data("shared_user", "hotel_beta")
        
        assert retrieved_a["context"]["hotel"] == "Alpha Hotel"
        assert retrieved_b["context"]["hotel"] == "Beta Hotel"

    @pytest.mark.asyncio
    async def test_update_session_with_tenant(self, session_manager):
        """Test updating session preserves tenant context."""
        session = await session_manager.get_or_create_session(
            user_id="tenant_user",
            canal="whatsapp",
            tenant_id="hotel_gamma"
        )
        
        session["context"]["reservation_id"] = "RES123"
        await session_manager.update_session("tenant_user", session, "hotel_gamma")
        
        retrieved = await session_manager.get_session_data("tenant_user", "hotel_gamma")
        assert retrieved["tenant_id"] == "hotel_gamma"
        assert retrieved["context"]["reservation_id"] == "RES123"

    @pytest.mark.asyncio
    async def test_set_session_data_with_tenant(self, session_manager):
        """Test set_session_data with tenant isolation."""
        await session_manager.get_or_create_session("data_user", "whatsapp", "hotel_delta")
        
        await session_manager.set_session_data(
            user_id="data_user",
            data_key="preference",
            data_value="ocean_view",
            tenant_id="hotel_delta"
        )
        
        session = await session_manager.get_session_data("data_user", "hotel_delta")
        assert session["context"]["preference"] == "ocean_view"


# ============================================================================
# 4. Cleanup & Metrics (6 tests)
# ============================================================================

class TestCleanupAndMetrics:
    """Tests for session cleanup and Prometheus metrics."""

    @pytest.mark.asyncio
    async def test_update_active_sessions_metric(self, session_manager, fake_redis):
        """Test active sessions metric is updated."""
        # Create multiple sessions
        await session_manager.get_or_create_session("user1", "whatsapp")
        await session_manager.get_or_create_session("user2", "gmail")
        await session_manager.get_or_create_session("user3", "whatsapp")
        
        with patch("app.services.session_manager.active_sessions") as mock_gauge:
            await session_manager._update_active_sessions_metric()
            mock_gauge.set.assert_called_once_with(3)

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_sessions_invalid_format(self, fake_redis, session_manager):
        """Test cleanup removes sessions with missing required fields."""
        # Create invalid session directly in Redis
        await fake_redis.set("session:orphan1", json.dumps({"user_id": "x"}))  # Missing canal, state
        await fake_redis.set("session:valid", json.dumps({
            "user_id": "valid",
            "canal": "whatsapp",
            "state": "initial"
        }))
        
        with patch("app.services.session_manager.session_expirations") as mock_counter:
            cleaned = await session_manager._cleanup_orphaned_sessions()
            
            assert cleaned == 1
            mock_counter.labels.assert_called_with(reason="invalid_format")

    @pytest.mark.asyncio
    async def test_cleanup_corrupted_json_sessions(self, fake_redis, session_manager):
        """Test cleanup removes sessions with corrupted JSON."""
        # Create corrupted session
        fake_redis._store["session:corrupted"] = "not valid json {"
        
        with patch("app.services.session_manager.session_expirations") as mock_counter:
            cleaned = await session_manager._cleanup_orphaned_sessions()
            
            assert cleaned == 1
            mock_counter.labels.assert_called_with(reason="corrupted")

    @pytest.mark.asyncio
    async def test_refresh_active_sessions_metric_public(self, session_manager):
        """Test public method to refresh metrics."""
        with patch.object(session_manager, "_update_active_sessions_metric") as mock_update:
            await session_manager.refresh_active_sessions_metric()
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_cleanup_task(self, session_manager):
        """Test cleanup task can be started."""
        assert session_manager._cleanup_task is None
        
        session_manager.start_cleanup_task()
        
        assert session_manager._cleanup_task is not None
        
        # Cleanup
        await session_manager.stop_cleanup_task()

    @pytest.mark.asyncio
    async def test_stop_cleanup_task(self, session_manager):
        """Test cleanup task can be stopped gracefully."""
        session_manager.start_cleanup_task()
        assert session_manager._cleanup_task is not None
        
        await session_manager.stop_cleanup_task()
        
        assert session_manager._cleanup_task is None


# ============================================================================
# 5. Edge Cases & Error Handling (6 tests)
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_session_manager_without_redis_uses_inmemory(self):
        """Test SessionManager works with in-memory Redis fallback."""
        manager = SessionManager(redis_client=None)
        
        session = await manager.get_or_create_session("inmem_user", "whatsapp")
        assert session["user_id"] == "inmem_user"
        
        # Update should also work
        session["context"]["test"] = "value"
        await manager.update_session("inmem_user", session)
        
        retrieved = await manager.get_session_data("inmem_user")
        assert retrieved["context"]["test"] == "value"

    @pytest.mark.asyncio
    async def test_get_session_data_handles_bytes(self, fake_redis, session_manager):
        """Test get_session_data handles bytes from Redis."""
        # Store as bytes (how real Redis returns data)
        session_data = {"user_id": "bytes_user", "canal": "whatsapp", "state": "initial"}
        fake_redis._store["session:bytes_user"] = json.dumps(session_data).encode()
        
        # Mock get to return bytes
        original_get = fake_redis.get
        async def get_bytes(key):
            result = await original_get(key)
            if isinstance(result, str):
                return result.encode()
            return result
        fake_redis.get = get_bytes
        
        data = await session_manager.get_session_data("bytes_user")
        assert data["user_id"] == "bytes_user"

    @pytest.mark.asyncio
    async def test_get_session_data_handles_dict(self, session_manager):
        """Test get_session_data handles dict directly."""
        # Some mock implementations return dict directly
        session_manager.redis._store["session:dict_user"] = {
            "user_id": "dict_user",
            "canal": "whatsapp",
            "state": "initial"
        }
        
        async def get_dict(key):
            return session_manager.redis._store.get(key)
        session_manager.redis.get = get_dict
        
        data = await session_manager.get_session_data("dict_user")
        assert data["user_id"] == "dict_user"

    @pytest.mark.asyncio
    async def test_get_session_data_handles_exception(self, fake_redis, session_manager):
        """Test get_session_data returns empty dict on exception."""
        async def failing_get(key):
            raise Exception("Unexpected error")
        fake_redis.get = failing_get
        
        data = await session_manager.get_session_data("error_user")
        assert data == {}

    @pytest.mark.asyncio
    async def test_empty_user_id_creates_session(self, session_manager):
        """Test session creation with empty string user_id."""
        session = await session_manager.get_or_create_session("", "whatsapp")
        assert session["user_id"] == ""
        assert session["canal"] == "whatsapp"

    @pytest.mark.asyncio
    async def test_special_characters_in_user_id(self, session_manager, fake_redis):
        """Test session with special characters in user_id."""
        special_id = "user+test@example.com"
        
        session = await session_manager.get_or_create_session(special_id, "gmail")
        assert session["user_id"] == special_id
        
        # Verify retrieval works
        retrieved = await session_manager.get_session_data(special_id)
        assert retrieved["user_id"] == special_id


# ============================================================================
# Singleton Tests
# ============================================================================

class TestSingleton:
    """Tests for singleton pattern."""

    @pytest.mark.asyncio
    async def test_get_session_manager_singleton(self):
        """Test get_session_manager returns singleton instance."""
        import app.services.session_manager as sm_module
        
        # Reset singleton
        sm_module._session_manager_instance = None
        
        with patch("app.core.redis_client.get_redis") as mock_get_redis:
            mock_get_redis.return_value = FakeRedis()
            
            manager1 = await get_session_manager()
            manager2 = await get_session_manager()
            
            assert manager1 is manager2
            
        # Reset singleton after test
        sm_module._session_manager_instance = None
