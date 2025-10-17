# 🔐 Reporte de Secret Scanning - P012

## 📊 Resumen Ejecutivo

- **Fecha:** 2025-10-17T04:18:10.534338
- **Duración:** 17.37 segundos
- **Estado:** CRITICAL - Immediate action required

### Métricas

| Métrica | Valor |
|---------|-------|
| Total issues | 25 |
| CRITICAL | 3 |
| HIGH | 22 |
| MEDIUM | 0 |
| LOW | 0 |
| Secret findings | 17 |
| Environment issues | 6 |
| Permission issues | 2 |
| Git history issues | 0 |

---

## 🔍 Hardcoded Secrets Found (17)

| File | Line | Type | Severity | Description | Recommendation |
|------|------|------|----------|-------------|----------------|
| scripts/validate_indexes.sh | L32 | password_assignment | **HIGH** | Hardcoded password | Move password to environment variable or secrets manager.... |
| scripts/validate_indexes.sh | L76 | password_assignment | **HIGH** | Hardcoded password | Move password to environment variable or secrets manager.... |
| scripts/validate_indexes.sh | L107 | password_assignment | **HIGH** | Hardcoded password | Move password to environment variable or secrets manager.... |
| docker/alertmanager/config-audio.yml | L6 | password_assignment | **HIGH** | Hardcoded password | Move password to environment variable or secrets manager.... |
| app/security/advanced_jwt_auth.py | L81 | password_assignment | **HIGH** | Hardcoded password | Move password to environment variable or secrets manager.... |
| tests/security/test_secret_scanning.py | L114 | password_assignment | **HIGH** | Hardcoded password | Move password to environment variable or secrets manager.... |
| tests/security/test_secret_scanning.py | L115 | password_assignment | **HIGH** | Hardcoded password | Move password to environment variable or secrets manager.... |
| tests/security/test_secret_scanning.py | L116 | password_assignment | **HIGH** | Hardcoded password | Move password to environment variable or secrets manager.... |
| tests/security/test_secret_scanning.py | L224 | connection_string | **HIGH** | Database connection string with embedded credentials | Use environment variables for credentials. Never commit conn... |
| tests/security/test_secret_scanning.py | L225 | connection_string | **HIGH** | Database connection string with embedded credentials | Use environment variables for credentials. Never commit conn... |
| tests/security/test_secret_scanning.py | L226 | connection_string | **HIGH** | Database connection string with embedded credentials | Use environment variables for credentials. Never commit conn... |
| tests/security/test_advanced_jwt_auth.py | L42 | password_assignment | **HIGH** | Hardcoded password | Move password to environment variable or secrets manager.... |
| tests/security/test_advanced_jwt_auth.py | L51 | password_assignment | **HIGH** | Hardcoded password | Move password to environment variable or secrets manager.... |
| tests/security/test_advanced_jwt_auth.py | L128 | password_assignment | **HIGH** | Hardcoded password | Move password to environment variable or secrets manager.... |
| tests/security/test_advanced_jwt_auth.py | L204 | password_assignment | **HIGH** | Hardcoded password | Move password to environment variable or secrets manager.... |
| tests/security/test_advanced_jwt_auth.py | L534 | password_assignment | **HIGH** | Hardcoded password | Move password to environment variable or secrets manager.... |
| tests/security/test_advanced_jwt_auth.py | L535 | password_assignment | **HIGH** | Hardcoded password | Move password to environment variable or secrets manager.... |


## 🔐 Environment Variable Issues (6)

| Variable | Issue Type | Severity | Recommendation |
|----------|------------|----------|----------------|
| SECRET_KEY | dummy_value | **CRITICAL** | Replace dummy value with secure SECRET_KEY. Generate with: openssl rand -hex 32 |
| POSTGRES_PASSWORD | dummy_value | **CRITICAL** | Replace dummy value with secure POSTGRES_PASSWORD. Generate with: openssl rand -hex 32 |
| REDIS_PASSWORD | dummy_value | **CRITICAL** | Replace dummy value with secure REDIS_PASSWORD. Generate with: openssl rand -hex 32 |
| WHATSAPP_ACCESS_TOKEN | weak_value | **HIGH** | WHATSAPP_ACCESS_TOKEN is too short (min: 50 chars). Use stronger value. |
| .gitignore | insecure_default | **HIGH** | Add 'secrets.json' to .gitignore to prevent accidental commits |
| .gitignore | insecure_default | **HIGH** | Add 'credentials.json' to .gitignore to prevent accidental commits |


## 🔒 File Permission Issues (2)

| File | Current | Expected | Severity | Risk Description |
|------|---------|----------|----------|------------------|
| .env | 0644 | 0600 | **HIGH** | File .env is readable by others. Should be restricted to owner only. |
| .env.production | 0644 | 0600 | **HIGH** | File .env.production is readable by others. Should be restricted to owner only. |


## ✅ No secrets in git history


## 💡 Recomendaciones

- 🔴 URGENT: Replace dummy values in .env with secure secrets
- ⚠️  Fix 2 file permission issues with: chmod 600 <file>
- Move all hardcoded secrets to environment variables or secrets management system

