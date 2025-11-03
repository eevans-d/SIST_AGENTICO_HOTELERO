"""
Admin API Pydantic Schemas
==========================

Type-safe schemas for admin endpoints to prevent SQL injection and ensure validation.

Author: Backend AI Team
Date: 2025-11-03
"""

from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re


# ============================================================
# TENANT MANAGEMENT SCHEMAS
# ============================================================

class TenantCreateSchema(BaseModel):
    """Schema for creating a new tenant"""
    tenant_id: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Unique tenant identifier (slug format)"
    )
    name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Tenant display name"
    )
    status: Literal["active", "inactive"] = Field(
        default="active",
        description="Tenant status"
    )
    business_hours_start: Optional[int] = Field(
        default=None,
        ge=0,
        le=23,
        description="Business hours start (0-23)"
    )
    business_hours_end: Optional[int] = Field(
        default=None,
        ge=0,
        le=23,
        description="Business hours end (0-23)"
    )
    business_hours_timezone: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Timezone for business hours"
    )

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id_format(cls, v: str) -> str:
        """Validate tenant_id is alphanumeric with hyphens/underscores only"""
        if not re.match(r"^[a-z0-9_-]+$", v):
            raise ValueError("tenant_id must be lowercase alphanumeric with hyphens/underscores only")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenant_id": "hotel-plaza-2025",
                "name": "Hotel Plaza",
                "status": "active",
                "business_hours_start": 8,
                "business_hours_end": 22,
                "business_hours_timezone": "America/Argentina/Buenos_Aires"
            }
        }
    )


class TenantUpdateSchema(BaseModel):
    """Schema for updating tenant properties"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    status: Optional[Literal["active", "inactive"]] = None
    business_hours_start: Optional[int] = Field(None, ge=0, le=23)
    business_hours_end: Optional[int] = Field(None, ge=0, le=23)
    business_hours_timezone: Optional[str] = Field(None, max_length=50)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Hotel Plaza Updated",
                "status": "active",
                "business_hours_start": 9
            }
        }
    )


class TenantIdentifierCreateSchema(BaseModel):
    """Schema for adding identifier to tenant"""
    identifier: str = Field(
        ...,
        min_length=5,
        max_length=100,
        description="User identifier (phone, email, etc.)"
    )

    @field_validator("identifier")
    @classmethod
    def validate_identifier_format(cls, v: str) -> str:
        """Validate identifier is phone or email format"""
        # Phone: +5491112345678 or email: user@example.com
        phone_pattern = r"^\+?[1-9]\d{1,14}$"  # E.164 format
        email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

        if not (re.match(phone_pattern, v) or re.match(email_pattern, v)):
            raise ValueError("identifier must be valid phone (E.164) or email format")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "identifier": "+5491112345678"
            }
        }
    )


# ============================================================
# FEATURE FLAG SCHEMAS
# ============================================================

class FeatureFlagUpdateSchema(BaseModel):
    """Schema for updating feature flags"""
    flag_key: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Feature flag key (dot notation)"
    )
    enabled: bool = Field(
        ...,
        description="Whether flag is enabled"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Flag description"
    )

    @field_validator("flag_key")
    @classmethod
    def validate_flag_key_format(cls, v: str) -> str:
        """Validate flag key uses dot notation"""
        if not re.match(r"^[a-z0-9_.]+$", v):
            raise ValueError("flag_key must be lowercase alphanumeric with dots/underscores")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "flag_key": "nlp.fallback.enhanced",
                "enabled": True,
                "description": "Enable enhanced NLP fallback responses"
            }
        }
    )


class ConfigUpdateSchema(BaseModel):
    """Schema for updating system configuration"""
    config_key: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Configuration key"
    )
    config_value: str = Field(
        ...,
        max_length=1000,
        description="Configuration value"
    )
    config_type: Literal["string", "int", "float", "bool", "json"] = Field(
        default="string",
        description="Value type for parsing"
    )

    @field_validator("config_key")
    @classmethod
    def validate_config_key_format(cls, v: str) -> str:
        """Validate config key format"""
        if not re.match(r"^[A-Z0-9_]+$", v):
            raise ValueError("config_key must be uppercase alphanumeric with underscores")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "config_key": "MAX_AUDIO_CACHE_SIZE_MB",
                "config_value": "500",
                "config_type": "int"
            }
        }
    )


# ============================================================
# REVIEW MANAGEMENT SCHEMAS
# ============================================================

class ReviewRequestSchema(BaseModel):
    """Schema for sending review request"""
    guest_id: str = Field(
        ...,
        min_length=5,
        max_length=100,
        description="Guest identifier (phone/email)"
    )
    force_send: bool = Field(
        default=False,
        description="Force send even if already sent recently"
    )

    @field_validator("guest_id")
    @classmethod
    def validate_guest_id_format(cls, v: str) -> str:
        """Validate guest_id is phone or email"""
        phone_pattern = r"^\+?[1-9]\d{1,14}$"
        email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

        if not (re.match(phone_pattern, v) or re.match(email_pattern, v)):
            raise ValueError("guest_id must be valid phone or email format")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "guest_id": "+5491112345678",
                "force_send": False
            }
        }
    )


class ReviewScheduleSchema(BaseModel):
    """Schema for scheduling review request"""
    guest_id: str = Field(..., min_length=5, max_length=100)
    guest_name: str = Field(..., min_length=2, max_length=200)
    booking_id: str = Field(..., min_length=3, max_length=50)
    checkout_date: datetime = Field(..., description="Checkout date ISO8601")
    segment: Literal["couple", "business", "family", "solo", "group", "vip"] = Field(
        default="couple",
        description="Guest segment for personalization"
    )
    language: Literal["es", "en", "pt"] = Field(
        default="es",
        description="Message language"
    )

    @field_validator("guest_id")
    @classmethod
    def validate_guest_id(cls, v: str) -> str:
        phone_pattern = r"^\+?[1-9]\d{1,14}$"
        email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not (re.match(phone_pattern, v) or re.match(email_pattern, v)):
            raise ValueError("guest_id must be valid phone or email")
        return v

    @field_validator("booking_id")
    @classmethod
    def validate_booking_id(cls, v: str) -> str:
        """Validate booking_id format"""
        if not re.match(r"^[A-Z0-9-]+$", v):
            raise ValueError("booking_id must be alphanumeric with hyphens")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "guest_id": "+5491112345678",
                "guest_name": "Juan Pérez",
                "booking_id": "HTL-001",
                "checkout_date": "2025-01-10T12:00:00Z",
                "segment": "couple",
                "language": "es"
            }
        }
    )


class ReviewMarkSubmittedSchema(BaseModel):
    """Schema for marking review as submitted"""
    booking_id: str = Field(..., min_length=3, max_length=50)
    guest_id: str = Field(..., min_length=5, max_length=100)

    @field_validator("booking_id")
    @classmethod
    def validate_booking_id(cls, v: str) -> str:
        if not re.match(r"^[A-Z0-9-]+$", v):
            raise ValueError("booking_id must be alphanumeric with hyphens")
        return v

    @field_validator("guest_id")
    @classmethod
    def validate_guest_id(cls, v: str) -> str:
        phone_pattern = r"^\+?[1-9]\d{1,14}$"
        email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not (re.match(phone_pattern, v) or re.match(email_pattern, v)):
            raise ValueError("guest_id must be valid phone or email")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "booking_id": "HTL-001",
                "guest_id": "+5491112345678"
            }
        }
    )


# ============================================================
# USER MANAGEMENT SCHEMAS
# ============================================================

class UserCreateSchema(BaseModel):
    """Schema for creating new user"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=12, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)
    tenant_id: Optional[str] = Field(None, max_length=50)
    is_superuser: bool = Field(default=False)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9_-]+$", v):
            raise ValueError("username must be lowercase alphanumeric with underscores/hyphens")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        return v.lower()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "admin_user",
                "email": "admin@hotelplaza.com",
                "password": "SecureP@ssw0rd123",
                "full_name": "Admin User",
                "tenant_id": "hotel-plaza-2025",
                "is_superuser": False
            }
        }
    )


class UserUpdateSchema(BaseModel):
    """Schema for updating user"""
    email: Optional[str] = Field(None, min_length=5, max_length=255)
    full_name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        return v.lower()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "newemail@hotelplaza.com",
                "full_name": "Updated Name",
                "is_active": True
            }
        }
    )


# ============================================================
# SESSION MANAGEMENT SCHEMAS
# ============================================================

class SessionCleanupSchema(BaseModel):
    """Schema for session cleanup filters"""
    older_than_hours: Optional[int] = Field(
        default=24,
        ge=1,
        le=720,  # Max 30 days
        description="Delete sessions older than N hours"
    )
    tenant_id: Optional[str] = Field(
        None,
        max_length=50,
        description="Filter by tenant"
    )
    only_expired: bool = Field(
        default=True,
        description="Only delete expired sessions"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "older_than_hours": 48,
                "tenant_id": "hotel-plaza-2025",
                "only_expired": True
            }
        }
    )


# ============================================================
# LOCK MANAGEMENT SCHEMAS
# ============================================================

class LockForceReleaseSchema(BaseModel):
    """Schema for forcing lock release"""
    room_id: str = Field(..., min_length=1, max_length=50)
    reason: str = Field(..., min_length=10, max_length=500)

    @field_validator("room_id")
    @classmethod
    def validate_room_id(cls, v: str) -> str:
        if not re.match(r"^[A-Z0-9-]+$", v):
            raise ValueError("room_id must be alphanumeric with hyphens")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "room_id": "ROOM-101",
                "reason": "Emergency manual release due to payment system failure"
            }
        }
    )


# ============================================================
# BULK OPERATION SCHEMAS
# ============================================================

class BulkTenantIdentifierCreateSchema(BaseModel):
    """Schema for bulk adding identifiers"""
    tenant_id: str = Field(..., min_length=2, max_length=50)
    identifiers: List[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of identifiers to add"
    )

    @field_validator("identifiers")
    @classmethod
    def validate_identifiers(cls, v: List[str]) -> List[str]:
        phone_pattern = r"^\+?[1-9]\d{1,14}$"
        email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

        for identifier in v:
            if not (re.match(phone_pattern, identifier) or re.match(email_pattern, identifier)):
                raise ValueError(f"Invalid identifier format: {identifier}")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenant_id": "hotel-plaza-2025",
                "identifiers": ["+5491112345678", "+5491198765432", "guest@example.com"]
            }
        }
    )
