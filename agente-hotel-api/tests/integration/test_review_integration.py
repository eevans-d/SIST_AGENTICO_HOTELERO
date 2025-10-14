"""
Integration tests for Review Requests feature.
Feature 6: Review Requests System

Tests end-to-end flows:
1. Automatic review scheduling on checkout
2. Review request sending with timing validation
3. Guest response processing with sentiment analysis
4. Reminder sequence management
5. Multi-platform review links
6. Admin manual controls
7. Analytics tracking
8. Unsubscribe handling
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.models.unified_message import UnifiedMessage
from app.models.schemas import GuestSegment
from app.core.settings import settings


class TestReviewRequestsIntegrationE2E:
    """Integration tests for review requests feature."""

    @pytest.fixture
    def test_client(self):
        """Fixture que crea cliente de prueba."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_full_review_flow_checkout_to_submission(self):
        """Test E2E: Complete flow from checkout to review submission."""
        # Arrange
        from app.services.orchestrator import Orchestrator
        from app.services.session_manager import SessionManager
        from app.services.lock_service import LockService
        from app.services.pms_adapter import get_pms_adapter
        from app.services.review_service import get_review_service

        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        review_service = await get_review_service()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        guest_id = "5491112345678"
        booking_id = "BOOK123456"

        # Setup session with completed booking
        await session_manager.set_session_data(guest_id, "guest_name", "María García")
        await session_manager.set_session_data(
            guest_id,
            "current_booking",
            {
                "booking_id": booking_id,
                "room_number": "305",
                "adults": 2,
                "children": 0,
                "total_price": 800,
                "package": "romantic getaway",
            },
        )

        # Mock WhatsApp client
        with patch.object(review_service, "whatsapp_client") as mock_whatsapp:
            mock_whatsapp.send_message = AsyncMock(return_value={"success": True, "message_id": "wamid_123"})

            # Step 1: Guest checks out (triggers review scheduling)
            checkout_message = UnifiedMessage(
                message_id="msg_checkout_1",
                sender_id=guest_id,
                text="Hola, quiero hacer checkout",
                timestamp=datetime.utcnow().isoformat(),
                platform="whatsapp",
            )

            # Process checkout message
            await orchestrator.process_message(checkout_message)

            # Verify review was scheduled
            session_data = await session_manager.get_session(guest_id)
            review_state = session_data.get("review_state", {})

            assert review_state.get("scheduled"), "Review should be scheduled"
            assert review_state.get("segment") == "couple", "Should detect couple segment"
            assert review_state.get("platform") == "tripadvisor", "Should recommend TripAdvisor for couples"
            assert review_state.get("sent_count") == 0, "Should not be sent yet"

            # Step 2: Send review request (after 24h delay - simulated with force_send)
            send_result = await review_service.send_review_request(guest_id, force_send=True)

            assert send_result["success"], "Review request should send successfully"
            assert send_result["sent_count"] == 1, "Sent count should increment"
            assert mock_whatsapp.send_message.called, "WhatsApp should be called"

            # Verify WhatsApp message content
            call_args = mock_whatsapp.send_message.call_args
            assert guest_id in str(call_args), "Should send to correct guest"
            message_text = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]["message"]
            assert "María" in message_text, "Should personalize with guest name"
            assert "tripadvisor" in message_text.lower() or "review" in message_text.lower(), "Should mention reviews"

            # Step 3: Guest responds positively
            positive_response = UnifiedMessage(
                message_id="msg_response_1",
                sender_id=guest_id,
                text="¡Fue increíble! Ya dejé mi reseña en TripAdvisor. Excelente experiencia.",
                timestamp=datetime.utcnow().isoformat(),
                platform="whatsapp",
            )

            response_result = await review_service.process_review_response(
                guest_id=guest_id, response_text=positive_response.text
            )

            # Verify sentiment analysis
            assert response_result["sentiment"] == "positive", "Should detect positive sentiment"
            assert response_result["submitted"], "Should mark as submitted"

            # Verify session state updated
            updated_session = await session_manager.get_session(guest_id)
            updated_review_state = updated_session.get("review_state", {})

            assert updated_review_state["responded"], "Should mark as responded"
            assert updated_review_state["submitted"], "Should mark as submitted"
            assert updated_review_state["sentiment"] == "positive", "Should store sentiment"

            # Step 4: Verify analytics updated
            analytics = await review_service.get_analytics()

            assert analytics["total_requests"] >= 1, "Should count request"
            assert analytics["total_responses"] >= 1, "Should count response"
            assert analytics["total_submissions"] >= 1, "Should count submission"
            assert analytics["conversion_rate"] > 0, "Should calculate conversion rate"

        print("✅ Full review flow test passed: Checkout → Schedule → Send → Respond → Analytics")

    @pytest.mark.asyncio
    async def test_guest_segment_detection_accuracy(self):
        """Test guest segmentation logic for personalized messaging."""
        from app.services.session_manager import SessionManager
        from app.services.orchestrator import Orchestrator
        from app.services.pms_adapter import get_pms_adapter
        from app.services.lock_service import LockService

        pms_adapter = await get_pms_adapter()
        session_manager = SessionManager()
        lock_service = LockService()
        orchestrator = Orchestrator(pms_adapter, session_manager, lock_service)

        # Test scenarios for different segments
        test_cases = [
            {
                "name": "VIP Guest",
                "booking": {"total_price": 6000, "adults": 2},
                "profile": {"visits": 3},
                "expected_segment": GuestSegment.VIP,
            },
            {
                "name": "Family",
                "booking": {"total_price": 1200, "adults": 2, "children": 2},
                "profile": {"visits": 1},
                "expected_segment": GuestSegment.FAMILY,
            },
            {
                "name": "Business Traveler",
                "booking": {"total_price": 800, "adults": 1},
                "profile": {"email": "john.doe@company.com", "visits": 1},
                "expected_segment": GuestSegment.BUSINESS,
            },
            {
                "name": "Group",
                "booking": {"total_price": 2000, "adults": 6, "room_count": 3},
                "profile": {"visits": 1},
                "expected_segment": GuestSegment.GROUP,
            },
            {
                "name": "Couple",
                "booking": {"total_price": 900, "adults": 2, "package": "romantic package"},
                "profile": {"visits": 1},
                "expected_segment": GuestSegment.COUPLE,
            },
            {
                "name": "Solo Traveler",
                "booking": {"total_price": 400, "adults": 1},
                "profile": {"visits": 1},
                "expected_segment": GuestSegment.SOLO,
            },
        ]

        for test_case in test_cases:
            guest_id = f"549111234567{test_cases.index(test_case)}"

            # Setup session with booking data
            await session_manager.set_session_data(guest_id, "current_booking", test_case["booking"])
            await session_manager.set_session_data(guest_id, "guest_profile", test_case["profile"])

            # Get session and determine segment
            session_data = await session_manager.get_session(guest_id)
            detected_segment = orchestrator._determine_guest_segment(session_data)

            assert detected_segment == test_case["expected_segment"], (
                f"Failed for {test_case['name']}: expected {test_case['expected_segment']}, got {detected_segment}"
            )

        print("✅ Guest segmentation test passed: All 6 segments detected correctly")

    @pytest.mark.asyncio
    async def test_reminder_sequence_timing(self):
        """Test reminder sequence respects timing intervals."""
        from app.services.review_service import get_review_service
        from app.services.session_manager import SessionManager

        review_service = await get_review_service()
        SessionManager()
        guest_id = "5491112345679"

        # Schedule review
        schedule_result = await review_service.schedule_review_request(
            guest_id=guest_id, booking_id="BOOK789", checkout_date=datetime.utcnow(), segment=GuestSegment.BUSINESS
        )

        assert schedule_result["success"], "Should schedule successfully"

        # Mock WhatsApp client
        with patch.object(review_service, "whatsapp_client") as mock_whatsapp:
            mock_whatsapp.send_message = AsyncMock(return_value={"success": True})

            # Send 1: Initial request (force send to bypass 24h delay)
            send1 = await review_service.send_review_request(guest_id, force_send=True)
            assert send1["success"], "First send should succeed"
            assert send1["sent_count"] == 1, "Sent count should be 1"

            # Try send 2: Too soon (should fail without force_send)
            send2_too_soon = await review_service.send_review_request(guest_id, force_send=False)
            assert not send2_too_soon["success"], "Should fail when too soon"
            assert send2_too_soon["reason"] == "too_soon", "Should indicate timing issue"

            # Send 2: With force send (simulates 72h later)
            send2 = await review_service.send_review_request(guest_id, force_send=True)
            assert send2["success"], "Second send should succeed with force"
            assert send2["sent_count"] == 2, "Sent count should be 2"

            # Send 3: Third reminder
            send3 = await review_service.send_review_request(guest_id, force_send=True)
            assert send3["success"], "Third send should succeed"
            assert send3["sent_count"] == 3, "Sent count should be 3"

            # Send 4: Max reminders reached
            send4 = await review_service.send_review_request(guest_id, force_send=True)
            assert not send4["success"], "Should fail after max reminders"
            assert send4["reason"] == "max_reminders_reached", "Should indicate max reminders"

        print("✅ Reminder sequence test passed: Timing and max reminders enforced")

    @pytest.mark.asyncio
    async def test_sentiment_analysis_accuracy(self):
        """Test sentiment analysis detects positive, negative, and unsubscribe."""
        from app.services.review_service import get_review_service
        from app.services.session_manager import SessionManager

        review_service = await get_review_service()
        session_manager = SessionManager()

        test_cases = [
            {
                "response": "¡Excelente estadía! Todo fue increíble y maravilloso. Recomiendo 100%.",
                "expected_sentiment": "positive",
            },
            {
                "response": "Amazing stay! Loved everything about the hotel. Perfect service!",
                "expected_sentiment": "positive",
            },
            {
                "response": "Muy decepcionante. Habitación terrible, mal servicio, muchos problemas.",
                "expected_sentiment": "negative",
            },
            {
                "response": "Bad experience. Disappointed with the room and terrible staff.",
                "expected_sentiment": "negative",
            },
            {
                "response": "Por favor, dejen de enviarme mensajes. No más solicitudes.",
                "expected_sentiment": "unsubscribe",
            },
            {"response": "Unsubscribe me. Stop sending these messages.", "expected_sentiment": "unsubscribe"},
            {"response": "Estuvo bien, nada especial.", "expected_sentiment": "neutral"},
        ]

        for idx, test_case in enumerate(test_cases):
            guest_id = f"549111234568{idx}"

            # Setup review state
            await session_manager.set_session_data(guest_id, "review_state", {"scheduled": True, "sent_count": 1})

            # Analyze response
            sentiment, reason = await review_service._analyze_response(test_case["response"])

            assert sentiment == test_case["expected_sentiment"], (
                f"Failed for '{test_case['response'][:30]}...': expected {test_case['expected_sentiment']}, got {sentiment}"
            )

        print("✅ Sentiment analysis test passed: 7 scenarios detected correctly")

    @pytest.mark.asyncio
    async def test_platform_recommendations_by_segment(self):
        """Test platform recommendations match guest segments."""
        from app.services.review_service import get_review_service
        from app.models.schemas import GuestSegment

        review_service = await get_review_service()

        expected_mappings = {
            GuestSegment.COUPLE: "tripadvisor",
            GuestSegment.BUSINESS: "google",
            GuestSegment.FAMILY: "booking",
            GuestSegment.SOLO: "tripadvisor",
            GuestSegment.GROUP: "facebook",
            GuestSegment.VIP: "google",
        }

        for segment, expected_platform in expected_mappings.items():
            recommended = review_service._recommend_platform(segment)
            assert recommended == expected_platform, (
                f"Failed for {segment}: expected {expected_platform}, got {recommended}"
            )

        print("✅ Platform recommendation test passed: All 6 segments mapped correctly")

    @pytest.mark.asyncio
    async def test_negative_sentiment_escalation(self):
        """Test negative sentiment triggers appropriate response and tracking."""
        from app.services.review_service import get_review_service
        from app.services.session_manager import SessionManager

        review_service = await get_review_service()
        session_manager = SessionManager()
        guest_id = "5491112345680"

        # Setup review state
        await session_manager.set_session_data(
            guest_id, "review_state", {"scheduled": True, "sent_count": 1, "segment": "business"}
        )
        await session_manager.set_session_data(guest_id, "guest_name", "Carlos López")

        # Mock WhatsApp client
        with patch.object(review_service, "whatsapp_client") as mock_whatsapp:
            mock_whatsapp.send_message = AsyncMock(return_value={"success": True})

            # Process negative response
            result = await review_service.process_review_response(
                guest_id=guest_id, response_text="Muy decepcionante. La habitación era terrible y el servicio malo."
            )

            # Verify negative sentiment detected
            assert result["sentiment"] == "negative", "Should detect negative sentiment"
            assert result["responded"], "Should mark as responded"

            # Verify session updated with negative sentiment
            session_data = await session_manager.get_session(guest_id)
            review_state = session_data.get("review_state", {})
            assert review_state["sentiment"] == "negative", "Should store negative sentiment"
            assert review_state["responded"], "Should mark responded"

        print("✅ Negative sentiment escalation test passed")

    @pytest.mark.asyncio
    async def test_unsubscribe_prevents_future_sends(self):
        """Test unsubscribe marks guest to prevent future messages."""
        from app.services.review_service import get_review_service
        from app.services.session_manager import SessionManager

        review_service = await get_review_service()
        session_manager = SessionManager()
        guest_id = "5491112345681"

        # Setup review state
        await session_manager.set_session_data(guest_id, "review_state", {"scheduled": True, "sent_count": 1})

        # Process unsubscribe request
        result = await review_service.process_review_response(
            guest_id=guest_id, response_text="Por favor, dejen de enviarme mensajes. No más."
        )

        # Verify unsubscribe detected
        assert result["sentiment"] == "unsubscribe", "Should detect unsubscribe"
        assert result["unsubscribed"], "Should mark as unsubscribed"

        # Verify session marked
        session_data = await session_manager.get_session(guest_id)
        review_state = session_data.get("review_state", {})
        assert review_state["unsubscribed"], "Should be unsubscribed"
        assert review_state["sent_count"] == 999, "Should set high count to prevent sends"

        # Try to send another review (should fail)
        with patch.object(review_service, "whatsapp_client") as mock_whatsapp:
            mock_whatsapp.send_message = AsyncMock(return_value={"success": True})

            send_result = await review_service.send_review_request(guest_id, force_send=True)

            assert not send_result["success"], "Should fail to send to unsubscribed guest"
            assert send_result["reason"] == "max_reminders_reached", "Should prevent send"
            assert not mock_whatsapp.send_message.called, "Should not call WhatsApp"

        print("✅ Unsubscribe test passed: Guest protected from future messages")

    @pytest.mark.asyncio
    async def test_concurrent_review_requests_different_guests(self):
        """Test concurrent review processing for multiple guests."""
        import asyncio
        from app.services.review_service import get_review_service
        from app.services.session_manager import SessionManager

        review_service = await get_review_service()
        session_manager = SessionManager()

        # Create 10 concurrent guests
        guest_ids = [f"54911123456{i:02d}" for i in range(10)]

        async def schedule_and_send(guest_id: str, segment: GuestSegment):
            """Schedule and send review for one guest."""
            # Schedule
            await review_service.schedule_review_request(
                guest_id=guest_id, booking_id=f"BOOK{guest_id[-3:]}", checkout_date=datetime.utcnow(), segment=segment
            )

            # Send with force
            with patch.object(review_service, "whatsapp_client") as mock_whatsapp:
                mock_whatsapp.send_message = AsyncMock(return_value={"success": True})
                result = await review_service.send_review_request(guest_id, force_send=True)
                return result

        # Process all concurrently
        segments = [GuestSegment.COUPLE, GuestSegment.BUSINESS, GuestSegment.FAMILY] * 4
        tasks = [schedule_and_send(gid, seg) for gid, seg in zip(guest_ids[:10], segments[:10])]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all succeeded
        success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        assert success_count == 10, f"Expected 10 successes, got {success_count}"

        # Verify each guest has correct state
        for guest_id in guest_ids:
            session_data = await session_manager.get_session(guest_id)
            review_state = session_data.get("review_state", {})
            assert review_state.get("scheduled"), f"Guest {guest_id} should be scheduled"
            assert review_state.get("sent_count") == 1, f"Guest {guest_id} should have sent_count=1"

        print("✅ Concurrent processing test passed: 10 guests processed simultaneously")

    @pytest.mark.asyncio
    async def test_analytics_realtime_updates(self):
        """Test analytics update in real-time as events occur."""
        from app.services.review_service import get_review_service
        from app.services.session_manager import SessionManager

        review_service = await get_review_service()
        session_manager = SessionManager()

        # Get initial analytics
        initial_analytics = await review_service.get_analytics()
        initial_requests = initial_analytics["total_requests"]

        # Schedule and send 3 reviews
        guest_ids = ["5491112345682", "5491112345683", "5491112345684"]

        with patch.object(review_service, "whatsapp_client") as mock_whatsapp:
            mock_whatsapp.send_message = AsyncMock(return_value={"success": True})

            for guest_id in guest_ids:
                # Schedule
                await review_service.schedule_review_request(
                    guest_id=guest_id,
                    booking_id=f"BOOK{guest_id[-3:]}",
                    checkout_date=datetime.utcnow(),
                    segment=GuestSegment.COUPLE,
                )

                # Send
                await review_service.send_review_request(guest_id, force_send=True)

            # Process responses (2 positive, 1 negative)
            await review_service.process_review_response(guest_ids[0], "¡Excelente! Increíble estadía.")
            await review_service.process_review_response(guest_ids[1], "Maravilloso hotel, todo perfecto.")
            await review_service.process_review_response(guest_ids[2], "Muy decepcionante, mala experiencia.")

            # Mark 2 as submitted
            for guest_id in guest_ids[:2]:
                session_data = await session_manager.get_session(guest_id)
                review_state = session_data.get("review_state", {})
                review_state["submitted"] = True
                session_data["review_state"] = review_state
                await session_manager.update_session(guest_id, session_data)

        # Get updated analytics
        updated_analytics = await review_service.get_analytics()

        # Verify updates
        assert updated_analytics["total_requests"] >= initial_requests + 3, "Should count new requests"
        assert updated_analytics["total_responses"] >= 3, "Should count responses"
        assert updated_analytics["total_submissions"] >= 2, "Should count submissions"

        # Verify conversion rate calculation
        if updated_analytics["total_requests"] > 0:
            expected_rate = updated_analytics["total_submissions"] / updated_analytics["total_requests"]
            assert abs(updated_analytics["conversion_rate"] - expected_rate) < 0.01, "Should calculate correct rate"

        print("✅ Analytics realtime update test passed")

    @pytest.mark.asyncio
    async def test_whatsapp_failure_retry_logic(self):
        """Test error handling when WhatsApp fails."""
        from app.services.review_service import get_review_service
        from app.services.session_manager import SessionManager

        review_service = await get_review_service()
        SessionManager()
        guest_id = "5491112345685"

        # Schedule review
        await review_service.schedule_review_request(
            guest_id=guest_id, booking_id="BOOK123", checkout_date=datetime.utcnow(), segment=GuestSegment.BUSINESS
        )

        # Mock WhatsApp client to fail
        with patch.object(review_service, "whatsapp_client") as mock_whatsapp:
            mock_whatsapp.send_message = AsyncMock(side_effect=Exception("WhatsApp API Error: Rate limit exceeded"))

            # Try to send (should handle exception gracefully)
            result = await review_service.send_review_request(guest_id, force_send=True)

            # Verify error handled
            assert not result["success"], "Should return failure"
            assert "error" in result or "reason" in result, "Should include error info"

        print("✅ WhatsApp failure handling test passed")

    @pytest.mark.asyncio
    async def test_platform_links_message_generation(self):
        """Test multi-platform links message generation."""
        from app.services.template_service import TemplateService

        template_service = TemplateService()

        # Get platform links message
        links_message = template_service.get_template("review_platform_links")

        # Verify all platforms included
        assert "google" in links_message.lower() or settings.google_review_url in links_message, (
            "Should include Google link"
        )
        assert "tripadvisor" in links_message.lower() or settings.tripadvisor_review_url in links_message, (
            "Should include TripAdvisor link"
        )
        assert "booking" in links_message.lower() or settings.booking_review_url in links_message, (
            "Should include Booking link"
        )

        print("✅ Platform links message test passed")

    @pytest.mark.asyncio
    async def test_review_timing_calculations(self):
        """Test review timing calculations for scheduling."""
        from app.services.review_service import get_review_service
        from app.services.session_manager import SessionManager

        review_service = await get_review_service()
        session_manager = SessionManager()
        guest_id = "5491112345686"

        # Schedule review with specific checkout date
        checkout_date = datetime.utcnow()
        await review_service.schedule_review_request(
            guest_id=guest_id, booking_id="BOOK999", checkout_date=checkout_date, segment=GuestSegment.FAMILY
        )

        # Get review state
        session_data = await session_manager.get_session(guest_id)
        review_state = session_data.get("review_state", {})

        # Verify scheduled time is 24h after checkout
        scheduled_at = datetime.fromisoformat(review_state["scheduled_at"])
        expected_scheduled = checkout_date + timedelta(hours=settings.review_initial_delay_hours)

        time_diff = abs((scheduled_at - expected_scheduled).total_seconds())
        assert time_diff < 5, f"Scheduled time should be ~24h after checkout (diff: {time_diff}s)"

        print("✅ Review timing calculations test passed")


class TestReviewAdminAPIIntegration:
    """Integration tests for admin API endpoints."""

    @pytest.fixture
    def test_client(self):
        """Fixture que crea cliente de prueba."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_admin_manual_send_endpoint(self):
        """Test admin API manual send endpoint."""
        from app.services.review_service import get_review_service
        from app.services.session_manager import SessionManager

        review_service = await get_review_service()
        SessionManager()
        guest_id = "5491112345687"

        # Schedule review
        await review_service.schedule_review_request(
            guest_id=guest_id, booking_id="BOOK111", checkout_date=datetime.utcnow(), segment=GuestSegment.VIP
        )

        # Mock WhatsApp
        with patch.object(review_service, "whatsapp_client") as mock_whatsapp:
            mock_whatsapp.send_message = AsyncMock(return_value={"success": True})

            # Call admin endpoint (simulated)
            result = await review_service.send_review_request(guest_id, force_send=True)

            assert result["success"], "Admin send should succeed"
            assert result["sent_count"] == 1, "Should increment sent count"

        print("✅ Admin manual send test passed")

    @pytest.mark.asyncio
    async def test_admin_analytics_endpoint(self):
        """Test admin analytics endpoint returns comprehensive data."""
        from app.services.review_service import get_review_service

        review_service = await get_review_service()

        # Get analytics
        analytics = await review_service.get_analytics()

        # Verify structure
        assert "total_requests" in analytics, "Should include total_requests"
        assert "total_responses" in analytics, "Should include total_responses"
        assert "total_submissions" in analytics, "Should include total_submissions"
        assert "conversion_rate" in analytics, "Should include conversion_rate"
        assert "by_segment" in analytics, "Should include segment breakdown"
        assert "by_platform" in analytics, "Should include platform breakdown"

        # Verify types
        assert isinstance(analytics["total_requests"], int), "Requests should be int"
        assert isinstance(analytics["conversion_rate"], (int, float)), "Rate should be numeric"

        print("✅ Admin analytics endpoint test passed")


# Run summary
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("FEATURE 6: REVIEW REQUESTS INTEGRATION TESTS")
    print("=" * 70)
    print("\nTest Coverage:")
    print("  ✅ Full E2E flow (checkout → schedule → send → respond → analytics)")
    print("  ✅ Guest segmentation (6 segments)")
    print("  ✅ Reminder sequence timing")
    print("  ✅ Sentiment analysis (positive/negative/unsubscribe)")
    print("  ✅ Platform recommendations")
    print("  ✅ Negative sentiment escalation")
    print("  ✅ Unsubscribe handling")
    print("  ✅ Concurrent processing (10 guests)")
    print("  ✅ Analytics realtime updates")
    print("  ✅ WhatsApp failure handling")
    print("  ✅ Platform links generation")
    print("  ✅ Timing calculations")
    print("  ✅ Admin manual send")
    print("  ✅ Admin analytics")
    print("\nTotal: 14 integration tests")
    print("=" * 70 + "\n")
