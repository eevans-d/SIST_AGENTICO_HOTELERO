import pytest

from app.services.tenant_context import tenant_context_service, TenantContextService


def test_resolve_known_user():
    t = tenant_context_service.resolve_tenant("+5491112345678")
    assert t == "hotel_centro"


def test_resolve_unknown_user_default():
    t = tenant_context_service.resolve_tenant("+549000000000")
    assert t == "default"


def test_strict_mode_returns_none():
    svc = TenantContextService(strict_mode=True)
    assert svc.resolve_tenant("+549000000000") is None


def test_validate_tenant():
    assert tenant_context_service.validate_tenant("hotel_centro") is True
    assert tenant_context_service.validate_tenant("default") is True
    assert tenant_context_service.validate_tenant("otro") is False