#!/usr/bin/env python3
"""
P014: Compliance Report Generator
==================================

Consolida findings de:
- P011: Dependency vulnerabilities (vuln-scan-latest.json)
- P012: Hardcoded secrets (secret-scan-latest.json)
- P013: OWASP Top 10 compliance (owasp-scan-latest.json)

Genera:
- Executive summary con risk score global
- Compliance matrix (OWASP, CWE, NIST, PCI-DSS)
- Risk matrix (likelihood × impact)
- Remediation roadmap priorizado
- SLO definitions y current status
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class Finding:
    """Unified security finding."""
    
    source: str  # P011, P012, P013
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str  # Vulnerability category
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    cwe_id: Optional[str] = None
    cvss_score: Optional[float] = None
    recommendation: str = ""


@dataclass
class ComplianceMetrics:
    """Compliance metrics across standards."""
    
    owasp_coverage: float = 0.0  # 0-100
    owasp_score: float = 0.0  # 0-100
    cwe_coverage: int = 0  # Number of CWE IDs covered
    nist_controls: List[str] = field(default_factory=list)
    pci_requirements: List[str] = field(default_factory=list)


@dataclass
class RiskAssessment:
    """Overall risk assessment."""
    
    risk_score: float  # 0-100 (0=worst, 100=best)
    risk_level: str  # CRITICAL, HIGH, MEDIUM, LOW
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    total_findings: int


@dataclass
class ComplianceReport:
    """Consolidated compliance report."""
    
    timestamp: str
    risk_assessment: RiskAssessment
    compliance_metrics: ComplianceMetrics
    findings_by_source: Dict[str, List[Finding]]
    findings_by_severity: Dict[str, List[Finding]]
    remediation_roadmap: List[Dict[str, any]]
    slo_status: Dict[str, any]


class ComplianceReportGenerator:
    """Generate comprehensive compliance report."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.security_dir = project_root / ".security"
        self.findings: List[Finding] = []
        
        # Severity weights for risk scoring
        self.severity_weights = {
            "CRITICAL": 10,
            "HIGH": 5,
            "MEDIUM": 2,
            "LOW": 1
        }
        
        # SLO definitions
        self.slos = {
            "critical_findings": {"max": 0, "current": 0, "status": "PASS"},
            "high_findings": {"max": 5, "current": 0, "status": "PASS"},
            "compliance_score": {"min": 70, "current": 0, "status": "FAIL"},
            "outdated_dependencies": {"max": 30, "current": 0, "status": "PASS"},  # Percentage
            "hardcoded_secrets": {"max": 0, "current": 0, "status": "PASS"},
        }
    
    def load_p011_findings(self) -> List[Finding]:
        """Load dependency vulnerability findings."""
        findings = []
        report_path = self.security_dir / "vuln-scan-latest.json"
        
        if not report_path.exists():
            print(f"⚠️  P011 report not found: {report_path}")
            return findings
        
        try:
            with open(report_path) as f:
                data = json.load(f)
            
            # Extract vulnerabilities
            vulnerabilities = data.get("vulnerabilities", [])
            
            for vuln in vulnerabilities:
                severity = vuln.get("severity", "UNKNOWN").upper()
                
                finding = Finding(
                    source="P011",
                    severity=severity,
                    category="Vulnerable Dependency",
                    description=f"{vuln.get('package', 'Unknown')} {vuln.get('version', '')} - {vuln.get('advisory', '')}",
                    cwe_id=vuln.get("cwe"),
                    cvss_score=vuln.get("cvss_score"),
                    recommendation=f"Update to version {vuln.get('fixed_version', 'latest')}"
                )
                findings.append(finding)
            
            print(f"✅ Loaded {len(findings)} P011 findings")
            
        except Exception as e:
            print(f"❌ Error loading P011: {e}")
        
        return findings
    
    def load_p012_findings(self) -> List[Finding]:
        """Load secret scanning findings."""
        findings = []
        report_path = self.security_dir / "secret-scan-latest.json"
        
        if not report_path.exists():
            print(f"⚠️  P012 report not found: {report_path}")
            return findings
        
        try:
            with open(report_path) as f:
                data = json.load(f)
            
            # Extract findings by category
            all_findings = data.get("findings", {})
            
            for category, items in all_findings.items():
                for item in items:
                    severity = item.get("severity", "HIGH").upper()
                    
                    finding = Finding(
                        source="P012",
                        severity=severity,
                        category=f"Secret: {category}",
                        description=item.get("description", "Hardcoded secret detected"),
                        file_path=item.get("file"),
                        line_number=item.get("line"),
                        recommendation="Move to environment variable or secrets manager"
                    )
                    findings.append(finding)
            
            print(f"✅ Loaded {len(findings)} P012 findings")
            
        except Exception as e:
            print(f"❌ Error loading P012: {e}")
        
        return findings
    
    def load_p013_findings(self) -> List[Finding]:
        """Load OWASP Top 10 findings."""
        findings = []
        report_path = self.security_dir / "owasp-scan-latest.json"
        
        if not report_path.exists():
            print(f"⚠️  P013 report not found: {report_path}")
            return findings
        
        try:
            with open(report_path) as f:
                data = json.load(f)
            
            # Extract findings
            owasp_findings = data.get("findings", [])
            
            for item in owasp_findings:
                finding = Finding(
                    source="P013",
                    severity=item.get("severity", "MEDIUM").upper(),
                    category=f"{item.get('category', 'Unknown')}: {item.get('category_name', '')}",
                    description=item.get("description", ""),
                    file_path=item.get("file_path"),
                    line_number=item.get("line_number"),
                    cwe_id=item.get("cwe_id"),
                    cvss_score=item.get("cvss_score"),
                    recommendation=item.get("recommendation", "")
                )
                findings.append(finding)
            
            print(f"✅ Loaded {len(findings)} P013 findings")
            
        except Exception as e:
            print(f"❌ Error loading P013: {e}")
        
        return findings
    
    def calculate_risk_score(self) -> RiskAssessment:
        """Calculate overall risk score based on findings."""
        severity_counts = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0
        }
        
        for finding in self.findings:
            severity = finding.severity.upper()
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        # Calculate weighted risk score (0-100, higher is better)
        total_weight = sum(
            count * self.severity_weights[severity]
            for severity, count in severity_counts.items()
        )
        
        # Maximum reasonable weight (for normalization)
        max_weight = 100
        
        risk_score = max(0, 100 - (total_weight / max_weight * 100))
        
        # Determine risk level
        if risk_score >= 70:
            risk_level = "LOW"
        elif risk_score >= 50:
            risk_level = "MEDIUM"
        elif risk_score >= 30:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"
        
        return RiskAssessment(
            risk_score=round(risk_score, 2),
            risk_level=risk_level,
            critical_count=severity_counts["CRITICAL"],
            high_count=severity_counts["HIGH"],
            medium_count=severity_counts["MEDIUM"],
            low_count=severity_counts["LOW"],
            total_findings=len(self.findings)
        )
    
    def calculate_compliance_metrics(self) -> ComplianceMetrics:
        """Calculate compliance metrics across standards."""
        # OWASP Top 10 coverage (from P013)
        owasp_report_path = self.security_dir / "owasp-scan-latest.json"
        owasp_score = 0.0
        owasp_coverage = 100.0  # We scan all 10 categories
        
        if owasp_report_path.exists():
            try:
                with open(owasp_report_path) as f:
                    data = json.load(f)
                owasp_score = data.get("compliance_score", 0.0)
            except Exception:
                pass
        
        # CWE coverage (unique CWE IDs from findings)
        cwe_ids = set()
        for finding in self.findings:
            if finding.cwe_id:
                cwe_ids.add(finding.cwe_id)
        
        # NIST controls mapping (simplified)
        nist_controls = []
        if any(f.source == "P011" for f in self.findings):
            nist_controls.append("SI-2 (Flaw Remediation)")
        if any(f.source == "P012" for f in self.findings):
            nist_controls.append("IA-5 (Authenticator Management)")
        if any(f.source == "P013" and "A01" in f.category for f in self.findings):
            nist_controls.append("AC-3 (Access Enforcement)")
        if any(f.source == "P013" and "A02" in f.category for f in self.findings):
            nist_controls.append("SC-13 (Cryptographic Protection)")
        
        # PCI-DSS requirements mapping (simplified)
        pci_requirements = []
        if any("injection" in f.category.lower() for f in self.findings):
            pci_requirements.append("Req 6.5.1 (Injection Flaws)")
        if any("crypto" in f.category.lower() for f in self.findings):
            pci_requirements.append("Req 4.1 (Strong Cryptography)")
        if any("secret" in f.category.lower() for f in self.findings):
            pci_requirements.append("Req 8.2 (Strong Authentication)")
        
        return ComplianceMetrics(
            owasp_coverage=owasp_coverage,
            owasp_score=owasp_score,
            cwe_coverage=len(cwe_ids),
            nist_controls=nist_controls,
            pci_requirements=pci_requirements
        )
    
    def generate_remediation_roadmap(self) -> List[Dict[str, any]]:
        """Generate prioritized remediation roadmap."""
        roadmap = []
        
        # Group findings by severity
        critical = [f for f in self.findings if f.severity == "CRITICAL"]
        high = [f for f in self.findings if f.severity == "HIGH"]
        medium = [f for f in self.findings if f.severity == "MEDIUM"]
        low = [f for f in self.findings if f.severity == "LOW"]
        
        # Phase 1: CRITICAL (immediate action)
        if critical:
            roadmap.append({
                "phase": 1,
                "name": "CRITICAL Remediation",
                "timeframe": "< 24 hours",
                "priority": "BLOCKER",
                "findings_count": len(critical),
                "actions": [
                    f"{f.category}: {f.description[:80]}..."
                    for f in critical[:5]  # Top 5
                ],
                "blocking_deployment": True
            })
        
        # Phase 2: HIGH (within 1 week)
        if high:
            roadmap.append({
                "phase": 2,
                "name": "HIGH Priority Fixes",
                "timeframe": "< 1 week",
                "priority": "HIGH",
                "findings_count": len(high),
                "actions": [
                    f"{f.category}: {f.description[:80]}..."
                    for f in high[:10]  # Top 10
                ],
                "blocking_deployment": False
            })
        
        # Phase 3: MEDIUM (within 1 month)
        if medium:
            roadmap.append({
                "phase": 3,
                "name": "MEDIUM Priority Improvements",
                "timeframe": "< 1 month",
                "priority": "MEDIUM",
                "findings_count": len(medium),
                "actions": ["Batch remediation of medium priority issues"],
                "blocking_deployment": False
            })
        
        # Phase 4: LOW (within 3 months)
        if low:
            roadmap.append({
                "phase": 4,
                "name": "LOW Priority Tech Debt",
                "timeframe": "< 3 months",
                "priority": "LOW",
                "findings_count": len(low),
                "actions": ["Incremental improvements as part of regular sprints"],
                "blocking_deployment": False
            })
        
        return roadmap
    
    def update_slo_status(self, risk_assessment: RiskAssessment, compliance_metrics: ComplianceMetrics):
        """Update SLO status based on current findings."""
        # Critical findings SLO
        self.slos["critical_findings"]["current"] = risk_assessment.critical_count
        self.slos["critical_findings"]["status"] = (
            "PASS" if risk_assessment.critical_count <= self.slos["critical_findings"]["max"]
            else "FAIL"
        )
        
        # High findings SLO
        self.slos["high_findings"]["current"] = risk_assessment.high_count
        self.slos["high_findings"]["status"] = (
            "PASS" if risk_assessment.high_count <= self.slos["high_findings"]["max"]
            else "FAIL"
        )
        
        # Compliance score SLO
        self.slos["compliance_score"]["current"] = compliance_metrics.owasp_score
        self.slos["compliance_score"]["status"] = (
            "PASS" if compliance_metrics.owasp_score >= self.slos["compliance_score"]["min"]
            else "FAIL"
        )
        
        # Hardcoded secrets SLO
        secret_count = len([f for f in self.findings if f.source == "P012"])
        self.slos["hardcoded_secrets"]["current"] = secret_count
        self.slos["hardcoded_secrets"]["status"] = (
            "PASS" if secret_count <= self.slos["hardcoded_secrets"]["max"]
            else "FAIL"
        )
    
    def generate_report(self) -> ComplianceReport:
        """Generate comprehensive compliance report."""
        print("\n" + "=" * 70)
        print("🔐 COMPLIANCE REPORT GENERATOR - P014")
        print("=" * 70)
        
        # Load findings from all sources
        print("\n📥 Loading findings from P011, P012, P013...")
        p011_findings = self.load_p011_findings()
        p012_findings = self.load_p012_findings()
        p013_findings = self.load_p013_findings()
        
        self.findings = p011_findings + p012_findings + p013_findings
        
        print(f"\n📊 Total findings loaded: {len(self.findings)}")
        
        # Calculate metrics
        print("\n🧮 Calculating risk assessment...")
        risk_assessment = self.calculate_risk_score()
        
        print("📈 Calculating compliance metrics...")
        compliance_metrics = self.calculate_compliance_metrics()
        
        print("🗺️  Generating remediation roadmap...")
        remediation_roadmap = self.generate_remediation_roadmap()
        
        print("🎯 Updating SLO status...")
        self.update_slo_status(risk_assessment, compliance_metrics)
        
        # Group findings
        findings_by_source = {
            "P011": [f for f in self.findings if f.source == "P011"],
            "P012": [f for f in self.findings if f.source == "P012"],
            "P013": [f for f in self.findings if f.source == "P013"],
        }
        
        findings_by_severity = {
            "CRITICAL": [f for f in self.findings if f.severity == "CRITICAL"],
            "HIGH": [f for f in self.findings if f.severity == "HIGH"],
            "MEDIUM": [f for f in self.findings if f.severity == "MEDIUM"],
            "LOW": [f for f in self.findings if f.severity == "LOW"],
        }
        
        report = ComplianceReport(
            timestamp=datetime.now().isoformat(),
            risk_assessment=risk_assessment,
            compliance_metrics=compliance_metrics,
            findings_by_source=findings_by_source,
            findings_by_severity=findings_by_severity,
            remediation_roadmap=remediation_roadmap,
            slo_status=self.slos
        )
        
        return report
    
    def export_to_json(self, report: ComplianceReport, output_path: Path):
        """Export report to JSON."""
        data = {
            "timestamp": report.timestamp,
            "risk_assessment": {
                "risk_score": report.risk_assessment.risk_score,
                "risk_level": report.risk_assessment.risk_level,
                "severity_breakdown": {
                    "CRITICAL": report.risk_assessment.critical_count,
                    "HIGH": report.risk_assessment.high_count,
                    "MEDIUM": report.risk_assessment.medium_count,
                    "LOW": report.risk_assessment.low_count,
                },
                "total_findings": report.risk_assessment.total_findings
            },
            "compliance_metrics": {
                "owasp_coverage": report.compliance_metrics.owasp_coverage,
                "owasp_score": report.compliance_metrics.owasp_score,
                "cwe_coverage": report.compliance_metrics.cwe_coverage,
                "nist_controls": report.compliance_metrics.nist_controls,
                "pci_requirements": report.compliance_metrics.pci_requirements
            },
            "findings_summary": {
                source: len(findings)
                for source, findings in report.findings_by_source.items()
            },
            "remediation_roadmap": report.remediation_roadmap,
            "slo_status": report.slo_status
        }
        
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"\n✅ JSON report saved: {output_path}")
    
    def export_to_markdown(self, report: ComplianceReport, output_path: Path):
        """Export report to Markdown."""
        lines = []
        
        # Header
        lines.append("# 🔐 Security Compliance Report")
        lines.append("")
        lines.append(f"**Generated**: {report.timestamp}")
        lines.append(f"**Project**: Agente Hotelero IA")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Executive Summary
        lines.append("## 📊 Executive Summary")
        lines.append("")
        lines.append(f"**Overall Risk Score**: {report.risk_assessment.risk_score}/100")
        lines.append(f"**Risk Level**: {self._get_risk_emoji(report.risk_assessment.risk_level)} **{report.risk_assessment.risk_level}**")
        lines.append(f"**Total Findings**: {report.risk_assessment.total_findings}")
        lines.append("")
        
        # Risk Assessment
        lines.append("### Severity Breakdown")
        lines.append("")
        lines.append("| Severity | Count | Weight | Impact |")
        lines.append("|----------|-------|--------|--------|")
        lines.append(f"| 🔴 **CRITICAL** | {report.risk_assessment.critical_count} | 10 | {report.risk_assessment.critical_count * 10} |")
        lines.append(f"| 🟠 **HIGH** | {report.risk_assessment.high_count} | 5 | {report.risk_assessment.high_count * 5} |")
        lines.append(f"| 🟡 **MEDIUM** | {report.risk_assessment.medium_count} | 2 | {report.risk_assessment.medium_count * 2} |")
        lines.append(f"| 🟢 **LOW** | {report.risk_assessment.low_count} | 1 | {report.risk_assessment.low_count * 1} |")
        lines.append("")
        
        # Compliance Metrics
        lines.append("## 📈 Compliance Metrics")
        lines.append("")
        lines.append("### Standards Coverage")
        lines.append("")
        lines.append("| Standard | Coverage | Score/Status |")
        lines.append("|----------|----------|--------------|")
        lines.append(f"| **OWASP Top 10 2021** | {report.compliance_metrics.owasp_coverage}% | {report.compliance_metrics.owasp_score}/100 |")
        lines.append(f"| **CWE** | {report.compliance_metrics.cwe_coverage} IDs | Mapped |")
        lines.append(f"| **NIST SP 800-53** | {len(report.compliance_metrics.nist_controls)} controls | Partial |")
        lines.append(f"| **PCI-DSS** | {len(report.compliance_metrics.pci_requirements)} reqs | Partial |")
        lines.append("")
        
        # NIST Controls
        if report.compliance_metrics.nist_controls:
            lines.append("#### NIST SP 800-53 Controls")
            lines.append("")
            for control in report.compliance_metrics.nist_controls:
                lines.append(f"- {control}")
            lines.append("")
        
        # PCI Requirements
        if report.compliance_metrics.pci_requirements:
            lines.append("#### PCI-DSS Requirements")
            lines.append("")
            for req in report.compliance_metrics.pci_requirements:
                lines.append(f"- {req}")
            lines.append("")
        
        # Findings by Source
        lines.append("## 🔍 Findings by Source")
        lines.append("")
        lines.append("| Source | Description | Findings |")
        lines.append("|--------|-------------|----------|")
        lines.append(f"| **P011** | Dependency Vulnerabilities | {len(report.findings_by_source['P011'])} |")
        lines.append(f"| **P012** | Hardcoded Secrets | {len(report.findings_by_source['P012'])} |")
        lines.append(f"| **P013** | OWASP Top 10 Compliance | {len(report.findings_by_source['P013'])} |")
        lines.append("")
        
        # Remediation Roadmap
        lines.append("## 🗺️ Remediation Roadmap")
        lines.append("")
        for phase in report.remediation_roadmap:
            emoji = "🔴" if phase["priority"] == "BLOCKER" else "🟠" if phase["priority"] == "HIGH" else "🟡"
            lines.append(f"### {emoji} Phase {phase['phase']}: {phase['name']}")
            lines.append("")
            lines.append(f"**Timeframe**: {phase['timeframe']}")
            lines.append(f"**Priority**: {phase['priority']}")
            lines.append(f"**Findings**: {phase['findings_count']}")
            lines.append(f"**Blocks Deployment**: {'Yes' if phase['blocking_deployment'] else 'No'}")
            lines.append("")
            lines.append("**Actions**:")
            lines.append("")
            for action in phase["actions"]:
                lines.append(f"- {action}")
            lines.append("")
        
        # SLO Status
        lines.append("## 🎯 SLO Status")
        lines.append("")
        lines.append("| SLO | Target | Current | Status |")
        lines.append("|-----|--------|---------|--------|")
        for slo_name, slo_data in report.slo_status.items():
            status_emoji = "✅" if slo_data["status"] == "PASS" else "❌"
            target = f"≤ {slo_data.get('max', 'N/A')}" if "max" in slo_data else f"≥ {slo_data.get('min', 'N/A')}"
            lines.append(f"| {slo_name.replace('_', ' ').title()} | {target} | {slo_data['current']} | {status_emoji} {slo_data['status']} |")
        lines.append("")
        
        # Recommendations
        lines.append("## 💡 Recommendations")
        lines.append("")
        if report.risk_assessment.critical_count > 0:
            lines.append("### 🔴 IMMEDIATE ACTION REQUIRED")
            lines.append("")
            lines.append(f"- **{report.risk_assessment.critical_count} CRITICAL findings** must be fixed before deployment")
            lines.append("- Review Phase 1 of remediation roadmap")
            lines.append("- Execute fixes within 24 hours")
            lines.append("")
        
        if report.risk_assessment.high_count > 5:
            lines.append("### 🟠 HIGH PRIORITY")
            lines.append("")
            lines.append(f"- **{report.risk_assessment.high_count} HIGH findings** exceed SLO (max 5)")
            lines.append("- Plan remediation within current sprint")
            lines.append("")
        
        if report.compliance_metrics.owasp_score < 70:
            lines.append("### 📊 COMPLIANCE GAP")
            lines.append("")
            lines.append(f"- **OWASP compliance score {report.compliance_metrics.owasp_score}/100** below target (70)")
            lines.append("- Focus on top OWASP categories from P013 report")
            lines.append("")
        
        lines.append("---")
        lines.append("")
        lines.append("**Report generated by**: P014 Compliance Report Generator")
        lines.append(f"**Next scan recommended**: {self._get_next_scan_date()}")
        
        with open(output_path, "w") as f:
            f.write("\n".join(lines))
        
        print(f"✅ Markdown report saved: {output_path}")
    
    def _get_risk_emoji(self, risk_level: str) -> str:
        """Get emoji for risk level."""
        emojis = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢"
        }
        return emojis.get(risk_level, "⚪")
    
    def _get_next_scan_date(self) -> str:
        """Calculate next recommended scan date."""
        from datetime import timedelta
        next_scan = datetime.now() + timedelta(days=7)
        return next_scan.strftime("%Y-%m-%d")
    
    def print_summary(self, report: ComplianceReport):
        """Print summary to console."""
        print("\n" + "=" * 70)
        print("📊 COMPLIANCE REPORT SUMMARY")
        print("=" * 70)
        
        print(f"\n🎯 Overall Risk Score: {report.risk_assessment.risk_score}/100")
        print(f"⚠️  Risk Level: {report.risk_assessment.risk_level}")
        print(f"🔍 Total Findings: {report.risk_assessment.total_findings}")
        
        print("\n📊 Severity Breakdown:")
        print(f"   • CRITICAL: {report.risk_assessment.critical_count}")
        print(f"   • HIGH: {report.risk_assessment.high_count}")
        print(f"   • MEDIUM: {report.risk_assessment.medium_count}")
        print(f"   • LOW: {report.risk_assessment.low_count}")
        
        print("\n📈 Compliance Metrics:")
        print(f"   • OWASP Score: {report.compliance_metrics.owasp_score}/100")
        print(f"   • CWE Coverage: {report.compliance_metrics.cwe_coverage} IDs")
        print(f"   • NIST Controls: {len(report.compliance_metrics.nist_controls)}")
        print(f"   • PCI Requirements: {len(report.compliance_metrics.pci_requirements)}")
        
        print("\n🗺️ Remediation Roadmap:")
        for phase in report.remediation_roadmap:
            print(f"   Phase {phase['phase']}: {phase['findings_count']} findings ({phase['timeframe']})")
        
        print("\n🎯 SLO Status:")
        for slo_name, slo_data in report.slo_status.items():
            status = "✅ PASS" if slo_data["status"] == "PASS" else "❌ FAIL"
            print(f"   {slo_name}: {slo_data['current']} {status}")
        
        print("\n" + "=" * 70)


def main():
    """Main execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate compliance report")
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "both"],
        default="both",
        help="Output format"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (optional)"
    )
    
    args = parser.parse_args()
    
    # Determine project root
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent.parent
    
    # Generate report
    generator = ComplianceReportGenerator(project_root)
    report = generator.generate_report()
    
    # Print summary
    generator.print_summary(report)
    
    # Export
    security_dir = project_root / ".security"
    security_dir.mkdir(exist_ok=True)
    
    if args.format in ["json", "both"]:
        json_path = Path(args.output) if args.output else security_dir / "compliance-report-latest.json"
        generator.export_to_json(report, json_path)
    
    if args.format in ["markdown", "both"]:
        md_path = security_dir / "compliance-report-latest.md"
        generator.export_to_markdown(report, md_path)
    
    # Exit code based on risk level
    exit_codes = {
        "LOW": 0,
        "MEDIUM": 0,
        "HIGH": 1,
        "CRITICAL": 2
    }
    
    exit_code = exit_codes.get(report.risk_assessment.risk_level, 2)
    
    if exit_code > 0:
        print(f"\n⚠️  Exiting with code {exit_code} ({report.risk_assessment.risk_level} risk)")
    
    return exit_code


if __name__ == "__main__":
    import sys
    sys.exit(main())
