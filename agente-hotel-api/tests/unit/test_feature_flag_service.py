import asyncio

import pytest

from app.services.feature_flag_service import FeatureFlagService


class DummyRedis:
    def __init__(self):
        self.store = {"feature_flags": {}}

    async def hget(self, name, key):  # mimic async redis
        bucket = self.store.get(name, {})
        val = bucket.get(key)
        if val is None:
            return None
        return str(val).encode()

    async def hset(self, name, key, value):  # mimic async redis
        bucket = self.store.setdefault(name, {})
        bucket[key] = value
        return 1


@pytest.mark.asyncio
async def test_default_flag_values():
    svc = FeatureFlagService(DummyRedis())
    # Usa defaults
    assert await svc.is_enabled("nlp.fallback.enhanced") is True
    assert await svc.is_enabled("canary.enabled") is False


@pytest.mark.asyncio
async def test_set_and_get_flag():
    svc = FeatureFlagService(DummyRedis())
    await svc.set_flag("canary.enabled", True)
    assert await svc.is_enabled("canary.enabled") is True


@pytest.mark.asyncio
async def test_flag_cache_ttl():
    svc = FeatureFlagService(DummyRedis(), ttl_seconds=1)
    await svc.set_flag("multi_tenant.experimental", True)
    assert await svc.is_enabled("multi_tenant.experimental") is True
    # Cambiamos valor debajo sin invalidar cache
    await svc.redis.hset("feature_flags", "multi_tenant.experimental", 0)
    # Debe seguir true por caché
    assert await svc.is_enabled("multi_tenant.experimental") is True
    await asyncio.sleep(1.1)
    # Expira caché => recoge false
    assert await svc.is_enabled("multi_tenant.experimental") is False
