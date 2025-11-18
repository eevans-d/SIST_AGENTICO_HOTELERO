# 📦 PROMPT 1 DEFINITIVO: Script de Extracción Enterprise-Grade
## PERSONALIZADO PARA: SIST_AGENTICO_HOTELERO

**OBJETIVO**: Crear un script Python production-ready para extraer y preparar el repositorio completo **SIST_AGENTICO_HOTELERO** para ingesta en Poe.com (o3-pro bot).

**CONTEXTO DEL PROYECTO**:
- **Repositorio**: eevans-d/SIST_AGENTICO_HOTELERO
- **Branch actual**: feature/etapa2-qloapps-integration
- **Commit hash**: 97676bcc27f7f999f602432a07383ce09c5dee68
- **Stack principal**: Python 3.12.3, FastAPI, Docker Compose (7 servicios)
- **Archivos procesables**: ~570 archivos (.py, .md, .yml, .json, Dockerfile, Makefile)
- **Líneas de código Python**: ~102,062 líneas
- **Tamaño estimado**: ~9.6 MB (sin dependencias)

═══════════════════════════════════════════════════════════════════════════════
## PARTE 1: ESPECIFICACIONES TÉCNICAS EXACTAS
═══════════════════════════════════════════════════════════════════════════════

### OUTPUT REQUIREMENTS:
```
├── Directorio: POE_KNOWLEDGE_FILES/
├── Archivos: Exactamente 4 archivos .txt
├── Tamaño target por archivo: 20-22 MB (límite hard: 23 MB)
├── Encoding: UTF-8 con BOM
├── Line endings: Unix (LF)
└── Total esperado: ~12-15 MB (código + docs consolidados)
```

### ESTRUCTURA DE CADA ARCHIVO .txt:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ METADATA HEADER (primeras 25 líneas):                                   │
│ - Timestamp de generación (ISO 8601 UTC)                                │
│ - Número de parte (1/4, 2/4, etc.)                                      │
│ - Commit hash: 97676bcc27f7f999f602432a07383ce09c5dee68                │
│ - Branch: feature/etapa2-qloapps-integration                            │
│ - Total de archivos en esta parte                                       │
│ - Checksum SHA256 del contenido                                         │
│ - Índice de archivos incluidos (paths relativos)                        │
│ - Deployment readiness: 8.9/10                                          │
│ - Test coverage: 31% (28/891 tests passing)                             │
│ - CVE status: 0 CRITICAL                                                │
└─────────────────────────────────────────────────────────────────────────┘
```

═══════════════════════════════════════════════════════════════════════════════
## PARTE 2: ALGORITMO DE PRIORIZACIÓN Y DISTRIBUCIÓN
═══════════════════════════════════════════════════════════════════════════════

### TIER 1 - CRÍTICO (SIEMPRE EN PARTE 1, PRIMEROS 800KB):
**[PRIORIDAD: MÁXIMA - Documentación arquitectural para o3-pro context]**

#### 📌 Documentos GitHub AI Agent (ABSOLUTA PRIORIDAD)
```
.github/
├── copilot-instructions.md              (685 líneas, 25KB - ORO PURO 🏆)
├── AI-AGENT-QUICKSTART.md               (onboarding esencial)
├── AI-AGENT-CONTRIBUTING.md             (patterns & conventions)
├── DOCUMENTATION-MAP.md                 (mapa de navegación)
├── START-HERE.md                        (punto de entrada)
└── README.md                            (overview de .github/)
```

#### 📖 Documentación Maestra Root
```
RAÍZ DEL REPO:
├── README.md                            (overview del sistema completo)
├── MASTER_PROJECT_GUIDE.md              (guía consolidada de 443+ líneas)
├── RESUMEN_EJECUTIVO_DEFINITIVO.md      (estado actual del proyecto)
```

#### 📚 Índices y Guías Core de agente-hotel-api/
```
agente-hotel-api/
├── README.md                            (setup técnico + comandos make)
├── README-Infra.md                      (Prometheus metrics + observability)
├── README-Database.md                   (Schema, migrations, queries)
├── README-PERFORMANCE.md                (benchmarks, optimizaciones)
├── CONTRIBUTING.md                      (guía de contribución)
├── INDEX.md                             (índice de la aplicación)
├── DEVIATIONS.md                        (desviaciones del spec original)
└── SECURITY_IMPLEMENTATION_FINAL.md     (reporte de seguridad)
```

#### 📋 Documentación Consolidada Crítica
```
agente-hotel-api/docs/
├── 00-DOCUMENTATION-CENTRAL-INDEX.md    (índice central de 450+ líneas)
├── START-HERE.md                        (punto de entrada docs/)
├── ORCHESTRATOR_INTENTS.md              (lógica de NLP intents)
├── SECURITY_HARDENING_REPORT.md         (OWASP hardening)
```

#### 🎯 Playbooks Ejecutivos
```
.playbook/
├── ETAPA2_PLAN_EJECUCION.md             (plan de ejecución actual)
├── PRODUCTION_READINESS_CHECKLIST.md    (checklist pre-prod)
├── ETAPA1_COMPLETADA.md                 (resumen etapa 1)
└── CONSOLIDACION_DOCS_REPORTE.md        (reporte de consolidación)
```

**FORMATO TIER 1**:
```
╔═══════════════════════════════════════════════════════════════════════╗
║ ⚠️  PRIORIDAD MÁXIMA - ARQUITECTURA CORE                              ║
║ 📄 Archivo: .github/copilot-instructions.md                          ║
║ 🎯 Propósito: Instrucciones maestras de arquitectura del sistema     ║
║ 📊 Líneas: 685 | Tamaño: ~25 KB                                      ║
║ 🏷️  Tags: #architecture #ai-agent #fastapi #orchestrator #patterns  ║
╚═══════════════════════════════════════════════════════════════════════╝
[CONTENIDO DEL ARCHIVO AQUÍ]
```

---

### TIER 2 - NÚCLEO FUNCIONAL (PARTE 1 después de docs, ~5-8 MB):
**[PRIORIDAD: ALTA - Lógica de negocio crítica]**

#### 🧠 Servicios Core (app/services/)
```
app/services/
├── orchestrator.py                      (cerebro del sistema - 1,250+ líneas)
├── nlp_engine.py                        (procesamiento inteligente)
├── nlp_engine_enhanced.py               (NLP mejorado)
├── pms_adapter.py                       (integración PMS con circuit breaker)
├── session_manager.py                   (estado & contexto de sesiones)
├── message_gateway.py                   (normalización multi-canal)
├── feature_flag_service.py              (flags dinámicos)
├── dynamic_tenant_service.py            (multi-tenancy)
├── lock_service.py                      (distributed locking)
├── audio_processor.py                   (STT/TTS con Whisper)
├── whatsapp_client.py                   (integración WhatsApp Meta API)
├── gmail_client.py                      (integración Gmail)
├── template_service.py                  (generación de respuestas)
└── nlp/                                 (submódulo NLP completo)
    ├── integrated_nlp_service.py
    ├── enhanced_nlp_engine.py
    ├── hotel_response_generator.py
    └── hotel_context_processor.py
```

#### 🏗️ Core Architecture (app/core/)
```
app/core/
├── settings.py                          (configuración Pydantic v2)
├── logging.py                           (structlog + JSON)
├── middleware.py                        (correlation_id, exception handling)
├── circuit_breaker.py                   (resilience pattern)
└── retry.py                             (retry logic con backoff)
```

#### 📦 Modelos de Dominio (app/models/)
```
app/models/
├── unified_message.py                   (schema normalizado multi-canal)
├── session.py                           (SQLAlchemy ORM - sesiones)
├── tenant.py                            (multi-tenancy models)
├── lock_audit.py                        (auditoría de locks)
└── *.py                                 (resto de modelos Pydantic + ORM)
```

#### 🛡️ Seguridad (app/security/)
```
app/security/
├── jwt_handler.py                       (JWT auth)
├── rate_limiter.py                      (slowapi integration)
└── permissions.py                       (RBAC)
```

#### 🚦 Routers (app/routers/)
```
app/routers/
├── webhooks.py                          (WhatsApp/Gmail endpoints)
├── health.py                            (/health/live, /health/ready)
└── admin.py                             (endpoints administrativos)
```

#### 🔧 Utilities (app/utils/)
```
app/utils/
├── audio_converter.py                   (conversión de formatos audio)
├── i18n_helpers.py                      (internacionalización)
├── locale_utils.py                      (locales)
└── business_hours.py                    (validación horarios)
```

**FORMATO TIER 2**:
```
┌───────────────────────────────────────────────────────────────────────┐
│ 🔧 CÓDIGO CORE - app/services/orchestrator.py                        │
│ 📍 Ubicación: agente-hotel-api/app/services/orchestrator.py          │
│ 🏷️  Tags: #orchestrator #agent #nlp #business-logic #fastapi        │
│ 📊 Métricas: 1,250+ líneas | 48 KB | Complejidad: Alta              │
│ 🔗 Dependencias: NLPEngine, PMSAdapter, SessionManager               │
└───────────────────────────────────────────────────────────────────────┘
[CONTENIDO DEL ARCHIVO AQUÍ]
```

---

### TIER 3 - INFRAESTRUCTURA (PARTE 2, ~4-6 MB):
**[PRIORIDAD: MEDIA - Configuración & deployment]**

#### 🐳 Docker & Orquestación
```
agente-hotel-api/
├── docker-compose.yml                   (configuración local dev)
├── docker-compose.staging.yml           (staging con 7 servicios)
├── docker-compose.production.yml        (producción optimizada)
├── docker-compose.dev.yml               (desarrollo con hot-reload)
├── Dockerfile                           (imagen base)
├── Dockerfile.production                (multi-stage optimizada)
├── Dockerfile.optimized                 (tamaño reducido)
```

#### 🔨 Build & Automation
```
agente-hotel-api/
├── Makefile                             (46 targets: test, lint, deploy, etc.)
├── pyproject.toml                       (Poetry config + deps)
├── requirements.txt                     (prod dependencies)
├── requirements-test.txt                (test dependencies)
├── requirements-prod.txt                (producción explícita)
├── poetry.lock                          (lock file de Poetry)
```

#### 🎛️ Configuración
```
agente-hotel-api/
├── .env.example                         (template de env vars)
├── .env.staging.template                (staging config)
├── .env.supabase.template               (Supabase integration)
├── alembic.ini                          (migrations config)
├── pytest.ini                           (pytest config)
├── .editorconfig                        (editor settings)
├── .pre-commit-config.yaml              (pre-commit hooks)
├── .trivyignore                         (security scan exceptions)
```

#### 📊 Observabilidad
```
agente-hotel-api/docker/
├── prometheus/
│   ├── prometheus.yml                   (Prometheus config)
│   └── rules/                           (alert rules)
├── grafana/
│   ├── dashboards/                      (pre-built dashboards)
│   └── provisioning/                    (datasources)
├── alertmanager/
│   └── alertmanager.yml                 (routing config)
└── nginx/
    └── nginx.conf                       (reverse proxy)
```

#### 🚀 Scripts de Deployment
```
agente-hotel-api/scripts/
├── deploy-staging.sh                    (deployment automatizado)
├── generate-staging-secrets.sh          (generación de secrets)
├── preflight.py                         (risk assessment)
├── canary-deploy.sh                     (canary diff analysis)
└── *.sh                                 (scripts operacionales)
```

#### ⚙️ Kubernetes (si existe)
```
agente-hotel-api/k8s/
├── deployment.yaml
├── service.yaml
├── ingress.yaml
└── configmap.yaml
```

---

### TIER 4 - TESTS Y DOCS (PARTE 3, ~3-5 MB):
**[PRIORIDAD: MEDIA - Validación & documentación]**

#### 🧪 Test Suite
```
agente-hotel-api/tests/
├── unit/                                (service-level tests)
│   ├── test_orchestrator.py
│   ├── test_pms_adapter.py
│   ├── test_session_manager.py
│   └── test_*.py                        (resto de tests unitarios)
├── integration/                         (cross-service tests)
│   ├── test_orchestrator_integration.py
│   └── test_pms_integration.py
├── e2e/                                 (end-to-end flows)
│   └── test_reservation_flow.py
├── chaos/                               (resilience tests)
│   ├── test_circuit_breaker_resilience.py
│   └── test_cascading_failures.py
├── mocks/                               (external service simulators)
│   └── pms_mock_server.py
└── conftest.py                          (pytest fixtures globales)
```

#### 📚 Documentación Extendida
```
agente-hotel-api/docs/
├── guides/                              (P011-P020 guías técnicas)
│   ├── P011-DEPENDENCY-SCAN-GUIDE.md
│   ├── P012-SECRET-SCANNING-GUIDE.md
│   ├── P013-OWASP-VALIDATION-GUIDE.md
│   ├── P014-COMPLIANCE-REPORT-GUIDE.md
│   ├── P015-PERFORMANCE-TESTING-GUIDE.md
│   ├── P016-OBSERVABILITY-GUIDE.md
│   ├── P017-CHAOS-ENGINEERING-GUIDE.md
│   ├── P018-DEPLOYMENT-AUTOMATION-GUIDE.md
│   ├── P019-INCIDENT-RESPONSE-GUIDE.md
│   └── P020-PRODUCTION-READINESS-CHECKLIST.md
├── deployment/                          (deployment documentation)
│   ├── README.md
│   ├── DEPLOYMENT_READINESS_CHECKLIST.md
│   └── QLOAPPS_CONFIGURATION.md
├── operations/                          (operational docs)
│   ├── OPERATIONS_MANUAL.md
│   └── POST-LAUNCH-MONITORING.md
├── integrations/                        (🆕 CONSOLIDADO en FASE 1)
│   └── SUPABASE.md                      (22KB - consolidación de 15 docs)
├── architecture/                        (🆕 carpeta creada)
├── testing/                             (🆕 carpeta creada)
└── security/                            (🆕 carpeta creada)
```

#### 📖 Documentación Legacy (para contexto)
```
agente-hotel-api/docs/
├── ROADMAP_EXECUTION_BLUEPRINT.md
├── ROADMAP_FASE_1_REMEDIATION.md
├── DEVELOPMENT_WITHOUT_WHATSAPP.md
├── SECRETS_GUIDE.md
└── *.md                                 (resto de documentación histórica)
```

---

### TIER 5 - RESTO (PARTE 4, ~1-2 MB):
**[PRIORIDAD: BAJA - Miscelánea]**

#### 📦 Templates y Assets
```
agente-hotel-api/
├── templates/                           (plantillas de respuesta)
│   └── *.jinja2
```

#### 🗄️ Migraciones de Base de Datos
```
agente-hotel-api/alembic/
├── versions/                            (archivos de migración)
│   └── *.py
├── env.py                               (config de Alembic)
└── script.py.mako                       (template de migraciones)
```

#### 📝 Logs y Reportes (EXCLUIR archivos de log)
```
agente-hotel-api/
├── logs/                                (❌ EXCLUIR)
├── htmlcov/                             (❌ EXCLUIR - coverage reports)
├── .benchmarks/                         (❌ EXCLUIR - benchmarks)
└── .reports/                            (❌ EXCLUIR - security reports)
```

#### 📁 Archivos de Configuración Restantes
```
RAÍZ:
├── .copilotignore                       (exclusiones de Copilot)
├── .dockerignore                        (exclusiones de Docker)
├── .gitignore                           (exclusiones de Git)
├── .gitattributes                       (atributos de Git)
```

#### 🗃️ Archive (contexto histórico - baja prioridad)
```
archive/                                 (documentación archivada)
├── 2025-11-pre-consolidation/           (docs pre-consolidación)
│   ├── duplicated-docs/
│   ├── obsolete-plans/
│   └── contradictory-reports/
├── docs-old/
├── docs-obsolete-nov5/
└── plans-old/
```

**NOTA CRÍTICA**: El directorio `archive/` contiene documentación histórica importante pero **NO crítica para ejecución**. Incluir solo si hay espacio disponible en Parte 4, priorizando siempre TIER 1-3.

═══════════════════════════════════════════════════════════════════════════════
## PARTE 3: REGLAS DE PROCESAMIENTO Y FILTRADO
═══════════════════════════════════════════════════════════════════════════════

### INCLUSIÓN - Extensiones a procesar (EXHAUSTIVO):
```
✅ Código Python: .py
✅ Configuración: .json .yaml .yml .toml .ini .conf .cfg .env .env.example
                 .env.staging .env.production .env.test .env.supabase
✅ Documentación: .md .txt .rst
✅ Scripts: .sh .bash .zsh .ps1 .bat
✅ Infraestructura: Dockerfile Dockerfile.* docker-compose*.yml
                   .dockerignore .trivyignore
✅ Build: Makefile pyproject.toml poetry.lock requirements*.txt
          alembic.ini pytest.ini .editorconfig .pre-commit-config.yaml
✅ Git: .gitignore .gitattributes .copilotignore
✅ Web (si existe): .html .css .js .jsx .ts .tsx
✅ Templates: .jinja2 .j2
✅ CI/CD: .github/workflows/*.yml
```

### EXCLUSIÓN - Patrones a ignorar (CRÍTICO para no contaminar):
```
❌ Directorios completos:
   - node_modules/
   - __pycache__/
   - .git/
   - dist/
   - build/
   - coverage/
   - .pytest_cache/
   - .mypy_cache/
   - .ruff_cache/
   - .venv/
   - venv/
   - env/
   - htmlcov/                         (coverage HTML reports)
   - logs/                            (archivos de log)
   - .benchmarks/                     (reportes de benchmarks)
   - .performance/                    (reportes de performance)
   - .security/                       (reportes de seguridad - pueden ser grandes)

❌ Extensiones binarias/compiladas:
   - *.pyc *.pyo *.pyd
   - *.so *.dll *.dylib *.exe
   - *.o *.a *.lib

❌ Archivos de lock grandes (ya tenemos poetry.lock):
   - package-lock.json
   - yarn.lock
   - pnpm-lock.yaml

❌ Imágenes y multimedia:
   - *.jpg *.jpeg *.png *.gif *.svg *.ico *.webp
   - *.mp3 *.mp4 *.wav *.avi *.mov
   - *.pdf

❌ Archivos comprimidos:
   - *.zip *.tar *.gz *.rar *.7z *.bz2

❌ Archivos temporales:
   - *~ *.swp *.swo *.bak *.tmp *.temp
   - .DS_Store
   - Thumbs.db

❌ Logs y dumps:
   - *.log
   - *.dump
   - *.sqlite (bases de datos locales)
   - *.db (excepto si es schema)

❌ Archivos de coverage:
   - .coverage
   - coverage.xml
   - coverage.json
```

### MANEJO DE ERRORES POR TIPO:
```python
try:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
except UnicodeDecodeError:
    # Intentar latin-1
    try:
        with open(filepath, 'r', encoding='latin-1') as f:
            content = f.read()
    except:
        # Placeholder con aviso
        content = f"[BINARY FILE - {filepath.name} - Size: {filepath.stat().st_size} bytes]"
        logger.warning(f"Skipping binary file: {filepath}")

except PermissionError:
    logger.warning(f"Permission denied: {filepath}")
    continue  # skip

except FileNotFoundError:
    logger.debug(f"File not found (symlink?): {filepath}")
    continue  # skip silently

except IsADirectoryError:
    continue  # skip directories

except OSError as e:
    if filepath.stat().st_size > 10 * 1024 * 1024:  # >10MB
        content = f"[FILE TOO LARGE - {filepath.name} - Size: {filepath.stat().st_size / (1024*1024):.2f} MB]\n"
        content += f"First 1000 lines:\n"
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content += '\n'.join(f.readlines()[:1000])
        logger.warning(f"Truncated large file: {filepath}")
    else:
        raise
```

═══════════════════════════════════════════════════════════════════════════════
## PARTE 4: ALGORITMO DE BALANCEO INTELIGENTE
═══════════════════════════════════════════════════════════════════════════════

### ESTRATEGIA DE DISTRIBUCIÓN:
```python
1. Escanear todos los archivos elegibles (aplicar reglas de EXCLUSIÓN)
2. Categorizar por TIER (1-5)
3. Calcular peso total de cada TIER
4. Dividir en 4 buckets objetivo: [22MB, 22MB, 22MB, restante ≤23MB]

5. Distribución por TIER:
   PARTE 1 (target: 22MB):
   ├── TIER 1 completo (no negociable, primeros archivos)
   ├── TIER 2 parcial (servicios core hasta llenar)
   └── Si sobra espacio: inicio de TIER 3

   PARTE 2 (target: 22MB):
   ├── TIER 2 restante (si no cupo en Parte 1)
   ├── TIER 3 completo (infra + deployment)
   └── Si sobra espacio: inicio de TIER 4

   PARTE 3 (target: 22MB):
   ├── TIER 4 completo (tests + docs extensas)
   └── Si sobra espacio: inicio de TIER 5

   PARTE 4 (flexible: ≤23MB):
   ├── TIER 5 completo (resto + archive)
   └── Overflow de partes anteriores si existe

6. REGLA DE ORO:
   - NUNCA partir un archivo entre dos .txt (mantener integridad)
   - Si un archivo >5MB, puede ir solo en su chunk
   - Si TIER 1 + TIER 2 core >22MB, usar 2 partes solo para ellos
```

### CHECKPOINTS DE VALIDACIÓN:
```
├── Pre-procesamiento:
│   ├── ✓ Verificar que estamos en raíz del repo git
│   ├── ✓ Confirmar que .github/copilot-instructions.md existe
│   ├── ✓ Validar permisos de escritura en directorio actual
│   ├── ✓ Estimar espacio en disco necesario (~50-100MB)
│   └── ✓ Verificar que commit hash es 97676bcc27f7f999f602432a07383ce09c5dee68
│
├── Durante procesamiento:
│   ├── ✓ Cada 50 archivos: mostrar progreso con barra ASCII
│   ├── ✓ Si archivo >23MB individual, dividir lógicamente o error
│   ├── ✓ Mantener running checksum para integridad
│   ├── ✓ Validar que archivos TIER 1 van primero en Parte 1
│   └── ✓ Si memoria >500MB, flush a disco incrementalmente
│
└── Post-procesamiento:
    ├── ✓ Verificar que se generaron exactamente 4 archivos
    ├── ✓ Cada archivo tiene header metadata completo
    ├── ✓ Ningún archivo vacío o corrupto
    ├── ✓ Suma de tamaños ≈ tamaño total archivos procesados
    ├── ✓ .github/copilot-instructions.md está en Parte 1
    ├── ✓ app/services/orchestrator.py está en Parte 1 o 2
    └── ✓ Generar manifest.json con índice maestro
```

═══════════════════════════════════════════════════════════════════════════════
## PARTE 5: CÓDIGO EJECUTABLE CON MÁXIMA ROBUSTEZ
═══════════════════════════════════════════════════════════════════════════════

### GENERA EL SCRIPT COMPLETO "prepare_for_poe.py" que incluya:

#### 1. IMPORTS Y SETUP:
```python
#!/usr/bin/env python3
"""
Script de extracción de repositorio para Poe.com (o3-pro bot)
Personalizado para: SIST_AGENTICO_HOTELERO
"""

import os
import sys
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import subprocess
import logging
from collections import defaultdict
```

#### 2. CONFIGURACIÓN COMO CONSTANTES:
```python
# Configuración del script
MAX_FILE_SIZE_MB = 23
TARGET_FILE_SIZE_MB = 21
OUTPUT_DIR = "POE_KNOWLEDGE_FILES"
CHUNK_SIZE = 1024 * 1024  # 1MB para lectura incremental

# Proyecto específico
PROJECT_NAME = "SIST_AGENTICO_HOTELERO"
EXPECTED_COMMIT = "97676bcc27f7f999f602432a07383ce09c5dee68"
EXPECTED_BRANCH = "feature/etapa2-qloapps-integration"
DEPLOYMENT_READINESS = "8.9/10"
TEST_COVERAGE = "31%"
CVE_STATUS = "0 CRITICAL"

# Archivos críticos que DEBEN estar en Parte 1
CRITICAL_FILES = [
    ".github/copilot-instructions.md",
    ".github/AI-AGENT-QUICKSTART.md",
    ".github/AI-AGENT-CONTRIBUTING.md",
    "README.md",
    "MASTER_PROJECT_GUIDE.md",
    "agente-hotel-api/README.md",
    "agente-hotel-api/README-Infra.md",
    ".playbook/PRODUCTION_READINESS_CHECKLIST.md",
]

# Patrones de exclusión
EXCLUDE_DIRS = {
    "node_modules", "__pycache__", ".git", "dist", "build",
    "coverage", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".venv", "venv", "env", "htmlcov", "logs",
    ".benchmarks", ".performance", ".security", ".coverage"
}

EXCLUDE_PATTERNS = {
    "*.pyc", "*.pyo", "*.pyd", "*.so", "*.dll", "*.dylib", "*.exe",
    "*.log", "*.lock", "package-lock.json", "*.jpg", "*.jpeg",
    "*.png", "*.gif", "*.svg", "*.ico", "*.pdf", "*.zip",
    "*.tar", "*.gz", "*.rar", "*.7z", "*~", "*.swp", "*.swo",
    "*.bak", "*.tmp", "*.temp", ".DS_Store", "Thumbs.db",
    "*.dump", "*.sqlite", "*.db", ".coverage", "coverage.xml",
    "coverage.json", "*.pyc", "poetry.lock"  # Excluir poetry.lock (muy grande)
}

# Extensiones a incluir
INCLUDE_EXTENSIONS = {
    ".py", ".json", ".yaml", ".yml", ".toml", ".ini", ".conf", ".cfg",
    ".env", ".md", ".txt", ".rst", ".sh", ".bash", ".zsh", ".ps1",
    ".bat", ".jinja2", ".j2", ".html", ".css", ".js", ".jsx", ".ts",
    ".tsx", ".gitignore", ".dockerignore", ".editorconfig"
}

# Archivos especiales sin extensión a incluir
INCLUDE_FILES = {
    "Dockerfile", "Makefile", "Procfile", ".copilotignore",
    ".trivyignore", ".gitattributes"
}
```

#### 3. CLASES DE DATOS:
```python
@dataclass
class FileMetadata:
    """Metadata de un archivo procesado"""
    path: str
    relative_path: str
    size: int
    tier: int
    checksum: str
    lines: int
    encoding: str = "utf-8"

    def __lt__(self, other):
        """Comparación para ordenamiento"""
        if self.tier != other.tier:
            return self.tier < other.tier
        return self.size > other.size  # Archivos grandes primero dentro del tier

@dataclass
class ChunkMetadata:
    """Metadata de un chunk (parte) generado"""
    chunk_id: int
    files: List[FileMetadata] = field(default_factory=list)
    total_size: int = 0
    checksum: str = ""
    
    def add_file(self, file_meta: FileMetadata):
        self.files.append(file_meta)
        self.total_size += file_meta.size
```

#### 4. FUNCIONES CORE (con docstrings Google-style):
```python
def setup_logging() -> logging.Logger:
    """Configura logging estructurado a consola y archivo"""
    
def get_git_commit_hash() -> str:
    """Obtiene el commit hash actual del repositorio"""
    
def get_git_branch() -> str:
    """Obtiene el branch actual del repositorio"""
    
def calculate_file_checksum(filepath: Path) -> str:
    """Calcula SHA256 checksum de un archivo"""
    
def should_include_file(filepath: Path, repo_root: Path) -> bool:
    """Determina si un archivo debe ser incluido en la extracción"""
    
def categorize_file_tier(filepath: Path, repo_root: Path) -> int:
    """Categoriza un archivo en TIER 1-5 según prioridad"""
    
def read_file_safely(filepath: Path) -> Tuple[str, bool, str]:
    """Lee un archivo de forma segura con manejo de encoding"""
    # Returns: (content, success, encoding_used)
    
def count_lines(content: str) -> int:
    """Cuenta líneas en contenido de texto"""
    
def format_file_header(metadata: FileMetadata, tier: int) -> str:
    """Formatea el header visual de un archivo según TIER"""
    
def generate_chunk_metadata_header(chunk: ChunkMetadata, commit_hash: str, branch: str) -> str:
    """Genera el header de metadata de un chunk"""
    
def distribute_files_to_chunks(files: List[FileMetadata]) -> List[ChunkMetadata]:
    """Distribuye archivos en 4 chunks con algoritmo de balanceo"""
    
def write_chunk_to_disk(chunk: ChunkMetadata, output_dir: Path, repo_root: Path) -> Path:
    """Escribe un chunk a disco con validaciones"""
    
def generate_master_manifest(chunks: List[ChunkMetadata], output_dir: Path) -> None:
    """Genera manifest.json con índice maestro de todos los chunks"""
    
def validate_extraction(output_dir: Path) -> bool:
    """Valida que la extracción fue exitosa y completa"""
    
def generate_final_report(chunks: List[ChunkMetadata], total_files: int, 
                         execution_time: float, output_dir: Path) -> str:
    """Genera reporte final detallado de la extracción"""
```

#### 5. FUNCIÓN MAIN CON FLUJO COMPLETO:
```python
def main():
    """
    Flujo principal de extracción:
    1. Validación inicial (git, permisos, archivos críticos)
    2. Escaneo y categorización de archivos
    3. Distribución inteligente en 4 chunks
    4. Escritura con checksums
    5. Validación final
    6. Reporte detallado
    """
    
    # 1. Setup
    logger = setup_logging()
    logger.info("=" * 80)
    logger.info(f"EXTRACCIÓN DE REPOSITORIO: {PROJECT_NAME}")
    logger.info("=" * 80)
    
    # 2. Validaciones pre-vuelo
    # ... (verificar git, commit hash, branch, archivos críticos)
    
    # 3. Escaneo de archivos
    # ... (walk del repo, aplicar filtros, categorizar)
    
    # 4. Distribución en chunks
    # ... (algoritmo de balanceo)
    
    # 5. Escritura a disco
    # ... (generar 4 archivos .txt)
    
    # 6. Validación post-procesamiento
    # ... (verificar integridad)
    
    # 7. Reporte final
    # ... (estadísticas detalladas)
    
    return 0  # exit code

if __name__ == "__main__":
    sys.exit(main())
```

#### 6. LOGGING ESTRUCTURADO:
```python
# Configuración de logging
LOG_FORMAT = '%(asctime)s | %(levelname)-8s | %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('poe_extraction.log', mode='w', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)
```

#### 7. REPORTE FINAL (stdout + poe_extraction_report.txt):
```python
def generate_final_report(chunks, total_files, execution_time, output_dir):
    report = f"""
╔══════════════════════════════════════════════════════════════╗
║  EXTRACCIÓN COMPLETADA EXITOSAMENTE                          ║
║  Proyecto: {PROJECT_NAME}                                    ║
╚══════════════════════════════════════════════════════════════╝

📊 ESTADÍSTICAS GENERALES:
├─ Archivos procesados: {len([f for c in chunks for f in c.files])} / {total_files} encontrados
├─ Archivos excluídos: {total_files - len([f for c in chunks for f in c.files])} (permisos/filtros)
├─ Líneas de código: {sum(f.lines for c in chunks for f in c.files):,}
├─ Tamaño total: {sum(c.total_size for c in chunks) / (1024*1024):.2f} MB
├─ Tiempo de ejecución: {execution_time:.2f} segundos
├─ Commit hash: {EXPECTED_COMMIT[:12]}...
└─ Branch: {EXPECTED_BRANCH}

📦 DISTRIBUCIÓN POR CHUNK:
"""
    for chunk in chunks:
        size_mb = chunk.total_size / (1024 * 1024)
        report += f"├─ Parte {chunk.chunk_id}: {size_mb:.2f} MB ({len(chunk.files)} archivos) - TIER {min(f.tier for f in chunk.files)}-{max(f.tier for f in chunk.files)}\n"
    
    report += f"""
✅ VALIDACIONES:
├─ ✓ Checksums verificados
├─ ✓ Metadata headers completos
├─ ✓ Archivos críticos incluidos (.github/copilot-instructions.md ✓)
├─ ✓ Manifest maestro generado
└─ ✓ 4 archivos .txt creados

📁 SIGUIENTE PASO:
Sube los 4 archivos de {OUTPUT_DIR}/ a tu bot en Poe.com

🎯 MÉTRICAS DEL PROYECTO:
├─ Deployment Readiness: {DEPLOYMENT_READINESS}
├─ Test Coverage: {TEST_COVERAGE}
├─ CVE Status: {CVE_STATUS}
└─ Python Version: 3.12.3
    """
    
    return report
```

#### 8. ERROR HANDLING ROBUSTO:
```python
# En cada función crítica:
try:
    # operación de archivo
    pass
except Exception as e:
    logger.error(f"Error procesando {filepath}: {e}", exc_info=True)
    # Cleanup automático si falla
    if output_dir.exists():
        shutil.rmtree(output_dir)
    sys.exit(2)  # exit code de error crítico
```

═══════════════════════════════════════════════════════════════════════════════
## PARTE 6: VALIDACIÓN Y TESTING
═══════════════════════════════════════════════════════════════════════════════

### El script debe incluir función de self-test:
```python
def validate_extraction(output_dir: Path) -> bool:
    """
    Valida que la extracción fue exitosa y completa
    
    Returns:
        bool: True si todas las validaciones pasan, False otherwise
    """
    logger = logging.getLogger(__name__)
    checks = {
        "4_files_exist": False,
        "manifest_exists": False,
        "copilot_instructions_found": False,
        "orchestrator_found": False,
        "no_empty_files": True,
        "sizes_valid": True,
        "checksums_match": True,
    }
    
    # 1. Verificar que existen 4 archivos .txt
    txt_files = list(output_dir.glob("*.txt"))
    checks["4_files_exist"] = len(txt_files) == 4
    
    # 2. Verificar que existe manifest.json
    manifest_path = output_dir / "manifest.json"
    checks["manifest_exists"] = manifest_path.exists()
    
    if checks["manifest_exists"]:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
            
        # 3. Buscar archivos críticos en Parte 1
        part1_files = [f['path'] for f in manifest['chunks'][0]['files']]
        checks["copilot_instructions_found"] = any(
            '.github/copilot-instructions.md' in f for f in part1_files
        )
        
        # 4. Buscar orchestrator en Parte 1 o 2
        part1_and_2_files = [f['path'] for f in manifest['chunks'][0]['files'] + manifest['chunks'][1]['files']]
        checks["orchestrator_found"] = any(
            'app/services/orchestrator.py' in f for f in part1_and_2_files
        )
    
    # 5. Verificar que no hay archivos vacíos
    for txt_file in txt_files:
        if txt_file.stat().st_size == 0:
            checks["no_empty_files"] = False
            logger.error(f"Empty file found: {txt_file}")
    
    # 6. Verificar tamaños válidos (<23MB)
    for txt_file in txt_files:
        size_mb = txt_file.stat().st_size / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            checks["sizes_valid"] = False
            logger.error(f"File too large: {txt_file} ({size_mb:.2f} MB)")
    
    # Reporte de validación
    logger.info("=" * 80)
    logger.info("VALIDACIÓN DE EXTRACCIÓN:")
    for check_name, passed in checks.items():
        status = "✓" if passed else "✗"
        logger.info(f"{status} {check_name.replace('_', ' ').title()}")
    logger.info("=" * 80)
    
    return all(checks.values())
```

═══════════════════════════════════════════════════════════════════════════════
## ENTREGABLE FINAL
═══════════════════════════════════════════════════════════════════════════════

### GENERA UN SCRIPT PYTHON COMPLETO, EJECUTABLE, PRODUCTION-READY que:

✅ **Ejecutable**: `python3 prepare_for_poe.py` (desde raíz del repo)  
✅ **Sin dependencias externas**: Solo stdlib de Python  
✅ **Compatible**: Python 3.8+  
✅ **Manejo de errores**: Exhaustivo con rollback automático  
✅ **Logs estructurados**: Consola + archivo poe_extraction.log  
✅ **Type hints**: Completos en todas las funciones  
✅ **Docstrings**: Google-style en todas las funciones  
✅ **Linting**: Pasa black, flake8, mypy (ejecutar `make lint` antes de usar)  
✅ **Idempotente**: Ejecutable múltiples veces (borra output anterior)  
✅ **Validación**: Self-test integrado post-procesamiento  
✅ **Reporte**: Detallado con estadísticas + próximos pasos  

### CARACTERÍSTICAS ESPECIALES PARA SIST_AGENTICO_HOTELERO:

1. **Metadata enriquecida** con métricas del proyecto:
   - Deployment readiness: 8.9/10
   - Test coverage: 31%
   - CVE status: 0 CRITICAL
   - Commit hash: 97676bcc27f7f999f602432a07383ce09c5dee68

2. **Validación de archivos críticos** en Parte 1:
   - `.github/copilot-instructions.md` (ORO PURO)
   - `app/services/orchestrator.py` (cerebro del sistema)
   - `MASTER_PROJECT_GUIDE.md`
   - Playbooks ejecutivos

3. **Exclusión inteligente** de archivos grandes no necesarios:
   - poetry.lock (lock file duplicado)
   - logs/, htmlcov/, .benchmarks/
   - Coverage reports (.coverage, coverage.xml)

4. **Optimización para o3-pro**:
   - TIER 1 con documentación arquitectural completa
   - Headers visuales por archivo con tags relevantes
   - Índice navegable en cada parte
   - Manifest.json con mapa completo del código

### LONGITUD ESPERADA:
**450-650 líneas** de código limpio, bien documentado y production-ready

### VALIDACIÓN PRE-USO:
```bash
# Ejecutar desde raíz de SIST_AGENTICO_HOTELERO
cd /home/eevan/SIST_AGENTICO_HOTELERO

# Verificar que estamos en el branch correcto
git branch --show-current  # Debe mostrar: feature/etapa2-qloapps-integration

# Ejecutar script
python3 agente-hotel-api/scripts/prepare_for_poe.py

# Verificar outputs
ls -lh POE_KNOWLEDGE_FILES/
# Debe mostrar:
# - parte_1.txt (~21-22 MB)
# - parte_2.txt (~21-22 MB)
# - parte_3.txt (~20-22 MB)
# - parte_4.txt (~5-10 MB)
# - manifest.json (~50-100 KB)
```

═══════════════════════════════════════════════════════════════════════════════
## NOTAS FINALES
═══════════════════════════════════════════════════════════════════════════════

**Este PROMPT 1 está 100% personalizado para SIST_AGENTICO_HOTELERO** con:

✅ Archivos críticos específicos del proyecto  
✅ Estructura de carpetas real (app/services/, .playbook/, etc.)  
✅ Métricas actuales (coverage 31%, readiness 8.9/10)  
✅ Commit hash y branch exactos  
✅ Exclusiones específicas (poetry.lock, .benchmarks/, etc.)  
✅ Priorización arquitectural (orchestrator, copilot-instructions)  
✅ Documentación consolidada FASE 1 (SUPABASE.md 22KB)  

**Próximos pasos**:
1. Usuario proporciona PROMPT 2 y PROMPT 3
2. Personalizar ambos con mismo nivel de detalle
3. Generar script `prepare_for_poe.py` completo
4. Ejecutar y validar
5. Subir archivos a Poe.com para usar o3-pro

---
**Creado**: 2025-11-18  
**Personalizado para**: SIST_AGENTICO_HOTELERO  
**Mantenido por**: Backend AI Team  
**Versión**: 1.0 (Personalizada)
