# [PROMPT 2.7] app/services/session_manager.py

import json
import redis.asyncio as redis


class SessionManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.ttl = 1800  # 30 minutos

    def _get_session_key(self, user_id: str, tenant_id: str | None = None) -> str:
        if tenant_id:
            return f"session:{tenant_id}:{user_id}"
        return f"session:{user_id}"

    async def get_or_create_session(self, user_id: str, canal: str, tenant_id: str | None = None) -> dict:
        session_key = self._get_session_key(user_id, tenant_id)
        session_data_str = await self.redis.get(session_key)
        if session_data_str:
            return json.loads(session_data_str)

        new_session = {
            "user_id": user_id,
            "canal": canal,
            "state": "initial",
            "context": {},
            "tts_enabled": False,
        }
        if tenant_id:
            new_session["tenant_id"] = tenant_id
        await self.redis.set(session_key, json.dumps(new_session), ex=self.ttl)
        return new_session

    async def update_session(self, user_id: str, session_data: dict, tenant_id: str | None = None):
        session_key = self._get_session_key(user_id, tenant_id)
        await self.redis.set(session_key, json.dumps(session_data), ex=self.ttl)
