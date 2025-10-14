# P011: Dependency Vulnerability Scan - Guía de Uso

## 📋 Resumen

**P011** implementa un sistema completo de escaneo de vulnerabilidades en dependencias Python, incluyendo:

- ✅ Detección de CVEs conocidos (pip-audit + safety)
- ✅ Identificación de paquetes desactualizados
- ✅ Validación de compatibilidad de licencias
- ✅ Verificación de integridad de dependency tree
- ✅ Tests automatizados de seguridad
- ✅ Reportes en múltiples formatos (JSON, HTML, Markdown)

## 🚀 Inicio Rápido

### 1. Instalar Herramientas

```bash
# Opción 1: Makefile (recomendado)
make install-security-tools

# Opción 2: Manual con Poetry
poetry add --group dev pip-audit safety pip-licenses
```

### 2. Ejecutar Escaneo

```bash
# Escaneo completo (output Markdown)
make security-deps

# Output JSON para CI/CD
make security-deps-json

# Output HTML interactivo
make security-deps-html
```

### 3. Ejecutar Tests Automatizados

```bash
# Todos los tests de seguridad de dependencias
pytest tests/security/test_dependency_security.py -v

# Solo tests críticos
pytest tests/security/test_dependency_security.py -m critical -v

# Solo tests de compliance
pytest tests/security/test_dependency_security.py -m compliance -v
```

## 📊 Descripción de Tests

### TestDependencyVulnerabilities (4 tests)

**Objetivo**: Detectar vulnerabilidades conocidas en dependencias.

| Test | Prioridad | Descripción |
|------|-----------|-------------|
| `test_no_critical_vulnerabilities` | 🔴 CRÍTICO | Bloquea si hay CVEs CRITICAL |
| `test_no_high_vulnerabilities` | 🟡 ALTA | Permite máximo 2 HIGH con excepción |
| `test_no_medium_vulnerabilities_in_critical_packages` | 🟡 ALTA | Valida paquetes core (FastAPI, SQLAlchemy, etc.) |
| `test_safety_check_passes` | 🟡 ALTA | Valida con Safety DB (complementa pip-audit) |

**Herramientas usadas**:
- `pip-audit`: PyPI Advisory Database + OSV
- `safety`: Safety DB (requiere API key para full scan)

**Ejemplo de salida**:
```
FAILED - Se encontraron 2 vulnerabilidades CRITICAL:
  - httpx 0.23.0: CVE-2023-12345 - Remote Code Execution via malformed headers
  - sqlalchemy 1.4.0: GHSA-XXXX-YYYY - SQL Injection in ORM queries
```

### TestDependencyFreshness (2 tests)

**Objetivo**: Asegurar que dependencias estén razonablemente actualizadas.

| Test | Umbral | Descripción |
|------|--------|-------------|
| `test_direct_dependencies_not_severely_outdated` | > 1 major version | Dependencias directas desactualizadas |
| `test_total_outdated_packages_reasonable` | < 30% | Porcentaje total de paquetes outdated |

**Ejemplo de salida**:
```
FAILED - Dependencias directas severamente desactualizadas (> 1 major version):
  - fastapi: 0.95.0 → 0.111.0 (actualizar con: poetry update fastapi)
  - pydantic: 1.10.0 → 2.8.2 (breaking changes, revisar changelog)
```

### TestLicenseCompliance (3 tests)

**Objetivo**: Validar compatibilidad de licencias con MIT/Apache 2.0.

| Test | Prioridad | Descripción |
|------|-----------|-------------|
| `test_no_copyleft_licenses_without_approval` | 🔴 CRÍTICO | Detecta GPL, AGPL, LGPL |
| `test_no_unknown_licenses` | 🟡 MEDIA | Máximo 5 paquetes con licencia desconocida |
| `test_licenses_compatible_with_project` | 🟢 BAJA | Valida licencias permisivas |

**Licencias permitidas**:
- ✅ MIT, Apache-2.0, BSD-3-Clause, BSD-2-Clause, ISC, PSF
- ⚠️ Copyleft (GPL, LGPL, AGPL) requieren aprobación legal
- ❌ Unknown requieren revisión manual

**Excepciones**: Documentar en `.security/license_exceptions.json`

### TestDependencyIntegrity (3 tests)

**Objetivo**: Validar integridad del dependency tree.

| Test | Validación | Descripción |
|------|------------|-------------|
| `test_pyproject_toml_has_version_constraints` | Versiones pinneadas | Detecta deps sin constraint (ej: `package = "*"`) |
| `test_no_duplicate_dependencies` | Duplicados | Valida que no hay múltiples versiones |
| `test_dependency_tree_has_no_conflicts` | pip check | Detecta conflictos de versión |

**Ejemplo de error**:
```
FAILED - Dependencias sin constraint de versión:
  - requests
  - beautifulsoup4

Usar: ^x.y.z (compatible), ~x.y.z (patch), o ">=x.y.z,<x+1.0.0" (range)
```

### TestProductionDependencies (2 tests)

**Objetivo**: Validar configuración de producción.

| Test | Ambiente | Descripción |
|------|----------|-------------|
| `test_production_dependencies_pinned` | Producción | Valida `requirements.prod.txt` con versiones exactas |
| `test_no_dev_dependencies_in_production` | Producción | Detecta pytest, ruff, etc. en prod |

**Nota**: Estos tests solo se ejecutan cuando `ENV=production`.

## 📁 Archivos Generados

### `.security/vuln-scan-{timestamp}.{format}`

**Contenido**:
- Timestamp y duración del escaneo
- Lista completa de vulnerabilidades con severidad
- Paquetes desactualizados (current → latest)
- Problemas de licencia
- Recomendaciones priorizadas

**Formatos disponibles**:
- **JSON**: Para integración con CI/CD
- **HTML**: Visualización interactiva con tablas
- **Markdown**: Para documentación y PRs

### `.security/vulnerability_exceptions.json`

**Propósito**: Documentar vulnerabilidades HIGH que están aprobadas temporalmente.

```json
{
  "vulnerability_exceptions": {
    "high": [
      {
        "package": "httpx",
        "vulnerability_id": "CVE-2023-12345",
        "approved": true,
        "reason": "Mitigated by WAF, fix expected in v0.25.0",
        "approved_by": "security-team@company.com",
        "approved_date": "2025-10-14",
        "expiry_date": "2025-11-14"
      }
    ]
  }
}
```

### `.security/license_exceptions.json`

**Propósito**: Aprobar licencias copyleft tras revisión legal.

```json
{
  "approved_copyleft": [
    "package-with-gpl-license"
  ],
  "notes": "GPL package approved for use in internal tools only, not distributed"
}
```

## 🔧 Configuración

### pyproject.toml

Agregar herramientas como dependencias de desarrollo:

```toml
[tool.poetry.group.dev.dependencies]
pip-audit = "^2.6.0"
safety = "^3.0.0"
pip-licenses = "^4.3.0"
```

### pytest.ini

Markers requeridos ya están configurados:

```ini
markers =
    security: Security tests
    critical: Critical security tests (blocking)
    high: High priority security tests
    compliance: License and compliance tests
    production: Production-specific tests
```

### Makefile

Ya integrado con los siguientes comandos:

```makefile
make security-deps          # Escaneo completo (Markdown)
make security-deps-json     # Escaneo completo (JSON)
make security-deps-html     # Escaneo completo (HTML)
make install-security-tools # Instalar pip-audit, safety, pip-licenses
```

## 🚦 Integración con CI/CD

### GitHub Actions

```yaml
name: Security Scan

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sundays

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install Poetry
        run: pip install poetry

      - name: Install dependencies
        run: |
          poetry install --all-extras
          poetry add --group dev pip-audit safety pip-licenses

      - name: Run dependency vulnerability scan
        run: |
          poetry run python scripts/security/vulnerability_scan.py \
            --format json \
            --output security-report.json

      - name: Upload security report
        uses: actions/upload-artifact@v4
        with:
          name: security-report
          path: security-report.json

      - name: Run security tests
        run: |
          poetry run pytest tests/security/test_dependency_security.py \
            -v \
            --junit-xml=security-tests.xml

      - name: Fail on CRITICAL vulnerabilities
        run: |
          if [ $? -eq 2 ]; then
            echo "CRITICAL vulnerabilities found!"
            exit 1
          fi
```

### GitLab CI

```yaml
security:dependency-scan:
  stage: security
  image: python:3.12
  script:
    - pip install poetry pip-audit safety pip-licenses
    - poetry install --all-extras
    - poetry run python scripts/security/vulnerability_scan.py --format json --output vuln-scan.json
  artifacts:
    reports:
      dependency_scanning: vuln-scan.json
    paths:
      - vuln-scan.json
    expire_in: 30 days
  only:
    - merge_requests
    - main
```

## 📈 Métricas y SLOs

### Security Health Score

Calculado automáticamente en cada escaneo:

| Métrica | Peso | Umbral Objetivo |
|---------|------|-----------------|
| CRITICAL vulnerabilities | 40% | 0 |
| HIGH vulnerabilities | 30% | ≤ 2 (con excepciones) |
| MEDIUM vulnerabilities | 15% | ≤ 10 |
| Paquetes desactualizados | 10% | < 30% |
| Problemas de licencia | 5% | 0 copyleft sin aprobar |

**Score = 100 - (penalización acumulada)**

- 🟢 **90-100**: Excelente (PASS)
- 🟡 **70-89**: Aceptable (PASS con warnings)
- 🔴 **< 70**: Crítico (BLOCK deployment)

### SLOs de Seguridad

| SLO | Objetivo | Medición |
|-----|----------|----------|
| Tiempo de resolución CRITICAL | < 24h | Desde detección hasta patch deployed |
| Tiempo de resolución HIGH | < 7 días | Desde detección hasta patch deployed |
| Cobertura de escaneo | 100% de dependencias | Todas las deps escaneadas semanalmente |
| False positive rate | < 5% | Vulnerabilidades reportadas que son FP |

## 🔍 Troubleshooting

### Error: `pip-audit` no encontrado

```bash
# Instalar en entorno Poetry
poetry add --group dev pip-audit

# Verificar instalación
poetry run pip-audit --version
```

### Error: `safety` retorna "Database outdated"

```bash
# Safety DB se actualiza automáticamente
# Para forzar actualización (requiere API key):
export SAFETY_API_KEY=your-key
poetry run safety check --update
```

### Error: `pip-licenses` tarda mucho

```bash
# Reducir timeout si hay paquetes problemáticos
poetry run pip-licenses --format json --timeout 30
```

### Error: Test `test_no_high_vulnerabilities` falla en CI

1. Revisar si la vulnerabilidad está documentada
2. Crear excepción en `.security/vulnerability_exceptions.json`
3. Commit y push del archivo de excepciones
4. Re-run del pipeline

### Error: Demasiados paquetes desactualizados

```bash
# Ver lista completa
pip list --outdated

# Actualizar interactivamente
poetry update --dry-run  # Ver qué se actualizaría
poetry update             # Actualizar todo
poetry update fastapi     # Actualizar solo un paquete
```

## 📚 Referencias

- **OWASP Top 10 2021 - A06**: Vulnerable and Outdated Components
- **NIST NVD**: https://nvd.nist.gov/
- **PyPI Advisory Database**: https://github.com/pypa/advisory-database
- **OSV Database**: https://osv.dev/
- **Safety DB**: https://pyup.io/safety/

## 🎯 Próximos Pasos (FASE 3)

- ✅ **P011**: Dependency Vulnerability Scan (COMPLETADO)
- ⏸️ **P012**: Secret Scanning & Hardening
- ⏸️ **P013**: OWASP Top 10 Validation
- ⏸️ **P014**: Security Compliance Report

---

**Última actualización**: 2025-10-14  
**Responsable**: Equipo de Seguridad  
**Próxima revisión**: 2025-11-14
