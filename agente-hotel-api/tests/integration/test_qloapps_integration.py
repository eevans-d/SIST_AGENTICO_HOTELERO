"""
Integration tests for QloApps PMS integration.

These tests validate the real integration with QloApps or use mocks if PMS_TYPE=mock.
"""

import pytest
import pytest_asyncio
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.settings import settings
from app.services.qloapps_client import create_qloapps_client
from app.services.pms_adapter import get_pms_adapter
from app.exceptions.pms_exceptions import PMSError, PMSAuthError


@pytest_asyncio.fixture
async def mock_redis():
    """Create a mock Redis client for testing."""
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    redis_mock.delete = AsyncMock()
    redis_mock.keys = AsyncMock(return_value=[])
    return redis_mock


@pytest_asyncio.fixture
async def pms_adapter(mock_redis):
    """Create PMS adapter with mocked Redis."""
    return get_pms_adapter(mock_redis)


class TestQloAppsClient:
    """Test QloAppsClient directly."""
    
    @pytest.mark.asyncio
    async def test_client_creation(self):
        """Test client can be created with current settings."""
        client = create_qloapps_client()
        assert client is not None
        assert client.base_url == settings.pms_base_url
        await client.close()
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        settings.pms_type != "qloapps",
        reason="Requires real QloApps connection (PMS_TYPE=qloapps)"
    )
    async def test_connection_real(self):
        """Test connection to real QloApps instance."""
        client = create_qloapps_client()
        
        try:
            is_connected = await client.test_connection()
            assert is_connected, "Should connect to QloApps"
        finally:
            await client.close()
    
    @pytest.mark.asyncio
    async def test_connection_mock(self):
        """Test connection with mocked httpx client."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = AsyncMock(
                status_code=200,
                json=lambda: {"prestashop": {"api": "1.0"}}
            )
            
            client = create_qloapps_client()
            
            try:
                is_connected = await client.test_connection()
                assert is_connected
            finally:
                await client.close()
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        settings.pms_type != "qloapps",
        reason="Requires real QloApps connection"
    )
    async def test_get_hotels_real(self):
        """Test fetching hotels from real QloApps."""
        client = create_qloapps_client()
        
        try:
            hotels = await client.get_hotels()
            assert isinstance(hotels, list)
            assert len(hotels) > 0, "Should have at least one hotel"
            
            hotel = hotels[0]
            assert "id" in hotel
            assert "name" in hotel
        finally:
            await client.close()
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        settings.pms_type != "qloapps",
        reason="Requires real QloApps connection"
    )
    async def test_get_room_types_real(self):
        """Test fetching room types from real QloApps."""
        client = create_qloapps_client()
        
        try:
            room_types = await client.get_room_types()
            assert isinstance(room_types, list)
            assert len(room_types) > 0, "Should have at least one room type"
            
            room_type = room_types[0]
            assert "id" in room_type
            assert "name" in room_type
        finally:
            await client.close()
    
    @pytest.mark.asyncio
    async def test_check_availability_mock(self):
        """Test availability check with mocked response."""
        mock_response = {
            "rooms": [
                {
                    "id": 1,
                    "name": "Standard Room",
                    "available": 5,
                    "price": 100.00
                }
            ]
        }
        
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = AsyncMock(
                status_code=200,
                json=lambda: mock_response
            )
            
            client = create_qloapps_client()
            
            try:
                check_in = date.today() + timedelta(days=1)
                check_out = check_in + timedelta(days=1)
                
                rooms = await client.check_availability(
                    hotel_id=1,
                    date_from=check_in,
                    date_to=check_out,
                    num_rooms=1,
                    num_adults=2
                )
                
                assert isinstance(rooms, list)
            finally:
                await client.close()
    
    @pytest.mark.asyncio
    async def test_authentication_error(self):
        """Test handling of authentication errors."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = AsyncMock(
                status_code=401,
                text="Unauthorized"
            )
            
            client = create_qloapps_client()
            
            try:
                with pytest.raises(PMSAuthError):
                    await client.test_connection()
            finally:
                await client.close()


class TestQloAppsAdapter:
    """Test QloAppsAdapter with various scenarios."""
    
    @pytest.mark.asyncio
    async def test_adapter_creation(self, pms_adapter):
        """Test adapter can be created."""
        assert pms_adapter is not None
    
    @pytest.mark.asyncio
    async def test_check_availability_cached(self, pms_adapter):
        """Test that availability checks use caching."""
        
        check_in = date.today() + timedelta(days=1)
        check_out = check_in + timedelta(days=1)
        
        # Mock the client method
        with patch.object(pms_adapter.client, "check_availability") as mock_check:
            mock_check.return_value = [
                {
                    "room_type_id": 1,
                    "room_type_name": "Standard",
                    "available_rooms": 5,
                    "price_per_night": 100.00,
                    "currency": "USD"
                }
            ]
            
            # First call - should hit the API
            result1 = await pms_adapter.check_availability(
                check_in=check_in.isoformat(),
                check_out=check_out.isoformat(),
                guests=2
            )
            
            assert mock_check.call_count == 1
            assert result1["available"]
            
            # Second call - should use cache
            result2 = await pms_adapter.check_availability(
                check_in=check_in.isoformat(),
                check_out=check_out.isoformat(),
                guests=2
            )
            
            # Should still be 1 (cached)
            assert mock_check.call_count == 1
            assert result2["available"]
    
    @pytest.mark.asyncio
    async def test_create_reservation_flow(self, pms_adapter):
        """Test complete reservation creation flow."""
        
        guest_info = {
            "name": "Test Guest",
            "email": "test@example.com",
            "phone": "+1234567890"
        }
        
        check_in = date.today() + timedelta(days=7)
        check_out = check_in + timedelta(days=2)
        
        # Mock client methods
        with patch.object(pms_adapter.client, "search_customer_by_email") as mock_search:
            with patch.object(pms_adapter.client, "create_customer") as mock_create_customer:
                with patch.object(pms_adapter.client, "create_booking") as mock_create_booking:
                    
                    # No existing customer
                    mock_search.return_value = None
                    
                    # Customer creation
                    mock_create_customer.return_value = {"id": 123}
                    
                    # Booking creation
                    mock_create_booking.return_value = {
                        "id": 456,
                        "reference": "BOOK456",
                        "status": "confirmed"
                    }
                    
                    result = await pms_adapter.create_reservation(
                        guest_info=guest_info,
                        check_in=check_in.isoformat(),
                        check_out=check_out.isoformat(),
                        room_type="doble",
                        num_guests=2
                    )
                    
                    assert result["success"]
                    assert result["reservation_id"] == 456
                    assert result["reference"] == "BOOK456"
                    assert mock_search.called
                    assert mock_create_customer.called
                    assert mock_create_booking.called
    
    @pytest.mark.asyncio
    async def test_get_room_types_cached(self, pms_adapter):
        """Test room types caching (1 hour TTL)."""
        
        with patch.object(pms_adapter.client, "get_room_types") as mock_get:
            mock_get.return_value = [
                {"id": 1, "name": "Standard", "max_guests": 2},
                {"id": 2, "name": "Deluxe", "max_guests": 3}
            ]
            
            # First call
            result1 = await pms_adapter.get_room_types()
            assert len(result1) == 2
            assert mock_get.call_count == 1
            
            # Second call - should use cache (1 hour TTL)
            result2 = await pms_adapter.get_room_types()
            assert len(result2) == 2
            assert mock_get.call_count == 1  # Still 1 (cached)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self, pms_adapter):
        """Test circuit breaker opens after multiple failures."""
        
        # Force circuit breaker to open by simulating failures
        with patch.object(pms_adapter.client, "check_availability") as mock_check:
            mock_check.side_effect = PMSError("Connection failed")
            
            # Try multiple times to trip the circuit breaker
            for _ in range(6):  # Threshold is 5
                try:
                    await pms_adapter.check_availability(
                        check_in="2025-01-10",
                        check_out="2025-01-12",
                        guests=2
                    )
                except PMSError:
                    pass
            
            # Circuit breaker should now be open
            # Next call should fail immediately without calling the client
            from app.core.circuit_breaker import CircuitState
            assert pms_adapter.circuit_breaker.state == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_booking(self, pms_adapter):
        """Test that cache is invalidated after creating a booking."""
        
        guest_info = {
            "name": "Test Guest",
            "email": "test@example.com",
            "phone": "+1234567890"
        }
        
        check_in = date.today() + timedelta(days=7)
        check_out = check_in + timedelta(days=2)
        
        with patch.object(pms_adapter.client, "search_customer_by_email") as mock_search:
            with patch.object(pms_adapter.client, "create_customer") as mock_create_customer:
                with patch.object(pms_adapter.client, "create_booking") as mock_create_booking:
                    with patch.object(pms_adapter, "_invalidate_cache_pattern") as mock_invalidate:
                        
                        mock_search.return_value = None
                        mock_create_customer.return_value = {"id": 123}
                        mock_create_booking.return_value = {
                            "id": 456,
                            "reference": "BOOK456",
                            "status": "confirmed"
                        }
                        
                        await pms_adapter.create_reservation(
                            guest_info=guest_info,
                            check_in=check_in.isoformat(),
                            check_out=check_out.isoformat(),
                            room_type="doble",
                            num_guests=2
                        )
                        
                        # Verify cache was invalidated
                        assert mock_invalidate.called
                        # Should invalidate availability cache
                        call_args = mock_invalidate.call_args[0][0]
                        assert "availability" in call_args


class TestPMSIntegrationEndToEnd:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        settings.pms_type != "qloapps",
        reason="Requires real QloApps connection"
    )
    async def test_full_booking_flow_real(self, mock_redis):
        """
        Test complete booking flow with real QloApps.
        
        WARNING: This creates a real booking. Only run in test environment.
        """
        adapter = get_pms_adapter(mock_redis)
        
        # Step 1: Check availability
        check_in = date.today() + timedelta(days=30)  # Far in future
        check_out = check_in + timedelta(days=2)
        
        availability = await adapter.check_availability(
            check_in=check_in.isoformat(),
            check_out=check_out.isoformat(),
            guests=2
        )
        
        assert availability["available"], "Should have rooms available"
        assert len(availability["rooms"]) > 0
        
        # Step 2: Get room types
        room_types = await adapter.get_room_types()
        assert len(room_types) > 0
        
        # Step 3: Create test booking
        guest_info = {
            "name": "Integration Test Guest",
            "email": f"test_{check_in.isoformat()}@example.com",  # Unique email
            "phone": "+1234567890"
        }
        
        result = await adapter.create_reservation(
            guest_info=guest_info,
            check_in=check_in.isoformat(),
            check_out=check_out.isoformat(),
            room_type="doble",
            num_guests=2
        )
        
        assert result["success"]
        assert "reservation_id" in result
        
        booking_id = result["reservation_id"]
        
        # Step 4: Retrieve the booking
        booking = await adapter.get_reservation(booking_id)
        assert booking is not None
        assert booking["id"] == booking_id
        
        # Step 5: Cancel the test booking (cleanup)
        cancel_result = await adapter.cancel_reservation(booking_id)
        assert cancel_result["success"]


@pytest.mark.asyncio
async def test_pms_adapter_singleton(mock_redis):
    """Test that get_pms_adapter returns the same instance."""
    adapter1 = get_pms_adapter(mock_redis)
    adapter2 = get_pms_adapter(mock_redis)
    
    assert adapter1 is adapter2, "Should return the same singleton instance"
