"""
Integration tests for WhatsApp Business API client.

Tests cover:
- Text message sending
- Template message sending
- Media download (2-step process)
- Webhook signature verification
- Error handling (auth, rate limits, media errors)
- Metrics tracking
"""

import json
from unittest.mock import Mock, AsyncMock, patch
import pytest
import httpx

from app.services.whatsapp_client import WhatsAppMetaClient
from app.exceptions.whatsapp_exceptions import (
    WhatsAppAuthError,
    WhatsAppRateLimitError,
    WhatsAppMediaError,
    WhatsAppTemplateError,
    WhatsAppNetworkError,
)


# ==================== FIXTURES ====================

@pytest.fixture
def whatsapp_client():
    """WhatsApp client fixture with mocked settings."""
    with patch("app.services.whatsapp_client.settings") as mock_settings:
        mock_settings.whatsapp_access_token.get_secret_value.return_value = "test_token"
        mock_settings.whatsapp_phone_number_id = "123456789"
        mock_settings.whatsapp_app_secret.get_secret_value.return_value = "test_secret"
        
        client = WhatsAppMetaClient()
        yield client


@pytest.fixture
def mock_httpx_response():
    """Factory for creating mock httpx responses."""
    def _create_response(status_code: int, json_data: dict | None = None, content: bytes | None = None):
        response = Mock(spec=httpx.Response)
        response.status_code = status_code
        response.json.return_value = json_data or {}
        response.text = json.dumps(json_data) if json_data else ""
        response.content = content or b""
        response.headers = {"content-type": "application/json"}
        return response
    return _create_response


# ==================== TEXT MESSAGE TESTS ====================

@pytest.mark.asyncio
async def test_send_message_success(whatsapp_client, mock_httpx_response):
    """Test successful text message sending."""
    # Mock successful API response
    success_response = mock_httpx_response(
        200,
        {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "14155552671", "wa_id": "14155552671"}],
            "messages": [{"id": "wamid.test123"}]
        }
    )
    
    whatsapp_client.client.post = AsyncMock(return_value=success_response)
    
    # Send message
    result = await whatsapp_client.send_message(
        to="14155552671",
        text="Hello from integration test!"
    )
    
    # Assertions
    assert result["messages"][0]["id"] == "wamid.test123"
    assert whatsapp_client.client.post.called
    
    # Verify payload structure
    call_args = whatsapp_client.client.post.call_args
    payload = call_args.kwargs["json"]
    assert payload["messaging_product"] == "whatsapp"
    assert payload["to"] == "14155552671"
    assert payload["text"]["body"] == "Hello from integration test!"


@pytest.mark.asyncio
async def test_send_message_auth_error(whatsapp_client, mock_httpx_response):
    """Test authentication error handling."""
    # Mock 401 response
    error_response = mock_httpx_response(
        401,
        {
            "error": {
                "message": "Invalid OAuth access token",
                "type": "OAuthException",
                "code": 190
            }
        }
    )
    
    whatsapp_client.client.post = AsyncMock(return_value=error_response)
    
    # Should raise WhatsAppAuthError
    with pytest.raises(WhatsAppAuthError) as exc_info:
        await whatsapp_client.send_message(to="14155552671", text="Test")
    
    assert exc_info.value.status_code == 401
    assert "Invalid OAuth access token" in str(exc_info.value)


@pytest.mark.asyncio
async def test_send_message_rate_limit(whatsapp_client, mock_httpx_response):
    """Test rate limit error handling."""
    # Mock 429 response
    error_response = mock_httpx_response(
        429,
        {
            "error": {
                "message": "Rate limit exceeded",
                "type": "RateLimitError",
                "code": 4,
                "retry_after": 60
            }
        }
    )
    
    whatsapp_client.client.post = AsyncMock(return_value=error_response)
    
    # Should raise WhatsAppRateLimitError
    with pytest.raises(WhatsAppRateLimitError) as exc_info:
        await whatsapp_client.send_message(to="14155552671", text="Test")
    
    assert exc_info.value.status_code == 429
    assert exc_info.value.retry_after == 60


@pytest.mark.asyncio
async def test_send_message_timeout(whatsapp_client):
    """Test timeout error handling."""
    whatsapp_client.client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
    
    # Should raise WhatsAppNetworkError
    with pytest.raises(WhatsAppNetworkError) as exc_info:
        await whatsapp_client.send_message(to="14155552671", text="Test")
    
    assert "Timeout" in str(exc_info.value)


# ==================== TEMPLATE MESSAGE TESTS ====================

@pytest.mark.asyncio
async def test_send_template_message_success(whatsapp_client, mock_httpx_response):
    """Test successful template message sending."""
    success_response = mock_httpx_response(
        200,
        {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "14155552671", "wa_id": "14155552671"}],
            "messages": [{"id": "wamid.template123"}]
        }
    )
    
    whatsapp_client.client.post = AsyncMock(return_value=success_response)
    
    # Send template message
    parameters = [{"type": "text", "text": "John Doe"}]
    result = await whatsapp_client.send_template_message(
        to="14155552671",
        template_name="welcome_message",
        language_code="es",
        parameters=parameters
    )
    
    # Assertions
    assert result["messages"][0]["id"] == "wamid.template123"
    
    # Verify payload structure
    call_args = whatsapp_client.client.post.call_args
    payload = call_args.kwargs["json"]
    assert payload["type"] == "template"
    assert payload["template"]["name"] == "welcome_message"
    assert payload["template"]["language"]["code"] == "es"
    assert payload["template"]["components"][0]["type"] == "body"


@pytest.mark.asyncio
async def test_send_template_message_not_found(whatsapp_client, mock_httpx_response):
    """Test template not found error."""
    error_response = mock_httpx_response(
        400,
        {
            "error": {
                "message": "Template does not exist",
                "type": "InvalidParameterException",
                "code": 100
            }
        }
    )
    
    whatsapp_client.client.post = AsyncMock(return_value=error_response)
    
    # Should raise WhatsAppTemplateError
    with pytest.raises(WhatsAppTemplateError) as exc_info:
        await whatsapp_client.send_template_message(
            to="14155552671",
            template_name="nonexistent_template"
        )
    
    assert "Template does not exist" in str(exc_info.value)
    assert exc_info.value.context.get("error", {}).get("code") == 100


# ==================== MEDIA DOWNLOAD TESTS ====================

@pytest.mark.asyncio
async def test_download_media_success(whatsapp_client, mock_httpx_response):
    """Test successful media download (2-step process)."""
    # Step 1: Mock media URL response
    url_response = mock_httpx_response(
        200,
        {
            "url": "https://lookaside.fbsbx.com/whatsapp_business/attachments/test.ogg",
            "mime_type": "audio/ogg",
            "sha256": "test_hash",
            "file_size": 12345,
            "id": "media123"
        }
    )
    
    # Step 2: Mock media download response
    media_content = b"fake_audio_data_ogg_opus"
    download_response = mock_httpx_response(200, content=media_content)
    download_response.headers = {"content-type": "audio/ogg"}
    
    # Mock both GET requests
    whatsapp_client.client.get = AsyncMock(side_effect=[url_response, download_response])
    
    # Download media
    result = await whatsapp_client.download_media("media123")
    
    # Assertions
    assert result == media_content
    assert whatsapp_client.client.get.call_count == 2
    
    # Verify first call (get URL)
    first_call = whatsapp_client.client.get.call_args_list[0]
    assert "media123" in str(first_call)
    
    # Verify second call (download)
    second_call = whatsapp_client.client.get.call_args_list[1]
    assert "lookaside.fbsbx.com" in str(second_call)


@pytest.mark.asyncio
async def test_download_media_not_found(whatsapp_client, mock_httpx_response):
    """Test media not found error."""
    error_response = mock_httpx_response(
        404,
        {
            "error": {
                "message": "Media not found",
                "type": "InvalidParameterException",
                "code": 100
            }
        }
    )
    
    whatsapp_client.client.get = AsyncMock(return_value=error_response)
    
    # Should raise WhatsAppMediaError
    with pytest.raises(WhatsAppMediaError) as exc_info:
        await whatsapp_client.download_media("nonexistent_media")
    
    assert exc_info.value.status_code == 404
    assert "Media not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_download_media_no_url(whatsapp_client, mock_httpx_response):
    """Test media download when URL is missing in response."""
    # Mock response without URL
    url_response = mock_httpx_response(
        200,
        {
            "mime_type": "audio/ogg",
            "id": "media123"
            # Missing "url" field
        }
    )
    
    whatsapp_client.client.get = AsyncMock(return_value=url_response)
    
    # Should raise WhatsAppMediaError
    with pytest.raises(WhatsAppMediaError) as exc_info:
        await whatsapp_client.download_media("media123")
    
    assert "No download URL" in str(exc_info.value)


@pytest.mark.asyncio
async def test_download_media_download_fails(whatsapp_client, mock_httpx_response):
    """Test media download failure in step 2."""
    # Step 1: Successful URL retrieval
    url_response = mock_httpx_response(
        200,
        {"url": "https://lookaside.fbsbx.com/whatsapp_business/attachments/test.ogg"}
    )
    
    # Step 2: Failed download
    download_response = mock_httpx_response(500, {"error": "Internal server error"})
    
    whatsapp_client.client.get = AsyncMock(side_effect=[url_response, download_response])
    
    # Should raise WhatsAppMediaError
    with pytest.raises(WhatsAppMediaError) as exc_info:
        await whatsapp_client.download_media("media123")
    
    assert "Failed to download media" in str(exc_info.value)
    assert exc_info.value.status_code == 500


# ==================== WEBHOOK SIGNATURE TESTS ====================

def test_verify_webhook_signature_valid(whatsapp_client):
    """Test valid webhook signature verification."""
    payload = b'{"object":"whatsapp_business_account","entry":[{"id":"123"}]}'
    
    # Compute valid signature
    import hmac
    import hashlib
    expected_signature = hmac.new(
        b"test_secret",
        payload,
        hashlib.sha256
    ).hexdigest()
    
    signature_header = f"sha256={expected_signature}"
    
    # Should return True
    is_valid = whatsapp_client.verify_webhook_signature(payload, signature_header)
    assert is_valid is True


def test_verify_webhook_signature_invalid(whatsapp_client):
    """Test invalid webhook signature verification."""
    payload = b'{"object":"whatsapp_business_account"}'
    signature_header = "sha256=invalid_signature_here"
    
    # Should return False
    is_valid = whatsapp_client.verify_webhook_signature(payload, signature_header)
    assert is_valid is False


def test_verify_webhook_signature_missing(whatsapp_client):
    """Test missing signature header."""
    payload = b'{"object":"whatsapp_business_account"}'
    
    # Should return False
    is_valid = whatsapp_client.verify_webhook_signature(payload, "")
    assert is_valid is False


def test_verify_webhook_signature_wrong_format(whatsapp_client):
    """Test signature with wrong format (not sha256=...)."""
    payload = b'{"object":"whatsapp_business_account"}'
    signature_header = "md5=somehash"
    
    # Should return False
    is_valid = whatsapp_client.verify_webhook_signature(payload, signature_header)
    assert is_valid is False


# ==================== CLIENT LIFECYCLE TESTS ====================

@pytest.mark.asyncio
async def test_client_close(whatsapp_client):
    """Test client connection pool cleanup."""
    whatsapp_client.client.aclose = AsyncMock()
    
    await whatsapp_client.close()
    
    assert whatsapp_client.client.aclose.called
