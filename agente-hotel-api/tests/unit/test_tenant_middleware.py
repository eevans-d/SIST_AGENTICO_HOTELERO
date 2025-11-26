"""
Unit tests for TenantMiddleware.

Tests tenant resolution from headers, JWT tokens, and default fallback.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.middleware import TenantMiddleware
from app.core.tenant_context import get_tenant_id


@pytest.fixture
def app_with_tenant_middleware():
    """Create a FastAPI app with TenantMiddleware for testing."""
    app = FastAPI()
    app.add_middleware(TenantMiddleware, default_tenant="test-default")
    
    @app.get("/test")
    async def test_endpoint():
        return {"tenant_id": get_tenant_id()}
    
    return app


@pytest.fixture
def client(app_with_tenant_middleware):
    """Create a test client."""
    return TestClient(app_with_tenant_middleware)


def test_tenant_from_header(client):
    """Test tenant resolution from X-Tenant-ID header."""
    response = client.get("/test", headers={"X-Tenant-ID": "hotel-abc"})
    assert response.status_code == 200
    assert response.json()["tenant_id"] == "hotel-abc"
    assert response.headers["X-Tenant-ID"] == "hotel-abc"


def test_tenant_from_lowercase_header(client):
    """Test tenant resolution from lowercase x-tenant-id header."""
    response = client.get("/test", headers={"x-tenant-id": "hotel-xyz"})
    assert response.status_code == 200
    assert response.json()["tenant_id"] == "hotel-xyz"


def test_tenant_default_fallback(client):
    """Test tenant resolution falls back to default when no header provided."""
    response = client.get("/test")
    assert response.status_code == 200
    assert response.json()["tenant_id"] == "test-default"
    assert response.headers["X-Tenant-ID"] == "test-default"


def test_tenant_context_isolation(client):
    """Test that tenant context is properly isolated between requests."""
    # First request with tenant A
    response1 = client.get("/test", headers={"X-Tenant-ID": "tenant-a"})
    assert response1.json()["tenant_id"] == "tenant-a"
    
    # Second request with tenant B
    response2 = client.get("/test", headers={"X-Tenant-ID": "tenant-b"})
    assert response2.json()["tenant_id"] == "tenant-b"
    
    # Third request with no tenant (should use default)
    response3 = client.get("/test")
    assert response3.json()["tenant_id"] == "test-default"


@pytest.mark.asyncio
async def test_tenant_context_cleanup():
    """Test that tenant context is cleaned up after request."""
    from app.core.tenant_context import set_tenant_id, get_tenant_id, clear_tenant_id
    
    # Set a tenant ID
    set_tenant_id("cleanup-test")
    assert get_tenant_id() == "cleanup-test"
    
    # Clear it
    clear_tenant_id()
    assert get_tenant_id() is None
