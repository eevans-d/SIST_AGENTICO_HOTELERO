# [PROMPT 2.8] app/routers/admin.py (FINAL)

from fastapi import APIRouter, Depends, Request
from fastapi import HTTPException
from ..services.dynamic_tenant_service import dynamic_tenant_service
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
