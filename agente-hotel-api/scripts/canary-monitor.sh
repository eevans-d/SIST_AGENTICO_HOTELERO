#!/usr/bin/env bash

# Script para monitoreo de despliegue canary
# Autor: Copilot
# Fecha: 2025-10-07

set -e  # Detener en caso de error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables
BASELINE_MONITORING_PERIOD=${BASELINE_MONITORING_PERIOD:-15m}  # Periodo de monitoreo de línea base (15 minutos)
CANARY_MONITORING_PERIOD=${CANARY_MONITORING_PERIOD:-15m}      # Periodo de monitoreo de canary (15 minutos)
ERROR_RATE_THRESHOLD=${ERROR_RATE_THRESHOLD:-0.02}             # Umbral de tasa de error (2%)
LATENCY_THRESHOLD=${LATENCY_THRESHOLD:-1.1}                    # Umbral de latencia (10% más que línea base)
PROMETHEUS_URL=${PROMETHEUS_URL:-"http://localhost:9091"}      # URL de Prometheus

# Archivo de reporte
REPORT_FILE=".playbook/canary_diff_report.json"
mkdir -p .playbook

# Funciones de utilidad
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validar conexión a Prometheus
validate_prometheus() {
    log_info "Validando conexión a Prometheus en $PROMETHEUS_URL..."
    
    if curl -s "$PROMETHEUS_URL/-/healthy" | grep -q "Prometheus"; then
        log_success "Prometheus accesible y funcionando correctamente"
        return 0
    else
        log_error "No se puede acceder a Prometheus. Verifica la URL y que el servicio esté corriendo."
        return 1
    fi
}

# Obtener métrica de Prometheus
get_prometheus_metric() {
    local query=$1
    local start_time=$2
    local end_time=$3
    local step=${4:-60s}
    
    local result=$(curl -s --data-urlencode "query=${query}" \
                         --data-urlencode "start=${start_time}" \
                         --data-urlencode "end=${end_time}" \
                         --data-urlencode "step=${step}" \
                         "${PROMETHEUS_URL}/api/v1/query_range")
    
    echo "$result"
}

# Analizar tasa de error para baseline y canary
analyze_error_rate() {
    log_info "Analizando tasa de error..."
    
    # Tiempo actual y hace 30 minutos
    local now=$(date +%s)
    local thirty_min_ago=$((now - 1800))
    
    # Consulta para tasa de error de baseline (últimos 30 min - 15 min)
    local baseline_query='sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))'
    local baseline_start=$thirty_min_ago
    local baseline_end=$((now - 900))  # 15 minutos atrás
    
    # Consulta para tasa de error de canary (últimos 15 min)
    local canary_start=$((now - 900))  # 15 minutos atrás
    local canary_end=$now
    
    # Obtener datos
    local baseline_data=$(get_prometheus_metric "$baseline_query" "$baseline_start" "$baseline_end")
    local canary_data=$(get_prometheus_metric "$baseline_query" "$canary_start" "$canary_end")
    
    # Extraer valores promedio
    local baseline_error_rate=$(echo "$baseline_data" | jq -r '.data.result[0].values | map(.[1]|tonumber) | add / length')
    local canary_error_rate=$(echo "$canary_data" | jq -r '.data.result[0].values | map(.[1]|tonumber) | add / length')
    
    # Manejar casos donde no hay datos
    if [ "$baseline_error_rate" == "null" ] || [ "$canary_error_rate" == "null" ]; then
        log_warning "No hay suficientes datos para analizar la tasa de error"
        baseline_error_rate=0
        canary_error_rate=0
    fi
    
    log_info "Tasa de error baseline: ${baseline_error_rate}"
    log_info "Tasa de error canary: ${canary_error_rate}"
    
    # Comparar tasas de error
    if (( $(echo "$canary_error_rate > $ERROR_RATE_THRESHOLD" | bc -l) )); then
        log_error "Tasa de error de canary (${canary_error_rate}) supera el umbral (${ERROR_RATE_THRESHOLD})"
        ERROR_RESULT="FAIL"
    elif (( $(echo "$canary_error_rate > $baseline_error_rate * 2" | bc -l) )); then
        log_error "Tasa de error de canary (${canary_error_rate}) es más del doble que baseline (${baseline_error_rate})"
        ERROR_RESULT="FAIL"
    else
        log_success "Tasa de error de canary dentro de límites aceptables"
        ERROR_RESULT="PASS"
    fi
    
    # Guardar resultados
    ERROR_BASELINE=$baseline_error_rate
    ERROR_CANARY=$canary_error_rate
}

# Analizar latencia P95 para baseline y canary
analyze_latency() {
    log_info "Analizando latencia P95..."
    
    # Tiempo actual y hace 30 minutos
    local now=$(date +%s)
    local thirty_min_ago=$((now - 1800))
    
    # Consulta para latencia P95 de baseline (últimos 30 min - 15 min)
    local baseline_query='histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))'
    local baseline_start=$thirty_min_ago
    local baseline_end=$((now - 900))  # 15 minutos atrás
    
    # Consulta para latencia P95 de canary (últimos 15 min)
    local canary_start=$((now - 900))  # 15 minutos atrás
    local canary_end=$now
    
    # Obtener datos
    local baseline_data=$(get_prometheus_metric "$baseline_query" "$baseline_start" "$baseline_end")
    local canary_data=$(get_prometheus_metric "$baseline_query" "$canary_start" "$canary_end")
    
    # Extraer valores promedio
    local baseline_latency=$(echo "$baseline_data" | jq -r '.data.result[0].values | map(.[1]|tonumber) | add / length')
    local canary_latency=$(echo "$canary_data" | jq -r '.data.result[0].values | map(.[1]|tonumber) | add / length')
    
    # Manejar casos donde no hay datos
    if [ "$baseline_latency" == "null" ] || [ "$canary_latency" == "null" ]; then
        log_warning "No hay suficientes datos para analizar la latencia"
        baseline_latency=0
        canary_latency=0
    fi
    
    log_info "Latencia P95 baseline: ${baseline_latency}s"
    log_info "Latencia P95 canary: ${canary_latency}s"
    
    # Comparar latencias
    if (( $(echo "$canary_latency > $baseline_latency * $LATENCY_THRESHOLD" | bc -l) )); then
        log_error "Latencia P95 de canary (${canary_latency}s) supera el umbral (${baseline_latency}s * ${LATENCY_THRESHOLD})"
        LATENCY_RESULT="FAIL"
    else
        log_success "Latencia P95 de canary dentro de límites aceptables"
        LATENCY_RESULT="PASS"
    fi
    
    # Guardar resultados
    LATENCY_BASELINE=$baseline_latency
    LATENCY_CANARY=$canary_latency
}

# Verificar estado del circuit breaker
check_circuit_breaker() {
    log_info "Verificando estado del circuit breaker..."
    
    # Consulta para el estado del circuit breaker
    local query='pms_circuit_breaker_state{service="pms_adapter"}'
    local now=$(date +%s)
    local fifteen_min_ago=$((now - 900))
    
    # Obtener datos
    local cb_data=$(get_prometheus_metric "$query" "$fifteen_min_ago" "$now")
    
    # Extraer último valor
    local cb_state=$(echo "$cb_data" | jq -r '.data.result[0].values[-1][1]')
    
    # Manejar caso donde no hay datos
    if [ -z "$cb_state" ] || [ "$cb_state" == "null" ]; then
        log_warning "No hay datos del circuit breaker"
        CB_STATE="unknown"
        CB_RESULT="UNKNOWN"
        return
    fi
    
    case "$cb_state" in
        "0")
            log_success "Circuit breaker está CERRADO (estado normal)"
            CB_STATE="CLOSED"
            CB_RESULT="PASS"
            ;;
        "1")
            log_error "Circuit breaker está ABIERTO (error)"
            CB_STATE="OPEN"
            CB_RESULT="FAIL"
            ;;
        "2")
            log_warning "Circuit breaker está MEDIO-ABIERTO (recuperándose)"
            CB_STATE="HALF_OPEN"
            CB_RESULT="WARNING"
            ;;
        *)
            log_warning "Estado del circuit breaker desconocido: $cb_state"
            CB_STATE="UNKNOWN"
            CB_RESULT="UNKNOWN"
            ;;
    esac
}

# Verificar métricas de negocio críticas
check_business_metrics() {
    log_info "Verificando métricas de negocio críticas..."
    
    # Consulta para reservas creadas en las últimas 24 horas
    local query='sum(increase(business_reservations_total{operation="create",status="success"}[24h]))'
    local now=$(date +%s)
    local day_ago=$((now - 86400))
    
    # Obtener datos
    local res_data=$(curl -s --data-urlencode "query=${query}" "${PROMETHEUS_URL}/api/v1/query")
    
    # Extraer valor
    local reservations=$(echo "$res_data" | jq -r '.data.result[0].value[1]')
    
    # Manejar caso donde no hay datos
    if [ -z "$reservations" ] || [ "$reservations" == "null" ]; then
        log_warning "No hay datos de reservas"
        RESERVATIONS=0
    else
        RESERVATIONS=$reservations
        log_info "Reservas creadas en las últimas 24 horas: $RESERVATIONS"
    fi
}

# Generar reporte de resultados
generate_report() {
    log_info "Generando reporte de resultados..."
    
    # Determinar estado general
    if [ "$ERROR_RESULT" == "FAIL" ] || [ "$LATENCY_RESULT" == "FAIL" ] || [ "$CB_RESULT" == "FAIL" ]; then
        OVERALL_STATUS="FAIL"
    elif [ "$ERROR_RESULT" == "PASS" ] && [ "$LATENCY_RESULT" == "PASS" ] && [ "$CB_RESULT" != "FAIL" ]; then
        OVERALL_STATUS="PASS"
    else
        OVERALL_STATUS="WARNING"
    fi
    
    # Crear JSON de reporte
    cat > "$REPORT_FILE" << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "status": "$OVERALL_STATUS",
  "metrics": {
    "error_rate": {
      "baseline": $ERROR_BASELINE,
      "canary": $ERROR_CANARY,
      "threshold": $ERROR_RATE_THRESHOLD,
      "status": "$ERROR_RESULT"
    },
    "latency_p95": {
      "baseline": $LATENCY_BASELINE,
      "canary": $LATENCY_CANARY,
      "threshold_factor": $LATENCY_THRESHOLD,
      "status": "$LATENCY_RESULT"
    },
    "circuit_breaker": {
      "state": "$CB_STATE",
      "status": "$CB_RESULT"
    },
    "business": {
      "reservations_24h": $RESERVATIONS
    }
  },
  "recommendation": "$([ "$OVERALL_STATUS" == "PASS" ] && echo "PROCEED" || echo "ROLLBACK")"
}
EOF
    
    log_info "Reporte generado en $REPORT_FILE"
    
    # Mostrar resumen
    echo -e "\n${BLUE}========== RESUMEN DE CANARY DIFF ==========${NC}"
    echo -e "Error Rate: ${ERROR_RESULT}"
    echo -e "Latencia P95: ${LATENCY_RESULT}"
    echo -e "Circuit Breaker: ${CB_RESULT}"
    echo -e "Reservas 24h: ${RESERVATIONS}"
    echo -e "${BLUE}=========================================${NC}"
    echo -e "Estado general: ${OVERALL_STATUS}"
    echo -e "Recomendación: $([ "$OVERALL_STATUS" == "PASS" ] && echo -e "${GREEN}PROCEED${NC}" || echo -e "${RED}ROLLBACK${NC}")"
    echo -e "${BLUE}=========================================${NC}"
}

# Función principal
main() {
    echo -e "${BLUE}=========================================${NC}"
    echo -e "${BLUE}=== ANÁLISIS DE DESPLIEGUE CANARY ===${NC}"
    echo -e "${BLUE}=========================================${NC}"
    
    # Validar que podamos conectar con Prometheus
    validate_prometheus
    
    # Ejecutar análisis
    analyze_error_rate
    analyze_latency
    check_circuit_breaker
    check_business_metrics
    
    # Generar reporte
    generate_report
    
    # Salir con código según estado
    if [ "$OVERALL_STATUS" == "PASS" ]; then
        exit 0
    else
        exit 1
    fi
}

# Ejecutar script
main