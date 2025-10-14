"""
Webhook Schema Validation
Strict Pydantic models for webhook payload validation
"""

from pydantic import BaseModel, Field, validator
from typing import Literal, Any
from datetime import datetime


class WhatsAppMessageValue(BaseModel):
    """WhatsApp message value structure."""

    messaging_product: Literal["whatsapp"] = "whatsapp"
    messages: list[dict] = Field(..., min_items=1, max_items=10)
    contacts: list[dict] | None = None

    @validator("messages")
    def validate_messages_structure(cls, v):
        """Ensure each message has required fields."""
        for msg in v:
            if "from" not in msg:
                raise ValueError("Message missing 'from' field")
            if not any(k in msg for k in ["text", "audio", "image", "document"]):
                raise ValueError("Message missing content type")
        return v


class WhatsAppChange(BaseModel):
    """WhatsApp change structure."""

    value: WhatsAppMessageValue
    field: Literal["messages"] = "messages"


class WhatsAppEntry(BaseModel):
    """WhatsApp entry structure."""

    id: str
    changes: list[WhatsAppChange] = Field(..., min_items=1, max_items=5)


class WhatsAppWebhookPayload(BaseModel):
    """
    Strict validation for WhatsApp webhook payload.

    Rejects any unknown fields and validates structure.
    """

    object: Literal["whatsapp_business_account"]
    entry: list[WhatsAppEntry] = Field(..., min_items=1, max_items=10)

    class Config:
        extra = "forbid"  # Reject unknown fields for security


class GmailWebhookPayload(BaseModel):
    """
    Strict validation for Gmail webhook payload.
    """

    message: dict = Field(..., description="Gmail push notification message")
    subscription: str = Field(..., min_length=1, max_length=500)

    @validator("message")
    def validate_message_structure(cls, v):
        """Ensure message has data and messageId."""
        if "data" not in v:
            raise ValueError("Message missing 'data' field")
        if "messageId" not in v:
            raise ValueError("Message missing 'messageId' field")
        return v

    class Config:
        extra = "forbid"


class ReservationPayload(BaseModel):
    """
    Strict validation for reservation data.

    Validates dates, guest count, and data consistency.
    """

    checkin: str = Field(..., regex=r"^\d{4}-\d{2}-\d{2}$", description="Check-in date in YYYY-MM-DD format")
    checkout: str = Field(..., regex=r"^\d{4}-\d{2}-\d{2}$", description="Check-out date in YYYY-MM-DD format")
    guests: int = Field(..., ge=1, le=10, description="Number of guests (1-10)")
    room_type: str = Field(..., min_length=1, max_length=50)
    guest_name: str | None = Field(None, min_length=1, max_length=200)
    guest_email: str | None = Field(None, regex=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    guest_phone: str | None = Field(None, regex=r"^\+?[1-9]\d{1,14}$")

    @validator("checkout")
    def checkout_after_checkin(cls, v, values):
        """Ensure checkout is after checkin."""
        if "checkin" in values:
            checkin_date = datetime.strptime(values["checkin"], "%Y-%m-%d")
            checkout_date = datetime.strptime(v, "%Y-%m-%d")

            if checkout_date <= checkin_date:
                raise ValueError("checkout must be after checkin")

            # Validate reasonable stay length (max 30 days)
            nights = (checkout_date - checkin_date).days
            if nights > 30:
                raise ValueError("Stay length cannot exceed 30 nights")

        return v

    @validator("checkin")
    def checkin_not_in_past(cls, v):
        """Ensure checkin is not in the past."""
        checkin_date = datetime.strptime(v, "%Y-%m-%d")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if checkin_date < today:
            raise ValueError("checkin date cannot be in the past")

        return v

    class Config:
        extra = "forbid"


class AvailabilityQuery(BaseModel):
    """
    Validation for availability check query.
    """

    checkin: str = Field(..., regex=r"^\d{4}-\d{2}-\d{2}$")
    checkout: str = Field(..., regex=r"^\d{4}-\d{2}-\d{2}$")
    guests: int = Field(..., ge=1, le=10)
    room_type: str | None = Field(None, min_length=1, max_length=50)

    @validator("checkout")
    def checkout_after_checkin(cls, v, values):
        if "checkin" in values and v <= values["checkin"]:
            raise ValueError("checkout must be after checkin")
        return v

    class Config:
        extra = "forbid"


class TenantCreatePayload(BaseModel):
    """
    Validation for tenant creation.
    """

    name: str = Field(..., min_length=1, max_length=200)
    config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

    @validator("name")
    def name_alphanumeric(cls, v):
        """Ensure tenant name is alphanumeric with spaces/hyphens only."""
        if not all(c.isalnum() or c in " -_" for c in v):
            raise ValueError("Tenant name must be alphanumeric with spaces, hyphens, or underscores only")
        return v

    class Config:
        extra = "forbid"


class WebhookVerification(BaseModel):
    """
    Validation for webhook verification (GET request).
    """

    hub_mode: str = Field(..., alias="hub.mode")
    hub_verify_token: str = Field(..., alias="hub.verify_token")
    hub_challenge: str = Field(..., alias="hub.challenge")

    @validator("hub_mode")
    def mode_must_be_subscribe(cls, v):
        if v != "subscribe":
            raise ValueError("hub.mode must be 'subscribe'")
        return v

    class Config:
        populate_by_name = True
