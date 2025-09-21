# [PROMPT 2.8] app/routers/admin.py (FINAL)

from fastapi import APIRouter, Depends
from ..core.security import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(get_current_user)])


@router.get("/dashboard")
async def get_dashboard():
    # Respuesta alineada con tests/test_auth.py
    return {"message": "Welcome to the admin dashboard"}
