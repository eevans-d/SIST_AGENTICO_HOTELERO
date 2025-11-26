# [PROMPT 2.3] app/services/lock_service.py

import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Any

import redis.asyncio as redis
from prometheus_client import Counter

from ..core.logging import logger
from ..core.database import AsyncSessionFactory
from ..models.lock_audit import LockAudit
from ..core.redis_client import get_redis_client
from ..core.tenant_context import get_tenant_id

# Métricas para lock service
lock_operations_total = Counter(
    "lock_operations_total",
    "Total de operaciones de lock ejecutadas",
    ["operation", "result"]
)
lock_conflicts_total = Counter(
    "lock_conflicts_total",
    "Total de conflictos de lock detectados",
    ["room_id"]
)
lock_extensions_total = Counter(
    "lock_extensions_total",
    "Total de extensiones de lock",
    ["result"]
)


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
        tenant_id = get_tenant_id()
        prefix = f"tenant:{tenant_id}:" if tenant_id else ""
        return f"{prefix}lock:room:{room_id}:{check_in}:{check_out}"

    async def acquire_lock(
        self, room_id: str, check_in: str, check_out: str, session_id: str, user_id: str, ttl: int = 1200
    ) -> Optional[str]:
        """Adquiere un lock si no hay conflictos. Retorna la key del lock o None."""
        if await self.check_conflicts(room_id, check_in, check_out):
            logger.warning(f"Conflicto de lock detectado para habitación {room_id}")
            lock_conflicts_total.labels(room_id=room_id).inc()
            lock_operations_total.labels(operation="acquire", result="conflict").inc()

            # Registrar evento de conflicto en audit trail
            await self._audit_lock_event(
                lock_key=f"lock:room:{room_id}:{check_in}:{check_out}",
                event_type="conflict",
                details={"session_id": session_id, "user_id": user_id, "reason": "date_overlap"}
            )
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
            lock_operations_total.labels(operation="acquire", result="success").inc()

            # Registrar en audit trail
            await self._audit_lock_event(
                lock_key=lock_key,
                event_type="acquired",
                details={
                    "session_id": session_id,
                    "user_id": user_id,
                    "room_id": room_id,
                    "check_in": check_in,
                    "check_out": check_out,
                    "ttl": ttl,
                }
            )
            return lock_key

        logger.warning(f"Fallo al adquirir lock (ya existe): {lock_key}")
        lock_operations_total.labels(operation="acquire", result="already_exists").inc()
        return None

    async def extend_lock(self, lock_key: str, extra_ttl: int = 600, max_extensions: int = 2) -> bool:
        """Extiende la expiración de un lock existente."""
        lock_data_str = await self.redis.get(lock_key)
        if not lock_data_str:
            lock_operations_total.labels(operation="extend", result="not_found").inc()
            return False

        lock_data = json.loads(lock_data_str)

        if lock_data["extensions"] >= max_extensions:
            logger.warning(f"Máximo de extensiones alcanzado para el lock: {lock_key}")
            lock_operations_total.labels(operation="extend", result="max_reached").inc()
            lock_extensions_total.labels(result="max_reached").inc()
            return False

        lock_data["extensions"] += 1
        new_ttl = await self.redis.ttl(lock_key) + extra_ttl
        lock_data["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=new_ttl)).isoformat()

        if await self.redis.set(lock_key, json.dumps(lock_data), ex=new_ttl):
            logger.info(f"Lock extendido: {lock_key}")
            lock_operations_total.labels(operation="extend", result="success").inc()
            lock_extensions_total.labels(result="success").inc()

            # Registrar extensión en audit trail
            await self._audit_lock_event(
                lock_key=lock_key,
                event_type="extended",
                details={
                    "extension_count": lock_data["extensions"],
                    "new_ttl": new_ttl,
                    "extra_ttl": extra_ttl,
                }
            )
            return True

        lock_operations_total.labels(operation="extend", result="set_failed").inc()
        lock_extensions_total.labels(result="failed").inc()
        return False

    async def release_lock(self, lock_key: str) -> bool:
        """Libera un lock."""
        # Obtener datos del lock antes de eliminar para audit trail
        lock_data_str = await self.redis.get(lock_key)

        deleted_count = await self.redis.delete(lock_key)
        if deleted_count > 0:
            logger.info(f"Lock liberado: {lock_key}")
            lock_operations_total.labels(operation="release", result="success").inc()

            # Registrar liberación en audit trail
            if lock_data_str:
                try:
                    lock_data = json.loads(lock_data_str)
                    await self._audit_lock_event(
                        lock_key=lock_key,
                        event_type="released",
                        details={
                            "session_id": lock_data.get("session_id"),
                            "user_id": lock_data.get("user_id"),
                            "extensions": lock_data.get("extensions", 0),
                        }
                    )
                except Exception as e:
                    logger.warning(f"Error auditing lock release: {e}")

            return True

        lock_operations_total.labels(operation="release", result="not_found").inc()
        return False

    async def check_conflicts(self, room_id: str, check_in: str, check_out: str) -> bool:
        """
        Verifica si el rango de fechas solicitado se solapa con locks existentes.

        PERFORMANCE FIX: Implementa comparación real de rangos de fechas para evitar
        falsos positivos que rechazan reservas válidas.

        Args:
            room_id: ID de la habitación
            check_in: Fecha de check-in (ISO 8601 format)
            check_out: Fecha de check-out (ISO 8601 format)

        Returns:
            True si existe solapamiento (conflicto), False si no hay conflicto
        """
        from datetime import datetime
        import json

        try:
            # Parse requested dates
            check_in_dt = datetime.fromisoformat(check_in.replace("Z", "+00:00"))
            check_out_dt = datetime.fromisoformat(check_out.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            logger.error(
                "lock_service.invalid_date_format",
                room_id=room_id,
                check_in=check_in,
                check_out=check_out,
                error=str(e)
            )
            # If dates are invalid, assume no conflict (fail open)
            return False

        # Scan all locks for this room (respecting tenant context)
        tenant_id = get_tenant_id()
        prefix = f"tenant:{tenant_id}:" if tenant_id else ""
        pattern = f"{prefix}lock:room:{room_id}:*"
        
        async for key in self.redis.scan_iter(pattern):
            lock_data_raw = await self.redis.get(key)
            if not lock_data_raw:
                continue

            try:
                lock_data = json.loads(lock_data_raw)
                existing_in_str = lock_data.get("check_in")
                existing_out_str = lock_data.get("check_out")

                if not existing_in_str or not existing_out_str:
                    logger.warning(
                        "lock_service.malformed_lock_data",
                        room_id=room_id,
                        lock_key=key
                    )
                    continue

                existing_in = datetime.fromisoformat(existing_in_str.replace("Z", "+00:00"))
                existing_out = datetime.fromisoformat(existing_out_str.replace("Z", "+00:00"))

                # Date range overlap check:
                # Two ranges overlap if NOT (new ends before existing starts OR new starts after existing ends)
                has_overlap = not (check_out_dt <= existing_in or check_in_dt >= existing_out)

                if has_overlap:
                    logger.info(
                        "lock_service.conflict_detected",
                        room_id=room_id,
                        requested_check_in=check_in,
                        requested_check_out=check_out,
                        existing_check_in=existing_in_str,
                        existing_check_out=existing_out_str,
                        lock_key=key
                    )
                    return True  # Conflict found

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.error(
                    "lock_service.error_parsing_lock",
                    room_id=room_id,
                    lock_key=key,
                    error=str(e)
                )
                continue

        # No conflicts found
        logger.debug(
            "lock_service.no_conflicts",
            room_id=room_id,
            check_in=check_in,
            check_out=check_out
        )
        return False

    async def get_active_locks(self) -> List[dict]:
        """Obtiene todos los locks activos."""
        locks = []
        async for key in self.redis.scan_iter("lock:room:*"):
            lock_data_str = await self.redis.get(key)
            if lock_data_str:
                locks.append(json.loads(lock_data_str))
        return locks

    async def release_all_locks(self):
        """Libera todos los locks (usar con precaución, solo admin/cleanup)."""
        async for key in self.redis.scan_iter("lock:room:*"):
            await self.redis.delete(key)
        logger.warning("Todos los locks han sido liberados manualmente")

    async def _audit_lock_event(self, lock_key: str, event_type: str, details: dict):
        """
        Registra un evento de lock en la tabla de auditoría.

        Args:
            lock_key: Clave del lock (ej: "lock:room:101:2025-01-01:2025-01-03")
            event_type: Tipo de evento - "acquired", "extended", "released", "conflict"
            details: Metadata adicional del evento (session_id, user_id, ttl, etc.)
        """
        try:
            async with AsyncSessionFactory() as session:
                audit_entry = LockAudit(
                    lock_key=lock_key,
                    event_type=event_type,
                    details=details,
                    tenant_id=get_tenant_id()
                )
                session.add(audit_entry)
                await session.commit()

                logger.debug(
                    "lock_service.audit_recorded",
                    lock_key=lock_key,
                    event_type=event_type
                )
        except Exception as e:
            logger.error(
                "lock_service.audit_failed",
                lock_key=lock_key,
                event_type=event_type,
                error=str(e),
                exc_info=True
            )
            # No re-lanzar - la auditoría no debería romper operaciones críticas


_lock_service_instance = None


async def get_lock_service() -> LockService:
    """Dependency provider for LockService singleton."""
    global _lock_service_instance
    if _lock_service_instance is None:
        redis_client = await get_redis_client()
        _lock_service_instance = LockService(redis_client)
    return _lock_service_instance

