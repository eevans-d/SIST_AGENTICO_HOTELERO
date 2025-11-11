"""Tests básicos del servicio de Feature Flags.

Objetivo: aumentar cobertura (>25%) y validar resolución de flags sin Redis real.

Casos cubiertos:
1. Fallback a DEFAULT_FLAGS cuando Redis devuelve None.
2. Override manual mediante set_flag y refresco de caché.
3. Uso del parámetro default cuando flag inexistente.
4. Métrica gauge actualizada (feature_flag_enabled) tras cambios.

Nota: Se usa un stub Redis minimalista con hget/hset async.
"""

from typing import Dict, Any

import pytest

from app.services.feature_flag_service import FeatureFlagService, DEFAULT_FLAGS
from app.services.metrics_service import metrics_service


class StubRedis:
    def __init__(self):
        self.store: Dict[str, Dict[str, Any]] = {"feature_flags": {}}

    async def hget(self, h: str, k: str):
        return self.store.get(h, {}).get(k)

    async def hset(self, h: str, k: str, v: Any):
        self.store.setdefault(h, {})[k] = v


@pytest.mark.asyncio
async def test_default_flag_resolution():
    svc = FeatureFlagService(StubRedis(), ttl_seconds=1)
    # Flag existente en DEFAULT_FLAGS
    enabled = await svc.is_enabled("tenancy.dynamic.enabled")
    assert enabled is DEFAULT_FLAGS["tenancy.dynamic.enabled"]

@pytest.mark.asyncio
async def test_override_and_cache_invalidation():
    svc = FeatureFlagService(StubRedis(), ttl_seconds=5)
    # Inicialmente reservado.qr.enabled False
    assert await svc.is_enabled("reservation.qr.enabled") is False
    await svc.set_flag("reservation.qr.enabled", True)
    # Tras override debe ser True
    assert await svc.is_enabled("reservation.qr.enabled") is True

@pytest.mark.asyncio
async def test_unknown_flag_uses_default_param():
    svc = FeatureFlagService(StubRedis(), ttl_seconds=1)
    assert await svc.is_enabled("flag.inexistente", default=True) is True
    assert await svc.is_enabled("flag.inexistente", default=False) is True  # cache mantiene primer valor

@pytest.mark.asyncio
async def test_metrics_gauge_updated():
    svc = FeatureFlagService(StubRedis(), ttl_seconds=0)  # TTL 0 fuerza refresh
    await svc.set_flag("reservation.qr.enabled", True)
    assert await svc.is_enabled("reservation.qr.enabled") is True
    # Extraer valor del gauge
    collected = list(metrics_service.feature_flag_enabled.collect())
    assert collected, "No se recolectaron métricas del gauge feature_flag_enabled"
    samples = collected[0].samples
    # Buscar última muestra del flag específico
    value = None
    for s in samples:
        if s.labels.get("flag") == "reservation.qr.enabled":
            value = s.value
    assert value == 1
