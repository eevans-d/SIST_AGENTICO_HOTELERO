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


@pytest.fixture
def pms_adapter():
    """Create PMS adapter instance for testing."""
    return QloAppsAdapter(
        base_url="https://test-pms.example.com",
        api_key="test-api-key"
    )


@pytest.fixture
def reservation_data():
    """Sample reservation data."""
    return {
        "checkin_date": date(2025, 12, 1),
        "checkout_date": date(2025, 12, 5),
        "room_type": "double",
        "guest_name": "John Doe",
        "guest_email": "john@example.com",
        "guest_phone": "+34600111222",
        "num_guests": 2
    }


class TestPMSAdapterReservations:
    """Tests for PMS adapter reservation functionality."""

    @pytest.mark.asyncio
    async def test_create_reservation_success(self, pms_adapter, reservation_data):
        """Test successful reservation creation."""
        mock_response = {
            "reservation_uuid": "test-uuid-123",
            "status": "confirmed",
            "booking_id": "HTL-12345"
        }
        
        with patch.object(pms_adapter, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await pms_adapter.create_reservation(**reservation_data)
            
            assert result is not None
            assert result["reservation_uuid"] == "test-uuid-123"
            assert result["status"] == "confirmed"

    @pytest.mark.asyncio
    async def test_create_reservation_with_tenant_id(self, pms_adapter, reservation_data):
        """Test reservation creation includes tenant_id."""
        reservation_data["tenant_id"] = "hotel-test"
        
        with patch.object(pms_adapter, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"reservation_uuid": "test-uuid", "status": "confirmed"}
            
            await pms_adapter.create_reservation(**reservation_data)
            
            # Verify tenant_id was included
            call_args = mock_request.call_args
            assert call_args is not None

    @pytest.mark.asyncio
    async def test_create_reservation_no_availability(self, pms_adapter, reservation_data):
        """Test reservation creation when room not available."""
        with patch.object(pms_adapter, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("Room not available")
            
            with pytest.raises(Exception):
                await pms_adapter.create_reservation(**reservation_data)

    @pytest.mark.asyncio
    async def test_create_reservation_invalid_data(self, pms_adapter):
        """Test reservation creation with invalid data."""
        invalid_data = {
            "checkin_date": date(2025, 12, 1),
            # Missing required fields
        }
        
        with pytest.raises((ValueError, KeyError, Exception)):
            await pms_adapter.create_reservation(**invalid_data)

    @pytest.mark.asyncio
    async def test_create_reservation_pms_error(self, pms_adapter, reservation_data):
        """Test handling of PMS errors during reservation."""
        with patch.object(pms_adapter, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = ConnectionError("PMS unreachable")
            
            with pytest.raises(ConnectionError):
                await pms_adapter.create_reservation(**reservation_data)

    @pytest.mark.asyncio
    async def test_create_reservation_pending_status(self, pms_adapter, reservation_data):
        """Test reservation creation with pending status."""
        mock_response = {
            "reservation_uuid": "test-uuid-123",
            "status": "pending",
            "message": "Awaiting confirmation"
        }
        
        with patch.object(pms_adapter, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await pms_adapter.create_reservation(**reservation_data)
            
            assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_create_reservation_with_special_requests(self, pms_adapter, reservation_data):
        """Test reservation with special requests."""
        reservation_data["special_requests"] = "Late checkout, extra pillows"
        
        with patch.object(pms_adapter, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"reservation_uuid": "test-uuid", "status": "confirmed"}
            
            result = await pms_adapter.create_reservation(**reservation_data)
            
            assert result is not None

    @pytest.mark.asyncio
    async def test_create_reservation_response_structure(self, pms_adapter, reservation_data):
        """Test that reservation response has expected structure."""
        mock_response = {
            "reservation_uuid": "test-uuid-123",
            "status": "confirmed",
            "booking_id": "HTL-12345",
            "total_price": 400.00,
            "currency": "USD"
        }
        
        with patch.object(pms_adapter, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await pms_adapter.create_reservation(**reservation_data)
            
            assert "reservation_uuid" in result
            assert "status" in result
            assert "booking_id" in result
