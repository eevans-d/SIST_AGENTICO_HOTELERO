import json
import re
import hmac
import hashlib

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.core.security import create_access_token
from app.models.lock_audit import Base


class _DummyWhatsAppClient:
    async def send_message(self, *args, **kwargs):
        return {"status": "ok"}

    async def send_audio_message(self, *args, **kwargs):
        return {"status": "ok"}

    async def send_interactive_message(self, *args, **kwargs):
        return {"status": "ok"}

    async def send_image(self, *args, **kwargs):
        return {"status": "ok"}

    async def send_location(self, *args, **kwargs):
        return {"status": "ok"}

    async def send_reaction(self, *args, **kwargs):
        return {"status": "ok"}

    async def close(self):
        return None


async def _setup_sqlite_memory_and_patch_modules():
    # Create in-memory SQLite and tables
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Patch database and modules that imported the factory directly
    from app.core import database as db
    db.engine = engine  # type: ignore
    db.AsyncSessionFactory = session_factory  # type: ignore

    # Patch dynamic_tenant_service module vars
    import app.services.dynamic_tenant_service as dyn_mod
    dyn_mod.AsyncSessionFactory = session_factory  # type: ignore
    # Recreate service instance to re-register Prometheus metrics after registry reset
    dyn_mod.dynamic_tenant_service = dyn_mod.DynamicTenantService(strict_mode=False, refresh_interval=999)  # type: ignore
    dynamic_tenant_service = dyn_mod.dynamic_tenant_service
    # Ensure a clean refresh of caches against our in-memory DB
    await dynamic_tenant_service.refresh()

    # Patch admin module factory (was imported by name)
    import app.routers.admin as admin_mod
    admin_mod.AsyncSessionFactory = session_factory  # type: ignore
    # Ensure admin uses the same dynamic_tenant_service instance
    admin_mod.dynamic_tenant_service = dyn_mod.dynamic_tenant_service  # type: ignore

    # Patch message_gateway dynamic resolver reference to the same instance
    import app.services.message_gateway as mg_mod
    mg_mod._TENANT_RESOLVER_DYNAMIC = dyn_mod.dynamic_tenant_service  # type: ignore

    return session_factory


def _make_signature(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _parse_metric_value(body: str, metric: str, labels: dict[str, str] | None = None) -> float | None:
    # Build regex for metric with optional labels
    if labels:
        labels_str = ",".join([f"{k}=\"{v}\"" for k, v in labels.items()])
        pattern = rf"^{re.escape(metric)}\{{{labels_str}\}}\s+(\d+(?:\.\d+)?)$"
    else:
        pattern = rf"^{re.escape(metric)}\s+(\d+(?:\.\d+)?)$"
    for line in body.splitlines():
        m = re.match(pattern, line)
        if m:
            return float(m.group(1))
    return None


@pytest.mark.asyncio
async def test_admin_tenants_e2e_and_metrics(monkeypatch):
    # Use in-memory DB and patch modules
    await _setup_sqlite_memory_and_patch_modules()

    # Patch WhatsApp client to avoid external calls
    import app.services.whatsapp_client as wa_mod
    monkeypatch.setattr(wa_mod, "WhatsAppMetaClient", _DummyWhatsAppClient)

    token = create_access_token({"sub": "admin"})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1) Create tenant
        r = await ac.post("/admin/tenants", headers=headers, json={"tenant_id": "hotel_e2e", "name": "Hotel E2E"})
        assert r.status_code == 200, r.text

        # 2) Add identifier and refresh cache implicitly
        identifier = "+549110001111"
        r = await ac.post(f"/admin/tenants/hotel_e2e/identifiers", headers=headers, json={"identifier": identifier})
        assert r.status_code == 200, r.text

        # 3) List tenants
        r = await ac.get("/admin/tenants", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert any(t["tenant_id"] == "hotel_e2e" and t["status"] == "active" for t in data.get("tenants", []))

        # 4) Metrics should reflect 1 active tenant and 1 identifier cached
        r = await ac.get("/metrics")
        metrics_txt = r.text
        tenants_active = _parse_metric_value(metrics_txt, "tenants_active_total")
        identifiers_cached = _parse_metric_value(metrics_txt, "tenant_identifiers_cached_total")
        assert tenants_active == 1
        assert identifiers_cached == 1

        # 5) Trigger tenant resolution via WhatsApp webhook (should count as 'hit')
        from app.core.settings import settings as st
        body = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "waba_id",
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": identifier,
                                        "id": "wamid.test",
                                        "timestamp": "1700000000",
                                        "type": "text",
                                        "text": {"body": "hola"},
                                    }
                                ]
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }
        body_bytes = json.dumps(body).encode("utf-8")
        sig = _make_signature(st.whatsapp_app_secret.get_secret_value(), body_bytes)
        r = await ac.post("/webhooks/whatsapp", content=body_bytes, headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})
        assert r.status_code == 200

        # Check counter increment for hit
        r = await ac.get("/metrics")
        hit_count = _parse_metric_value(r.text, "tenant_resolution_total", {"result": "hit"})
        assert hit_count is not None and hit_count >= 1

        # 6) Remove identifier first (avoid lazy-load in refresh), then deactivate tenant
        r = await ac.delete(f"/admin/tenants/hotel_e2e/identifiers/{identifier}", headers=headers)
        assert r.status_code in (200, 404)

        # After removing identifier, identifiers_cached should be 0 while tenant still active
        r = await ac.get("/metrics")
        tenants_active = _parse_metric_value(r.text, "tenants_active_total")
        identifiers_cached = _parse_metric_value(r.text, "tenant_identifiers_cached_total")
        assert tenants_active == 1
        assert identifiers_cached == 0

        # Now deactivate tenant and verify active tenants drop to 0
        r = await ac.patch("/admin/tenants/hotel_e2e", headers=headers, json={"status": "inactive"})
        assert r.status_code == 200

        r = await ac.get("/metrics")
        tenants_active = _parse_metric_value(r.text, "tenants_active_total")
        identifiers_cached = _parse_metric_value(r.text, "tenant_identifiers_cached_total")
        assert tenants_active == 0
        assert identifiers_cached == 0
