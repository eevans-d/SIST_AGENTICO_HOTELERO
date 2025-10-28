# [PROMPT 2.8] app/routers/admin.py (FINAL)

from fastapi import APIRouter, Depends, Request
from fastapi import HTTPException
from ..services.dynamic_tenant_service import dynamic_tenant_service
from ..services.audio_processor import AudioProcessor
from ..models.tenant import Tenant, TenantUserIdentifier
from ..core.database import AsyncSessionFactory
from sqlalchemy import select
from ..core.security import get_current_user
from ..core.ratelimit import limit
from ..services.feature_flag_service import DEFAULT_FLAGS
from ..core.redis_client import get_redis
from ..services.feature_flag_service import get_feature_flag_service, DEFAULT_FLAGS

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(get_current_user)])


@router.get("/dashboard")
@limit("30/minute")
async def get_dashboard(request: Request):
    # Respuesta alineada con tests/test_auth.py
    return {"message": "Welcome to the admin dashboard"}


@router.get("/tenants")
@limit("60/minute")
async def list_tenants(request: Request):
    return {"tenants": dynamic_tenant_service.list_tenants()}


@router.get("/feature-flags")
@limit("60/minute")
async def get_feature_flags(request: Request):
    """Devuelve el estado efectivo de los feature flags.

    Origen: Redis hash `feature_flags` (1/true/on/yes → enabled), con fallback a DEFAULT_FLAGS.
    Respuesta: { "flags": { "flag_name": true|false, ... } }
    """
    try:
        r = await get_redis()
        raw = await r.hgetall("feature_flags")
    except Exception:
        raw = {}
    flags: dict[str, bool] = {}
    # Cargar defaults primero
    for k, v in DEFAULT_FLAGS.items():
        flags[k] = bool(v)
    # Sobrescribir con Redis cuando exista
    for k, v in raw.items():
        key = k.decode() if isinstance(k, (bytes, bytearray)) else str(k)
        val = v.decode() if isinstance(v, (bytes, bytearray)) else str(v)
        flags[key] = val.lower() in ("1", "true", "on", "yes")
    # Ordenar de forma estable por nombre
    ordered = {k: flags[k] for k in sorted(flags.keys())}
    return {"flags": ordered}


@router.get("/feature-flags")
@limit("60/minute")
async def list_feature_flags(request: Request):
    """Lista los feature flags conocidos con su estado actual.

    Origen de verdad: Redis hash `feature_flags` (override). Si no existe en Redis, se toma de DEFAULT_FLAGS.
    """
    ff = await get_feature_flag_service()
    # Leer overrides crudos de Redis para indicar fuente
    try:
        redis_overrides = await ff.redis.hgetall("feature_flags")
    except Exception:
        redis_overrides = {}

    flags = []
    all_keys = set(DEFAULT_FLAGS.keys()) | set(
        k.decode() if isinstance(k, (bytes, bytearray)) else str(k) for k in (redis_overrides or {}).keys()
    )
    for key in sorted(all_keys):
        enabled = await ff.is_enabled(key, default=DEFAULT_FLAGS.get(key, False))
        source = "redis" if redis_overrides and (
            (key.encode() in redis_overrides) or (key in redis_overrides)
        ) else "default"
        flags.append({"flag": key, "enabled": enabled, "source": source})

    return {"flags": flags}


@router.post("/tenants/refresh")
@limit("30/minute")
async def refresh_tenants(request: Request):
    try:
        await dynamic_tenant_service.refresh()
        return {"status": "refreshed"}
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tenants")
@limit("30/minute")
async def create_tenant(request: Request, body: dict):
    tenant_id = body.get("tenant_id")
    name = body.get("name")
    if not tenant_id or not name:
        raise HTTPException(status_code=400, detail="tenant_id y name requeridos")
    async with AsyncSessionFactory() as session:  # type: ignore
        exists = (await session.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))).scalar_one_or_none()
        if exists:
            raise HTTPException(status_code=409, detail="Tenant ya existe")
        t = Tenant(tenant_id=tenant_id, name=name)
        session.add(t)
        await session.commit()
    await dynamic_tenant_service.refresh()
    return {"status": "created", "tenant_id": tenant_id}


@router.post("/tenants/{tenant_id}/identifiers")
async def add_identifier(tenant_id: str, body: dict):
    identifier = body.get("identifier")
    if not identifier:
        raise HTTPException(status_code=400, detail="identifier requerido")
    async with AsyncSessionFactory() as session:  # type: ignore
        tenant = (await session.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant no encontrado")
        existing = (
            await session.execute(select(TenantUserIdentifier).where(TenantUserIdentifier.identifier == identifier))
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Identifier ya asignado")
        session.add(TenantUserIdentifier(tenant_id=tenant.id, identifier=identifier))
        await session.commit()
    await dynamic_tenant_service.refresh()
    return {"status": "identifier_added", "tenant_id": tenant_id, "identifier": identifier}


@router.delete("/tenants/{tenant_id}/identifiers/{identifier}")
async def remove_identifier(tenant_id: str, identifier: str):
    async with AsyncSessionFactory() as session:  # type: ignore
        tenant = (await session.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant no encontrado")
        rec = (
            await session.execute(
                select(TenantUserIdentifier).where(
                    TenantUserIdentifier.identifier == identifier,
                    TenantUserIdentifier.tenant_id == tenant.id,
                )
            )
        ).scalar_one_or_none()
        if not rec:
            raise HTTPException(status_code=404, detail="Identifier no encontrado")
        await session.delete(rec)
        await session.commit()
    await dynamic_tenant_service.refresh()
    return {"status": "identifier_removed", "tenant_id": tenant_id, "identifier": identifier}


@router.patch("/tenants/{tenant_id}")
async def update_tenant(tenant_id: str, body: dict):
    """
    Actualiza estado y/o horario comercial del tenant.

    Body opcional:
      - status: "active" | "inactive"
      - business_hours_start: int (0-23)
      - business_hours_end: int (1-24)
      - business_hours_timezone: str (IANA TZ)
    """
    async with AsyncSessionFactory() as session:  # type: ignore
        tenant = (await session.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant no encontrado")

        if "status" in body:
            status = body.get("status")
            if status not in ("active", "inactive"):
                raise HTTPException(status_code=400, detail="status inválido")
            tenant.status = status  # type: ignore[assignment]

        if "business_hours_start" in body:
            try:
                raw = body.get("business_hours_start")
                if raw is None:
                    raise ValueError
                bh_start = int(raw)
                if not (0 <= bh_start <= 23):
                    raise ValueError
                tenant.business_hours_start = bh_start  # type: ignore[attr-defined]
            except Exception:
                raise HTTPException(status_code=400, detail="business_hours_start inválido")

        if "business_hours_end" in body:
            try:
                raw = body.get("business_hours_end")
                if raw is None:
                    raise ValueError
                bh_end = int(raw)
                if not (1 <= bh_end <= 24):
                    raise ValueError
                tenant.business_hours_end = bh_end  # type: ignore[attr-defined]
            except Exception:
                raise HTTPException(status_code=400, detail="business_hours_end inválido")

        if "business_hours_timezone" in body:
            bh_tz = body.get("business_hours_timezone")
            if not isinstance(bh_tz, str) or not bh_tz:
                raise HTTPException(status_code=400, detail="business_hours_timezone inválido")
            tenant.business_hours_timezone = bh_tz  # type: ignore[attr-defined]

        await session.commit()

    await dynamic_tenant_service.refresh()
    return {
        "status": "updated",
        "tenant_id": tenant_id,
        "new_status": getattr(tenant, "status", None),
        "business_hours_start": getattr(tenant, "business_hours_start", None),
        "business_hours_end": getattr(tenant, "business_hours_end", None),
        "business_hours_timezone": getattr(tenant, "business_hours_timezone", None),
    }


# Endpoints para gestión de caché de audio
@router.get("/audio-cache/stats")
@limit("60/minute")
async def get_audio_cache_stats(request: Request):
    """Obtiene estadísticas de la caché de audio."""
    audio_processor = AudioProcessor()
    return await audio_processor.get_cache_stats()


@router.delete("/audio-cache")
@limit("10/minute")
async def clear_audio_cache(request: Request):
    """Limpia toda la caché de audio."""
    audio_processor = AudioProcessor()
    deleted_count = await audio_processor.clear_audio_cache()
    return {"status": "cache_cleared", "deleted_entries": deleted_count}


@router.delete("/audio-cache/entry")
@limit("30/minute")
async def remove_cache_entry(request: Request, text: str, voice: str = "default"):
    """Elimina una entrada específica de la caché."""
    audio_processor = AudioProcessor()
    removed = await audio_processor.remove_from_cache(text, voice)
    return {
        "status": "entry_removed" if removed else "entry_not_found",
        "text": text,
        "voice": voice,
        "removed": removed,
    }


@router.post("/audio-cache/cleanup")
@limit("5/minute")
async def trigger_audio_cache_cleanup(request: Request):
    """Ejecuta manualmente la limpieza de caché basada en tamaño."""
    from ..services.audio_cache_service import get_audio_cache_service

    cache_service = await get_audio_cache_service()
    cleanup_result = await cache_service._check_and_cleanup_cache()

    return {"status": "cleanup_triggered", "result": cleanup_result}


# ============================================================
# FEATURE 6: REVIEW MANAGEMENT ENDPOINTS
# ============================================================


@router.post("/reviews/send")
@limit("10/minute")
async def send_review_request(request: Request, body: dict):
    """
    Envía una solicitud de reseña manualmente a un huésped.

    Body:
        {
            "guest_id": "5491112345678",
            "force_send": false
        }
    """
    from ..services.review_service import get_review_service

    guest_id = body.get("guest_id")
    if not guest_id:
        raise HTTPException(status_code=400, detail="guest_id es requerido")

    force_send = body.get("force_send", False)

    review_service = get_review_service()
    result = await review_service.send_review_request(guest_id, force_send)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to send review request"))

    return result


@router.post("/reviews/schedule")
@limit("10/minute")
async def schedule_review_request_admin(request: Request, body: dict):
    """
    Programa una solicitud de reseña para envío diferido.

    Body:
        {
            "guest_id": "5491112345678",
            "guest_name": "Juan Pérez",
            "booking_id": "HTL-001",
            "checkout_date": "2025-01-10T12:00:00Z",
            "segment": "couple",  # couple|business|family|solo|group|vip
            "language": "es"
        }
    """
    from ..services.review_service import get_review_service, GuestSegment
    from datetime import datetime

    required_fields = ["guest_id", "guest_name", "booking_id", "checkout_date"]
    for field in required_fields:
        if field not in body:
            raise HTTPException(status_code=400, detail=f"{field} es requerido")

    # Parse segment
    segment_str = body.get("segment", "couple")
    try:
        segment = GuestSegment(segment_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Segment inválido: {segment_str}")

    # Parse checkout date
    try:
        checkout_date = datetime.fromisoformat(body["checkout_date"].replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="checkout_date debe ser ISO 8601")

    review_service = get_review_service()
    result = await review_service.schedule_review_request(
        guest_id=body["guest_id"],
        guest_name=body["guest_name"],
        booking_id=body["booking_id"],
        checkout_date=checkout_date,
        segment=segment,
        language=body.get("language", "es"),
    )

    return result


@router.post("/reviews/mark-submitted")
@limit("30/minute")
async def mark_review_submitted_admin(request: Request, body: dict):
    """
    Marca una reseña como enviada (cuando se confirma externamente).

    Body:
        {
            "guest_id": "5491112345678",
            "platform": "google"  # google|tripadvisor|booking|expedia|facebook
        }
    """
    from ..services.review_service import get_review_service, ReviewPlatform

    guest_id = body.get("guest_id")
    platform_str = body.get("platform")

    if not guest_id or not platform_str:
        raise HTTPException(status_code=400, detail="guest_id y platform son requeridos")

    try:
        platform = ReviewPlatform(platform_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Platform inválida: {platform_str}")

    review_service = get_review_service()
    result = await review_service.mark_review_submitted(guest_id, platform)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error", "Review request not found"))

    return result


@router.get("/reviews/analytics")
@limit("60/minute")
async def get_review_analytics(request: Request):
    """
    Obtiene estadísticas y analytics del sistema de reseñas.

    Returns:
        {
            "overview": {
                "requests_sent": 150,
                "responses_received": 75,
                "reviews_submitted": 50,
                "conversion_rate": 33.3
            },
            "platform_performance": {"google": 25, "tripadvisor": 15, ...},
            "segment_performance": {"couple": {...}, "business": {...}, ...}
        }
    """
    from ..services.review_service import get_review_service

    review_service = get_review_service()
    analytics = review_service.get_review_analytics()

    return analytics


@router.get("/audit-logs")
@limit("60/minute")
async def get_audit_logs(
    request: Request,
    tenant_id: str | None = None,
    user_id: str | None = None,
    event_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """
    Obtiene logs de auditoría con paginación y filtros opcionales.

    Este endpoint implementa paginación para prevenir sobrecarga al consultar
    miles de registros. Soporta filtros múltiples para queries específicas.

    Query Parameters:
        tenant_id (str, optional): Filtrar por tenant/hotel específico
        user_id (str, optional): Filtrar por usuario específico
        event_type (str, optional): Tipo de evento (login_success, access_denied, etc.)
        page (int, optional): Número de página (1-indexed, default: 1)
        page_size (int, optional): Registros por página (default: 20, max: 100)

    Returns:
        {
            "logs": [
                {
                    "id": 123,
                    "timestamp": "2025-10-14T10:30:00Z",
                    "event_type": "login_success",
                    "user_id": "user123",
                    "ip_address": "192.168.1.100",
                    "resource": "/api/auth/login",
                    "details": {...},
                    "tenant_id": "hotel_abc",
                    "severity": "info"
                },
                ...
            ],
            "pagination": {
                "page": 1,
                "page_size": 20,
                "total": 1534,
                "pages": 77
            }
        }

    Raises:
        HTTPException 400: Si page < 1 o page_size fuera de rango

    Example:
        GET /admin/audit-logs?tenant_id=hotel_abc&page=2&page_size=50
        GET /admin/audit-logs?user_id=user123&event_type=login_failed
    """
    from ..services.security.audit_logger import get_audit_logger, AuditEventType
    from ..core.constants import MAX_PAGE_SIZE, MIN_PAGE_SIZE

    # Validar parámetros
    if page < 1:
        raise HTTPException(status_code=400, detail="page debe ser >= 1")

    if page_size < MIN_PAGE_SIZE or page_size > MAX_PAGE_SIZE:
        raise HTTPException(status_code=400, detail=f"page_size debe estar entre {MIN_PAGE_SIZE} y {MAX_PAGE_SIZE}")

    # Convertir event_type string a enum si fue proporcionado
    event_type_enum = None
    if event_type:
        try:
            event_type_enum = AuditEventType(event_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"event_type inválido: {event_type}. Valores permitidos: {[e.value for e in AuditEventType]}",
            )

    # Obtener logs con paginación
    audit_logger = get_audit_logger()
    logs, total = await audit_logger.get_audit_logs(
        tenant_id=tenant_id,
        user_id=user_id,
        event_type=event_type_enum,
        page=page,
        page_size=page_size,
    )

    # Calcular número total de páginas
    import math

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    # Convertir logs a dict para respuesta JSON
    logs_data = [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "event_type": log.event_type,
            "user_id": log.user_id,
            "ip_address": log.ip_address,
            "resource": log.resource,
            "details": log.details,
            "tenant_id": log.tenant_id,
            "severity": log.severity,
        }
        for log in logs
    ]

    return {
        "logs": logs_data,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": total_pages,
        },
    }
