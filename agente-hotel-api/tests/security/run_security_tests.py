"""
Security Test Runner and Report Generator
Comprehensive security test execution and reporting
"""

import subprocess
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import argparse


class SecurityTestRunner:
    """Security test runner with comprehensive reporting"""

    def __init__(self, test_directory="tests/security"):
        self.test_directory = Path(test_directory)
        self.results = {}
        self.report_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "test_suites": {},
            "summary": {},
            "security_findings": [],
            "recommendations": [],
        }

    def run_test_suite(self, test_file, verbose=False):
        """Run a specific test suite"""
        print(f"\n🔒 Running security tests: {test_file}")

        cmd = [
            "python",
            "-m",
            "pytest",
            str(self.test_directory / test_file),
            "-v" if verbose else "-q",
            "--tb=short",
            "--json-report",
            f"--json-report-file=.reports/{test_file}_report.json",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)

            # Parse JSON report if available
            report_file = Path(f".reports/{test_file}_report.json")
            if report_file.exists():
                with open(report_file, "r") as f:
                    json_data = json.load(f)

                self.report_data["test_suites"][test_file] = {
                    "status": "passed" if result.returncode == 0 else "failed",
                    "tests_run": json_data.get("summary", {}).get("total", 0),
                    "tests_passed": json_data.get("summary", {}).get("passed", 0),
                    "tests_failed": json_data.get("summary", {}).get("failed", 0),
                    "duration": json_data.get("duration", 0),
                    "failures": [],
                }

                # Extract failure details
                for test in json_data.get("tests", []):
                    if test.get("outcome") == "failed":
                        self.report_data["test_suites"][test_file]["failures"].append(
                            {"test_name": test.get("nodeid", ""), "error": test.get("call", {}).get("longrepr", "")}
                        )

            self.results[test_file] = result.returncode == 0

            if result.returncode == 0:
                print(f"✅ {test_file}: PASSED")
            else:
                print(f"❌ {test_file}: FAILED")
                if verbose:
                    print(f"STDOUT: {result.stdout}")
                    print(f"STDERR: {result.stderr}")

            return result.returncode == 0

        except Exception as e:
            print(f"❌ Error running {test_file}: {e}")
            self.results[test_file] = False
            return False

    def run_all_security_tests(self, verbose=False):
        """Run all security test suites"""
        print("🚀 Starting Comprehensive Security Test Suite")
        print("=" * 60)

        # Ensure reports directory exists
        Path(".reports").mkdir(exist_ok=True)

        # Security test files in order of execution
        test_files = [
            "test_advanced_jwt_auth.py",
            "test_security_audit_logger.py",
            "test_rate_limiter.py",
            "test_security_middleware.py",
            "test_data_encryption.py",
            "test_security_api_endpoints.py",
            "test_integration_security.py",
            "test_penetration_testing.py",
        ]

        passed_tests = 0
        total_tests = len(test_files)

        for test_file in test_files:
            if self.run_test_suite(test_file, verbose):
                passed_tests += 1

        # Generate summary
        self.report_data["summary"] = {
            "total_suites": total_tests,
            "passed_suites": passed_tests,
            "failed_suites": total_tests - passed_tests,
            "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
        }

        # Generate security analysis
        self.analyze_security_posture()

        # Generate report
        self.generate_security_report()

        print("\n" + "=" * 60)
        print("📊 Security Test Summary:")
        print(f"   Total Test Suites: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {total_tests - passed_tests}")
        print(f"   Success Rate: {self.report_data['summary']['success_rate']:.1f}%")

        if passed_tests == total_tests:
            print("🎉 All security tests PASSED!")
            return True
        else:
            print("⚠️  Some security tests FAILED!")
            return False

    def analyze_security_posture(self):
        """Analyze overall security posture"""
        findings = []
        recommendations = []

        # Analyze test results for security implications
        for suite_name, suite_data in self.report_data["test_suites"].items():
            if suite_data["status"] == "failed":
                if "jwt" in suite_name.lower():
                    findings.append(
                        {
                            "severity": "HIGH",
                            "category": "Authentication",
                            "finding": "JWT authentication vulnerabilities detected",
                            "suite": suite_name,
                        }
                    )
                    recommendations.append(
                        {
                            "priority": "CRITICAL",
                            "action": "Fix JWT implementation vulnerabilities immediately",
                            "category": "Authentication",
                        }
                    )

                elif "rate_limiter" in suite_name.lower():
                    findings.append(
                        {
                            "severity": "MEDIUM",
                            "category": "Rate Limiting",
                            "finding": "Rate limiting implementation issues",
                            "suite": suite_name,
                        }
                    )
                    recommendations.append(
                        {
                            "priority": "HIGH",
                            "action": "Review and fix rate limiting mechanisms",
                            "category": "DoS Protection",
                        }
                    )

                elif "encryption" in suite_name.lower():
                    findings.append(
                        {
                            "severity": "HIGH",
                            "category": "Data Protection",
                            "finding": "Data encryption vulnerabilities detected",
                            "suite": suite_name,
                        }
                    )
                    recommendations.append(
                        {
                            "priority": "CRITICAL",
                            "action": "Fix data encryption implementation",
                            "category": "Data Protection",
                        }
                    )

                elif "penetration" in suite_name.lower():
                    findings.append(
                        {
                            "severity": "CRITICAL",
                            "category": "Penetration Testing",
                            "finding": "Security vulnerabilities detected in penetration tests",
                            "suite": suite_name,
                        }
                    )
                    recommendations.append(
                        {
                            "priority": "CRITICAL",
                            "action": "Address all penetration testing vulnerabilities",
                            "category": "General Security",
                        }
                    )

        # Add general recommendations based on success rate
        success_rate = self.report_data["summary"]["success_rate"]

        if success_rate < 50:
            recommendations.append(
                {
                    "priority": "CRITICAL",
                    "action": "Comprehensive security review required - multiple critical failures",
                    "category": "General Security",
                }
            )
        elif success_rate < 80:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "action": "Security improvements needed - several test failures detected",
                    "category": "General Security",
                }
            )
        elif success_rate < 95:
            recommendations.append(
                {
                    "priority": "MEDIUM",
                    "action": "Minor security improvements recommended",
                    "category": "General Security",
                }
            )
        else:
            recommendations.append(
                {
                    "priority": "LOW",
                    "action": "Security posture is good - maintain current standards",
                    "category": "General Security",
                }
            )

        self.report_data["security_findings"] = findings
        self.report_data["recommendations"] = recommendations

    def generate_security_report(self):
        """Generate comprehensive security report"""

        # JSON report
        json_report_file = Path(".reports/security_test_report.json")
        with open(json_report_file, "w") as f:
            json.dump(self.report_data, f, indent=2)

        # HTML report
        html_report = self.generate_html_report()
        html_report_file = Path(".reports/security_test_report.html")
        with open(html_report_file, "w") as f:
            f.write(html_report)

        # Markdown report
        md_report = self.generate_markdown_report()
        md_report_file = Path(".reports/security_test_report.md")
        with open(md_report_file, "w") as f:
            f.write(md_report)

        print("\n📋 Security reports generated:")
        print(f"   JSON: {json_report_file}")
        print(f"   HTML: {html_report_file}")
        print(f"   Markdown: {md_report_file}")

    def generate_html_report(self):
        """Generate HTML security report"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Security Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
        .summary {{ background: #ecf0f1; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .test-suite {{ margin: 10px 0; padding: 10px; border-left: 4px solid #3498db; }}
        .passed {{ border-left-color: #27ae60; }}
        .failed {{ border-left-color: #e74c3c; }}
        .finding {{ margin: 5px 0; padding: 8px; border-radius: 3px; }}
        .finding.critical {{ background: #fadbd8; color: #c0392b; }}
        .finding.high {{ background: #fdeaa7; color: #d68910; }}
        .finding.medium {{ background: #d5f4e6; color: #239b56; }}
        .recommendation {{ margin: 5px 0; padding: 8px; background: #e8f6f3; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔒 Security Test Report</h1>
        <p>Generated: {self.report_data["timestamp"]}</p>
    </div>

    <div class="summary">
        <h2>📊 Summary</h2>
        <p><strong>Total Test Suites:</strong> {self.report_data["summary"]["total_suites"]}</p>
        <p><strong>Passed:</strong> {self.report_data["summary"]["passed_suites"]}</p>
        <p><strong>Failed:</strong> {self.report_data["summary"]["failed_suites"]}</p>
        <p><strong>Success Rate:</strong> {self.report_data["summary"]["success_rate"]:.1f}%</p>
    </div>

    <h2>🧪 Test Suites</h2>
"""

        for suite_name, suite_data in self.report_data["test_suites"].items():
            status_class = "passed" if suite_data["status"] == "passed" else "failed"
            status_emoji = "✅" if suite_data["status"] == "passed" else "❌"

            html += f"""
    <div class="test-suite {status_class}">
        <h3>{status_emoji} {suite_name}</h3>
        <p>Status: {suite_data["status"].upper()}</p>
        <p>Tests Run: {suite_data["tests_run"]}</p>
        <p>Passed: {suite_data["tests_passed"]}</p>
        <p>Failed: {suite_data["tests_failed"]}</p>
        <p>Duration: {suite_data["duration"]:.2f}s</p>
"""

            if suite_data["failures"]:
                html += "<h4>Failures:</h4><ul>"
                for failure in suite_data["failures"]:
                    html += f"<li>{failure['test_name']}</li>"
                html += "</ul>"

            html += "</div>"

        if self.report_data["security_findings"]:
            html += "<h2>🚨 Security Findings</h2>"
            for finding in self.report_data["security_findings"]:
                severity_class = finding["severity"].lower()
                html += f"""
    <div class="finding {severity_class}">
        <strong>[{finding["severity"]}] {finding["category"]}:</strong> {finding["finding"]}
        <br><small>Suite: {finding["suite"]}</small>
    </div>
"""

        if self.report_data["recommendations"]:
            html += "<h2>💡 Recommendations</h2>"
            for rec in self.report_data["recommendations"]:
                html += f"""
    <div class="recommendation">
        <strong>[{rec["priority"]}] {rec["category"]}:</strong> {rec["action"]}
    </div>
"""

        html += """
</body>
</html>
"""
        return html

    def generate_markdown_report(self):
        """Generate Markdown security report"""
        md = f"""# 🔒 Security Test Report

**Generated:** {self.report_data["timestamp"]}

## 📊 Summary

- **Total Test Suites:** {self.report_data["summary"]["total_suites"]}
- **Passed:** {self.report_data["summary"]["passed_suites"]}
- **Failed:** {self.report_data["summary"]["failed_suites"]}
- **Success Rate:** {self.report_data["summary"]["success_rate"]:.1f}%

## 🧪 Test Suites

"""

        for suite_name, suite_data in self.report_data["test_suites"].items():
            status_emoji = "✅" if suite_data["status"] == "passed" else "❌"

            md += f"""### {status_emoji} {suite_name}

- **Status:** {suite_data["status"].upper()}
- **Tests Run:** {suite_data["tests_run"]}
- **Passed:** {suite_data["tests_passed"]}
- **Failed:** {suite_data["tests_failed"]}
- **Duration:** {suite_data["duration"]:.2f}s

"""

            if suite_data["failures"]:
                md += "**Failures:**\n"
                for failure in suite_data["failures"]:
                    md += f"- {failure['test_name']}\n"
                md += "\n"

        if self.report_data["security_findings"]:
            md += "## 🚨 Security Findings\n\n"
            for finding in self.report_data["security_findings"]:
                md += f"- **[{finding['severity']}] {finding['category']}:** {finding['finding']} _(Suite: {finding['suite']})_\n"
            md += "\n"

        if self.report_data["recommendations"]:
            md += "## 💡 Recommendations\n\n"
            for rec in self.report_data["recommendations"]:
                md += f"- **[{rec['priority']}] {rec['category']}:** {rec['action']}\n"
            md += "\n"

        return md


def main():
    """Main function for command line execution"""
    parser = argparse.ArgumentParser(description="Run comprehensive security tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--test", "-t", help="Run specific test file")
    parser.add_argument("--report-only", action="store_true", help="Generate report from existing results")

    args = parser.parse_args()

    runner = SecurityTestRunner()

    if args.report_only:
        runner.generate_security_report()
        return

    if args.test:
        success = runner.run_test_suite(args.test, args.verbose)
    else:
        success = runner.run_all_security_tests(args.verbose)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
