# [PROMPT GA-02 + E.1] app/routers/webhooks.py

import hmac
import hashlib
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Query
from prometheus_client import Counter
from fastapi.responses import PlainTextResponse
from typing import Any, cast
import json
import redis.asyncio as redis
import structlog

from ..core.settings import settings
from ..core.redis_client import get_redis
from ..core.ratelimit import limit
from ..services.orchestrator import Orchestrator
from ..services.pms_adapter import get_pms_adapter
from ..services.session_manager import SessionManager
from ..services.lock_service import LockService
from ..services.message_gateway import MessageGateway

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
logger = structlog.get_logger(__name__)

# Métrica: consolidación de texto+imagen en un solo mensaje (imagen con caption)
whatsapp_text_image_consolidated_total = Counter(
    "whatsapp_text_image_consolidated_total",
    "Total de envíos text_with_image consolidados en un solo mensaje (imagen con caption)"
)


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
async def verify_whatsapp_webhook(
    request: Request,
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
):
    """Handshake de verificación de WhatsApp (GET)."""
    if mode == "subscribe" and token == settings.whatsapp_verify_token.get_secret_value():
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/whatsapp", dependencies=[Depends(verify_webhook_signature)])
@limit("120/minute")
async def handle_whatsapp_webhook(request: Request):
    """
    WhatsApp Business API webhook handler.

    Processes incoming messages from WhatsApp Cloud API v18.0:
    - Text messages
    - Audio messages (for STT processing)
    - Media messages (images, videos, documents)
    - Interactive messages (buttons, lists)
    - Location messages
    - Reaction messages
    - Button replies
    - Template status updates

    Security:
    - Signature verification (HMAC-SHA256)
    - Rate limiting (120 req/min)
    - Payload size limit (1MB)

    Flow:
    1. Validate content-type and payload size
    2. Parse JSON payload
    3. Normalize to UnifiedMessage
    4. Process via Orchestrator
    5. Return response based on message type
    """
    # Validaciones básicas de cabeceras/payload
    ctype = request.headers.get("content-type", "").lower()
    if ctype and "application/json" not in ctype:
        logger.warning("whatsapp.webhook.unsupported_media_type", content_type=ctype)
        raise HTTPException(status_code=415, detail="Unsupported Media Type")

    # Limitar tamaño de payload a 1MB (ya manejado por middleware, pero doble check)
    body_bytes = await request.body()
    if len(body_bytes) > 1_000_000:
        logger.warning("whatsapp.webhook.payload_too_large", size=len(body_bytes))
        raise HTTPException(status_code=413, detail="Payload too large")

    # Procesa el webhook: normaliza el payload, invoca Orchestrator y devuelve respuesta.
    try:
        payload = json.loads(body_bytes.decode() or "{}")
        logger.info(
            "whatsapp.webhook.received", payload_keys=list(payload.keys()), entry_count=len(payload.get("entry", []))
        )
    except Exception as e:
        logger.error("whatsapp.webhook.invalid_json", error=str(e))
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
        # BLOQUEANTE 3: Pass request_source to prevent channel spoofing
        unified = gateway.normalize_whatsapp_message(
            payload,
            request_source="webhook_whatsapp"
        )
    except (ValueError, Exception):
        # Payload sin mensajes o error de normalización; acuse de recibo sin procesar
        return {"status": "ok"}

    # Procesar el mensaje con el orquestador
    result = await orchestrator.handle_unified_message(unified)

    # Obtener cliente de WhatsApp para enviar respuestas
    from ..services.whatsapp_client import WhatsAppMetaClient

    whatsapp_client = WhatsAppMetaClient()

    try:
        # Comprobar el tipo de respuesta para determinar qué método usar
        if "response_type" in result:
            response_type = result.get("response_type")
            content = result.get("content", {})
            original_message = result.get("original_message")

            if response_type == "interactive_buttons" and original_message:
                # Enviar mensaje interactivo con botones
                await whatsapp_client.send_interactive_message(
                    to=original_message.user_id,
                    header_text=content.get("header_text"),
                    body_text=content.get("body_text", ""),
                    footer_text=content.get("footer_text"),
                    action_buttons=content.get("action_buttons"),
                )

            elif response_type == "interactive_list" and original_message:
                # Enviar mensaje interactivo con lista
                await whatsapp_client.send_interactive_message(
                    to=original_message.user_id,
                    header_text=content.get("header_text"),
                    body_text=content.get("body_text", ""),
                    footer_text=content.get("footer_text"),
                    list_sections=content.get("list_sections"),
                    list_button_text=content.get("list_button_text"),
                )

            elif response_type == "location" and original_message:
                # Enviar mensaje de ubicación usando el nuevo método send_location
                content = result.get("content", {})
                await whatsapp_client.send_location(
                    to=original_message.user_id,
                    latitude=content.get("latitude", 0),
                    longitude=content.get("longitude", 0),
                    name=content.get("name"),
                    address=content.get("address"),
                )

            elif response_type == "audio_with_location" and original_message:
                # Enviar primero el mensaje de audio
                if content.get("audio_data"):
                    # Enviar el mensaje de audio
                    await whatsapp_client.send_audio_message(
                        to=original_message.user_id, audio_data=content.get("audio_data")
                    )

                    # Si hay texto, enviarlo como mensaje separado
                    if text := content.get("text"):
                        await whatsapp_client.send_message(to=original_message.user_id, text=text)

                # Luego enviar la ubicación usando el nuevo método send_location
                location = content.get("location", {})
                if location:
                    await whatsapp_client.send_location(
                        to=original_message.user_id,
                        latitude=location.get("latitude", 0),
                        longitude=location.get("longitude", 0),
                        name=location.get("name"),
                        address=location.get("address"),
                    )

            elif response_type == "audio" and original_message:
                # Enviar mensaje de audio
                # Verificar si content es un diccionario o directamente el texto
                if isinstance(content, dict):
                    audio_data = content.get("audio_data")
                    text = content.get("text", "")
                else:
                    # El contenido es el texto y audio_data debería estar en un campo separado
                    audio_data = result.get("audio_data")
                    text = content

                if audio_data:
                    await whatsapp_client.send_audio_message(to=original_message.user_id, audio_data=audio_data)

                # Si hay texto, enviarlo como mensaje separado
                if text:
                    await whatsapp_client.send_message(to=original_message.user_id, text=text)

                # Manejar mensaje de seguimiento si existe
                if follow_up := content.get("follow_up"):
                    follow_up_type = follow_up.get("type")
                    follow_up_content = follow_up.get("content", {})

                    # Enviamos el mensaje de seguimiento según su tipo
                    if follow_up_type == "interactive_list":
                        await whatsapp_client.send_interactive_message(
                            to=original_message.user_id,
                            header_text=follow_up_content.get("header_text"),
                            body_text=follow_up_content.get("body_text", ""),
                            footer_text=follow_up_content.get("footer_text"),
                            list_sections=follow_up_content.get("list_sections"),
                            list_button_text=follow_up_content.get("list_button_text"),
                        )

            elif response_type == "text" and original_message:
                # Enviar texto simple
                if isinstance(content, dict):
                    text = content.get("text", "")
                else:
                    text = content or ""
                await whatsapp_client.send_message(to=original_message.user_id, text=text)

            # Feature 3: Manejo de response types con imágenes
            elif response_type == "text_with_image" and original_message:
                # Consolidación opcional: enviar solo una imagen con caption que incluya el texto
                from ..services.feature_flag_service import DEFAULT_FLAGS
                image_url = result.get("image_url")
                text = result.get("content", "")
                caption = result.get("image_caption", "")

                if image_url and DEFAULT_FLAGS.get("humanize.consolidate_text.enabled", False):
                    combo_caption = text.strip()
                    if caption:
                        combo_caption = f"{combo_caption}\n\n{caption}" if combo_caption else caption
                    await whatsapp_client.send_image(
                        to=original_message.user_id, image_url=image_url, caption=combo_caption
                    )
                    try:
                        whatsapp_text_image_consolidated_total.inc()
                    except Exception:
                        # No romper el flujo si Prometheus no está disponible
                        pass
                else:
                    # Comportamiento por defecto
                    if text:
                        await whatsapp_client.send_message(to=original_message.user_id, text=text)
                    if image_url:
                        await whatsapp_client.send_image(
                            to=original_message.user_id, image_url=image_url, caption=caption
                        )

            elif response_type == "audio_with_image" and original_message:
                # Enviar audio primero
                audio_data = result.get("audio_data")
                if audio_data:
                    await whatsapp_client.send_audio_message(to=original_message.user_id, audio_data=audio_data)

                # Enviar texto si existe
                text = result.get("content", "")
                if text:
                    await whatsapp_client.send_message(to=original_message.user_id, text=text)

                # Enviar imagen si existe
                image_url = result.get("image_url")
                if image_url:
                    caption = result.get("image_caption", "")
                    await whatsapp_client.send_image(to=original_message.user_id, image_url=image_url, caption=caption)

            elif response_type == "interactive_buttons_with_image" and original_message:
                # Enviar imagen primero
                image_url = result.get("image_url")
                if image_url:
                    caption = result.get("image_caption", "")
                    await whatsapp_client.send_image(to=original_message.user_id, image_url=image_url, caption=caption)

                # Luego enviar botones interactivos
                await whatsapp_client.send_interactive_message(
                    to=original_message.user_id,
                    header_text=content.get("header_text"),
                    body_text=content.get("body_text", ""),
                    footer_text=content.get("footer_text"),
                    action_buttons=content.get("action_buttons"),
                )

            elif response_type == "reaction" and original_message:
                # Enviar reacción a un mensaje
                await whatsapp_client.send_reaction(
                    to=original_message.user_id,
                    message_id=content.get("message_id", ""),
                    emoji=content.get("emoji", "👍"),
                )

            elif response_type == "image_with_text" and original_message:
                # FEATURE 5: Enviar imagen con texto (para QR codes de confirmación)
                image_path = result.get("image_path")
                image_caption = result.get("image_caption", "")
                text_content = result.get("content", "")

                if image_path:
                    # Enviar primero el texto
                    if text_content:
                        await whatsapp_client.send_message(to=original_message.user_id, text=text_content)

                    # Luego enviar la imagen con caption
                    try:
                        # Para archivos locales, necesitamos convertir a URL
                        # En producción esto sería una URL de S3 o CDN
                        from pathlib import Path

                        if Path(image_path).exists():
                            # Upload to temporary hosting or convert to base64
                            # Por ahora, enviamos solo el caption como texto
                            await whatsapp_client.send_message(
                                to=original_message.user_id,
                                text=f"📱 {image_caption}\n\n(QR code would be sent here in production)",
                            )
                        else:
                            # Imagen no encontrada, enviar fallback
                            await whatsapp_client.send_message(
                                to=original_message.user_id, text=f"⚠️ Error enviando QR code. {image_caption}"
                            )
                    except Exception as img_error:
                        logger.error("whatsapp.send_qr_image_error", error=str(img_error), image_path=image_path)
                        # Fallback: enviar solo el texto de confirmación
                        await whatsapp_client.send_message(
                            to=original_message.user_id,
                            text="✅ Tu reserva está confirmada. El QR code se enviará por email.",
                        )

        elif "response" in result and unified:
            # Respuesta de texto tradicional
            await whatsapp_client.send_message(to=unified.user_id, text=result.get("response", ""))

    except Exception as e:
        logger.error("whatsapp.webhook.send_response_error", error=str(e))
    finally:
        await whatsapp_client.close()

    # Siempre devolver OK al webhook para confirmar recepción
    # Además, si el orquestador devolvió una respuesta textual, incluirla para facilitar validación en tests/integraciones
    response_payload: dict[str, Any] = {"status": "ok"}
    try:
        if isinstance(result, dict):
            # Eco de respuesta textual (compat tests)
            if "response" in result and isinstance(result.get("response"), str):
                response_payload["response"] = result["response"]
            # Eco de respuestas interactivas/ubicación/audio para validación en tests/integraciones
            if "response_type" in result:
                response_payload["response_type"] = result.get("response_type")
                # Incluir contenido estructurado si existe
                if "content" in result:
                    response_payload["content"] = result.get("content")
                # Campos opcionales de imagen/audio
                for extra_key in ("image_url", "image_caption", "audio_data"):
                    if extra_key in result:
                        response_payload[extra_key] = result.get(extra_key)
    except Exception:
        pass
    return response_payload


@router.post("/gmail")
@limit("120/minute")
async def gmail_webhook(request: Request, body: bytes = Depends(get_body)):
    """
    Gmail webhook endpoint for push notifications.

    Gmail API can send push notifications when new emails arrive using Cloud Pub/Sub.
    This endpoint receives those notifications and polls for new messages.

    Alternative: For simpler setups, use scheduled polling instead of webhooks.

    Flow:
    1. Gmail sends push notification via Pub/Sub
    2. This endpoint receives notification
    3. Poll Gmail for new messages
    4. Normalize and process via orchestrator

    Docs: https://developers.google.com/gmail/api/guides/push
    """
    from ..services.gmail_client import GmailIMAPClient, GmailClientError

    # Parse Pub/Sub message (si viene de Cloud Pub/Sub)
    try:
        payload = json.loads(body)
        logger.info("gmail.webhook.received", extra={"payload_keys": list(payload.keys())})
    except json.JSONDecodeError:
        logger.warning("gmail.webhook.invalid_json")
        return {"status": "error", "message": "Invalid JSON"}

    # Configurar servicios (similar a WhatsApp webhook)
    class _InMemoryRedis:
        _store: dict[str, Any] = {}

        async def get(self, key: str):
            return self._store.get(key)

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

    redis_typed: redis.Redis = cast(redis.Redis, redis_client)
    orchestrator = Orchestrator(
        pms_adapter=get_pms_adapter(redis_typed),
        session_manager=SessionManager(redis_typed),
        lock_service=LockService(redis_typed),
    )
    gateway = MessageGateway()
    gmail_client = GmailIMAPClient()

    # Poll Gmail para nuevos mensajes
    try:
        messages = gmail_client.poll_new_messages(mark_read=True)

        if not messages:
            logger.info("gmail.webhook.no_messages")
            return {"status": "ok", "messages_processed": 0}

        logger.info("gmail.webhook.messages_found", extra={"count": len(messages)})

        # Procesar cada mensaje
        results = []
        for email_dict in messages:
            try:
                # Normalizar a UnifiedMessage
                # BLOQUEANTE 3: Pass request_source to prevent channel spoofing
                unified = gateway.normalize_gmail_message(
                    email_dict,
                    request_source="webhook_gmail"
                )

                # Procesar via orchestrator
                result = await orchestrator.handle_unified_message(unified)
                results.append(result)

                logger.info(
                    "gmail.message.processed", extra={"message_id": unified.message_id, "user_id": unified.user_id}
                )

            except Exception as e:
                logger.error(
                    "gmail.message.processing_error",
                    extra={"message_id": email_dict.get("message_id"), "error": str(e)},
                )
                continue

        return {"status": "ok", "messages_processed": len(results), "results": results}

    except GmailClientError as e:
        logger.error("gmail.webhook.client_error", extra={"error": str(e)})
        return {"status": "error", "message": str(e)}
    except Exception:
        logger.exception("gmail.webhook.unexpected_error")
        return {"status": "error", "message": "Internal server error"}
