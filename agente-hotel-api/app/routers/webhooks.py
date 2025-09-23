# [PROMPT GA-02] app/routers/webhooks.py

import hmac
import hashlib
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Query
from fastapi.responses import PlainTextResponse
from typing import Any, cast
import json
import redis.asyncio as redis

from ..core.settings import settings
from ..core.redis_client import get_redis
from ..core.ratelimit import limit
from ..services.orchestrator import Orchestrator
from ..services.pms_adapter import get_pms_adapter
from ..services.session_manager import SessionManager
from ..services.lock_service import LockService
from ..services.message_gateway import MessageGateway

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def get_body(request: Request):
    return await request.body()


def verify_webhook_signature(
    signature: str = Header(None, alias="X-Hub-Signature-256"), body: bytes = Depends(get_body)
):
    """Verifica firma de webhooks de WhatsApp con App Secret."""
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature")

    app_secret = settings.whatsapp_app_secret.get_secret_value()
    expected_signature = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(signature.replace("sha256=", ""), expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    return True


@router.get("/whatsapp")
@limit("60/minute")
async def verify_whatsapp_webhook(request: Request, mode: str = Query(None, alias="hub.mode"), token: str = Query(None, alias="hub.verify_token"), challenge: str = Query(None, alias="hub.challenge")):
    """Handshake de verificación de WhatsApp (GET)."""
    if mode == "subscribe" and token == settings.whatsapp_verify_token.get_secret_value():
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/whatsapp", dependencies=[Depends(verify_webhook_signature)])
@limit("120/minute")
async def handle_whatsapp_webhook(request: Request):
    # Validaciones básicas de cabeceras/payload
    ctype = request.headers.get("content-type", "").lower()
    if ctype and "application/json" not in ctype:
        raise HTTPException(status_code=415, detail="Unsupported Media Type")

    # Limitar tamaño de payload a 1MB
    body_bytes = await request.body()
    if len(body_bytes) > 1_000_000:
        raise HTTPException(status_code=413, detail="Payload too large")

    # Procesa el webhook: normaliza el payload, invoca Orchestrator y devuelve respuesta.
    try:
        payload = json.loads(body_bytes.decode() or "{}")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Fallback Redis en memoria para pruebas/local si no hay servidor
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

        async def ping(self):
            return True

    redis_client = await get_redis()
    try:
        await redis_client.ping()  # type: ignore[attr-defined]
    except Exception:
        redis_client = _InMemoryRedis()  # type: ignore[assignment]

    # Asegurar tipado para servicios que esperan redis.Redis
    redis_typed: redis.Redis = cast(redis.Redis, redis_client)
    orchestrator = Orchestrator(
        pms_adapter=get_pms_adapter(redis_typed),
        session_manager=SessionManager(redis_typed),
        lock_service=LockService(redis_typed),
    )
    gateway = MessageGateway()

    try:
        unified = gateway.normalize_whatsapp_message(payload)
    except ValueError:
        # Payload sin mensajes; acuse de recibo sin procesar
        return {"status": "ok"}

    result = await orchestrator.handle_unified_message(unified)
    return result
