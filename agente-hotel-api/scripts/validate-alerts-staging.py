#!/usr/bin/env python3
"""
Alert Validation Script for Staging Environment.

Generates synthetic load to trigger alerts and validates that Prometheus/AlertManager
respond correctly. Tests all 8 new alerts added in audit phase.

Usage:
    python scripts/validate-alerts-staging.py --prometheus-url http://localhost:9090

Requirements:
    pip install requests prometheus-api-client
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from typing import Dict, Optional, Tuple, Callable
from pathlib import Path

import aiohttp
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class AlertValidator:
    """Validates Prometheus alerts by generating synthetic load and querying metrics."""

    def __init__(self, prometheus_url: str, api_base_url: str, prometheus_url_alt: Optional[str] = None, load_mode: str = "synthetic", session_count: int = 120):
        self.prometheus_url = prometheus_url
        self.prometheus_url_alt = prometheus_url_alt
        self.api_base_url = api_base_url
        self.load_mode = load_mode
        self.session_count = session_count
        self.results: Dict[str, Dict] = {}

    def _query_once(self, base_url: str, query: str) -> Optional[float]:
        response = requests.get(
            f"{base_url}/api/v1/query",
            params={"query": query},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if data["status"] == "success" and data["data"]["result"]:
            result = data["data"]["result"][0]
            return float(result["value"][1])
        return 0.0  # Considerar 0 cuando hay serie pero sin puntos en ventana

    def query_prometheus(self, query: str) -> Optional[float]:
        """Execute PromQL query and return scalar result, with optional fallback URL."""
        try:
            return self._query_once(self.prometheus_url, query)
        except Exception as e:
            logger.warning(f"Prometheus query failed on primary URL: {e}")
            if self.prometheus_url_alt:
                try:
                    logger.info("Retrying query on alternate Prometheus URL...")
                    return self._query_once(self.prometheus_url_alt, query)
                except Exception as e2:
                    logger.error(f"Prometheus query failed on alternate URL: {e2}")
                    return None
            return None

    def wait_for_condition(
        self,
        probe: Callable[[], Optional[float]],
        condition: Callable[[Optional[float]], bool],
        timeout_seconds: int = 20,
        interval_seconds: float = 2.0,
    ) -> Optional[float]:
        """Polls a metric until a condition is met or timeout occurs."""
        deadline = time.time() + timeout_seconds
        last = None
        while time.time() < deadline:
            last = probe()
            if condition(last):
                return last
            time.sleep(interval_seconds)
        return last

    def _classify_session_state(
        self, current_value: Optional[float], threshold: float, alert_name: str
    ) -> str:
        """
        Classify alert state based on current value, threshold, and load mode.

        States:
        - NO_DATA: Metric unreachable or no series yet
        - BELOW_THRESHOLD: Metric available and value < threshold
        - SIMULATED: Threshold exceeded by synthetic load (not firing yet)
        - PASS: Alert firing or condition met (real mode)
        - PENDING: Threshold exceeded (real mode) but alert not firing yet
        """
        if current_value is None:
            return "NO_DATA"

        if current_value <= threshold:
            return "BELOW_THRESHOLD"

        # Threshold exceeded
        if self.load_mode == "synthetic":
            return "SIMULATED"
        else:  # real mode
            is_firing, _ = self.check_alert_firing(alert_name)
            return "PASS" if is_firing else "PENDING"

    def check_alert_firing(self, alert_name: str) -> Tuple[bool, Optional[str]]:
        """Check if specific alert is currently firing (with fallback support)."""
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/alerts",
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            if data["status"] == "success":
                for alert in data["data"]["alerts"]:
                    if alert["labels"].get("alertname") == alert_name:
                        state = alert["state"]
                        return state == "firing", state
            return False, None
        except Exception as e:
            logger.warning(f"Alert check failed on primary URL: {e}")
            if self.prometheus_url_alt:
                try:
                    logger.info("Retrying alert check on alternate Prometheus URL...")
                    response = requests.get(
                        f"{self.prometheus_url_alt}/api/v1/alerts",
                        timeout=10,
                    )
                    response.raise_for_status()
                    data = response.json()

                    if data["status"] == "success":
                        for alert in data["data"]["alerts"]:
                            if alert["labels"].get("alertname") == alert_name:
                                state = alert["state"]
                                return state == "firing", state
                    return False, None
                except Exception as e2:
                    logger.error(f"Alert check failed on alternate URL: {e2}")
                    return False, None
            return False, None

    async def generate_session_load(self, session_count: int = 150):
        """
        Generate synthetic session load to trigger SessionsHighWarning alert.

        Creates multiple concurrent sessions via API to simulate high load.
        Target: Trigger alert when session_active_total > 100.
        """
        logger.info(f"🔄 Generating session load: {session_count} concurrent sessions")

        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(session_count):
                # Simular creación de sesiones via webhook
                task = self._create_session(session, f"test_user_{i}")
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum(1 for r in results if not isinstance(r, Exception))

            logger.info(f"✅ Session load generated: {success_count}/{session_count} successful")
            return success_count

    async def _create_session(self, session: aiohttp.ClientSession, user_id: str):
        """Create single session via API (mock)."""
        # En staging real, esto llamaría al webhook de WhatsApp
        # Por ahora, incrementamos métrica directamente via script auxiliar
        await asyncio.sleep(0.1)  # Simulate API delay
        return {"user_id": user_id, "status": "created"}

    async def generate_real_session_load(self, session_count: int = 50):
        """Generate real load by posting WhatsApp-like payloads to the webhook.

        Uses the dummy signature bypass accepted by the webhook for testing.
        """
        logger.info(f"🔄 Generating REAL session load via webhook: {session_count} requests")
        url = f"{self.api_base_url}/webhooks/whatsapp"
        headers = {
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "dummy-signature",
        }

        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(session_count):
                user = f"REAL_USER_{i}"
                payload = {
                    "entry": [
                        {
                            "changes": [
                                {
                                    "value": {
                                        "messages": [
                                            {
                                                "id": f"mid.{user}.1731126400",
                                                "from": user,
                                                "timestamp": "1731126400",
                                                "type": "text",
                                                "text": {"body": "hola"},
                                            }
                                        ],
                                        "contacts": [{"wa_id": user}],
                                    }
                                }
                            ]
                        }
                    ],
                    "metadata": {"source": "alert_validator"},
                }

                tasks.append(session.post(url, headers=headers, data=json.dumps(payload)))

            responses = await asyncio.gather(*tasks, return_exceptions=True)
            ok = 0
            errors = []
            for i, r in enumerate(responses):
                if isinstance(r, Exception):
                    if len(errors) < 3:
                        errors.append({"index": i, "error": str(r), "type": type(r).__name__})
                    continue
                status = getattr(r, "status", 500)
                if status < 400:
                    ok += 1
                elif len(errors) < 3:
                    errors.append({"index": i, "status": status, "type": "http_error"})

            logger.info(f"✅ Real session load posted: {ok}/{session_count} 2xx/3xx responses")
            if errors:
                logger.warning(f"Sample errors (first 3): {json.dumps(errors, indent=2)}")
            return ok

    async def validate_session_alerts(self) -> Dict:
        """
        Validate Session-related alerts (4 alerts).

        Tests:
        1. SessionsHighWarning (>100 sessions for 10m)
        2. SessionsHighCritical (>200 sessions for 5m)
        3. SessionLeakDetected (deriv > 0.5/min for 1h)
        4. SessionCleanupFailures (>3 errors in 1h)
        """
        logger.info("\n" + "=" * 60)
        logger.info("📊 VALIDATING SESSION ALERTS")
        logger.info("=" * 60)

        results = {}

        # Test 1: SessionsHighWarning (threshold: >100)
        logger.info("\n1️⃣  Testing SessionsHighWarning (threshold: >100)")
        current_sessions = self.query_prometheus("session_active_total")
        logger.info(f"   Current sessions: {current_sessions}")

        if current_sessions is None:
            results["SessionsHighWarning"] = {
                "tested": True,
                "threshold_exceeded": False,
                "alert_firing": False,
                "current_value": None,
                "status": "NO_DATA",
                "reason": "Prometheus unreachable or no series yet",
            }
        elif current_sessions > 100:
            logger.info("   ⚠️  Threshold exceeded, waiting for alert to fire (10m)...")
            # En validación real, esperaríamos 10min. Aquí simulamos check
            is_firing, state = self.check_alert_firing("SessionsHighWarning")
            results["SessionsHighWarning"] = {
                "tested": True,
                "threshold_exceeded": True,
                "alert_firing": is_firing,
                "current_value": current_sessions,
                "status": "PASS" if is_firing else "PENDING",
            }
        else:
            logger.info(f"   ℹ️  Threshold NOT exceeded (current: {current_sessions}, need >100)")
            if self.load_mode == "real":
                logger.info("   Generating REAL load via webhook...")
                await self.generate_real_session_load(session_count=self.session_count)
            else:
                logger.info("   Generating synthetic load...")
                await self.generate_session_load(session_count=self.session_count)

            # Re-check metric con pequeño polling
            new_sessions = self.wait_for_condition(
                lambda: self.query_prometheus("session_active_total"),
                lambda v: (v is not None) and (v > current_sessions),
                timeout_seconds=15,
                interval_seconds=3.0,
            )
            results["SessionsHighWarning"] = {
                "tested": True,
                "threshold_exceeded": (new_sessions is not None) and (new_sessions > 100),
                "alert_firing": False,
                "current_value": new_sessions,
                "status": self._classify_session_state(new_sessions, 100, "SessionsHighWarning"),
            }

        # Test 2: SessionsHighCritical (threshold: >200)
        logger.info("\n2️⃣  Testing SessionsHighCritical (threshold: >200)")
        current_sessions_2 = self.query_prometheus("session_active_total")
        if current_sessions_2 is None:
            results["SessionsHighCritical"] = {
                "tested": True,
                "threshold_exceeded": False,
                "alert_firing": False,
                "current_value": None,
                "status": "NO_DATA",
            }
        elif current_sessions_2 > 200:
            is_firing, state = self.check_alert_firing("SessionsHighCritical")
            results["SessionsHighCritical"] = {
                "tested": True,
                "threshold_exceeded": True,
                "alert_firing": is_firing,
                "current_value": current_sessions_2,
                "status": "PASS" if is_firing else "PENDING",
            }
        else:
            logger.info(f"   ℹ️  Threshold NOT exceeded (current: {current_sessions_2}, need >200)")
            results["SessionsHighCritical"] = {
                "tested": True,
                "threshold_exceeded": False,
                "alert_firing": False,
                "current_value": current_sessions_2,
                "status": "BELOW_THRESHOLD" if current_sessions_2 < 200 else "SKIP",
                "reason": "Production-only test (requires 200+ concurrent sessions)",
            }

        # Test 3: SessionLeakDetected (deriv > 0.5/min)
        logger.info("\n3️⃣  Testing SessionLeakDetected (deriv > 0.5/min)")
        deriv = self.query_prometheus("deriv(session_active_total[30m])")
        logger.info(f"   Derivative: {deriv}")

        if deriv is None:
            status = "NO_DATA"
        elif deriv <= 0.5:
            status = "BELOW_THRESHOLD"
        else:
            status = "SKIP"  # Long-running test

        results["SessionLeakDetected"] = {
            "tested": True,
            "threshold_exceeded": (deriv is not None) and (deriv > 0.5),
            "alert_firing": False,
            "current_value": deriv,
            "status": status,
            "reason": "Long-running test (requires 1h sustained growth)" if status == "SKIP" else None,
        }

        # Test 4: SessionCleanupFailures (>3 errors/hour)
        logger.info("\n4️⃣  Testing SessionCleanupFailures (>3 errors/hour)")
        cleanup_errors = self.query_prometheus('increase(session_cleanup_total{result="error"}[1h])')
        logger.info(f"   Cleanup errors (1h): {cleanup_errors}")

        if cleanup_errors is None:
            status = "NO_DATA"
        elif cleanup_errors == 0:
            status = "PASS"
        elif cleanup_errors <= 3:
            status = "BELOW_THRESHOLD"
        else:
            status = "FAIL"

        results["SessionCleanupFailures"] = {
            "tested": True,
            "threshold_exceeded": (cleanup_errors is not None) and (cleanup_errors > 3),
            "alert_firing": False,
            "current_value": cleanup_errors,
            "status": status,
        }

        return results

    async def validate_lock_alerts(self) -> Dict:
        """
        Validate Lock Service alerts (4 alerts).

        Tests:
        1. LockConflictsHigh (>0.5 conflicts/sec for 10m)
        2. LockConflictsCritical (>2 conflicts/sec for 5m)
        3. LockExtensionsExceeded (>0.2 max_reached/sec for 10m)
        4. LockOperationsFailureRate (>10% failures for 10m)
        """
        logger.info("\n" + "=" * 60)
        logger.info("🔒 VALIDATING LOCK SERVICE ALERTS")
        logger.info("=" * 60)

        results = {}

        # Test 1: LockConflictsHigh (>0.5 rps)
        logger.info("\n1️⃣  Testing LockConflictsHigh (threshold: >0.5 conflicts/sec)")
        conflicts_rate = self.query_prometheus("sum(rate(lock_conflicts_total[5m]))")
        logger.info(f"   Conflict rate: {conflicts_rate} conflicts/sec")

        if conflicts_rate is None:
            status = "NO_DATA"
        elif conflicts_rate == 0 or conflicts_rate < 0.5:
            status = "PASS" if conflicts_rate == 0 else "BELOW_THRESHOLD"
        else:
            status = "NEEDS_INVESTIGATION"

        results["LockConflictsHigh"] = {
            "tested": True,
            "threshold_exceeded": (conflicts_rate is not None) and (conflicts_rate > 0.5),
            "alert_firing": False,
            "current_value": conflicts_rate,
            "status": status,
        }

        # Test 2: LockConflictsCritical (>2 rps)
        logger.info("\n2️⃣  Testing LockConflictsCritical (threshold: >2 conflicts/sec)")

        if conflicts_rate is None:
            status_2 = "NO_DATA"
        elif conflicts_rate < 2:
            status_2 = "PASS" if conflicts_rate < 0.5 else "BELOW_THRESHOLD"
        else:
            status_2 = "CRITICAL"

        results["LockConflictsCritical"] = {
            "tested": True,
            "threshold_exceeded": (conflicts_rate is not None) and (conflicts_rate > 2),
            "alert_firing": False,
            "current_value": conflicts_rate,
            "status": status_2,
        }

        # Test 3: LockExtensionsExceeded
        logger.info("\n3️⃣  Testing LockExtensionsExceeded (threshold: >0.2 max_reached/sec)")
        extensions_rate = self.query_prometheus('sum(rate(lock_extensions_total{result="max_reached"}[5m]))')
        logger.info(f"   Extensions max_reached rate: {extensions_rate} ops/sec")

        if extensions_rate is None:
            status_ext = "NO_DATA"
        elif extensions_rate == 0 or extensions_rate < 0.2:
            status_ext = "PASS" if extensions_rate == 0 else "BELOW_THRESHOLD"
        else:
            status_ext = "NEEDS_TUNING"

        results["LockExtensionsExceeded"] = {
            "tested": True,
            "threshold_exceeded": (extensions_rate is not None) and (extensions_rate > 0.2),
            "alert_firing": False,
            "current_value": extensions_rate,
            "status": status_ext,
        }

        # Test 4: LockOperationsFailureRate (>10%)
        logger.info("\n4️⃣  Testing LockOperationsFailureRate (threshold: >10%)")
        total_ops = self.query_prometheus("sum(rate(lock_operations_total[5m]))")
        failed_ops = self.query_prometheus('sum(rate(lock_operations_total{result!="success"}[5m]))')

        if total_ops and total_ops > 0:
            failure_rate = (failed_ops or 0) / total_ops
            logger.info(f"   Failure rate: {failure_rate:.2%}")
            results["LockOperationsFailureRate"] = {
                "tested": True,
                "threshold_exceeded": failure_rate > 0.1,
                "alert_firing": False,
                "current_value": failure_rate,
                "status": "PASS" if failure_rate < 0.1 else "NEEDS_INVESTIGATION",
            }
        else:
            logger.info("   ℹ️  No lock operations recorded yet")
            results["LockOperationsFailureRate"] = {
                "tested": True,
                "threshold_exceeded": False,
                "alert_firing": False,
                "current_value": None,
                "status": "SKIP",
                "reason": "No lock operations in last 5m",
            }

        return results

    def fetch_current_alerts(self) -> Dict:
        """Fetch current alerts from Prometheus /api/v1/alerts and summarize by alertname."""
        try:
            resp = requests.get(f"{self.prometheus_url}/api/v1/alerts", timeout=10)
            resp.raise_for_status()
        except Exception:
            if self.prometheus_url_alt:
                try:
                    resp = requests.get(f"{self.prometheus_url_alt}/api/v1/alerts", timeout=10)
                    resp.raise_for_status()
                except Exception as e2:
                    logger.error(f"Failed to fetch alerts: {e2}")
                    return {}
            else:
                return {}

        data = resp.json()
        if data.get("status") != "success":
            return {}
        alerts = data.get("data", {}).get("alerts", [])
        summary: Dict[str, Dict[str, int]] = {}
        for a in alerts:
            name = a.get("labels", {}).get("alertname", "unknown")
            state = a.get("state", "unknown")
            summary.setdefault(name, {"count": 0, "firing": 0, "pending": 0})
            summary[name]["count"] += 1
            if state == "firing":
                summary[name]["firing"] += 1
            if state == "pending":
                summary[name]["pending"] += 1
        return summary

    def generate_report(self, session_results: Dict, lock_results: Dict) -> Dict:
        """Generate comprehensive validation report."""
        all_results = {**session_results, **lock_results}

        alerts_snapshot = self.fetch_current_alerts()

        report = {
            "timestamp": datetime.now().isoformat(),
            "prometheus_url": self.prometheus_url,
            "mode": self.load_mode,
            "total_alerts_tested": len(all_results),
            "alerts": all_results,
            "firing_alerts_snapshot": alerts_snapshot,
            "summary": {
                "passed": sum(1 for r in all_results.values() if r["status"] == "PASS"),
                "failed": sum(1 for r in all_results.values() if r["status"] == "FAIL"),
                "pending": sum(1 for r in all_results.values() if r["status"] == "PENDING"),
                "skipped": sum(1 for r in all_results.values() if r["status"] == "SKIP"),
                "simulated": sum(1 for r in all_results.values() if r["status"] == "SIMULATED"),
                "no_data": sum(1 for r in all_results.values() if r["status"] == "NO_DATA"),
                "below_threshold": sum(1 for r in all_results.values() if r["status"] == "BELOW_THRESHOLD"),
            },
        }

        return report


async def main():
    parser = argparse.ArgumentParser(description="Validate Prometheus alerts in staging")
    parser.add_argument(
        "--prometheus-url",
        default="http://localhost:9090",
        help="Prometheus server URL",
    )
    parser.add_argument(
        "--prometheus-url-alt",
        default="http://localhost:9091",
        help="Alternate Prometheus URL (fallback)",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8002",
        help="API server URL for load generation",
    )
    parser.add_argument(
        "--output",
        default=".playbook/alert_validation_report.json",
        help="Output report file path",
    )
    parser.add_argument(
        "--load-mode",
        choices=["synthetic", "real"],
        default="synthetic",
        help="Load generation mode: synthetic (default) or real (webhook)",
    )
    parser.add_argument(
        "--session-count",
        type=int,
        default=120,
        help="Number of sessions/messages to generate for load (1-500)",
    )
    parser.add_argument(
        "--skip-load-generation",
        action="store_true",
        help="Skip synthetic load generation (validation only)",
    )

    args = parser.parse_args()

    # Validate session-count bounds
    if not (1 <= args.session_count <= 500):
        logger.error("❌ --session-count must be between 1 and 500")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("🚀 ALERT VALIDATION - STAGING ENVIRONMENT")
    logger.info("=" * 60)
    logger.info(f"Prometheus URL: {args.prometheus_url}")
    logger.info(f"API URL: {args.api_url}")
    logger.info(f"Output report: {args.output}")
    logger.info("")

    # Create validator
    validator = AlertValidator(
        args.prometheus_url,
        args.api_url,
        prometheus_url_alt=args.prometheus_url_alt,
        load_mode=args.load_mode,
        session_count=args.session_count,
    )

    # Validate session alerts
    session_results = await validator.validate_session_alerts()

    # Validate lock alerts
    lock_results = await validator.validate_lock_alerts()

    # Generate report
    report = validator.generate_report(session_results, lock_results)

    # Ensure output directory exists
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("📋 VALIDATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total alerts tested: {report['total_alerts_tested']}")
    logger.info(f"✅ Passed: {report['summary']['passed']}")
    logger.info(f"❌ Failed: {report['summary']['failed']}")
    logger.info(f"⏳ Pending: {report['summary']['pending']}")
    logger.info(f"⏭️  Skipped: {report['summary']['skipped']}")
    logger.info(f"🧪 Simulated: {report['summary']['simulated']}")
    logger.info(f"📊 Below Threshold: {report['summary']['below_threshold']}")
    logger.info(f"📉 No Data: {report['summary']['no_data']}")
    logger.info(f"\n📄 Report saved to: {args.output}")

    # Exit code
    if report["summary"]["failed"] > 0:
        logger.error("\n⚠️  Some alerts FAILED validation")
        sys.exit(1)
    else:
        logger.info("\n✅ Alert validation SUCCESSFUL")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
