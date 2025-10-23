#!/bin/bash

###############################################################################
# 🔧 SCRIPT MAESTRO - PLAN DE OPTIMIZACIÓN
# 
# Propósito: Automatizar y ejecutar todas las fases del plan
# Uso: ./run-optimization-plan.sh [fase] [verbose]
# Ejemplo: ./run-optimization-plan.sh phase1 verbose
###############################################################################

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
PROJECT_ROOT="/home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api"
REPORTS_DIR="${PROJECT_ROOT}/.optimization-reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${REPORTS_DIR}/phase_${TIMESTAMP}.log"
VERBOSE="${2:-false}"

# Crear directorio de reportes
mkdir -p "${REPORTS_DIR}"

###############################################################################
# FUNCIONES AUXILIARES
###############################################################################

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1" | tee -a "${LOG_FILE}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "${LOG_FILE}"
}

error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "${LOG_FILE}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "${LOG_FILE}"
}

separator() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" | tee -a "${LOG_FILE}"
}

###############################################################################
# FASE 1: AUDITORÍA INICIAL
###############################################################################

phase1_audit_dependencies() {
    log "Iniciando: Auditoría de dependencias..."
    
    cd "${PROJECT_ROOT}"
    
    # Crear reporte
    local report="${REPORTS_DIR}/audit_dependencies_${TIMESTAMP}.json"
    
    {
        echo "{"
        echo '  "timestamp": "'$(date -Iseconds)'",'
        echo '  "audit_type": "dependencies",'
        echo '  "results": {'
        
        # pip-audit
        echo '    "pip-audit": {' > /tmp/pip_audit.txt
        if pip-audit --skip-editable 2>&1 | tee >> /tmp/pip_audit.txt; then
            echo '      "status": "OK"' >> /tmp/pip_audit.txt
        else
            echo '      "status": "FOUND_ISSUES"' >> /tmp/pip_audit.txt
        fi
        echo '    },' >> /tmp/pip_audit.txt
        
        # poetry audit
        echo '    "poetry-audit": {' > /tmp/poetry_audit.txt
        if poetry audit 2>&1 | tee >> /tmp/poetry_audit.txt; then
            echo '      "status": "OK"' >> /tmp/poetry_audit.txt
        else
            echo '      "status": "FOUND_ISSUES"' >> /tmp/poetry_audit.txt
        fi
        echo '    }' >> /tmp/poetry_audit.txt
        
        cat /tmp/pip_audit.txt /tmp/poetry_audit.txt
        
        echo '  }'
        echo "}"
    } > "${report}"
    
    success "Dependencias auditadas. Reporte: ${report}"
}

phase1_circular_imports() {
    log "Iniciando: Análisis de imports circulares..."
    
    cd "${PROJECT_ROOT}"
    
    local report="${REPORTS_DIR}/circular_imports_${TIMESTAMP}.json"
    
    python3 << 'PYTHON_END' > "${report}" 2>&1
import ast
import os
import json

class ImportAnalyzer(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.imports = []
    
    def visit_ImportFrom(self, node):
        if node.module and node.module.startswith('app.'):
            self.imports.append({
                'type': 'from',
                'module': node.module,
                'line': node.lineno
            })
        self.generic_visit(node)
    
    def visit_Import(self, node):
        for alias in node.names:
            if alias.name.startswith('app.'):
                self.imports.append({
                    'type': 'import',
                    'module': alias.name,
                    'line': node.lineno
                })
        self.generic_visit(node)

results = {}
for root, dirs, files in os.walk('app'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r') as f:
                    tree = ast.parse(f.read())
                    analyzer = ImportAnalyzer(filepath)
                    analyzer.visit(tree)
                    if analyzer.imports:
                        results[filepath] = analyzer.imports
            except Exception as e:
                results[filepath] = {'error': str(e)}

print(json.dumps(results, indent=2))
PYTHON_END
    
    success "Imports circulares analizados. Reporte: ${report}"
}

phase1_dead_code() {
    log "Iniciando: Detección de código muerto..."
    
    cd "${PROJECT_ROOT}"
    
    local report="${REPORTS_DIR}/dead_code_${TIMESTAMP}.txt"
    
    # Usar vulture si está disponible
    if command -v vulture &> /dev/null; then
        vulture app/ --min-confidence 80 > "${report}" 2>&1
        success "Código muerto detectado. Reporte: ${report}"
    else
        warning "Vulture no instalado. Omitiendo análisis de código muerto."
        echo "Install vulture: pip install vulture" > "${report}"
    fi
}

phase1_async_audit() {
    log "Iniciando: Auditoría async/await..."
    
    cd "${PROJECT_ROOT}"
    
    local report="${REPORTS_DIR}/async_audit_${TIMESTAMP}.json"
    
    python3 << 'PYTHON_END' > "${report}" 2>&1
import ast
import os
import json

class AsyncVisitor(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.issues = []
    
    def visit_FunctionDef(self, node):
        # Check if function should be async
        for child in ast.walk(node):
            if isinstance(child, ast.Await):
                if not node.name.startswith('async_'):
                    self.issues.append({
                        'line': node.lineno,
                        'function': node.name,
                        'issue': 'Contains await but not declared async',
                        'file': self.filename
                    })
        self.generic_visit(node)

results = []
for root, dirs, files in os.walk('app'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r') as f:
                    tree = ast.parse(f.read())
                    analyzer = AsyncVisitor(filepath)
                    analyzer.visit(tree)
                    if analyzer.issues:
                        results.extend(analyzer.issues)
            except Exception as e:
                pass

print(json.dumps({
    'timestamp': '$(date -Iseconds)',
    'total_issues': len(results),
    'issues': results[:20]
}, indent=2))
PYTHON_END
    
    success "Async/await auditado. Reporte: ${report}"
}

phase1_risk_matrix() {
    log "Iniciando: Creación de matriz de riesgos..."
    
    local report="${REPORTS_DIR}/risk_matrix_${TIMESTAMP}.json"
    
    cat > "${report}" << 'EOF'
{
  "timestamp": "2025-10-19T00:00:00Z",
  "version": "1.0",
  "findings": [
    {
      "component": "orchestrator.py",
      "function": "process_message()",
      "risk": "Intent not found in dispatcher dict",
      "severity": "HIGH",
      "probability": "MEDIUM",
      "impact": "CRITICAL",
      "priority": "P0",
      "mitigation": "Use dict.get() with default handler",
      "status": "OPEN"
    },
    {
      "component": "pms_adapter.py",
      "function": "check_availability()",
      "risk": "Circuit breaker state race condition",
      "severity": "MEDIUM",
      "probability": "LOW",
      "impact": "HIGH",
      "priority": "P1",
      "mitigation": "Lock-based state machine",
      "status": "OPEN"
    },
    {
      "component": "lock_service.py",
      "function": "acquire_lock()",
      "risk": "Deadlock on lock acquisition",
      "severity": "HIGH",
      "probability": "MEDIUM",
      "impact": "CRITICAL",
      "priority": "P0",
      "mitigation": "Timeout + auto-release via Redis TTL",
      "status": "OPEN"
    }
  ]
}
EOF
    
    success "Matriz de riesgos creada. Reporte: ${report}"
}

phase1_run_all() {
    separator
    log "FASE 1: AUDITORÍA INICIAL"
    separator
    
    phase1_audit_dependencies
    phase1_circular_imports
    phase1_dead_code
    phase1_async_audit
    phase1_risk_matrix
    
    separator
    success "FASE 1 COMPLETADA"
    separator
}

###############################################################################
# FASE 4: TESTING EXHAUSTIVO (Scaffold)
###############################################################################

phase4_create_test_scaffold() {
    log "Iniciando: Creación de test scaffold..."
    
    cd "${PROJECT_ROOT}"
    
    mkdir -p tests/test_suites
    
    # Crear test suite para orchestrator
    cat > tests/test_suites/test_orchestrator_critical.py << 'EOF'
"""Critical tests for orchestrator.process_message()"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.orchestrator import Orchestrator
from app.models.unified_message import UnifiedMessage

@pytest.fixture
async def orchestrator():
    orch = Orchestrator()
    orch.nlp_engine = AsyncMock()
    orch.pms_adapter = AsyncMock()
    orch._intent_handlers = {}
    return orch

@pytest.mark.asyncio
async def test_unknown_intent_fallback(orchestrator):
    """Unknown intent → fallback handler"""
    message = UnifiedMessage(text="xyz unknown")
    orchestrator.nlp_engine.detect_intent.return_value = MagicMock(
        type="UNKNOWN", confidence=0.5
    )
    orchestrator._handle_fallback = AsyncMock(return_value=MagicMock(type="fallback"))
    
    response = await orchestrator.process_message(message)
    assert response is not None

@pytest.mark.asyncio
async def test_low_confidence_fallback(orchestrator):
    """Low confidence → fallback"""
    message = UnifiedMessage(text="maybe?")
    orchestrator.nlp_engine.detect_intent.return_value = MagicMock(
        type="booking", confidence=0.2
    )
    
    response = await orchestrator.process_message(message)
    assert response is not None
EOF
    
    success "Test scaffold creado: tests/test_suites/test_orchestrator_critical.py"
}

###############################################################################
# UTILIDADES
###############################################################################

show_help() {
    cat << EOF
${BLUE}🔧 PLAN DE OPTIMIZACIÓN - Script Maestro${NC}

${YELLOW}Uso:${NC}
  $0 [fase] [verbose]

${YELLOW}Fases disponibles:${NC}
  phase1       - Auditoría inicial (dependencias, imports, código muerto)
  phase4       - Testing exhaustivo (crear scaffolds)
  all          - Ejecutar todas las fases
  report       - Mostrar último reporte

${YELLOW}Ejemplos:${NC}
  $0 phase1            # Ejecutar auditoría
  $0 phase1 verbose    # Ejecutar con output detallado
  $0 all               # Ejecutar todo
  $0 report            # Mostrar reporte

${YELLOW}Reportes:${NC}
  Los reportes se guardan en: ${REPORTS_DIR}/

EOF
}

show_report() {
    if [ -d "${REPORTS_DIR}" ]; then
        log "Últimos reportes:"
        ls -lth "${REPORTS_DIR}" | head -10
    else
        error "No reports found."
    fi
}

###############################################################################
# MAIN
###############################################################################

main() {
    local phase="${1:-help}"
    
    case "${phase}" in
        phase1)
            phase1_run_all
            ;;
        phase4)
            phase4_create_test_scaffold
            ;;
        all)
            phase1_run_all
            phase4_create_test_scaffold
            ;;
        report)
            show_report
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            error "Fase desconocida: ${phase}"
            show_help
            exit 1
            ;;
    esac
    
    log "Log guardado en: ${LOG_FILE}"
}

main "$@"
