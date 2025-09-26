from __future__ import annotations
import asyncio
from typing import Dict, Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import AsyncSessionFactory, engine
from ..core.logging import logger
from ..models.lock_audit import Base
from ..models.tenant import Tenant, TenantUserIdentifier

class DynamicTenantService:
    """Servicio dinámico de tenants con caché en memoria.

    - Carga mapping identifier -> tenant_id lógico.
    - Refrescable bajo demanda (admin endpoint) o en intervalo.
    - Fallback a 'default' si no encuentra y modo no estricto.
    """

    def __init__(self, strict_mode: bool = False, refresh_interval: int = 300):
        self.strict_mode = strict_mode
        self.refresh_interval = refresh_interval
        self._mapping: Dict[str, str] = {}
        self._tenants_meta: Dict[str, dict] = {}
        self._lock = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        # Crear tablas si no existen (simple bootstrap; en prod usar migrations)
        async with engine.begin() as conn:  # type: ignore[attr-defined]
            await conn.run_sync(Base.metadata.create_all)
        await self.refresh()
        self._task = asyncio.create_task(self._auto_refresh_loop())
        logger.info("DynamicTenantService started", tenants=len(self._tenants_meta))

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except Exception:  # pragma: no cover
                pass

    async def _auto_refresh_loop(self):  # pragma: no cover (dificil de testear timing)
        while True:
            await asyncio.sleep(self.refresh_interval)
            try:
                await self.refresh()
            except Exception as e:
                logger.warning("Auto refresh tenants failed", error=str(e))

    async def refresh(self):
        async with self._lock:
            async with AsyncSessionFactory() as session:  # type: ignore
                mapping: Dict[str, str] = {}
                tenants_meta: Dict[str, dict] = {}
                # Obtener tenants activos
                tenants = (await session.execute(select(Tenant).where(Tenant.status == "active"))).scalars().all()
                for t in tenants:
                    tenants_meta[t.tenant_id] = {"name": t.name, "status": t.status}
                # Obtener identificadores
                ids = (await session.execute(select(TenantUserIdentifier))).scalars().all()
                for i in ids:
                    if i.tenant and i.tenant.status == "active":
                        mapping[i.identifier] = i.tenant.tenant_id
                self._mapping = mapping
                self._tenants_meta = tenants_meta
        logger.info("Tenants cache refreshed", identifiers=len(self._mapping), tenants=len(self._tenants_meta))

    def resolve_tenant(self, user_id: str, provided_tenant: Optional[str] = None) -> Optional[str]:
        if provided_tenant:
            return provided_tenant
        if user_id in self._mapping:
            return self._mapping[user_id]
        if self.strict_mode:
            return None
        return "default"

    def list_tenants(self) -> List[dict]:
        return [
            {"tenant_id": tid, **meta} for tid, meta in sorted(self._tenants_meta.items(), key=lambda x: x[0])
        ]

dynamic_tenant_service = DynamicTenantService(strict_mode=False)
