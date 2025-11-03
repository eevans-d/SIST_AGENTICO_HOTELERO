"""
Tests for Admin Pydantic Schemas
=================================

Validates schema validation logic and security (SQL injection prevention).

Author: Backend AI Team
Date: 2025-11-03
"""

import pytest
from pydantic import ValidationError

from app.models.admin_schemas import (
    TenantCreateSchema,
    TenantUpdateSchema,
    TenantIdentifierCreateSchema,
    ReviewRequestSchema,
    ReviewScheduleSchema,
    ReviewMarkSubmittedSchema,
    UserCreateSchema,
    UserUpdateSchema,
)


class TestTenantSchemas:
    """Test tenant management schemas"""

    def test_tenant_create_valid(self):
        """Test valid tenant creation"""
        data = {
            "tenant_id": "hotel-plaza-2025",
            "name": "Hotel Plaza",
            "status": "active"
        }
        schema = TenantCreateSchema(**data)
        assert schema.tenant_id == "hotel-plaza-2025"
        assert schema.name == "Hotel Plaza"
        assert schema.status == "active"

    def test_tenant_create_invalid_tenant_id(self):
        """Test that uppercase tenant_id is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            TenantCreateSchema(
                tenant_id="HOTEL-PLAZA",  # Uppercase not allowed
                name="Hotel Plaza"
            )

        errors = exc_info.value.errors()
        assert any("lowercase" in str(e) for e in errors)

    def test_tenant_create_sql_injection_prevention(self):
        """Test SQL injection attempt in tenant_id"""
        with pytest.raises(ValidationError):
            TenantCreateSchema(
                tenant_id="hotel'; DROP TABLE tenants;--",
                name="Hotel"
            )

    def test_tenant_update_partial(self):
        """Test partial update of tenant"""
        schema = TenantUpdateSchema(name="Updated Name")
        assert schema.name == "Updated Name"
        assert schema.status is None

    def test_tenant_identifier_valid_phone(self):
        """Test valid phone identifier"""
        schema = TenantIdentifierCreateSchema(identifier="+5491112345678")
        assert schema.identifier == "+5491112345678"

    def test_tenant_identifier_valid_email(self):
        """Test valid email identifier"""
        schema = TenantIdentifierCreateSchema(identifier="guest@hotel.com")
        assert schema.identifier == "guest@hotel.com"

    def test_tenant_identifier_invalid(self):
        """Test invalid identifier format"""
        with pytest.raises(ValidationError) as exc_info:
            TenantIdentifierCreateSchema(identifier="invalid-format")

        errors = exc_info.value.errors()
        assert any("phone" in str(e) or "email" in str(e) for e in errors)


class TestReviewSchemas:
    """Test review management schemas"""

    def test_review_request_valid(self):
        """Test valid review request"""
        schema = ReviewRequestSchema(
            guest_id="+5491112345678",
            force_send=False
        )
        assert schema.guest_id == "+5491112345678"
        assert schema.force_send is False

    def test_review_request_sql_injection_prevention(self):
        """Test SQL injection in guest_id"""
        with pytest.raises(ValidationError):
            ReviewRequestSchema(
                guest_id="123'; DELETE FROM reviews;--"
            )

    def test_review_schedule_valid(self):
        """Test valid review schedule"""
        from datetime import datetime

        schema = ReviewScheduleSchema(
            guest_id="+5491112345678",
            guest_name="Juan Pérez",
            booking_id="HTL-001",
            checkout_date=datetime(2025, 1, 10, 12, 0, 0),
            segment="couple",
            language="es"
        )
        assert schema.guest_id == "+5491112345678"
        assert schema.segment == "couple"
        assert schema.language == "es"

    def test_review_schedule_invalid_segment(self):
        """Test invalid guest segment"""
        from datetime import datetime

        with pytest.raises(ValidationError) as exc_info:
            ReviewScheduleSchema(
                guest_id="+5491112345678",
                guest_name="Juan Pérez",
                booking_id="HTL-001",
                checkout_date=datetime(2025, 1, 10),
                segment="invalid_segment",  # Not in enum
                language="es"
            )

        errors = exc_info.value.errors()
        assert any("segment" in str(e) for e in errors)

    def test_review_schedule_invalid_booking_id(self):
        """Test SQL injection in booking_id"""
        from datetime import datetime

        with pytest.raises(ValidationError):
            ReviewScheduleSchema(
                guest_id="+5491112345678",
                guest_name="Juan Pérez",
                booking_id="HTL'; DROP TABLE bookings;--",
                checkout_date=datetime(2025, 1, 10),
                segment="couple",
                language="es"
            )

    def test_review_mark_submitted_valid(self):
        """Test valid mark submitted"""
        schema = ReviewMarkSubmittedSchema(
            booking_id="HTL-001",
            guest_id="+5491112345678"
        )
        assert schema.booking_id == "HTL-001"


class TestUserSchemas:
    """Test user management schemas"""

    def test_user_create_valid(self):
        """Test valid user creation"""
        schema = UserCreateSchema(
            username="admin_user",
            email="admin@hotel.com",
            password="SecureP@ssw0rd123",
            full_name="Admin User",
            tenant_id="hotel-plaza-2025"
        )
        assert schema.username == "admin_user"
        assert schema.email == "admin@hotel.com"
        assert schema.is_superuser is False

    def test_user_create_email_normalized(self):
        """Test that email is normalized to lowercase"""
        schema = UserCreateSchema(
            username="user1",
            email="USER@HOTEL.COM",
            password="SecureP@ssw0rd123"
        )
        assert schema.email == "user@hotel.com"

    def test_user_create_invalid_username(self):
        """Test SQL injection in username"""
        with pytest.raises(ValidationError):
            UserCreateSchema(
                username="admin'; DROP TABLE users;--",
                email="admin@hotel.com",
                password="SecureP@ssw0rd123"
            )

    def test_user_create_weak_password(self):
        """Test password length validation"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreateSchema(
                username="user1",
                email="user@hotel.com",
                password="short"  # Too short
            )

        errors = exc_info.value.errors()
        assert any("12" in str(e) for e in errors)

    def test_user_update_partial(self):
        """Test partial user update"""
        schema = UserUpdateSchema(
            email="newemail@hotel.com",
            is_active=False
        )
        assert schema.email == "newemail@hotel.com"
        assert schema.is_active is False
        assert schema.full_name is None


class TestSecurityValidation:
    """Test security validations across all schemas"""

    def test_script_tags_allowed_but_sanitized_at_api_level(self):
        """
        Test that schema accepts HTML (Pydantic doesn't sanitize by default).

        NOTE: XSS prevention happens at API level via:
        1. Content-Type headers (application/json)
        2. Response escaping in frontend
        3. CSP headers

        Pydantic focuses on type/format validation, not content sanitization.
        """
        schema = TenantCreateSchema(
            tenant_id="hotel-test",
            name="<script>alert('xss')</script>"
        )
        # Schema accepts it - API layer must sanitize before rendering
        assert "<script>" in schema.name

    def test_max_length_enforcement(self):
        """Test that max lengths are enforced"""
        with pytest.raises(ValidationError):
            TenantCreateSchema(
                tenant_id="a" * 100,  # Exceeds max_length
                name="Hotel"
            )

    def test_required_fields_validation(self):
        """Test that required fields cannot be omitted"""
        with pytest.raises(ValidationError):
            TenantCreateSchema(name="Hotel")  # Missing tenant_id

    def test_enum_validation(self):
        """Test enum validation"""
        with pytest.raises(ValidationError):
            TenantCreateSchema(
                tenant_id="hotel-test",
                name="Hotel",
                status="invalid_status"  # Not in Literal
            )
