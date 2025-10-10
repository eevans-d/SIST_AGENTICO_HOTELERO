#!/bin/bash

###############################################################################
# QUICK VALIDATION SCRIPT - Sistema Agente Hotelero IA
# Validación rápida post-limpieza
# Version: 1.0.0
###############################################################################

# No usar set -e para que continúe con todos los checks

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   VALIDACIÓN RÁPIDA - Sistema Agente Hotelero IA      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

cd /home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api

PASS=0
FAIL=0

# Función para test
test_check() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} $2"
        ((FAIL++))
    fi
}

echo -e "${YELLOW}[1] Verificando Estructura del Proyecto...${NC}"
[ -d "app" ]; test_check $? "Directorio app/ existe"
[ -d "tests" ]; test_check $? "Directorio tests/ existe"
[ -d "docs" ]; test_check $? "Directorio docs/ existe"
[ -d "scripts" ]; test_check $? "Directorio scripts/ existe"
[ -d "docker" ]; test_check $? "Directorio docker/ existe"

echo ""
echo -e "${YELLOW}[2] Verificando Archivos Esenciales...${NC}"
[ -f "pyproject.toml" ]; test_check $? "pyproject.toml existe"
[ -f "Makefile" ]; test_check $? "Makefile existe"
[ -f "README.md" ]; test_check $? "README.md existe"
[ -f "docker-compose.yml" ]; test_check $? "docker-compose.yml existe"
[ -f ".env.example" ]; test_check $? ".env.example existe"

echo ""
echo -e "${YELLOW}[3] Verificando Limpieza...${NC}"
[ ! -d "__pycache__" ]; test_check $? "No hay __pycache__ en raíz"
[ ! -d ".pytest_cache" ]; test_check $? ".pytest_cache eliminado"
[ ! -d ".ruff_cache" ]; test_check $? ".ruff_cache eliminado"
[ ! -d "venv" ]; test_check $? "venv/ eliminado"
[ ! -d "node_modules" ]; test_check $? "node_modules/ eliminado"

echo ""
echo -e "${YELLOW}[4] Verificando Organización...${NC}"
[ -d "tests/legacy" ]; test_check $? "tests/legacy/ creado"
[ -d "docs/archive" ]; test_check $? "docs/archive/ creado"
[ -d "docker/compose-archive" ]; test_check $? "docker/compose-archive/ creado"
[ -d "backups" ]; test_check $? "backups/ creado"
[ -d "tools" ]; test_check $? "tools/ creado"

echo ""
echo -e "${YELLOW}[5] Verificando Servicios (Phase 12)...${NC}"
[ -f "app/services/performance_optimizer.py" ]; test_check $? "Performance Optimizer existe"
[ -f "app/services/database_tuner.py" ]; test_check $? "Database Tuner existe"
[ -f "app/services/cache_optimizer.py" ]; test_check $? "Cache Optimizer existe"
[ -f "app/services/resource_monitor.py" ]; test_check $? "Resource Monitor existe"
[ -f "app/services/auto_scaler.py" ]; test_check $? "Auto Scaler existe"
[ -f "app/services/performance_scheduler.py" ]; test_check $? "Performance Scheduler existe"
[ -f "app/routers/performance.py" ]; test_check $? "Performance Router existe"

echo ""
echo -e "${YELLOW}[6] Verificando Tests (Phase 12)...${NC}"
[ -f "tests/unit/test_performance_optimizer.py" ]; test_check $? "Test Performance Optimizer existe"
[ -f "tests/unit/test_resource_monitor.py" ]; test_check $? "Test Resource Monitor existe"
[ -f "tests/integration/test_optimization_system.py" ]; test_check $? "Test Integration existe"

echo ""
echo -e "${YELLOW}[7] Verificando Documentación...${NC}"
[ -f "docs/PHASE_12_SUMMARY.md" ]; test_check $? "Phase 12 Summary existe"
[ -f "docs/PERFORMANCE_OPTIMIZATION_GUIDE.md" ]; test_check $? "Performance Guide existe"
[ -f "README-PERFORMANCE.md" ]; test_check $? "README Performance existe"
[ -f "docs/CLEANUP_REPORT_20251009.md" ]; test_check $? "Cleanup Report existe"
[ -f "docs/FINAL_PROJECT_SUMMARY.md" ]; test_check $? "Final Summary existe"

echo ""
echo -e "${YELLOW}[8] Verificando Scripts...${NC}"
[ -f "scripts/deep_cleanup.sh" ]; test_check $? "Deep Cleanup script existe"
[ -f "scripts/validate_performance_system.sh" ]; test_check $? "Validation script existe"
[ -x "scripts/deep_cleanup.sh" ]; test_check $? "Deep Cleanup es ejecutable"
[ -x "scripts/validate_performance_system.sh" ]; test_check $? "Validation es ejecutable"

echo ""
echo -e "${YELLOW}[9] Estadísticas del Proyecto...${NC}"
echo -e "  ${BLUE}•${NC} Archivos Python (app/): $(find app -name '*.py' 2>/dev/null | wc -l)"
echo -e "  ${BLUE}•${NC} Archivos de Test: $(find tests -name '*.py' 2>/dev/null | wc -l)"
echo -e "  ${BLUE}•${NC} Documentos Markdown: $(find . -type f -name '*.md' ! -path '*/.venv/*' ! -path '*/node_modules/*' ! -path '*/.git/*' 2>/dev/null | wc -l)"
echo -e "  ${BLUE}•${NC} Scripts: $(find scripts -type f 2>/dev/null | wc -l)"

echo ""
echo -e "${YELLOW}[10] Tamaños de Directorios...${NC}"
echo -e "  ${BLUE}•${NC} agente-hotel-api/: $(du -sh . 2>/dev/null | cut -f1)"
echo -e "  ${BLUE}•${NC} app/: $(du -sh app 2>/dev/null | cut -f1)"
echo -e "  ${BLUE}•${NC} tests/: $(du -sh tests 2>/dev/null | cut -f1)"
echo -e "  ${BLUE}•${NC} docs/: $(du -sh docs 2>/dev/null | cut -f1)"
echo -e "  ${BLUE}•${NC} docker/: $(du -sh docker 2>/dev/null | cut -f1)"

echo ""
echo "═════════════════════════════════════════════════════"
echo -e "  ${GREEN}PASS: $PASS${NC}  |  ${RED}FAIL: $FAIL${NC}"
echo "═════════════════════════════════════════════════════"

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✅ VALIDACIÓN COMPLETADA EXITOSAMENTE${NC}"
    echo ""
    echo "Próximos pasos recomendados:"
    echo "  1. Ejecutar tests: poetry run pytest tests/ -v"
    echo "  2. Iniciar sistema: make docker-up"
    echo "  3. Verificar health: make health"
    echo "  4. Validar performance: ./scripts/validate_performance_system.sh"
    exit 0
else
    echo -e "${RED}⚠️  VALIDACIÓN COMPLETADA CON ERRORES${NC}"
    echo ""
    echo "Revisa los errores arriba y corrige antes de continuar."
    exit 1
fi
