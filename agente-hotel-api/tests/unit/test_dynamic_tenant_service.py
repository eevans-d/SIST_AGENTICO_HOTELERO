import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.services import dynamic_tenant_service as dyn_mod
from app.models.tenant import Tenant, TenantUserIdentifier
from app.models.lock_audit import Base
from app.core import database


async def _setup_sqlite_memory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    # Inyectar en módulo database para que lo use dynamic_tenant_service.refresh
    database.engine = engine  # type: ignore
    database.AsyncSessionFactory = session_factory  # type: ignore
    return session_factory


@pytest.mark.asyncio
async def test_dynamic_tenant_resolution():
    # Arrange: insertar tenant y mapping
    session_factory = await _setup_sqlite_memory()
    async with session_factory() as session:  # type: ignore
        t = Tenant(tenant_id="hotel_demo", name="Hotel Demo")
        session.add(t)
        await session.flush()
        session.add(TenantUserIdentifier(tenant_id=t.id, identifier="+111"))
        await session.commit()

    # Act: refresh cache
    # Parchear factory dentro del módulo del servicio
    dyn_mod.AsyncSessionFactory = session_factory  # type: ignore
    dynamic_tenant_service = dyn_mod.dynamic_tenant_service  # alias
    await dynamic_tenant_service.refresh()
    # Assert resolution
    assert dynamic_tenant_service.resolve_tenant("+111") == "hotel_demo"
    # Unknown -> default
    assert dynamic_tenant_service.resolve_tenant("+999") == "default"

    # List tenants contains our tenant
    tenants = dynamic_tenant_service.list_tenants()
    assert any(t["tenant_id"] == "hotel_demo" for t in tenants)


@pytest.mark.asyncio
async def test_dynamic_tenant_strict_and_provided():
    # Arrange: sqlite in-memory and a single tenant without identifiers
    session_factory = await _setup_sqlite_memory()
    async with session_factory() as session:  # type: ignore
        t = Tenant(tenant_id="hotel_strict", name="Hotel Strict")
        session.add(t)
        await session.commit()

    # Use a fresh service instance in strict mode
    from app.services.dynamic_tenant_service import DynamicTenantService

    svc = DynamicTenantService(strict_mode=True, refresh_interval=999)
    # Inyectar factory en el módulo del servicio
    dyn_mod.AsyncSessionFactory = session_factory  # type: ignore
    await svc.refresh()

    # Provided tenant bypasses lookup
    assert svc.resolve_tenant("+000", provided_tenant="hotel_provided") == "hotel_provided"

    # No mapping and strict -> None
    assert svc.resolve_tenant("+999") is None


@pytest.mark.asyncio
async def test_dynamic_tenant_identifier_normalization():
    # Arrange: sqlite in-memory and a tenant with a messy phone identifier
    session_factory = await _setup_sqlite_memory()
    async with session_factory() as session:  # type: ignore
        t = Tenant(tenant_id="hotel_norm", name="Hotel Norm")
        session.add(t)
        await session.flush()
        # Identifier con espacios, paréntesis, guiones y prefijo 00
        session.add(TenantUserIdentifier(tenant_id=t.id, identifier=" 00 54 (9) 11-000-2222 "))
        await session.commit()

    # Use a fresh service instance
    from app.services.dynamic_tenant_service import DynamicTenantService

    svc = DynamicTenantService(strict_mode=False, refresh_interval=999)
    # Inyectar factory en el módulo del servicio
    dyn_mod.AsyncSessionFactory = session_factory  # type: ignore
    await svc.refresh()

    # Diferentes formatos del mismo número deben resolver al mismo tenant
    assert svc.resolve_tenant("+549110002222") == "hotel_norm"
    assert svc.resolve_tenant("00549110002222") == "hotel_norm"
    assert svc.resolve_tenant(" +54 9 11 000 2222 ") == "hotel_norm"
