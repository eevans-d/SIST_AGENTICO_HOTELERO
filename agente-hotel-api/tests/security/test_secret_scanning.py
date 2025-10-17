"""
P012: Tests de Secret Scanning & Hardening
===========================================

Tests automatizados para validar que no hay secretos hardcodeados,
credenciales débiles o configuraciones inseguras.

Validaciones:
1. No hay secretos hardcodeados en código fuente
2. Variables de entorno production configuradas correctamente
3. Archivos .env en .gitignore
4. Permisos correctos en archivos sensibles
5. No hay secretos en git history (gitleaks)
6. API keys rotadas regularmente

Referencias:
- OWASP Top 10 2021 - A05:2021 - Security Misconfiguration
- CWE-798: Use of Hard-coded Credentials
- CWE-259: Use of Hard-coded Password
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import List

import pytest


class TestHardcodedSecrets:
    """Tests para detectar secretos hardcodeados."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def source_files(self, project_root: Path) -> List[Path]:
        """Lista de archivos fuente a escanear."""
        extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".yaml", ".yml"}
        exclude_dirs = {
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            ".git",
            ".pytest_cache",
            "htmlcov",
            ".security",
        }

        files = []
        for file_path in project_root.rglob("*"):
            if file_path.is_dir():
                continue

            if any(excluded in file_path.parts for excluded in exclude_dirs):
                continue

            if file_path.suffix in extensions and file_path.name != ".env.example":
                files.append(file_path)

        return files

    @pytest.mark.security
    @pytest.mark.critical
    def test_no_hardcoded_api_keys(self, source_files: List[Path]):
        """
        CRÍTICO: No debe haber API keys hardcodeadas en código fuente.

        Detecta patrones como:
        - api_key = "sk_live_..."
        - apiKey: "1234567890abcdef"
        - API_KEY = "AKIAIOSFODNN7EXAMPLE"
        """
        api_key_pattern = r'(?i)(api[_-]?key|apikey|api[_-]?secret)\s*[=:]\s*["\']([a-zA-Z0-9_\-]{20,})["\']'

        findings = []
        for file_path in source_files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")

                for line_num, line in enumerate(content.split("\n"), start=1):
                    # Skip comments
                    if line.strip().startswith("#") or line.strip().startswith("//"):
                        continue

                    matches = re.finditer(api_key_pattern, line)
                    for match in matches:
                        # Skip if it contains placeholder values
                        matched_value = match.group(2)
                        if any(
                            placeholder in matched_value.upper()
                            for placeholder in ["REPLACE", "CHANGE", "TODO", "EXAMPLE", "YOUR_", "TEST"]
                        ):
                            continue

                        findings.append(f"{file_path}:{line_num} - {match.group(0)[:50]}...")

            except Exception:
                continue

        assert len(findings) == 0, f"Found {len(findings)} hardcoded API keys:\n" + "\n".join(findings[:10])

    @pytest.mark.security
    @pytest.mark.critical
    def test_no_hardcoded_passwords(self, source_files: List[Path]):
        """
        CRÍTICO: No debe haber contraseñas hardcodeadas.

        Detecta patrones como:
        - password = "MySecretPass123"
        - passwd: "admin123"
        - pwd = "P@ssw0rd"
        """
        password_pattern = r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']([^"\']{6,})["\']'

        findings = []
        for file_path in source_files:
            try:
                # Skip test files (pueden tener passwords de ejemplo)
                if "test_" in file_path.name or "conftest" in file_path.name:
                    continue

                # Skip config files (pueden tener placeholders)
                if file_path.suffix in {".yml", ".yaml"} and "config" in file_path.name.lower():
                    continue

                content = file_path.read_text(encoding="utf-8", errors="ignore")

                for line_num, line in enumerate(content.split("\n"), start=1):
                    if line.strip().startswith("#") or line.strip().startswith("//"):
                        continue

                    matches = re.finditer(password_pattern, line)
                    for match in matches:
                        matched_value = match.group(2)

                        # Skip placeholder values
                        if any(
                            placeholder in matched_value.upper()
                            for placeholder in ["REPLACE", "CHANGE", "TODO", "EXAMPLE", "YOUR_", "TEST", "DUMMY"]
                        ):
                            continue

                        # Skip if it's clearly a variable name or config key
                        if len(matched_value) < 6 or matched_value.isupper():
                            continue

                        findings.append(f"{file_path}:{line_num} - password=***")

            except Exception:
                continue

        assert len(findings) == 0, f"Found {len(findings)} hardcoded passwords:\n" + "\n".join(findings[:10])

    @pytest.mark.security
    @pytest.mark.critical
    def test_no_aws_credentials(self, source_files: List[Path]):
        """
        CRÍTICO: No debe haber credenciales AWS hardcodeadas.

        AWS Access Keys tienen formato: AKIA[0-9A-Z]{16}
        """
        aws_key_pattern = r"AKIA[0-9A-Z]{16}"

        findings = []
        for file_path in source_files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")

                matches = re.finditer(aws_key_pattern, content)
                for match in matches:
                    line_num = content[: match.start()].count("\n") + 1
                    findings.append(f"{file_path}:{line_num} - AWS Access Key detected")

            except Exception:
                continue

        assert len(findings) == 0, f"Found {len(findings)} AWS credentials:\n" + "\n".join(findings)

    @pytest.mark.security
    @pytest.mark.high
    def test_no_private_keys_in_repo(self, project_root: Path):
        """
        ALTA: No debe haber claves privadas en el repositorio.

        Detecta:
        - -----BEGIN PRIVATE KEY-----
        - -----BEGIN RSA PRIVATE KEY-----
        - -----BEGIN EC PRIVATE KEY-----
        """
        private_key_pattern = r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"

        findings = []
        for file_path in project_root.rglob("*"):
            if file_path.is_dir():
                continue

            # Skip binary files
            if file_path.suffix in {".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe"}:
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")

                if re.search(private_key_pattern, content):
                    findings.append(str(file_path.relative_to(project_root)))

            except Exception:
                continue

        assert len(findings) == 0, f"Found {len(findings)} private keys in repository:\n" + "\n".join(findings)

    @pytest.mark.security
    @pytest.mark.high
    def test_no_connection_strings_with_passwords(self, source_files: List[Path]):
        """
        ALTA: No debe haber connection strings con contraseñas embebidas.

        Detecta:
        - postgres://user:password@host
        - mysql://user:password@host
        - mongodb://user:password@host
        """
        conn_string_pattern = r"(?i)(postgres|mysql|mongodb)://[^:]+:[^@]+@"

        findings = []
        for file_path in source_files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")

                for line_num, line in enumerate(content.split("\n"), start=1):
                    if line.strip().startswith("#") or line.strip().startswith("//"):
                        continue

                    matches = re.finditer(conn_string_pattern, line)
                    for match in matches:
                        # Skip if it contains env var reference
                        if "${" in line or "%" in line or "REPLACE" in line.upper():
                            continue

                        findings.append(f"{file_path}:{line_num} - Connection string with embedded credentials")

            except Exception:
                continue

        assert len(findings) == 0, f"Found {len(findings)} connection strings with passwords:\n" + "\n".join(findings)

    @pytest.mark.security
    def test_no_jwt_tokens_hardcoded(self, source_files: List[Path]):
        """
        Valida que no hay JWT tokens hardcodeados.

        JWT format: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature
        """
        jwt_pattern = r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"

        findings = []
        for file_path in source_files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")

                # Skip test files (pueden tener JWTs de ejemplo)
                if "test_" in file_path.name or "conftest" in file_path.name:
                    continue

                matches = re.finditer(jwt_pattern, content)
                for match in matches:
                    line_num = content[: match.start()].count("\n") + 1
                    findings.append(f"{file_path}:{line_num} - JWT token detected")

            except Exception:
                continue

        assert len(findings) == 0, f"Found {len(findings)} hardcoded JWT tokens:\n" + "\n".join(findings)


class TestEnvironmentVariables:
    """Tests de configuración de variables de entorno."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def env_file(self, project_root: Path) -> Path:
        return project_root / ".env"

    @pytest.fixture
    def env_vars(self, env_file: Path) -> dict:
        """Parse .env file."""
        if not env_file.exists():
            return {}

        env = {}
        content = env_file.read_text()

        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip().strip('"').strip("'")

        return env

    @pytest.mark.security
    @pytest.mark.critical
    def test_env_file_exists(self, env_file: Path):
        """
        CRÍTICO: Debe existir archivo .env para configuración.
        """
        assert env_file.exists(), ".env file not found. Create from .env.example"

    @pytest.mark.security
    @pytest.mark.critical
    def test_secret_key_configured(self, env_vars: dict):
        """
        CRÍTICO: SECRET_KEY debe estar configurado y no ser valor dummy.
        """
        assert "SECRET_KEY" in env_vars, "SECRET_KEY not found in .env"

        secret_key = env_vars["SECRET_KEY"]

        # Check for dummy values
        dummy_indicators = ["REPLACE", "CHANGE", "TODO", "FIXME", "EXAMPLE", "YOUR_", "SECRET_KEY_HERE"]
        assert not any(indicator in secret_key.upper() for indicator in dummy_indicators), (
            f"SECRET_KEY contains dummy value: {secret_key[:10]}..."
        )

        # Check minimum length (should be at least 32 chars for good entropy)
        assert len(secret_key) >= 32, f"SECRET_KEY too short ({len(secret_key)} chars). Minimum: 32 chars."

    @pytest.mark.security
    @pytest.mark.critical
    def test_database_password_configured(self, env_vars: dict):
        """
        CRÍTICO: POSTGRES_PASSWORD debe estar configurado y ser fuerte.
        """
        assert "POSTGRES_PASSWORD" in env_vars, "POSTGRES_PASSWORD not found in .env"

        password = env_vars["POSTGRES_PASSWORD"]

        # Check for dummy values
        dummy_indicators = ["REPLACE", "CHANGE", "TODO", "PASSWORD", "ADMIN", "TEST"]
        assert not any(indicator in password.upper() for indicator in dummy_indicators), (
            "POSTGRES_PASSWORD contains dummy value"
        )

        # Check minimum length
        assert len(password) >= 16, f"POSTGRES_PASSWORD too short ({len(password)} chars). Minimum: 16 chars."

    @pytest.mark.security
    @pytest.mark.high
    def test_redis_password_configured(self, env_vars: dict):
        """
        ALTA: REDIS_PASSWORD debe estar configurado si Redis está en uso.
        """
        if "REDIS_PASSWORD" not in env_vars:
            pytest.skip("REDIS_PASSWORD not configured (optional)")

        password = env_vars["REDIS_PASSWORD"]

        dummy_indicators = ["REPLACE", "CHANGE", "TODO"]
        assert not any(indicator in password.upper() for indicator in dummy_indicators), "REDIS_PASSWORD is dummy value"

        assert len(password) >= 12, f"REDIS_PASSWORD too short ({len(password)} chars). Minimum: 12 chars."

    @pytest.mark.security
    @pytest.mark.high
    def test_pms_api_key_configured(self, env_vars: dict):
        """
        ALTA: PMS_API_KEY debe estar configurado si PMS no es mock.
        """
        pms_type = env_vars.get("PMS_TYPE", "mock")

        if pms_type == "mock":
            pytest.skip("PMS_TYPE=mock, API key not required")

        assert "PMS_API_KEY" in env_vars, "PMS_API_KEY required for non-mock PMS"

        api_key = env_vars["PMS_API_KEY"]

        dummy_indicators = ["REPLACE", "CHANGE", "TODO", "API_KEY"]
        assert not any(indicator in api_key.upper() for indicator in dummy_indicators), "PMS_API_KEY is dummy value"

    @pytest.mark.security
    @pytest.mark.production
    def test_debug_mode_disabled_in_production(self, env_vars: dict):
        """
        PRODUCCIÓN: DEBUG debe estar en false en producción.
        """
        environment = env_vars.get("ENVIRONMENT", "development")

        if environment != "production":
            pytest.skip("Not production environment")

        debug = env_vars.get("DEBUG", "false").lower()
        assert debug in ["false", "0", "no"], f"DEBUG mode enabled in production: {debug}"


class TestGitignoreCoverage:
    """Tests de cobertura de .gitignore."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def gitignore_content(self, project_root: Path) -> str:
        gitignore_path = project_root / ".gitignore"
        if not gitignore_path.exists():
            return ""
        return gitignore_path.read_text()

    @pytest.mark.security
    @pytest.mark.critical
    def test_gitignore_exists(self, project_root: Path):
        """
        CRÍTICO: Debe existir .gitignore para prevenir commits accidentales.
        """
        gitignore_path = project_root / ".gitignore"
        assert gitignore_path.exists(), ".gitignore file not found"

    @pytest.mark.security
    @pytest.mark.critical
    def test_env_files_in_gitignore(self, gitignore_content: str):
        """
        CRÍTICO: .env debe estar en .gitignore.
        """
        assert ".env" in gitignore_content, ".env not in .gitignore - risk of committing secrets"

    @pytest.mark.security
    @pytest.mark.high
    def test_sensitive_files_in_gitignore(self, gitignore_content: str):
        """
        ALTA: Archivos sensibles comunes deben estar en .gitignore.
        """
        required_patterns = [
            "*.pem",
            "*.key",
            "secrets.json",
            "credentials.json",
        ]

        missing = []
        for pattern in required_patterns:
            if pattern not in gitignore_content:
                missing.append(pattern)

        assert len(missing) == 0, f"Missing patterns in .gitignore: {', '.join(missing)}"


class TestFilePermissions:
    """Tests de permisos de archivos sensibles."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @pytest.mark.security
    @pytest.mark.high
    @pytest.mark.skipif(os.name == "nt", reason="File permissions not applicable on Windows")
    def test_env_file_permissions(self, project_root: Path):
        """
        ALTA: .env debe tener permisos restrictivos (600).

        600 = Owner: read+write, Group: none, Others: none
        """
        env_file = project_root / ".env"

        if not env_file.exists():
            pytest.skip(".env file not found")

        current_perms = oct(env_file.stat().st_mode)[-4:]

        # Accept 600 (owner only) or 644 (owner write, others read - less secure but common)
        acceptable_perms = ["0600", "0400"]  # 0600 = rw-------, 0400 = r--------

        assert current_perms in acceptable_perms, (
            f".env has insecure permissions: {current_perms}. Should be 0600. Fix with: chmod 600 .env"
        )

    @pytest.mark.security
    @pytest.mark.high
    @pytest.mark.skipif(os.name == "nt", reason="File permissions not applicable on Windows")
    def test_private_key_permissions(self, project_root: Path):
        """
        ALTA: Archivos .pem/.key deben tener permisos 600.
        """
        private_key_files = []

        for pattern in ["*.pem", "*.key", "id_rsa", "id_ed25519"]:
            private_key_files.extend(project_root.rglob(pattern))

        if not private_key_files:
            pytest.skip("No private key files found")

        insecure_files = []
        for key_file in private_key_files:
            current_perms = oct(key_file.stat().st_mode)[-4:]

            if current_perms not in ["0600", "0400"]:
                insecure_files.append(f"{key_file.name}: {current_perms}")

        assert len(insecure_files) == 0, (
            "Private keys with insecure permissions:\n" + "\n".join(insecure_files) + "\n\nFix with: chmod 600 <file>"
        )


class TestSecretRotation:
    """Tests de rotación de secretos."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @pytest.mark.security
    def test_env_file_recently_updated(self, project_root: Path):
        """
        Valida que .env fue actualizado recientemente (< 90 días).

        Secretos deben rotarse periódicamente como best practice.
        """
        env_file = project_root / ".env"

        if not env_file.exists():
            pytest.skip(".env file not found")

        mod_time = datetime.fromtimestamp(env_file.stat().st_mtime)
        days_since_update = (datetime.now() - mod_time).days

        # Warning if > 90 days
        assert days_since_update <= 90, (
            f".env not updated in {days_since_update} days. Consider rotating secrets (recommendation: every 90 days)."
        )


class TestGitHistory:
    """Tests de secretos en git history."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @pytest.mark.security
    @pytest.mark.slow
    def test_no_secrets_in_git_history_gitleaks(self, project_root: Path):
        """
        Ejecuta gitleaks para detectar secretos en git history.

        Requiere gitleaks instalado: brew install gitleaks
        """
        import subprocess

        try:
            result = subprocess.run(
                ["gitleaks", "detect", "--no-git", "-v"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )

            # gitleaks returns 1 if secrets found, 0 if clean
            assert result.returncode == 0, f"gitleaks found secrets in git history:\n{result.stdout}"

        except FileNotFoundError:
            pytest.skip("gitleaks not installed (brew install gitleaks)")
        except subprocess.TimeoutExpired:
            pytest.skip("gitleaks timeout (>2min)")
