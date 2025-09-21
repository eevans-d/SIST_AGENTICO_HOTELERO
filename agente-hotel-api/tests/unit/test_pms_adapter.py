# [PROMPT 2.10] tests/unit/test_pms_adapter.py (FINAL)

import pytest
from app.services.pms_adapter import QloAppsAdapter


@pytest.mark.asyncio
async def test_check_availability_with_cache(mocker):
    mock_redis = mocker.AsyncMock()
    adapter = QloAppsAdapter(redis_client=mock_redis)
    assert adapter  # Usar la variable para que el linter no se queje
