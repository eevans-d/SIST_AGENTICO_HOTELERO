# P013: OWASP Top 10 2021 Validation Guide

**Version**: 1.0.0  
**Last Updated**: 2025-01-XX  
**Owner**: Security Team  
**Status**: ✅ Production Ready

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [OWASP Top 10 2021 Coverage](#owasp-top-10-2021-coverage)
3. [Installation & Setup](#installation--setup)
4. [Usage](#usage)
5. [Detection Capabilities](#detection-capabilities)
6. [Compliance Scoring](#compliance-scoring)
7. [CI/CD Integration](#cicd-integration)
8. [Remediation Guide](#remediation-guide)
9. [Appendix: CWE Mappings](#appendix-cwe-mappings)

---

## Overview

### Purpose

**OWASP Validator** es una herramienta de análisis estático que valida compliance contra **OWASP Top 10 2021**, proporcionando:

- ✅ **Detección automatizada** de 10 categorías de vulnerabilidades
- ✅ **Compliance scoring** (0-100) con severity weighting
- ✅ **77 CWE mappings** para trazabilidad
- ✅ **Multi-format export** (JSON, Markdown)
- ✅ **CI/CD integration** con exit codes

### Scope

**Categorías OWASP 2021**:

| ID | Category | CWE Count | Detection Methods |
|----|----------|-----------|-------------------|
| **A01** | Broken Access Control | 34 | Regex patterns, static analysis |
| **A02** | Cryptographic Failures | 8 | Algorithm detection, key analysis |
| **A03** | Injection | 9 | Pattern matching, AST parsing |
| **A04** | Insecure Design | 5 | Architectural checks |
| **A05** | Security Misconfiguration | 9 | Config validation |
| **A06** | Vulnerable Components | 2 | Integration with P011 |
| **A07** | Authentication Failures | 8 | Auth flow analysis |
| **A08** | Data Integrity Failures | 6 | Deserialization checks |
| **A09** | Logging and Monitoring | 3 | Logging coverage analysis |
| **A10** | SSRF | 3 | URL validation checks |

**Total**: 10 categories, 77 CWE mappings, 100+ detection patterns

---

## OWASP Top 10 2021 Coverage

### A01: Broken Access Control

**Description**: Failures related to access control allowing unauthorized data/function access.

**CWE IDs**: 22, 23, 35, 59, 200, 201, 219, 264, 275, 276, 284, 285, 352, 359, 377, 402, 425, 441, 497, 538, 540, 548, 552, 566, 601, 639, 651, 668, 706, 862, 863, 913, 922, 1275

**Detection Methods**:
- Missing authorization decorators on router endpoints
- Path traversal vulnerabilities (concatenation in `open()`, `Path()`)
- Insecure Direct Object References (IDOR)
- Tenant isolation checks in queries

**Example Findings**:
```python
# ❌ Missing Authorization
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    # No Depends(get_current_user)
    return db.query(User).filter(User.id == user_id).first()

# ✅ Correct
@router.get("/users/{user_id}")
async def get_user(user_id: int, current_user: User = Depends(get_current_user)):
    # Authorization enforced
    return db.query(User).filter(User.id == user_id, User.tenant_id == current_user.tenant_id).first()
```

**Remediation**:
1. Add `Depends(get_current_user)` to all protected endpoints
2. Validate object ownership before access
3. Use parameterized paths with validation
4. Implement tenant isolation in all queries

---

### A02: Cryptographic Failures

**Description**: Failures related to cryptography, often leading to exposure of sensitive data.

**CWE IDs**: 259, 327, 328, 329, 330, 331, 335, 338

**Detection Methods**:
- Weak algorithms (MD5, SHA1, DES, RC4)
- Hardcoded encryption keys
- TLS version enforcement (1.2+)
- Sensitive data encryption at rest

**Example Findings**:
```python
# ❌ Weak Algorithm
import hashlib
password_hash = hashlib.md5(password.encode()).hexdigest()

# ✅ Correct
import bcrypt
password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# ❌ Hardcoded Key
SECRET_KEY = "my-secret-key-12345"

# ✅ Correct
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise ValueError("SECRET_KEY must be set and >= 32 chars")
```

**Remediation**:
1. Use SHA256, SHA3, or bcrypt for hashing
2. Use AES-256 for encryption
3. Store keys in environment variables or secrets manager
4. Enforce TLS 1.2+ in configurations
5. Encrypt sensitive fields at rest (e.g., `EncryptedField`)

---

### A03: Injection

**Description**: User-supplied data not validated, filtered, or sanitized.

**CWE IDs**: 74, 75, 77, 78, 79, 88, 89, 91, 917

**Detection Methods**:
- SQL injection (string concatenation in queries)
- NoSQL injection ($where, $ne patterns)
- Command injection (os.system, subprocess with user input)
- LDAP injection
- XSS (innerHTML, document.write)
- Prompt injection (LLM-specific)

**Example Findings**:
```python
# ❌ SQL Injection
query = f"SELECT * FROM users WHERE username = '{username}'"
db.execute(query)

# ✅ Correct (Parameterized Query)
query = "SELECT * FROM users WHERE username = :username"
db.execute(query, {"username": username})

# ❌ Command Injection
os.system(f"ping {user_input}")

# ✅ Correct
import subprocess
subprocess.run(["ping", "-c", "1", user_input], check=True)

# ❌ XSS
html = f"<div>{user_input}</div>"

# ✅ Correct
from html import escape
html = f"<div>{escape(user_input)}</div>"
```

**Remediation**:
1. **Always use parameterized queries** (SQLAlchemy ORM, async drivers)
2. **Never use `os.system()` or `eval()` with user input**
3. Use subprocess with list arguments (not shell=True)
4. Sanitize/escape all user input before rendering
5. Implement input validation with Pydantic models
6. For AI agents: sanitize prompts against injection attacks

---

### A04: Insecure Design

**Description**: Missing or ineffective control design (architectural flaws).

**CWE IDs**: 209, 256, 501, 522, 799

**Detection Methods**:
- Missing rate limiting
- No input validation
- Business logic flaws (e.g., bookings in the past)

**Example Findings**:
```python
# ❌ Missing Rate Limiting
@router.post("/login")
async def login(credentials: LoginRequest):
    # No rate limit - brute force vulnerable
    return authenticate(credentials)

# ✅ Correct
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")
async def login(credentials: LoginRequest):
    return authenticate(credentials)
```

**Remediation**:
1. Implement rate limiting (slowapi + Redis)
2. Add input validation (Pydantic schemas)
3. Validate business logic (dates, quantities, state transitions)
4. Design threat modeling sessions for critical flows

---

### A05: Security Misconfiguration

**Description**: Missing appropriate security hardening or misconfigured permissions.

**CWE IDs**: 2, 11, 13, 15, 16, 260, 315, 520, 526

**Detection Methods**:
- DEBUG mode enabled in production
- Missing security headers (X-Content-Type-Options, X-Frame-Options, CSP)
- CORS misconfiguration (allow_origins=["*"])
- Default credentials

**Example Findings**:
```python
# ❌ DEBUG Enabled
DEBUG = True  # In .env for production

# ✅ Correct
DEBUG = False  # Or os.getenv("DEBUG", "false").lower() == "true"

# ❌ Missing Security Headers
app = FastAPI()

# ✅ Correct
from app.core.middleware import security_headers_middleware
app.add_middleware(security_headers_middleware)

# Headers added:
# - X-Content-Type-Options: nosniff
# - X-Frame-Options: DENY
# - Content-Security-Policy: default-src 'self'
```

**Remediation**:
1. Disable DEBUG in production (.env validation)
2. Add security headers middleware
3. Configure CORS with explicit allowed origins
4. Remove default credentials (check P012 secret scan)
5. Run security configuration audits

---

### A06: Vulnerable and Outdated Components

**Description**: Using components with known vulnerabilities.

**CWE IDs**: 1104, 1329

**Detection Methods**:
- Integration with P011 (dependency vulnerability scan)
- Reports vulnerable package count from `.security/vuln-scan-latest.json`

**Example Output**:
```json
{
  "category": "A06",
  "severity": "CRITICAL",
  "finding_type": "Vulnerable Dependencies",
  "description": "Found 12 vulnerable dependencies",
  "recommendation": "Run 'make security-deps' and update packages"
}
```

**Remediation**:
1. Run `make security-deps` to scan dependencies
2. Update vulnerable packages: `poetry update <package>`
3. Review breaking changes before upgrading
4. Set up automated dependency updates (Dependabot)

---

### A07: Identification and Authentication Failures

**Description**: Confirmation of user identity, authentication, or session management issues.

**CWE IDs**: 255, 259, 287, 288, 290, 294, 295, 306, 307

**Detection Methods**:
- Weak JWT configuration (HS256 + hardcoded secret)
- Missing password complexity validation
- No account lockout after failed attempts

**Example Findings**:
```python
# ❌ Weak JWT
import jwt
token = jwt.encode({"user": "admin"}, "secret", algorithm="HS256")

# ✅ Correct
import jwt
from app.core.settings import settings

token = jwt.encode(
    {"user": "admin"},
    settings.secret_key.get_secret_value(),
    algorithm="HS256"
)

# ❌ No Password Complexity
password = request.password  # No validation

# ✅ Correct
from pydantic import BaseModel, validator

class PasswordChange(BaseModel):
    password: str
    
    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain uppercase letter")
        if not re.search(r'[0-9]', v):
            raise ValueError("Password must contain digit")
        return v
```

**Remediation**:
1. Use environment variables for JWT secrets (P012)
2. Implement password complexity validation (min 8 chars, uppercase, digit, special)
3. Add account lockout after 5 failed login attempts
4. Use secure session management (HTTPOnly cookies, SameSite)

---

### A08: Software and Data Integrity Failures

**Description**: Code and infrastructure that doesn't protect against integrity violations.

**CWE IDs**: 345, 353, 426, 494, 502, 565, 784, 829

**Detection Methods**:
- Insecure deserialization (pickle.loads)
- eval()/exec() with external data
- yaml.load() without safe_load
- Unvalidated file uploads

**Example Findings**:
```python
# ❌ Insecure Deserialization
import pickle
data = pickle.loads(user_input)

# ✅ Correct
import json
data = json.loads(user_input)

# ❌ yaml.load (arbitrary code execution)
import yaml
config = yaml.load(file)

# ✅ Correct
import yaml
config = yaml.safe_load(file)
```

**Remediation**:
1. **Never use pickle with untrusted data** - use JSON
2. Replace `yaml.load()` with `yaml.safe_load()`
3. Validate file uploads (content-type, extension, size)
4. Implement integrity checks (HMAC signatures)

---

### A09: Security Logging and Monitoring Failures

**Description**: Insufficient logging, detection, monitoring, and active response.

**CWE IDs**: 778, 779, 223

**Detection Methods**:
- Missing security event logging
- No authentication failure logging
- PII in logs (not masked)

**Example Findings**:
```python
# ❌ No Logging
@router.post("/login")
async def login(credentials: LoginRequest):
    user = authenticate(credentials)
    # No logging of success/failure
    return {"token": generate_token(user)}

# ✅ Correct
import logging
logger = logging.getLogger(__name__)

@router.post("/login")
async def login(credentials: LoginRequest):
    try:
        user = authenticate(credentials)
        logger.info(f"Login successful for user {user.id}")
        return {"token": generate_token(user)}
    except AuthenticationError:
        logger.warning(f"Failed login attempt for {credentials.username}")
        raise
```

**Remediation**:
1. Log all authentication events (success/failure)
2. Log authorization failures
3. Mask sensitive data in logs (passwords, tokens, PII)
4. Implement log aggregation (e.g., ELK stack, Grafana Loki)
5. Set up alerting for suspicious patterns

---

### A10: Server-Side Request Forgery (SSRF)

**Description**: Fetching remote resources without validating user-supplied URL.

**CWE IDs**: 601, 918

**Detection Methods**:
- Unvalidated redirects
- Arbitrary URL fetch from user input (requests.get, httpx.get)
- Open redirect vulnerabilities

**Example Findings**:
```python
# ❌ Unvalidated URL Fetch
import requests
url = request.query_params.get("url")
response = requests.get(url)

# ✅ Correct
ALLOWED_DOMAINS = ["api.example.com", "cdn.example.com"]

def validate_url(url: str) -> bool:
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    return domain in ALLOWED_DOMAINS

url = request.query_params.get("url")
if not validate_url(url):
    raise ValueError("Invalid URL domain")
response = requests.get(url)

# ❌ Open Redirect
@router.get("/redirect")
async def redirect(url: str):
    return RedirectResponse(url)

# ✅ Correct
ALLOWED_REDIRECTS = ["/dashboard", "/profile", "/settings"]

@router.get("/redirect")
async def redirect(url: str):
    if url not in ALLOWED_REDIRECTS:
        raise ValueError("Invalid redirect target")
    return RedirectResponse(url)
```

**Remediation**:
1. Whitelist allowed domains for external requests
2. Validate redirect targets against whitelist
3. Block internal IP ranges (127.0.0.1, 169.254.*, 10.*, 192.168.*)
4. Use DNS rebinding protection

---

## Installation & Setup

### Prerequisites

- Python 3.10+
- Project dependencies installed (`poetry install`)

### No Additional Dependencies

El validator utiliza solo bibliotecas estándar de Python:
- `re` (regex patterns)
- `pathlib` (file system traversal)
- `json` (export)
- `dataclasses` (data structures)

---

## Usage

### Basic Usage

#### 1. Run Markdown Report

```bash
python scripts/security/owasp_validator.py --format markdown
```

**Output**: `.security/owasp-scan-latest.md` con findings detallados.

#### 2. Run JSON Report (CI/CD)

```bash
python scripts/security/owasp_validator.py --format json --output .security/owasp-scan-latest.json
```

**Output**: JSON estructurado con todos los findings.

#### 3. Scan Specific Category

```bash
# Solo A03: Injection
python scripts/security/owasp_validator.py --category A03 --format markdown
```

#### 4. Verbose Mode

```bash
python scripts/security/owasp_validator.py --verbose --format markdown
```

### Makefile Integration

```bash
# Scan completo (Markdown)
make owasp-scan

# JSON para CI/CD
make owasp-scan-json

# Scan categoría específica
make owasp-scan-category CATEGORY=A03

# View last report
make owasp-report
```

---

## Detection Capabilities

### Pattern-Based Detection

**Injection Patterns** (`INJECTION_PATTERNS`):
```python
{
    "sql_injection": r'(SELECT|INSERT|UPDATE|DELETE).*\+.*(WHERE|FROM)',
    "nosql_injection": r'\$where.*\$ne.*\$or',
    "command_injection": r'(subprocess|os\.system|eval|exec)\s*\(.*\+.*\)',
    "ldap_injection": r'ldap.*search.*\+.*\)',
}
```

**XSS Patterns** (`XSS_PATTERNS`):
```python
{
    "reflected_xss": r'(innerHTML|outerHTML|document\.write).*request\.',
    "stored_xss": r'(innerHTML|outerHTML).*(?:database|db|mongo)',
}
```

**SSRF Patterns** (`SSRF_PATTERNS`):
```python
{
    "unvalidated_redirect": r'redirect\(.*request\.',
    "arbitrary_url_fetch": r'(requests\.get|httpx\.get)\s*\(.*request\.',
}
```

### Static Code Analysis

**Checks**:
1. **Authorization**: Missing `Depends()` decorators on router endpoints
2. **Cryptography**: Weak algorithms, hardcoded keys
3. **Configuration**: DEBUG mode, security headers, CORS
4. **Authentication**: JWT secrets, password complexity
5. **Deserialization**: pickle, eval, yaml.load
6. **Logging**: Missing logger usage in auth modules

### Integration Checks

**P011 Integration** (A06):
- Reads `.security/vuln-scan-latest.json`
- Reports vulnerable dependency count
- Severity: CRITICAL if >=5 vulnerabilities

---

## Compliance Scoring

### Scoring Formula

```python
def calculate_compliance_score(findings: List[OWASPFinding]) -> float:
    weights = {
        "CRITICAL": 10,
        "HIGH": 5,
        "MEDIUM": 2,
        "LOW": 1
    }
    
    total_weight = sum(weights[f.severity] for f in findings)
    baseline = 100
    
    score = max(0, 100 - (total_weight / baseline * 100))
    return round(score, 2)
```

### Severity Definitions

| Severity | Weight | Criteria | Examples |
|----------|--------|----------|----------|
| **CRITICAL** | 10 | Immediate exploitation, data breach | SQL injection, insecure deserialization, weak crypto |
| **HIGH** | 5 | Likely exploitation, significant impact | Missing auth, path traversal, SSRF |
| **MEDIUM** | 2 | Possible exploitation, moderate impact | Missing headers, weak password policy |
| **LOW** | 1 | Unlikely exploitation, minimal impact | Logging issues, info disclosure |

### Score Thresholds

| Score Range | Risk Level | Exit Code | Action Required |
|-------------|------------|-----------|-----------------|
| **70-100** | ✅ **LOW** | 0 | Continue, monitor |
| **50-69** | ⚠️ **MEDIUM** | 1 | Remediate HIGH/CRITICAL |
| **0-49** | 🚨 **HIGH** | 2 | STOP - Immediate remediation |

### Example Calculation

**Findings**:
- 2 CRITICAL (SQL injection, weak JWT): 2 × 10 = 20
- 5 HIGH (missing auth): 5 × 5 = 25
- 3 MEDIUM (missing headers): 3 × 2 = 6
- 1 LOW (logging): 1 × 1 = 1

**Total Weight**: 20 + 25 + 6 + 1 = 52

**Score**: 100 - (52/100 × 100) = **48%** → 🚨 **HIGH RISK** (Exit code 2)

---

## CI/CD Integration

### GitHub Actions

```yaml
name: OWASP Top 10 Validation

on:
  pull_request:
  push:
    branches: [main, develop]

jobs:
  owasp-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install --no-root
      
      - name: Run OWASP Validator
        run: |
          python scripts/security/owasp_validator.py \
            --format json \
            --output .security/owasp-scan-latest.json
      
      - name: Check Compliance Score
        run: |
          score=$(jq '.compliance_score' .security/owasp-scan-latest.json)
          if (( $(echo "$score < 70" | bc -l) )); then
            echo "❌ Compliance score $score < 70 (FAIL)"
            exit 1
          fi
          echo "✅ Compliance score $score >= 70 (PASS)"
      
      - name: Upload Report
        uses: actions/upload-artifact@v3
        with:
          name: owasp-report
          path: .security/owasp-scan-latest.json
```

### GitLab CI

```yaml
owasp-validation:
  stage: security
  image: python:3.10
  script:
    - pip install poetry
    - poetry install --no-root
    - python scripts/security/owasp_validator.py --format json --output owasp-report.json
    - |
      SCORE=$(jq '.compliance_score' owasp-report.json)
      if [ $(echo "$SCORE < 70" | bc) -eq 1 ]; then
        echo "❌ OWASP compliance score $SCORE < 70"
        exit 1
      fi
  artifacts:
    reports:
      security: owasp-report.json
    paths:
      - owasp-report.json
    expire_in: 30 days
  allow_failure: false
```

### Pre-Commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash

echo "🔍 Running OWASP Top 10 validation..."

python scripts/security/owasp_validator.py --format json --output /tmp/owasp-scan.json

EXIT_CODE=$?

if [ $EXIT_CODE -eq 2 ]; then
    echo "🚨 CRITICAL: OWASP compliance score < 50"
    echo "Review findings in /tmp/owasp-scan.json"
    exit 1
elif [ $EXIT_CODE -eq 1 ]; then
    echo "⚠️ WARNING: OWASP compliance score 50-69"
    echo "Consider fixing HIGH/CRITICAL findings before pushing"
    # Don't block commit, just warn
fi

echo "✅ OWASP validation passed"
exit 0
```

---

## Remediation Guide

### Priority Matrix

| Severity | Timeframe | Examples | Action |
|----------|-----------|----------|--------|
| **CRITICAL** | **< 24h** | SQL injection, weak crypto, insecure deserialization | Immediate fix + hotfix deploy |
| **HIGH** | **< 1 week** | Missing auth, path traversal, SSRF | Schedule fix in current sprint |
| **MEDIUM** | **< 1 month** | Missing headers, weak password policy | Backlog, next sprint |
| **LOW** | **< 3 months** | Logging improvements | Tech debt backlog |

### Remediation Workflow

1. **Review Findings**:
   ```bash
   make owasp-report
   # Opens .security/owasp-scan-latest.md
   ```

2. **Prioritize by Severity**:
   - CRITICAL: Stop feature work, fix immediately
   - HIGH: Add to current sprint
   - MEDIUM/LOW: Schedule for future sprints

3. **Fix & Validate**:
   ```bash
   # Make changes
   git add .
   
   # Re-run scan
   make owasp-scan
   
   # Verify finding is resolved
   ```

4. **Document Exceptions**:
   - If finding is false positive, document in `.security/owasp-exceptions.yml`:
     ```yaml
     exceptions:
       - category: A03
         file: app/services/legacy_query.py
         line: 42
         reason: "Legacy code, scheduled for refactor Q2 2025"
         approved_by: "security-team@example.com"
         expires: "2025-06-30"
     ```

---

## Appendix: CWE Mappings

### Complete CWE Reference

**A01: Broken Access Control** (34 CWEs):
- CWE-22: Path Traversal
- CWE-284: Improper Access Control
- CWE-352: CSRF
- CWE-862: Missing Authorization
- CWE-863: Incorrect Authorization
- ... (full list in script)

**A02: Cryptographic Failures** (8 CWEs):
- CWE-259: Use of Hard-coded Password
- CWE-327: Use of Broken Crypto
- CWE-328: Weak Hash
- ... (full list in script)

**A03: Injection** (9 CWEs):
- CWE-78: OS Command Injection
- CWE-79: XSS
- CWE-89: SQL Injection
- CWE-917: Expression Language Injection
- ... (full list in script)

**[Remaining categories follow same pattern]**

---

## Support & Resources

### Internal Resources

- **Security Team**: security@example.com
- **Slack Channel**: #security-qa
- **Runbook**: `docs/OPERATIONS_MANUAL.md`

### External References

- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST SP 800-53](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final)

---

**Document Version**: 1.0.0  
**Last Review**: 2025-01-XX  
**Next Review**: 2025-04-XX (Quarterly)
