import asyncio
import json
from datetime import datetime, UTC

import pytest
import pytest_asyncio

from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError

from app.services.session_manager import (
    SessionManager,
    active_sessions,
    session_save_retries,
    session_expirations,
)


class FakeRedis:
    """Minimal async Redis-like client for testing SessionManager.

    Supports: get, set(ex=ttl), delete, scan(match, count)
    - Stores values in-memory (as JSON strings like real Redis would)
    - Tracks TTL per key (not enforced automatically)
    - scan() returns all keys that match the pattern and ignores cursor semantics
    """

    def __init__(self):
        self._store: dict[str, str] = {}
        self._ttl: dict[str, int] = {}
        # For simulating transient failures on set
        self._set_failures: list[BaseException] = []

    # Helpers to control behavior in tests
    def fail_next_set_with(self, exc: BaseException):
        self._set_failures.append(exc)

    # Redis API (async)
    async def get(self, key: str):
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        if self._set_failures:
            # Pop the first planned failure and raise it
            exc = self._set_failures.pop(0)
            raise exc
        self._store[key] = value
        if ex is not None:
            self._ttl[key] = ex

    async def delete(self, key: str):
        self._store.pop(key, None)
        self._ttl.pop(key, None)

    async def scan(self, cursor: int = 0, match: str | None = None, count: int = 10):
        # Very simplified SCAN: return all matching keys in one batch and cursor=0
        if match is None:
            keys = list(self._store.keys())
        else:
            # Only support prefix match patterns like 'session:*'
            if match.endswith("*"):
                prefix = match[:-1]
                keys = [k for k in self._store.keys() if k.startswith(prefix)]
            else:
                keys = [k for k in self._store.keys() if k == match]
        # Mimic Redis returning bytes for keys (SessionManager handles str keys)
        # We'll return str keys to keep it simple and compatible with JSON loads used in code.
        return 0, keys


@pytest_asyncio.fixture
async def fake_redis():
    return FakeRedis()


@pytest.mark.asyncio
async def test_get_or_create_session_creates_with_ttl_and_updates_metric(fake_redis):
    sm = SessionManager(redis_client=fake_redis, ttl=123)

    session = await sm.get_or_create_session(user_id="u1", canal="whatsapp", tenant_id="t1")

    # Basic shape
    assert session["user_id"] == "u1"
    assert session["canal"] == "whatsapp"
    assert session.get("tenant_id") == "t1"
    assert session["state"] == "initial"
    assert isinstance(datetime.fromisoformat(session["created_at"]), datetime)

    # Stored in Redis with prefixed key and TTL tracked
    key = "session:t1:u1"
    assert await fake_redis.get(key) is not None
    assert fake_redis._ttl.get(key) == 123

    # Metric updated
    assert active_sessions._value.get() == 1


@pytest.mark.asyncio
async def test_update_session_updates_last_activity_and_persists(fake_redis):
    sm = SessionManager(redis_client=fake_redis, ttl=10)
    session = await sm.get_or_create_session(user_id="u2", canal="gmail")

    before = datetime.now(UTC)
    # Simulate user context update
    session.setdefault("context", {})["last_intent"] = "check_availability"

    await sm.update_session("u2", session)

    raw = await fake_redis.get("session:u2")
    saved = json.loads(raw)

    # last_activity refreshed and is >= before
    last_activity = datetime.fromisoformat(saved["last_activity"])
    assert last_activity >= before

    # Context persisted
    assert saved["context"]["last_intent"] == "check_availability"

    # TTL refreshed on update
    assert fake_redis._ttl.get("session:u2") == 10


@pytest.mark.asyncio
async def test_save_with_retry_on_transient_errors(fake_redis):
    sm = SessionManager(redis_client=fake_redis, ttl=10, max_retries=3, retry_delay_base=0)

    # Make first set() call fail with a connection error, then succeed
    fake_redis.fail_next_set_with(RedisConnectionError("conn down"))

    session = await sm.get_or_create_session(user_id="u3", canal="whatsapp")

    # Should eventually succeed and record a retry
    # Check labeled counters directly
    retry_counter = session_save_retries.labels(operation="create", result="retry")._value.get()
    success_counter = session_save_retries.labels(operation="create", result="success")._value.get()

    assert retry_counter >= 1
    # success on retry is only logged if attempt>0 in _save_session_with_retry
    assert success_counter >= 1

    # And the session exists in store
    assert await fake_redis.get("session:u3") is not None


@pytest.mark.asyncio
async def test_cleanup_orphaned_sessions_removes_invalid_and_counts(fake_redis):
    sm = SessionManager(redis_client=fake_redis, ttl=10)

    # Valid session
    await fake_redis.set(
        "session:valid",
        json.dumps({"user_id": "a", "canal": "whatsapp", "state": "ok", "created_at": datetime.now(UTC).isoformat()}),
        ex=10,
    )
    # Invalid format (missing required fields)
    await fake_redis.set("session:badfmt", json.dumps({"foo": 1}), ex=10)
    # Corrupted JSON
    await fake_redis.set("session:corrupt", "{not-json}", ex=10)

    cleaned = await sm._cleanup_orphaned_sessions()

    # Should clean 2 (badfmt + corrupt), keep valid
    assert cleaned == 2
    assert await fake_redis.get("session:valid") is not None
    assert await fake_redis.get("session:badfmt") is None
    assert await fake_redis.get("session:corrupt") is None

    # Counters incremented by reasons
    invalid_fmt = session_expirations.labels(reason="invalid_format")._value.get()
    corrupted = session_expirations.labels(reason="corrupted")._value.get()

    assert invalid_fmt >= 1
    assert corrupted >= 1


@pytest.mark.asyncio
async def test_active_sessions_metric_counts_all_sessions(fake_redis):
    sm = SessionManager(redis_client=fake_redis, ttl=10)

    await sm.get_or_create_session(user_id="k1", canal="whatsapp")
    await sm.get_or_create_session(user_id="k2", canal="whatsapp")
    await sm.get_or_create_session(user_id="k3", canal="whatsapp")

    # Metric is updated on each get_or_create; should reflect 3
    assert active_sessions._value.get() == 3

    # After deleting one key and forcing a metric update, value should drop
    await fake_redis.delete("session:k2")
    await sm._update_active_sessions_metric()

    assert active_sessions._value.get() == 2
