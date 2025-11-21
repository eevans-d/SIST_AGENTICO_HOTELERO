import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.message_gateway import MessageGateway, MessageNormalizationError, TenantIsolationError, ChannelSpoofingError
from app.models.unified_message import UnifiedMessage

@pytest.fixture
def message_gateway():
    return MessageGateway()

@pytest.fixture
def mock_metrics():
    with patch("app.services.message_gateway.metrics_service") as mock:
        yield mock

# --- Tenant Resolution Tests ---

def test_resolve_tenant_default(message_gateway):
    """Test default tenant resolution when no user_id"""
    assert message_gateway._resolve_tenant(None) == "default"
    assert message_gateway._resolve_tenant("") == "default"

def test_resolve_tenant_dynamic(message_gateway):
    """Test dynamic tenant resolution"""
    with patch("app.services.message_gateway._TENANT_RESOLVER_DYNAMIC") as mock_resolver:
        mock_resolver.resolve_tenant.return_value = "tenant_123"
        assert message_gateway._resolve_tenant("user1") == "tenant_123"

def test_resolve_tenant_static_fallback(message_gateway):
    """Test fallback to static resolver if dynamic is disabled"""
    with patch("app.services.message_gateway._TENANT_RESOLVER_STATIC") as mock_static, \
         patch("app.services.message_gateway.DEFAULT_FLAGS", {"tenancy.dynamic.enabled": False}):
        
        mock_static.resolve_tenant.return_value = "static_tenant"
        
        assert message_gateway._resolve_tenant("user1") == "static_tenant"

# --- Tenant Isolation Tests ---

@pytest.mark.asyncio
async def test_validate_tenant_isolation_default(message_gateway):
    """Test validation skipped for default tenant"""
    # Should not raise
    await message_gateway._validate_tenant_isolation("u1", "default", "whatsapp")

@pytest.mark.asyncio
async def test_validate_tenant_isolation_success(message_gateway):
    """Test successful tenant validation"""
    with patch("app.core.database.AsyncSessionFactory") as mock_session_factory:
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        
        # Mock DB result: user belongs to requested tenant
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "tenant_abc"
        mock_session.execute.return_value = mock_result
        
        await message_gateway._validate_tenant_isolation("u1", "tenant_abc", "whatsapp")

@pytest.mark.asyncio
async def test_validate_tenant_isolation_violation(message_gateway):
    """Test tenant isolation violation"""
    with patch("app.core.database.AsyncSessionFactory") as mock_session_factory:
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        
        # Mock DB result: user belongs to DIFFERENT tenant
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "tenant_xyz"
        mock_session.execute.return_value = mock_result
        
        with pytest.raises(TenantIsolationError):
            await message_gateway._validate_tenant_isolation("u1", "tenant_abc", "whatsapp")

# --- Metadata Filtering Tests ---

def test_filter_metadata_whitelist(message_gateway):
    """Test metadata filtering allows only whitelisted keys"""
    raw = {
        "user_context": "valid",
        "malicious_key": "drop_me",
        "source": "webhook"
    }
    filtered = message_gateway._filter_metadata(raw)
    assert "user_context" in filtered
    assert "source" in filtered
    assert "malicious_key" not in filtered

def test_filter_metadata_types(message_gateway):
    """Test metadata type validation"""
    raw = {
        "user_context": {"nested": "dict_not_allowed"},
        "source": "valid_string"
    }
    filtered = message_gateway._filter_metadata(raw)
    assert "source" in filtered
    assert "user_context" not in filtered  # Dicts not allowed as values

def test_filter_metadata_length(message_gateway):
    """Test metadata length validation"""
    long_string = "a" * 1001
    raw = {"user_context": long_string}
    filtered = message_gateway._filter_metadata(raw)
    assert "user_context" not in filtered

# --- Channel Spoofing Tests ---

def test_validate_channel_spoofing_success(message_gateway):
    """Test channel validation passes when matching"""
    message_gateway._validate_channel_not_spoofed("whatsapp", "whatsapp")

def test_validate_channel_spoofing_failure(message_gateway):
    """Test channel validation fails when mismatch"""
    with pytest.raises(ChannelSpoofingError):
        message_gateway._validate_channel_not_spoofed("sms", "whatsapp")

def test_validate_channel_spoofing_no_claim(message_gateway):
    """Test channel validation passes when no channel claimed"""
    message_gateway._validate_channel_not_spoofed(None, "whatsapp")

# --- WhatsApp Normalization Tests ---

def test_normalize_whatsapp_valid(message_gateway, mock_metrics):
    """Test normalizing valid WhatsApp payload"""
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "123456789",
                        "id": "msg_123",
                        "timestamp": "1609459200",
                        "type": "text",
                        "text": {"body": "Hello"}
                    }],
                    "contacts": [{"wa_id": "123456789"}]
                }
            }]
        }]
    }
    
    msg = message_gateway.normalize_whatsapp_message(payload)
    
    assert isinstance(msg, UnifiedMessage)
    assert msg.user_id == "123456789"
    assert msg.texto == "Hello"
    assert msg.canal == "whatsapp"

def test_normalize_whatsapp_missing_fields(message_gateway, mock_metrics):
    """Test normalization with missing fields raises error"""
    payload = {"entry": []}
    with pytest.raises(MessageNormalizationError):
        message_gateway.normalize_whatsapp_message(payload)

def test_normalize_whatsapp_spoofing(message_gateway, mock_metrics):
    """Test normalization detects channel spoofing"""
    payload = {
        "channel": "sms",  # Attacker claims SMS
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{"from": "123", "type": "text", "text": {"body": "Hi"}}]
                }
            }]
        }]
    }
    
    # ChannelSpoofingError is caught and re-raised as MessageNormalizationError
    with pytest.raises(MessageNormalizationError):
        message_gateway.normalize_whatsapp_message(payload)

# --- Gmail Normalization Tests ---

def test_normalize_gmail_valid(message_gateway):
    """Test normalizing valid Gmail payload"""
    email_dict = {
        "message_id": "msg_123",
        "from": "John Doe <john@example.com>",
        "subject": "Booking",
        "body": "I want a room",
        "timestamp": "2024-01-01T12:00:00Z"
    }
    
    msg = message_gateway.normalize_gmail_message(email_dict)
    
    assert isinstance(msg, UnifiedMessage)
    assert msg.user_id == "john@example.com"
    assert msg.texto == "I want a room"
    assert msg.canal == "gmail"
    assert msg.metadata["subject"] == "Booking"

def test_normalize_gmail_missing_fields(message_gateway):
    """Test normalization with missing fields"""
    email_dict = {"from": "john@example.com"}
    with pytest.raises(MessageNormalizationError):
        message_gateway.normalize_gmail_message(email_dict)

def test_extract_email_address(message_gateway):
    """Test email extraction logic"""
    assert message_gateway._extract_email_address("user@test.com") == "user@test.com"
    assert message_gateway._extract_email_address("Name <user@test.com>") == "user@test.com"
    assert message_gateway._extract_email_address("invalid") == "invalid"
