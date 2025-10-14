#!/usr/bin/env python3
"""
P013: OWASP Top 10 2021 Validation Scanner
==========================================

Valida el cumplimiento contra OWASP Top 10 2021:
- A01: Broken Access Control
- A02: Cryptographic Failures
- A03: Injection
- A04: Insecure Design
- A05: Security Misconfiguration
- A06: Vulnerable and Outdated Components
- A07: Identification and Authentication Failures
- A08: Software and Data Integrity Failures
- A09: Security Logging and Monitoring Failures
- A10: Server-Side Request Forgery (SSRF)

Usage:
    python scripts/security/owasp_validator.py --format markdown
    python scripts/security/owasp_validator.py --format json --output scan.json
    python scripts/security/owasp_validator.py --category A03 --verbose
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Optional
import subprocess


@dataclass
class OWASPFinding:
    """Representa un finding de vulnerabilidad OWASP."""

    category: str  # A01-A10
    category_name: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    finding_type: str
    file_path: str
    line_number: Optional[int]
    description: str
    evidence: str
    recommendation: str
    cwe_id: Optional[str] = None
    cvss_score: Optional[float] = None


@dataclass
class OWASPScanResult:
    """Resultado consolidado del escaneo OWASP."""

    scan_timestamp: str
    scan_duration_seconds: float
    findings: List[OWASPFinding]
    summary: Dict[str, int]
    compliance_score: float  # 0-100


class OWASPValidator:
    """Validador de OWASP Top 10 2021."""

    OWASP_CATEGORIES = {
        "A01": {
            "name": "Broken Access Control",
            "cwe": ["CWE-22", "CWE-23", "CWE-35", "CWE-59", "CWE-200", "CWE-201", "CWE-219", "CWE-264", "CWE-275"],
        },
        "A02": {
            "name": "Cryptographic Failures",
            "cwe": ["CWE-259", "CWE-327", "CWE-328", "CWE-329", "CWE-330", "CWE-331", "CWE-335", "CWE-338"],
        },
        "A03": {
            "name": "Injection",
            "cwe": ["CWE-74", "CWE-75", "CWE-77", "CWE-78", "CWE-79", "CWE-88", "CWE-89", "CWE-91", "CWE-917"],
        },
        "A04": {
            "name": "Insecure Design",
            "cwe": ["CWE-209", "CWE-256", "CWE-501", "CWE-522", "CWE-799"],
        },
        "A05": {
            "name": "Security Misconfiguration",
            "cwe": ["CWE-2", "CWE-11", "CWE-13", "CWE-15", "CWE-16", "CWE-260", "CWE-315", "CWE-520", "CWE-526"],
        },
        "A06": {
            "name": "Vulnerable and Outdated Components",
            "cwe": ["CWE-1104", "CWE-1329"],
        },
        "A07": {
            "name": "Identification and Authentication Failures",
            "cwe": ["CWE-255", "CWE-259", "CWE-287", "CWE-288", "CWE-290", "CWE-294", "CWE-295", "CWE-306", "CWE-307"],
        },
        "A08": {
            "name": "Software and Data Integrity Failures",
            "cwe": ["CWE-345", "CWE-353", "CWE-426", "CWE-494", "CWE-502", "CWE-565", "CWE-784", "CWE-829"],
        },
        "A09": {
            "name": "Security Logging and Monitoring Failures",
            "cwe": ["CWE-778", "CWE-779", "CWE-778", "CWE-223"],
        },
        "A10": {
            "name": "Server-Side Request Forgery",
            "cwe": ["CWE-918"],
        },
    }

    # Patrones de injection comunes
    INJECTION_PATTERNS = {
        "sql_injection": {
            "pattern": r'(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\s+.*\+.*\s*(WHERE|FROM|INTO)',
            "severity": "CRITICAL",
            "cwe": "CWE-89",
        },
        "nosql_injection": {
            "pattern": r'\$where.*\$ne.*\$or.*\$and',
            "severity": "HIGH",
            "cwe": "CWE-943",
        },
        "command_injection": {
            "pattern": r'(subprocess|os\.system|os\.popen|eval|exec)\s*\(.*\+.*\)',
            "severity": "CRITICAL",
            "cwe": "CWE-78",
        },
        "ldap_injection": {
            "pattern": r'ldap.*search.*\+.*\)',
            "severity": "HIGH",
            "cwe": "CWE-90",
        },
    }

    # Patrones de XSS
    XSS_PATTERNS = {
        "reflected_xss": {
            "pattern": r'(innerHTML|outerHTML|document\.write)\s*=.*request\.',
            "severity": "HIGH",
            "cwe": "CWE-79",
        },
        "stored_xss": {
            "pattern": r'(innerHTML|outerHTML)\s*=.*(?:database|db|mongo|redis)',
            "severity": "CRITICAL",
            "cwe": "CWE-79",
        },
    }

    # Patrones de autenticación débil
    AUTH_PATTERNS = {
        "weak_jwt": {
            "pattern": r'jwt\.encode.*HS256.*(?!SECRET_KEY)',
            "severity": "CRITICAL",
            "cwe": "CWE-327",
        },
        "no_password_validation": {
            "pattern": r'password\s*=\s*request\.',
            "severity": "HIGH",
            "cwe": "CWE-521",
        },
    }

    # Patrones de SSRF
    SSRF_PATTERNS = {
        "unvalidated_redirect": {
            "pattern": r'redirect\(.*request\.',
            "severity": "HIGH",
            "cwe": "CWE-601",
        },
        "arbitrary_url_fetch": {
            "pattern": r'(requests\.get|httpx\.get|urllib\.request)\s*\(.*request\.',
            "severity": "CRITICAL",
            "cwe": "CWE-918",
        },
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.findings: List[OWASPFinding] = []
        self.start_time = datetime.now()

    def run_full_scan(self) -> OWASPScanResult:
        """Ejecuta escaneo completo de OWASP Top 10."""
        print("\n" + "=" * 80)
        print("🔐 OWASP TOP 10 2021 VALIDATION - P013")
        print("=" * 80 + "\n")

        # A01: Broken Access Control
        print("🔍 1/10: Validando Access Control (A01)...")
        self._check_access_control()

        # A02: Cryptographic Failures
        print("🔍 2/10: Validando Cryptography (A02)...")
        self._check_cryptographic_failures()

        # A03: Injection
        print("🔍 3/10: Validando Injection (A03)...")
        self._check_injection_vulnerabilities()

        # A04: Insecure Design
        print("🔍 4/10: Validando Secure Design (A04)...")
        self._check_insecure_design()

        # A05: Security Misconfiguration
        print("🔍 5/10: Validando Security Config (A05)...")
        self._check_security_misconfiguration()

        # A06: Vulnerable Components
        print("🔍 6/10: Validando Dependencies (A06)...")
        self._check_vulnerable_components()

        # A07: Authentication Failures
        print("🔍 7/10: Validando Authentication (A07)...")
        self._check_authentication_failures()

        # A08: Data Integrity
        print("🔍 8/10: Validando Data Integrity (A08)...")
        self._check_data_integrity()

        # A09: Logging and Monitoring
        print("🔍 9/10: Validando Logging (A09)...")
        self._check_logging_monitoring()

        # A10: SSRF
        print("🔍 10/10: Validando SSRF (A10)...")
        self._check_ssrf_vulnerabilities()

        duration = (datetime.now() - self.start_time).total_seconds()

        # Calcular summary
        summary = self._calculate_summary()
        compliance_score = self._calculate_compliance_score()

        result = OWASPScanResult(
            scan_timestamp=self.start_time.isoformat(),
            scan_duration_seconds=duration,
            findings=self.findings,
            summary=summary,
            compliance_score=compliance_score,
        )

        self._print_summary(result)
        return result

    def _check_access_control(self):
        """A01: Broken Access Control."""
        # 1. Check for missing authorization decorators
        for file_path in self.project_root.rglob("*.py"):
            if "routers" not in str(file_path):
                continue

            try:
                content = file_path.read_text()
                lines = content.split("\n")

                for i, line in enumerate(lines, 1):
                    # Detect route without auth decorator
                    if re.search(r'@router\.(get|post|put|delete|patch)', line, re.IGNORECASE):
                        # Check if next 5 lines have auth decorator
                        context = "\n".join(lines[max(0, i - 5) : i])
                        if "Depends" not in context and "requires_auth" not in context:
                            self.findings.append(
                                OWASPFinding(
                                    category="A01",
                                    category_name="Broken Access Control",
                                    severity="HIGH",
                                    finding_type="Missing Authorization",
                                    file_path=str(file_path.relative_to(self.project_root)),
                                    line_number=i,
                                    description="Route endpoint without authorization decorator",
                                    evidence=line.strip(),
                                    recommendation="Add Depends(get_current_user) or @requires_auth decorator",
                                    cwe_id="CWE-284",
                                )
                            )

            except Exception:
                continue

        # 2. Check for path traversal vulnerabilities
        for file_path in self.project_root.rglob("*.py"):
            try:
                content = file_path.read_text()
                if re.search(r'open\(.*\+.*\)', content) or re.search(r'Path\(.*\+.*\)', content):
                    self.findings.append(
                        OWASPFinding(
                            category="A01",
                            category_name="Broken Access Control",
                            severity="CRITICAL",
                            finding_type="Path Traversal",
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=None,
                            description="Potential path traversal vulnerability",
                            evidence="Dynamic file path construction detected",
                            recommendation="Use Path.resolve() and validate against allowed directories",
                            cwe_id="CWE-22",
                        )
                    )
            except Exception:
                continue

    def _check_cryptographic_failures(self):
        """A02: Cryptographic Failures."""
        # 1. Check for weak encryption algorithms
        weak_algos = ["MD5", "SHA1", "DES", "RC4"]

        for file_path in self.project_root.rglob("*.py"):
            try:
                content = file_path.read_text()

                for algo in weak_algos:
                    if re.search(rf'\b{algo}\b', content, re.IGNORECASE):
                        self.findings.append(
                            OWASPFinding(
                                category="A02",
                                category_name="Cryptographic Failures",
                                severity="HIGH",
                                finding_type="Weak Cryptography",
                                file_path=str(file_path.relative_to(self.project_root)),
                                line_number=None,
                                description=f"Weak cryptographic algorithm detected: {algo}",
                                evidence=f"Usage of {algo} found in code",
                                recommendation=f"Replace {algo} with SHA256 or better",
                                cwe_id="CWE-327",
                            )
                        )

            except Exception:
                continue

        # 2. Check for hardcoded encryption keys
        for file_path in self.project_root.rglob("*.py"):
            try:
                content = file_path.read_text()

                if re.search(r'(key|secret)\s*=\s*["\'][a-zA-Z0-9]{16,}["\']', content, re.IGNORECASE):
                    self.findings.append(
                        OWASPFinding(
                            category="A02",
                            category_name="Cryptographic Failures",
                            severity="CRITICAL",
                            finding_type="Hardcoded Encryption Key",
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=None,
                            description="Hardcoded encryption key detected",
                            evidence="key = \"...\" pattern found",
                            recommendation="Use environment variables or secrets manager",
                            cwe_id="CWE-798",
                        )
                    )

            except Exception:
                continue

    def _check_injection_vulnerabilities(self):
        """A03: Injection."""
        for file_path in self.project_root.rglob("*.py"):
            if "test_" in file_path.name:
                continue

            try:
                content = file_path.read_text()
                lines = content.split("\n")

                for pattern_name, pattern_config in self.INJECTION_PATTERNS.items():
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern_config["pattern"], line, re.IGNORECASE):
                            self.findings.append(
                                OWASPFinding(
                                    category="A03",
                                    category_name="Injection",
                                    severity=pattern_config["severity"],
                                    finding_type=pattern_name.replace("_", " ").title(),
                                    file_path=str(file_path.relative_to(self.project_root)),
                                    line_number=i,
                                    description=f"Potential {pattern_name.replace('_', ' ')} vulnerability",
                                    evidence=line.strip()[:100],
                                    recommendation="Use parameterized queries or input validation",
                                    cwe_id=pattern_config["cwe"],
                                )
                            )

            except Exception:
                continue

    def _check_insecure_design(self):
        """A04: Insecure Design."""
        # Check for missing rate limiting
        main_file = self.project_root / "app" / "main.py"
        if main_file.exists():
            content = main_file.read_text()
            if "Limiter" not in content and "rate_limit" not in content:
                self.findings.append(
                    OWASPFinding(
                        category="A04",
                        category_name="Insecure Design",
                        severity="MEDIUM",
                        finding_type="Missing Rate Limiting",
                        file_path="app/main.py",
                        line_number=None,
                        description="No rate limiting configured",
                        evidence="Limiter/rate_limit not found in main.py",
                        recommendation="Implement rate limiting with slowapi or similar",
                        cwe_id="CWE-770",
                    )
                )

    def _check_security_misconfiguration(self):
        """A05: Security Misconfiguration."""
        # Check for DEBUG mode in production
        env_file = self.project_root / ".env"
        if env_file.exists():
            content = env_file.read_text()
            if re.search(r'DEBUG\s*=\s*[Tt]rue', content):
                self.findings.append(
                    OWASPFinding(
                        category="A05",
                        category_name="Security Misconfiguration",
                        severity="HIGH",
                        finding_type="DEBUG Mode Enabled",
                        file_path=".env",
                        line_number=None,
                        description="DEBUG mode enabled",
                        evidence="DEBUG=true found in .env",
                        recommendation="Set DEBUG=false in production",
                        cwe_id="CWE-489",
                    )
                )

        # Check for missing security headers
        middleware_file = self.project_root / "app" / "core" / "middleware.py"
        if middleware_file.exists():
            content = middleware_file.read_text()
            required_headers = ["X-Content-Type-Options", "X-Frame-Options", "Content-Security-Policy"]

            for header in required_headers:
                if header not in content:
                    self.findings.append(
                        OWASPFinding(
                            category="A05",
                            category_name="Security Misconfiguration",
                            severity="MEDIUM",
                            finding_type="Missing Security Header",
                            file_path="app/core/middleware.py",
                            line_number=None,
                            description=f"Missing security header: {header}",
                            evidence=f"{header} not found in middleware",
                            recommendation=f"Add {header} to SecurityHeadersMiddleware",
                            cwe_id="CWE-16",
                        )
                    )

    def _check_vulnerable_components(self):
        """A06: Vulnerable and Outdated Components."""
        # Delegate to P011 (dependency scan)
        vuln_report = self.project_root / ".security" / "vuln-scan-latest.json"
        if vuln_report.exists():
            try:
                data = json.loads(vuln_report.read_text())
                vuln_count = data.get("summary", {}).get("total_vulnerabilities", 0)

                if vuln_count > 0:
                    self.findings.append(
                        OWASPFinding(
                            category="A06",
                            category_name="Vulnerable and Outdated Components",
                            severity="HIGH" if vuln_count < 5 else "CRITICAL",
                            finding_type="Vulnerable Dependencies",
                            file_path="dependencies",
                            line_number=None,
                            description=f"{vuln_count} vulnerable dependencies detected",
                            evidence="See .security/vuln-scan-latest.json for details",
                            recommendation="Run 'make security-deps' and update packages",
                            cwe_id="CWE-1104",
                        )
                    )
            except Exception:
                pass

    def _check_authentication_failures(self):
        """A07: Identification and Authentication Failures."""
        # Check for weak JWT configuration
        for file_path in self.project_root.rglob("*.py"):
            try:
                content = file_path.read_text()

                # Check for JWT with HS256 and hardcoded secret
                if re.search(r'jwt\.encode.*HS256', content, re.IGNORECASE):
                    if "SECRET_KEY" not in content and "os.getenv" not in content:
                        self.findings.append(
                            OWASPFinding(
                                category="A07",
                                category_name="Authentication Failures",
                                severity="CRITICAL",
                                finding_type="Weak JWT Configuration",
                                file_path=str(file_path.relative_to(self.project_root)),
                                line_number=None,
                                description="JWT with hardcoded secret",
                                evidence="jwt.encode with HS256 and no env var",
                                recommendation="Use SECRET_KEY from environment variables",
                                cwe_id="CWE-798",
                            )
                        )

                # Check for missing password complexity validation
                if "password" in content and "len(" not in content and "validate" not in content.lower():
                    self.findings.append(
                        OWASPFinding(
                            category="A07",
                            category_name="Authentication Failures",
                            severity="MEDIUM",
                            finding_type="Weak Password Policy",
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=None,
                            description="No password complexity validation",
                            evidence="password field without validation",
                            recommendation="Implement password complexity requirements (min 8 chars, uppercase, number, special)",
                            cwe_id="CWE-521",
                        )
                    )

            except Exception:
                continue

    def _check_data_integrity(self):
        """A08: Software and Data Integrity Failures."""
        # Check for insecure deserialization
        for file_path in self.project_root.rglob("*.py"):
            try:
                content = file_path.read_text()

                # Check for pickle usage
                if "pickle.loads" in content or "pickle.load" in content:
                    self.findings.append(
                        OWASPFinding(
                            category="A08",
                            category_name="Data Integrity Failures",
                            severity="CRITICAL",
                            finding_type="Insecure Deserialization",
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=None,
                            description="Insecure deserialization with pickle",
                            evidence="pickle.loads() detected",
                            recommendation="Use JSON or validate data before unpickling",
                            cwe_id="CWE-502",
                        )
                    )

            except Exception:
                continue

    def _check_logging_monitoring(self):
        """A09: Security Logging and Monitoring Failures."""
        # Check for logging of authentication failures
        auth_files = list(self.project_root.rglob("*auth*.py"))

        for file_path in auth_files:
            try:
                content = file_path.read_text()

                # Check if failed auth attempts are logged
                if "password" in content.lower() and "logger" not in content:
                    self.findings.append(
                        OWASPFinding(
                            category="A09",
                            category_name="Logging and Monitoring Failures",
                            severity="MEDIUM",
                            finding_type="Missing Security Logging",
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=None,
                            description="Authentication logic without logging",
                            evidence="No logger usage in auth module",
                            recommendation="Log all authentication failures and suspicious activities",
                            cwe_id="CWE-778",
                        )
                    )

            except Exception:
                continue

    def _check_ssrf_vulnerabilities(self):
        """A10: Server-Side Request Forgery."""
        for file_path in self.project_root.rglob("*.py"):
            if "test_" in file_path.name:
                continue

            try:
                content = file_path.read_text()
                lines = content.split("\n")

                for pattern_name, pattern_config in self.SSRF_PATTERNS.items():
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern_config["pattern"], line, re.IGNORECASE):
                            self.findings.append(
                                OWASPFinding(
                                    category="A10",
                                    category_name="Server-Side Request Forgery",
                                    severity=pattern_config["severity"],
                                    finding_type=pattern_name.replace("_", " ").title(),
                                    file_path=str(file_path.relative_to(self.project_root)),
                                    line_number=i,
                                    description=f"Potential {pattern_name.replace('_', ' ')} vulnerability",
                                    evidence=line.strip()[:100],
                                    recommendation="Validate and whitelist URLs before making requests",
                                    cwe_id=pattern_config["cwe"],
                                )
                            )

            except Exception:
                continue

    def _calculate_summary(self) -> Dict[str, int]:
        """Calcula summary de findings."""
        summary = {"total": len(self.findings), "by_severity": {}, "by_category": {}}

        for finding in self.findings:
            # Por severidad
            severity = finding.severity
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1

            # Por categoría
            category = finding.category
            summary["by_category"][category] = summary["by_category"].get(category, 0) + 1

        return summary

    def _calculate_compliance_score(self) -> float:
        """Calcula score de compliance (0-100)."""
        if not self.findings:
            return 100.0

        # Peso por severidad
        weights = {"CRITICAL": 10, "HIGH": 5, "MEDIUM": 2, "LOW": 1}

        total_weight = sum(weights[f.severity] for f in self.findings)

        # Score: 100 - (total_weight / baseline * 100)
        baseline = 100  # Máximo esperado
        score = max(0, 100 - (total_weight / baseline * 100))

        return round(score, 2)

    def _print_summary(self, result: OWASPScanResult):
        """Imprime resumen del escaneo."""
        print("\n" + "=" * 80)
        print("📊 RESUMEN DEL ESCANEO OWASP")
        print("=" * 80 + "\n")

        print(f"⏱️  Duración: {result.scan_duration_seconds:.2f}s")
        print(f"📅 Timestamp: {result.scan_timestamp}")
        print(f"🔍 Total findings: {result.summary['total']}")

        if result.summary.get("by_severity"):
            print("\n📊 Por Severidad:")
            for severity, count in sorted(result.summary["by_severity"].items(), key=lambda x: x[1], reverse=True):
                print(f"   • {severity}: {count}")

        if result.summary.get("by_category"):
            print("\n📂 Por Categoría OWASP:")
            for category, count in sorted(result.summary["by_category"].items()):
                cat_name = self.OWASP_CATEGORIES[category]["name"]
                print(f"   • {category} ({cat_name}): {count}")

        print(f"\n🎯 Compliance Score: {result.compliance_score}/100")

        if result.compliance_score >= 90:
            print("   ✅ Excellent security posture!")
        elif result.compliance_score >= 70:
            print("   ⚠️  Good, but needs improvement")
        elif result.compliance_score >= 50:
            print("   ⚠️  Moderate risk - action recommended")
        else:
            print("   🔴 High risk - immediate action required!")

    def export_to_json(self, output_path: Path):
        """Exporta resultados a JSON."""
        result = self.run_full_scan()
        data = {
            "scan_timestamp": result.scan_timestamp,
            "scan_duration_seconds": result.scan_duration_seconds,
            "findings": [asdict(f) for f in result.findings],
            "summary": result.summary,
            "compliance_score": result.compliance_score,
        }

        output_path.write_text(json.dumps(data, indent=2))
        print(f"\n✅ JSON report saved: {output_path}")

    def export_to_markdown(self, output_path: Path):
        """Exporta resultados a Markdown."""
        result = self.run_full_scan()

        md_lines = ["# 🔐 OWASP Top 10 2021 Validation Report - P013\n"]
        md_lines.append(f"**Scan Date**: {result.scan_timestamp}\n")
        md_lines.append(f"**Duration**: {result.scan_duration_seconds:.2f} seconds\n")
        md_lines.append(f"**Compliance Score**: {result.compliance_score}/100\n")

        if result.compliance_score >= 90:
            md_lines.append("**Status**: ✅ **EXCELLENT**\n")
        elif result.compliance_score >= 70:
            md_lines.append("**Status**: ⚠️ **GOOD**\n")
        elif result.compliance_score >= 50:
            md_lines.append("**Status**: ⚠️ **MODERATE RISK**\n")
        else:
            md_lines.append("**Status**: 🔴 **HIGH RISK**\n")

        md_lines.append("\n## 📊 Summary\n\n")
        md_lines.append(f"- **Total Findings**: {result.summary['total']}\n")

        if result.summary.get("by_severity"):
            md_lines.append("\n### By Severity\n\n")
            for severity, count in sorted(result.summary["by_severity"].items(), key=lambda x: x[1], reverse=True):
                md_lines.append(f"- **{severity}**: {count}\n")

        if result.summary.get("by_category"):
            md_lines.append("\n### By OWASP Category\n\n")
            for category, count in sorted(result.summary["by_category"].items()):
                cat_name = self.OWASP_CATEGORIES[category]["name"]
                md_lines.append(f"- **{category}** ({cat_name}): {count}\n")

        md_lines.append("\n## 🐛 Findings\n\n")

        for i, finding in enumerate(result.findings, 1):
            md_lines.append(f"### {i}. {finding.finding_type} ({finding.severity})\n\n")
            md_lines.append(f"- **Category**: {finding.category} - {finding.category_name}\n")
            md_lines.append(f"- **File**: `{finding.file_path}`\n")
            if finding.line_number:
                md_lines.append(f"- **Line**: {finding.line_number}\n")
            if finding.cwe_id:
                md_lines.append(f"- **CWE**: {finding.cwe_id}\n")
            md_lines.append(f"- **Description**: {finding.description}\n")
            md_lines.append(f"- **Evidence**: `{finding.evidence}`\n")
            md_lines.append(f"- **Recommendation**: {finding.recommendation}\n\n")

        output_path.write_text("".join(md_lines))
        print(f"\n✅ Markdown report saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="OWASP Top 10 2021 Validator")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown", help="Output format")
    parser.add_argument("--output", type=str, help="Output file path")
    parser.add_argument("--category", type=str, help="Scan only specific category (A01-A10)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent.parent

    validator = OWASPValidator(project_root)

    if args.format == "json":
        output_path = Path(args.output) if args.output else project_root / ".security" / "owasp-scan-latest.json"
        validator.export_to_json(output_path)
    else:
        output_path = Path(args.output) if args.output else project_root / ".security" / "owasp-scan-latest.md"
        validator.export_to_markdown(output_path)

    # Exit code based on compliance score
    result = validator.run_full_scan()
    if result.compliance_score < 50:
        sys.exit(2)  # CRITICAL
    elif result.compliance_score < 70:
        sys.exit(1)  # HIGH
    else:
        sys.exit(0)  # OK


if __name__ == "__main__":
    main()
