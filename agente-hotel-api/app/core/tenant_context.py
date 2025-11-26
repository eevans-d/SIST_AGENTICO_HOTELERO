"""
Tenant context management for multi-tenancy support.

This module provides a context variable to store the current tenant ID
for the request lifecycle, accessible throughout the application.
"""

from contextvars import ContextVar
from typing import Optional

# Context variable to store the current tenant ID
_tenant_id_context: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)


def set_tenant_id(tenant_id: Optional[str]) -> None:
    """Set the tenant ID for the current context."""
    _tenant_id_context.set(tenant_id)


def get_tenant_id() -> Optional[str]:
    """Get the tenant ID from the current context."""
    return _tenant_id_context.get()


def clear_tenant_id() -> None:
    """Clear the tenant ID from the current context."""
    _tenant_id_context.set(None)
