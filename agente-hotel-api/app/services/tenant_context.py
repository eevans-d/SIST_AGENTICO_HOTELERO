"""Tenant Context Service (fase 5)

Responsabilidad: resolver y validar tenant_id a partir de metadatos del mensaje o reglas.
Diseño simple inicial:
- Mapping estático en memoria (simulando futura consulta a DB/config).
- Fallback: tenant "default" si no se puede resolver y el flag experimental está desactivado.
"""

from __future__ import annotations
from typing import Optional

TENANT_MAPPING = {
    # Ejemplos: 'phone_or_email': 'tenant_id'
    "+5491112345678": "hotel_centro",
    "reservas@demo-hotel.com": "hotel_centro",
}


class TenantContextService:
    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode

    def resolve_tenant(self, user_id: str, provided_tenant: Optional[str] = None) -> Optional[str]:
        if provided_tenant:
            return provided_tenant
        if user_id in TENANT_MAPPING:
            return TENANT_MAPPING[user_id]
        if self.strict_mode:
            return None
        return "default"

    def validate_tenant(self, tenant_id: Optional[str]) -> bool:
        if tenant_id is None:
            return False
        if tenant_id == "default":
            return True
        return tenant_id in set(TENANT_MAPPING.values())


tenant_context_service = TenantContextService(strict_mode=False)
