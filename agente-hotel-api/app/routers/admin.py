# [PROMPT 2.8] app/routers/admin.py (FINAL)

from fastapi import APIRouter, Depends, Request
from fastapi import HTTPException
from ..services.dynamic_tenant_service import dynamic_tenant_service
from ..services.feature_flag_service import get_feature_flag_service
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
async def list_tenants():
    return {"tenants": dynamic_tenant_service.list_tenants()}


@router.post("/tenants/refresh")
async def refresh_tenants():
    try:
        await dynamic_tenant_service.refresh()
        return {"status": "refreshed"}
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tenants")
async def create_tenant(body: dict):
    tenant_id = body.get("tenant_id")
    name = body.get("name")
    if not tenant_id or not name:
        raise HTTPException(status_code=400, detail="tenant_id y name requeridos")
    async with AsyncSessionFactory() as session:  # type: ignore
        exists = (
            await session.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))
        ).scalar_one_or_none()
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
        tenant = (
            await session.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))
        ).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant no encontrado")
        existing = (
            await session.execute(
                select(TenantUserIdentifier).where(TenantUserIdentifier.identifier == identifier)
            )
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
        tenant = (
            await session.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))
        ).scalar_one_or_none()
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
        tenant = (
            await session.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))
        ).scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant no encontrado")
        tenant.status = status
        await session.commit()
    await dynamic_tenant_service.refresh()
    return {"status": "updated", "tenant_id": tenant_id, "new_status": status}
