#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════
Performance Validation Script - Agente Hotelero IA System
═══════════════════════════════════════════════════════════════════════════

Validates k6 performance test results against defined SLOs and generates
comprehensive analysis reports.

Features:
---------
- Load and parse k6 JSON output
- Validate against SLO thresholds
- Calculate P50, P95, P99 latencies
- Error rate analysis
- Throughput analysis
- Generate HTML and Markdown reports
- Trend comparison with baseline
- Exit codes for CI/CD integration

SLO Targets:
------------
- P95 Latency: < 3000ms
- Error Rate: < 1%
- Throughput: > 10 RPS
- Check Pass Rate: > 99%

Usage:
------
# Validate latest results
python3 tests/load/validate_performance.py

# Validate specific results file
python3 tests/load/validate_performance.py --results .performance/results-smoke-*.json

# Compare with baseline
python3 tests/load/validate_performance.py --baseline .performance/baseline.json

# Generate HTML report
python3 tests/load/validate_performance.py --format html --output report.html

# CI/CD mode (exit codes only)
python3 tests/load/validate_performance.py --ci-mode

Exit Codes:
-----------
0: All SLOs passed
1: One or more SLOs failed (warnings)
2: Critical SLO failures (deployment blocker)

@version 1.0.0
@since P015
@author AI Agent
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
import glob


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS AND CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

class SLOStatus(Enum):
    """SLO compliance status"""
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    CRITICAL = "CRITICAL"


class SLOLevel(Enum):
    """SLO severity level"""
    P0 = "P0"  # Critical - deployment blocker
    P1 = "P1"  # High - requires immediate attention
    P2 = "P2"  # Medium - should be addressed soon
    P3 = "P3"  # Low - nice to have


# SLO Thresholds
SLO_THRESHOLDS = {
    "p95_latency_ms": {
        "target": 3000,
        "warning": 2500,
        "level": SLOLevel.P0,
        "description": "95th percentile response time must be under 3 seconds"
    },
    "p99_latency_ms": {
        "target": 5000,
        "warning": 4000,
        "level": SLOLevel.P1,
        "description": "99th percentile response time must be under 5 seconds"
    },
    "error_rate_percent": {
        "target": 1.0,
        "warning": 0.5,
        "level": SLOLevel.P0,
        "description": "Error rate must be below 1%"
    },
    "throughput_rps": {
        "target": 10.0,
        "warning": 15.0,
        "level": SLOLevel.P2,
        "description": "Minimum throughput of 10 requests per second"
    },
    "check_pass_rate_percent": {
        "target": 99.0,
        "warning": 99.5,
        "level": SLOLevel.P1,
        "description": "Check pass rate must be above 99%"
    },
    "http_req_duration_avg_ms": {
        "target": 1500,
        "warning": 1000,
        "level": SLOLevel.P2,
        "description": "Average response time should be under 1.5 seconds"
    }
}

# Metrics to extract from k6 results
REQUIRED_METRICS = [
    "http_req_duration",
    "http_req_failed",
    "http_reqs",
    "checks",
    "errors",
    "success"
]


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class LatencyMetrics:
    """Latency statistics"""
    min_ms: float
    max_ms: float
    avg_ms: float
    median_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float


@dataclass
class ThroughputMetrics:
    """Throughput statistics"""
    total_requests: int
    duration_seconds: float
    requests_per_second: float
    successful_requests: int
    failed_requests: int


@dataclass
class ErrorMetrics:
    """Error statistics"""
    total_errors: int
    error_rate_percent: float
    error_types: Dict[str, int]


@dataclass
class CheckMetrics:
    """Check validation statistics"""
    total_checks: int
    passed_checks: int
    failed_checks: int
    pass_rate_percent: float


@dataclass
class SLOResult:
    """Single SLO validation result"""
    name: str
    description: str
    measured_value: float
    target_value: float
    warning_value: float
    status: SLOStatus
    level: SLOLevel
    pass_fail: bool
    deviation_percent: float


@dataclass
class ValidationReport:
    """Complete validation report"""
    test_name: str
    scenario: str
    timestamp: str
    duration_seconds: float
    
    latency: LatencyMetrics
    throughput: ThroughputMetrics
    errors: ErrorMetrics
    checks: CheckMetrics
    
    slo_results: List[SLOResult]
    overall_status: SLOStatus
    overall_pass: bool
    
    recommendations: List[str]
    warnings: List[str]
    critical_issues: List[str]


# ═══════════════════════════════════════════════════════════════════════════
# K6 RESULTS PARSER
# ═══════════════════════════════════════════════════════════════════════════

class K6ResultsParser:
    """Parse k6 JSON output and extract metrics"""
    
    def __init__(self, results_file: Path):
        self.results_file = results_file
        self.data = self._load_results()
    
    def _load_results(self) -> Dict[str, Any]:
        """Load k6 results JSON file"""
        try:
            with open(self.results_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ Results file not found: {self.results_file}")
            sys.exit(2)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in results file: {e}")
            sys.exit(2)
    
    def get_metric(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Get specific metric from results"""
        metrics = self.data.get('metrics', {})
        return metrics.get(metric_name)
    
    def get_latency_metrics(self) -> LatencyMetrics:
        """Extract latency metrics"""
        duration_metric = self.get_metric('http_req_duration')
        if not duration_metric:
            print("⚠️  Warning: http_req_duration metric not found")
            return LatencyMetrics(0, 0, 0, 0, 0, 0, 0)
        
        values = duration_metric.get('values', {})
        
        return LatencyMetrics(
            min_ms=values.get('min', 0),
            max_ms=values.get('max', 0),
            avg_ms=values.get('avg', 0),
            median_ms=values.get('med', 0),
            p90_ms=values.get('p(90)', 0),
            p95_ms=values.get('p(95)', 0),
            p99_ms=values.get('p(99)', 0)
        )
    
    def get_throughput_metrics(self) -> ThroughputMetrics:
        """Extract throughput metrics"""
        reqs_metric = self.get_metric('http_reqs')
        if not reqs_metric:
            return ThroughputMetrics(0, 0, 0, 0, 0)
        
        values = reqs_metric.get('values', {})
        total_requests = int(values.get('count', 0))
        rate = values.get('rate', 0)
        
        # Calculate duration from state if available
        state = self.data.get('state', {})
        test_run_duration = state.get('testRunDurationMs', 0) / 1000.0
        
        # Get success/failure counts
        failed_metric = self.get_metric('http_req_failed')
        failed_requests = 0
        if failed_metric:
            failed_requests = int(failed_metric.get('values', {}).get('passes', 0))
        
        successful_requests = total_requests - failed_requests
        
        return ThroughputMetrics(
            total_requests=total_requests,
            duration_seconds=test_run_duration,
            requests_per_second=rate,
            successful_requests=successful_requests,
            failed_requests=failed_requests
        )
    
    def get_error_metrics(self) -> ErrorMetrics:
        """Extract error metrics"""
        errors_metric = self.get_metric('errors')
        failed_metric = self.get_metric('http_req_failed')
        
        total_errors = 0
        if errors_metric:
            total_errors = int(errors_metric.get('values', {}).get('count', 0))
        
        error_rate = 0.0
        if failed_metric:
            values = failed_metric.get('values', {})
            error_rate = values.get('rate', 0) * 100  # Convert to percentage
        
        return ErrorMetrics(
            total_errors=total_errors,
            error_rate_percent=error_rate,
            error_types={}  # k6 doesn't provide detailed error types in summary
        )
    
    def get_check_metrics(self) -> CheckMetrics:
        """Extract check validation metrics"""
        checks_metric = self.get_metric('checks')
        if not checks_metric:
            return CheckMetrics(0, 0, 0, 0.0)
        
        values = checks_metric.get('values', {})
        total = int(values.get('count', 0))
        passed = int(values.get('passes', 0))
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0.0
        
        return CheckMetrics(
            total_checks=total,
            passed_checks=passed,
            failed_checks=failed,
            pass_rate_percent=pass_rate
        )
    
    def get_scenario(self) -> str:
        """Extract scenario name from results"""
        # Try to get from options or tags
        options = self.data.get('options', {})
        scenarios = options.get('scenarios', {})
        if scenarios:
            return list(scenarios.keys())[0]
        return "unknown"
    
    def get_test_duration(self) -> float:
        """Get test duration in seconds"""
        state = self.data.get('state', {})
        return state.get('testRunDurationMs', 0) / 1000.0


# ═══════════════════════════════════════════════════════════════════════════
# SLO VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════

class SLOValidator:
    """Validate metrics against SLO thresholds"""
    
    def __init__(self, parser: K6ResultsParser):
        self.parser = parser
        self.latency = parser.get_latency_metrics()
        self.throughput = parser.get_throughput_metrics()
        self.errors = parser.get_error_metrics()
        self.checks = parser.get_check_metrics()
    
    def validate_slo(self, name: str, measured_value: float, is_greater_better: bool = False) -> SLOResult:
        """Validate a single SLO"""
        slo_config = SLO_THRESHOLDS[name]
        target = slo_config['target']
        warning = slo_config['warning']
        level = slo_config['level']
        description = slo_config['description']
        
        # Determine status based on direction (lower is better vs higher is better)
        if is_greater_better:
            # For metrics like throughput where higher is better
            if measured_value >= warning:
                status = SLOStatus.PASS
                pass_fail = True
            elif measured_value >= target:
                status = SLOStatus.WARNING
                pass_fail = True
            else:
                status = SLOStatus.CRITICAL if level == SLOLevel.P0 else SLOStatus.FAIL
                pass_fail = False
        else:
            # For metrics like latency/errors where lower is better
            if measured_value <= warning:
                status = SLOStatus.PASS
                pass_fail = True
            elif measured_value <= target:
                status = SLOStatus.WARNING
                pass_fail = True
            else:
                status = SLOStatus.CRITICAL if level == SLOLevel.P0 else SLOStatus.FAIL
                pass_fail = False
        
        # Calculate deviation
        if is_greater_better:
            deviation = ((measured_value - target) / target * 100) if target > 0 else 0
        else:
            deviation = ((measured_value - target) / target * 100) if target > 0 else 0
        
        return SLOResult(
            name=name,
            description=description,
            measured_value=measured_value,
            target_value=target,
            warning_value=warning,
            status=status,
            level=level,
            pass_fail=pass_fail,
            deviation_percent=deviation
        )
    
    def validate_all(self) -> List[SLOResult]:
        """Validate all SLOs"""
        results = []
        
        # P95 Latency
        results.append(self.validate_slo(
            "p95_latency_ms",
            self.latency.p95_ms,
            is_greater_better=False
        ))
        
        # P99 Latency
        results.append(self.validate_slo(
            "p99_latency_ms",
            self.latency.p99_ms,
            is_greater_better=False
        ))
        
        # Error Rate
        results.append(self.validate_slo(
            "error_rate_percent",
            self.errors.error_rate_percent,
            is_greater_better=False
        ))
        
        # Throughput
        results.append(self.validate_slo(
            "throughput_rps",
            self.throughput.requests_per_second,
            is_greater_better=True
        ))
        
        # Check Pass Rate
        results.append(self.validate_slo(
            "check_pass_rate_percent",
            self.checks.pass_rate_percent,
            is_greater_better=True
        ))
        
        # Average Latency
        results.append(self.validate_slo(
            "http_req_duration_avg_ms",
            self.latency.avg_ms,
            is_greater_better=False
        ))
        
        return results
    
    def get_overall_status(self, slo_results: List[SLOResult]) -> Tuple[SLOStatus, bool]:
        """Determine overall status from individual SLO results"""
        has_critical = any(r.status == SLOStatus.CRITICAL for r in slo_results)
        has_fail = any(r.status == SLOStatus.FAIL for r in slo_results)
        has_warning = any(r.status == SLOStatus.WARNING for r in slo_results)
        
        if has_critical:
            return SLOStatus.CRITICAL, False
        elif has_fail:
            return SLOStatus.FAIL, False
        elif has_warning:
            return SLOStatus.WARNING, True
        else:
            return SLOStatus.PASS, True
    
    def generate_recommendations(self, slo_results: List[SLOResult]) -> List[str]:
        """Generate recommendations based on results"""
        recommendations = []
        
        for result in slo_results:
            if not result.pass_fail:
                if "latency" in result.name:
                    recommendations.append(
                        f"🔧 {result.name}: Consider implementing caching, optimizing database queries, or scaling horizontally"
                    )
                elif "error" in result.name:
                    recommendations.append(
                        f"🔧 {result.name}: Investigate error logs, check circuit breaker status, verify external service health"
                    )
                elif "throughput" in result.name:
                    recommendations.append(
                        f"🔧 {result.name}: Increase worker processes, optimize async operations, consider load balancing"
                    )
                elif "check" in result.name:
                    recommendations.append(
                        f"🔧 {result.name}: Review failed checks in k6 output, validate API contracts, check data quality"
                    )
        
        return recommendations
    
    def generate_warnings(self, slo_results: List[SLOResult]) -> List[str]:
        """Generate warnings for SLOs in warning state"""
        warnings = []
        
        for result in slo_results:
            if result.status == SLOStatus.WARNING:
                warnings.append(
                    f"⚠️  {result.name}: {result.measured_value:.2f} (target: {result.target_value}, warning: {result.warning_value})"
                )
        
        return warnings
    
    def generate_critical_issues(self, slo_results: List[SLOResult]) -> List[str]:
        """Generate critical issues list"""
        critical = []
        
        for result in slo_results:
            if result.status == SLOStatus.CRITICAL:
                critical.append(
                    f"🚨 {result.name}: {result.measured_value:.2f} exceeds threshold {result.target_value} (Level: {result.level.value})"
                )
        
        return critical


# ═══════════════════════════════════════════════════════════════════════════
# REPORT GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

class ReportGenerator:
    """Generate validation reports in various formats"""
    
    def __init__(self, report: ValidationReport):
        self.report = report
    
    def generate_console_report(self) -> str:
        """Generate console-friendly report"""
        lines = []
        
        lines.append("═" * 80)
        lines.append("📊 PERFORMANCE VALIDATION REPORT")
        lines.append("═" * 80)
        lines.append(f"Test: {self.report.test_name}")
        lines.append(f"Scenario: {self.report.scenario.upper()}")
        lines.append(f"Timestamp: {self.report.timestamp}")
        lines.append(f"Duration: {self.report.duration_seconds:.2f}s")
        lines.append("═" * 80)
        
        # Latency Section
        lines.append("\n📈 LATENCY METRICS")
        lines.append("─" * 80)
        lat = self.report.latency
        lines.append(f"Min:     {lat.min_ms:>10.2f} ms")
        lines.append(f"Avg:     {lat.avg_ms:>10.2f} ms")
        lines.append(f"Median:  {lat.median_ms:>10.2f} ms")
        lines.append(f"P90:     {lat.p90_ms:>10.2f} ms")
        lines.append(f"P95:     {lat.p95_ms:>10.2f} ms")
        lines.append(f"P99:     {lat.p99_ms:>10.2f} ms")
        lines.append(f"Max:     {lat.max_ms:>10.2f} ms")
        
        # Throughput Section
        lines.append("\n🚀 THROUGHPUT METRICS")
        lines.append("─" * 80)
        thr = self.report.throughput
        lines.append(f"Total Requests:      {thr.total_requests:>10}")
        lines.append(f"Successful:          {thr.successful_requests:>10}")
        lines.append(f"Failed:              {thr.failed_requests:>10}")
        lines.append(f"Requests/sec:        {thr.requests_per_second:>10.2f}")
        
        # Error Section
        lines.append("\n❌ ERROR METRICS")
        lines.append("─" * 80)
        err = self.report.errors
        lines.append(f"Total Errors:        {err.total_errors:>10}")
        lines.append(f"Error Rate:          {err.error_rate_percent:>9.2f}%")
        
        # Check Section
        lines.append("\n✅ CHECK METRICS")
        lines.append("─" * 80)
        chk = self.report.checks
        lines.append(f"Total Checks:        {chk.total_checks:>10}")
        lines.append(f"Passed:              {chk.passed_checks:>10}")
        lines.append(f"Failed:              {chk.failed_checks:>10}")
        lines.append(f"Pass Rate:           {chk.pass_rate_percent:>9.2f}%")
        
        # SLO Results
        lines.append("\n🎯 SLO VALIDATION RESULTS")
        lines.append("═" * 80)
        for slo in self.report.slo_results:
            status_icon = {
                SLOStatus.PASS: "✅",
                SLOStatus.WARNING: "⚠️ ",
                SLOStatus.FAIL: "❌",
                SLOStatus.CRITICAL: "🚨"
            }.get(slo.status, "❓")
            
            lines.append(f"\n{status_icon} {slo.name.upper()}")
            lines.append(f"   Description: {slo.description}")
            lines.append(f"   Measured:    {slo.measured_value:.2f}")
            lines.append(f"   Target:      {slo.target_value:.2f}")
            lines.append(f"   Warning:     {slo.warning_value:.2f}")
            lines.append(f"   Status:      {slo.status.value} ({slo.level.value})")
            lines.append(f"   Deviation:   {slo.deviation_percent:+.2f}%")
        
        # Overall Status
        lines.append("\n" + "═" * 80)
        lines.append("🏁 OVERALL STATUS")
        lines.append("═" * 80)
        status_icon = "✅" if self.report.overall_pass else "❌"
        lines.append(f"{status_icon} {self.report.overall_status.value}")
        
        # Critical Issues
        if self.report.critical_issues:
            lines.append("\n🚨 CRITICAL ISSUES")
            lines.append("─" * 80)
            for issue in self.report.critical_issues:
                lines.append(f"  {issue}")
        
        # Warnings
        if self.report.warnings:
            lines.append("\n⚠️  WARNINGS")
            lines.append("─" * 80)
            for warning in self.report.warnings:
                lines.append(f"  {warning}")
        
        # Recommendations
        if self.report.recommendations:
            lines.append("\n💡 RECOMMENDATIONS")
            lines.append("─" * 80)
            for rec in self.report.recommendations:
                lines.append(f"  {rec}")
        
        lines.append("\n" + "═" * 80)
        
        return "\n".join(lines)
    
    def generate_markdown_report(self) -> str:
        """Generate Markdown report"""
        lines = []
        
        lines.append("# Performance Validation Report\n")
        lines.append(f"**Test:** {self.report.test_name}  ")
        lines.append(f"**Scenario:** {self.report.scenario.upper()}  ")
        lines.append(f"**Timestamp:** {self.report.timestamp}  ")
        lines.append(f"**Duration:** {self.report.duration_seconds:.2f}s\n")
        
        # Overall Status
        status_badge = "![PASS](https://img.shields.io/badge/Status-PASS-success)" if self.report.overall_pass else "![FAIL](https://img.shields.io/badge/Status-FAIL-critical)"
        lines.append(f"## Overall Status: {status_badge}\n")
        
        # Metrics Tables
        lines.append("## 📊 Performance Metrics\n")
        
        lines.append("### Latency\n")
        lines.append("| Metric | Value (ms) |")
        lines.append("|--------|------------|")
        lat = self.report.latency
        lines.append(f"| Min | {lat.min_ms:.2f} |")
        lines.append(f"| Avg | {lat.avg_ms:.2f} |")
        lines.append(f"| Median | {lat.median_ms:.2f} |")
        lines.append(f"| P90 | {lat.p90_ms:.2f} |")
        lines.append(f"| **P95** | **{lat.p95_ms:.2f}** |")
        lines.append(f"| **P99** | **{lat.p99_ms:.2f}** |")
        lines.append(f"| Max | {lat.max_ms:.2f} |\n")
        
        lines.append("### Throughput\n")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        thr = self.report.throughput
        lines.append(f"| Total Requests | {thr.total_requests} |")
        lines.append(f"| Successful | {thr.successful_requests} |")
        lines.append(f"| Failed | {thr.failed_requests} |")
        lines.append(f"| **Requests/sec** | **{thr.requests_per_second:.2f}** |\n")
        
        lines.append("### Errors\n")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        err = self.report.errors
        lines.append(f"| Total Errors | {err.total_errors} |")
        lines.append(f"| **Error Rate** | **{err.error_rate_percent:.2f}%** |\n")
        
        # SLO Results Table
        lines.append("## 🎯 SLO Validation\n")
        lines.append("| SLO | Measured | Target | Status | Level |")
        lines.append("|-----|----------|--------|--------|-------|")
        for slo in self.report.slo_results:
            status_emoji = {
                SLOStatus.PASS: "✅",
                SLOStatus.WARNING: "⚠️",
                SLOStatus.FAIL: "❌",
                SLOStatus.CRITICAL: "🚨"
            }.get(slo.status, "❓")
            lines.append(f"| {slo.name} | {slo.measured_value:.2f} | {slo.target_value:.2f} | {status_emoji} {slo.status.value} | {slo.level.value} |")
        lines.append("")
        
        # Issues and Recommendations
        if self.report.critical_issues:
            lines.append("## 🚨 Critical Issues\n")
            for issue in self.report.critical_issues:
                lines.append(f"- {issue}")
            lines.append("")
        
        if self.report.warnings:
            lines.append("## ⚠️ Warnings\n")
            for warning in self.report.warnings:
                lines.append(f"- {warning}")
            lines.append("")
        
        if self.report.recommendations:
            lines.append("## 💡 Recommendations\n")
            for rec in self.report.recommendations:
                lines.append(f"- {rec}")
            lines.append("")
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════

def find_latest_results(pattern: str = ".performance/results-*.json") -> Optional[Path]:
    """Find the latest results file"""
    files = glob.glob(pattern)
    if not files:
        return None
    # Sort by modification time, newest first
    files.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
    return Path(files[0])


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description="Validate k6 performance test results against SLOs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate latest results
  python3 validate_performance.py
  
  # Validate specific file
  python3 validate_performance.py --results .performance/results-smoke-2025-01-01.json
  
  # Generate markdown report
  python3 validate_performance.py --format markdown --output report.md
  
  # CI/CD mode (minimal output, exit codes only)
  python3 validate_performance.py --ci-mode

Exit Codes:
  0 = All SLOs passed
  1 = One or more SLOs failed (warnings)
  2 = Critical SLO failures (deployment blocker)
        """
    )
    
    parser.add_argument(
        '--results',
        type=str,
        help='Path to k6 results JSON file (default: latest in .performance/)'
    )
    
    parser.add_argument(
        '--format',
        choices=['console', 'markdown', 'json'],
        default='console',
        help='Output format (default: console)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output file path (default: stdout)'
    )
    
    parser.add_argument(
        '--ci-mode',
        action='store_true',
        help='CI/CD mode: minimal output, rely on exit codes'
    )
    
    parser.add_argument(
        '--baseline',
        type=str,
        help='Baseline results file for comparison (future feature)'
    )
    
    args = parser.parse_args()
    
    # Find results file
    if args.results:
        results_file = Path(args.results)
    else:
        results_file = find_latest_results()
        if not results_file:
            print("❌ No results files found in .performance/")
            print("Run k6 tests first: make perf-smoke")
            sys.exit(2)
        
        if not args.ci_mode:
            print(f"📂 Using latest results: {results_file}")
    
    # Parse results
    k6_parser = K6ResultsParser(results_file)
    
    # Validate SLOs
    validator = SLOValidator(k6_parser)
    slo_results = validator.validate_all()
    overall_status, overall_pass = validator.get_overall_status(slo_results)
    
    # Generate recommendations
    recommendations = validator.generate_recommendations(slo_results)
    warnings = validator.generate_warnings(slo_results)
    critical_issues = validator.generate_critical_issues(slo_results)
    
    # Create report
    report = ValidationReport(
        test_name=results_file.stem,
        scenario=k6_parser.get_scenario(),
        timestamp=datetime.now().isoformat(),
        duration_seconds=k6_parser.get_test_duration(),
        latency=k6_parser.get_latency_metrics(),
        throughput=k6_parser.get_throughput_metrics(),
        errors=k6_parser.get_error_metrics(),
        checks=k6_parser.get_check_metrics(),
        slo_results=slo_results,
        overall_status=overall_status,
        overall_pass=overall_pass,
        recommendations=recommendations,
        warnings=warnings,
        critical_issues=critical_issues
    )
    
    # Generate output
    generator = ReportGenerator(report)
    
    if args.format == 'console':
        output_text = generator.generate_console_report()
    elif args.format == 'markdown':
        output_text = generator.generate_markdown_report()
    elif args.format == 'json':
        output_text = json.dumps(asdict(report), indent=2, default=str)
    
    # Write output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_text)
        if not args.ci_mode:
            print(f"✅ Report written to: {args.output}")
    else:
        if not args.ci_mode:
            print(output_text)
    
    # CI mode summary
    if args.ci_mode:
        if overall_pass:
            print(f"✅ PASS: All SLOs met ({overall_status.value})")
        else:
            print(f"❌ FAIL: SLO violations detected ({overall_status.value})")
            if critical_issues:
                print(f"🚨 {len(critical_issues)} critical issue(s)")
    
    # Exit with appropriate code
    if overall_status == SLOStatus.CRITICAL:
        sys.exit(2)
    elif not overall_pass:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
