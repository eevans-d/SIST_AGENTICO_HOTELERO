#!/bin/bash
# CI Local Pipeline - Agente Hotel API
# Runs all quality checks before pushing code

set -e

echo "╔════════════════════════════════════════════════╗"
echo "║  🚀 CI LOCAL PIPELINE - Agente Hotel API     ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

START_TIME=$(date +%s)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Report function
step() {
    echo -e "${BLUE}▶ $1${NC}"
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

error() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# STEP 1: Linting
step "Paso 1/7: Linting con Ruff..."
if docker compose -f docker-compose.dev.yml exec -T agente-api ruff check app/ tests/ --fix 2>/dev/null; then
    success "Linting pasado"
else
    error "Linting falló - ejecuta 'make lint' para ver detalles"
fi

# STEP 2: Format checking
step "Paso 2/7: Verificando formato con Ruff..."
if docker compose -f docker-compose.dev.yml exec -T agente-api ruff format --check app/ tests/ 2>/dev/null; then
    success "Formato correcto"
else
    warning "Formato incorrecto - ejecuta 'make fmt' para arreglar"
    # No bloqueante
fi

# STEP 3: Type checking (non-blocking)
step "Paso 3/7: Type checking con MyPy..."
if docker compose -f docker-compose.dev.yml exec -T agente-api mypy app/ --config-file pyproject.toml --no-error-summary 2>/dev/null || true; then
    success "Type checking completado"
else
    warning "Type checking con warnings (no bloqueante)"
fi

# STEP 4: Security scan
step "Paso 4/7: Escaneo de seguridad con Bandit..."
if docker compose -f docker-compose.dev.yml exec -T agente-api bandit -r app/ -c pyproject.toml -lll -q 2>/dev/null; then
    success "Escaneo de seguridad pasado"
else
    error "Vulnerabilidades de seguridad detectadas"
fi

# STEP 5: Unit tests
step "Paso 5/7: Ejecutando tests unitarios..."
if docker compose -f docker-compose.dev.yml exec -T agente-api python -m pytest tests/unit -v --tb=short 2>&1 | tail -20; then
    success "Tests unitarios pasados"
else
    error "Tests unitarios fallaron"
fi

# STEP 6: Integration tests
step "Paso 6/7: Ejecutando tests de integración..."
if docker compose -f docker-compose.dev.yml exec -T agente-api python -m pytest tests/integration -v --tb=short 2>&1 | tail -20; then
    success "Tests de integración pasados"
else
    error "Tests de integración fallaron"
fi

# STEP 7: Coverage check (non-blocking)
step "Paso 7/7: Verificando cobertura de tests..."
if docker compose -f docker-compose.dev.yml exec -T agente-api python -m pytest --cov=app --cov-report=term-missing --cov-fail-under=70 -q 2>/dev/null; then
    success "Cobertura ≥70%"
else
    warning "Cobertura <70% (no bloqueante en local)"
fi

# Final report
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║  ✅ CI LOCAL PIPELINE COMPLETADO              ║"
echo "╚════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}Duración: ${DURATION}s${NC}"
echo ""
echo "🚀 Todo listo para push!"
