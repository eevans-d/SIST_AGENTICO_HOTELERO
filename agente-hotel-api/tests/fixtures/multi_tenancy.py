"""
Fixtures centralizadas para multi-tenancy testing.

Este módulo proporciona fixtures reutilizables para tests que requieren
validación de aislamiento de datos por tenant_id.
"""

import pytest
import pytest_asyncio
from typing import Dict, Any


# Tenant IDs de prueba
TEST_TENANT_A = "hotel-test-a"
TEST_TENANT_B = "hotel-test-b"
TEST_TENANT_DEFAULT = "hotel-default"


@pytest.fixture
def tenant_a_id() -> str:
    """Fixture que retorna el ID del tenant A para tests."""
    return TEST_TENANT_A


@pytest.fixture
def tenant_b_id() -> str:
    """Fixture que retorna el ID del tenant B para tests."""
    return TEST_TENANT_B


@pytest.fixture
def default_tenant_id() -> str:
    """Fixture que retorna el ID del tenant por defecto."""
    return TEST_TENANT_DEFAULT


@pytest.fixture
def tenant_a_user() -> Dict[str, Any]:
    """
    Fixture que retorna datos de usuario del tenant A.
    
    Returns:
        dict: Datos del usuario incluyendo tenant_id, user_id, channel
    """
    return {
        "tenant_id": TEST_TENANT_A,
        "user_id": "+34600111222",
        "channel": "whatsapp",
        "name": "Test User A",
    }


@pytest.fixture
def tenant_b_user() -> Dict[str, Any]:
    """
    Fixture que retorna datos de usuario del tenant B.
    
    Returns:
        dict: Datos del usuario incluyendo tenant_id, user_id, channel
    """
    return {
        "tenant_id": TEST_TENANT_B,
        "user_id": "+34600333444",
        "channel": "whatsapp",
        "name": "Test User B",
    }


@pytest.fixture
def audit_log_data_tenant_a(tenant_a_id: str, tenant_a_user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fixture que retorna datos de audit log para tenant A.
    
    Args:
        tenant_a_id: ID del tenant A
        tenant_a_user: Datos del usuario del tenant A
        
    Returns:
        dict: Datos para crear un AuditLog del tenant A
    """
    return {
        "event_type": "reservation_created",
        "user_id": tenant_a_user["user_id"],
        "ip_address": "192.168.1.100",
        "resource": "/api/reservations/123",
        "details": {"booking_id": "HTL-A-123", "room_type": "double"},
        "tenant_id": tenant_a_id,
        "severity": "info",
    }


@pytest.fixture
def audit_log_data_tenant_b(tenant_b_id: str, tenant_b_user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fixture que retorna datos de audit log para tenant B.
    
    Args:
        tenant_b_id: ID del tenant B
        tenant_b_user: Datos del usuario del tenant B
        
    Returns:
        dict: Datos para crear un AuditLog del tenant B
    """
    return {
        "event_type": "reservation_created",
        "user_id": tenant_b_user["user_id"],
        "ip_address": "192.168.1.101",
        "resource": "/api/reservations/456",
        "details": {"booking_id": "HTL-B-456", "room_type": "suite"},
        "tenant_id": tenant_b_id,
        "severity": "info",
    }


@pytest.fixture
def dlq_entry_data_tenant_a(tenant_a_id: str) -> Dict[str, Any]:
    """
    Fixture que retorna datos de DLQ entry para tenant A.
    
    Args:
        tenant_a_id: ID del tenant A
        
    Returns:
        dict: Datos para crear un DLQEntry del tenant A
    """
    from datetime import datetime
    return {
        "id": "dlq-a-001",
        "message_data": {"intent": "check_availability", "user_id": "+34600111222"},
        "error_message": "PMS connection timeout",
        "error_type": "ConnectionTimeoutError",
        "retry_count": 3,
        "first_failed_at": datetime.utcnow(),
        "tenant_id": tenant_a_id,
    }


@pytest.fixture
def dlq_entry_data_tenant_b(tenant_b_id: str) -> Dict[str, Any]:
    """
    Fixture que retorna datos de DLQ entry para tenant B.
    
    Args:
        tenant_b_id: ID del tenant B
        
    Returns:
        dict: Datos para crear un DLQEntry del tenant B
    """
    from datetime import datetime
    return {
        "id": "dlq-b-001",
        "message_data": {"intent": "check_availability", "user_id": "+34600333444"},
        "error_message": "PMS connection timeout",
        "error_type": "ConnectionTimeoutError",
        "retry_count": 3,
        "first_failed_at": datetime.utcnow(),
        "tenant_id": tenant_b_id,
    }


@pytest.fixture
def lock_audit_data_tenant_a(tenant_a_id: str) -> Dict[str, Any]:
    """
    Fixture que retorna datos de lock audit para tenant A.
    
    Args:
        tenant_a_id: ID del tenant A
        
    Returns:
        dict: Datos para crear un LockAudit del tenant A
    """
    return {
        "lock_key": "reservation:123",
        "event_type": "lock_acquired",
        "details": {"holder": "worker-1", "ttl": 30},
        "tenant_id": tenant_a_id,
    }


@pytest.fixture
def lock_audit_data_tenant_b(tenant_b_id: str) -> Dict[str, Any]:
    """
    Fixture que retorna datos de lock audit para tenant B.
    
    Args:
        tenant_b_id: ID del tenant B
        
    Returns:
        dict: Datos para crear un LockAudit del tenant B
    """
    return {
        "lock_key": "reservation:456",
        "event_type": "lock_acquired",
        "details": {"holder": "worker-2", "ttl": 30},
        "tenant_id": tenant_b_id,
    }


@pytest_asyncio.fixture
async def create_test_tenants_in_db(tenant_a_id: str, tenant_b_id: str):
    """
    Fixture que crea tenants de prueba en la base de datos.
    
    Esta fixture es útil para tests de integración que requieren
    tenants reales en la BD.
    
    Args:
        tenant_a_id: ID del tenant A
        tenant_b_id: ID del tenant B
        
    Yields:
        dict: Diccionario con los IDs de los tenants creados
    """
    from app.core.database import get_db
    from app.models.tenant import Tenant
    
    async for db in get_db():
        # Crear tenant A
        tenant_a = Tenant(tenant_id=tenant_a_id, name="Hotel Test A", status="active")
        db.add(tenant_a)
        
        # Crear tenant B
        tenant_b = Tenant(tenant_id=tenant_b_id, name="Hotel Test B", status="active")
        db.add(tenant_b)
        
        await db.commit()
        
        yield {"tenant_a": tenant_a_id, "tenant_b": tenant_b_id}
        
        # Cleanup
        await db.delete(tenant_a)
        await db.delete(tenant_b)
        await db.commit()
