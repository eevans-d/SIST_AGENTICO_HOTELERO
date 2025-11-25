#!/usr/bin/env python3
"""
Final Validation Runner for Audio System
Comprehensive end-to-end validation of the complete audio system
"""

import asyncio
import aiohttp
import time
import json
import sys
from typing import Dict, List, Any
from dataclasses import dataclass
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    test_name: str
    success: bool
    duration: float
    details: Dict[str, Any]
    error_message: str = ""


class AudioSystemValidator:
    """Comprehensive validation suite for the audio system"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.results: List[ValidationResult] = []

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def validate_system_health(self) -> ValidationResult:
        """Validate basic system health endpoints"""
        start_time = time.time()

        try:
            # Test liveness endpoint
            async with self.session.get(f"{self.base_url}/health/live") as response:
                if response.status != 200:
                    raise Exception(f"Liveness check failed: {response.status}")

            # Test readiness endpoint
            async with self.session.get(f"{self.base_url}/health/ready") as response:
                if response.status != 200:
                    raise Exception(f"Readiness check failed: {response.status}")

                data = await response.json()
                if not data.get("healthy", False):
                    raise Exception(f"System not ready: {data}")

            duration = time.time() - start_time
            return ValidationResult(
                test_name="system_health",
                success=True,
                duration=duration,
                details={"liveness": "ok", "readiness": "ok"},
            )

        except Exception as e:
            return ValidationResult(
                test_name="system_health",
                success=False,
                duration=time.time() - start_time,
                details={},
                error_message=str(e),
            )

    async def validate_audio_processing(self) -> ValidationResult:
        """Validate audio processing capabilities"""
        start_time = time.time()

        try:
            # Test audio processing endpoint
            test_payload = {
                "audio_data": "dGVzdCBhdWRpbyBkYXRh",  # base64 encoded test data
                "format": "wav",
                "operation": "optimize",
            }

            async with self.session.post(f"{self.base_url}/api/audio/process", json=test_payload) as response:
                if response.status != 200:
                    raise Exception(f"Audio processing failed: {response.status}")

                result = await response.json()
                if not result.get("success", False):
                    raise Exception(f"Audio processing unsuccessful: {result}")

            duration = time.time() - start_time
            return ValidationResult(test_name="audio_processing", success=True, duration=duration, details=result)

        except Exception as e:
            return ValidationResult(
                test_name="audio_processing",
                success=False,
                duration=time.time() - start_time,
                details={},
                error_message=str(e),
            )

    async def validate_cache_performance(self) -> ValidationResult:
        """Validate cache performance metrics"""
        start_time = time.time()

        try:
            # Test cache operations
            test_operations = []

            for i in range(10):
                cache_payload = {"key": f"test_key_{i}", "value": f"test_value_{i}", "operation": "set"}

                async with self.session.post(f"{self.base_url}/api/cache/operation", json=cache_payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        test_operations.append(result)

            # Validate cache hit rate from metrics
            async with self.session.get(f"{self.base_url}/metrics") as response:
                if response.status == 200:
                    metrics_text = await response.text()
                    # Parse cache metrics
                    cache_hits = 0
                    cache_misses = 0

                    for line in metrics_text.split("\n"):
                        if "audio_cache_hits_total" in line and not line.startswith("#"):
                            cache_hits += float(line.split()[-1])
                        elif "audio_cache_misses_total" in line and not line.startswith("#"):
                            cache_misses += float(line.split()[-1])

                    hit_rate = cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0

                    duration = time.time() - start_time
                    return ValidationResult(
                        test_name="cache_performance",
                        success=hit_rate >= 0.7,  # Expect at least 70% hit rate
                        duration=duration,
                        details={
                            "cache_hits": cache_hits,
                            "cache_misses": cache_misses,
                            "hit_rate": hit_rate,
                            "operations_tested": len(test_operations),
                        },
                    )

            raise Exception("Could not retrieve metrics")

        except Exception as e:
            return ValidationResult(
                test_name="cache_performance",
                success=False,
                duration=time.time() - start_time,
                details={},
                error_message=str(e),
            )

    async def validate_compression_efficiency(self) -> ValidationResult:
        """Validate compression system efficiency"""
        start_time = time.time()

        try:
            # Test different compression levels
            compression_results = []

            for level in [1, 3, 5]:
                compression_payload = {
                    "data": "VGhpcyBpcyBhIHRlc3QgYXVkaW8gZmlsZSB3aXRoIHNvbWUgcmVwZXRpdGl2ZSBkYXRhLiBUaGlzIGlzIGEgdGVzdCBhdWRpbyBmaWxlIHdpdGggc29tZSByZXBldGl0aXZlIGRhdGEu",
                    "level": level,
                    "format": "wav",
                }

                async with self.session.post(
                    f"{self.base_url}/api/audio/compress", json=compression_payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        compression_results.append(
                            {
                                "level": level,
                                "ratio": result.get("compression_ratio", 1.0),
                                "duration": result.get("processing_time", 0),
                            }
                        )

            # Validate compression ratios are reasonable
            avg_ratio = sum(r["ratio"] for r in compression_results) / len(compression_results)

            duration = time.time() - start_time
            return ValidationResult(
                test_name="compression_efficiency",
                success=avg_ratio >= 1.5,  # Expect at least 1.5x compression
                duration=duration,
                details={"compression_results": compression_results, "average_ratio": avg_ratio},
            )

        except Exception as e:
            return ValidationResult(
                test_name="compression_efficiency",
                success=False,
                duration=time.time() - start_time,
                details={},
                error_message=str(e),
            )

    async def validate_connection_pooling(self) -> ValidationResult:
        """Validate connection pool health and efficiency"""
        start_time = time.time()

        try:
            # Test concurrent connections
            concurrent_tasks = []

            async def make_request(request_id: int):
                async with self.session.get(f"{self.base_url}/api/pool/status") as response:
                    if response.status == 200:
                        return {"id": request_id, "status": "success"}
                    else:
                        return {"id": request_id, "status": "failed", "code": response.status}

            # Create 20 concurrent requests
            for i in range(20):
                concurrent_tasks.append(make_request(i))

            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)

            successful_requests = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")

            # Check pool metrics
            async with self.session.get(f"{self.base_url}/metrics") as response:
                if response.status == 200:
                    metrics_text = await response.text()
                    pool_health = 1.0  # Default

                    for line in metrics_text.split("\n"):
                        if "audio_pool_health_score" in line and not line.startswith("#"):
                            pool_health = float(line.split()[-1])
                            break

                    duration = time.time() - start_time
                    return ValidationResult(
                        test_name="connection_pooling",
                        success=successful_requests >= 18 and pool_health >= 0.8,
                        duration=duration,
                        details={
                            "total_requests": 20,
                            "successful_requests": successful_requests,
                            "pool_health_score": pool_health,
                            "success_rate": successful_requests / 20,
                        },
                    )

            raise Exception("Could not retrieve pool metrics")

        except Exception as e:
            return ValidationResult(
                test_name="connection_pooling",
                success=False,
                duration=time.time() - start_time,
                details={},
                error_message=str(e),
            )

    async def validate_monitoring_integration(self) -> ValidationResult:
        """Validate monitoring and metrics integration"""
        start_time = time.time()

        try:
            # Test metrics endpoint
            async with self.session.get(f"{self.base_url}/metrics") as response:
                if response.status != 200:
                    raise Exception(f"Metrics endpoint failed: {response.status}")

                metrics_text = await response.text()

                # Check for required metrics
                required_metrics = [
                    "audio_cache_hits_total",
                    "audio_cache_misses_total",
                    "audio_compression_operations_total",
                    "audio_pool_health_score",
                    "audio_cache_operation_seconds",
                ]

                missing_metrics = []
                for metric in required_metrics:
                    if metric not in metrics_text:
                        missing_metrics.append(metric)

                if missing_metrics:
                    raise Exception(f"Missing required metrics: {missing_metrics}")

                # Count total metrics
                metric_lines = [
                    line for line in metrics_text.split("\n") if line and not line.startswith("#") and "audio_" in line
                ]

                duration = time.time() - start_time
                return ValidationResult(
                    test_name="monitoring_integration",
                    success=len(missing_metrics) == 0,
                    duration=duration,
                    details={
                        "total_audio_metrics": len(metric_lines),
                        "required_metrics_present": len(required_metrics) - len(missing_metrics),
                        "missing_metrics": missing_metrics,
                    },
                )

        except Exception as e:
            return ValidationResult(
                test_name="monitoring_integration",
                success=False,
                duration=time.time() - start_time,
                details={},
                error_message=str(e),
            )

    async def run_all_validations(self) -> Dict[str, Any]:
        """Run all validation tests"""
        logger.info("🔬 Starting comprehensive audio system validation...")

        # Define validation tests
        validations = [
            self.validate_system_health,
            self.validate_audio_processing,
            self.validate_cache_performance,
            self.validate_compression_efficiency,
            self.validate_connection_pooling,
            self.validate_monitoring_integration,
        ]

        # Run all validations
        for validation_func in validations:
            logger.info(f"Running {validation_func.__name__}...")
            result = await validation_func()
            self.results.append(result)

            if result.success:
                logger.info(f"✅ {result.test_name} - PASSED ({result.duration:.3f}s)")
            else:
                logger.error(f"❌ {result.test_name} - FAILED ({result.duration:.3f}s): {result.error_message}")

        # Generate summary
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        total_duration = sum(r.duration for r in self.results)

        summary = {
            "validation_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": passed_tests / total_tests,
                "total_duration": total_duration,
                "timestamp": time.time(),
            },
            "test_results": [
                {
                    "test_name": r.test_name,
                    "success": r.success,
                    "duration": r.duration,
                    "details": r.details,
                    "error_message": r.error_message,
                }
                for r in self.results
            ],
        }

        return summary


async def main():
    """Main validation runner"""
    logger.info("🎵 Audio System - Final Validation Suite")
    logger.info("=" * 50)

    async with AudioSystemValidator() as validator:
        summary = await validator.run_all_validations()

        # Print results
        print("\n" + "=" * 50)
        print("🎯 VALIDATION SUMMARY")
        print("=" * 50)

        validation_summary = summary["validation_summary"]
        print(f"Total Tests: {validation_summary['total_tests']}")
        print(f"Passed: {validation_summary['passed_tests']}")
        print(f"Failed: {validation_summary['failed_tests']}")
        print(f"Success Rate: {validation_summary['success_rate']:.1%}")
        print(f"Total Duration: {validation_summary['total_duration']:.3f}s")

        # Save detailed results
        results_file = Path("validation_results.json")
        with open(results_file, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\n📊 Detailed results saved to: {results_file}")

        # Determine overall success
        if validation_summary["success_rate"] >= 0.9:
            print("\n🎉 VALIDATION PASSED - System ready for production!")
            return 0
        elif validation_summary["success_rate"] >= 0.7:
            print("\n⚠️  VALIDATION PARTIAL - Some issues detected, review required")
            return 1
        else:
            print("\n❌ VALIDATION FAILED - System not ready for production")
            return 2


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Validation failed with error: {e}")
        sys.exit(1)
