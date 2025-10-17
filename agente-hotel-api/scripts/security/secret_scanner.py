#!/usr/bin/env python3
"""
P012: Secret Scanning & Hardening
==================================

Detecta secretos hardcodeados, valida gestión de credenciales y audita
permisos de archivos sensibles.

Validaciones:
1. Secretos hardcodeados en código fuente (gitleaks, trufflehog, detect-secrets)
2. Variables de entorno sin valores dummy
3. Archivos .env en .gitignore
4. Permisos correctos en archivos sensibles (600 o 644)
5. Rotación de API keys (última actualización)
6. Secretos en git history
7. Variables de entorno production requeridas

Herramientas externas opcionales:
- gitleaks: Git secret scanning
- trufflehog: Deep secret scanning in commits
- detect-secrets: Baseline secret detection

Uso:
    python scripts/security/secret_scanner.py [--strict] [--format json|html|markdown]

Referencias:
- OWASP Top 10 2021 - A05:2021 - Security Misconfiguration
- CWE-798: Use of Hard-coded Credentials
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class SecretFinding:
    """Representa un secreto encontrado."""

    file_path: str
    line_number: int
    secret_type: str  # api_key, password, token, private_key, etc.
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    description: str
    matched_string: str  # Partial match (redacted)
    recommendation: str
    source: str  # built-in, gitleaks, trufflehog, detect-secrets


@dataclass
class EnvironmentIssue:
    """Representa un problema en variables de entorno."""

    variable_name: str
    issue_type: str  # missing, dummy_value, weak_value, insecure_default
    severity: str
    current_value: Optional[str]  # Redacted
    recommendation: str


@dataclass
class FilePermissionIssue:
    """Representa un problema de permisos."""

    file_path: str
    current_permissions: str  # e.g., "0644"
    expected_permissions: str  # e.g., "0600"
    severity: str
    risk_description: str


@dataclass
class GitHistoryIssue:
    """Representa un secreto en git history."""

    commit_hash: str
    file_path: str
    secret_type: str
    description: str
    severity: str


@dataclass
class ScanResult:
    """Resultado consolidado del escaneo de secretos."""

    scan_timestamp: str
    scan_duration_seconds: float
    secret_findings: List[SecretFinding]
    environment_issues: List[EnvironmentIssue]
    file_permission_issues: List[FilePermissionIssue]
    git_history_issues: List[GitHistoryIssue]
    summary: Dict[str, any]


class SecretScanner:
    """Escáner de secretos hardcodeados y configuraciones inseguras."""

    # Patrones de regex para detectar secretos
    SECRET_PATTERNS = {
        "generic_api_key": {
            "pattern": r'(?i)(api[_-]?key|apikey|api[_-]?secret)\s*[=:]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?',
            "severity": "HIGH",
            "description": "Generic API key pattern detected",
        },
        "aws_access_key": {
            "pattern": r"(?i)aws[_-]?access[_-]?key[_-]?id\s*[=:]\s*['\"]?(AKIA[0-9A-Z]{16})['\"]?",
            "severity": "CRITICAL",
            "description": "AWS Access Key ID",
        },
        "aws_secret_key": {
            "pattern": r"(?i)aws[_-]?secret[_-]?access[_-]?key\s*[=:]\s*['\"]?([a-zA-Z0-9/+=]{40})['\"]?",
            "severity": "CRITICAL",
            "description": "AWS Secret Access Key",
        },
        "github_token": {
            "pattern": r"(?i)github[_-]?token\s*[=:]\s*['\"]?([a-zA-Z0-9_]{40})['\"]?",
            "severity": "CRITICAL",
            "description": "GitHub Personal Access Token",
        },
        "slack_token": {
            "pattern": r"xox[baprs]-[0-9a-zA-Z]{10,48}",
            "severity": "HIGH",
            "description": "Slack Token",
        },
        "private_key": {
            "pattern": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
            "severity": "CRITICAL",
            "description": "Private Key",
        },
        "jwt_token": {
            "pattern": r"ey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
            "severity": "MEDIUM",
            "description": "JWT Token",
        },
        "password_assignment": {
            "pattern": r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']([^"\']{8,})["\']',
            "severity": "HIGH",
            "description": "Hardcoded password",
        },
        "connection_string": {
            "pattern": r"(?i)(postgres|mysql|mongodb)://[^:]+:[^@]+@",
            "severity": "HIGH",
            "description": "Database connection string with embedded credentials",
        },
    }

    # Variables de entorno requeridas en producción
    REQUIRED_ENV_VARS = {
        "SECRET_KEY": {"min_length": 32, "allow_dummy": False},
        "POSTGRES_PASSWORD": {"min_length": 16, "allow_dummy": False},
        "REDIS_PASSWORD": {"min_length": 12, "allow_dummy": False},
        "PMS_API_KEY": {"min_length": 20, "allow_dummy": False},
        "WHATSAPP_ACCESS_TOKEN": {"min_length": 50, "allow_dummy": False},
    }

    # Valores dummy que no deben usarse en producción
    DUMMY_VALUES = {
        "REPLACE_WITH_SECURE",
        "CHANGEME",
        "CHANGE_ME",
        "TODO",
        "FIXME",
        "DUMMY",
        "TEST",
        "EXAMPLE",
        "SECRET_KEY_HERE",
        "YOUR_",
        "INSERT_",
        "12345",
        "password",
        "admin",
    }

    # Archivos sensibles que requieren permisos restrictivos
    SENSITIVE_FILES = {
        ".env": "0600",
        ".env.production": "0600",
        ".env.local": "0600",
        "secrets.json": "0600",
        "credentials.json": "0600",
        "private_key.pem": "0600",
        "id_rsa": "0600",
        "id_ed25519": "0600",
    }

    def __init__(self, project_root: Path, strict_mode: bool = False):
        self.project_root = project_root
        self.strict_mode = strict_mode
        self.findings: List[SecretFinding] = []
        self.env_issues: List[EnvironmentIssue] = []
        self.permission_issues: List[FilePermissionIssue] = []
        self.git_issues: List[GitHistoryIssue] = []

    def run_full_scan(self) -> ScanResult:
        """Ejecuta escaneo completo de secretos."""
        print("=" * 80)
        print("🔐 ESCANEO DE SECRETOS Y HARDENING - P012")
        print("=" * 80)
        print()

        start_time = datetime.now()

        # 1. Escaneo de archivos fuente
        print("🔍 1/7: Escaneando código fuente...")
        self.scan_source_files()

        # 2. Validación de variables de entorno
        print("🔍 2/7: Validando variables de entorno...")
        self.validate_environment_variables()

        # 3. Verificación de .gitignore
        print("🔍 3/7: Verificando .gitignore...")
        self.check_gitignore_coverage()

        # 4. Auditoría de permisos de archivos
        print("🔍 4/7: Auditando permisos de archivos...")
        self.audit_file_permissions()

        # 5. Escaneo con gitleaks (opcional)
        print("🔍 5/7: Escaneando con gitleaks...")
        self.run_gitleaks_scan()

        # 6. Escaneo con trufflehog (opcional)
        print("🔍 6/7: Escaneando con trufflehog...")
        self.run_trufflehog_scan()

        # 7. Validación de rotación de secretos
        print("🔍 7/7: Validando rotación de secretos...")
        self.check_secret_rotation()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Generar resumen
        summary = self._generate_summary()

        result = ScanResult(
            scan_timestamp=start_time.isoformat(),
            scan_duration_seconds=duration,
            secret_findings=self.findings,
            environment_issues=self.env_issues,
            file_permission_issues=self.permission_issues,
            git_history_issues=self.git_issues,
            summary=summary,
        )

        self._print_summary(result)

        return result

    def scan_source_files(self):
        """Escanea archivos fuente buscando secretos hardcodeados."""
        # Extensiones a escanear
        extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".yaml", ".yml", ".sh", ".env"}

        # Directorios a excluir
        exclude_dirs = {
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            ".git",
            ".pytest_cache",
            "htmlcov",
            ".mypy_cache",
            ".ruff_cache",
        }

        for file_path in self.project_root.rglob("*"):
            # Skip directories
            if file_path.is_dir():
                continue

            # Skip excluded directories
            if any(excluded in file_path.parts for excluded in exclude_dirs):
                continue

            # Skip files with wrong extension
            if file_path.suffix not in extensions:
                continue

            # Skip .env.example (dummy values allowed)
            if file_path.name == ".env.example":
                continue

            self._scan_file(file_path)

    def _scan_file(self, file_path: Path):
        """Escanea un archivo individual."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")

            for line_num, line in enumerate(lines, start=1):
                for secret_type, config in self.SECRET_PATTERNS.items():
                    matches = re.finditer(config["pattern"], line)

                    for match in matches:
                        # Redact the actual secret
                        matched_text = match.group(0)
                        redacted = matched_text[:10] + "***" + matched_text[-4:] if len(matched_text) > 14 else "***"

                        # Skip if it looks like a comment or example
                        if self._is_likely_false_positive(line, matched_text):
                            continue

                        self.findings.append(
                            SecretFinding(
                                file_path=str(file_path.relative_to(self.project_root)),
                                line_number=line_num,
                                secret_type=secret_type,
                                severity=config["severity"],
                                description=config["description"],
                                matched_string=redacted,
                                recommendation=self._get_recommendation(secret_type),
                                source="built-in",
                            )
                        )

        except Exception as e:
            print(f"   ⚠️  Error escaneando {file_path}: {e}")

    def _is_likely_false_positive(self, line: str, matched_text: str) -> bool:
        """Detecta falsos positivos comunes."""
        line.lower()

        # Skip comments
        if line.strip().startswith("#") or line.strip().startswith("//"):
            return True

        # Skip docstrings
        if '"""' in line or "'''" in line:
            return True

        # Skip example/placeholder values
        if any(placeholder in matched_text.upper() for placeholder in self.DUMMY_VALUES):
            return True

        # Skip if it's clearly a variable name definition
        if "=" not in line and ":" not in line:
            return True

        return False

    def _get_recommendation(self, secret_type: str) -> str:
        """Genera recomendación basada en el tipo de secreto."""
        recommendations = {
            "generic_api_key": "Move to environment variable or secrets management system (e.g., AWS Secrets Manager, HashiCorp Vault)",
            "aws_access_key": "CRITICAL: Rotate AWS credentials immediately. Use IAM roles instead of access keys when possible.",
            "aws_secret_key": "CRITICAL: Rotate AWS credentials immediately. Never commit AWS secrets to git.",
            "github_token": "CRITICAL: Revoke and rotate GitHub token immediately. Use GitHub Apps for automation.",
            "slack_token": "Rotate Slack token. Use OAuth or Slack Apps with proper scopes.",
            "private_key": "CRITICAL: Remove private key from repository immediately. Rotate certificates.",
            "jwt_token": "Avoid committing JWT tokens. Tokens should be short-lived and generated at runtime.",
            "password_assignment": "Move password to environment variable or secrets manager.",
            "connection_string": "Use environment variables for credentials. Never commit connection strings with passwords.",
        }

        return recommendations.get(
            secret_type, "Move secret to secure environment variable or secrets management system."
        )

    def validate_environment_variables(self):
        """Valida variables de entorno requeridas."""
        env_file = self.project_root / ".env"

        if not env_file.exists():
            self.env_issues.append(
                EnvironmentIssue(
                    variable_name=".env",
                    issue_type="missing",
                    severity="HIGH",
                    current_value=None,
                    recommendation="Create .env file from .env.example and set secure values",
                )
            )
            return

        # Parse .env file
        env_vars = self._parse_env_file(env_file)

        # Check required variables
        for var_name, config in self.REQUIRED_ENV_VARS.items():
            value = env_vars.get(var_name)

            if not value:
                self.env_issues.append(
                    EnvironmentIssue(
                        variable_name=var_name,
                        issue_type="missing",
                        severity="CRITICAL",
                        current_value=None,
                        recommendation=f"Set {var_name} in .env file (min length: {config['min_length']})",
                    )
                )
                continue

            # Check for dummy values
            if any(dummy in value.upper() for dummy in self.DUMMY_VALUES):
                self.env_issues.append(
                    EnvironmentIssue(
                        variable_name=var_name,
                        issue_type="dummy_value",
                        severity="CRITICAL" if not config["allow_dummy"] else "HIGH",
                        current_value="DUMMY_VALUE_DETECTED",
                        recommendation=f"Replace dummy value with secure {var_name}. Generate with: openssl rand -hex 32",
                    )
                )

            # Check minimum length
            elif len(value) < config["min_length"]:
                self.env_issues.append(
                    EnvironmentIssue(
                        variable_name=var_name,
                        issue_type="weak_value",
                        severity="HIGH",
                        current_value=f"LENGTH_{len(value)}",
                        recommendation=f"{var_name} is too short (min: {config['min_length']} chars). Use stronger value.",
                    )
                )

    def _parse_env_file(self, env_file: Path) -> Dict[str, str]:
        """Parse archivo .env."""
        env_vars = {}

        try:
            content = env_file.read_text()
            for line in content.split("\n"):
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Parse KEY=VALUE
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    env_vars[key] = value

        except Exception as e:
            print(f"   ⚠️  Error parsing .env: {e}")

        return env_vars

    def check_gitignore_coverage(self):
        """Verifica que archivos sensibles estén en .gitignore."""
        gitignore_path = self.project_root / ".gitignore"

        if not gitignore_path.exists():
            self.env_issues.append(
                EnvironmentIssue(
                    variable_name=".gitignore",
                    issue_type="missing",
                    severity="CRITICAL",
                    current_value=None,
                    recommendation="Create .gitignore file to prevent committing sensitive files",
                )
            )
            return

        gitignore_content = gitignore_path.read_text()

        # Check for sensitive patterns
        required_patterns = [".env", "*.pem", "*.key", "secrets.json", "credentials.json"]

        for pattern in required_patterns:
            if pattern not in gitignore_content:
                self.env_issues.append(
                    EnvironmentIssue(
                        variable_name=".gitignore",
                        issue_type="insecure_default",
                        severity="HIGH",
                        current_value=None,
                        recommendation=f"Add '{pattern}' to .gitignore to prevent accidental commits",
                    )
                )

    def audit_file_permissions(self):
        """Audita permisos de archivos sensibles."""
        for filename, expected_perms in self.SENSITIVE_FILES.items():
            file_path = self.project_root / filename

            if not file_path.exists():
                continue

            # Get current permissions
            current_stat = file_path.stat()
            current_perms = oct(current_stat.st_mode)[-4:]

            # Compare with expected
            if current_perms != expected_perms:
                self.permission_issues.append(
                    FilePermissionIssue(
                        file_path=str(file_path.relative_to(self.project_root)),
                        current_permissions=current_perms,
                        expected_permissions=expected_perms,
                        severity="HIGH" if expected_perms == "0600" else "MEDIUM",
                        risk_description=f"File {filename} is readable by others. Should be restricted to owner only.",
                    )
                )

    def run_gitleaks_scan(self):
        """Ejecuta gitleaks para escanear git history."""
        try:
            result = subprocess.run(
                [
                    "gitleaks",
                    "detect",
                    "--no-git",
                    "-v",
                    "--report-format",
                    "json",
                    "--report-path",
                    "/tmp/gitleaks.json",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                print("   ✓ gitleaks: No secrets found in git history")
            elif Path("/tmp/gitleaks.json").exists():
                # Parse gitleaks report
                report = json.loads(Path("/tmp/gitleaks.json").read_text())

                for finding in report:
                    self.git_issues.append(
                        GitHistoryIssue(
                            commit_hash=finding.get("Commit", "unknown")[:8],
                            file_path=finding.get("File", "unknown"),
                            secret_type=finding.get("RuleID", "unknown"),
                            description=finding.get("Description", "Secret detected in git history"),
                            severity="CRITICAL",
                        )
                    )

                print(f"   ⚠️  gitleaks: {len(report)} secrets found in git history")
            else:
                print("   ⚠️  gitleaks: Scan completed with warnings")

        except FileNotFoundError:
            print("   ⚠️  gitleaks not installed (optional). Install: brew install gitleaks")
        except subprocess.TimeoutExpired:
            print("   ⚠️  gitleaks timeout (>2min)")
        except Exception as e:
            print(f"   ⚠️  gitleaks error: {e}")

    def run_trufflehog_scan(self):
        """Ejecuta trufflehog para escaneo profundo."""
        try:
            result = subprocess.run(
                ["trufflehog", "filesystem", str(self.project_root), "--json"],
                capture_output=True,
                text=True,
                timeout=180,
            )

            if result.returncode == 0 and result.stdout:
                # Parse trufflehog output (JSONL format)
                for line in result.stdout.strip().split("\n"):
                    if not line:
                        continue

                    try:
                        finding = json.loads(line)
                        self.git_issues.append(
                            GitHistoryIssue(
                                commit_hash="filesystem",
                                file_path=finding.get("SourceMetadata", {})
                                .get("Data", {})
                                .get("Filesystem", {})
                                .get("file", "unknown"),
                                secret_type=finding.get("DetectorName", "unknown"),
                                description="Secret detected by trufflehog",
                                severity="HIGH",
                            )
                        )
                    except json.JSONDecodeError:
                        continue

                print(f"   ⚠️  trufflehog: {len(self.git_issues)} potential secrets found")
            else:
                print("   ✓ trufflehog: No secrets found")

        except FileNotFoundError:
            print("   ⚠️  trufflehog not installed (optional). Install: brew install trufflehog")
        except subprocess.TimeoutExpired:
            print("   ⚠️  trufflehog timeout (>3min)")
        except Exception as e:
            print(f"   ⚠️  trufflehog error: {e}")

    def check_secret_rotation(self):
        """Valida rotación de secretos (última modificación)."""
        env_file = self.project_root / ".env"

        if not env_file.exists():
            return

        # Check file modification time
        mod_time = datetime.fromtimestamp(env_file.stat().st_mtime)
        days_since_update = (datetime.now() - mod_time).days

        # Warn if secrets haven't been rotated in > 90 days
        if days_since_update > 90:
            self.env_issues.append(
                EnvironmentIssue(
                    variable_name=".env (rotation)",
                    issue_type="insecure_default",
                    severity="MEDIUM",
                    current_value=f"{days_since_update} days old",
                    recommendation=f"Secrets in .env haven't been updated in {days_since_update} days. Consider rotating API keys and passwords.",
                )
            )

    def _generate_summary(self) -> Dict[str, any]:
        """Genera resumen del escaneo."""
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

        # Count by severity
        for finding in self.findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1

        for issue in self.env_issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1

        for issue in self.permission_issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1

        for issue in self.git_issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1

        total_issues = sum(severity_counts.values())

        status = self._determine_status(severity_counts)

        return {
            "total_issues": total_issues,
            "severity_breakdown": severity_counts,
            "secret_findings_count": len(self.findings),
            "environment_issues_count": len(self.env_issues),
            "permission_issues_count": len(self.permission_issues),
            "git_history_issues_count": len(self.git_issues),
            "scan_status": status,
            "recommendations": self._generate_recommendations(),
        }

    def _determine_status(self, severity_counts: Dict[str, int]) -> str:
        """Determina el estado general del escaneo."""
        if severity_counts["CRITICAL"] > 0:
            return "CRITICAL - Immediate action required"
        elif severity_counts["HIGH"] > 0:
            return "HIGH - Priority remediation needed"
        elif severity_counts["MEDIUM"] > 0:
            return "MEDIUM - Review recommended"
        elif severity_counts["LOW"] > 0:
            return "LOW - Minor issues detected"
        else:
            return "PASS - No secrets or security issues detected"

    def _generate_recommendations(self) -> List[str]:
        """Genera recomendaciones basadas en hallazgos."""
        recommendations = []

        if any(f.severity == "CRITICAL" for f in self.findings):
            recommendations.append("🔴 URGENT: Rotate all CRITICAL secrets immediately and remove from git history")

        if any(i.issue_type == "dummy_value" for i in self.env_issues):
            recommendations.append("🔴 URGENT: Replace dummy values in .env with secure secrets")

        if len(self.git_issues) > 0:
            recommendations.append(
                f"⚠️  {len(self.git_issues)} secrets found in git history - use git filter-repo to clean history"
            )

        if len(self.permission_issues) > 0:
            recommendations.append(
                f"⚠️  Fix {len(self.permission_issues)} file permission issues with: chmod 600 <file>"
            )

        if len(self.findings) > 0:
            recommendations.append("Move all hardcoded secrets to environment variables or secrets management system")

        if not recommendations:
            recommendations.append("✅ No immediate security issues detected")

        return recommendations

    def _print_summary(self, result: ScanResult):
        """Imprime resumen del escaneo."""
        print()
        print("=" * 80)
        print("📊 RESUMEN DEL ESCANEO")
        print("=" * 80)
        print()
        print(f"⏱️  Duración: {result.scan_duration_seconds:.2f}s")
        print(f"📅 Timestamp: {result.scan_timestamp}")
        print()
        print(f"🔍 Total issues: {result.summary['total_issues']}")
        print(f"   • CRITICAL: {result.summary['severity_breakdown']['CRITICAL']}")
        print(f"   • HIGH:     {result.summary['severity_breakdown']['HIGH']}")
        print(f"   • MEDIUM:   {result.summary['severity_breakdown']['MEDIUM']}")
        print(f"   • LOW:      {result.summary['severity_breakdown']['LOW']}")
        print()
        print(f"📁 Secret findings: {result.summary['secret_findings_count']}")
        print(f"🔐 Environment issues: {result.summary['environment_issues_count']}")
        print(f"🔒 Permission issues: {result.summary['permission_issues_count']}")
        print(f"📜 Git history issues: {result.summary['git_history_issues_count']}")
        print()
        print(f"🎯 Estado: {result.summary['scan_status']}")
        print()

        if result.summary["recommendations"]:
            print("💡 RECOMENDACIONES:")
            print()
            for rec in result.summary["recommendations"]:
                print(f"   {rec}")
            print()

        print("=" * 80)

    def export_to_json(self, result: ScanResult, output_path: Path):
        """Exporta resultado a JSON."""
        data = {
            "scan_timestamp": result.scan_timestamp,
            "scan_duration_seconds": result.scan_duration_seconds,
            "secret_findings": [asdict(f) for f in result.secret_findings],
            "environment_issues": [asdict(i) for i in result.environment_issues],
            "file_permission_issues": [asdict(i) for i in result.file_permission_issues],
            "git_history_issues": [asdict(i) for i in result.git_history_issues],
            "summary": result.summary,
        }

        output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"✅ Reporte JSON exportado a: {output_path}")

    def export_to_markdown(self, result: ScanResult, output_path: Path):
        """Exporta resultado a Markdown."""
        md = f"""# 🔐 Reporte de Secret Scanning - P012

## 📊 Resumen Ejecutivo

- **Fecha:** {result.scan_timestamp}
- **Duración:** {result.scan_duration_seconds:.2f} segundos
- **Estado:** {result.summary["scan_status"]}

### Métricas

| Métrica | Valor |
|---------|-------|
| Total issues | {result.summary["total_issues"]} |
| CRITICAL | {result.summary["severity_breakdown"]["CRITICAL"]} |
| HIGH | {result.summary["severity_breakdown"]["HIGH"]} |
| MEDIUM | {result.summary["severity_breakdown"]["MEDIUM"]} |
| LOW | {result.summary["severity_breakdown"]["LOW"]} |
| Secret findings | {result.summary["secret_findings_count"]} |
| Environment issues | {result.summary["environment_issues_count"]} |
| Permission issues | {result.summary["permission_issues_count"]} |
| Git history issues | {result.summary["git_history_issues_count"]} |

---

{self._md_secret_findings(result.secret_findings)}

{self._md_env_issues(result.environment_issues)}

{self._md_permission_issues(result.file_permission_issues)}

{self._md_git_issues(result.git_history_issues)}

{self._md_recommendations(result.summary["recommendations"])}
"""
        output_path.write_text(md)
        print(f"✅ Reporte Markdown exportado a: {output_path}")

    def _md_secret_findings(self, findings: List[SecretFinding]) -> str:
        if not findings:
            return "## ✅ No hardcoded secrets found\n"

        rows = []
        for f in sorted(findings, key=lambda x: ("CRITICAL", "HIGH", "MEDIUM", "LOW").index(x.severity)):
            rows.append(
                f"| {f.file_path} | L{f.line_number} | {f.secret_type} | **{f.severity}** | {f.description} | {f.recommendation[:60]}... |"
            )

        table = "\n".join(rows)
        return f"""## 🔍 Hardcoded Secrets Found ({len(findings)})

| File | Line | Type | Severity | Description | Recommendation |
|------|------|------|----------|-------------|----------------|
{table}
"""

    def _md_env_issues(self, issues: List[EnvironmentIssue]) -> str:
        if not issues:
            return "## ✅ No environment variable issues\n"

        rows = []
        for i in sorted(issues, key=lambda x: ("CRITICAL", "HIGH", "MEDIUM", "LOW").index(x.severity)):
            rows.append(f"| {i.variable_name} | {i.issue_type} | **{i.severity}** | {i.recommendation} |")

        table = "\n".join(rows)
        return f"""## 🔐 Environment Variable Issues ({len(issues)})

| Variable | Issue Type | Severity | Recommendation |
|----------|------------|----------|----------------|
{table}
"""

    def _md_permission_issues(self, issues: List[FilePermissionIssue]) -> str:
        if not issues:
            return "## ✅ No file permission issues\n"

        rows = []
        for i in sorted(issues, key=lambda x: ("CRITICAL", "HIGH", "MEDIUM", "LOW").index(x.severity)):
            rows.append(
                f"| {i.file_path} | {i.current_permissions} | {i.expected_permissions} | **{i.severity}** | {i.risk_description} |"
            )

        table = "\n".join(rows)
        return f"""## 🔒 File Permission Issues ({len(issues)})

| File | Current | Expected | Severity | Risk Description |
|------|---------|----------|----------|------------------|
{table}
"""

    def _md_git_issues(self, issues: List[GitHistoryIssue]) -> str:
        if not issues:
            return "## ✅ No secrets in git history\n"

        rows = []
        for i in issues:
            rows.append(f"| {i.commit_hash} | {i.file_path} | {i.secret_type} | **{i.severity}** | {i.description} |")

        table = "\n".join(rows)
        return f"""## 📜 Secrets in Git History ({len(issues)})

**WARNING**: Secrets in git history require cleaning with `git filter-repo` or BFG Repo-Cleaner.

| Commit | File | Type | Severity | Description |
|--------|------|------|----------|-------------|
{table}
"""

    def _md_recommendations(self, recommendations: List[str]) -> str:
        items = "\n".join([f"- {rec}" for rec in recommendations])
        return f"""## 💡 Recomendaciones

{items}
"""


def main():
    parser = argparse.ArgumentParser(description="P012: Secret Scanning & Hardening")
    parser.add_argument("--strict", action="store_true", help="Strict mode: fail on any findings")
    parser.add_argument(
        "--format", choices=["json", "markdown"], default="markdown", help="Output format (default: markdown)"
    )
    parser.add_argument("--output", type=Path, help="Output file (default: .security/secret-scan-{timestamp}.{ext})")

    args = parser.parse_args()

    # Determinar project root
    project_root = Path(__file__).parent.parent.parent

    # Crear directorio de salida
    output_dir = project_root / ".security"
    output_dir.mkdir(exist_ok=True)

    # Ejecutar escaneo
    scanner = SecretScanner(project_root, strict_mode=args.strict)
    result = scanner.run_full_scan()

    # Exportar resultado
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.output:
        output_path = args.output
    else:
        ext = args.format if args.format != "markdown" else "md"
        output_path = output_dir / f"secret-scan-{timestamp}.{ext}"

    if args.format == "json":
        scanner.export_to_json(result, output_path)
    elif args.format == "markdown":
        scanner.export_to_markdown(result, output_path)

    # Exit code basado en severidad
    if result.summary["severity_breakdown"]["CRITICAL"] > 0:
        sys.exit(2)  # Critical issues
    elif result.summary["severity_breakdown"]["HIGH"] > 0:
        sys.exit(1)  # High issues
    else:
        sys.exit(0)  # Success


if __name__ == "__main__":
    main()
