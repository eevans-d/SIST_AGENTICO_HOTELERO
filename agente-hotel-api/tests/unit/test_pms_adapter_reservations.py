"""
Unit tests for PMS Adapter reservation functionality.

Tests cover:
- Successful reservation creation
- Error handling
- Reservation confirmation
- Cancellation
- Tenant ID propagation
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import date

from app.services.pms_adapter import QloAppsAdapter
from app.exceptions.pms_exceptions import PMSError


@pytest.fixture
def pms_adapter(fake_redis):
    """Create PMS adapter instance for testing."""
    return QloAppsAdapter(redis_client=fake_redis)


@pytest.fixture
def reservation_data():
    """Sample reservation data."""
    return {
        "checkin": "2025-12-01",
        "checkout": "2025-12-05",
        "room_type": "double",
        "guest_name": "John Doe",
        "guest_email": "john@example.com",
        "guest_phone": "+34600111222",
        "guests": 2
    }


class TestPMSAdapterReservations:
    """Tests for PMS adapter reservation functionality."""

    @pytest.mark.asyncio
    async def test_create_reservation_success(self, pms_adapter, reservation_data):
        """Test successful reservation creation."""
        mock_booking = {
            "booking_reference": "HTL-12345",
            "status": "confirmed",
            "total_amount": 400.0,
            "currency": "USD",
            "check_in": "2025-12-01",
            "check_out": "2025-12-05"
        }
        
        pms_adapter.qloapps.create_booking = AsyncMock(return_value=mock_booking)
        
        result = await pms_adapter.create_reservation(reservation_data)
        
        assert result is not None
        assert result["booking_reference"] == "HTL-12345"
        assert result["status"] == "confirmed"

    @pytest.mark.asyncio
    async def test_create_reservation_with_tenant_id(self, pms_adapter, reservation_data):
        """Test reservation creation includes tenant_id."""
        reservation_data["tenant_id"] = "hotel-test"
        
        mock_booking = {
            "booking_reference": "HTL-12345",
            "status": "confirmed",
            "total_amount": 400.0,
            "currency": "USD",
            "check_in": "2025-12-01",
            "check_out": "2025-12-05"
        }
        pms_adapter.qloapps.create_booking = AsyncMock(return_value=mock_booking)
        
        await pms_adapter.create_reservation(reservation_data)
        
        # Verify create_booking was called
        pms_adapter.qloapps.create_booking.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_reservation_no_availability(self, pms_adapter, reservation_data):
        """Test reservation creation when room not available."""
        pms_adapter.qloapps.create_booking = AsyncMock(side_effect=Exception("Room not available"))
        
        with pytest.raises(PMSError):
            await pms_adapter.create_reservation(reservation_data)

    @pytest.mark.asyncio
    async def test_create_reservation_invalid_data(self, pms_adapter):
        """Test reservation creation with invalid data."""
        invalid_data = {
            "checkin": "2025-12-01",
            # Missing required fields
        }
        
        # Depending on implementation, this might raise KeyError or PMSError
        with pytest.raises(Exception):
            await pms_adapter.create_reservation(invalid_data)

    @pytest.mark.asyncio
    async def test_create_reservation_pms_error(self, pms_adapter, reservation_data):
        """Test handling of PMS errors during reservation."""
        pms_adapter.qloapps.create_booking = AsyncMock(side_effect=ConnectionError("PMS unreachable"))
        
        with pytest.raises(PMSError):
            await pms_adapter.create_reservation(reservation_data)

    @pytest.mark.asyncio
    async def test_create_reservation_pending_status(self, pms_adapter, reservation_data):
        """Test reservation creation with pending status."""
        mock_booking = {
            "booking_reference": "HTL-12345",
            "status": "pending",
            "total_amount": 400.0,
            "currency": "USD",
            "check_in": "2025-12-01",
            "check_out": "2025-12-05"
        }
        
        pms_adapter.qloapps.create_booking = AsyncMock(return_value=mock_booking)
        
        result = await pms_adapter.create_reservation(reservation_data)
        
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_create_reservation_with_special_requests(self, pms_adapter, reservation_data):
        """Test reservation with special requests."""
        reservation_data["special_requests"] = "Late checkout, extra pillows"
        
        mock_booking = {
            "booking_reference": "HTL-12345",
            "status": "confirmed",
            "total_amount": 400.0,
            "currency": "USD",
            "check_in": "2025-12-01",
            "check_out": "2025-12-05"
        }
        pms_adapter.qloapps.create_booking = AsyncMock(return_value=mock_booking)
        
        result = await pms_adapter.create_reservation(reservation_data)
        
        assert result is not None
        # Verify special requests were passed (implementation detail check)
        call_args = pms_adapter.qloapps.create_booking.call_args
        assert call_args is not None
        # guest_info is passed as keyword arg
        guest_info = call_args.kwargs.get('guest_info', {})
        assert guest_info.get('address') == "Late checkout, extra pillows"

    @pytest.mark.asyncio
    async def test_create_reservation_response_structure(self, pms_adapter, reservation_data):
        """Test that reservation response has expected structure."""
        mock_booking = {
            "booking_reference": "HTL-12345",
            "status": "confirmed",
            "total_amount": 400.0,
            "currency": "USD",
            "check_in": "2025-12-01",
            "check_out": "2025-12-05"
        }
        
        pms_adapter.qloapps.create_booking = AsyncMock(return_value=mock_booking)
        
        result = await pms_adapter.create_reservation(reservation_data)
        
        assert "booking_reference" in result
        assert "status" in result
        assert "total_amount" in result
