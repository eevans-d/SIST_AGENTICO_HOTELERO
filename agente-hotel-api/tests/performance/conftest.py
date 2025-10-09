"""
Configuración específica para pruebas de performance de audio.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

# Evitar imports del sistema principal para pruebas aisladas
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def redis_mock():
    """Mock de Redis para pruebas de performance."""
    mock_redis = Mock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock()
    mock_redis.keys = AsyncMock(return_value=[])
    mock_redis.delete = AsyncMock()
    return mock_redis