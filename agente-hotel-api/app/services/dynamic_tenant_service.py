from __future__ import annotations
import asyncio
from typing import Dict, Optional, List
from sqlalchemy import select
from ..core.database import AsyncSessionFactory, engine
from ..core.logging import logger
from prometheus_client import Counter, Gauge, Histogram
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
        # Métricas
        self.resolution_total = Counter("tenant_resolution_total", "Total resoluciones de tenant", ["result"])
        self.active_tenants_gauge = Gauge("tenants_active_total", "Tenants activos en cache")
        self.identifiers_cached_gauge = Gauge("tenant_identifiers_cached_total", "Identificadores en cache")
        self.refresh_latency = Histogram("tenant_refresh_latency_seconds", "Latencia de refresh de tenants")

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
        start = asyncio.get_event_loop().time()
        async with self._lock:
            async with AsyncSessionFactory() as session:  # type: ignore
                mapping: Dict[str, str] = {}
                tenants_meta: Dict[str, dict] = {}
                tenants = (await session.execute(select(Tenant).where(Tenant.status == "active"))).scalars().all()
                for t in tenants:
                    tenants_meta[t.tenant_id] = {
                        "name": t.name,
                        "status": t.status,
                        # Optional business hours overrides
                        "business_hours_start": getattr(t, "business_hours_start", None),
                        "business_hours_end": getattr(t, "business_hours_end", None),
                        "business_hours_timezone": getattr(t, "business_hours_timezone", None),
                    }
                ids = (await session.execute(select(TenantUserIdentifier))).scalars().all()
                for i in ids:
                    if i.tenant and i.tenant.status == "active":
                        norm = self._normalize_identifier(str(i.identifier))
                        mapping[norm] = i.tenant.tenant_id
                self._mapping = mapping
                self._tenants_meta = tenants_meta
                # Métricas gauges
                try:
                    self.active_tenants_gauge.set(len(self._tenants_meta))
                    self.identifiers_cached_gauge.set(len(self._mapping))
                except Exception:  # pragma: no cover
                    pass
        elapsed = asyncio.get_event_loop().time() - start
        try:
            self.refresh_latency.observe(elapsed)
        except Exception:  # pragma: no cover
            pass
        logger.info(
            "Tenants cache refreshed",
            identifiers=len(self._mapping),
            tenants=len(self._tenants_meta),
            elapsed=elapsed,
        )

    def resolve_tenant(self, user_id: str, provided_tenant: Optional[str] = None) -> Optional[str]:
        if provided_tenant:
            try:
                self.resolution_total.labels(result="provided").inc()
            except Exception:  # pragma: no cover
                pass
            return provided_tenant
        key = self._normalize_identifier(user_id)
        if key in self._mapping:
            try:
                self.resolution_total.labels(result="hit").inc()
            except Exception:  # pragma: no cover
                pass
            return self._mapping[key]
        if self.strict_mode:
            try:
                self.resolution_total.labels(result="miss_strict").inc()
            except Exception:  # pragma: no cover
                pass
            return None
        try:
            self.resolution_total.labels(result="default").inc()
        except Exception:  # pragma: no cover
            pass
        return "default"

    def list_tenants(self) -> List[dict]:
        return [{"tenant_id": tid, **meta} for tid, meta in sorted(self._tenants_meta.items(), key=lambda x: x[0])]

    def get_tenant_meta(self, tenant_id: str) -> Optional[dict]:
        """Obtiene el metadata del tenant activo desde caché.

        Devuelve None si no existe o si no está en caché (no activo).
        """
        return self._tenants_meta.get(tenant_id)

    def _normalize_identifier(self, identifier: str) -> str:
        """Normaliza identificadores de usuario (teléfono/email) para matching estable.

        Reglas simples sin dependencias externas:
        - Emails: lower-case + strip espacios.
        - Teléfonos: eliminar espacios, guiones y paréntesis. Convertir prefijo 00→+.
          Conservar '+' si viene. Si solo dígitos y sin prefijo, se dejan tal cual.
        """
        if not identifier:
            return identifier
        s = identifier.strip()
        if "@" in s:
            return s.lower()
        # Teléfono básico
        s = s.replace("(", "").replace(")", "").replace(" ", "").replace("-", "")
        if s.startswith("00"):
            s = "+" + s[2:]
        # Opción avanzada con phonenumbers si flag está activo y la librería está disponible
        try:
            from .feature_flag_service import DEFAULT_FLAGS  # evitar await en método sync

            advanced = DEFAULT_FLAGS.get("tenancy.phone_normalization.advanced", False)
        except Exception:
            advanced = False

        if advanced:
            try:
                import phonenumbers

                # Solo intentamos parsear si parece internacional (+...)
                if s.startswith("+"):
                    num = phonenumbers.parse(s, None)
                    if phonenumbers.is_possible_number(num) and phonenumbers.is_valid_number(num):
                        return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
            except Exception:
                # Fallback silencioso
                pass

        # Dejar '+' si está, si no, devolver dígitos tal cual
        return s


dynamic_tenant_service = DynamicTenantService(strict_mode=False)
