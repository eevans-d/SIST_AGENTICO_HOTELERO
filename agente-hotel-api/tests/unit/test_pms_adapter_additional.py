from datetime import date, datetime
import json

import pytest

from app.services.pms_adapter import QloAppsAdapter, PMSError, PMSAuthError, circuit_breaker_state
from app.core.circuit_breaker import CircuitState


class FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self.store[key] = value
        return True

    async def delete(self, *keys: str):
        for k in keys:
            self.store.pop(k, None)
        return True

    async def scan(self, cursor: int = 0, match: str | None = None, count: int = 100):
        if match is None:
            keys = list(self.store.keys())
        else:
            keys = [k for k in self.store.keys() if match.replace("*", "") in k]
        return 0, keys


@pytest.mark.asyncio
async def test_cb_open_no_stale_returns_empty_list(mocker):
    redis = FakeRedis()
    adapter = QloAppsAdapter(redis)

    # Force CB OPEN, no stale available
    adapter.circuit_breaker.state = CircuitState.OPEN
    adapter.circuit_breaker.last_failure_time = datetime.now()

    # Ensure cache miss in both attempts
    async def _fake_get_from_cache(_key: str):
        return None

    adapter._get_from_cache = _fake_get_from_cache  # type: ignore[assignment]

    result = await adapter.check_availability(date(2025, 11, 1), date(2025, 11, 3), guests=2)
    assert result == []
    assert circuit_breaker_state._value.get() == 1.0  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_error_path_uses_stale_and_marks_stale(mocker):
    redis = FakeRedis()
    adapter = QloAppsAdapter(redis)

    key = "availability:2025-11-10:2025-11-12:1:any"
    rooms = [{"room_id": "1", "room_type": "Doble", "price_per_night": 120.0, "currency": "USD"}]

    calls = {"n": 0}

    async def _fake_get_from_cache(k: str):  # noqa: ANN001
        calls["n"] += 1
        if calls["n"] == 1:
            return None
        if k == key:
            return rooms
        return None

    adapter._get_from_cache = _fake_get_from_cache  # type: ignore[assignment]

    # Force circuit breaker call to raise generic Exception path
    async def _fake_cb_call(func, inner, operation_label=None):  # noqa: ANN001
        raise Exception("network error")

    adapter.circuit_breaker.call = _fake_cb_call  # type: ignore[assignment]

    result = await adapter.check_availability(date(2025, 11, 10), date(2025, 11, 12), guests=1)
    assert isinstance(result, list) and result and result[0].get("potentially_stale") is True
    assert f"{key}:stale" in redis.store


@pytest.mark.asyncio
async def test_auth_error_propagates_without_stale(monkeypatch):
    redis = FakeRedis()
    adapter = QloAppsAdapter(redis)

    async def _fail_auth(**kwargs):  # noqa: ANN001
        raise PMSAuthError("bad token")

    monkeypatch.setattr(adapter.qloapps, "check_availability", _fail_auth)

    with pytest.raises(PMSAuthError):
        await adapter.check_availability(date(2025, 12, 1), date(2025, 12, 2), guests=1)


@pytest.mark.asyncio
async def test_create_reservation_invalidates_availability_cache(monkeypatch, mocker):
    redis = FakeRedis()
    adapter = QloAppsAdapter(redis)

    # Stub create_booking
    mock_q = mocker.AsyncMock()
    mock_q.create_booking = mocker.AsyncMock(return_value={"booking_reference": "BK-1"})
    monkeypatch.setattr(adapter, "qloapps", mock_q)

    spy_invalidate = mocker.AsyncMock()
    monkeypatch.setattr(adapter, "_invalidate_cache_pattern", spy_invalidate)

    payload = {
        "checkin": "2025-12-01T00:00:00Z",
        "checkout": "2025-12-03T00:00:00Z",
        "room_type": "double",
        "guests": 2,
        "guest_name": "John Doe",
        "guest_email": "john@example.com",
    }

    result = await adapter.create_reservation(payload)
    assert result.get("booking_reference") == "BK-1"
    spy_invalidate.assert_called_once()
    assert spy_invalidate.call_args[0][0] == "availability:*"


@pytest.mark.asyncio
async def test_cancel_reservation_success_invalidates_cache(monkeypatch, mocker):
    redis = FakeRedis()
    adapter = QloAppsAdapter(redis)

    mock_q = mocker.AsyncMock()
    mock_q.cancel_booking = mocker.AsyncMock(return_value=True)
    monkeypatch.setattr(adapter, "qloapps", mock_q)

    spy_invalidate = mocker.AsyncMock()
    monkeypatch.setattr(adapter, "_invalidate_cache_pattern", spy_invalidate)

    ok = await adapter.cancel_reservation("123")
    assert ok is True
    spy_invalidate.assert_called_once()


@pytest.mark.asyncio
async def test_get_reservation_error_raises_pmserror(monkeypatch):
    redis = FakeRedis()
    adapter = QloAppsAdapter(redis)

    async def _fail_get(_id):  # noqa: ANN001
        raise Exception("db down")

    monkeypatch.setattr(adapter.qloapps, "get_booking", _fail_get)

    with pytest.raises(PMSError):
        await adapter.get_reservation("123")


@pytest.mark.asyncio
async def test_late_checkout_cache_hit(monkeypatch):
    redis = FakeRedis()
    adapter = QloAppsAdapter(redis)

    # Booking stub
    async def _get_booking(_id):  # noqa: ANN001
        return {
            "room_id": 10,
            "checkout_date": "2025-12-10T00:00:00Z",
            "price_per_night": 100.0,
        }

    monkeypatch.setattr(adapter.qloapps, "get_booking", _get_booking)

    # Pre-populate cache
    cache_key = "late_checkout_check:123:2025-12-10T00:00:00Z"
    payload = {
        "available": True,
        "fee": 50.0,
        "daily_rate": 100.0,
        "requested_time": "14:00",
        "standard_checkout": "12:00",
        "next_booking_id": None,
        "message": "Late checkout available",
    }
    await redis.setex(cache_key, 300, json.dumps(payload))

    result = await adapter.check_late_checkout_availability("123", requested_checkout_time="14:00")
    assert result == payload


@pytest.mark.asyncio
async def test_confirm_late_checkout_not_available(monkeypatch):
    redis = FakeRedis()
    adapter = QloAppsAdapter(redis)

    async def _not_available(reservation_id: str, requested_checkout_time: str = "14:00"):
        return {"available": False, "fee": 50.0}

    monkeypatch.setattr(adapter, "check_late_checkout_availability", _not_available)

    result = await adapter.confirm_late_checkout("123", checkout_time="14:00")
    assert result["success"] is False
    assert "not available" in result["message"].lower()
