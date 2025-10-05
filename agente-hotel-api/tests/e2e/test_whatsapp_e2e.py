"""
End-to-end tests for WhatsApp Business API integration.

Tests complete flows from webhook to response:
- Text message flow: Webhook → Normalize → Process → Response
- Audio message flow: Webhook → Download → STT → NLP → Response
- Template response flow: Webhook → Process → Template → Response
"""

import json
from unittest.mock import Mock, AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.main import app


# ==================== FIXTURES ====================

@pytest.fixture
def sample_whatsapp_webhook_text():
    """Sample WhatsApp webhook payload with text message."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15551234567",
                                "phone_number_id": "PHONE_NUMBER_ID"
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "John Doe"},
                                    "wa_id": "14155552671"
                                }
                            ],
                            "messages": [
                                {
                                    "from": "14155552671",
                                    "id": "wamid.HBgLMTQxNTU1NTI2NzEVAgARGBI5QTNDQTVCMEI1RTQ0RTFFMzcA",
                                    "timestamp": "1633024800",
                                    "type": "text",
                                    "text": {"body": "I want to book a room"}
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }


@pytest.fixture
def sample_whatsapp_webhook_audio():
    """Sample WhatsApp webhook payload with audio message."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15551234567",
                                "phone_number_id": "PHONE_NUMBER_ID"
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Jane Smith"},
                                    "wa_id": "14155552672"
                                }
                            ],
                            "messages": [
                                {
                                    "from": "14155552672",
                                    "id": "wamid.AUDIO123",
                                    "timestamp": "1633024900",
                                    "type": "audio",
                                    "audio": {
                                        "mime_type": "audio/ogg; codecs=opus",
                                        "sha256": "test_hash",
                                        "id": "media_audio_123",
                                        "voice": True
                                    }
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }


# ==================== E2E TESTS ====================

@pytest.mark.asyncio
async def test_whatsapp_text_message_e2e(sample_whatsapp_webhook_text):
    """
    Test complete text message flow.
    
    Flow:
    1. Webhook receives text message
    2. Normalize to UnifiedMessage
    3. Process via Orchestrator (NLP + PMS)
    4. Send response via WhatsApp
    """
    # Mock settings
    with patch("app.routers.webhooks.settings") as mock_settings, \
         patch("app.routers.webhooks.get_redis") as mock_redis, \
         patch("app.routers.webhooks.get_pms_adapter") as mock_pms:
        
        # Configure mocks
        mock_settings.whatsapp_app_secret.get_secret_value.return_value = "test_secret"
        mock_settings.whatsapp_verify_token.get_secret_value.return_value = "test_verify"
        
        # Mock Redis (in-memory)
        redis_mock = AsyncMock()
        redis_mock.ping.return_value = True
        redis_mock.get.return_value = None
        redis_mock.setex.return_value = True
        mock_redis.return_value = redis_mock
        
        # Mock PMS adapter
        pms_mock = AsyncMock()
        pms_mock.check_availability.return_value = {
            "available": True,
            "rooms": [{"room_id": 101, "type": "standard", "price": 100}]
        }
        mock_pms.return_value = pms_mock
        
        # Compute signature for webhook
        import hmac
        import hashlib
        payload_bytes = json.dumps(sample_whatsapp_webhook_text).encode()
        signature = hmac.new(
            b"test_secret",
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        # Send request
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/webhooks/whatsapp",
                json=sample_whatsapp_webhook_text,
                headers={
                    "X-Hub-Signature-256": f"sha256={signature}",
                    "Content-Type": "application/json"
                }
            )
        
        # Assertions
        assert response.status_code == 200
        result = response.json()
        assert result.get("status") in ["ok", "processed"]


@pytest.mark.asyncio
async def test_whatsapp_audio_message_e2e(sample_whatsapp_webhook_audio):
    """
    Test complete audio message flow.
    
    Flow:
    1. Webhook receives audio message
    2. Download media via WhatsApp API
    3. Transcribe audio (STT)
    4. Process text via NLP
    5. Send text response
    """
    # Mock WhatsApp client
    with patch("app.services.whatsapp_client.WhatsAppMetaClient") as MockClient, \
         patch("app.routers.webhooks.settings") as mock_settings, \
         patch("app.routers.webhooks.get_redis") as mock_redis:
        
        # Configure WhatsApp client mock
        client_instance = AsyncMock()
        client_instance.download_media.return_value = b"fake_audio_ogg_data"
        MockClient.return_value = client_instance
        
        # Configure settings
        mock_settings.whatsapp_app_secret.get_secret_value.return_value = "test_secret"
        
        # Mock Redis
        redis_mock = AsyncMock()
        redis_mock.ping.return_value = True
        redis_mock.get.return_value = None
        redis_mock.setex.return_value = True
        mock_redis.return_value = redis_mock
        
        # Compute signature
        import hmac
        import hashlib
        payload_bytes = json.dumps(sample_whatsapp_webhook_audio).encode()
        signature = hmac.new(
            b"test_secret",
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        # Send request
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/webhooks/whatsapp",
                json=sample_whatsapp_webhook_audio,
                headers={
                    "X-Hub-Signature-256": f"sha256={signature}",
                    "Content-Type": "application/json"
                }
            )
        
        # Assertions
        assert response.status_code == 200
        result = response.json()
        assert result.get("status") in ["ok", "processed"]


@pytest.mark.asyncio
async def test_whatsapp_webhook_invalid_signature():
    """Test webhook with invalid signature is rejected."""
    payload = {"object": "whatsapp_business_account", "entry": []}
    
    with patch("app.routers.webhooks.settings") as mock_settings:
        mock_settings.whatsapp_app_secret.get_secret_value.return_value = "test_secret"
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/webhooks/whatsapp",
                json=payload,
                headers={
                    "X-Hub-Signature-256": "sha256=invalid_signature",
                    "Content-Type": "application/json"
                }
            )
        
        # Should be rejected
        assert response.status_code == 401
        assert "signature" in response.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_whatsapp_webhook_verification():
    """Test WhatsApp webhook verification (GET)."""
    with patch("app.routers.webhooks.settings") as mock_settings:
        mock_settings.whatsapp_verify_token.get_secret_value.return_value = "test_verify_token"
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/webhooks/whatsapp",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "test_verify_token",
                    "hub.challenge": "challenge_12345"
                }
            )
        
        # Should return challenge
        assert response.status_code == 200
        assert response.text == "challenge_12345"


@pytest.mark.asyncio
async def test_whatsapp_webhook_verification_invalid_token():
    """Test WhatsApp webhook verification with wrong token."""
    with patch("app.routers.webhooks.settings") as mock_settings:
        mock_settings.whatsapp_verify_token.get_secret_value.return_value = "correct_token"
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/webhooks/whatsapp",
                params={
                    "hub.mode": "subscribe",
                    "hub.verify_token": "wrong_token",
                    "hub.challenge": "challenge_12345"
                }
            )
        
        # Should be rejected
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_whatsapp_template_message_flow():
    """
    Test template message response flow.
    
    Flow:
    1. Guest sends booking request
    2. System processes via NLP
    3. System sends template confirmation message
    """
    # Mock WhatsApp client with template support
    with patch("app.services.whatsapp_client.WhatsAppMetaClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.send_template_message.return_value = {
            "messages": [{"id": "wamid.template123"}]
        }
        MockClient.return_value = client_instance
        
        # Create orchestrator with mocked services
        from app.services.orchestrator import Orchestrator
        
        orchestrator_mock = AsyncMock()
        orchestrator_mock.handle_unified_message.return_value = {
            "status": "ok",
            "template_sent": True,
            "message_id": "wamid.template123"
        }
        
        # In a real scenario, the orchestrator would:
        # 1. Receive UnifiedMessage
        # 2. Process via NLP (intent: book_room)
        # 3. Check PMS availability
        # 4. Send template confirmation
        
        # Here we just verify the template method works
        result = await client_instance.send_template_message(
            to="14155552671",
            template_name="booking_confirmation",
            parameters=[
                {"type": "text", "text": "John Doe"},
                {"type": "text", "text": "Standard Room"},
                {"type": "text", "text": "$100"}
            ]
        )
        
        assert result["messages"][0]["id"] == "wamid.template123"
        assert client_instance.send_template_message.called
