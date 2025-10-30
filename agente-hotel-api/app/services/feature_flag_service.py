"""Servicio simple de Feature Flags (Fase 5 - Esqueleto)

Patrones:
- Lectura rápida desde caché local in-memory con TTL suave
- Origen de verdad en Redis hash `feature_flags`
- Fallback a valores por defecto declarados en `DEFAULT_FLAGS`

No se implementa (todavía) invalidación push; se confía en TTL corto.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional


from ..core.redis_client import get_redis
from .metrics_service import metrics_service


DEFAULT_FLAGS: Dict[str, bool] = {
    "nlp.fallback.enhanced": True,
    "canary.enabled": False,
    "multi_tenant.experimental": False,
    "tenancy.dynamic.enabled": True,
    # Normalización avanzada de teléfonos (phonenumbers). Fallback simple si False o lib no instalada
    "tenancy.phone_normalization.advanced": False,
    # Preferir respuestas de texto simples por defecto (tests e integraciones básicas)
    "features.interactive_messages": False,
    # Humanización de respuestas (opt-in, seguro por defecto)
    "humanize.es_ar.enabled": False,
    "humanize.consolidate_text.enabled": False,
    "humanize.delay.enabled": False,
    # Confirmación de reserva con QR (opcional, desactivado por defecto)
    "reservation.qr.enabled": False,
}


class FeatureFlagService:
    def __init__(self, redis_client: Any, ttl_seconds: int = 30):
        self.redis = redis_client
        self.ttl = ttl_seconds
        self._cache: Dict[str, tuple[float, bool]] = {}
        self._lock = asyncio.Lock()

    async def is_enabled(self, flag: str, default: Optional[bool] = None) -> bool:
        """Devuelve el estado del flag.

        Orden de resolución:
        1. Caché local válida
        2. Redis hash `feature_flags`
        3. DEFAULT_FLAGS
        4. Parámetro `default` (si no existe en defaults)
        """
        now = time.time()
        cached = self._cache.get(flag)
        if cached and (now - cached[0]) < self.ttl:
            return cached[1]

        # Evita thundering herd: un solo lector refresca
        async with self._lock:
            cached = self._cache.get(flag)
            if cached and (now - cached[0]) < self.ttl:
                return cached[1]

            try:
                value = await self.redis.hget("feature_flags", flag)
                if value is not None:
                    raw = value.decode() if isinstance(value, (bytes, bytearray)) else str(value)
                    enabled = raw.lower() in ("1", "true", "on", "yes")
                else:
                    if flag in DEFAULT_FLAGS:
                        enabled = DEFAULT_FLAGS[flag]
                    else:
                        enabled = bool(default) if default is not None else False
            except Exception:
                # Resiliencia: en error Redis usar default seguro
                if flag in DEFAULT_FLAGS:
                    enabled = DEFAULT_FLAGS[flag]
                else:
                    enabled = bool(default) if default is not None else False

            self._cache[flag] = (now, enabled)
            # Métrica gauge
            try:
                metrics_service.update_feature_flag(flag, enabled)
            except Exception:  # pragma: no cover
                pass
            return enabled

    async def set_flag(self, flag: str, value: bool):
        """Establece un flag (uso administrativo / pruebas)."""
        try:
            await self.redis.hset("feature_flags", flag, int(value))
        finally:
            # Invalida caché local
            self._cache.pop(flag, None)
            try:
                metrics_service.update_feature_flag(flag, value)
            except Exception:  # pragma: no cover
                pass


_feature_flag_service: Optional[FeatureFlagService] = None


async def get_feature_flag_service() -> FeatureFlagService:
    global _feature_flag_service
    if _feature_flag_service is None:
        redis_client = await get_redis()
        _feature_flag_service = FeatureFlagService(redis_client)
    return _feature_flag_service
