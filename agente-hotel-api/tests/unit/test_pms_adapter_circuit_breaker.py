import json
from datetime import date, datetime

import pytest

from app.services.pms_adapter import QloAppsAdapter, circuit_breaker_state
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
        # No se usa en estos tests
        return 0, []


@pytest.mark.asyncio
async def test_check_availability_uses_stale_when_circuit_open(monkeypatch):
    redis = FakeRedis()
    adapter = QloAppsAdapter(redis)

    key = "availability:2025-11-01:2025-11-03:2:any"
    rooms = [{"room_id": "1", "room_type": "Doble", "price_per_night": 120.0, "currency": "USD"}]

    # Simular que no hay cache fresca al inicio, pero existe un valor "stale"
    # Forzamos _get_from_cache a devolver None en la primera llamada (chequeo inicial)
    # y datos en la segunda llamada (fallback tras CB abierto)
    calls = {"n": 0}

    async def _fake_get_from_cache(k: str):  # noqa: ANN001
        calls["n"] += 1
        if calls["n"] == 1:
            return None
        if k == key:
            return rooms
        return None

    adapter._get_from_cache = _fake_get_from_cache  # type: ignore[assignment]

    # Force circuit OPEN and not ready to reset
    adapter.circuit_breaker.state = CircuitState.OPEN
    adapter.circuit_breaker.last_failure_time = datetime.now()

    result = await adapter.check_availability(date(2025, 11, 1), date(2025, 11, 3), guests=2)

    # Should return stale data with marker
    assert isinstance(result, list) and len(result) == 1
    assert result[0].get("potentially_stale") is True

    # Stale marker key is set
    # Como _set_cache de fallback marca la clave :stale, esperamos verla en Redis
    assert f"{key}:stale" in redis.store

    # Gauge should reflect OPEN path (set to 1)
    assert circuit_breaker_state._value.get() == 1.0  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_check_availability_success_clears_stale(monkeypatch, mocker):
    redis = FakeRedis()
    adapter = QloAppsAdapter(redis)

    # Pre-mark stale
    key = "availability:2025-12-01:2025-12-05:1:any"
    await redis.setex(f"{key}:stale", 60, "true")

    # Stub qloapps client to return fresh data
    mock_q = mocker.AsyncMock()
    mock_q.check_availability = mocker.AsyncMock(
        return_value=[
            {
                "room_id": "2",
                "room_type": "Suite",
                "price_per_night": 200.0,
                "currency": "USD",
            }
        ]
    )
    monkeypatch.setattr(adapter, "qloapps", mock_q)

    # Ensure breaker closed
    adapter.circuit_breaker.state = CircuitState.CLOSED

    result = await adapter.check_availability(date(2025, 12, 1), date(2025, 12, 5), guests=1)

    # Fresh data returned without stale marker
    assert isinstance(result, list) and len(result) == 1
    assert "potentially_stale" not in result[0]

    # Stale key cleared
    assert f"{key}:stale" not in redis.store

    # Gauge should be CLOSED (0)
    assert circuit_breaker_state._value.get() == 0.0  # type: ignore[attr-defined]
