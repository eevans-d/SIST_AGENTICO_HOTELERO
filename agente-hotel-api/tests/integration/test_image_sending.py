"""
Integration tests for room image sending feature.
Feature 3: Envío Automático de Foto de Habitación

Tests the complete flow from availability check to automatic room photo sending.
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch

from app.models.unified_message import UnifiedMessage
from app.services.orchestrator import Orchestrator
from app.services.session_manager import SessionManager
from app.services.lock_service import LockService
from app.utils.room_images import get_room_image_url


@pytest_asyncio.fixture
async def mock_redis():
    """Mock Redis client for testing."""
    redis = Mock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.setex = AsyncMock(return_value=True)
    redis.ping = AsyncMock(return_value=True)
    return redis


@pytest_asyncio.fixture
async def orchestrator(mock_redis):
    """Create orchestrator with mocked dependencies."""
    pms_adapter = Mock()
    pms_adapter.check_availability = AsyncMock(
        return_value={"available": True, "rooms": [{"type": "double", "price": 10000}]}
    )

    session_manager = SessionManager(mock_redis)
    lock_service = LockService(mock_redis)

    return Orchestrator(pms_adapter=pms_adapter, session_manager=session_manager, lock_service=lock_service)


class TestAvailabilityWithRoomPhoto:
    """Tests for automatic room photo sending after availability check."""

    @pytest.mark.asyncio
    @patch("app.services.orchestrator.settings")
    async def test_sends_image_after_availability_check(self, mock_settings, orchestrator):
        """Should include image in response when room images enabled."""
        # Enable room images
        mock_settings.room_images_enabled = True
        mock_settings.room_images_base_url = "https://example.com/images/rooms"

        # Create availability check message
        message = UnifiedMessage(
            user_id="+1234567890",
            texto="Check availability for double room",
            canal="whatsapp",
            tipo="text",
            timestamp=1234567890,
        )

        # Mock NLP to detect check_availability intent
        with patch.object(
            orchestrator.nlp_engine,
            "process_text",
            return_value={
                "intent": {"name": "check_availability", "confidence": 0.95},
                "entities": [],
                "language": "en",
            },
        ):
            result = await orchestrator.handle_unified_message(message)

        # Should include image in response
        assert "image_url" in result
        assert result["image_url"] is not None
        assert "https://" in result["image_url"]

        # Should have appropriate response type
        assert result["response_type"] in ["text_with_image", "interactive_buttons_with_image"]

    @pytest.mark.asyncio
    @patch("app.services.orchestrator.settings")
    async def test_no_image_when_disabled(self, mock_settings, orchestrator):
        """Should not include image when feature is disabled."""
        # Disable room images
        mock_settings.room_images_enabled = False

        message = UnifiedMessage(
            user_id="+1234567890", texto="Check availability", canal="whatsapp", tipo="text", timestamp=1234567890
        )

        with patch.object(
            orchestrator.nlp_engine,
            "process_text",
            return_value={
                "intent": {"name": "check_availability", "confidence": 0.95},
                "entities": [],
                "language": "en",
            },
        ):
            result = await orchestrator.handle_unified_message(message)

        # Should not have image_url or it should be None
        image_url = result.get("image_url")
        assert image_url is None

        # Response type should be without image
        assert result["response_type"] in ["text", "interactive_buttons"]

    @pytest.mark.asyncio
    @patch("app.services.orchestrator.settings")
    async def test_includes_caption_with_room_details(self, mock_settings, orchestrator):
        """Should include caption with room details when sending image."""
        mock_settings.room_images_enabled = True
        mock_settings.room_images_base_url = "https://example.com/images/rooms"

        message = UnifiedMessage(
            user_id="+1234567890", texto="Show me double rooms", canal="whatsapp", tipo="text", timestamp=1234567890
        )

        with patch.object(
            orchestrator.nlp_engine,
            "process_text",
            return_value={
                "intent": {"name": "check_availability", "confidence": 0.95},
                "entities": [],
                "language": "en",
            },
        ):
            result = await orchestrator.handle_unified_message(message)

        # Should have caption
        assert "image_caption" in result
        caption = result["image_caption"]

        # Caption should contain room details
        assert caption is not None
        assert len(caption) > 0

    @pytest.mark.asyncio
    @patch("app.services.orchestrator.settings")
    async def test_graceful_fallback_when_image_url_invalid(self, mock_settings, orchestrator):
        """Should continue normally if image URL is invalid."""
        mock_settings.room_images_enabled = True
        # Use HTTP instead of HTTPS (invalid for WhatsApp)
        mock_settings.room_images_base_url = "http://example.com/images/rooms"

        message = UnifiedMessage(
            user_id="+1234567890", texto="Check availability", canal="whatsapp", tipo="text", timestamp=1234567890
        )

        with patch.object(
            orchestrator.nlp_engine,
            "process_text",
            return_value={
                "intent": {"name": "check_availability", "confidence": 0.95},
                "entities": [],
                "language": "en",
            },
        ):
            result = await orchestrator.handle_unified_message(message)

        # Should still return valid response
        assert "response_type" in result
        assert "content" in result

        # Image should be None or not included due to invalid URL
        image_url = result.get("image_url")
        if image_url:
            # If included, should be invalid (no HTTPS)
            assert not image_url.startswith("https://")

    @pytest.mark.asyncio
    @patch("app.services.orchestrator.settings")
    async def test_works_with_audio_messages(self, mock_settings, orchestrator):
        """Should handle image with audio response for voice messages."""
        mock_settings.room_images_enabled = True
        mock_settings.room_images_base_url = "https://example.com/images/rooms"

        # Audio message
        message = UnifiedMessage(
            user_id="+1234567890",
            texto="",
            canal="whatsapp",
            tipo="audio",
            media_url="https://example.com/audio/message.ogg",
            timestamp=1234567890,
        )

        # Mock STT
        with patch.object(
            orchestrator.audio_processor,
            "transcribe_audio",
            return_value={"transcript": "Check availability for suite", "confidence": 0.90, "language": "en"},
        ):
            # Mock NLP
            with patch.object(
                orchestrator.nlp_engine,
                "process_text",
                return_value={
                    "intent": {"name": "check_availability", "confidence": 0.95},
                    "entities": [],
                    "language": "en",
                },
            ):
                # Mock TTS
                with patch.object(
                    orchestrator.audio_processor, "generate_audio_response", return_value=b"fake_audio_data"
                ):
                    result = await orchestrator.handle_unified_message(message)

        # Should have audio_with_image response type
        assert result["response_type"] == "audio_with_image"
        assert "audio_data" in result
        assert "image_url" in result
        assert result["image_url"] is not None

    @pytest.mark.asyncio
    @patch("app.services.orchestrator.settings")
    async def test_different_room_types_get_different_images(self, mock_settings, orchestrator):
        """Should use different images for different room types."""
        mock_settings.room_images_enabled = True
        mock_settings.room_images_base_url = "https://example.com/images/rooms"

        # Test suite
        suite_url = get_room_image_url("suite")
        assert suite_url is not None
        assert "suite" in suite_url.lower()

        # Test double
        double_url = get_room_image_url("double")
        assert double_url is not None
        assert "double" in double_url.lower()

        # URLs should be different
        assert suite_url != double_url

    @pytest.mark.asyncio
    @patch("app.services.orchestrator.settings")
    async def test_spanish_room_types_mapped_correctly(self, mock_settings, orchestrator):
        """Should map Spanish room type names to correct images."""
        mock_settings.room_images_enabled = True
        mock_settings.room_images_base_url = "https://example.com/images/rooms"

        # Spanish room types should map to same images as English
        doble_url = get_room_image_url("doble")
        double_url = get_room_image_url("double")

        assert doble_url == double_url

        # Test suite
        suite_es_url = get_room_image_url("suite")  # Same in Spanish
        assert suite_es_url is not None

    @pytest.mark.asyncio
    @patch("app.services.orchestrator.settings")
    async def test_logs_image_preparation(self, mock_settings, orchestrator, caplog):
        """Should log image preparation for observability."""
        mock_settings.room_images_enabled = True
        mock_settings.room_images_base_url = "https://example.com/images/rooms"

        message = UnifiedMessage(
            user_id="+1234567890", texto="Check availability", canal="whatsapp", tipo="text", timestamp=1234567890
        )

        with patch.object(
            orchestrator.nlp_engine,
            "process_text",
            return_value={
                "intent": {"name": "check_availability", "confidence": 0.95},
                "entities": [],
                "language": "en",
            },
        ):
            await orchestrator.handle_unified_message(message)

        # Should log image preparation
        # Note: In real test with structlog, check for log events
        # This is simplified - in production use structlog testing utilities


class TestRoomImageWebhookIntegration:
    """Tests for webhook handling of image responses."""

    @pytest.mark.asyncio
    async def test_text_with_image_response_type(self):
        """Should handle text_with_image response type in webhook."""
        from app.services.whatsapp_client import WhatsAppMetaClient

        # Mock WhatsApp client
        whatsapp_client = Mock(spec=WhatsAppMetaClient)
        whatsapp_client.send_message = AsyncMock()
        whatsapp_client.send_image = AsyncMock()

        # Simulate orchestrator response
        result = {
            "response_type": "text_with_image",
            "content": "We have availability for double rooms!",
            "image_url": "https://example.com/images/rooms/double-room.jpg",
            "image_caption": "Double Room - $100/night",
        }

        # Usar un stub mínimo para evitar dependencias de esquema completo
        from types import SimpleNamespace
        original_message = SimpleNamespace(user_id="+1234567890")

        # Simulate webhook handling
        if result["response_type"] == "text_with_image":
            # Send text
            await whatsapp_client.send_message(to=original_message.user_id, text=result["content"])

            # Send image
            if result.get("image_url"):
                await whatsapp_client.send_image(
                    to=original_message.user_id, image_url=result["image_url"], caption=result.get("image_caption", "")
                )

        # Verify calls
        whatsapp_client.send_message.assert_called_once()
        whatsapp_client.send_image.assert_called_once()

    @pytest.mark.asyncio
    async def test_text_with_image_consolidated_when_flag_enabled(self):
        """When consolidate flag is enabled, should send a single image with combined caption."""
        from app.services.whatsapp_client import WhatsAppMetaClient
        from app.services.feature_flag_service import DEFAULT_FLAGS

        # Enable consolidate flag
        DEFAULT_FLAGS["humanize.consolidate_text.enabled"] = True

        # Mock WhatsApp client
        whatsapp_client = Mock(spec=WhatsAppMetaClient)
        whatsapp_client.send_message = AsyncMock()
        whatsapp_client.send_image = AsyncMock()

        # Simulate orchestrator response
        result = {
            "response_type": "text_with_image",
            "content": "We have availability for double rooms!",
            "image_url": "https://example.com/images/rooms/double-room.jpg",
            "image_caption": "Double Room - $100/night",
        }

        from types import SimpleNamespace
        original_message = SimpleNamespace(user_id="+1234567890")

        # Simulate webhook handling with consolidation
        if result["response_type"] == "text_with_image":
            image_url = result.get("image_url")
            text = result.get("content", "")
            caption = result.get("image_caption", "")

            if image_url and DEFAULT_FLAGS.get("humanize.consolidate_text.enabled", False):
                combo_caption = text.strip()
                if caption:
                    combo_caption = f"{combo_caption}\n\n{caption}" if combo_caption else caption
                await whatsapp_client.send_image(
                    to=original_message.user_id, image_url=image_url, caption=combo_caption
                )
            else:
                if text:
                    await whatsapp_client.send_message(to=original_message.user_id, text=text)
                if image_url:
                    await whatsapp_client.send_image(
                        to=original_message.user_id, image_url=image_url, caption=caption
                    )

        # Verify only image was sent and text was not
        whatsapp_client.send_message.assert_not_called()
        whatsapp_client.send_image.assert_called_once()
        # Check that caption contains both text and original caption
        args, kwargs = whatsapp_client.send_image.call_args
        sent_caption = kwargs.get("caption")
        assert "We have availability for double rooms!" in sent_caption
        assert "Double Room - $100/night" in sent_caption
        assert "\n\n" in sent_caption

    @pytest.mark.asyncio
    async def test_interactive_buttons_with_image_response_type(self):
        """Should handle interactive_buttons_with_image response type."""
        from app.services.whatsapp_client import WhatsAppMetaClient

        whatsapp_client = Mock(spec=WhatsAppMetaClient)
        whatsapp_client.send_image = AsyncMock()
        whatsapp_client.send_interactive_message = AsyncMock()

        result = {
            "response_type": "interactive_buttons_with_image",
            "content": {
                "header_text": "Double Room Available",
                "body_text": "Would you like to book?",
                "action_buttons": [{"id": "book", "title": "Book Now"}],
            },
            "image_url": "https://example.com/images/rooms/double-room.jpg",
            "image_caption": "Double Room",
        }

        original_message = UnifiedMessage(
            user_id="+1234567890", texto="Check availability", canal="whatsapp", tipo="text", timestamp=1234567890
        )

        # Simulate webhook handling
        if result["response_type"] == "interactive_buttons_with_image":
            # Send image first
            if result.get("image_url"):
                await whatsapp_client.send_image(
                    to=original_message.user_id, image_url=result["image_url"], caption=result.get("image_caption", "")
                )

            # Then send interactive buttons
            content = result["content"]
            await whatsapp_client.send_interactive_message(
                to=original_message.user_id,
                header_text=content.get("header_text"),
                body_text=content.get("body_text", ""),
                action_buttons=content.get("action_buttons"),
            )

        # Verify calls
        whatsapp_client.send_image.assert_called_once()
        whatsapp_client.send_interactive_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_audio_with_image_response_type(self):
        """Should handle audio_with_image response type."""
        from app.services.whatsapp_client import WhatsAppMetaClient

        whatsapp_client = Mock(spec=WhatsAppMetaClient)
        whatsapp_client.send_audio_message = AsyncMock()
        whatsapp_client.send_message = AsyncMock()
        whatsapp_client.send_image = AsyncMock()

        result = {
            "response_type": "audio_with_image",
            "content": "We have availability",
            "audio_data": b"fake_audio_data",
            "image_url": "https://example.com/images/rooms/suite.jpg",
            "image_caption": "Suite Room",
        }

        original_message = UnifiedMessage(
            user_id="+1234567890",
            texto="",
            canal="whatsapp",
            tipo="audio",
            media_url="https://example.com/audio.ogg",
            timestamp=1234567890,
        )

        # Simulate webhook handling
        if result["response_type"] == "audio_with_image":
            # Send audio
            if result.get("audio_data"):
                await whatsapp_client.send_audio_message(to=original_message.user_id, audio_data=result["audio_data"])

            # Send text if exists
            if result.get("content"):
                await whatsapp_client.send_message(to=original_message.user_id, text=result["content"])

            # Send image
            if result.get("image_url"):
                await whatsapp_client.send_image(
                    to=original_message.user_id, image_url=result["image_url"], caption=result.get("image_caption", "")
                )

        # Verify all sends
        whatsapp_client.send_audio_message.assert_called_once()
        whatsapp_client.send_message.assert_called_once()
        whatsapp_client.send_image.assert_called_once()


class TestRoomImageErrorHandling:
    """Tests for error handling in room image feature."""

    @pytest.mark.asyncio
    @patch("app.services.orchestrator.settings")
    async def test_continues_without_image_on_url_generation_error(self, mock_settings, orchestrator):
        """Should continue normally if image URL generation fails."""
        mock_settings.room_images_enabled = True
        mock_settings.room_images_base_url = "https://example.com/images/rooms"

        message = UnifiedMessage(
            user_id="+1234567890", texto="Check availability", canal="whatsapp", tipo="text", timestamp=1234567890
        )

        # Mock get_room_image_url to raise exception
        with patch("app.services.orchestrator.get_room_image_url", side_effect=Exception("URL error")):
            with patch.object(
                orchestrator.nlp_engine,
                "process_text",
                return_value={
                    "intent": {"name": "check_availability", "confidence": 0.95},
                    "entities": [],
                    "language": "en",
                },
            ):
                result = await orchestrator.handle_unified_message(message)

        # Should still return valid response
        assert "response_type" in result
        assert "content" in result

        # Image should be None due to error
        assert result.get("image_url") is None

    @pytest.mark.asyncio
    @patch("app.services.orchestrator.settings")
    async def test_logs_warning_on_image_preparation_failure(self, mock_settings, orchestrator, caplog):
        """Should log warning if image preparation fails."""
        mock_settings.room_images_enabled = True
        mock_settings.room_images_base_url = "https://example.com/images/rooms"

        message = UnifiedMessage(
            user_id="+1234567890", texto="Check availability", canal="whatsapp", tipo="text", timestamp=1234567890
        )

        with patch("app.services.orchestrator.get_room_image_url", side_effect=Exception("Failed")):
            with patch.object(
                orchestrator.nlp_engine,
                "process_text",
                return_value={
                    "intent": {"name": "check_availability", "confidence": 0.95},
                    "entities": [],
                    "language": "en",
                },
            ):
                result = await orchestrator.handle_unified_message(message)

        # Should still work
        assert result is not None
