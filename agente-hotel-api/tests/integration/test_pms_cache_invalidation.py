import json
import fnmatch

import pytest

from app.services.pms_adapter import QloAppsAdapter


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
        keys = list(self.store.keys())
        if match:
            keys = [k for k in keys if fnmatch.fnmatch(k, match)]
        # Return all at once for simplicity
        return 0, keys


@pytest.mark.asyncio
async def test_create_reservation_invalidates_availability_cache(mocker):
    redis = FakeRedis()
    adapter = QloAppsAdapter(redis)

    # Seed availability cache with two keys
    await redis.setex(
        "availability:2025-11-01:2025-11-03:2:any",
        300,
        json.dumps([
            {"room_id": "1", "room_type": "Doble", "price_per_night": 100.0, "currency": "USD"}
        ]),
    )
    await redis.setex(
        "availability:2025-12-20:2025-12-25:2:su ite",
        300,
        json.dumps([
            {"room_id": "2", "room_type": "Suite", "price_per_night": 200.0, "currency": "USD"}
        ]),
    )

    # Stub qloapps client to avoid real calls
    mocker.patch.object(
        adapter,
        "qloapps",
        new=mocker.AsyncMock(
            create_booking=mocker.AsyncMock(
                return_value={
                    "booking_id": "123",
                    "booking_reference": "REF-123",
                    "status": "confirmed",
                    "total_amount": 200.0,
                    "currency": "USD",
                    "confirmation_sent": True,
                    "check_in": "2025-11-01",
                    "check_out": "2025-11-03",
                }
            )
        ),
    )

    # Create reservation (should trigger availability:* invalidation)
    payload = {
        "checkin": "2025-11-01",
        "checkout": "2025-11-03",
        "room_type": "Doble",
        "guests": 2,
        "guest_name": "John Doe",
        "guest_email": "john@example.com",
        "guest_phone": "+541112223334",
        "price_per_night": 100.0,
        "channel": "whatsapp",
    }

    result = await adapter.create_reservation(payload)

    # Both availability keys should be gone
    assert "availability:2025-11-01:2025-11-03:2:any" not in redis.store
    assert "availability:2025-12-20:2025-12-25:2:su ite" not in redis.store
    assert result.get("status") == "confirmed"


@pytest.mark.asyncio
async def test_cancel_reservation_invalidates_availability_cache(mocker):
    redis = FakeRedis()
    adapter = QloAppsAdapter(redis)

    # Seed availability cache
    await redis.setex(
        "availability:2025-10-20:2025-10-22:1:any",
        300,
        json.dumps([
            {"room_id": "1", "room_type": "Doble", "price_per_night": 150.0, "currency": "USD"}
        ]),
    )

    # Stub qloapps.cancel_booking to succeed
    mock_client = mocker.AsyncMock()
    mock_client.cancel_booking = mocker.AsyncMock(return_value=True)
    mocker.patch.object(adapter, "qloapps", new=mock_client)

    success = await adapter.cancel_reservation("123", reason="test")

    assert success is True
    # Availability cache should be invalidated
    assert not any(k.startswith("availability:") for k in redis.store.keys())
