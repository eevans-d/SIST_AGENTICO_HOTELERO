# [PROMPT 2.3] app/services/lock_service.py

import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Any

import redis.asyncio as redis

from ..core.logging import logger


class LockService:
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        # Fallback a Redis en memoria si no se provee cliente (útil para tests)
        if redis_client is None:
            class _InMemoryRedis:
                def __init__(self):
                    self._store: dict[str, Any] = {}

                async def get(self, key: str):
                    return self._store.get(key)

                async def set(self, key: str, value: Any, ex: int | None = None, nx: bool | None = None):
                    if nx and key in self._store:
                        return False
                    self._store[key] = value
                    return True

                async def delete(self, key: str):
                    return 1 if self._store.pop(key, None) is not None else 0

                async def ttl(self, key: str):
                    return 600

                async def scan_iter(self, match: str = "*"):
                    import fnmatch
                    for k in list(self._store.keys()):
                        if fnmatch.fnmatch(k, match):
                            yield k

            self.redis = _InMemoryRedis()  # type: ignore[assignment]
        else:
            self.redis = redis_client

    def _get_lock_key(self, room_id: str, check_in: str, check_out: str) -> str:
        return f"lock:room:{room_id}:{check_in}:{check_out}"

    async def acquire_lock(
        self, room_id: str, check_in: str, check_out: str, session_id: str, user_id: str, ttl: int = 1200
    ) -> Optional[str]:
        """Adquiere un lock si no hay conflictos. Retorna la key del lock o None."""
        if await self.check_conflicts(room_id, check_in, check_out):
            logger.warning(f"Conflicto de lock detectado para habitación {room_id}")
            return None

        lock_key = self._get_lock_key(room_id, check_in, check_out)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl)

        lock_data = {
            "session_id": session_id,
            "user_id": user_id,
            "check_in": check_in,
            "check_out": check_out,
            "room_id": room_id,
            "acquired_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "extensions": 0,
        }

        # NX=True solo crea la key si no existe
        if await self.redis.set(lock_key, json.dumps(lock_data), ex=ttl, nx=True):
            logger.info(f"Lock adquirido: {lock_key}")
            # Aquí se podría registrar en la tabla de auditoría
            return lock_key

        logger.warning(f"Fallo al adquirir lock (ya existe): {lock_key}")
        return None

    async def extend_lock(self, lock_key: str, extra_ttl: int = 600, max_extensions: int = 2) -> bool:
        """Extiende la expiración de un lock existente."""
        lock_data_str = await self.redis.get(lock_key)
        if not lock_data_str:
            return False

        lock_data = json.loads(lock_data_str)

        if lock_data["extensions"] >= max_extensions:
            logger.warning(f"Máximo de extensiones alcanzado para el lock: {lock_key}")
            return False

        lock_data["extensions"] += 1
        new_ttl = await self.redis.ttl(lock_key) + extra_ttl
        lock_data["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=new_ttl)).isoformat()

        if await self.redis.set(lock_key, json.dumps(lock_data), ex=new_ttl):
            logger.info(f"Lock extendido: {lock_key}")
            return True

        return False

    async def release_lock(self, lock_key: str) -> bool:
        """Libera un lock."""
        deleted_count = await self.redis.delete(lock_key)
        if deleted_count > 0:
            logger.info(f"Lock liberado: {lock_key}")
            return True
        return False

    async def check_conflicts(self, room_id: str, check_in: str, check_out: str) -> bool:
        """Verifica si el rango de fechas solicitado se solapa con locks existentes."""
        # Simplificación: Por ahora, solo chequea si existe un lock para la misma habitación.
        # Una implementación completa requeriría chequear solapamiento de fechas.
        pattern = f"lock:room:{room_id}:*"
        async for key in self.redis.scan_iter(pattern):
            # Aquí iría la lógica de comparación de rangos de fechas
            return True  # Asumimos conflicto si hay cualquier lock para la habitación
        return False

    async def get_active_locks(self) -> List[dict]:
        """Obtiene todos los locks activos."""
        locks = []
        async for key in self.redis.scan_iter("lock:room:*"):
            lock_data_str = await self.redis.get(key)
            if lock_data_str:
                locks.append(json.loads(lock_data_str))
        return locks
