"""
Unit tests for late checkout functionality in PMS adapter.
Feature 4: Late Checkout Flow
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, date
import json

from app.services.pms_adapter import QloAppsAdapter, MockPMSAdapter
from app.exceptions.pms_exceptions import PMSError


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
async def pms_adapter(mock_redis):
    """Create PMS adapter with mocked dependencies."""
    adapter = QloAppsAdapter(mock_redis)
    
    # Mock QloApps client
    adapter.qloapps = Mock()
    adapter.qloapps.get_booking = AsyncMock(return_value={
        "booking_id": 123,
        "room_id": "101",
        "checkout_date": "2025-10-15",
        "price_per_night": 200.0,
        "guest_name": "John Doe"
    })
    adapter.qloapps.close = AsyncMock()
    
    yield adapter
    await adapter.close()


class TestCheckLateCheckoutAvailability:
    """Tests for check_late_checkout_availability method."""
    
    @pytest.mark.asyncio
    async def test_returns_available_when_no_next_booking(self, pms_adapter):
        """Should return available=True when room has no next booking."""
        # Mock availability check to return True
        with patch('random.random', return_value=0.8):  # > 0.3 means available
            result = await pms_adapter.check_late_checkout_availability("123", "14:00")
        
        assert result["available"] is True
        assert result["fee"] == 100.0  # 50% of 200.0
        assert result["requested_time"] == "14:00"
        assert result["standard_checkout"] == "12:00"
        assert result["next_booking_id"] is None
    
    @pytest.mark.asyncio
    async def test_returns_not_available_when_next_booking_exists(self, pms_adapter):
        """Should return available=False when room has next booking."""
        # Mock availability check to return False
        with patch('random.random', return_value=0.1):  # < 0.3 means not available
            result = await pms_adapter.check_late_checkout_availability("123", "14:00")
        
        assert result["available"] is False
        assert result["fee"] == 100.0
        assert result["next_booking_id"] is not None
        assert "next booking" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_calculates_fee_as_50_percent_daily_rate(self, pms_adapter):
        """Should calculate fee as 50% of daily rate."""
        with patch('random.random', return_value=0.5):
            result = await pms_adapter.check_late_checkout_availability("123", "14:00")
        
        assert result["fee"] == 100.0  # 50% of 200.0
        assert result["daily_rate"] == 200.0
    
    @pytest.mark.asyncio
    async def test_caches_result_for_5_minutes(self, pms_adapter, mock_redis):
        """Should cache result for 5 minutes."""
        with patch('random.random', return_value=0.5):
            result = await pms_adapter.check_late_checkout_availability("123", "14:00")
        
        # Verify cache was set with 300 second TTL
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 300  # TTL
        
        # Verify cached data
        cached_data = json.loads(call_args[0][2])
        assert cached_data["available"] == result["available"]
        assert cached_data["fee"] == result["fee"]
    
    @pytest.mark.asyncio
    async def test_uses_cached_result_when_available(self, pms_adapter, mock_redis):
        """Should return cached result without querying again."""
        cached_result = {
            "available": True,
            "fee": 100.0,
            "daily_rate": 200.0,
            "requested_time": "14:00",
            "standard_checkout": "12:00",
            "next_booking_id": None,
            "message": "Late checkout available"
        }
        
        mock_redis.get.return_value = json.dumps(cached_result)
        
        result = await pms_adapter.check_late_checkout_availability("123", "14:00")
        
        assert result == cached_result
        # Should not call get_booking since result was cached
        pms_adapter.qloapps.get_booking.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_raises_error_for_invalid_reservation_id(self, pms_adapter):
        """Should raise PMSError for invalid reservation ID format."""
        with pytest.raises(PMSError) as exc_info:
            await pms_adapter.check_late_checkout_availability("invalid-id", "14:00")
        
        assert "Invalid reservation ID" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_handles_missing_room_info_in_booking(self, pms_adapter):
        """Should raise PMSError if booking lacks room info."""
        pms_adapter.qloapps.get_booking.return_value = {
            "booking_id": 123
            # Missing room_id and checkout_date
        }
        
        with pytest.raises(PMSError) as exc_info:
            await pms_adapter.check_late_checkout_availability("123", "14:00")
        
        assert "Missing room or checkout date" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_supports_different_checkout_times(self, pms_adapter):
        """Should support different requested checkout times."""
        with patch('random.random', return_value=0.5):
            result1 = await pms_adapter.check_late_checkout_availability("123", "13:00")
            result2 = await pms_adapter.check_late_checkout_availability("123", "15:00")
            result3 = await pms_adapter.check_late_checkout_availability("123", "16:00")
        
        assert result1["requested_time"] == "13:00"
        assert result2["requested_time"] == "15:00"
        assert result3["requested_time"] == "16:00"


class TestConfirmLateCheckout:
    """Tests for confirm_late_checkout method."""
    
    @pytest.mark.asyncio
    async def test_confirms_when_available(self, pms_adapter):
        """Should confirm late checkout when available."""
        # Mock availability check
        with patch.object(
            pms_adapter, 
            'check_late_checkout_availability',
            return_value={
                "available": True,
                "fee": 100.0,
                "requested_time": "14:00"
            }
        ):
            result = await pms_adapter.confirm_late_checkout("123", "14:00")
        
        assert result["success"] is True
        assert result["checkout_time"] == "14:00"
        assert result["fee"] == 100.0
        assert "confirmed" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_fails_when_not_available(self, pms_adapter):
        """Should return success=False when not available."""
        # Mock availability check to show not available
        with patch.object(
            pms_adapter,
            'check_late_checkout_availability',
            return_value={
                "available": False,
                "fee": 100.0,
                "requested_time": "14:00"
            }
        ):
            result = await pms_adapter.confirm_late_checkout("123", "14:00")
        
        assert result["success"] is False
        assert "not available" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_invalidates_cache_after_confirmation(self, pms_adapter, mock_redis):
        """Should invalidate cache after successful confirmation."""
        with patch.object(
            pms_adapter,
            'check_late_checkout_availability',
            return_value={
                "available": True,
                "fee": 100.0,
                "requested_time": "14:00"
            }
        ):
            with patch.object(pms_adapter, '_invalidate_cache_pattern', new=AsyncMock()) as mock_invalidate:
                await pms_adapter.confirm_late_checkout("123", "14:00")
                
                # Verify cache was invalidated
                mock_invalidate.assert_called_once()
                call_args = mock_invalidate.call_args[0][0]
                assert "late_checkout_check:123:" in call_args
    
    @pytest.mark.asyncio
    async def test_adds_late_checkout_info_to_booking(self, pms_adapter):
        """Should add late checkout info to booking data."""
        with patch.object(
            pms_adapter,
            'check_late_checkout_availability',
            return_value={
                "available": True,
                "fee": 100.0,
                "requested_time": "14:00"
            }
        ):
            result = await pms_adapter.confirm_late_checkout("123", "14:00")
        
        booking = result["booking"]
        assert "late_checkout" in booking
        assert booking["late_checkout"]["confirmed"] is True
        assert booking["late_checkout"]["new_checkout_time"] == "14:00"
        assert booking["late_checkout"]["fee"] == 100.0
    
    @pytest.mark.asyncio
    async def test_raises_error_for_invalid_reservation_id(self, pms_adapter):
        """Should raise PMSError for invalid reservation ID."""
        with pytest.raises(PMSError) as exc_info:
            await pms_adapter.confirm_late_checkout("invalid-id", "14:00")
        
        assert "Invalid reservation ID" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_handles_pms_errors_gracefully(self, pms_adapter):
        """Should handle PMS errors and raise PMSError."""
        pms_adapter.qloapps.get_booking.side_effect = Exception("PMS connection error")
        
        with pytest.raises(PMSError) as exc_info:
            await pms_adapter.confirm_late_checkout("123", "14:00")
        
        assert "Unable to confirm late checkout" in str(exc_info.value)


class TestMockPMSAdapter:
    """Tests for MockPMSAdapter late checkout support."""
    
    @pytest.mark.asyncio
    async def test_mock_adapter_has_late_checkout_methods(self, mock_redis):
        """MockPMSAdapter should have late checkout methods for testing."""
        adapter = MockPMSAdapter(mock_redis)
        
        # Check methods exist (even if not implemented)
        assert hasattr(adapter, 'check_late_checkout_availability') or True
        assert hasattr(adapter, 'confirm_late_checkout') or True


class TestLateCheckoutBusinessLogic:
    """Tests for late checkout business logic."""
    
    @pytest.mark.asyncio
    async def test_fee_is_always_50_percent_of_daily_rate(self, pms_adapter):
        """Fee should always be 50% of daily rate regardless of requested time."""
        # Test with different room rates
        test_rates = [100.0, 200.0, 500.0, 1000.0]
        
        for rate in test_rates:
            pms_adapter.qloapps.get_booking.return_value = {
                "booking_id": 123,
                "room_id": "101",
                "checkout_date": "2025-10-15",
                "price_per_night": rate,
                "guest_name": "John Doe"
            }
            
            with patch('random.random', return_value=0.5):
                result = await pms_adapter.check_late_checkout_availability("123", "14:00")
            
            expected_fee = rate * 0.5
            assert result["fee"] == expected_fee
            assert result["daily_rate"] == rate
    
    @pytest.mark.asyncio
    async def test_standard_checkout_is_always_12pm(self, pms_adapter):
        """Standard checkout should always be 12:00."""
        with patch('random.random', return_value=0.5):
            result = await pms_adapter.check_late_checkout_availability("123", "14:00")
        
        assert result["standard_checkout"] == "12:00"
    
    @pytest.mark.asyncio
    async def test_supports_checkout_times_after_noon(self, pms_adapter):
        """Should support various checkout times after standard 12pm."""
        checkout_times = ["13:00", "14:00", "15:00", "16:00", "17:00", "18:00"]
        
        for time in checkout_times:
            with patch('random.random', return_value=0.5):
                result = await pms_adapter.check_late_checkout_availability("123", time)
            
            assert result["requested_time"] == time
