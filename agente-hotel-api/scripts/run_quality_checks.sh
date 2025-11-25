#!/bin/bash
# Script de Verificación de Calidad Completa
# Ejecuta todas las verificaciones de calidad del código

set -e

PROJECT_ROOT="/home/eevan/ProyectosIA/SIST_AGENTICO_HOTELERO/agente-hotel-api"
cd "$PROJECT_ROOT"

echo "🔍 INICIANDO VERIFICACIONES DE CALIDAD DEL CÓDIGO"
echo "=================================================="
echo ""

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# Función para reportar resultado
report_check() {
    local check_name=$1
    local status=$2
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    if [ "$status" = "0" ]; then
        echo -e "${GREEN}✓${NC} $check_name: PASADO"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo -e "${RED}✗${NC} $check_name: FALLADO"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
}

# 1. VERIFICACIÓN DE SINTAXIS
echo "1️⃣  Verificando sintaxis Python..."
if python3 -m py_compile app/**/*.py 2>/dev/null; then
    report_check "Sintaxis Python" 0
else
    report_check "Sintaxis Python" 1
fi
echo ""

# 2. LINTING CON RUFF
echo "2️⃣  Ejecutando linting con Ruff..."
if poetry run ruff check app/ --quiet 2>/dev/null; then
    report_check "Ruff Linting" 0
else
    echo "   Errores encontrados:"
    poetry run ruff check app/ --quiet | head -10
    report_check "Ruff Linting" 1
fi
echo ""

# 3. FORMATEO DE CÓDIGO
echo "3️⃣  Verificando formateo de código..."
if poetry run ruff format --check app/ --quiet 2>/dev/null; then
    report_check "Formateo Ruff" 0
else
    report_check "Formateo Ruff" 1
    echo "   Ejecuta: make fmt"
fi
echo ""

# 4. IMPORTS ORDENADOS
echo "4️⃣  Verificando orden de imports..."
if poetry run ruff check app/ --select I --quiet 2>/dev/null; then
    report_check "Orden de Imports" 0
else
    report_check "Orden de Imports" 1
fi
echo ""

# 5. COMPLEJIDAD CICLOMÁTICA
echo "5️⃣  Analizando complejidad ciclomática..."
if poetry run ruff check app/ --select C901 --quiet 2>/dev/null; then
    report_check "Complejidad Ciclomática" 0
else
    echo "   Funciones con alta complejidad detectadas"
    poetry run ruff check app/ --select C901 | head -5
    report_check "Complejidad Ciclomática" 1
fi
echo ""

# 6. SECURITY CHECKS
echo "6️⃣  Verificando seguridad con Bandit..."
if command -v bandit &> /dev/null; then
    if bandit -r app/ -ll -q 2>/dev/null; then
        report_check "Security Scan (Bandit)" 0
    else
        report_check "Security Scan (Bandit)" 1
    fi
else
    echo "   ⚠️  Bandit no instalado (pip install bandit)"
    report_check "Security Scan (Bandit)" 1
fi
echo ""

# 7. DEPENDENCY VULNERABILITIES
echo "7️⃣  Verificando vulnerabilidades en dependencias..."
if command -v safety &> /dev/null; then
    if poetry export -f requirements.txt | safety check --stdin --json 2>/dev/null > /tmp/safety_check.json; then
        report_check "Vulnerability Scan (Safety)" 0
    else
        vuln_count=$(cat /tmp/safety_check.json | grep -o "\"vulnerability\"" | wc -l)
        echo "   ⚠️  $vuln_count vulnerabilidades encontradas"
        report_check "Vulnerability Scan (Safety)" 1
    fi
else
    echo "   ⚠️  Safety no instalado (pip install safety)"
    report_check "Vulnerability Scan (Safety)" 1
fi
echo ""

# 8. SECRET SCANNING
echo "8️⃣  Buscando secretos expuestos..."
if command -v gitleaks &> /dev/null; then
    if gitleaks detect --no-git --quiet 2>/dev/null; then
        report_check "Secret Scanning (Gitleaks)" 0
    else
        report_check "Secret Scanning (Gitleaks)" 1
    fi
else
    echo "   ℹ️  Gitleaks no instalado"
    # Búsqueda básica de patrones
    if ! grep -r "password.*=.*['\"]" app/ 2>/dev/null | grep -v ".pyc" | grep -q .; then
        report_check "Secret Scanning (Basic)" 0
    else
        report_check "Secret Scanning (Basic)" 1
    fi
fi
echo ""

# 9. TESTS UNITARIOS
echo "9️⃣  Ejecutando tests unitarios..."
if poetry run pytest tests/unit/ -q --tb=no 2>/dev/null; then
    report_check "Tests Unitarios" 0
else
    report_check "Tests Unitarios" 1
fi
echo ""

# 10. COBERTURA DE TESTS
echo "🔟  Calculando cobertura de tests..."
if poetry run pytest --cov=app --cov-report=term-missing --cov-report=json tests/ -q 2>/dev/null; then
    coverage=$(cat coverage.json | grep -o '"percent_covered": [0-9.]*' | grep -o '[0-9.]*')
    if [ -n "$coverage" ]; then
        echo "   📊 Cobertura: ${coverage}%"
        if (( $(echo "$coverage >= 70" | bc -l) )); then
            report_check "Cobertura de Tests (≥70%)" 0
        else
            report_check "Cobertura de Tests (≥70%)" 1
        fi
    else
        report_check "Cobertura de Tests" 1
    fi
else
    report_check "Cobertura de Tests" 1
fi
echo ""

# 11. STRUCTURE VALIDATION
echo "1️⃣1️⃣  Validando estructura de proyecto..."
missing_files=0
for file in "app/main.py" "app/core/settings.py" "app/routers/health.py" "pyproject.toml" "Dockerfile"; do
    if [ ! -f "$file" ]; then
        echo "   ⚠️  Archivo faltante: $file"
        missing_files=$((missing_files + 1))
    fi
done

if [ $missing_files -eq 0 ]; then
    report_check "Estructura de Proyecto" 0
else
    report_check "Estructura de Proyecto" 1
fi
echo ""

# 12. DOCKER BUILD
echo "1️⃣2️⃣  Verificando Dockerfile..."
if docker build -f Dockerfile -t agente-hotel-test --quiet . > /dev/null 2>&1; then
    report_check "Docker Build" 0
    docker rmi agente-hotel-test > /dev/null 2>&1
else
    report_check "Docker Build" 1
fi
echo ""

# 13. DOCUMENTACIÓN
echo "1️⃣3️⃣  Verificando documentación..."
doc_score=0
[ -f "README.md" ] && doc_score=$((doc_score + 1))
[ -f "docs/HANDOVER_PACKAGE.md" ] && doc_score=$((doc_score + 1))
[ -f "docs/OPERATIONS_MANUAL.md" ] && doc_score=$((doc_score + 1))
[ -f "docs/ROBUSTNESS_ASSESSMENT.md" ] && doc_score=$((doc_score + 1))

if [ $doc_score -ge 3 ]; then
    report_check "Documentación ($doc_score/4 archivos)" 0
else
    report_check "Documentación ($doc_score/4 archivos)" 1
fi
echo ""

# 14. TYPE CHECKING (mypy)
echo "1️⃣4️⃣  Verificando tipos con MyPy..."
if command -v mypy &> /dev/null; then
    if poetry run mypy app/ --ignore-missing-imports --no-error-summary 2>/dev/null | grep -q "Success"; then
        report_check "Type Checking (MyPy)" 0
    else
        report_check "Type Checking (MyPy)" 1
    fi
else
    echo "   ℹ️  MyPy no instalado (pip install mypy)"
    report_check "Type Checking (MyPy)" 1
fi
echo ""

# 15. CONFIGURACIÓN DE PRODUCCIÓN
echo "1️⃣5️⃣  Verificando configuración de producción..."
prod_check=0
if [ -f ".env.example" ]; then
    prod_check=$((prod_check + 1))
fi
if [ -f "docker-compose.production.yml" ]; then
    prod_check=$((prod_check + 1))
fi
if [ -f "Dockerfile.production" ]; then
    prod_check=$((prod_check + 1))
fi

if [ $prod_check -ge 2 ]; then
    report_check "Configuración Producción ($prod_check/3)" 0
else
    report_check "Configuración Producción ($prod_check/3)" 1
fi
echo ""

# REPORTE FINAL
echo ""
echo "=================================================="
echo "📊 RESUMEN DE VERIFICACIONES DE CALIDAD"
echo "=================================================="
echo ""
echo "Total de verificaciones: $TOTAL_CHECKS"
echo -e "${GREEN}Pasadas: $PASSED_CHECKS${NC}"
echo -e "${RED}Falladas: $FAILED_CHECKS${NC}"
echo ""

# Calcular porcentaje
PERCENTAGE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))

if [ $PERCENTAGE -ge 90 ]; then
    echo -e "${GREEN}🎉 CALIDAD EXCELENTE: ${PERCENTAGE}%${NC}"
    echo "✅ El proyecto está listo para producción"
    exit 0
elif [ $PERCENTAGE -ge 70 ]; then
    echo -e "${YELLOW}⚠️  CALIDAD BUENA: ${PERCENTAGE}%${NC}"
    echo "Algunas mejoras recomendadas antes de producción"
    exit 1
else
    echo -e "${RED}❌ CALIDAD INSUFICIENTE: ${PERCENTAGE}%${NC}"
    echo "Correcciones necesarias antes de continuar"
    exit 1
fi
