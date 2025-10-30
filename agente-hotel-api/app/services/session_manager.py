# [PROMPT 2.7] app/services/session_manager.py

import json
import asyncio
from datetime import datetime, UTC
from typing import Optional, Any
import redis.asyncio as redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError
from prometheus_client import Gauge, Counter
from ..core.logging import logger
from ..core.constants import (
    MAX_RETRIES_DEFAULT,
    RETRY_DELAY_BASE,
    SESSION_TTL_DEFAULT,
    SESSION_CLEANUP_INTERVAL,
)

# Métricas para monitoreo de sesiones
active_sessions = Gauge("session_active_total", "Número de sesiones activas")
session_cleanups = Counter("session_cleanup_total", "Limpiezas de sesiones ejecutadas", ["result"])
session_expirations = Counter("session_expirations_total", "Sesiones expiradas", ["reason"])
session_save_retries = Counter(
    "session_save_retries_total", "Reintentos de guardado de sesión", ["operation", "result"]
)


class SessionManager:
    """
    Gestor de sesiones de usuario con persistencia en Redis.

    Maneja el ciclo de vida completo de las sesiones de conversación, incluyendo:
    - Creación y recuperación de sesiones
    - Actualización con retry automático y exponential backoff
    - Limpieza periódica de sesiones huérfanas/corruptas
    - Métricas de Prometheus para observabilidad
    - Soporte multi-tenant

    Características de robustez:
    ----------------------
    - **Retry con exponential backoff**: Reintentos automáticos en operaciones Redis
      (1s, 2s, 4s delays para MAX_RETRIES_DEFAULT=3)
    - **Manejo específico de errores Redis**: ConnectionError, TimeoutError, RedisError
    - **Logging estructurado**: Contexto completo en todos los puntos de fallo
    - **Métricas de retry**: Contadores para monitoreo de reintentos y fallos
    - **Cleanup automático**: Tarea en background para limpiar sesiones corruptas

    Ejemplo de uso:
    --------------
    ```python
    session_manager = SessionManager(redis_client)
    session_manager.start_cleanup_task()

    # Obtener o crear sesión
    session = await session_manager.get_or_create_session(
        user_id="user123",
        canal="whatsapp",
        tenant_id="hotel_abc"
    )

    # Actualizar sesión (con retry automático)
    session["context"]["last_intent"] = "check_availability"
    await session_manager.update_session("user123", session, tenant_id="hotel_abc")
    ```

    Atributos:
    ---------
    redis : redis.Redis
        Cliente Redis async para persistencia de sesiones.
    ttl : int
        Time-to-live de sesiones en segundos (default: SESSION_TTL_DEFAULT=1800s).
    max_retries : int
        Número máximo de reintentos en operaciones Redis (default: MAX_RETRIES_DEFAULT=3).
    retry_delay_base : int
        Delay base para exponential backoff en segundos (default: RETRY_DELAY_BASE=1).
    """

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        ttl: int = SESSION_TTL_DEFAULT,
        max_retries: int = MAX_RETRIES_DEFAULT,
        retry_delay_base: int = RETRY_DELAY_BASE,
    ):
        """
        Inicializa el gestor de sesiones.

        Args:
            redis_client: Cliente Redis async configurado.
            ttl: Time-to-live de sesiones en segundos (default: 1800).
            max_retries: Número máximo de reintentos (default: 3).
            retry_delay_base: Delay base para backoff exponencial (default: 1).
        """
        # Fallback a un Redis en memoria si no se provee cliente (útil para tests)
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

                async def setex(self, key: str, ttl: int, value: Any):
                    self._store[key] = value
                    return True

                async def delete(self, key: str):
                    return 1 if self._store.pop(key, None) is not None else 0

                async def ttl(self, key: str):
                    # No expiración real en memoria; devolver un TTL fijo
                    return 600

                async def scan(self, cursor: int = 0, match: str = "*", count: int = 100):
                    import fnmatch
                    keys = [k for k in self._store.keys() if fnmatch.fnmatch(k, match)]
                    # Sin paginación real; devolver todo y cursor 0
                    return 0, keys[:count]

                async def scan_iter(self, match: str = "*"):
                    import fnmatch
                    for k in list(self._store.keys()):
                        if fnmatch.fnmatch(k, match):
                            yield k

                async def ping(self):
                    return True

            self.redis = _InMemoryRedis()  # type: ignore[assignment]
        else:
            self.redis = redis_client
        self.ttl = ttl
        self.max_retries = max_retries
        self.retry_delay_base = retry_delay_base
        self._cleanup_task = None
        self._cleanup_interval = SESSION_CLEANUP_INTERVAL  # 600s (10 min)

    def _get_session_key(self, user_id: str, tenant_id: Optional[str] = None) -> str:
        """
        Genera la clave Redis para una sesión.

        Args:
            user_id: Identificador del usuario.
            tenant_id: Identificador del tenant (opcional para multi-tenancy).

        Returns:
            Clave Redis en formato "session:{tenant_id}:{user_id}" o "session:{user_id}".
        """
        if tenant_id:
            return f"session:{tenant_id}:{user_id}"
        return f"session:{user_id}"

    async def _save_session_with_retry(self, session_key: str, session_data: dict, operation: str = "save") -> bool:
        """
        Guarda sesión en Redis con retry automático y exponential backoff.

        Esta operación crítica puede fallar por:
        - Problemas de red con Redis (ConnectionError)
        - Timeouts de Redis (TimeoutError)
        - Redis sobrecargado (RedisError genérico)

        El retry con exponential backoff mejora la resiliencia ante fallos transitorios.

        Args:
            session_key: Clave Redis donde guardar la sesión.
            session_data: Datos de sesión a serializar y guardar.
            operation: Nombre de operación para logging ("save", "create", "update").

        Returns:
            True si guardó exitosamente, False si todos los reintentos fallaron.

        Raises:
            RedisError: Si todos los reintentos fallan, re-lanza la última excepción.
        """
        for attempt in range(self.max_retries):
            try:
                # Intentar guardar en Redis con TTL
                await self.redis.set(session_key, json.dumps(session_data), ex=self.ttl)

                # Log de éxito solo si fue retry (attempt > 0)
                if attempt > 0:
                    logger.info(
                        f"session_manager.{operation}_retry_success",
                        session_key=session_key,
                        attempt=attempt + 1,
                        operation=operation,
                    )
                    session_save_retries.labels(operation=operation, result="success").inc()

                return True

            except (RedisConnectionError, RedisTimeoutError) as e:
                # Errores de conexión/timeout son candidatos para retry
                is_last_attempt = attempt == self.max_retries - 1

                if is_last_attempt:
                    # Último intento falló - log error y re-lanzar
                    logger.error(
                        f"session_manager.{operation}_all_retries_failed",
                        session_key=session_key,
                        error=str(e),
                        error_type=type(e).__name__,
                        total_attempts=self.max_retries,
                        operation=operation,
                        exc_info=True,
                    )
                    session_save_retries.labels(operation=operation, result="failed").inc()
                    raise
                else:
                    # Calcular delay con exponential backoff: 1s, 2s, 4s, ...
                    delay = self.retry_delay_base * (2**attempt)

                    logger.warning(
                        f"session_manager.{operation}_retry",
                        session_key=session_key,
                        error=str(e),
                        error_type=type(e).__name__,
                        attempt=attempt + 1,
                        max_attempts=self.max_retries,
                        retry_delay=delay,
                        operation=operation,
                    )
                    session_save_retries.labels(operation=operation, result="retry").inc()

                    # Esperar antes del siguiente intento
                    await asyncio.sleep(delay)

            except RedisError as e:
                # Otros errores Redis (menos comunes, posiblemente no transitorios)
                logger.error(
                    f"session_manager.{operation}_redis_error",
                    session_key=session_key,
                    error=str(e),
                    error_type=type(e).__name__,
                    attempt=attempt + 1,
                    operation=operation,
                    exc_info=True,
                )
                session_save_retries.labels(operation=operation, result="failed").inc()
                raise

            except Exception as e:
                # Errores inesperados (ej: JSON serialization)
                logger.error(
                    f"session_manager.{operation}_unexpected_error",
                    session_key=session_key,
                    error=str(e),
                    error_type=type(e).__name__,
                    attempt=attempt + 1,
                    operation=operation,
                    exc_info=True,
                )
                session_save_retries.labels(operation=operation, result="failed").inc()
                raise

        return False

    async def get_or_create_session(self, user_id: str, canal: str, tenant_id: Optional[str] = None) -> dict:
        """
        Obtiene una sesión existente o crea una nueva si no existe.

        La creación de sesiones incluye retry automático para manejar fallos
        transitorios de Redis (conexión, timeout).

        Args:
            user_id: Identificador único del usuario.
            canal: Canal de comunicación ("whatsapp", "gmail", etc.).
            tenant_id: Identificador del tenant para multi-tenancy (opcional).

        Returns:
            Dict con datos de sesión (user_id, canal, state, context, etc.).

        Raises:
            RedisError: Si falla la obtención Y la creación de sesión.

        Ejemplo:
        -------
        ```python
        session = await session_manager.get_or_create_session(
            user_id="user123",
            canal="whatsapp",
            tenant_id="hotel_abc"
        )
        # session = {
        #     "user_id": "user123",
        #     "canal": "whatsapp",
        #     "state": "initial",
        #     "context": {},
        #     "tts_enabled": False,
        #     "tenant_id": "hotel_abc",
        #     "created_at": "2024-01-15T10:30:00",
        #     "last_activity": "2024-01-15T10:30:00"
        # }
        ```
        """
        session_key = self._get_session_key(user_id, tenant_id)

        try:
            # Intentar obtener sesión existente
            session_data_str = await self.redis.get(session_key)

            if session_data_str:
                session = json.loads(session_data_str)
                # Actualizar métrica de sesiones activas
                await self._update_active_sessions_metric()
                return session

        except RedisError as e:
            # Error al obtener sesión - log pero intentar crear nueva
            logger.warning(
                "session_manager.get_failed_will_create",
                session_key=session_key,
                error=str(e),
                error_type=type(e).__name__,
            )

        # No existe sesión - crear nueva
        new_session = {
            "user_id": user_id,
            "canal": canal,
            "state": "initial",
            "context": {},
            "tts_enabled": False,
            "created_at": datetime.now(UTC).isoformat(),
            "last_activity": datetime.now(UTC).isoformat(),
        }

        if tenant_id:
            new_session["tenant_id"] = tenant_id

        # Guardar con retry automático
        await self._save_session_with_retry(session_key, new_session, operation="create")
        await self._update_active_sessions_metric()

        return new_session

    async def update_session(self, user_id: str, session_data: dict, tenant_id: Optional[str] = None):
        """
        Actualiza una sesión existente con retry automático.

        Actualiza automáticamente el timestamp de última actividad y guarda
        en Redis con exponential backoff en caso de fallos transitorios.

        Args:
            user_id: Identificador del usuario.
            session_data: Datos de sesión actualizados a persistir.
            tenant_id: Identificador del tenant (opcional).

        Raises:
            RedisError: Si todos los reintentos fallan.

        Ejemplo:
        -------
        ```python
        # Obtener sesión
        session = await session_manager.get_or_create_session("user123", "whatsapp")

        # Modificar contexto
        session["context"]["last_intent"] = "check_availability"
        session["context"]["check_in"] = "2024-02-01"

        # Guardar con retry automático
        await session_manager.update_session("user123", session)
        ```
        """
        session_key = self._get_session_key(user_id, tenant_id)

        # Actualizar timestamp de última actividad
        session_data["last_activity"] = datetime.now(UTC).isoformat()

        # Guardar con retry automático
        await self._save_session_with_retry(session_key, session_data, operation="update")

    async def _update_active_sessions_metric(self):
        """Actualiza la métrica de sesiones activas."""
        try:
            # Contar todas las sesiones activas usando SCAN
            count = 0
            cursor = "0"
            while True:
                cursor, keys = await self.redis.scan(cursor=int(cursor), match="session:*", count=100)
                count += len(keys)
                if cursor == 0 or cursor == "0":
                    break
            active_sessions.set(count)
        except Exception as e:
            logger.warning(f"Failed to update active sessions metric: {e}")

    async def cleanup_expired_sessions(self):
        """
        Background task para limpiar sesiones expiradas y actualizar métricas.
        Redis maneja TTL automáticamente, pero esta tarea asegura limpieza adicional.
        """
        logger.info("🧹 Starting session cleanup background task")
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                logger.debug("Running session cleanup...")

                # Actualizar métrica de sesiones activas
                await self._update_active_sessions_metric()

                # Limpiar sesiones huérfanas o corruptas
                cleaned = await self._cleanup_orphaned_sessions()

                session_cleanups.labels(result="success").inc()
                logger.info(f"✅ Session cleanup completed. Cleaned {cleaned} orphaned sessions.")

            except asyncio.CancelledError:
                logger.info("Session cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
                session_cleanups.labels(result="error").inc()

    async def _cleanup_orphaned_sessions(self) -> int:
        """Limpia sesiones corruptas o mal formadas."""
        cleaned = 0
        try:
            cursor = "0"
            while True:
                cursor, keys = await self.redis.scan(cursor=int(cursor), match="session:*", count=100)

                for key in keys:
                    try:
                        data = await self.redis.get(key)
                        if not data:
                            continue

                        # Validar que sea JSON válido
                        session = json.loads(data)

                        # Validar campos requeridos
                        if not all(k in session for k in ["user_id", "canal", "state"]):
                            logger.warning(f"Orphaned session found: {key}")
                            await self.redis.delete(key)
                            session_expirations.labels(reason="invalid_format").inc()
                            cleaned += 1

                    except (json.JSONDecodeError, Exception) as e:
                        logger.warning(f"Corrupted session {key}: {e}")
                        await self.redis.delete(key)
                        session_expirations.labels(reason="corrupted").inc()
                        cleaned += 1

                if cursor == 0 or cursor == "0":
                    break

        except Exception as e:
            logger.error(f"Error cleaning orphaned sessions: {e}")

        return cleaned

    def start_cleanup_task(self):
        """Inicia la tarea de limpieza en background."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self.cleanup_expired_sessions())
            logger.info("✅ Session cleanup task started")

    async def stop_cleanup_task(self):
        """Detiene la tarea de limpieza."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Session cleanup task stopped")
