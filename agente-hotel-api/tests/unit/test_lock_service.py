# [PROMPT 2.10] tests/unit/test_lock_service.py

import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import cast

import pytest

from app.services.lock_service import LockService
import redis.asyncio as aioredis


class FakeRedis:
    """Pequeña implementación en memoria de Redis (async) para pruebas.

    Soporta: set/get/delete/ttl/scan_iter con expiración por key.
    """

    def __init__(self):
        # key -> {"value": str, "expires_at": float|None}
        self._store = {}

    async def set(self, key: str, value: str, ex: int | None = None, nx: bool = False):
        # Limpieza si expiró
        self._cleanup_if_expired(key)

        if nx and key in self._store:
            return False

        expires_at = time.time() + ex if ex is not None else None
        self._store[key] = {"value": value, "expires_at": expires_at}
        return True

    async def get(self, key: str):
        self._cleanup_if_expired(key)
        data = self._store.get(key)
        return None if data is None else data["value"]

    async def delete(self, key: str):
        self._cleanup_if_expired(key)
        if key in self._store:
            del self._store[key]
            return 1
        return 0

    async def ttl(self, key: str):
        self._cleanup_if_expired(key)
        data = self._store.get(key)
        if not data:
            return -2  # clave no existe
        if data["expires_at"] is None:
            return -1  # sin expiración
        return max(0, int(data["expires_at"] - time.time()))

    async def scan_iter(self, pattern: str):
        # Soporte básico para patrones del tipo "prefix*"
        prefix = pattern[:-1] if pattern.endswith("*") else pattern
        # Hacer snapshot de claves para evitar RuntimeError al mutar durante iteración
        for key in list(self._store.keys()):
            self._cleanup_if_expired(key)
            if key.startswith(prefix) and key in self._store:
                yield key

    def _cleanup_if_expired(self, key: str):
        data = self._store.get(key)
        if not data:
            return
        exp = data["expires_at"]
        if exp is not None and exp <= time.time():
            self._store.pop(key, None)


@pytest.mark.asyncio
async def test_concurrent_lock_acquisition():
    redis = FakeRedis()
    service = LockService(cast(aioredis.Redis, redis))

    room_id = "101"
    check_in = "2025-11-10"
    check_out = "2025-11-12"

    async def attempt(i: int):
        return await service.acquire_lock(
            room_id=room_id,
            check_in=check_in,
            check_out=check_out,
            session_id=f"s{i}",
            user_id=f"u{i}",
            ttl=5,
        )

    # Lanzamos varias adquisiciones en paralelo para el mismo rango/room
    results = await asyncio.gather(*[attempt(i) for i in range(10)])

    # Solo una debería tener éxito (retorna lock_key), el resto debe ser None
    successes = [r for r in results if r]
    assert len(successes) == 1

    # El patrón de conflicto debe impedir una segunda adquisición posterior
    second_try = await attempt(99)
    assert second_try is None


@pytest.mark.asyncio
async def test_extend_and_release_lock():
    redis = FakeRedis()
    service = LockService(cast(aioredis.Redis, redis))

    key = await service.acquire_lock(
        room_id="202",
        check_in="2025-12-01",
        check_out="2025-12-05",
        session_id="sess1",
        user_id="user1",
        ttl=2,
    )
    assert key is not None

    # Verificar TTL inicial
    ttl1 = await redis.ttl(key)
    assert 0 <= ttl1 <= 2

    # Extender el lock
    ok = await service.extend_lock(key, extra_ttl=3, max_extensions=2)
    assert ok is True

    # TTL debe ser mayor tras la extensión
    ttl2 = await redis.ttl(key)
    assert ttl2 > ttl1

    # Verificar que el campo extensions del payload incrementó
    raw = await redis.get(key)
    assert raw is not None
    data = json.loads(raw)
    assert data["extensions"] == 1

    # Liberar el lock
    released = await service.release_lock(key)
    assert released is True

    # Segunda liberación no debe hacer nada
    released2 = await service.release_lock(key)
    assert released2 is False


@pytest.mark.asyncio
async def test_extend_lock_respects_max_extensions():
    redis = FakeRedis()
    service = LockService(cast(aioredis.Redis, redis))

    key = await service.acquire_lock(
        room_id="303",
        check_in="2026-01-10",
        check_out="2026-01-12",
        session_id="sess2",
        user_id="user2",
        ttl=5,
    )
    assert key is not None

    # Dos extensiones deberían funcionar
    assert await service.extend_lock(key) is True
    assert await service.extend_lock(key) is True
    # La tercera debe fallar por max_extensions alcanzado (default=2)
    assert await service.extend_lock(key) is False


@pytest.mark.asyncio
async def test_get_active_locks_lists_all():
    redis = FakeRedis()
    service = LockService(cast(aioredis.Redis, redis))

    k1 = await service.acquire_lock("401", "2026-02-01", "2026-02-02", "s1", "u1", ttl=10)
    k2 = await service.acquire_lock("402", "2026-02-03", "2026-02-04", "s2", "u2", ttl=10)
    assert k1 and k2

    active = await service.get_active_locks()
    # Debe contener 2 locks activos
    assert isinstance(active, list)
    assert len(active) == 2

    # Liberar uno y comprobar que la lista se actualiza
    await service.release_lock(k1)
    active2 = await service.get_active_locks()
    assert len(active2) == 1

