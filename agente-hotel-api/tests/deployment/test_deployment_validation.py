"""
Deployment Validation Tests

Smoke tests, integration checks, and rollback verification for
automated deployments.

Author: AI Agent
Date: October 15, 2025
"""

import asyncio
import pytest
from httpx import AsyncClient, ConnectError, HTTPStatusError
import time
from typing import Dict, List

# Test configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 30
RETRY_INTERVAL = 2
MAX_RETRIES = 10


class DeploymentValidator:
    """Validates deployment health and functionality"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = None
    
    async def __aenter__(self):
        self.client = AsyncClient(base_url=self.base_url, timeout=TIMEOUT)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def wait_for_ready(self, max_retries: int = MAX_RETRIES) -> bool:
        """Wait for service to be ready"""
        for attempt in range(max_retries):
            try:
                response = await self.client.get("/health/ready")
                if response.status_code == 200:
                    return True
            except (ConnectError, HTTPStatusError):
                pass
            
            await asyncio.sleep(RETRY_INTERVAL)
        
        return False
    
    async def check_health_endpoints(self) -> Dict[str, bool]:
        """Check all health endpoints"""
        endpoints = {
            "/health/live": False,
            "/health/ready": False,
            "/metrics": False,
        }
        
        for endpoint in endpoints.keys():
            try:
                response = await self.client.get(endpoint)
                endpoints[endpoint] = response.status_code == 200
            except Exception:
                endpoints[endpoint] = False
        
        return endpoints
    
    async def check_api_endpoints(self) -> Dict[str, bool]:
        """Check critical API endpoints"""
        endpoints = {
            "/api/v1/webhooks/whatsapp": False,  # POST endpoint
            "/docs": False,  # OpenAPI docs
        }
        
        # GET /docs
        try:
            response = await self.client.get("/docs")
            endpoints["/docs"] = response.status_code == 200
        except Exception:
            endpoints["/docs"] = False
        
        # POST webhook (without payload - expect 422 or similar, not 500)
        try:
            response = await self.client.post(
                "/api/v1/webhooks/whatsapp",
                json={}
            )
            # Any response except 500 is acceptable (endpoint is alive)
            endpoints["/api/v1/webhooks/whatsapp"] = response.status_code != 500
        except Exception:
            endpoints["/api/v1/webhooks/whatsapp"] = False
        
        return endpoints
    
    async def check_database_connectivity(self) -> bool:
        """Check if database connection is working"""
        try:
            # Health endpoint should validate DB
            response = await self.client.get("/health/ready")
            data = response.json()
            return data.get("database", {}).get("status") == "healthy"
        except Exception:
            return False
    
    async def check_redis_connectivity(self) -> bool:
        """Check if Redis connection is working"""
        try:
            response = await self.client.get("/health/ready")
            data = response.json()
            return data.get("redis", {}).get("status") == "healthy"
        except Exception:
            return False
    
    async def measure_response_time(self, endpoint: str = "/health/live") -> float:
        """Measure endpoint response time in milliseconds"""
        start = time.time()
        try:
            await self.client.get(endpoint)
            return (time.time() - start) * 1000
        except Exception:
            return -1.0


# ═══════════════════════════════════════════════════════════════════════════
# SMOKE TESTS
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@pytest.mark.deployment
async def test_service_is_reachable():
    """Test that the service is reachable"""
    async with DeploymentValidator() as validator:
        ready = await validator.wait_for_ready()
        assert ready, "Service failed to become ready within timeout"


@pytest.mark.asyncio
@pytest.mark.deployment
async def test_health_endpoints():
    """Test all health check endpoints"""
    async with DeploymentValidator() as validator:
        await validator.wait_for_ready()
        
        health_status = await validator.check_health_endpoints()
        
        assert health_status["/health/live"], "/health/live endpoint failed"
        assert health_status["/health/ready"], "/health/ready endpoint failed"
        assert health_status["/metrics"], "/metrics endpoint failed (non-critical)"


@pytest.mark.asyncio
@pytest.mark.deployment
async def test_api_endpoints_responsive():
    """Test that critical API endpoints are responsive"""
    async with DeploymentValidator() as validator:
        await validator.wait_for_ready()
        
        api_status = await validator.check_api_endpoints()
        
        assert api_status["/docs"], "OpenAPI docs endpoint failed"
        assert api_status["/api/v1/webhooks/whatsapp"], "WhatsApp webhook endpoint failed"


@pytest.mark.asyncio
@pytest.mark.deployment
async def test_database_connectivity():
    """Test database connectivity"""
    async with DeploymentValidator() as validator:
        await validator.wait_for_ready()
        
        db_healthy = await validator.check_database_connectivity()
        assert db_healthy, "Database connectivity check failed"


@pytest.mark.asyncio
@pytest.mark.deployment
async def test_redis_connectivity():
    """Test Redis connectivity"""
    async with DeploymentValidator() as validator:
        await validator.wait_for_ready()
        
        redis_healthy = await validator.check_redis_connectivity()
        assert redis_healthy, "Redis connectivity check failed"


@pytest.mark.asyncio
@pytest.mark.deployment
async def test_response_time_acceptable():
    """Test that response times are acceptable"""
    async with DeploymentValidator() as validator:
        await validator.wait_for_ready()
        
        response_time = await validator.measure_response_time()
        
        assert response_time > 0, "Failed to measure response time"
        assert response_time < 1000, f"Response time too high: {response_time}ms (expected < 1000ms)"


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.deployment
async def test_full_health_check_cycle():
    """Test full health check cycle"""
    async with DeploymentValidator() as validator:
        # 1. Wait for service
        ready = await validator.wait_for_ready(max_retries=15)
        assert ready, "Service not ready"
        
        # 2. Check all health endpoints
        health = await validator.check_health_endpoints()
        assert all(health.values()), f"Some health checks failed: {health}"
        
        # 3. Check database
        db_ok = await validator.check_database_connectivity()
        assert db_ok, "Database connectivity failed"
        
        # 4. Check Redis
        redis_ok = await validator.check_redis_connectivity()
        assert redis_ok, "Redis connectivity failed"
        
        # 5. Measure performance
        latency = await validator.measure_response_time()
        assert latency > 0 and latency < 2000, f"Latency out of range: {latency}ms"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.deployment
async def test_concurrent_health_checks():
    """Test concurrent health check requests"""
    async with DeploymentValidator() as validator:
        await validator.wait_for_ready()
        
        # Make 10 concurrent requests
        tasks = [
            validator.check_health_endpoints()
            for _ in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        for result in results:
            assert result["/health/live"], "Concurrent health check failed"
            assert result["/health/ready"], "Concurrent readiness check failed"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.deployment
async def test_api_availability_after_deployment():
    """Test that API is available after deployment"""
    async with DeploymentValidator() as validator:
        await validator.wait_for_ready()
        
        # Check OpenAPI docs
        response = await validator.client.get("/docs")
        assert response.status_code == 200
        
        # Check API v1 endpoints exist
        response = await validator.client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_spec = response.json()
        paths = openapi_spec.get("paths", {})
        
        # Verify critical paths exist
        assert "/health/live" in paths
        assert "/health/ready" in paths
        assert "/api/v1/webhooks/whatsapp" in paths


# ═══════════════════════════════════════════════════════════════════════════
# ROLLBACK VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@pytest.mark.rollback
@pytest.mark.deployment
async def test_rollback_service_healthy():
    """Test that service is healthy after rollback"""
    async with DeploymentValidator() as validator:
        # After rollback, service should be reachable
        ready = await validator.wait_for_ready(max_retries=20)
        assert ready, "Service not ready after rollback"
        
        # All health checks should pass
        health = await validator.check_health_endpoints()
        assert all(health.values()), f"Health checks failed after rollback: {health}"


@pytest.mark.asyncio
@pytest.mark.rollback
@pytest.mark.deployment
async def test_rollback_data_integrity():
    """Test data integrity after rollback"""
    async with DeploymentValidator() as validator:
        await validator.wait_for_ready()
        
        # Database should be accessible
        db_ok = await validator.check_database_connectivity()
        assert db_ok, "Database not accessible after rollback"
        
        # Redis should be accessible
        redis_ok = await validator.check_redis_connectivity()
        assert redis_ok, "Redis not accessible after rollback"


@pytest.mark.asyncio
@pytest.mark.rollback
@pytest.mark.deployment
async def test_rollback_performance_baseline():
    """Test that performance is at baseline after rollback"""
    async with DeploymentValidator() as validator:
        await validator.wait_for_ready()
        
        # Measure response time multiple times
        latencies = []
        for _ in range(5):
            latency = await validator.measure_response_time()
            latencies.append(latency)
            await asyncio.sleep(1)
        
        avg_latency = sum(latencies) / len(latencies)
        
        # Average latency should be acceptable
        assert avg_latency > 0, "Failed to measure latency"
        assert avg_latency < 1500, f"Average latency too high after rollback: {avg_latency}ms"


# ═══════════════════════════════════════════════════════════════════════════
# DEPLOYMENT METRICS
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@pytest.mark.metrics
@pytest.mark.deployment
async def test_prometheus_metrics_available():
    """Test that Prometheus metrics are being exposed"""
    async with DeploymentValidator() as validator:
        await validator.wait_for_ready()
        
        response = await validator.client.get("/metrics")
        assert response.status_code == 200
        
        metrics_text = response.text
        
        # Check for key metrics
        assert "http_requests_total" in metrics_text
        assert "http_request_duration_seconds" in metrics_text
        assert "process_cpu_seconds_total" in metrics_text


@pytest.mark.asyncio
@pytest.mark.metrics
@pytest.mark.deployment
async def test_deployment_tracking_metrics():
    """Test that deployment tracking metrics exist"""
    async with DeploymentValidator() as validator:
        await validator.wait_for_ready()
        
        response = await validator.client.get("/metrics")
        metrics_text = response.text
        
        # Should have deployment-related metrics
        # These would be custom metrics added by the application
        assert "app_info" in metrics_text or "build_info" in metrics_text


if __name__ == "__main__":
    # Run smoke tests
    pytest.main([
        __file__,
        "-v",
        "-m", "deployment",
        "--tb=short"
    ])
