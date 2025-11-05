# P012: Secret Scanning & Hardening - Guía Completa

## 📋 Resumen Ejecutivo

**Script**: `scripts/security/secret_scanner.py`  
**Tests**: `tests/security/test_secret_scanning.py` (15 tests)  
**Objetivo**: Detectar secretos hardcodeados, credenciales débiles y configuraciones inseguras  
**Compliance**: OWASP Top 10 A05:2021 (Security Misconfiguration), CWE-798, CWE-259

---

## 🎯 Capacidades del Scanner

### 1. Detección de Secretos Hardcodeados (9 Patrones)

| Tipo | Patrón | Severidad | Ejemplo |
|------|--------|-----------|---------|
| **API Keys Genéricas** | `api_key = "abc..."` | HIGH | `API_KEY = "sk_live_abc123..."` |
| **AWS Access Keys** | `AKIA[0-9A-Z]{16}` | CRITICAL | `AKIAIOSFODNN7EXAMPLE` |
| **AWS Secret Keys** | `aws_secret = "..."` | CRITICAL | `aws_secret_access_key = "wJal..."` |
| **GitHub Tokens** | `github_token = "..."` | CRITICAL | `github_token = "ghp_..."` |
| **Slack Tokens** | `xox[baprs]-...` | HIGH | `xoxb-1234567890...` |
| **Private Keys** | `-----BEGIN PRIVATE KEY-----` | CRITICAL | RSA/EC/OpenSSH keys |
| **JWT Tokens** | `eyJ...` (3 parts) | MEDIUM | `eyJhbGci...` |
| **Passwords** | `password = "..."` | HIGH | `password = "MyPass123"` |
| **Connection Strings** | `postgres://user:pass@...` | HIGH | Embedded credentials |

### 2. Validación de Variables de Entorno

| Variable | Min Length | Validación | Severidad |
|----------|------------|------------|-----------|
| `SECRET_KEY` | 32 chars | No dummy values | CRITICAL |
| `POSTGRES_PASSWORD` | 16 chars | Fuerte | CRITICAL |
| `REDIS_PASSWORD` | 12 chars | No defaults | HIGH |
| `PMS_API_KEY` | 20 chars | Válido | HIGH |
| `WHATSAPP_ACCESS_TOKEN` | 50 chars | Meta format | HIGH |

**Dummy Values Detectados** (13 patrones):
- `REPLACE_WITH_SECURE`, `CHANGEME`, `CHANGE_ME`
- `TODO`, `FIXME`, `DUMMY`, `TEST`, `EXAMPLE`
- `SECRET_KEY_HERE`, `YOUR_`, `INSERT_`
- `12345`, `password`, `admin`

### 3. Auditoría de Permisos de Archivos

| Archivo | Permisos Requeridos | Riesgo si Incorrectos |
|---------|---------------------|------------------------|
| `.env` | 0600 (rw-------) | Exposición de secretos |
| `.env.production` | 0600 | Credenciales production |
| `secrets.json` | 0600 | API keys |
| `private_key.pem` | 0600 | Compromise de PKI |
| `id_rsa` / `id_ed25519` | 0600 | SSH key compromise |

### 4. Cobertura de .gitignore

**Patrones Requeridos**:
- `.env` (critical)
- `*.pem` (private keys)
- `*.key` (certificates)
- `secrets.json` (config files)
- `credentials.json` (auth files)

### 5. Escaneo de Git History (Opcional)

**gitleaks**: Escanea commits históricos
```bash
gitleaks detect --no-git -v --report-format json
```

**trufflehog**: Deep scan de filesystem y git
```bash
trufflehog filesystem <path> --json
```

### 6. Política de Rotación

- **Threshold**: 90 días desde última modificación de `.env`
- **Recommendation**: Rotar API keys y passwords cada 90 días
- **Severidad**: MEDIUM (warning preventivo)

---

## 🚀 Uso del Script

### Escaneo Básico (Markdown Output)

```bash
# Desde raíz del proyecto
python scripts/security/secret_scanner.py

# Output: .security/secret_scan_report.md
```

**Salida de ejemplo**:
```markdown
# Secret Scanning Report

**Scan Date**: 2024-01-15 10:30:00
**Duration**: 2.5 seconds
**Status**: ⚠️ ISSUES FOUND

## Summary
- **CRITICAL**: 2 issues
- **HIGH**: 5 issues
- **MEDIUM**: 3 issues

## Secret Findings (7)

### CRITICAL: AWS Access Key
- **File**: `app/config.py:45`
- **Description**: AWS access key detected
- **Recommendation**: Move to environment variables

...
```

### Escaneo para CI/CD (JSON Output)

```bash
python scripts/security/secret_scanner.py --format json --output .security/scan.json

# Exit codes:
# 0 = Clean or LOW/MEDIUM only
# 1 = HIGH severity issues
# 2 = CRITICAL severity issues
```

**JSON Schema**:
```json
{
  "scan_timestamp": "2024-01-15T10:30:00",
  "scan_duration_seconds": 2.5,
  "secret_findings": [
    {
      "file_path": "app/config.py",
      "line_number": 45,
      "secret_type": "aws_access_key",
      "severity": "CRITICAL",
      "description": "AWS access key detected",
      "matched_string": "AKIA***************",
      "recommendation": "Move to environment variables",
      "source": "source_code"
    }
  ],
  "environment_issues": [...],
  "file_permission_issues": [...],
  "git_history_issues": [...],
  "summary": {
    "total_issues": 10,
    "by_severity": {
      "CRITICAL": 2,
      "HIGH": 5,
      "MEDIUM": 3
    }
  }
}
```

### Modo Strict (Falla en Cualquier Finding)

```bash
python scripts/security/secret_scanner.py --strict

# Exit code 1 si hay cualquier finding (incluso LOW)
```

### Escaneo con Git History (gitleaks + trufflehog)

```bash
# Requiere gitleaks y trufflehog instalados
python scripts/security/secret_scanner.py --include-git-history
```

---

## 🧪 Tests Automatizados

### Ejecución de Tests

```bash
# Todos los tests de secret scanning
pytest tests/security/test_secret_scanning.py -v

# Solo tests críticos
pytest tests/security/test_secret_scanning.py -m critical

# Tests de producción
pytest tests/security/test_secret_scanning.py -m production

# Incluir tests lentos (gitleaks)
pytest tests/security/test_secret_scanning.py --runslow
```

### Cobertura de Tests (15 tests)

#### **TestHardcodedSecrets** (7 tests)

1. ✅ `test_no_hardcoded_api_keys` - CRITICAL
   - Detecta: `api_key = "sk_live_..."`
   - Patrón: 20+ caracteres alfanuméricos

2. ✅ `test_no_hardcoded_passwords` - CRITICAL
   - Detecta: `password = "MyPass123"`
   - Excluye: placeholders y variables

3. ✅ `test_no_aws_credentials` - CRITICAL
   - Detecta: `AKIA[0-9A-Z]{16}`
   - Cobertura: access keys

4. ✅ `test_no_private_keys_in_repo` - HIGH
   - Detecta: `-----BEGIN PRIVATE KEY-----`
   - Tipos: RSA, EC, OpenSSH

5. ✅ `test_no_connection_strings_with_passwords` - HIGH
   - Detecta: `postgres://user:pass@host`
   - Excluye: referencias a env vars (`${VAR}`)

6. ✅ `test_no_jwt_tokens_hardcoded` - MEDIUM
   - Detecta: `eyJ...` (3-part base64)
   - Excluye: archivos de test

7. ✅ `test_no_github_tokens` (implícito en patrón)
   - Detecta: `ghp_`, `gho_`, tokens de 40 chars

#### **TestEnvironmentVariables** (5 tests)

8. ✅ `test_env_file_exists` - CRITICAL
   - Valida existencia de `.env`

9. ✅ `test_secret_key_configured` - CRITICAL
   - Min 32 chars
   - No dummy values
   - Entropía adecuada

10. ✅ `test_database_password_configured` - CRITICAL
    - Min 16 chars
    - No defaults (`postgres`, `admin`)

11. ✅ `test_redis_password_configured` - HIGH
    - Min 12 chars si configurado
    - Skip si REDIS_PASSWORD ausente

12. ✅ `test_debug_mode_disabled_in_production` - PRODUCTION
    - `DEBUG=false` en prod
    - Skip si `ENVIRONMENT != production`

#### **TestGitignoreCoverage** (2 tests)

13. ✅ `test_gitignore_exists` - CRITICAL
    - Valida existencia de `.gitignore`

14. ✅ `test_sensitive_files_in_gitignore` - HIGH
    - Patrones requeridos: `.env`, `*.pem`, `*.key`, `secrets.json`

#### **TestFilePermissions** (1 test)

15. ✅ `test_env_file_permissions` - HIGH
    - Valida 0600 (rw-------)
    - Skip en Windows
    - Guía de remediación

---

## 🔧 Integración con Makefile

### Agregar a `Makefile`:

```makefile
.PHONY: secret-scan secret-scan-json fix-permissions secret-scan-strict

# Escaneo normal con output Markdown
secret-scan:
	@echo "🔍 Scanning for hardcoded secrets..."
	@python scripts/security/secret_scanner.py --format markdown
	@echo "📄 Report: .security/secret_scan_report.md"

# Escaneo para CI/CD (JSON)
secret-scan-json:
	@echo "🔍 Running secret scan (CI/CD mode)..."
	@python scripts/security/secret_scanner.py --format json --output .security/scan.json
	@echo "✅ Report: .security/scan.json"

# Fix automático de permisos
fix-permissions:
	@echo "🔒 Fixing file permissions..."
	@chmod 600 .env .env.production 2>/dev/null || true
	@chmod 600 private_key.pem id_rsa id_ed25519 2>/dev/null || true
	@echo "✅ Permissions fixed"

# Modo strict para CI/CD
secret-scan-strict:
	@echo "🔍 Running strict secret scan..."
	@python scripts/security/secret_scanner.py --strict --format json
	@echo "✅ No secrets found"
```

### Uso de Targets:

```bash
# Desarrollo local
make secret-scan

# Pre-commit check
make secret-scan-strict

# CI/CD pipeline
make secret-scan-json && echo "Secrets scan passed"
```

---

## 🪝 Pre-commit Hook

### Instalación

**1. Instalar pre-commit**:
```bash
pip install pre-commit
```

**2. Crear `.pre-commit-config.yaml`**:
```yaml
repos:
  - repo: local
    hooks:
      # Secret Scanner
      - id: secret-scan
        name: Secret Scanner
        entry: python scripts/security/secret_scanner.py --strict
        language: system
        pass_filenames: false
        stages: [commit]
        verbose: true

      # File Permissions
      - id: check-file-permissions
        name: Check Sensitive File Permissions
        entry: bash -c 'chmod 600 .env 2>/dev/null || true'
        language: system
        pass_filenames: false
        stages: [commit]

  # Gitleaks (optional, requires gitleaks installed)
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
        name: Gitleaks
        entry: gitleaks protect --verbose --redact --staged
        language: system
```

**3. Activar hooks**:
```bash
pre-commit install
```

**4. Test del hook**:
```bash
pre-commit run --all-files
```

---

## 🛡️ Remediación de Findings

### 1. Secretos Hardcodeados → Environment Variables

**❌ Antes**:
```python
# app/config.py
API_KEY = "sk_live_1234567890abcdef"
DB_PASSWORD = "MySecretPass123"
```

**✅ Después**:
```python
# app/config.py
import os
API_KEY = os.getenv("API_KEY")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")

# .env (no commitear!)
API_KEY=sk_live_1234567890abcdef
POSTGRES_PASSWORD=MySecretPass123
```

### 2. Dummy Values → Valores Reales

**❌ Antes**:
```bash
# .env
SECRET_KEY=REPLACE_WITH_SECURE
POSTGRES_PASSWORD=changeme
```

**✅ Después**:
```bash
# .env
SECRET_KEY=9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8
POSTGRES_PASSWORD=Xk9mP#vL2$nQ8wT@rY4hJ6
```

**Generación de secretos seguros**:
```bash
# SECRET_KEY (32 bytes = 64 hex chars)
openssl rand -hex 32

# Passwords (20 caracteres alfanuméricos + símbolos)
openssl rand -base64 24
```

### 3. Permisos Inseguros → 0600

**❌ Antes**:
```bash
$ ls -la .env
-rw-r--r-- 1 user group 1234 Jan 15 10:00 .env  # 644 - leíble por otros!
```

**✅ Después**:
```bash
chmod 600 .env
chmod 600 .env.production
chmod 600 private_key.pem

$ ls -la .env
-rw------- 1 user group 1234 Jan 15 10:00 .env  # 600 - solo owner
```

### 4. .gitignore Incompleto → Coverage Completo

**❌ Antes**:
```gitignore
# .gitignore
node_modules/
__pycache__/
```

**✅ Después**:
```gitignore
# .gitignore
node_modules/
__pycache__/

# Secrets (CRITICAL)
.env
.env.*
!.env.example
secrets.json
credentials.json

# Keys & Certificates
*.pem
*.key
*.p12
*.pfx
id_rsa
id_ed25519
```

### 5. Private Keys en Repo → Git History Cleanup

**Si ya commiteaste una clave privada**:

```bash
# 1. Instalar git-filter-repo
pip install git-filter-repo

# 2. Eliminar archivo de history
git filter-repo --path private_key.pem --invert-paths

# 3. Force push (CUIDADO - reescribe history)
git push --force

# 4. Rotar la clave comprometida
# La clave antigua ya está expuesta, DEBE rotarse
```

---

## 🔄 CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/security.yml
name: Security Scan

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Full history for gitleaks

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run Secret Scanner
        run: |
          python scripts/security/secret_scanner.py --format json --output scan.json
        continue-on-error: true

      - name: Check Exit Code
        run: |
          if [ $? -eq 2 ]; then
            echo "❌ CRITICAL secrets found!"
            exit 1
          elif [ $? -eq 1 ]; then
            echo "⚠️ HIGH severity secrets found"
            exit 1
          else
            echo "✅ No critical secrets"
          fi

      - name: Upload Scan Results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: secret-scan-report
          path: scan.json

      - name: Run Gitleaks (Optional)
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### GitLab CI/CD

```yaml
# .gitlab-ci.yml
secret_scan:
  stage: security
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - python scripts/security/secret_scanner.py --format json --output scan.json
  artifacts:
    reports:
      junit: scan.json
    paths:
      - scan.json
    expire_in: 30 days
  allow_failure: false
  only:
    - merge_requests
    - main
```

---

## 📊 Métricas y Reporting

### Dashboard Grafana (Prometheus Metrics)

```python
# En secret_scanner.py ya incluye métricas:
secret_findings_total = Counter(
    "secret_scan_findings_total",
    "Total secret findings",
    ["severity", "type"]
)

scan_duration_seconds = Histogram(
    "secret_scan_duration_seconds",
    "Secret scan duration"
)

# Uso en dashboards:
# - Total findings by severity (gauge)
# - Scan frequency (rate)
# - Top secret types (bar chart)
```

### Executive Summary Report

```markdown
# Secret Scanning - Executive Summary

**Period**: Last 7 days
**Scans**: 42 scans
**Status**: ⚠️ 3 CRITICAL issues pending

## Key Findings

1. **AWS Credentials** (CRITICAL)
   - Location: `app/config.py:45`
   - Action: Moved to AWS Secrets Manager
   - Status: ✅ Resolved

2. **Database Password** (CRITICAL)
   - Location: `.env`
   - Action: Rotated password
   - Status: ✅ Resolved

3. **API Key Rotation** (MEDIUM)
   - Last rotated: 95 days ago
   - Action: Schedule rotation
   - Status: 🔄 In Progress

## Trend Analysis

- **Week 1**: 12 findings
- **Week 2**: 8 findings (-33%)
- **Week 3**: 3 findings (-62%)
- **Week 4**: 0 findings (-100%) ✅

## Compliance Status

- ✅ OWASP A05:2021 - Security Misconfiguration
- ✅ CWE-798 - Hard-coded Credentials
- ✅ PCI-DSS 3.2.1 - Requirement 8.2.3 (Password Complexity)
```

---

## 🎓 Best Practices

### 1. Never Commit Secrets

```bash
# ❌ NUNCA hacer esto:
git add .env
git commit -m "Added config"

# ✅ SIEMPRE revisar antes:
git status
# (confirmar que .env NO está staged)
git add app/
git commit -m "Added feature"
```

### 2. Use Secret Management Solutions

**Para Development**:
- `.env` files (local, no commitear)
- `direnv` (auto-load env vars)

**Para Production**:
- **AWS Secrets Manager** (cloud)
- **HashiCorp Vault** (self-hosted)
- **Kubernetes Secrets** (k8s)
- **Azure Key Vault** (Azure)

**Ejemplo con AWS Secrets Manager**:
```python
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']

# Uso
db_password = get_secret('prod/postgres/password')
```

### 3. Rotate Secrets Regularly

**Policy Recommendations**:
- **Passwords**: 90 días
- **API Keys**: 90 días
- **Certificates**: 365 días
- **SSH Keys**: 180 días

**Automation**:
```bash
# Cron job para alertas de rotación
0 0 * * * python scripts/check_secret_age.py --warn-days 80
```

### 4. Implement Least Privilege

```python
# ❌ No dar acceso global
API_KEY = "sk_live_full_access_key"

# ✅ Usar keys con scopes limitados
READONLY_API_KEY = "sk_live_readonly_key"
WRITE_API_KEY = "sk_live_write_key"  # Solo donde sea necesario
```

### 5. Monitor and Alert

```yaml
# alertmanager config
- alert: SecretsFoundInCode
  expr: secret_scan_findings_total{severity="CRITICAL"} > 0
  for: 5m
  annotations:
    summary: "CRITICAL secrets detected in codebase"
    description: "{{ $value }} critical secrets found"
```

---

## 🔗 Referencias

### OWASP
- [OWASP Top 10 2021 - A05: Security Misconfiguration](https://owasp.org/Top10/A05_2021-Security_Misconfiguration/)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

### CWE
- [CWE-798: Use of Hard-coded Credentials](https://cwe.mitre.org/data/definitions/798.html)
- [CWE-259: Use of Hard-coded Password](https://cwe.mitre.org/data/definitions/259.html)

### Tools
- [gitleaks](https://github.com/gitleaks/gitleaks) - Git secret scanner
- [trufflehog](https://github.com/trufflesecurity/trufflehog) - Deep secret scanner
- [detect-secrets](https://github.com/Yelp/detect-secrets) - Baseline secret detection

### Standards
- **PCI-DSS 3.2.1**: Requirement 8.2 (Password Complexity)
- **NIST 800-53**: SC-12 (Cryptographic Key Establishment)
- **ISO 27001**: A.9.4.3 (Password Management)

---

## ✅ Checklist de Implementación

### Pre-Deploy
- [ ] Ejecutar `make secret-scan`
- [ ] Revisar `.env` - no dummy values
- [ ] Verificar permisos: `ls -la .env` (debe ser 600)
- [ ] Confirmar `.gitignore` incluye `.env`
- [ ] Tests passing: `pytest tests/security/test_secret_scanning.py`

### Post-Deploy
- [ ] Configurar pre-commit hooks
- [ ] Integrar en CI/CD pipeline
- [ ] Configurar alertas de Prometheus
- [ ] Documentar proceso de rotación
- [ ] Training para equipo de desarrollo

### Maintenance
- [ ] Scan semanal: `make secret-scan`
- [ ] Revisar findings en dashboard Grafana
- [ ] Rotar secretos cada 90 días
- [ ] Actualizar patrones de detección
- [ ] Audit log de accesos a secretos

---

**Documentación generada**: P012 - Secret Scanning & Hardening  
**Versión**: 1.0  
**Última actualización**: 2024-01-15
