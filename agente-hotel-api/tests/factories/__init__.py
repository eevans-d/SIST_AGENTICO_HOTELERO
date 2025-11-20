from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone, date
from typing import Any, Dict, Optional

from app.models.unified_message import UnifiedMessage


def unified_message(
    *,
    user_id: str = "u-1",
    canal: str = "whatsapp",
    tipo: str = "text",
    texto: Optional[str] = "hola",
    message_id: str = "m-1",
    media_url: Optional[str] = None,
    tenant_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> UnifiedMessage:
    """Factory para crear UnifiedMessage consistente para tests.

    Args:
        user_id: Id del usuario
        canal: Canal (whatsapp, gmail)
        tipo: Tipo de mensaje (text, audio, image, interactive)
        texto: Contenido textual
        message_id: Id del mensaje
        media_url: URL de media si aplica
        tenant_id: Tenant opcional
        metadata: Metadatos adicionales

    Returns:
        UnifiedMessage preparado para tests
    """
    msg = UnifiedMessage(
        message_id=message_id,
        canal=canal,
        user_id=user_id,
        timestamp_iso=datetime.now(timezone.utc).isoformat(),
        tipo=tipo,
        texto=texto,
        media_url=media_url,
        metadata=metadata or {},
        tenant_id=tenant_id,
    )
    return msg


def iso_day(offset_days: int = 0) -> str:
    """Devuelve una fecha ISO (YYYY-MM-DD) desplazada desde hoy en UTC."""
    d = datetime.now(timezone.utc).date() + timedelta(days=offset_days)
    return d.isoformat()


def as_date(val: str | date) -> date:
    """Convierte a date si es string ISO."""
    if isinstance(val, date):
        return val
    return datetime.fromisoformat(val).date()


def tenant_meta(
    *, start: int = 9, end: int = 18, timezone_str: Optional[str] = None
) -> Dict[str, Any]:
    """Estructura de metadatos de tenant usada por dynamic_tenant_service."""
    return {
        "business_hours_start": start,
        "business_hours_end": end,
        "business_hours_timezone": timezone_str,
    }


def pms_late_checkout_available(*, fee: int = 0, requested_time: str = "14:00") -> Dict[str, Any]:
    return {"available": True, "fee": fee, "requested_time": requested_time}


def pms_late_checkout_unavailable(*, standard_time: str = "12:00") -> Dict[str, Any]:
    return {"available": False, "standard_time": standard_time}

