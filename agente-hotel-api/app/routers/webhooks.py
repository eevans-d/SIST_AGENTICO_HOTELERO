# [PROMPT GA-02] app/routers/webhooks.py

import hmac
import hashlib
from fastapi import APIRouter, Depends, Header, HTTPException, Request

from ..core.settings import settings

router = APIRouter(tags=["Webhooks"])


async def get_body(request: Request):
    return await request.body()


def verify_webhook_signature(
    signature: str = Header(None, alias="X-Hub-Signature-256"), body: bytes = Depends(get_body)
):
    """Verifica firma de webhooks de WhatsApp"""
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature")

    expected_signature = hmac.new(
        settings.whatsapp_verify_token.get_secret_value().encode(), body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature.replace("sha256=", ""), expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    return True


@router.post("/whatsapp", dependencies=[Depends(verify_webhook_signature)])
async def handle_whatsapp_webhook(request: Request):
    # Lógica para procesar el webhook de WhatsApp
    return {"status": "ok"}
