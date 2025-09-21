# [PROMPT 2.8] app/routers/admin.py (FINAL)

from fastapi import APIRouter, Depends
from ..core.security import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(get_current_user)])


@router.get("/dashboard-data")
async def get_dashboard_data():
    return {"conversations": []}
