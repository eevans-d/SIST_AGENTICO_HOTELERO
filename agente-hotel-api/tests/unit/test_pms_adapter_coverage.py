import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, datetime
from app.services.pms_adapter import QloAppsAdapter
from app.exceptions.pms_exceptions import PMSError, PMSAuthError, CircuitBreakerOpenError

@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.get.return_value = None
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    redis.scan = AsyncMock(return_value=(0, []))
    return redis

@pytest.fixture
def mock_qloapps():
    client = AsyncMock()
    client.check_availability = AsyncMock()
    client.create_booking = AsyncMock()
    client.get_booking = AsyncMock()
    client.cancel_booking = AsyncMock()
    client.close = AsyncMock()
    return client

@pytest.fixture
def pms_adapter(mock_redis, mock_qloapps):
    with patch("app.services.pms_adapter.create_qloapps_client", return_value=mock_qloapps), \
         patch("app.services.pms_adapter.settings") as mock_settings:
        
        mock_settings.pms_base_url = "http://pms.test"
        mock_settings.pms_api_key.get_secret_value.return_value = "secret"
        mock_settings.pms_hotel_id = 1
        
        adapter = QloAppsAdapter(redis_client=mock_redis)
        # Replace the client created in __init__ with our mock
        adapter.qloapps = mock_qloapps
        return adapter

@pytest.mark.asyncio
async def test_check_availability_cache_hit(pms_adapter, mock_redis):
    # Setup
    mock_redis.get.return_value = '[{"room_type": "Double", "price": 100}]'
    
    # Execute
    result = await pms_adapter.check_availability(date(2023, 1, 1), date(2023, 1, 2))
    
    # Verify
    assert len(result) == 1
    assert result[0]["room_type"] == "Double"
    mock_redis.get.assert_called()
    pms_adapter.qloapps.check_availability.assert_not_called()

@pytest.mark.asyncio
async def test_check_availability_cache_miss_success(pms_adapter, mock_redis, mock_qloapps):
    # Setup
    mock_redis.get.return_value = None
    mock_qloapps.check_availability.return_value = [
        {"room_type_name": "Double", "price": 100, "quantity": 5}
    ]
    
    # Execute
    result = await pms_adapter.check_availability(date(2023, 1, 1), date(2023, 1, 2))
    
    # Verify
    assert len(result) == 1
    assert result[0]["room_type"] == "Double"
    mock_qloapps.check_availability.assert_called()
    mock_redis.setex.assert_called()

@pytest.mark.asyncio
async def test_check_availability_pms_error_fallback_stale(pms_adapter, mock_redis, mock_qloapps):
    # Setup
    mock_redis.get.side_effect = [None, '[{"room_type": "Double", "price": 100}]'] # First miss (fresh), then hit (stale)
    mock_qloapps.check_availability.side_effect = Exception("PMS Down")
    
    # Execute
    result = await pms_adapter.check_availability(date(2023, 1, 1), date(2023, 1, 2))
    
    # Verify
    assert len(result) == 1
    assert result[0]["potentially_stale"] is True
    assert result[0]["room_type"] == "Double"

@pytest.mark.asyncio
async def test_create_reservation_success(pms_adapter, mock_qloapps):
    # Setup
    reservation_data = {
        "checkin": "2023-01-01",
        "checkout": "2023-01-05",
        "room_type": "Double",
        "guest_name": "John Doe",
        "guest_email": "john@example.com",
        "price_per_night": 100
    }
    mock_qloapps.create_booking.return_value = {
        "booking_id": "123",
        "booking_reference": "REF123",
        "status": "confirmed",
        "total_amount": 400.0,
        "check_in": "2023-01-01",
        "check_out": "2023-01-05"
    }
    
    # Execute
    result = await pms_adapter.create_reservation(reservation_data)
    
    # Verify
    assert result["booking_id"] == "123"
    assert result["status"] == "confirmed"
    mock_qloapps.create_booking.assert_called()

@pytest.mark.asyncio
async def test_create_reservation_validation_error(pms_adapter, mock_qloapps):
    # Setup
    reservation_data = {
        "checkin": "2023-01-01",
        "checkout": "2023-01-05",
        "room_type": "Double"
    }
    mock_qloapps.create_booking.return_value = {
        "booking_id": "invalid_id", # Should be int or convertible
        # Missing required fields
    }
    
    # Execute & Verify
    with pytest.raises(PMSError) as excinfo:
        await pms_adapter.create_reservation(reservation_data)
    assert "Invalid reservation response format" in str(excinfo.value)

@pytest.mark.asyncio
async def test_get_reservation_success(pms_adapter, mock_qloapps):
    # Setup
    mock_qloapps.get_booking.return_value = {"id": 123, "status": "confirmed"}
    
    # Execute
    result = await pms_adapter.get_reservation("123")
    
    # Verify
    assert result["id"] == 123
    mock_qloapps.get_booking.assert_called_with(123)

@pytest.mark.asyncio
async def test_cancel_reservation_success(pms_adapter, mock_qloapps):
    # Setup
    mock_qloapps.cancel_booking.return_value = True
    
    # Execute
    result = await pms_adapter.cancel_reservation("123", reason="changed plans")
    
    # Verify
    assert result is True
    mock_qloapps.cancel_booking.assert_called_with(123, "changed plans")

@pytest.mark.asyncio
async def test_check_late_checkout_availability_generic_cache_hit(pms_adapter, mock_redis):
    # Setup
    mock_redis.get.return_value = '{"available": true, "fee": 20}'
    
    # Execute
    result = await pms_adapter.check_late_checkout_availability("123")
    
    # Verify
    assert result["available"] is True
    assert result["fee"] == 20
    mock_redis.get.assert_called()
