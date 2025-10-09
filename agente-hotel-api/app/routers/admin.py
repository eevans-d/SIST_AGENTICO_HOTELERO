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
async def update_tenant_status(tenant_id: str, body: dict):
    status = body.get("status")
    if status not in ("active", "inactive"):
        raise HTTPException(status_code=400, detail="status inválido")
    async with AsyncSessionFactory() as session:  # type: ignore
        tenant = (await session.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant no encontrado")
        tenant.status = status  # type: ignore[assignment]
        await session.commit()
    await dynamic_tenant_service.refresh()
    return {"status": "updated", "tenant_id": tenant_id, "new_status": status}


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
    return {
        "status": "cache_cleared",
        "deleted_entries": deleted_count
    }


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
        "removed": removed
    }


@router.post("/audio-cache/cleanup")
@limit("5/minute")
async def trigger_audio_cache_cleanup(request: Request):
    """Ejecuta manualmente la limpieza de caché basada en tamaño."""
    from ..services.audio_cache_service import get_audio_cache_service
    
    cache_service = await get_audio_cache_service()
    cleanup_result = await cache_service._check_and_cleanup_cache()
    
    return {
        "status": "cleanup_triggered",
        "result": cleanup_result
    }
