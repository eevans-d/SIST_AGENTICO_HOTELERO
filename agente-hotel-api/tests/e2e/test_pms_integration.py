"""
End-to-End PMS Integration Tests
Comprehensive testing of the complete PMS workflow
"""

import pytest
import asyncio
from datetime import date, timedelta

from app.services.pms.enhanced_pms_service import (
    EnhancedPMSService,
    PMSType,
    Reservation,
    Guest,
    RoomType,
    ReservationStatus,
)
from app.services.pms.intelligent_reservation_manager import ReservationWorkflowState, get_reservation_manager
from app.services.pms.booking_confirmation_service import (
    ConfirmationChannel,
    GuestPreferences,
    get_confirmation_service,
)
from app.services.nlp.hotel_context_processor import ConversationContext
from app.services.template_service import TemplateService


@pytest.fixture
async def pms_service():
    """Mock PMS service for testing"""
    service = EnhancedPMSService(pms_type=PMSType.MOCK)
    await service.start()
    yield service
    await service.stop()


@pytest.fixture
async def reservation_manager(pms_service):
    """Reservation manager with mock PMS"""
    manager = get_reservation_manager(pms_service)
    yield manager


@pytest.fixture
async def confirmation_service():
    """Mock confirmation service"""
    template_service = TemplateService()
    service = get_confirmation_service(template_service)
    yield service


@pytest.fixture
def sample_guest():
    """Sample guest data"""
    return Guest(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="+1-555-0123",
        date_of_birth=date(1985, 5, 15),
        nationality="US",
        id_number="123456789",
    )


@pytest.fixture
def sample_reservation_data():
    """Sample reservation data"""
    tomorrow = date.today() + timedelta(days=1)
    day_after = tomorrow + timedelta(days=2)

    return {
        "checkin_date": tomorrow,
        "checkout_date": day_after,
        "adults": 2,
        "children": 0,
        "room_type": RoomType.DELUXE_DOUBLE,
        "special_requests": ["Late check-in", "High floor"],
    }


class TestPMSAvailabilityCheck:
    """Test availability checking functionality"""

    async def test_basic_availability_check(self, pms_service):
        """Test basic availability check"""

        tomorrow = date.today() + timedelta(days=1)
        day_after = tomorrow + timedelta(days=2)

        availability = await pms_service.check_availability(
            checkin_date=tomorrow, checkout_date=day_after, adults=2, children=0
        )

        assert len(availability) > 0
        assert all(room.available_rooms > 0 for room in availability)
        assert all(len(room.rates) > 0 for room in availability)

        # Verify rate information
        for room in availability:
            for rate in room.rates:
                assert rate.base_rate > 0
                assert rate.currency in ["USD", "EUR"]
                assert rate.rate_plan is not None

    async def test_availability_with_room_type_filter(self, pms_service):
        """Test availability check with specific room types"""

        tomorrow = date.today() + timedelta(days=1)
        day_after = tomorrow + timedelta(days=2)

        availability = await pms_service.check_availability(
            checkin_date=tomorrow,
            checkout_date=day_after,
            adults=2,
            children=0,
            room_types=[RoomType.DELUXE_DOUBLE, RoomType.JUNIOR_SUITE],
        )

        assert len(availability) <= 2
        room_types_found = [room.room_type for room in availability]
        assert all(rt in [RoomType.DELUXE_DOUBLE, RoomType.JUNIOR_SUITE] for rt in room_types_found)

    async def test_availability_no_rooms_available(self, pms_service):
        """Test availability when no rooms available"""

        # Far future date that should have no availability in mock
        far_future = date.today() + timedelta(days=1000)
        day_after = far_future + timedelta(days=1)

        availability = await pms_service.check_availability(
            checkin_date=far_future, checkout_date=day_after, adults=2, children=0
        )

        # Mock service should return empty list for far future dates
        assert len(availability) == 0


class TestReservationManagement:
    """Test reservation CRUD operations"""

    async def test_create_reservation(self, pms_service, sample_guest, sample_reservation_data):
        """Test reservation creation"""

        reservation = Reservation(
            guest=sample_guest,
            room_type=sample_reservation_data["room_type"],
            checkin_date=sample_reservation_data["checkin_date"],
            checkout_date=sample_reservation_data["checkout_date"],
            adults=sample_reservation_data["adults"],
            children=sample_reservation_data["children"],
            special_requests=sample_reservation_data["special_requests"],
        )

        created_reservation = await pms_service.create_reservation(reservation)

        assert created_reservation.reservation_id is not None
        assert created_reservation.confirmation_number is not None
        assert created_reservation.status == ReservationStatus.CONFIRMED
        assert created_reservation.guest.email == sample_guest.email
        assert created_reservation.room_type == sample_reservation_data["room_type"]
        assert created_reservation.total_amount > 0
        assert created_reservation.created_at is not None

    async def test_get_reservation(self, pms_service, sample_guest, sample_reservation_data):
        """Test retrieving reservation"""

        # Create reservation first
        reservation = Reservation(
            guest=sample_guest,
            room_type=sample_reservation_data["room_type"],
            checkin_date=sample_reservation_data["checkin_date"],
            checkout_date=sample_reservation_data["checkout_date"],
            adults=sample_reservation_data["adults"],
            children=sample_reservation_data["children"],
        )

        created_reservation = await pms_service.create_reservation(reservation)

        # Retrieve reservation
        retrieved_reservation = await pms_service.get_reservation(created_reservation.reservation_id)

        assert retrieved_reservation is not None
        assert retrieved_reservation.reservation_id == created_reservation.reservation_id
        assert retrieved_reservation.confirmation_number == created_reservation.confirmation_number
        assert retrieved_reservation.guest.email == sample_guest.email

    async def test_update_reservation(self, pms_service, sample_guest, sample_reservation_data):
        """Test updating reservation"""

        # Create reservation first
        reservation = Reservation(
            guest=sample_guest,
            room_type=sample_reservation_data["room_type"],
            checkin_date=sample_reservation_data["checkin_date"],
            checkout_date=sample_reservation_data["checkout_date"],
            adults=sample_reservation_data["adults"],
            children=sample_reservation_data["children"],
        )

        created_reservation = await pms_service.create_reservation(reservation)

        # Update reservation
        update_data = {"adults": 3, "special_requests": ["Ocean view", "Extra towels"]}

        updated_reservation = await pms_service.update_reservation(created_reservation.reservation_id, update_data)

        assert updated_reservation.adults == 3
        assert "Ocean view" in updated_reservation.special_requests
        assert updated_reservation.updated_at is not None

    async def test_cancel_reservation(self, pms_service, sample_guest, sample_reservation_data):
        """Test cancelling reservation"""

        # Create reservation first
        reservation = Reservation(
            guest=sample_guest,
            room_type=sample_reservation_data["room_type"],
            checkin_date=sample_reservation_data["checkin_date"],
            checkout_date=sample_reservation_data["checkout_date"],
            adults=sample_reservation_data["adults"],
            children=sample_reservation_data["children"],
        )

        created_reservation = await pms_service.create_reservation(reservation)

        # Cancel reservation
        success = await pms_service.cancel_reservation(created_reservation.reservation_id, "Test cancellation")

        assert success is True

        # Verify cancellation
        cancelled_reservation = await pms_service.get_reservation(created_reservation.reservation_id)
        assert cancelled_reservation.status == ReservationStatus.CANCELLED


class TestReservationWorkflow:
    """Test intelligent reservation workflow"""

    async def test_complete_reservation_workflow(self, reservation_manager):
        """Test complete reservation workflow from inquiry to completion"""

        session_id = "test_session_123"

        # Start workflow
        initial_context = ConversationContext(session_id=session_id, reservation_context={})

        workflow = await reservation_manager.start_reservation_workflow(session_id, initial_context)
        assert workflow.state == ReservationWorkflowState.INQUIRY

        # Step 1: Provide dates and guest count
        context_with_dates = ConversationContext(
            session_id=session_id,
            reservation_context={"checkin_date": (date.today() + timedelta(days=1)).isoformat(), "guest_count": 2},
        )

        next_state, result_data = await reservation_manager.process_workflow_step(
            workflow.workflow_id, context_with_dates
        )

        assert next_state == ReservationWorkflowState.AVAILABILITY_CHECK

        # Step 2: Process availability results
        next_state, result_data = await reservation_manager.process_workflow_step(
            workflow.workflow_id, context_with_dates
        )

        assert next_state == ReservationWorkflowState.SELECTION
        assert "available_options" in result_data
        assert len(result_data["available_options"]) > 0

        # Step 3: Select room type
        context_with_selection = ConversationContext(
            session_id=session_id,
            reservation_context={
                **context_with_dates.reservation_context,
                "selected_room_type": RoomType.DELUXE_DOUBLE.value,
            },
        )

        next_state, result_data = await reservation_manager.process_workflow_step(
            workflow.workflow_id, context_with_selection
        )

        assert next_state == ReservationWorkflowState.GUEST_DETAILS

        # Step 4: Provide guest details
        context_with_guest = ConversationContext(
            session_id=session_id,
            reservation_context={
                **context_with_selection.reservation_context,
                "guest_name": "John Doe",
                "guest_email": "john.doe@example.com",
                "guest_phone": "+1-555-0123",
            },
        )

        next_state, result_data = await reservation_manager.process_workflow_step(
            workflow.workflow_id, context_with_guest
        )

        assert next_state == ReservationWorkflowState.CONFIRMATION
        assert "reservation_summary" in result_data

        # Step 5: Confirm reservation
        context_confirmed = ConversationContext(
            session_id=session_id, reservation_context={**context_with_guest.reservation_context, "confirmed": True}
        )

        next_state, result_data = await reservation_manager.process_workflow_step(
            workflow.workflow_id, context_confirmed
        )

        assert next_state == ReservationWorkflowState.PROCESSING

        # Step 6: Complete processing
        next_state, result_data = await reservation_manager.process_workflow_step(
            workflow.workflow_id, context_confirmed
        )

        assert next_state == ReservationWorkflowState.COMPLETED
        assert "reservation" in result_data
        assert "confirmation_details" in result_data

        # Verify final reservation
        final_reservation = result_data["reservation"]
        assert final_reservation.reservation_id is not None
        assert final_reservation.confirmation_number is not None
        assert final_reservation.status == ReservationStatus.CONFIRMED

    async def test_workflow_business_rule_validation(self, reservation_manager):
        """Test business rule validation in workflow"""

        session_id = "test_business_rules"

        # Start workflow
        workflow = await reservation_manager.start_reservation_workflow(
            session_id, ConversationContext(session_id=session_id)
        )

        # Try to book for past date (should fail)
        context_past_date = ConversationContext(
            session_id=session_id,
            reservation_context={"checkin_date": (date.today() - timedelta(days=1)).isoformat(), "guest_count": 2},
        )

        next_state, result_data = await reservation_manager.process_workflow_step(
            workflow.workflow_id, context_past_date
        )

        assert next_state == ReservationWorkflowState.ERROR
        assert "violations" in result_data
        assert len(result_data["violations"]) > 0

    async def test_workflow_cancellation(self, reservation_manager):
        """Test workflow cancellation"""

        session_id = "test_cancellation"

        # Start workflow
        workflow = await reservation_manager.start_reservation_workflow(
            session_id, ConversationContext(session_id=session_id)
        )

        # Cancel workflow
        success = await reservation_manager.cancel_reservation(workflow.workflow_id, "user_cancelled")
        assert success is True

        # Check workflow status
        status = await reservation_manager.get_workflow_status(workflow.workflow_id)
        assert status["state"] == ReservationWorkflowState.CANCELLED.value


class TestConfirmationService:
    """Test booking confirmation functionality"""

    async def test_generate_confirmation_documents(self, confirmation_service, sample_guest, sample_reservation_data):
        """Test confirmation document generation"""

        reservation = Reservation(
            reservation_id="test_123",
            confirmation_number="CONF123456",
            guest=sample_guest,
            room_type=sample_reservation_data["room_type"],
            checkin_date=sample_reservation_data["checkin_date"],
            checkout_date=sample_reservation_data["checkout_date"],
            adults=sample_reservation_data["adults"],
            children=sample_reservation_data["children"],
            status=ReservationStatus.CONFIRMED,
            total_amount=299.99,
            currency="USD",
        )

        guest_preferences = GuestPreferences(preferred_language="en", preferred_channels=[ConfirmationChannel.EMAIL])

        documents = await confirmation_service._generate_confirmation_documents(reservation, guest_preferences)

        assert len(documents) >= 3  # At least confirmation letter, QR code, and instructions

        # Check document types
        doc_types = [doc.document_type for doc in documents]
        from app.services.pms.booking_confirmation_service import DocumentType

        assert DocumentType.CONFIRMATION_LETTER in doc_types
        assert DocumentType.QR_CODE in doc_types
        assert DocumentType.CHECK_IN_INSTRUCTIONS in doc_types

        # Verify document content
        confirmation_letter = next(doc for doc in documents if doc.document_type == DocumentType.CONFIRMATION_LETTER)
        assert "CONF123456" in confirmation_letter.content
        assert "John Doe" in confirmation_letter.content
        assert confirmation_letter.content_type == "text/html"

    async def test_send_confirmation_email_channel(self, confirmation_service, sample_guest, sample_reservation_data):
        """Test sending confirmation via email channel"""

        reservation = Reservation(
            reservation_id="test_email_123",
            confirmation_number="EMAIL123456",
            guest=sample_guest,
            room_type=sample_reservation_data["room_type"],
            checkin_date=sample_reservation_data["checkin_date"],
            checkout_date=sample_reservation_data["checkout_date"],
            adults=sample_reservation_data["adults"],
            children=sample_reservation_data["children"],
            status=ReservationStatus.CONFIRMED,
            total_amount=399.99,
            currency="USD",
        )

        # Mock the send confirmation (since we don't have real email service in test)
        result = await confirmation_service.send_confirmation(
            reservation, [ConfirmationChannel.EMAIL], GuestPreferences(preferred_language="en")
        )

        assert result["reservation_id"] == "test_email_123"
        assert result["total_deliveries"] == 1
        assert result["documents_generated"] > 0


class TestEndToEndIntegration:
    """Complete end-to-end integration tests"""

    async def test_full_hotel_agent_workflow(self, pms_service, reservation_manager, confirmation_service):
        """Test complete workflow from inquiry to confirmation"""

        # 1. Guest inquires about availability
        session_id = "e2e_test_session"

        workflow = await reservation_manager.start_reservation_workflow(
            session_id, ConversationContext(session_id=session_id)
        )

        # 2. Guest provides dates and requirements
        inquiry_context = ConversationContext(
            session_id=session_id,
            reservation_context={
                "checkin_date": (date.today() + timedelta(days=3)).isoformat(),
                "checkout_date": (date.today() + timedelta(days=5)).isoformat(),
                "guest_count": 2,
                "preferences": ["ocean view", "high floor"],
            },
        )

        # Process availability check
        state, data = await reservation_manager.process_workflow_step(workflow.workflow_id, inquiry_context)

        assert state == ReservationWorkflowState.SELECTION
        available_options = data["available_options"]
        assert len(available_options) > 0

        # 3. Guest selects room type
        selection_context = ConversationContext(
            session_id=session_id,
            reservation_context={
                **inquiry_context.reservation_context,
                "selected_room_type": available_options[0].room_type.value,
            },
        )

        state, data = await reservation_manager.process_workflow_step(workflow.workflow_id, selection_context)

        assert state == ReservationWorkflowState.GUEST_DETAILS

        # 4. Guest provides personal information
        guest_context = ConversationContext(
            session_id=session_id,
            reservation_context={
                **selection_context.reservation_context,
                "guest_name": "Alice Johnson",
                "guest_email": "alice.johnson@example.com",
                "guest_phone": "+1-555-9876",
            },
        )

        state, data = await reservation_manager.process_workflow_step(workflow.workflow_id, guest_context)

        assert state == ReservationWorkflowState.CONFIRMATION
        summary = data["reservation_summary"]
        assert summary["guest_name"] == "Alice Johnson"
        assert summary["total_amount"] > 0

        # 5. Guest confirms reservation
        confirmation_context = ConversationContext(
            session_id=session_id, reservation_context={**guest_context.reservation_context, "confirmed": True}
        )

        # Process confirmation and completion
        state, data = await reservation_manager.process_workflow_step(workflow.workflow_id, confirmation_context)

        # May need multiple steps to complete
        while state == ReservationWorkflowState.PROCESSING:
            state, data = await reservation_manager.process_workflow_step(workflow.workflow_id, confirmation_context)

        assert state == ReservationWorkflowState.COMPLETED

        final_reservation = data["reservation"]
        assert final_reservation.reservation_id is not None
        assert final_reservation.confirmation_number is not None
        assert final_reservation.guest.email == "alice.johnson@example.com"

        # 6. Send confirmation
        confirmation_result = await confirmation_service.send_confirmation(
            final_reservation, [ConfirmationChannel.EMAIL], GuestPreferences(preferred_language="en")
        )

        assert confirmation_result["successful_deliveries"] >= 0
        assert confirmation_result["documents_generated"] > 0

        # 7. Verify reservation in PMS
        verified_reservation = await pms_service.get_reservation(final_reservation.reservation_id)
        assert verified_reservation is not None
        assert verified_reservation.status == ReservationStatus.CONFIRMED

    async def test_error_handling_and_recovery(self, pms_service, reservation_manager):
        """Test error handling and recovery scenarios"""

        session_id = "error_test_session"

        # Start workflow
        workflow = await reservation_manager.start_reservation_workflow(
            session_id, ConversationContext(session_id=session_id)
        )

        # Test invalid date range
        invalid_context = ConversationContext(
            session_id=session_id,
            reservation_context={
                "checkin_date": (date.today() + timedelta(days=5)).isoformat(),
                "checkout_date": (date.today() + timedelta(days=1)).isoformat(),  # Before checkin
                "guest_count": 2,
            },
        )

        state, data = await reservation_manager.process_workflow_step(workflow.workflow_id, invalid_context)

        # Should handle validation error gracefully
        assert state in [ReservationWorkflowState.ERROR, ReservationWorkflowState.INFORMATION_GATHERING]

        # Test recovery with valid dates
        valid_context = ConversationContext(
            session_id=session_id,
            reservation_context={
                "checkin_date": (date.today() + timedelta(days=1)).isoformat(),
                "checkout_date": (date.today() + timedelta(days=3)).isoformat(),
                "guest_count": 2,
            },
        )

        # Reset workflow or create new one if needed
        if state == ReservationWorkflowState.ERROR:
            workflow = await reservation_manager.start_reservation_workflow(
                session_id + "_recovery", ConversationContext(session_id=session_id + "_recovery")
            )

        state, data = await reservation_manager.process_workflow_step(workflow.workflow_id, valid_context)

        # Should proceed to availability check
        assert state == ReservationWorkflowState.AVAILABILITY_CHECK

    @pytest.mark.performance
    async def test_performance_metrics(self, pms_service):
        """Test performance of PMS operations"""

        import time

        # Test availability check performance
        start_time = time.time()

        tomorrow = date.today() + timedelta(days=1)
        day_after = tomorrow + timedelta(days=2)

        availability = await pms_service.check_availability(
            checkin_date=tomorrow, checkout_date=day_after, adults=2, children=0
        )

        availability_time = time.time() - start_time

        # Should complete within reasonable time
        assert availability_time < 5.0  # 5 seconds max
        assert len(availability) > 0

        # Test reservation creation performance
        guest = Guest(first_name="Performance", last_name="Test", email="perf.test@example.com", phone="+1-555-0000")

        reservation = Reservation(
            guest=guest,
            room_type=RoomType.STANDARD_DOUBLE,
            checkin_date=tomorrow,
            checkout_date=day_after,
            adults=2,
            children=0,
        )

        start_time = time.time()
        created_reservation = await pms_service.create_reservation(reservation)
        creation_time = time.time() - start_time

        assert creation_time < 3.0  # 3 seconds max
        assert created_reservation.reservation_id is not None

        # Test concurrent operations
        tasks = []
        for i in range(5):
            task = asyncio.create_task(
                pms_service.check_availability(checkin_date=tomorrow, checkout_date=day_after, adults=2, children=0)
            )
            tasks.append(task)

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        concurrent_time = time.time() - start_time

        assert concurrent_time < 10.0  # Should handle concurrent requests efficiently
        assert all(len(result) > 0 for result in results)


if __name__ == "__main__":
    # Run specific test categories
    pytest.main(
        [__file__, "-v", "--tb=short", "-k", "test_complete_reservation_workflow or test_full_hotel_agent_workflow"]
    )
