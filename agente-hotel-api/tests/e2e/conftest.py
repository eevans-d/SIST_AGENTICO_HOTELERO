"""
E2E Test Configuration and Fixtures for Multi-Tenancy Testing.

This module provides:
- E2E test database setup
- Tenant fixtures for E2E tests
- User fixtures for different tenants
- Cleanup utilities
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator

from app.models.lock_audit import Base
from app.models.tenant import Tenant
from app.models.user import User


# E2E Test Database Configuration
E2E_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def e2e_db_engine():
    """
    Create a fresh database engine for each E2E test.
    Uses SQLite in-memory for fast, isolated tests.
    """
    engine = create_async_engine(
        E2E_DATABASE_URL,
        echo=False,
        future=True
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def e2e_db_session(e2e_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a database session for E2E tests.
    Session is automatically rolled back after each test.
    """
    async_session = sessionmaker(
        e2e_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def tenant_a(e2e_db_session: AsyncSession) -> Tenant:
    """Create tenant A for E2E tests."""
    tenant = Tenant(
        tenant_id="hotel-a-e2e",
        name="Hotel A E2E Test",
        config={
            "pms_url": "https://pms-a.example.com",
            "features": ["reservations", "late_checkout"]
        }
    )
    e2e_db_session.add(tenant)
    await e2e_db_session.commit()
    await e2e_db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def tenant_b(e2e_db_session: AsyncSession) -> Tenant:
    """Create tenant B for E2E tests."""
    tenant = Tenant(
        tenant_id="hotel-b-e2e",
        name="Hotel B E2E Test",
        config={
            "pms_url": "https://pms-b.example.com",
            "features": ["reservations"]
        }
    )
    e2e_db_session.add(tenant)
    await e2e_db_session.commit()
    await e2e_db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def user_tenant_a(e2e_db_session: AsyncSession, tenant_a: Tenant) -> User:
    """Create a user for tenant A."""
    user = User(
        phone_number="+34600111222",
        tenant_id=tenant_a.tenant_id,
        preferred_language="es",
        metadata={"test": "user_a"}
    )
    e2e_db_session.add(user)
    await e2e_db_session.commit()
    await e2e_db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_tenant_b(e2e_db_session: AsyncSession, tenant_b: Tenant) -> User:
    """Create a user for tenant B."""
    user = User(
        phone_number="+34600333444",
        tenant_id=tenant_b.tenant_id,
        preferred_language="en",
        metadata={"test": "user_b"}
    )
    e2e_db_session.add(user)
    await e2e_db_session.commit()
    await e2e_db_session.refresh(user)
    return user


@pytest.fixture
def reservation_data_tenant_a():
    """Sample reservation data for tenant A."""
    return {
        "checkin_date": "2025-12-01",
        "checkout_date": "2025-12-05",
        "room_type": "double",
        "guest_name": "Juan Pérez",
        "guest_email": "juan@example.com",
        "guest_phone": "+34600111222",
        "num_guests": 2,
        "special_requests": "Vista al mar"
    }


@pytest.fixture
def reservation_data_tenant_b():
    """Sample reservation data for tenant B."""
    return {
        "checkin_date": "2025-12-10",
        "checkout_date": "2025-12-15",
        "room_type": "suite",
        "guest_name": "John Smith",
        "guest_email": "john@example.com",
        "guest_phone": "+34600333444",
        "num_guests": 3,
        "special_requests": "Late checkout"
    }


@pytest_asyncio.fixture
async def cleanup_test_data(e2e_db_session: AsyncSession):
    """
    Cleanup fixture that runs after each test.
    Ensures all test data is removed.
    """
    yield
    
    # Cleanup all tables
    async with e2e_db_session.begin():
        # Delete in reverse order of dependencies
        await e2e_db_session.execute("DELETE FROM audit_logs")
        await e2e_db_session.execute("DELETE FROM dlq_permanent_failures")
        await e2e_db_session.execute("DELETE FROM lock_audit")
        await e2e_db_session.execute("DELETE FROM users")
        await e2e_db_session.execute("DELETE FROM tenants")
    
    await e2e_db_session.commit()
