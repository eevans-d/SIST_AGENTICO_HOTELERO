# [PROMPT 2.8] app/routers/admin.py (FINAL)

from fastapi import APIRouter, Depends, Request
from ..core.security import get_current_user
from ..core.ratelimit import limit

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(get_current_user)])


@router.get("/dashboard")
@limit("30/minute")
async def get_dashboard(request: Request):
    # Respuesta alineada con tests/test_auth.py
    return {"message": "Welcome to the admin dashboard"}
