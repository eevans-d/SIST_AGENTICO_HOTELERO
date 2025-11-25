#!/usr/bin/env bash
#
# canary-analysis.sh - Script para analizar despliegues canary
#
# Este script verifica el rendimiento de un despliegue canary comparándolo
# con la versión base, utilizando métricas de Prometheus para tomar decisiones
# sobre la promoción o rollback del despliegue canary.
#
# Uso:
#   ./canary-analysis.sh [--threshold-latency valor] [--threshold-error valor] [--period minutos]
#
# Ejemplos:
#   ./canary-analysis.sh
#   ./canary-analysis.sh --threshold-latency 1.2 --threshold-error 0.03 --period 30
#

set -eo pipefail

# Colores para salida
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # Sin Color

# Valores predeterminados
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
THRESHOLD_LATENCY="${THRESHOLD_LATENCY:-1.2}"  # 20% de incremento en latencia
THRESHOLD_ERROR="${THRESHOLD_ERROR:-0.02}"      # 2% de incremento en errores
ANALYSIS_PERIOD="${ANALYSIS_PERIOD:-15}"        # 15 minutos
REPORT_DIR="${REPORT_DIR:-.playbook}"
REPORT_FILE="${REPORT_FILE:-canary_diff_report.json}"

# Funciones de ayuda
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

check_dependencies() {
    local missing=0
    
    # Verificar curl
    if ! command -v curl &> /dev/null; then
        log_error "Falta 'curl'. Instálalo con 'apt-get install curl' o similar."
        missing=1
    fi
    
    # Verificar jq
    if ! command -v jq &> /dev/null; then
        log_error "Falta 'jq'. Instálalo con 'apt-get install jq' o similar."
        missing=1
    fi
    
    # Verificar bc
    if ! command -v bc &> /dev/null; then
        log_error "Falta 'bc'. Instálalo con 'apt-get install bc' o similar."
        missing=1
    fi
    
    if [ $missing -eq 1 ]; then
        exit 1
    fi
}

check_prometheus() {
    log_info "Verificando conexión con Prometheus en $PROMETHEUS_URL..."
    
    if ! curl -s "$PROMETHEUS_URL/api/v1/status/config" | jq -e '.status == "success"' &> /dev/null; then
        log_error "No se pudo conectar a Prometheus en $PROMETHEUS_URL"
        exit 1
    fi
    
    log_success "Conexión exitosa con Prometheus"
}

# Analizar argumentos
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --threshold-latency) THRESHOLD_LATENCY="$2"; shift ;;
        --threshold-error) THRESHOLD_ERROR="$2"; shift ;;
        --period) ANALYSIS_PERIOD="$2"; shift ;;
        --prometheus-url) PROMETHEUS_URL="$2"; shift ;;
        --help)
            echo "Uso: $0 [--threshold-latency valor] [--threshold-error valor] [--period minutos] [--prometheus-url url]"
            echo ""
            echo "Opciones:"
            echo "  --threshold-latency valor    Umbral de incremento en latencia (defecto: 1.2 = 20%)"
            echo "  --threshold-error valor      Umbral de incremento en tasa de errores (defecto: 0.02 = 2%)"
            echo "  --period minutos             Período de análisis en minutos (defecto: 15)"
            echo "  --prometheus-url url         URL de Prometheus (defecto: http://localhost:9090)"
            echo ""
            exit 0
            ;;
        *) log_error "Opción desconocida: $1"; exit 1 ;;
    esac
    shift
done

# Ejecutar verificaciones iniciales
check_dependencies
check_prometheus

# Crear directorio para reportes si no existe
mkdir -p "$REPORT_DIR"

log_info "Iniciando análisis de despliegue canary"
log_info "- Umbral de latencia: ${THRESHOLD_LATENCY}x"
log_info "- Umbral de errores: ${THRESHOLD_ERROR}"
log_info "- Período de análisis: ${ANALYSIS_PERIOD} minutos"

# Recolectar métricas base (versión estable)
log_info "Recolectando métricas de la versión base..."

# Latencia P95 base
BASE_LATENCY_P95=$(curl -s "$PROMETHEUS_URL/api/v1/query" --data-urlencode "query=histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{deployment=\"stable\"}[${ANALYSIS_PERIOD}m])) by (le))" | jq -r '.data.result[0].value[1]')
if [ -z "$BASE_LATENCY_P95" ] || [ "$BASE_LATENCY_P95" = "null" ]; then
    BASE_LATENCY_P95="0"
    log_warning "No se encontraron datos de latencia para la versión base. Usando 0 como valor predeterminado."
fi

# Tasa de errores base
BASE_ERROR_RATE=$(curl -s "$PROMETHEUS_URL/api/v1/query" --data-urlencode "query=sum(rate(http_requests_total{deployment=\"stable\", status=~\"5..\"}[${ANALYSIS_PERIOD}m]))/sum(rate(http_requests_total{deployment=\"stable\"}[${ANALYSIS_PERIOD}m]))" | jq -r '.data.result[0].value[1]')
if [ -z "$BASE_ERROR_RATE" ] || [ "$BASE_ERROR_RATE" = "null" ]; then
    BASE_ERROR_RATE="0"
    log_warning "No se encontraron datos de tasa de errores para la versión base. Usando 0 como valor predeterminado."
fi

# Recolectar métricas canary
log_info "Recolectando métricas de la versión canary..."

# Latencia P95 canary
CANARY_LATENCY_P95=$(curl -s "$PROMETHEUS_URL/api/v1/query" --data-urlencode "query=histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{deployment=\"canary\"}[${ANALYSIS_PERIOD}m])) by (le))" | jq -r '.data.result[0].value[1]')
if [ -z "$CANARY_LATENCY_P95" ] || [ "$CANARY_LATENCY_P95" = "null" ]; then
    CANARY_LATENCY_P95="0"
    log_warning "No se encontraron datos de latencia para la versión canary. Usando 0 como valor predeterminado."
fi

# Tasa de errores canary
CANARY_ERROR_RATE=$(curl -s "$PROMETHEUS_URL/api/v1/query" --data-urlencode "query=sum(rate(http_requests_total{deployment=\"canary\", status=~\"5..\"}[${ANALYSIS_PERIOD}m]))/sum(rate(http_requests_total{deployment=\"canary\"}[${ANALYSIS_PERIOD}m]))" | jq -r '.data.result[0].value[1]')
if [ -z "$CANARY_ERROR_RATE" ] || [ "$CANARY_ERROR_RATE" = "null" ]; then
    CANARY_ERROR_RATE="0"
    log_warning "No se encontraron datos de tasa de errores para la versión canary. Usando 0 como valor predeterminado."
fi

# Calcular diferencias
log_info "Calculando diferencias..."

if [ "$BASE_LATENCY_P95" = "0" ]; then
    LATENCY_RATIO=1
else
    LATENCY_RATIO=$(echo "scale=3; $CANARY_LATENCY_P95 / $BASE_LATENCY_P95" | bc)
fi

ERROR_DIFF=$(echo "scale=3; $CANARY_ERROR_RATE - $BASE_ERROR_RATE" | bc)

log_info "Métricas base:"
log_info "- Latencia P95: ${BASE_LATENCY_P95} segundos"
log_info "- Tasa de errores: ${BASE_ERROR_RATE}"

log_info "Métricas canary:"
log_info "- Latencia P95: ${CANARY_LATENCY_P95} segundos"
log_info "- Tasa de errores: ${CANARY_ERROR_RATE}"

log_info "Diferencias:"
log_info "- Ratio de latencia: ${LATENCY_RATIO}x"
log_info "- Diferencia de errores: ${ERROR_DIFF}"

# Evaluación de resultados
log_info "Evaluando resultados..."

LATENCY_STATUS="PASS"
ERROR_STATUS="PASS"
OVERALL_STATUS="PASS"
PROMOTION_RECOMMENDATION="PROCEED"
WARNINGS=[]

# Verificar latencia
if (( $(echo "$LATENCY_RATIO > $THRESHOLD_LATENCY" | bc -l) )); then
    LATENCY_STATUS="FAIL"
    OVERALL_STATUS="FAIL"
    PROMOTION_RECOMMENDATION="ROLLBACK"
    WARNINGS=$(echo "$WARNINGS" | jq -c '. + ["Latencia P95 canary excede el umbral"]')
elif (( $(echo "$LATENCY_RATIO > 1.1" | bc -l) )); then
    LATENCY_STATUS="WARNING"
    WARNINGS=$(echo "$WARNINGS" | jq -c '. + ["Latencia P95 canary muestra incremento significativo"]')
fi

# Verificar errores
if (( $(echo "$ERROR_DIFF > $THRESHOLD_ERROR" | bc -l) )); then
    ERROR_STATUS="FAIL"
    OVERALL_STATUS="FAIL"
    PROMOTION_RECOMMENDATION="ROLLBACK"
    WARNINGS=$(echo "$WARNINGS" | jq -c '. + ["Tasa de errores canary excede el umbral"]')
elif (( $(echo "$ERROR_DIFF > 0.01" | bc -l) )); then
    ERROR_STATUS="WARNING"
    WARNINGS=$(echo "$WARNINGS" | jq -c '. + ["Tasa de errores canary muestra incremento significativo"]')
fi

# Generar reporte
log_info "Generando reporte en ${REPORT_DIR}/${REPORT_FILE}..."

cat > "${REPORT_DIR}/${REPORT_FILE}" << EOF
{
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "analysis_period_minutes": ${ANALYSIS_PERIOD},
    "thresholds": {
        "latency_ratio": ${THRESHOLD_LATENCY},
        "error_difference": ${THRESHOLD_ERROR}
    },
    "base_metrics": {
        "latency_p95": ${BASE_LATENCY_P95},
        "error_rate": ${BASE_ERROR_RATE}
    },
    "canary_metrics": {
        "latency_p95": ${CANARY_LATENCY_P95},
        "error_rate": ${CANARY_ERROR_RATE}
    },
    "diff": {
        "latency_ratio": ${LATENCY_RATIO},
        "error_difference": ${ERROR_DIFF}
    },
    "results": {
        "latency_status": "${LATENCY_STATUS}",
        "error_status": "${ERROR_STATUS}",
        "overall_status": "${OVERALL_STATUS}",
        "promotion_recommendation": "${PROMOTION_RECOMMENDATION}",
        "warnings": ${WARNINGS}
    }
}
EOF

# Mostrar resultado final
if [ "$OVERALL_STATUS" = "PASS" ]; then
    log_success "Análisis canary exitoso - Se recomienda PROCEDER con el despliegue"
    exit 0
elif [ "$OVERALL_STATUS" = "FAIL" ]; then
    log_error "Análisis canary fallido - Se recomienda ROLLBACK del despliegue"
    exit 1
else
    log_warning "Análisis canary con advertencias - Revisar métricas adicionales antes de proceder"
    exit 0
fi