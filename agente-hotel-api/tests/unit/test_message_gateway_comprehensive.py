# [MEGA PLAN FASE 3] tests/unit/test_message_gateway_comprehensive.py
"""
Comprehensive tests for MessageGateway service.
Target: 60-70% coverage for message_gateway.py

Test Categories:
1. WhatsApp Normalization (8 tests)
2. Gmail Normalization (6 tests)
3. Security Validations (10 tests)
4. Metadata Filtering (6 tests)
5. Tenant Resolution (5 tests)
6. Edge Cases & Error Handling (5 tests)
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

from app.services.message_gateway import (
    MessageGateway,
    MessageNormalizationError,
    TenantIsolationError,
    ALLOWED_METADATA_KEYS,
)
from app.exceptions.pms_exceptions import ChannelSpoofingError


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def gateway():
    """Provide a fresh MessageGateway instance."""
    return MessageGateway()


@pytest.fixture
def valid_whatsapp_payload():
    """Valid WhatsApp webhook payload structure."""
    return {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "id": "wamid.123456789",
                        "from": "5215512345678",
                        "timestamp": "1732800000",
                        "type": "text",
                        "text": {"body": "Quiero reservar una habitación"}
                    }],
                    "contacts": [{
                        "wa_id": "5215512345678",
                        "profile": {"name": "Guest User"}
                    }]
                }
            }]
        }]
    }


@pytest.fixture
def valid_gmail_payload():
    """Valid Gmail email dictionary."""
    return {
        "message_id": "msg_12345",
        "from": "guest@example.com",
        "subject": "Room Reservation Inquiry",
        "body": "I would like to book a room for next week.",
        "timestamp": "2025-11-28T10:00:00Z"
    }


# ============================================================================
# 1. WhatsApp Normalization (8 tests)
# ============================================================================

class TestWhatsAppNormalization:
    """Tests for WhatsApp webhook payload normalization."""

    def test_normalize_valid_text_message(self, gateway, valid_whatsapp_payload):
        """Test normalizing a valid text message."""
        with patch.object(gateway, "_resolve_tenant", return_value="default"):
            unified = gateway.normalize_whatsapp_message(valid_whatsapp_payload)
        
        assert unified.message_id == "wamid.123456789"
        assert unified.canal == "whatsapp"
        assert unified.user_id == "5215512345678"
        assert unified.tipo == "text"
        assert unified.texto == "Quiero reservar una habitación"
        assert unified.tenant_id == "default"

    def test_normalize_audio_message(self, gateway):
        """Test normalizing an audio message."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "wamid.audio123",
                            "from": "5215512345678",
                            "timestamp": "1732800000",
                            "type": "audio",
                            "audio": {"id": "audio_media_id"}
                        }],
                        "contacts": []
                    }
                }]
            }]
        }
        
        with patch.object(gateway, "_resolve_tenant", return_value="default"):
            unified = gateway.normalize_whatsapp_message(payload)
        
        assert unified.tipo == "audio"
        assert unified.texto is None

    def test_normalize_missing_entry_raises(self, gateway):
        """Test that missing entry raises error."""
        with pytest.raises(MessageNormalizationError) as exc:
            gateway.normalize_whatsapp_message({})
        
        assert "missing_entry" in str(exc.value)

    def test_normalize_missing_changes_raises(self, gateway):
        """Test that missing changes raises error."""
        payload = {"entry": [{}]}
        
        with pytest.raises(MessageNormalizationError) as exc:
            gateway.normalize_whatsapp_message(payload)
        
        assert "missing_changes" in str(exc.value)

    def test_normalize_missing_messages_raises(self, gateway):
        """Test that missing messages raises error."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {"messages": []}
                }]
            }]
        }
        
        with pytest.raises(MessageNormalizationError) as exc:
            gateway.normalize_whatsapp_message(payload)
        
        assert "missing_messages" in str(exc.value)

    def test_normalize_empty_payload(self, gateway):
        """Test normalizing empty/None payload."""
        with pytest.raises(MessageNormalizationError):
            gateway.normalize_whatsapp_message(None)

    def test_normalize_extracts_contact_wa_id_fallback(self, gateway):
        """Test user_id fallback to contacts when from is empty."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg123",
                            "from": "",
                            "timestamp": "1732800000",
                            "type": "text",
                            "text": {"body": "Hello"}
                        }],
                        "contacts": [{
                            "wa_id": "fallback_user_id"
                        }]
                    }
                }]
            }]
        }
        
        with patch.object(gateway, "_resolve_tenant", return_value="default"):
            unified = gateway.normalize_whatsapp_message(payload)
        
        assert unified.user_id == "fallback_user_id"

    def test_normalize_handles_invalid_timestamp(self, gateway):
        """Test handling of invalid timestamp defaults to now."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg123",
                            "from": "user123",
                            "timestamp": "invalid_timestamp",
                            "type": "text",
                            "text": {"body": "Hello"}
                        }],
                        "contacts": []
                    }
                }]
            }]
        }
        
        with patch.object(gateway, "_resolve_tenant", return_value="default"):
            unified = gateway.normalize_whatsapp_message(payload)
        
        # Should have a valid ISO timestamp (defaulted to now)
        assert unified.timestamp_iso is not None
        assert "T" in unified.timestamp_iso


# ============================================================================
# 2. Gmail Normalization (6 tests)
# ============================================================================

class TestGmailNormalization:
    """Tests for Gmail email normalization."""

    def test_normalize_valid_gmail_message(self, gateway, valid_gmail_payload):
        """Test normalizing a valid Gmail message."""
        unified = gateway.normalize_gmail_message(valid_gmail_payload)
        
        assert unified.message_id == "msg_12345"
        assert unified.canal == "gmail"
        assert unified.user_id == "guest@example.com"
        assert unified.tipo == "text"
        assert "book a room" in unified.texto

    def test_normalize_gmail_extracts_email_from_name_format(self, gateway):
        """Test extracting email from 'Name <email>' format."""
        payload = {
            "message_id": "msg_name_format",
            "from": "John Doe <john.doe@example.com>",
            "subject": "Test",
            "body": "Test body",
            "timestamp": "2025-11-28T10:00:00Z"
        }
        
        unified = gateway.normalize_gmail_message(payload)
        assert unified.user_id == "john.doe@example.com"

    def test_normalize_gmail_missing_required_field_raises(self, gateway):
        """Test that missing required fields raise error."""
        payload = {
            "message_id": "msg123",
            "from": "user@test.com",
            # Missing 'body' and 'timestamp'
        }
        
        with pytest.raises(MessageNormalizationError) as exc:
            gateway.normalize_gmail_message(payload)
        
        assert "Missing required field" in str(exc.value)

    def test_normalize_gmail_invalid_type_raises(self, gateway):
        """Test that non-dict input raises error."""
        with pytest.raises(MessageNormalizationError) as exc:
            gateway.normalize_gmail_message("not a dict")
        
        assert "must be a dictionary" in str(exc.value)

    def test_normalize_gmail_metadata_includes_subject(self, gateway, valid_gmail_payload):
        """Test that Gmail metadata includes subject."""
        unified = gateway.normalize_gmail_message(valid_gmail_payload)
        
        assert "subject" in unified.metadata
        assert unified.metadata["subject"] == "Room Reservation Inquiry"

    def test_extract_email_address_variations(self, gateway):
        """Test email extraction from various formats."""
        # Direct email
        assert gateway._extract_email_address("user@test.com") == "user@test.com"
        
        # Name <email> format
        assert gateway._extract_email_address("Name <user@test.com>") == "user@test.com"
        
        # Multiple emails (takes first)
        result = gateway._extract_email_address("User <first@test.com>, Other <other@test.com>")
        assert result == "first@test.com"
        
        # Fallback to cleaned input
        assert gateway._extract_email_address("  plain string  ") == "plain string"


# ============================================================================
# 3. Security Validations (10 tests)
# ============================================================================

class TestSecurityValidations:
    """Tests for security validation mechanisms."""

    def test_channel_spoofing_detected(self, gateway):
        """Test that channel spoofing is detected and blocked."""
        with pytest.raises(ChannelSpoofingError):
            gateway._validate_channel_not_spoofed(
                claimed_channel="sms",  # Attacker claims SMS
                actual_channel="whatsapp",  # But endpoint is WhatsApp
                user_id="attacker123",
                correlation_id="corr123"
            )

    def test_channel_spoofing_no_claim_allowed(self, gateway):
        """Test that missing channel claim is allowed (uses actual)."""
        # Should not raise - no claimed channel
        gateway._validate_channel_not_spoofed(
            claimed_channel=None,
            actual_channel="whatsapp",
            user_id="user123"
        )

    def test_channel_spoofing_matching_channels_allowed(self, gateway):
        """Test that matching channels are allowed."""
        # Should not raise
        gateway._validate_channel_not_spoofed(
            claimed_channel="whatsapp",
            actual_channel="whatsapp",
            user_id="user123"
        )

    def test_whatsapp_payload_with_spoofed_channel_blocked(self, gateway, valid_whatsapp_payload):
        """Test WhatsApp payload with spoofed channel field is blocked."""
        valid_whatsapp_payload["channel"] = "sms"  # Attacker tries to spoof
        
        # The ChannelSpoofingError is caught and re-raised as MessageNormalizationError
        with pytest.raises(MessageNormalizationError):
            gateway.normalize_whatsapp_message(valid_whatsapp_payload)

    def test_gmail_payload_with_spoofed_channel_blocked(self, gateway, valid_gmail_payload):
        """Test Gmail payload with spoofed channel field is blocked."""
        valid_gmail_payload["channel"] = "whatsapp"  # Attacker tries to spoof
        
        # The ChannelSpoofingError is caught and re-raised as MessageNormalizationError
        with pytest.raises(MessageNormalizationError):
            gateway.normalize_gmail_message(valid_gmail_payload)

    @pytest.mark.asyncio
    async def test_tenant_isolation_validation_default_skipped(self, gateway):
        """Test tenant isolation is skipped for default tenant."""
        # Should not raise for default tenant
        await gateway._validate_tenant_isolation(
            user_id="user123",
            tenant_id="default",
            channel="whatsapp"
        )

    @pytest.mark.asyncio
    async def test_tenant_isolation_violation_raises(self, gateway):
        """Test tenant isolation violation raises TenantIsolationError."""
        with patch("app.core.database.AsyncSessionFactory") as mock_session:
            # Mock DB to return different tenant
            mock_ctx = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = "hotel_other"  # Different tenant
            mock_ctx.__aenter__.return_value.execute.return_value = mock_result
            mock_session.return_value = mock_ctx
            
            with pytest.raises(TenantIsolationError) as exc:
                await gateway._validate_tenant_isolation(
                    user_id="user123",
                    tenant_id="hotel_plaza",
                    channel="whatsapp"
                )
            
            assert exc.value.requested_tenant_id == "hotel_plaza"
            assert exc.value.actual_tenant_id == "hotel_other"

    @pytest.mark.asyncio
    async def test_tenant_isolation_user_not_found_allowed(self, gateway):
        """Test user not found in any tenant is allowed with warning."""
        with patch("app.core.database.AsyncSessionFactory") as mock_session:
            mock_ctx = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None  # User not found
            mock_ctx.__aenter__.return_value.execute.return_value = mock_result
            mock_session.return_value = mock_ctx
            
            # Should not raise - new user
            await gateway._validate_tenant_isolation(
                user_id="new_user",
                tenant_id="hotel_plaza",
                channel="whatsapp"
            )

    @pytest.mark.asyncio
    async def test_tenant_isolation_db_error_handled(self, gateway):
        """Test DB errors during tenant validation are handled gracefully."""
        with patch("app.core.database.AsyncSessionFactory") as mock_session:
            mock_session.side_effect = Exception("DB connection failed")
            
            # Should not raise - DB errors logged but don't block
            await gateway._validate_tenant_isolation(
                user_id="user123",
                tenant_id="hotel_plaza",
                channel="whatsapp"
            )

    def test_tenant_isolation_error_attributes(self):
        """Test TenantIsolationError stores attributes correctly."""
        error = TenantIsolationError(
            "Test error",
            user_id="user123",
            requested_tenant_id="hotel_a",
            actual_tenant_id="hotel_b"
        )
        
        assert error.user_id == "user123"
        assert error.requested_tenant_id == "hotel_a"
        assert error.actual_tenant_id == "hotel_b"


# ============================================================================
# 4. Metadata Filtering (6 tests)
# ============================================================================

class TestMetadataFiltering:
    """Tests for metadata injection prevention."""

    def test_allowed_metadata_keys_filtered(self, gateway):
        """Test that only whitelisted keys are allowed."""
        raw_metadata = {
            "user_context": "valid",
            "source": "webhook",
            "admin": True,  # Should be dropped
            "role": "superuser",  # Should be dropped
        }
        
        filtered = gateway._filter_metadata(raw_metadata)
        
        assert "user_context" in filtered
        assert "source" in filtered
        assert "admin" not in filtered
        assert "role" not in filtered

    def test_dangerous_metadata_keys_blocked(self, gateway):
        """Test that dangerous keys are blocked."""
        dangerous_metadata = {
            "bypass_validation": True,
            "override_tenant_id": "evil_tenant",
            "is_admin": True,
            "permissions": ["all"],
        }
        
        filtered = gateway._filter_metadata(dangerous_metadata)
        
        assert len(filtered) == 0

    def test_metadata_value_type_validation(self, gateway):
        """Test that only scalar values are allowed."""
        raw_metadata = {
            "user_context": "string_value",  # OK
            "custom_fields": {"nested": "object"},  # Should be dropped
            "source": ["array", "value"],  # Should be dropped
        }
        
        filtered = gateway._filter_metadata(raw_metadata)
        
        assert "user_context" in filtered
        assert "custom_fields" not in filtered
        assert "source" not in filtered

    def test_metadata_string_length_limit(self, gateway):
        """Test that overly long strings are dropped."""
        long_string = "x" * 1001  # Over 1000 char limit
        
        raw_metadata = {
            "user_context": long_string,
            "source": "short_value",
        }
        
        filtered = gateway._filter_metadata(raw_metadata)
        
        assert "user_context" not in filtered
        assert "source" in filtered

    def test_metadata_empty_or_none_returns_empty(self, gateway):
        """Test that empty/None metadata returns empty dict."""
        assert gateway._filter_metadata(None) == {}
        assert gateway._filter_metadata({}) == {}

    def test_allowed_metadata_keys_constant(self):
        """Test ALLOWED_METADATA_KEYS contains expected keys."""
        assert "user_context" in ALLOWED_METADATA_KEYS
        assert "custom_fields" in ALLOWED_METADATA_KEYS
        assert "source" in ALLOWED_METADATA_KEYS
        assert "external_request_id" in ALLOWED_METADATA_KEYS
        assert "language_hint" in ALLOWED_METADATA_KEYS
        assert "subject" in ALLOWED_METADATA_KEYS
        assert "from_full" in ALLOWED_METADATA_KEYS


# ============================================================================
# 5. Tenant Resolution (5 tests)
# ============================================================================

class TestTenantResolution:
    """Tests for dynamic/static tenant resolution."""

    def test_resolve_tenant_empty_user_returns_default(self, gateway):
        """Test empty user_id returns default tenant."""
        assert gateway._resolve_tenant(None) == "default"
        assert gateway._resolve_tenant("") == "default"

    def test_resolve_tenant_dynamic_enabled(self, gateway):
        """Test dynamic tenant resolution when enabled."""
        with patch.dict("app.services.message_gateway.DEFAULT_FLAGS", {"tenancy.dynamic.enabled": True}):
            with patch("app.services.message_gateway._TENANT_RESOLVER_DYNAMIC") as mock_resolver:
                mock_resolver.resolve_tenant.return_value = "hotel_dynamic"
                
                result = gateway._resolve_tenant("user123")
                
                assert result == "hotel_dynamic"

    def test_resolve_tenant_dynamic_fails_falls_to_static(self, gateway):
        """Test fallback to static resolver when dynamic fails."""
        with patch.dict("app.services.message_gateway.DEFAULT_FLAGS", {"tenancy.dynamic.enabled": True}):
            with patch("app.services.message_gateway._TENANT_RESOLVER_DYNAMIC") as mock_dyn:
                with patch("app.services.message_gateway._TENANT_RESOLVER_STATIC") as mock_static:
                    mock_dyn.resolve_tenant.side_effect = Exception("Dynamic failed")
                    mock_static.resolve_tenant.return_value = "hotel_static"
                    
                    result = gateway._resolve_tenant("user123")
                    
                    assert result == "hotel_static"

    def test_resolve_tenant_both_fail_returns_default(self, gateway):
        """Test returns default when both resolvers fail."""
        with patch.dict("app.services.message_gateway.DEFAULT_FLAGS", {"tenancy.dynamic.enabled": True}):
            with patch("app.services.message_gateway._TENANT_RESOLVER_DYNAMIC") as mock_dyn:
                with patch("app.services.message_gateway._TENANT_RESOLVER_STATIC") as mock_static:
                    mock_dyn.resolve_tenant.side_effect = Exception("Dynamic failed")
                    mock_static.resolve_tenant.side_effect = Exception("Static failed")
                    
                    result = gateway._resolve_tenant("user123")
                    
                    assert result == "default"

    def test_resolve_tenant_dynamic_disabled(self, gateway):
        """Test static resolution when dynamic is disabled."""
        with patch.dict("app.services.message_gateway.DEFAULT_FLAGS", {"tenancy.dynamic.enabled": False}):
            with patch("app.services.message_gateway._TENANT_RESOLVER_STATIC") as mock_static:
                mock_static.resolve_tenant.return_value = "hotel_static"
                
                result = gateway._resolve_tenant("user123")
                
                assert result == "hotel_static"


# ============================================================================
# 6. Edge Cases & Error Handling (5 tests)
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_get_correlation_id_from_payload(self, gateway):
        """Test correlation ID extraction from payload."""
        payload = {"correlation_id": "corr_12345"}
        assert gateway._get_correlation_id(payload) == "corr_12345"
        
        payload_empty = {}
        assert gateway._get_correlation_id(payload_empty) == ""

    def test_normalize_whatsapp_unexpected_error(self, gateway):
        """Test unexpected errors during normalization."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{"type": "text", "from": "user"}]
                    }
                }]
            }]
        }
        
        with patch.object(gateway, "_resolve_tenant", side_effect=RuntimeError("Unexpected")):
            with pytest.raises(MessageNormalizationError) as exc:
                gateway.normalize_whatsapp_message(payload)
            
            assert "unexpected" in str(exc.value)

    def test_normalize_whatsapp_none_text_body(self, gateway):
        """Test handling of message without text body."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg123",
                            "from": "user123",
                            "timestamp": "1732800000",
                            "type": "text",
                            "text": {}  # No body
                        }],
                        "contacts": []
                    }
                }]
            }]
        }
        
        with patch.object(gateway, "_resolve_tenant", return_value="default"):
            unified = gateway.normalize_whatsapp_message(payload)
        
        assert unified.texto is None

    def test_normalize_whatsapp_unknown_message_type(self, gateway):
        """Test handling of unknown message type."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg123",
                            "from": "user123",
                            "timestamp": "1732800000",
                            "type": "sticker",  # Unknown type
                            "sticker": {"id": "sticker123"}
                        }],
                        "contacts": []
                    }
                }]
            }]
        }
        
        with patch.object(gateway, "_resolve_tenant", return_value="default"):
            unified = gateway.normalize_whatsapp_message(payload)
        
        # Unknown types default to text handling
        assert unified.tipo == "text"

    def test_message_normalization_error_str(self):
        """Test MessageNormalizationError string representation."""
        error = MessageNormalizationError("missing_field")
        assert str(error) == "missing_field"
