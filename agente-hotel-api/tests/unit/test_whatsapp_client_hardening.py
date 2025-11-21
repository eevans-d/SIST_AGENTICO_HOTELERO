import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import aiohttp
from app.services.whatsapp_client import WhatsAppMetaClient
from app.exceptions.whatsapp_exceptions import WhatsAppError, WhatsAppAuthError, WhatsAppRateLimitError

# Mock settings
@pytest.fixture
def mock_settings():
    with patch("app.services.whatsapp_client.settings") as mock:
        mock.whatsapp_access_token.get_secret_value.return_value = "test_token"
        mock.whatsapp_phone_number_id = "123456789"
        mock.whatsapp_app_secret.get_secret_value.return_value = "test_secret"
        yield mock

@pytest.fixture
def whatsapp_client(mock_settings):
    client = WhatsAppMetaClient()
    # Mock internal clients
    client.client = AsyncMock(spec=httpx.AsyncClient)
    return client

@pytest.mark.asyncio
class TestWhatsAppClientHardening:
    
    async def test_initialization(self, mock_settings):
        """Test client initialization and configuration"""
        client = WhatsAppMetaClient()
        assert client.phone_number_id == "123456789"
        assert client.access_token == "test_token"
        assert isinstance(client.client, httpx.AsyncClient)
        assert client._aiohttp_session is None

    async def test_get_aiohttp_session_reuse(self, whatsapp_client):
        """Test aiohttp session reuse"""
        # First call creates session
        session1 = await whatsapp_client._get_aiohttp_session()
        assert isinstance(session1, aiohttp.ClientSession)
        
        # Second call returns same session
        session2 = await whatsapp_client._get_aiohttp_session()
        assert session1 is session2
        
        # Cleanup
        await whatsapp_client.close()

    async def test_send_message_success(self, whatsapp_client):
        """Test sending a text message successfully"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "msg_123"}]}
        whatsapp_client.client.post.return_value = mock_response
        
        response = await whatsapp_client.send_message("5551234", "Hello")
        
        assert response["messages"][0]["id"] == "msg_123"
        whatsapp_client.client.post.assert_called_once()
        
        # Verify payload
        call_args = whatsapp_client.client.post.call_args
        assert call_args[1]["json"]["to"] == "5551234"
        assert call_args[1]["json"]["text"]["body"] == "Hello"

    async def test_send_message_auth_error(self, whatsapp_client):
        """Test handling of authentication error"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "Unauthorized", "code": 190}}
        whatsapp_client.client.post.return_value = mock_response
        
        with pytest.raises(WhatsAppAuthError):
            await whatsapp_client.send_message("5551234", "Hello")

    async def test_send_message_rate_limit(self, whatsapp_client):
        """Test handling of rate limit error"""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": {"message": "Rate limit exceeded", "code": 131048}}
        whatsapp_client.client.post.return_value = mock_response
        
        with pytest.raises(WhatsAppRateLimitError):
            await whatsapp_client.send_message("5551234", "Hello")

    async def test_send_template_message(self, whatsapp_client):
        """Test sending a template message"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "msg_123"}]}
        whatsapp_client.client.post.return_value = mock_response
        
        parameters = [{"type": "text", "text": "param1"}]
        response = await whatsapp_client.send_template_message("5551234", "hello_world", "en_US", parameters)
        
        assert response["messages"][0]["id"] == "msg_123"
        
        # Verify payload
        call_args = whatsapp_client.client.post.call_args
        payload = call_args[1]["json"]
        assert payload["template"]["name"] == "hello_world"
        assert payload["template"]["language"]["code"] == "en_US"
        
        expected_components = [{"type": "body", "parameters": parameters}]
        assert payload["template"]["components"] == expected_components

    async def test_close_cleanup(self, whatsapp_client):
        """Test resource cleanup on close"""
        # Initialize session
        await whatsapp_client._get_aiohttp_session()
        assert whatsapp_client._aiohttp_session is not None
        
        # Mock session close
        whatsapp_client._aiohttp_session.close = AsyncMock()
        
        await whatsapp_client.close()
        
        whatsapp_client._aiohttp_session.close.assert_called_once()
        whatsapp_client.client.aclose.assert_called_once()

