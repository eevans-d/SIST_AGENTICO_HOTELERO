import pytest
import asyncio
import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.pms_adapter import QloAppsAdapter
from app.exceptions.pms_exceptions import PMSError, CircuitBreakerOpenError
from app.models.pms_schemas import RoomAvailability

# Mock settings
@pytest.fixture
def mock_settings():
    with patch("app.services.pms_adapter.settings") as mock:
        mock.pms_base_url = "http://pms.local"
        mock.pms_api_key.get_secret_value.return_value = "test_key"
        mock.pms_hotel_id = 1
        yield mock

@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    mock.get.return_value = None
    return mock

@pytest.fixture
def mock_qloapps_client():
    with patch("app.services.pms_adapter.create_qloapps_client") as mock_create:
        mock_client = AsyncMock()
        mock_create.return_value = mock_client
        yield mock_client

@pytest.fixture
def pms_adapter(mock_settings, mock_redis, mock_qloapps_client):
    adapter = QloAppsAdapter(redis_client=mock_redis)
    # Mock internal components
    adapter.circuit_breaker = MagicMock()
    adapter.circuit_breaker.call = AsyncMock()
    adapter.rate_limiter = AsyncMock()
    return adapter

@pytest.mark.asyncio
class TestPMSAdapterHardening:
    
    async def test_initialization(self, mock_settings, mock_redis):
        """Test adapter initialization"""
        adapter = QloAppsAdapter(redis_client=mock_redis)
        assert adapter.base_url == "http://pms.local"
        assert adapter.api_key == "test_key"
        assert adapter.hotel_id == 1
        assert adapter.redis == mock_redis

    async def test_check_availability_cache_hit(self, pms_adapter, mock_redis):
        """Test availability check with cache hit"""
        cached_data = [{"room_type": "Deluxe", "price": 100.0, "available": 5}]
        mock_redis.get.return_value = json.dumps(cached_data)
        
        result = await pms_adapter.check_availability(date(2023, 1, 1), date(2023, 1, 2))
        
        assert result == cached_data
        mock_redis.get.assert_called_once()
        pms_adapter.circuit_breaker.call.assert_not_called()

    async def test_check_availability_success(self, pms_adapter, mock_redis):
        """Test availability check success (cache miss)"""
        mock_redis.get.return_value = None
        
        # Mock circuit breaker call to return data
        pms_data = [{"id": 1, "room_type_name": "Deluxe", "price": 100.0, "quantity": 5}]
        pms_adapter.circuit_breaker.call.return_value = pms_data
        
        # Mock normalization
        pms_adapter._normalize_qloapps_availability = MagicMock(return_value=[
            {
                "room_id": "101",
                "room_type": "Deluxe",
                "price_per_night": 100.0,
                "available_rooms": 5,
                "max_occupancy": 2,
                "facilities": [],
                "images": [],
                "potentially_stale": False
            }
        ])
        
        result = await pms_adapter.check_availability(date(2023, 1, 1), date(2023, 1, 2))
        
        assert len(result) == 1
        assert result[0]["room_type"] == "Deluxe"
        assert result[0]["price_per_night"] == 100.0
        pms_adapter.circuit_breaker.call.assert_called_once()
        mock_redis.setex.assert_called_once()

    async def test_check_availability_validation_error(self, pms_adapter, mock_redis):
        """Test validation error on PMS response"""
        mock_redis.get.return_value = None
        pms_adapter.circuit_breaker.call.return_value = []
        
        # Return invalid data (missing required fields)
        pms_adapter._normalize_qloapps_availability = MagicMock(return_value=[
            {"room_type": "Deluxe"} # Missing price, available, etc.
        ])
        
        with pytest.raises(PMSError) as exc:
            await pms_adapter.check_availability(date(2023, 1, 1), date(2023, 1, 2))
        
        assert "Invalid PMS response format" in str(exc.value)

    async def test_check_availability_circuit_breaker_open(self, pms_adapter, mock_redis):
        """Test fallback when circuit breaker is open"""
        mock_redis.get.return_value = None
        pms_adapter.circuit_breaker.call.side_effect = CircuitBreakerOpenError("Open")
        
        stale_data = [{"room_type": "Stale", "price": 90.0, "available": 1}]
        # First call returns None (cache miss), second call returns stale data
        mock_redis.get.side_effect = [None, json.dumps(stale_data)]
        
        result = await pms_adapter.check_availability(date(2023, 1, 1), date(2023, 1, 2))
        
        expected = [{"room_type": "Stale", "price": 90.0, "available": 1, "potentially_stale": True}]
        assert result == expected

    async def test_invalidate_cache_pattern(self, pms_adapter, mock_redis):
        """Test cache invalidation by pattern"""
        mock_redis.scan.side_effect = [(10, [b"key1", b"key2"]), (0, [b"key3"])]
        
        await pms_adapter._invalidate_cache_pattern("prefix:*")
        
        assert mock_redis.delete.call_count == 2
        mock_redis.delete.assert_any_call(b"key1", b"key2")
        mock_redis.delete.assert_any_call(b"key3")

