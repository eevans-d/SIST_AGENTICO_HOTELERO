"""
Unit tests for core tenant_context module (contextvars).

Tests for context variable management functions in app/core/tenant_context.py.
"""

import pytest
from app.core.tenant_context import (
    set_tenant_id,
    get_tenant_id,
    clear_tenant_id,
    reset_tenant_id,
)


class TestCoreTenantContext:
    """Tests for core tenant context management using contextvars."""

    def test_set_and_get_tenant_id(self):
        """Test setting and getting tenant ID."""
        token = set_tenant_id("hotel-123")
        assert get_tenant_id() == "hotel-123"
        reset_tenant_id(token)

    def test_get_tenant_id_default_none(self):
        """Test get_tenant_id returns None when not set."""
        # Clear any existing context first
        clear_tenant_id()
        assert get_tenant_id() is None

    def test_clear_tenant_id(self):
        """Test clearing tenant ID."""
        token = set_tenant_id("hotel-456")
        assert get_tenant_id() == "hotel-456"
        clear_tenant_id()
        assert get_tenant_id() is None

    def test_reset_tenant_id_restores_previous(self):
        """Test reset_tenant_id restores previous context."""
        # Set initial value
        token1 = set_tenant_id("hotel-original")
        assert get_tenant_id() == "hotel-original"
        
        # Set new value
        token2 = set_tenant_id("hotel-new")
        assert get_tenant_id() == "hotel-new"
        
        # Reset to previous
        reset_tenant_id(token2)
        assert get_tenant_id() == "hotel-original"
        
        # Clean up
        reset_tenant_id(token1)

    def test_set_tenant_id_with_none(self):
        """Test setting tenant ID to None explicitly."""
        token = set_tenant_id(None)
        assert get_tenant_id() is None
        reset_tenant_id(token)

    def test_multiple_set_operations(self):
        """Test multiple sequential set operations."""
        token1 = set_tenant_id("tenant-a")
        assert get_tenant_id() == "tenant-a"
        
        token2 = set_tenant_id("tenant-b")
        assert get_tenant_id() == "tenant-b"
        
        token3 = set_tenant_id("tenant-c")
        assert get_tenant_id() == "tenant-c"
        
        # Reset in reverse order
        reset_tenant_id(token3)
        assert get_tenant_id() == "tenant-b"
        
        reset_tenant_id(token2)
        assert get_tenant_id() == "tenant-a"
        
        reset_tenant_id(token1)

    def test_tenant_id_isolation_in_same_thread(self):
        """Test tenant ID changes are isolated within context."""
        # Start clean
        clear_tenant_id()
        assert get_tenant_id() is None
        
        # Set and verify
        token = set_tenant_id("isolated-tenant")
        assert get_tenant_id() == "isolated-tenant"
        
        # Clean up
        reset_tenant_id(token)
