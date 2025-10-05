# [PROMPT 2.7] app/services/session_manager.py

import json
import asyncio
from datetime import datetime
import redis.asyncio as redis
from prometheus_client import Gauge, Counter
from ..core.logging import logger

# Métricas para monitoreo de sesiones
active_sessions = Gauge("session_active_total", "Número de sesiones activas")
session_cleanups = Counter("session_cleanup_total", "Limpiezas de sesiones ejecutadas", ["result"])
session_expirations = Counter("session_expirations_total", "Sesiones expiradas", ["reason"])


class SessionManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.ttl = 1800  # 30 minutos
        self._cleanup_task = None
        self._cleanup_interval = 600  # Cleanup cada 10 minutos

    def _get_session_key(self, user_id: str, tenant_id: str | None = None) -> str:
        if tenant_id:
            return f"session:{tenant_id}:{user_id}"
        return f"session:{user_id}"

    async def get_or_create_session(self, user_id: str, canal: str, tenant_id: str | None = None) -> dict:
        session_key = self._get_session_key(user_id, tenant_id)
        session_data_str = await self.redis.get(session_key)
        if session_data_str:
            session = json.loads(session_data_str)
            # Actualizar métrica de sesiones activas
            await self._update_active_sessions_metric()
            return session

        new_session = {
            "user_id": user_id,
            "canal": canal,
            "state": "initial",
            "context": {},
            "tts_enabled": False,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
        }
        if tenant_id:
            new_session["tenant_id"] = tenant_id
        await self.redis.set(session_key, json.dumps(new_session), ex=self.ttl)
        await self._update_active_sessions_metric()
        return new_session

    async def update_session(self, user_id: str, session_data: dict, tenant_id: str | None = None):
        session_key = self._get_session_key(user_id, tenant_id)
        # Actualizar timestamp de última actividad
        session_data["last_activity"] = datetime.utcnow().isoformat()
        await self.redis.set(session_key, json.dumps(session_data), ex=self.ttl)
    
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
