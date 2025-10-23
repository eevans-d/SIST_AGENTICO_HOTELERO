#!/usr/bin/env python3
# ════════════════════════════════════════════════════════════════════════════════
# Smoke Tests for Staging Deployment
# ════════════════════════════════════════════════════════════════════════════════
# Purpose: Validate all 7 services are working correctly
# Usage: python scripts/smoke_tests.py
# Generated: 2025-10-23
# ════════════════════════════════════════════════════════════════════════════════

import asyncio
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Tuple
import httpx
import psycopg2
import redis

# ════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════════

SERVICES_CONFIG = {
    "agente_api": {
        "host": "localhost",
        "port": 8002,
        "type": "http",
        "endpoints": [
            {"path": "/health/live", "expected_status": 200},
            {"path": "/health/ready", "expected_status": 200},
        ]
    },
    "postgres": {
        "host": "localhost",
        "port": 5432,
        "type": "database",
        "user": "agente_user",
        "password": "staging_secure_pass_12345",
        "database": "agente_hotel_staging"
    },
    "redis": {
        "host": "localhost",
        "port": 6379,
        "type": "cache",
        "db": 0
    },
    "prometheus": {
        "host": "localhost",
        "port": 9090,
        "type": "http",
        "endpoints": [
            {"path": "/-/healthy", "expected_status": 200},
            {"path": "/api/v1/query?query=up", "expected_status": 200}
        ]
    },
    "grafana": {
        "host": "localhost",
        "port": 3000,
        "type": "http",
        "endpoints": [
            {"path": "/api/health", "expected_status": 200}
        ]
    },
    "alertmanager": {
        "host": "localhost",
        "port": 9093,
        "type": "http",
        "endpoints": [
            {"path": "/-/healthy", "expected_status": 200}
        ]
    },
    "jaeger": {
        "host": "localhost",
        "port": 16686,
        "type": "http",
        "endpoints": [
            {"path": "/api/traces", "expected_status": 200}
        ]
    }
}

# ════════════════════════════════════════════════════════════════════════════════
# TEST RESULTS
# ════════════════════════════════════════════════════════════════════════════════

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.tests = []
    
    def add_pass(self, service: str, test: str, duration_ms: float = 0):
        self.passed += 1
        self.tests.append({
            "status": "PASS",
            "service": service,
            "test": test,
            "duration_ms": duration_ms
        })
    
    def add_fail(self, service: str, test: str, error: str, duration_ms: float = 0):
        self.failed += 1
        self.tests.append({
            "status": "FAIL",
            "service": service,
            "test": test,
            "error": error,
            "duration_ms": duration_ms
        })
    
    def add_warning(self, service: str, test: str, message: str):
        self.warnings += 1
        self.tests.append({
            "status": "WARN",
            "service": service,
            "test": test,
            "message": message
        })
    
    def summary(self) -> Dict:
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0
        return {
            "total": total,
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "pass_rate": pass_rate,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def print_report(self):
        summary = self.summary()
        
        print("\n╔════════════════════════════════════════════════════════════════╗")
        print("║              📊 SMOKE TEST RESULTS REPORT                    ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        
        print(f"\n📈 SUMMARY")
        print(f"   Total Tests:  {summary['total']}")
        print(f"   ✅ Passed:    {summary['passed']}")
        print(f"   ❌ Failed:    {summary['failed']}")
        print(f"   ⚠️  Warnings: {summary['warnings']}")
        print(f"   Success Rate: {summary['pass_rate']:.1f}%")
        
        print(f"\n📋 DETAILED RESULTS")
        print(f"   {'Service':<20} {'Test':<30} {'Status':<10} {'Duration':<12}")
        print("   " + "─" * 80)
        
        for test in self.tests:
            status_icon = "✅" if test["status"] == "PASS" else "❌" if test["status"] == "FAIL" else "⚠️ "
            duration = f"{test.get('duration_ms', 0):.2f}ms" if test.get('duration_ms') else "-"
            print(f"   {test['service']:<20} {test['test']:<30} {status_icon} {test['status']:<8} {duration:<12}")
        
        if summary['failed'] == 0:
            print("\n✅ ════════════════════════════════════════════════════════════════")
            print("✅ ALL SMOKE TESTS PASSED! System ready for operation")
            print("✅ ════════════════════════════════════════════════════════════════")
        else:
            print("\n❌ ════════════════════════════════════════════════════════════════")
            print("❌ SOME TESTS FAILED - Review errors above")
            print("❌ ════════════════════════════════════════════════════════════════")

# ════════════════════════════════════════════════════════════════════════════════
# TEST FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════════

async def test_http_service(results: TestResults, service_name: str, config: Dict):
    """Test HTTP service health endpoints."""
    base_url = f"http://{config['host']}:{config['port']}"
    
    for endpoint in config.get("endpoints", []):
        test_name = f"GET {endpoint['path']}"
        start = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{base_url}{endpoint['path']}")
                duration = (time.time() - start) * 1000
                
                if response.status_code == endpoint.get("expected_status", 200):
                    results.add_pass(service_name, test_name, duration)
                else:
                    results.add_fail(
                        service_name,
                        test_name,
                        f"Expected {endpoint.get('expected_status', 200)}, got {response.status_code}",
                        duration
                    )
        except Exception as e:
            duration = (time.time() - start) * 1000
            results.add_fail(service_name, test_name, str(e), duration)

def test_postgres_service(results: TestResults, service_name: str, config: Dict):
    """Test PostgreSQL connectivity and basic operations."""
    test_name = "Database Connection"
    start = time.time()
    
    try:
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"]
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        cursor.close()
        conn.close()
        
        duration = (time.time() - start) * 1000
        results.add_pass(service_name, test_name, duration)
    except Exception as e:
        duration = (time.time() - start) * 1000
        results.add_fail(service_name, test_name, str(e), duration)

def test_redis_service(results: TestResults, service_name: str, config: Dict):
    """Test Redis connectivity and basic operations."""
    test_name = "Cache Connection"
    start = time.time()
    
    try:
        r = redis.Redis(
            host=config["host"],
            port=config["port"],
            db=config.get("db", 0),
            decode_responses=True
        )
        r.ping()
        
        # Test set/get
        r.set("smoke_test_key", "smoke_test_value", ex=10)
        value = r.get("smoke_test_key")
        
        if value == "smoke_test_value":
            duration = (time.time() - start) * 1000
            results.add_pass(service_name, test_name, duration)
        else:
            results.add_fail(service_name, test_name, "Set/Get mismatch")
    except Exception as e:
        duration = (time.time() - start) * 1000
        results.add_fail(service_name, test_name, str(e), duration)

async def run_all_tests():
    """Run all smoke tests."""
    results = TestResults()
    
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║          🧪 STARTING STAGING DEPLOYMENT SMOKE TESTS           ║")
    print("╚════════════════════════════════════════════════════════════════╝\n")
    
    for service_name, config in SERVICES_CONFIG.items():
        print(f"🔍 Testing {service_name}...")
        
        service_type = config.get("type")
        
        try:
            if service_type == "http":
                await test_http_service(results, service_name, config)
            elif service_type == "database":
                test_postgres_service(results, service_name, config)
            elif service_type == "cache":
                test_redis_service(results, service_name, config)
        except Exception as e:
            results.add_fail(service_name, "Service Test", str(e))
    
    results.print_report()
    return results.failed == 0

# ════════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════════

async def main():
    success = await run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
