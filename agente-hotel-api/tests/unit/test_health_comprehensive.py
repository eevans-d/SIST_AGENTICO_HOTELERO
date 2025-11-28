# [MEGA PLAN FASE 4] tests/unit/test_health_comprehensive.py
"""
Comprehensive tests for Health router endpoints.
Target: 70-80% coverage for health.py

Test Categories:
1. Liveness Check (3 tests)
2. Readiness Check (10 tests)
3. Basic Health Check (3 tests)
4. Metrics Integration (4 tests)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.execute.return_value = MagicMock()
    return db


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.ping.return_value = True
    return redis_mock


# ============================================================================
# 1. Liveness Check (3 tests)
# ============================================================================

class TestLivenessCheck:
    """Tests for /health/live endpoint."""

    @pytest.mark.asyncio
    async def test_liveness_returns_alive(self):
        """Test liveness check returns alive=True."""
        from app.routers.health import liveness_check
        
        response = await liveness_check()
        assert response["alive"] is True
        assert "timestamp" in response

    @pytest.mark.asyncio
    async def test_liveness_timestamp_is_iso_format(self):
        """Test liveness timestamp is ISO 8601 format."""
        from app.routers.health import liveness_check
        
        response = await liveness_check()
        # Should parse without error
        parsed = datetime.fromisoformat(response["timestamp"].replace("Z", "+00:00"))
        assert parsed is not None

    @pytest.mark.asyncio
    async def test_liveness_always_succeeds(self):
        """Test liveness check always returns regardless of dependencies."""
        from app.routers.health import liveness_check
        
        # Even if DB/Redis are down, liveness should succeed
        response = await liveness_check()
        assert response["alive"] is True


# ============================================================================
# 2. Readiness Check (10 tests)
# ============================================================================

class TestReadinessCheck:
    """Tests for /health/ready endpoint."""

    @pytest.mark.asyncio
    async def test_readiness_all_healthy(self, mock_db, mock_redis):
        """Test readiness when all dependencies are healthy."""
        from app.routers.health import readiness_check
        
        with patch.dict("os.environ", {"CHECK_DB_IN_READINESS": "true", "CHECK_REDIS_IN_READINESS": "true"}):
            with patch("app.routers.health.settings") as mock_settings:
                mock_settings.check_pms_in_readiness = False
                mock_settings.pms_type = None
                
                response = await readiness_check(db=mock_db, redis_client=mock_redis)
        
        # JSONResponse has body attribute
        import json
        data = json.loads(response.body)
        assert data["ready"] is True
        assert data["checks"]["database"] is True
        assert data["checks"]["redis"] is True

    @pytest.mark.asyncio
    async def test_readiness_database_down(self, mock_redis):
        """Test readiness returns 503 when database is down."""
        from app.routers.health import readiness_check
        
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Connection refused")
        
        with patch.dict("os.environ", {"CHECK_DB_IN_READINESS": "true", "CHECK_REDIS_IN_READINESS": "true"}):
            with patch("app.routers.health.settings") as mock_settings:
                mock_settings.check_pms_in_readiness = False
                mock_settings.pms_type = None
                
                response = await readiness_check(db=mock_db, redis_client=mock_redis)
        
        assert response.status_code == 503
        import json
        data = json.loads(response.body)
        assert data["ready"] is False
        assert data["checks"]["database"] is False

    @pytest.mark.asyncio
    async def test_readiness_redis_down(self, mock_db):
        """Test readiness returns 503 when Redis is down."""
        from app.routers.health import readiness_check
        
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = Exception("Connection refused")
        
        with patch.dict("os.environ", {"CHECK_DB_IN_READINESS": "true", "CHECK_REDIS_IN_READINESS": "true"}):
            with patch("app.routers.health.settings") as mock_settings:
                mock_settings.check_pms_in_readiness = False
                mock_settings.pms_type = None
                
                response = await readiness_check(db=mock_db, redis_client=mock_redis)
        
        assert response.status_code == 503
        import json
        data = json.loads(response.body)
        assert data["ready"] is False
        assert data["checks"]["redis"] is False

    @pytest.mark.asyncio
    async def test_readiness_db_check_disabled(self, mock_redis):
        """Test readiness skips DB check when disabled."""
        from app.routers.health import readiness_check
        
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("DB Error")  # Would fail if checked
        
        with patch.dict("os.environ", {"CHECK_DB_IN_READINESS": "false", "CHECK_REDIS_IN_READINESS": "true"}):
            with patch("app.routers.health.settings") as mock_settings:
                mock_settings.check_pms_in_readiness = False
                mock_settings.pms_type = None
                
                response = await readiness_check(db=mock_db, redis_client=mock_redis)
        
        assert response.status_code == 200
        import json
        data = json.loads(response.body)
        assert data["checks"]["database"] is True  # Skipped = True

    @pytest.mark.asyncio
    async def test_readiness_redis_check_disabled(self, mock_db):
        """Test readiness skips Redis check when disabled."""
        from app.routers.health import readiness_check
        
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = Exception("Redis Error")  # Would fail if checked
        
        with patch.dict("os.environ", {"CHECK_DB_IN_READINESS": "true", "CHECK_REDIS_IN_READINESS": "false"}):
            with patch("app.routers.health.settings") as mock_settings:
                mock_settings.check_pms_in_readiness = False
                mock_settings.pms_type = None
                
                response = await readiness_check(db=mock_db, redis_client=mock_redis)
        
        assert response.status_code == 200
        import json
        data = json.loads(response.body)
        assert data["checks"]["redis"] is True  # Skipped = True

    @pytest.mark.asyncio
    async def test_readiness_pms_check_mock_mode(self, mock_db, mock_redis):
        """Test PMS check is skipped in mock mode."""
        from app.routers.health import readiness_check
        
        with patch.dict("os.environ", {"CHECK_DB_IN_READINESS": "true", "CHECK_REDIS_IN_READINESS": "true"}):
            with patch("app.routers.health.settings") as mock_settings:
                mock_settings.check_pms_in_readiness = True
                mock_pms_type = MagicMock()
                mock_pms_type.value = "mock"
                mock_settings.pms_type = mock_pms_type
                
                response = await readiness_check(db=mock_db, redis_client=mock_redis)
        
        import json
        data = json.loads(response.body)
        assert data["checks"]["pms"] is True  # Mock mode = True

    @pytest.mark.asyncio
    async def test_readiness_pms_check_disabled(self, mock_db, mock_redis):
        """Test PMS check skipped when not required."""
        from app.routers.health import readiness_check
        
        with patch.dict("os.environ", {"CHECK_DB_IN_READINESS": "true", "CHECK_REDIS_IN_READINESS": "true"}):
            with patch("app.routers.health.settings") as mock_settings:
                mock_settings.check_pms_in_readiness = False
                mock_settings.pms_type = None
                
                response = await readiness_check(db=mock_db, redis_client=mock_redis)
        
        import json
        data = json.loads(response.body)
        assert data["checks"]["pms"] is True

    @pytest.mark.asyncio
    async def test_readiness_pms_real_check_success(self, mock_db, mock_redis):
        """Test real PMS check when enabled and succeeds."""
        from app.routers.health import readiness_check
        
        with patch.dict("os.environ", {"CHECK_DB_IN_READINESS": "true", "CHECK_REDIS_IN_READINESS": "true"}):
            with patch("app.routers.health.settings") as mock_settings:
                mock_settings.check_pms_in_readiness = True
                mock_pms_type = MagicMock()
                mock_pms_type.value = "qloapps"
                mock_settings.pms_type = mock_pms_type
                mock_settings.pms_base_url = "http://pms.example.com"
                
                with patch("app.routers.health.httpx.AsyncClient") as mock_client:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
                    
                    response = await readiness_check(db=mock_db, redis_client=mock_redis)
        
        import json
        data = json.loads(response.body)
        assert data["checks"]["pms"] is True

    @pytest.mark.asyncio
    async def test_readiness_pms_real_check_failure(self, mock_db, mock_redis):
        """Test real PMS check when enabled and fails."""
        from app.routers.health import readiness_check
        
        with patch.dict("os.environ", {"CHECK_DB_IN_READINESS": "true", "CHECK_REDIS_IN_READINESS": "true"}):
            with patch("app.routers.health.settings") as mock_settings:
                mock_settings.check_pms_in_readiness = True
                mock_pms_type = MagicMock()
                mock_pms_type.value = "qloapps"
                mock_settings.pms_type = mock_pms_type
                mock_settings.pms_base_url = "http://pms.example.com"
                
                with patch("app.routers.health.httpx.AsyncClient") as mock_client:
                    mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=Exception("PMS unreachable"))
                    
                    response = await readiness_check(db=mock_db, redis_client=mock_redis)
        
        assert response.status_code == 503
        import json
        data = json.loads(response.body)
        assert data["checks"]["pms"] is False

    @pytest.mark.asyncio
    async def test_readiness_returns_timestamp(self, mock_db, mock_redis):
        """Test readiness response includes timestamp."""
        from app.routers.health import readiness_check
        
        with patch.dict("os.environ", {"CHECK_DB_IN_READINESS": "true", "CHECK_REDIS_IN_READINESS": "true"}):
            with patch("app.routers.health.settings") as mock_settings:
                mock_settings.check_pms_in_readiness = False
                mock_settings.pms_type = None
                
                response = await readiness_check(db=mock_db, redis_client=mock_redis)
        
        import json
        data = json.loads(response.body)
        assert "timestamp" in data
        # Should be valid ISO format
        parsed = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        assert parsed is not None


# ============================================================================
# 3. Basic Health Check (3 tests)
# ============================================================================

class TestBasicHealthCheck:
    """Tests for /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_healthy(self):
        """Test basic health check returns healthy status."""
        from app.routers.health import health_check
        
        response = await health_check()
        assert response["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_includes_timestamp(self):
        """Test health check includes timestamp."""
        from app.routers.health import health_check
        
        response = await health_check()
        assert "timestamp" in response

    @pytest.mark.asyncio
    async def test_health_timestamp_format(self):
        """Test health timestamp is valid ISO format."""
        from app.routers.health import health_check
        
        response = await health_check()
        # Should parse without error
        ts = response["timestamp"]
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None


# ============================================================================
# 4. Metrics Integration (4 tests)
# ============================================================================

class TestMetricsIntegration:
    """Tests for metrics updates during health checks."""

    @pytest.mark.asyncio
    async def test_readiness_updates_dependency_metrics(self, mock_db, mock_redis):
        """Test readiness updates dependency_up metric."""
        from app.routers.health import readiness_check
        
        with patch.dict("os.environ", {"CHECK_DB_IN_READINESS": "true", "CHECK_REDIS_IN_READINESS": "true"}):
            with patch("app.routers.health.settings") as mock_settings:
                mock_settings.check_pms_in_readiness = False
                mock_settings.pms_type = None
                
                with patch("app.routers.health.dependency_up") as mock_dep:
                    await readiness_check(db=mock_db, redis_client=mock_redis)
                    
                    # Should have called labels for each dependency
                    assert mock_dep.labels.called

    @pytest.mark.asyncio
    async def test_readiness_updates_readiness_up_metric(self, mock_db, mock_redis):
        """Test readiness updates readiness_up gauge."""
        from app.routers.health import readiness_check
        
        with patch.dict("os.environ", {"CHECK_DB_IN_READINESS": "true", "CHECK_REDIS_IN_READINESS": "true"}):
            with patch("app.routers.health.settings") as mock_settings:
                mock_settings.check_pms_in_readiness = False
                mock_settings.pms_type = None
                
                with patch("app.routers.health.readiness_up") as mock_ready:
                    await readiness_check(db=mock_db, redis_client=mock_redis)
                    
                    mock_ready.set.assert_called_with(1)

    @pytest.mark.asyncio
    async def test_readiness_updates_timestamp_metric(self, mock_db, mock_redis):
        """Test readiness updates last check timestamp."""
        from app.routers.health import readiness_check
        
        with patch.dict("os.environ", {"CHECK_DB_IN_READINESS": "true", "CHECK_REDIS_IN_READINESS": "true"}):
            with patch("app.routers.health.settings") as mock_settings:
                mock_settings.check_pms_in_readiness = False
                mock_settings.pms_type = None
                
                with patch("app.routers.health.readiness_last_check_timestamp") as mock_ts:
                    await readiness_check(db=mock_db, redis_client=mock_redis)
                    
                    # Should have called set with a timestamp
                    assert mock_ts.set.called

    @pytest.mark.asyncio
    async def test_readiness_metrics_error_handling(self, mock_db, mock_redis):
        """Test readiness handles metrics update errors gracefully."""
        from app.routers.health import readiness_check
        
        with patch.dict("os.environ", {"CHECK_DB_IN_READINESS": "true", "CHECK_REDIS_IN_READINESS": "true"}):
            with patch("app.routers.health.settings") as mock_settings:
                mock_settings.check_pms_in_readiness = False
                mock_settings.pms_type = None
                
                with patch("app.routers.health.dependency_up") as mock_dep:
                    mock_dep.labels.side_effect = Exception("Metrics error")
                    
                    # Should not raise even if metrics fail
                    response = await readiness_check(db=mock_db, redis_client=mock_redis)
                    
                    # Response should still be valid
                    assert response.status_code == 200
