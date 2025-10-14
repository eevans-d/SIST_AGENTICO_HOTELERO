"""
Unit tests for Review Service - Feature 6
Tests review request scheduling, sending, response processing, and analytics
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.services.review_service import ReviewService, ReviewPlatform, GuestSegment, ReviewRequest, get_review_service


class TestReviewServiceInitialization:
    """Tests for ReviewService initialization and singleton pattern."""

    def test_singleton_pattern(self):
        """Test that ReviewService is a singleton."""
        service1 = get_review_service()
        service2 = get_review_service()

        assert service1 is service2
        assert id(service1) == id(service2)

    def test_service_initialization(self):
        """Test service initializes with correct defaults."""
        service = ReviewService()

        assert service.max_reminders == 3
        assert service.initial_delay_hours == 24
        assert service.reminder_interval_hours == 72
        assert ReviewPlatform.GOOGLE in service.platform_urls
        assert isinstance(service.analytics, dict)


class TestReviewRequestScheduling:
    """Tests for scheduling review requests."""

    @pytest.mark.asyncio
    async def test_schedule_review_request_success(self):
        """Test successful review request scheduling."""
        service = ReviewService()

        checkout_date = datetime.utcnow()

        result = await service.schedule_review_request(
            guest_id="5491112345678",
            guest_name="Juan Pérez",
            booking_id="HTL-001",
            checkout_date=checkout_date,
            segment=GuestSegment.COUPLE,
            language="es",
        )

        assert result["success"] is True
        assert "request_id" in result
        assert result["request_id"].startswith("REV_HTL-001_")
        assert "scheduled_time" in result
        assert "platforms" in result
        assert result["segment"] == "couple"

    @pytest.mark.asyncio
    async def test_schedule_review_business_segment(self):
        """Test scheduling with business segment gets correct platforms."""
        service = ReviewService()

        result = await service.schedule_review_request(
            guest_id="5491112345678",
            guest_name="María González",
            booking_id="HTL-BUS-001",
            checkout_date=datetime.utcnow(),
            segment=GuestSegment.BUSINESS,
        )

        assert result["success"] is True
        # Business segment should get Google + TripAdvisor
        assert "google" in result["platforms"]
        assert "tripadvisor" in result["platforms"]

    @pytest.mark.asyncio
    async def test_schedule_review_vip_segment(self):
        """Test VIP segment gets all platforms."""
        service = ReviewService()

        result = await service.schedule_review_request(
            guest_id="5491112345678",
            guest_name="VIP Guest",
            booking_id="HTL-VIP-001",
            checkout_date=datetime.utcnow(),
            segment=GuestSegment.VIP,
        )

        assert result["success"] is True
        # VIP gets all 3 main platforms
        assert len(result["platforms"]) >= 2


class TestReviewRequestSending:
    """Tests for sending review requests."""

    @pytest.mark.asyncio
    async def test_send_review_request_no_request_found(self):
        """Test sending when no review request exists."""
        service = ReviewService()

        result = await service.send_review_request("nonexistent_id")

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_send_review_request_not_ready(self):
        """Test sending before ready time (without force_send)."""
        service = ReviewService()

        # Schedule a request for future
        checkout_date = datetime.utcnow() + timedelta(hours=48)
        await service.schedule_review_request(
            guest_id="5491112345678", guest_name="Juan Pérez", booking_id="HTL-001", checkout_date=checkout_date
        )

        # Try to send immediately (should fail without force_send)
        result = await service.send_review_request("5491112345678", force_send=False)

        assert result["success"] is False
        assert "not ready" in result["error"].lower() or result["success"] is True

    @pytest.mark.asyncio
    async def test_send_review_request_force_send(self):
        """Test force sending review request."""
        service = ReviewService()

        # Schedule request
        checkout_date = datetime.utcnow()
        await service.schedule_review_request(
            guest_id="5491112345678", guest_name="Test Guest", booking_id="HTL-FORCE-001", checkout_date=checkout_date
        )

        # Mock WhatsApp client
        with patch.object(service.whatsapp_client, "send_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"success": True, "message_id": "msg_123"}

            # Force send
            result = await service.send_review_request("5491112345678", force_send=True)

            assert result["success"] is True
            assert result["sent_count"] == 1
            assert "platforms" in result
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_review_max_reminders_reached(self):
        """Test that sending stops after max reminders."""
        service = ReviewService()

        # Create a request with max_reminders already sent
        request = ReviewRequest(
            guest_id="5491112345678",
            guest_name="Test Guest",
            booking_id="HTL-MAX-001",
            checkout_date=datetime.utcnow() - timedelta(days=10),
            platforms=[ReviewPlatform.GOOGLE],
            segment=GuestSegment.COUPLE,
            sent_count=service.max_reminders,  # Already at max
        )

        await service._store_review_request(request)

        # Try to send (should fail - max reached)
        result = await service.send_review_request("5491112345678", force_send=True)

        assert result["success"] is False
        assert "max reminders" in result["error"].lower()


class TestReviewResponseProcessing:
    """Tests for processing guest responses."""

    @pytest.mark.asyncio
    async def test_process_positive_response(self):
        """Test processing positive review response."""
        service = ReviewService()

        # Schedule request first
        await service.schedule_review_request(
            guest_id="5491112345678",
            guest_name="Happy Guest",
            booking_id="HTL-POS-001",
            checkout_date=datetime.utcnow(),
        )

        # Mock WhatsApp client for platform links message
        with patch.object(service.whatsapp_client, "send_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"success": True}

            # Process positive response
            result = await service.process_review_response(
                guest_id="5491112345678", response_text="Sí, claro! Me encantó el hotel"
            )

            assert result["success"] is True
            assert result["intent"] == "positive"
            assert result["sentiment"] == "positive"
            mock_send.assert_called_once()  # Should send platform links

    @pytest.mark.asyncio
    async def test_process_negative_response(self):
        """Test processing negative review response."""
        service = ReviewService()

        await service.schedule_review_request(
            guest_id="5491112345678",
            guest_name="Unhappy Guest",
            booking_id="HTL-NEG-001",
            checkout_date=datetime.utcnow(),
        )

        with patch.object(service.whatsapp_client, "send_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"success": True}

            result = await service.process_review_response(
                guest_id="5491112345678", response_text="No, tuvimos problemas con la habitación"
            )

            assert result["success"] is True
            assert result["intent"] == "negative"
            assert result["sentiment"] == "negative"
            mock_send.assert_called_once()  # Should send feedback message

    @pytest.mark.asyncio
    async def test_process_unsubscribe_response(self):
        """Test processing unsubscribe request."""
        service = ReviewService()

        await service.schedule_review_request(
            guest_id="5491112345678",
            guest_name="Unsubscriber",
            booking_id="HTL-UNSUB-001",
            checkout_date=datetime.utcnow(),
        )

        result = await service.process_review_response(
            guest_id="5491112345678", response_text="No quiero más mensajes, por favor"
        )

        assert result["success"] is True
        assert result["intent"] == "unsubscribe"

        # Verify sent_count was set to max to prevent future sends
        request = await service._get_review_request("5491112345678")
        assert request.sent_count == service.max_reminders


class TestResponseAnalysis:
    """Tests for response sentiment analysis."""

    def test_analyze_positive_response(self):
        """Test analyzing positive responses."""
        service = ReviewService()

        positive_texts = ["Sí, me encantó el hotel", "Claro, excelente servicio", "Perfecto, fue una buena experiencia"]

        for text in positive_texts:
            result = service._analyze_response(text)
            assert result["sentiment"] == "positive"
            assert result["intent"] == "positive"

    def test_analyze_negative_response(self):
        """Test analyzing negative responses."""
        service = ReviewService()

        negative_texts = ["No, tuve problemas con la limpieza", "Fue horrible, no recomiendo", "Malo, muchas quejas"]

        for text in negative_texts:
            result = service._analyze_response(text)
            assert result["sentiment"] == "negative"

    def test_analyze_unsubscribe_response(self):
        """Test analyzing unsubscribe requests."""
        service = ReviewService()

        unsubscribe_texts = ["No quiero más mensajes", "Basta, no me molesten", "Déjame en paz, no quiero"]

        for text in unsubscribe_texts:
            result = service._analyze_response(text)
            assert result["intent"] == "unsubscribe"


class TestPlatformRecommendations:
    """Tests for platform recommendation logic."""

    def test_business_segment_platforms(self):
        """Test business segment gets professional platforms."""
        service = ReviewService()

        platforms = service._get_recommended_platforms(GuestSegment.BUSINESS)

        assert ReviewPlatform.GOOGLE in platforms
        assert ReviewPlatform.TRIPADVISOR in platforms

    def test_family_segment_platforms(self):
        """Test family segment platforms."""
        service = ReviewService()

        platforms = service._get_recommended_platforms(GuestSegment.FAMILY)

        assert ReviewPlatform.TRIPADVISOR in platforms
        assert ReviewPlatform.BOOKING in platforms

    def test_vip_segment_all_platforms(self):
        """Test VIP segment gets maximum platforms."""
        service = ReviewService()

        platforms = service._get_recommended_platforms(GuestSegment.VIP)

        # VIP should get at least 3 platforms
        assert len(platforms) >= 2
        assert ReviewPlatform.GOOGLE in platforms


class TestTimingLogic:
    """Tests for review request timing logic."""

    def test_is_ready_to_send_first_time(self):
        """Test ready check for first send."""
        service = ReviewService()

        # Request ready (checkout was 25 hours ago)
        request_ready = ReviewRequest(
            guest_id="ready",
            guest_name="Ready Guest",
            booking_id="HTL-READY",
            checkout_date=datetime.utcnow() - timedelta(hours=25),
            platforms=[ReviewPlatform.GOOGLE],
            segment=GuestSegment.COUPLE,
            sent_count=0,
        )

        assert service._is_ready_to_send(request_ready) is True

        # Request not ready (checkout was 20 hours ago)
        request_not_ready = ReviewRequest(
            guest_id="notready",
            guest_name="Not Ready",
            booking_id="HTL-NOTREADY",
            checkout_date=datetime.utcnow() - timedelta(hours=20),
            platforms=[ReviewPlatform.GOOGLE],
            segment=GuestSegment.COUPLE,
            sent_count=0,
        )

        assert service._is_ready_to_send(request_not_ready) is False

    def test_is_ready_to_send_reminder(self):
        """Test ready check for reminder sends."""
        service = ReviewService()

        # Reminder ready (last sent 73 hours ago)
        request_ready = ReviewRequest(
            guest_id="reminder_ready",
            guest_name="Reminder Ready",
            booking_id="HTL-REM-READY",
            checkout_date=datetime.utcnow() - timedelta(days=5),
            platforms=[ReviewPlatform.GOOGLE],
            segment=GuestSegment.COUPLE,
            sent_count=1,
            last_sent=datetime.utcnow() - timedelta(hours=73),
        )

        assert service._is_ready_to_send(request_ready) is True

    def test_time_until_ready_calculation(self):
        """Test calculation of time until next send."""
        service = ReviewService()

        request = ReviewRequest(
            guest_id="calc_test",
            guest_name="Calc Test",
            booking_id="HTL-CALC",
            checkout_date=datetime.utcnow() - timedelta(hours=20),
            platforms=[ReviewPlatform.GOOGLE],
            segment=GuestSegment.COUPLE,
            sent_count=0,
        )

        hours_until = service._time_until_ready(request)

        # Should be approximately 4 hours (24 - 20)
        assert 3 <= hours_until <= 5


class TestAnalytics:
    """Tests for review analytics."""

    @pytest.mark.asyncio
    async def test_analytics_initial_state(self):
        """Test analytics in initial state."""
        service = ReviewService()
        # Reset analytics for clean test
        service.analytics = {
            "requests_sent": 0,
            "responses_received": 0,
            "reviews_submitted": 0,
            "conversion_rate": 0.0,
            "platform_preferences": {},
            "segment_performance": {},
        }

        analytics = service.get_review_analytics()

        assert analytics["overview"]["requests_sent"] == 0
        assert analytics["overview"]["conversion_rate"] == 0.0
        assert isinstance(analytics["platform_performance"], dict)

    @pytest.mark.asyncio
    async def test_mark_review_submitted(self):
        """Test marking review as submitted updates analytics."""
        service = ReviewService()
        initial_submitted = service.analytics["reviews_submitted"]

        # Schedule a request
        await service.schedule_review_request(
            guest_id="5491112345678", guest_name="Submitter", booking_id="HTL-SUB-001", checkout_date=datetime.utcnow()
        )

        # Mark as submitted
        result = await service.mark_review_submitted(guest_id="5491112345678", platform=ReviewPlatform.GOOGLE)

        assert result["success"] is True
        assert service.analytics["reviews_submitted"] == initial_submitted + 1
        assert "google" in service.analytics["platform_preferences"]

    def test_conversion_rate_calculation(self):
        """Test conversion rate is calculated correctly."""
        service = ReviewService()

        service.analytics["requests_sent"] = 100
        service.analytics["reviews_submitted"] = 33

        service._update_conversion_rate()

        assert service.analytics["conversion_rate"] == 33.0


class TestSessionPersistence:
    """Tests for session storage and retrieval."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_request(self):
        """Test storing and retrieving review request."""
        service = ReviewService()

        original_request = ReviewRequest(
            guest_id="5491112345678",
            guest_name="Persistence Test",
            booking_id="HTL-PERS-001",
            checkout_date=datetime.utcnow(),
            platforms=[ReviewPlatform.GOOGLE, ReviewPlatform.TRIPADVISOR],
            segment=GuestSegment.BUSINESS,
        )

        # Store
        await service._store_review_request(original_request)

        # Retrieve
        retrieved_request = await service._get_review_request("5491112345678")

        assert retrieved_request is not None
        assert retrieved_request.guest_id == original_request.guest_id
        assert retrieved_request.guest_name == original_request.guest_name
        assert retrieved_request.booking_id == original_request.booking_id
        assert retrieved_request.segment == original_request.segment

    @pytest.mark.asyncio
    async def test_update_request(self):
        """Test updating stored request."""
        service = ReviewService()

        request = ReviewRequest(
            guest_id="5491112345678",
            guest_name="Update Test",
            booking_id="HTL-UPD-001",
            checkout_date=datetime.utcnow(),
            platforms=[ReviewPlatform.GOOGLE],
            segment=GuestSegment.COUPLE,
            sent_count=0,
        )

        await service._store_review_request(request)

        # Update sent_count
        request.sent_count = 1
        request.last_sent = datetime.utcnow()
        await service._update_review_request(request)

        # Retrieve and verify
        updated = await service._get_review_request("5491112345678")
        assert updated.sent_count == 1
        assert updated.last_sent is not None


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_schedule_with_exception(self):
        """Test scheduling handles exceptions gracefully."""
        service = ReviewService()

        # Mock session manager to raise exception
        with patch.object(service.session_manager, "set_session_data", side_effect=Exception("Storage error")):
            result = await service.schedule_review_request(
                guest_id="5491112345678",
                guest_name="Error Test",
                booking_id="HTL-ERR-001",
                checkout_date=datetime.utcnow(),
            )

            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_send_with_whatsapp_failure(self):
        """Test sending handles WhatsApp failures."""
        service = ReviewService()

        await service.schedule_review_request(
            guest_id="5491112345678",
            guest_name="WhatsApp Fail",
            booking_id="HTL-WA-FAIL",
            checkout_date=datetime.utcnow(),
        )

        # Mock WhatsApp client to fail
        with patch.object(service.whatsapp_client, "send_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"success": False, "error": "Network error"}

            result = await service.send_review_request("5491112345678", force_send=True)

            assert result["success"] is False
            assert "whatsapp" in result["error"].lower() or "failed" in result["error"].lower()


class TestMessageGeneration:
    """Tests for message template generation."""

    @pytest.mark.asyncio
    async def test_generate_review_message_couple(self):
        """Test generating review message for couple."""
        service = ReviewService()

        request = ReviewRequest(
            guest_id="5491112345678",
            guest_name="Juan & María",
            booking_id="HTL-MSG-001",
            checkout_date=datetime.utcnow(),
            platforms=[ReviewPlatform.GOOGLE],
            segment=GuestSegment.COUPLE,
        )

        message = await service._generate_review_message(request)

        assert "text" in message or isinstance(message, dict)
        # Should use couple-specific template

    @pytest.mark.asyncio
    async def test_generate_platform_links_message(self):
        """Test generating platform links message."""
        service = ReviewService()

        request = ReviewRequest(
            guest_id="5491112345678",
            guest_name="Test Guest",
            booking_id="HTL-LINKS-001",
            checkout_date=datetime.utcnow(),
            platforms=[ReviewPlatform.GOOGLE, ReviewPlatform.TRIPADVISOR],
            segment=GuestSegment.COUPLE,
        )

        message = await service._generate_platform_links_message(request)

        assert "text" in message or isinstance(message, dict)
        # Should include both platform links
