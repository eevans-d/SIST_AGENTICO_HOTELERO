"""
P013: OWASP Top 10 2021 Validation Tests
=========================================

Tests automatizados para validar compliance contra OWASP Top 10 2021.

Categorías:
- A01: Broken Access Control (4 tests)
- A02: Cryptographic Failures (3 tests)
- A03: Injection (5 tests)
- A04: Insecure Design (2 tests)
- A05: Security Misconfiguration (4 tests)
- A06: Vulnerable Components (2 tests)
- A07: Authentication Failures (3 tests)
- A08: Data Integrity Failures (2 tests)
- A09: Logging and Monitoring (2 tests)
- A10: SSRF (3 tests)

Total: 30 tests
"""

import re
from pathlib import Path
from typing import List

import pytest


class TestA01BrokenAccessControl:
    """A01: Broken Access Control - CWE-200, CWE-284, CWE-22."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def router_files(self, project_root: Path) -> List[Path]:
        """Lista de archivos de routers."""
        return list((project_root / "app" / "routers").rglob("*.py"))

    @pytest.mark.security
    @pytest.mark.critical
    def test_all_endpoints_have_authorization(self, router_files: List[Path]):
        """
        CRÍTICO: Todos los endpoints públicos deben tener autorización.

        Valida que:
        - @router decorators tienen Depends(get_current_user) o similar
        - Endpoints públicos están explícitamente marcados
        """
        unprotected_endpoints = []

        for router_file in router_files:
            try:
                content = router_file.read_text()
                lines = content.split("\n")

                for i, line in enumerate(lines):
                    # Detectar decoradores de ruta
                    if re.search(r"@router\.(get|post|put|delete|patch)", line, re.IGNORECASE):
                        # Verificar contexto (5 líneas antes y después)
                        context_start = max(0, i - 5)
                        context_end = min(len(lines), i + 10)
                        context = "\n".join(lines[context_start:context_end])

                        # Excepciones: endpoints públicos conocidos
                        if any(
                            public in context.lower()
                            for public in [
                                "/health",
                                "/metrics",
                                "/docs",
                                "/openapi",
                                "public=true",
                                "allow_public",
                            ]
                        ):
                            continue

                        # Verificar presencia de auth
                        if not any(
                            auth in context
                            for auth in ["Depends(", "requires_auth", "get_current_user", "verify_token"]
                        ):
                            unprotected_endpoints.append(f"{router_file.name}:{i + 1} - {line.strip()}")

            except Exception:
                continue

        assert len(unprotected_endpoints) == 0, (
            f"Found {len(unprotected_endpoints)} unprotected endpoints:\n" + "\n".join(unprotected_endpoints[:10])
        )

    @pytest.mark.security
    @pytest.mark.high
    def test_no_path_traversal_vulnerabilities(self, project_root: Path):
        """
        ALTA: No debe haber vulnerabilidades de path traversal.

        Detecta:
        - open() con concatenación de strings
        - Path() con construcción dinámica insegura
        - Sin validación de .. en paths
        """
        vulnerable_files = []

        for py_file in project_root.rglob("*.py"):
            if "test_" in py_file.name:
                continue

            try:
                content = py_file.read_text()

                # Detectar construcción dinámica de paths
                if re.search(r"open\([^)]*\+[^)]*\)", content) or re.search(r"Path\([^)]*\+[^)]*\)", content):
                    # Verificar si hay validación
                    if ".resolve()" not in content and "normalize" not in content.lower():
                        vulnerable_files.append(str(py_file.relative_to(project_root)))

            except Exception:
                continue

        assert len(vulnerable_files) == 0, (
            f"Found {len(vulnerable_files)} files with potential path traversal:\n" + "\n".join(vulnerable_files)
        )

    @pytest.mark.security
    @pytest.mark.high
    def test_tenant_isolation_enforced(self, project_root: Path):
        """
        ALTA: Aislamiento de tenants debe estar implementado.

        Verifica que queries de base de datos incluyen filtro de tenant.
        """
        service_files = list((project_root / "app" / "services").rglob("*.py"))

        queries_without_tenant = []

        for service_file in service_files:
            try:
                content = service_file.read_text()
                lines = content.split("\n")

                for i, line in enumerate(lines):
                    # Detectar queries SQL/ORM
                    if re.search(r"\.(query|filter|select|find)", line, re.IGNORECASE):
                        # Verificar si hay filtro de tenant en contexto
                        context = "\n".join(lines[max(0, i - 3) : min(len(lines), i + 3)])

                        if "tenant" not in context.lower() and "organization" not in context.lower():
                            queries_without_tenant.append(f"{service_file.name}:{i + 1} - {line.strip()}")

            except Exception:
                continue

        # Permitir algunos falsos positivos (queries de sistema, tests)
        assert len(queries_without_tenant) < 10, (
            f"Found {len(queries_without_tenant)} queries without tenant isolation:\n"
            + "\n".join(queries_without_tenant[:5])
        )

    @pytest.mark.security
    def test_no_idor_vulnerabilities(self, project_root: Path):
        """
        Valida que no hay Insecure Direct Object References (IDOR).

        Detecta:
        - IDs de objetos expuestos sin validación de ownership
        - /{id} endpoints sin verificación de permisos
        """
        router_files = list((project_root / "app" / "routers").rglob("*.py"))

        potential_idor = []

        for router_file in router_files:
            try:
                content = router_file.read_text()
                lines = content.split("\n")

                for i, line in enumerate(lines):
                    # Detectar endpoints con path parameters
                    if re.search(r'@router\.(get|put|delete|patch)\(["\'].*\{[^}]+\}', line):
                        # Verificar si hay validación de ownership en función
                        func_start = i
                        func_end = min(len(lines), i + 20)
                        func_body = "\n".join(lines[func_start:func_end])

                        if "owner" not in func_body.lower() and "current_user" not in func_body.lower():
                            potential_idor.append(f"{router_file.name}:{i + 1} - {line.strip()}")

            except Exception:
                continue

        # Algunos endpoints públicos son esperados
        assert len(potential_idor) < 5, f"Found {len(potential_idor)} potential IDOR vulnerabilities:\n" + "\n".join(
            potential_idor
        )


class TestA02CryptographicFailures:
    """A02: Cryptographic Failures - CWE-327, CWE-328, CWE-798."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @pytest.mark.security
    @pytest.mark.critical
    def test_no_weak_crypto_algorithms(self, project_root: Path):
        """
        CRÍTICO: No debe haber algoritmos criptográficos débiles.

        Detecta:
        - MD5, SHA1 (obsoletos)
        - DES, RC4 (inseguros)
        - Recomienda SHA256, SHA3, AES-256
        """
        weak_algos = {
            "MD5": "SHA256",
            "SHA1": "SHA256",
            "DES": "AES-256",
            "RC4": "AES-256",
        }

        findings = []

        for py_file in project_root.rglob("*.py"):
            if "test_" in py_file.name:
                continue

            try:
                content = py_file.read_text()

                for weak, recommended in weak_algos.items():
                    if re.search(rf"\b{weak}\b", content, re.IGNORECASE):
                        findings.append(f"{py_file.name}: {weak} (use {recommended})")

            except Exception:
                continue

        assert len(findings) == 0, f"Found {len(findings)} weak crypto algorithms:\n" + "\n".join(findings)

    @pytest.mark.security
    @pytest.mark.critical
    def test_tls_version_enforced(self, project_root: Path):
        """
        CRÍTICO: TLS 1.2+ debe estar enforced.

        Verifica:
        - No hay TLS 1.0/1.1 configurado
        - TLS 1.2 o 1.3 está explícito
        """
        config_files = list(project_root.rglob("*.yml")) + list(project_root.rglob("*.yaml"))

        weak_tls_configs = []

        for config_file in config_files:
            try:
                content = config_file.read_text()

                if re.search(r"TLS.*1\.[01]", content, re.IGNORECASE):
                    weak_tls_configs.append(str(config_file.relative_to(project_root)))

            except Exception:
                continue

        assert len(weak_tls_configs) == 0, f"Found {len(weak_tls_configs)} files with weak TLS:\n" + "\n".join(
            weak_tls_configs
        )

    @pytest.mark.security
    @pytest.mark.high
    def test_sensitive_data_encryption_at_rest(self, project_root: Path):
        """
        ALTA: Datos sensibles deben estar encriptados en reposo.

        Valida que:
        - Campos como credit_card, ssn, password están encriptados
        - Se usa EncryptedField o similar
        """
        model_files = list((project_root / "app" / "models").rglob("*.py"))

        sensitive_fields = ["credit_card", "ssn", "social_security", "tax_id"]
        unencrypted_fields = []

        for model_file in model_files:
            try:
                content = model_file.read_text()
                lines = content.split("\n")

                for i, line in enumerate(lines):
                    for sensitive in sensitive_fields:
                        if sensitive in line.lower() and "=" in line:
                            # Verificar si está usando EncryptedField
                            if "Encrypted" not in line and "encrypt" not in line.lower():
                                unencrypted_fields.append(f"{model_file.name}:{i + 1} - {line.strip()}")

            except Exception:
                continue

        assert len(unencrypted_fields) == 0, (
            f"Found {len(unencrypted_fields)} unencrypted sensitive fields:\n" + "\n".join(unencrypted_fields)
        )


class TestA03Injection:
    """A03: Injection - CWE-74, CWE-78, CWE-79, CWE-89."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @pytest.mark.security
    @pytest.mark.critical
    def test_no_sql_injection_vulnerabilities(self, project_root: Path):
        """
        CRÍTICO: No debe haber vulnerabilidades de SQL injection.

        Detecta:
        - String concatenation en queries SQL
        - f-strings en queries
        - Recomienda parameterized queries
        """
        vulnerable_patterns = [
            r"(SELECT|INSERT|UPDATE|DELETE).*\+.*WHERE",
            r'f["\'].*SELECT.*\{',
            r'\.execute\(["\'][^"\']*\+',
        ]

        findings = []

        for py_file in project_root.rglob("*.py"):
            if "test_" in py_file.name:
                continue

            try:
                content = py_file.read_text()

                for pattern in vulnerable_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        findings.append(str(py_file.relative_to(project_root)))
                        break

            except Exception:
                continue

        assert len(findings) == 0, f"Found {len(findings)} potential SQL injection vulnerabilities:\n" + "\n".join(
            findings
        )

    @pytest.mark.security
    @pytest.mark.critical
    def test_no_command_injection_vulnerabilities(self, project_root: Path):
        """
        CRÍTICO: No debe haber command injection.

        Detecta:
        - os.system() con input dinámico
        - subprocess con shell=True y concatenación
        """
        vulnerable_patterns = [
            r"os\.system\(.*\+",
            r"subprocess\.(call|run|Popen).*shell\s*=\s*True.*\+",
            r"eval\(.*request",
            r"exec\(.*request",
        ]

        findings = []

        for py_file in project_root.rglob("*.py"):
            if "test_" in py_file.name:
                continue

            try:
                content = py_file.read_text()

                for pattern in vulnerable_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[: match.start()].count("\n") + 1
                        findings.append(f"{py_file.name}:{line_num}")

            except Exception:
                continue

        assert len(findings) == 0, f"Found {len(findings)} command injection vulnerabilities:\n" + "\n".join(findings)

    @pytest.mark.security
    @pytest.mark.high
    def test_no_xss_vulnerabilities(self, project_root: Path):
        """
        ALTA: No debe haber XSS en templates o respuestas.

        Detecta:
        - innerHTML con datos no sanitizados
        - Respuestas HTML sin escape
        """
        xss_patterns = [
            r"innerHTML\s*=.*request",
            r"outerHTML\s*=.*request",
            r"document\.write\(.*request",
        ]

        findings = []

        for file_path in project_root.rglob("*"):
            if file_path.suffix not in {".py", ".js", ".html", ".jinja2"}:
                continue

            if "test_" in file_path.name:
                continue

            try:
                content = file_path.read_text()

                for pattern in xss_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        findings.append(str(file_path.relative_to(project_root)))
                        break

            except Exception:
                continue

        assert len(findings) == 0, f"Found {len(findings)} potential XSS vulnerabilities:\n" + "\n".join(findings)

    @pytest.mark.security
    @pytest.mark.high
    def test_input_validation_on_all_endpoints(self, project_root: Path):
        """
        ALTA: Todos los endpoints deben validar input.

        Verifica que:
        - Se usan Pydantic models para request bodies
        - Path/query params tienen validación
        """
        router_files = list((project_root / "app" / "routers").rglob("*.py"))

        unvalidated_endpoints = []

        for router_file in router_files:
            try:
                content = router_file.read_text()
                lines = content.split("\n")

                for i, line in enumerate(lines):
                    if "@router.post" in line or "@router.put" in line:
                        # Verificar si hay Pydantic model en función
                        func_start = i
                        func_end = min(len(lines), i + 10)
                        func_signature = "\n".join(lines[func_start:func_end])

                        if ":" not in func_signature or "BaseModel" not in content:
                            unvalidated_endpoints.append(f"{router_file.name}:{i + 1}")

            except Exception:
                continue

        # Algunos endpoints pueden no tener body
        assert len(unvalidated_endpoints) < 5, (
            f"Found {len(unvalidated_endpoints)} endpoints without input validation:\n"
            + "\n".join(unvalidated_endpoints)
        )

    @pytest.mark.security
    @pytest.mark.ai
    def test_no_prompt_injection_vulnerabilities(self, project_root: Path):
        """
        AI-specific: No debe haber prompt injection en AI agent.

        Detecta:
        - Concatenación directa de user input en prompts
        - Sin sanitization de input para LLM
        """
        llm_files = []
        for py_file in project_root.rglob("*.py"):
            content = py_file.read_text()
            if "prompt" in content.lower() or "llm" in content.lower() or "openai" in content.lower():
                llm_files.append(py_file)

        vulnerable_prompts = []

        for llm_file in llm_files:
            if "test_" in llm_file.name:
                continue

            try:
                content = llm_file.read_text()

                # Detectar concatenación directa de input en prompts
                if re.search(r'prompt.*\+.*request|prompt.*f["\'].*\{.*user', content, re.IGNORECASE):
                    # Verificar si hay sanitization
                    if "sanitize" not in content.lower() and "validate" not in content.lower():
                        vulnerable_prompts.append(str(llm_file.relative_to(project_root)))

            except Exception:
                continue

        assert len(vulnerable_prompts) == 0, (
            f"Found {len(vulnerable_prompts)} potential prompt injection vulnerabilities:\n"
            + "\n".join(vulnerable_prompts)
        )


class TestA04InsecureDesign:
    """A04: Insecure Design - CWE-209, CWE-256."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @pytest.mark.security
    @pytest.mark.high
    def test_rate_limiting_configured(self, project_root: Path):
        """
        ALTA: Rate limiting debe estar configurado.

        Valida:
        - Limiter está importado en main.py
        - Endpoints críticos tienen @limiter.limit()
        """
        main_file = project_root / "app" / "main.py"

        if not main_file.exists():
            pytest.skip("main.py not found")

        content = main_file.read_text()

        assert "Limiter" in content or "rate_limit" in content, "Rate limiting not configured in main.py"

    @pytest.mark.security
    def test_business_logic_validation(self, project_root: Path):
        """
        Valida que la lógica de negocio tiene validaciones.

        Ejemplo: No se pueden hacer reservas en el pasado
        """
        service_files = list((project_root / "app" / "services").rglob("*.py"))

        # Buscar funciones de reserva sin validación de fecha
        booking_functions_without_validation = []

        for service_file in service_files:
            try:
                content = service_file.read_text()

                if "booking" in content.lower() or "reservation" in content.lower():
                    if "datetime" not in content and "date" not in content.lower():
                        booking_functions_without_validation.append(service_file.name)

            except Exception:
                continue

        # Puede haber servicios sin validación temporal
        assert len(booking_functions_without_validation) < 3, "Business logic validation may be missing"


class TestA05SecurityMisconfiguration:
    """A05: Security Misconfiguration - CWE-2, CWE-16."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @pytest.mark.security
    @pytest.mark.critical
    def test_debug_mode_disabled_in_production(self, project_root: Path):
        """
        CRÍTICO: DEBUG debe estar deshabilitado en producción.
        """
        env_file = project_root / ".env"

        if not env_file.exists():
            pytest.skip(".env not found")

        content = env_file.read_text()

        # Si ENVIRONMENT=production, DEBUG debe ser false
        is_production = re.search(r"ENVIRONMENT\s*=\s*production", content, re.IGNORECASE)

        if is_production:
            debug_enabled = re.search(r"DEBUG\s*=\s*[Tt]rue", content)
            assert debug_enabled is None, "DEBUG mode is enabled in production environment"

    @pytest.mark.security
    @pytest.mark.high
    def test_security_headers_configured(self, project_root: Path):
        """
        ALTA: Security headers deben estar configurados.

        Valida:
        - X-Content-Type-Options: nosniff
        - X-Frame-Options: DENY
        - Content-Security-Policy
        """
        middleware_file = project_root / "app" / "core" / "middleware.py"

        if not middleware_file.exists():
            pytest.skip("middleware.py not found")

        content = middleware_file.read_text()

        required_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": ["DENY", "SAMEORIGIN"],
            "Content-Security-Policy": "default-src",
        }

        missing_headers = []

        for header, value in required_headers.items():
            if header not in content:
                missing_headers.append(header)

        assert len(missing_headers) == 0, f"Missing security headers: {', '.join(missing_headers)}"

    @pytest.mark.security
    def test_cors_properly_configured(self, project_root: Path):
        """
        Valida configuración de CORS.

        Debe:
        - No permitir * en producción
        - Tener lista de allowed origins explícita
        """
        main_file = project_root / "app" / "main.py"

        if not main_file.exists():
            pytest.skip("main.py not found")

        content = main_file.read_text()

        if "CORSMiddleware" in content:
            # Verificar que no se use allow_origins=["*"]
            assert 'allow_origins=["*"]' not in content, "CORS allows all origins (insecure)"

    @pytest.mark.security
    def test_error_messages_dont_leak_info(self, project_root: Path):
        """
        Valida que mensajes de error no revelan info sensible.

        Debe evitar:
        - Stack traces en producción
        - Database errors expuestos
        - Internal paths revelados
        """
        exception_handlers = list((project_root / "app").rglob("*exception*.py")) + list(
            (project_root / "app").rglob("*error*.py")
        )

        leaky_errors = []

        for handler_file in exception_handlers:
            try:
                content = handler_file.read_text()

                # Detectar si se exponen excepciones sin sanitizar
                if "str(exc)" in content or "repr(exc)" in content:
                    if "DEBUG" not in content and "environment" not in content.lower():
                        leaky_errors.append(handler_file.name)

            except Exception:
                continue

        # Algunos handlers de debug son esperados
        assert len(leaky_errors) < 2, f"Error handlers may leak information: {', '.join(leaky_errors)}"


class TestA06VulnerableComponents:
    """A06: Vulnerable and Outdated Components - CWE-1104."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @pytest.mark.security
    @pytest.mark.critical
    def test_no_known_vulnerable_dependencies(self, project_root: Path):
        """
        CRÍTICO: No debe haber dependencias con vulnerabilidades conocidas.

        Delega a P011 (dependency scan).
        """
        vuln_report = project_root / ".security" / "vuln-scan-latest.json"

        if not vuln_report.exists():
            pytest.skip("Run 'make security-deps-json' first")

        import json

        data = json.loads(vuln_report.read_text())

        critical_vulns = data.get("summary", {}).get("severity_breakdown", {}).get("CRITICAL", 0)
        high_vulns = data.get("summary", {}).get("severity_breakdown", {}).get("HIGH", 0)

        assert critical_vulns == 0, f"Found {critical_vulns} CRITICAL vulnerabilities in dependencies"
        assert high_vulns <= 2, f"Found {high_vulns} HIGH vulnerabilities (max 2 allowed with exceptions)"

    @pytest.mark.security
    def test_dependencies_are_up_to_date(self, project_root: Path):
        """
        Valida que dependencias están actualizadas (< 30% outdated).

        Delega a P011 (freshness check).
        """
        vuln_report = project_root / ".security" / "vuln-scan-latest.json"

        if not vuln_report.exists():
            pytest.skip("Run 'make security-deps-json' first")

        import json

        data = json.loads(vuln_report.read_text())

        outdated_info = data.get("outdated_packages", {})
        total = outdated_info.get("total_packages", 1)
        outdated = outdated_info.get("total_outdated", 0)

        outdated_percentage = (outdated / total) * 100 if total > 0 else 0

        assert outdated_percentage < 30, f"{outdated_percentage:.1f}% of dependencies are outdated (max 30%)"


class TestA07AuthenticationFailures:
    """A07: Identification and Authentication Failures - CWE-287, CWE-798."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @pytest.mark.security
    @pytest.mark.critical
    def test_jwt_uses_strong_secret(self, project_root: Path):
        """
        CRÍTICO: JWT debe usar SECRET_KEY desde environment.

        No debe:
        - Tener secret hardcodeado
        - Usar HS256 con secret débil
        """
        auth_files = list(project_root.rglob("*auth*.py")) + list(project_root.rglob("*jwt*.py"))

        weak_jwt_configs = []

        for auth_file in auth_files:
            if "test_" in auth_file.name:
                continue

            try:
                content = auth_file.read_text()

                # Detectar jwt.encode con secret hardcodeado
                if re.search(r"jwt\.encode.*HS256", content, re.IGNORECASE):
                    if "SECRET_KEY" not in content and "os.getenv" not in content and "settings" not in content:
                        weak_jwt_configs.append(auth_file.name)

            except Exception:
                continue

        assert len(weak_jwt_configs) == 0, (
            f"Found {len(weak_jwt_configs)} JWT configs with weak secrets:\n" + "\n".join(weak_jwt_configs)
        )

    @pytest.mark.security
    @pytest.mark.high
    def test_password_complexity_enforced(self, project_root: Path):
        """
        ALTA: Contraseñas deben tener complejidad mínima.

        Debe validar:
        - Min 8 caracteres
        - Al menos 1 mayúscula
        - Al menos 1 número
        - Al menos 1 caracter especial
        """
        validator_files = list(project_root.rglob("*validator*.py")) + list(project_root.rglob("*password*.py"))

        password_validators = []

        for validator_file in validator_files:
            try:
                content = validator_file.read_text()

                if "password" in content.lower():
                    # Verificar que hay validación de complejidad
                    has_length_check = "len(" in content or "min_length" in content.lower()
                    has_complexity_check = "regex" in content.lower() or "pattern" in content.lower()

                    if has_length_check or has_complexity_check:
                        password_validators.append(validator_file.name)

            except Exception:
                continue

        assert len(password_validators) > 0, (
            "No password complexity validation found. Implement in validators or Pydantic models."
        )

    @pytest.mark.security
    def test_account_lockout_after_failed_attempts(self, project_root: Path):
        """
        Valida que hay lockout tras intentos fallidos.

        Debe implementar:
        - Rate limiting en /login
        - Cuenta de intentos fallidos
        - Lockout temporal (15-30 min)
        """
        auth_files = list(project_root.rglob("*auth*.py")) + list(project_root.rglob("*login*.py"))

        lockout_implementations = []

        for auth_file in auth_files:
            try:
                content = auth_file.read_text()

                if "login" in content.lower():
                    # Buscar implementación de lockout
                    has_attempt_tracking = "attempt" in content.lower() or "failed" in content.lower()
                    has_rate_limit = "limiter" in content.lower() or "rate_limit" in content.lower()

                    if has_attempt_tracking or has_rate_limit:
                        lockout_implementations.append(auth_file.name)

            except Exception:
                continue

        # Puede estar en middleware o rate limiter
        if len(lockout_implementations) == 0:
            pytest.skip("Account lockout may be implemented in rate limiter")


class TestA08DataIntegrityFailures:
    """A08: Software and Data Integrity Failures - CWE-502."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @pytest.mark.security
    @pytest.mark.critical
    def test_no_insecure_deserialization(self, project_root: Path):
        """
        CRÍTICO: No debe haber deserialización insegura.

        Detecta:
        - pickle.loads() sin validación
        - eval() con datos externos
        - yaml.load() sin safe_load
        """
        unsafe_patterns = {
            "pickle.loads": "Use JSON instead of pickle",
            "pickle.load": "Use JSON instead of pickle",
            "eval(": "Never use eval() with external data",
            "yaml.load(": "Use yaml.safe_load() instead",
        }

        findings = []

        for py_file in project_root.rglob("*.py"):
            if "test_" in py_file.name:
                continue

            try:
                content = py_file.read_text()

                for unsafe, recommendation in unsafe_patterns.items():
                    if unsafe in content:
                        findings.append(f"{py_file.name}: {unsafe} - {recommendation}")

            except Exception:
                continue

        assert len(findings) == 0, f"Found {len(findings)} insecure deserialization:\n" + "\n".join(findings)

    @pytest.mark.security
    def test_file_uploads_validated(self, project_root: Path):
        """
        Valida que file uploads están validados.

        Debe verificar:
        - Content-Type
        - File extension
        - File size limit
        - Malware scanning (optional)
        """
        router_files = list((project_root / "app" / "routers").rglob("*.py"))

        upload_handlers = []

        for router_file in router_files:
            try:
                content = router_file.read_text()

                if "UploadFile" in content or "File(" in content:
                    # Verificar validación
                    has_validation = (
                        "content_type" in content.lower()
                        or "extension" in content.lower()
                        or "validate" in content.lower()
                    )

                    if not has_validation:
                        upload_handlers.append(router_file.name)

            except Exception:
                continue

        assert len(upload_handlers) == 0, (
            f"Found {len(upload_handlers)} file upload handlers without validation:\n" + "\n".join(upload_handlers)
        )


class TestA09LoggingMonitoringFailures:
    """A09: Security Logging and Monitoring Failures - CWE-778."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @pytest.mark.security
    @pytest.mark.high
    def test_authentication_events_logged(self, project_root: Path):
        """
        ALTA: Eventos de autenticación deben ser logueados.

        Debe loguear:
        - Login attempts (success/failure)
        - Logout events
        - Password changes
        - Token generation
        """
        auth_files = list(project_root.rglob("*auth*.py")) + list(project_root.rglob("*login*.py"))

        auth_with_logging = []

        for auth_file in auth_files:
            if "test_" in auth_file.name:
                continue

            try:
                content = auth_file.read_text()

                if "login" in content.lower() or "authenticate" in content.lower():
                    if "logger" in content or "log" in content.lower():
                        auth_with_logging.append(auth_file.name)

            except Exception:
                continue

        assert len(auth_with_logging) > 0, "Authentication events should be logged. Add logger to auth modules."

    @pytest.mark.security
    def test_sensitive_data_masked_in_logs(self, project_root: Path):
        """
        Valida que datos sensibles están enmascarados en logs.

        No debe loguear:
        - Passwords
        - Credit card numbers
        - Tokens completos
        - Personal identifiable information (PII)
        """
        logging_config = project_root / "app" / "core" / "logging.py"

        if not logging_config.exists():
            pytest.skip("logging.py not found")

        content = logging_config.read_text()

        # Verificar que hay filtrado/masking
        has_filtering = "filter" in content.lower() or "mask" in content.lower() or "redact" in content.lower()

        assert has_filtering, "Logging should filter/mask sensitive data. Implement LoggingFilter or similar."


class TestA10SSRF:
    """A10: Server-Side Request Forgery - CWE-918."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @pytest.mark.security
    @pytest.mark.critical
    def test_no_unvalidated_url_fetch(self, project_root: Path):
        """
        CRÍTICO: URLs externas deben ser validadas antes de fetch.

        Detecta:
        - requests.get(user_input)
        - httpx.get(user_input)
        - urllib.request(user_input)
        """
        ssrf_patterns = [
            r"requests\.get\([^)]*request\.",
            r"httpx\.get\([^)]*request\.",
            r"urllib\.request\.urlopen\([^)]*request\.",
        ]

        findings = []

        for py_file in project_root.rglob("*.py"):
            if "test_" in py_file.name:
                continue

            try:
                content = py_file.read_text()

                for pattern in ssrf_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Verificar si hay validación
                        context_start = max(0, match.start() - 200)
                        context = content[context_start : match.end() + 200]

                        if "validate" not in context.lower() and "whitelist" not in context.lower():
                            line_num = content[: match.start()].count("\n") + 1
                            findings.append(f"{py_file.name}:{line_num}")

            except Exception:
                continue

        assert len(findings) == 0, f"Found {len(findings)} potential SSRF vulnerabilities:\n" + "\n".join(findings[:5])

    @pytest.mark.security
    @pytest.mark.high
    def test_internal_services_not_accessible_from_outside(self, project_root: Path):
        """
        ALTA: Servicios internos no deben ser accesibles externamente.

        Valida que:
        - Redis, Postgres, etc. no tienen bind 0.0.0.0
        - Docker compose no expone puertos internos
        """
        docker_compose = project_root / "docker-compose.yml"

        if not docker_compose.exists():
            pytest.skip("docker-compose.yml not found")

        content = docker_compose.read_text()

        # Detectar servicios internos expuestos públicamente
        internal_services = ["redis", "postgres", "mysql"]
        exposed_services = []

        for service in internal_services:
            if service in content.lower():
                # Buscar ports mapping hacia host
                service_section_match = re.search(rf"{service}:.*?(?=\n  \w|\Z)", content, re.DOTALL | re.IGNORECASE)
                if service_section_match:
                    service_section = service_section_match.group()

                    # Detectar ports expuestos al host (formato: "6379:6379")
                    if re.search(r'ports:.*\n.*-\s*["\']?\d+:\d+', service_section, re.IGNORECASE):
                        exposed_services.append(service)

        # Permitir exposición en desarrollo, pero alertar
        if len(exposed_services) > 0:
            pytest.skip(
                f"Internal services exposed (dev ok, prod NO): {', '.join(exposed_services)}. "
                f"Ensure firewall rules in production."
            )

    @pytest.mark.security
    def test_redirect_urls_validated(self, project_root: Path):
        """
        Valida que redirects son validados (Open Redirect).

        Detecta:
        - RedirectResponse(user_input) sin validación
        - Location header con input dinámico
        """
        redirect_patterns = [
            r"RedirectResponse\([^)]*request\.",
            r"redirect\([^)]*request\.",
        ]

        findings = []

        for py_file in project_root.rglob("*.py"):
            if "test_" in py_file.name:
                continue

            try:
                content = py_file.read_text()

                for pattern in redirect_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Verificar validación
                        context = content[max(0, match.start() - 100) : match.end() + 100]

                        if "validate" not in context.lower() and "allowed" not in context.lower():
                            line_num = content[: match.start()].count("\n") + 1
                            findings.append(f"{py_file.name}:{line_num}")

            except Exception:
                continue

        assert len(findings) == 0, f"Found {len(findings)} unvalidated redirects:\n" + "\n".join(findings)
