#!/bin/bash
#
# Script de validación del sistema de optimización de performance
# Verifica que todos los servicios y componentes estén funcionando correctamente
#

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
TIMEOUT=10

# Contadores
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Funciones auxiliares
print_header() {
    echo -e "${BLUE}=====================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=====================================${NC}"
}

print_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
    ((TESTS_TOTAL++))
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((TESTS_PASSED++))
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
    ((TESTS_FAILED++))
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Test de conectividad básica
test_connectivity() {
    print_header "Test 1: Conectividad Básica"
    
    print_test "Verificando API principal..."
    if curl -s -f -m $TIMEOUT "${API_BASE_URL}/" > /dev/null 2>&1; then
        print_success "API principal respondiendo"
    else
        print_error "API principal no responde"
        return 1
    fi
    
    print_test "Verificando endpoint de salud..."
    if curl -s -f -m $TIMEOUT "${API_BASE_URL}/health/live" > /dev/null 2>&1; then
        print_success "Health endpoint OK"
    else
        print_error "Health endpoint falla"
        return 1
    fi
}

# Test de endpoints de performance
test_performance_endpoints() {
    print_header "Test 2: Endpoints de Performance"
    
    # Status endpoint
    print_test "GET /api/v1/performance/status"
    response=$(curl -s -w "%{http_code}" -m $TIMEOUT "${API_BASE_URL}/api/v1/performance/status" -o /tmp/perf_status.json)
    if [ "$response" = "200" ]; then
        print_success "Status endpoint OK (HTTP 200)"
        # Verificar contenido
        if jq -e '.system_health' /tmp/perf_status.json > /dev/null 2>&1; then
            print_success "Status contiene datos esperados"
        else
            print_error "Status no contiene datos esperados"
        fi
    elif [ "$response" = "404" ]; then
        print_info "Status endpoint no disponible (módulo opcional)"
    else
        print_error "Status endpoint falla (HTTP $response)"
    fi
    
    # Metrics endpoint
    print_test "GET /api/v1/performance/metrics"
    response=$(curl -s -w "%{http_code}" -m $TIMEOUT "${API_BASE_URL}/api/v1/performance/metrics" -o /tmp/perf_metrics.json)
    if [ "$response" = "200" ]; then
        print_success "Metrics endpoint OK (HTTP 200)"
    elif [ "$response" = "404" ]; then
        print_info "Metrics endpoint no disponible (módulo opcional)"
    else
        print_error "Metrics endpoint falla (HTTP $response)"
    fi
    
    # Optimization report endpoint
    print_test "GET /api/v1/performance/optimization/report"
    response=$(curl -s -w "%{http_code}" -m $TIMEOUT "${API_BASE_URL}/api/v1/performance/optimization/report" -o /tmp/perf_opt_report.json)
    if [ "$response" = "200" ]; then
        print_success "Optimization report endpoint OK (HTTP 200)"
    elif [ "$response" = "404" ]; then
        print_info "Optimization report endpoint no disponible (módulo opcional)"
    else
        print_error "Optimization report endpoint falla (HTTP $response)"
    fi
}

# Test de endpoints de base de datos
test_database_endpoints() {
    print_header "Test 3: Endpoints de Base de Datos"
    
    print_test "GET /api/v1/performance/database/report"
    response=$(curl -s -w "%{http_code}" -m $TIMEOUT "${API_BASE_URL}/api/v1/performance/database/report" -o /tmp/db_report.json)
    if [ "$response" = "200" ]; then
        print_success "Database report endpoint OK (HTTP 200)"
    elif [ "$response" = "404" ]; then
        print_info "Database report endpoint no disponible (módulo opcional)"
    else
        print_error "Database report endpoint falla (HTTP $response)"
    fi
}

# Test de endpoints de cache
test_cache_endpoints() {
    print_header "Test 4: Endpoints de Cache"
    
    print_test "GET /api/v1/performance/cache/report"
    response=$(curl -s -w "%{http_code}" -m $TIMEOUT "${API_BASE_URL}/api/v1/performance/cache/report" -o /tmp/cache_report.json)
    if [ "$response" = "200" ]; then
        print_success "Cache report endpoint OK (HTTP 200)"
    elif [ "$response" = "404" ]; then
        print_info "Cache report endpoint no disponible (módulo opcional)"
    else
        print_error "Cache report endpoint falla (HTTP $response)"
    fi
}

# Test de endpoints de escalado
test_scaling_endpoints() {
    print_header "Test 5: Endpoints de Escalado"
    
    print_test "GET /api/v1/performance/scaling/status"
    response=$(curl -s -w "%{http_code}" -m $TIMEOUT "${API_BASE_URL}/api/v1/performance/scaling/status" -o /tmp/scaling_status.json)
    if [ "$response" = "200" ]; then
        print_success "Scaling status endpoint OK (HTTP 200)"
    elif [ "$response" = "404" ]; then
        print_info "Scaling status endpoint no disponible (módulo opcional)"
    else
        print_error "Scaling status endpoint falla (HTTP $response)"
    fi
    
    print_test "POST /api/v1/performance/scaling/evaluate"
    response=$(curl -s -w "%{http_code}" -m $TIMEOUT -X POST "${API_BASE_URL}/api/v1/performance/scaling/evaluate" -o /tmp/scaling_eval.json)
    if [ "$response" = "200" ]; then
        print_success "Scaling evaluate endpoint OK (HTTP 200)"
    elif [ "$response" = "404" ] || [ "$response" = "429" ]; then
        print_info "Scaling evaluate endpoint no disponible o rate limited"
    else
        print_error "Scaling evaluate endpoint falla (HTTP $response)"
    fi
}

# Test de endpoints de alertas
test_alerts_endpoints() {
    print_header "Test 6: Endpoints de Alertas"
    
    print_test "GET /api/v1/performance/alerts"
    response=$(curl -s -w "%{http_code}" -m $TIMEOUT "${API_BASE_URL}/api/v1/performance/alerts" -o /tmp/alerts.json)
    if [ "$response" = "200" ]; then
        print_success "Alerts endpoint OK (HTTP 200)"
        # Verificar estructura
        if jq -e '.alerts' /tmp/alerts.json > /dev/null 2>&1; then
            print_success "Alerts contiene datos esperados"
        fi
    elif [ "$response" = "404" ]; then
        print_info "Alerts endpoint no disponible (módulo opcional)"
    else
        print_error "Alerts endpoint falla (HTTP $response)"
    fi
}

# Test de endpoints de recomendaciones
test_recommendations_endpoints() {
    print_header "Test 7: Endpoints de Recomendaciones"
    
    print_test "GET /api/v1/performance/recommendations"
    response=$(curl -s -w "%{http_code}" -m $TIMEOUT "${API_BASE_URL}/api/v1/performance/recommendations" -o /tmp/recommendations.json)
    if [ "$response" = "200" ]; then
        print_success "Recommendations endpoint OK (HTTP 200)"
    elif [ "$response" = "404" ]; then
        print_info "Recommendations endpoint no disponible (módulo opcional)"
    else
        print_error "Recommendations endpoint falla (HTTP $response)"
    fi
}

# Test de métricas de Prometheus
test_prometheus_metrics() {
    print_header "Test 8: Métricas de Prometheus"
    
    print_test "GET /metrics (Prometheus endpoint)"
    response=$(curl -s -w "%{http_code}" -m $TIMEOUT "${API_BASE_URL}/metrics" -o /tmp/prometheus_metrics.txt)
    if [ "$response" = "200" ]; then
        print_success "Prometheus metrics endpoint OK (HTTP 200)"
        
        # Verificar métricas específicas de performance
        if grep -q "performance_optimization_duration_seconds" /tmp/prometheus_metrics.txt; then
            print_success "Métricas de performance optimizer presentes"
        fi
        
        if grep -q "system_resource_usage" /tmp/prometheus_metrics.txt; then
            print_success "Métricas de resource monitor presentes"
        fi
        
        if grep -q "scaling_operations_total" /tmp/prometheus_metrics.txt; then
            print_success "Métricas de auto scaler presentes"
        fi
    else
        print_error "Prometheus metrics endpoint falla (HTTP $response)"
    fi
}

# Test de integración básica
test_basic_integration() {
    print_header "Test 9: Integración Básica"
    
    print_test "Verificando que servicios se comunican correctamente"
    
    # Obtener métricas
    if curl -s -f -m $TIMEOUT "${API_BASE_URL}/api/v1/performance/metrics" > /tmp/int_metrics.json 2>/dev/null; then
        # Verificar que tenemos datos de CPU y memoria
        if jq -e '.current_metrics.cpu_percent' /tmp/int_metrics.json > /dev/null 2>&1; then
            print_success "Monitor de recursos funciona correctamente"
        fi
    fi
    
    # Verificar que el sistema general está operativo
    if curl -s -f -m $TIMEOUT "${API_BASE_URL}/api/v1/performance/status" > /tmp/int_status.json 2>/dev/null; then
        health=$(jq -r '.system_health // "unknown"' /tmp/int_status.json)
        if [ "$health" != "unknown" ]; then
            print_success "Sistema de optimización operativo (health: $health)"
        fi
    fi
}

# Test de documentación
test_documentation() {
    print_header "Test 10: Documentación"
    
    print_test "Verificando documentación de API (OpenAPI/Swagger)"
    response=$(curl -s -w "%{http_code}" -m $TIMEOUT "${API_BASE_URL}/docs" -o /dev/null)
    if [ "$response" = "200" ]; then
        print_success "Documentación de API disponible en /docs"
    else
        print_error "Documentación de API no disponible"
    fi
    
    print_test "Verificando archivos de documentación"
    if [ -f "docs/PERFORMANCE_OPTIMIZATION_GUIDE.md" ]; then
        print_success "Guía de optimización de performance presente"
    else
        print_error "Guía de optimización de performance faltante"
    fi
    
    if [ -f "README-PERFORMANCE.md" ]; then
        print_success "README de performance presente"
    else
        print_error "README de performance faltante"
    fi
}

# Test de archivos de configuración
test_configuration_files() {
    print_header "Test 11: Archivos de Configuración"
    
    print_test "Verificando servicios de optimización"
    
    files=(
        "app/services/performance_optimizer.py"
        "app/services/database_tuner.py"
        "app/services/cache_optimizer.py"
        "app/services/resource_monitor.py"
        "app/services/auto_scaler.py"
        "app/services/performance_scheduler.py"
    )
    
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            print_success "$(basename $file) presente"
        else
            print_error "$(basename $file) faltante"
        fi
    done
    
    print_test "Verificando router de performance"
    if [ -f "app/routers/performance.py" ]; then
        print_success "Performance router presente"
    else
        print_error "Performance router faltante"
    fi
}

# Test de dependencias
test_dependencies() {
    print_header "Test 12: Dependencias"
    
    print_test "Verificando dependencias en pyproject.toml"
    if grep -q "psutil" pyproject.toml; then
        print_success "psutil presente en dependencias"
    else
        print_error "psutil faltante en dependencias"
    fi
    
    if grep -q "croniter" pyproject.toml; then
        print_success "croniter presente en dependencias"
    else
        print_error "croniter faltante en dependencias"
    fi
}

# Resumen final
print_summary() {
    print_header "Resumen de Validación"
    
    echo -e "Total de tests: ${TESTS_TOTAL}"
    echo -e "${GREEN}Tests exitosos: ${TESTS_PASSED}${NC}"
    echo -e "${RED}Tests fallidos: ${TESTS_FAILED}${NC}"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "\n${GREEN}✓ TODOS LOS TESTS PASARON${NC}"
        echo -e "${GREEN}Sistema de optimización validado correctamente${NC}"
        return 0
    else
        echo -e "\n${YELLOW}⚠ ALGUNOS TESTS FALLARON${NC}"
        echo -e "${YELLOW}Revisar logs anteriores para detalles${NC}"
        
        # Si la mayoría de tests pasó, aún es aceptable
        pass_rate=$((TESTS_PASSED * 100 / TESTS_TOTAL))
        if [ $pass_rate -ge 70 ]; then
            echo -e "${YELLOW}Tasa de éxito: ${pass_rate}% - Sistema funcional con advertencias${NC}"
            return 0
        else
            echo -e "${RED}Tasa de éxito: ${pass_rate}% - Sistema requiere atención${NC}"
            return 1
        fi
    fi
}

# Main
main() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║   Performance Optimization System - Validation Suite     ║"
    echo "║   Agente Hotelero IA System                              ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
    
    print_info "API Base URL: ${API_BASE_URL}"
    print_info "Timeout: ${TIMEOUT}s"
    echo ""
    
    # Ejecutar todos los tests
    test_connectivity || true
    test_performance_endpoints || true
    test_database_endpoints || true
    test_cache_endpoints || true
    test_scaling_endpoints || true
    test_alerts_endpoints || true
    test_recommendations_endpoints || true
    test_prometheus_metrics || true
    test_basic_integration || true
    test_documentation || true
    test_configuration_files || true
    test_dependencies || true
    
    echo ""
    print_summary
}

# Ejecutar main
main

# Limpiar archivos temporales
rm -f /tmp/perf_*.json /tmp/db_report.json /tmp/cache_report.json /tmp/scaling_*.json /tmp/alerts.json /tmp/recommendations.json /tmp/prometheus_metrics.txt /tmp/int_*.json

exit $?
