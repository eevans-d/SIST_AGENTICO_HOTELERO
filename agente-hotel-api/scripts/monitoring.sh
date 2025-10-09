#!/bin/bash

# Script de monitoreo automático para Agente Hotelero IA System
# Monitorea la salud del sistema y genera alertas automáticas

set -euo pipefail

# Configuración
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/agente-hotel/monitoring.log"
ALERT_LOG="/var/log/agente-hotel/alerts.log"
CONFIG_FILE="$PROJECT_ROOT/.env.production"
PROMETHEUS_URL="http://localhost:9090"
GRAFANA_URL="http://localhost:3000"
API_URL="http://localhost:8000"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Función de logging
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        "ALERT")
            echo -e "${RED}[ALERT]${NC} $message"
            echo "[$timestamp] [ALERT] $message" >> "$ALERT_LOG"
            ;;
    esac
    
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Función para enviar alertas
send_alert() {
    local severity=$1
    local title=$2
    local message=$3
    
    log "ALERT" "$title: $message"
    
    # Aquí se pueden agregar integraciones con sistemas de alertas
    # Ejemplo: Slack, Discord, Email, PagerDuty, etc.
    
    # Ejemplo de webhook a Slack (comentado)
    # if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
    #     curl -X POST -H 'Content-type: application/json' \
    #         --data "{\"text\":\"🚨 [$severity] $title\n$message\"}" \
    #         "$SLACK_WEBHOOK_URL"
    # fi
}

# Verificar salud de servicios principales
check_service_health() {
    local service_name=$1
    local health_url=$2
    local timeout=${3:-10}
    
    if curl -s -f --max-time "$timeout" "$health_url" > /dev/null; then
        log "INFO" "$service_name: ✓ Saludable"
        return 0
    else
        log "ERROR" "$service_name: ✗ No responde"
        send_alert "HIGH" "Servicio No Disponible" "$service_name no está respondiendo en $health_url"
        return 1
    fi
}

# Verificar métricas de performance
check_performance_metrics() {
    log "INFO" "Verificando métricas de performance..."
    
    # Verificar latencia de API
    local api_latency=$(curl -s -w "%{time_total}" -o /dev/null "$API_URL/health/ready" || echo "999")
    local api_latency_ms=$(echo "$api_latency * 1000" | bc -l | cut -d. -f1)
    
    if [ "$api_latency_ms" -gt 2000 ]; then
        send_alert "MEDIUM" "Alta Latencia de API" "Latencia actual: ${api_latency_ms}ms (umbral: 2000ms)"
    fi
    
    # Verificar uso de memoria de contenedores
    if command -v docker &> /dev/null; then
        local containers=("agente-hotel-api-prod" "postgres-agente-prod" "redis-agente-prod")
        
        for container in "${containers[@]}"; do
            if docker ps | grep -q "$container"; then
                local memory_usage=$(docker stats --no-stream --format "{{.MemPerc}}" "$container" 2>/dev/null | sed 's/%//' || echo "0")
                
                if (( $(echo "$memory_usage > 85" | bc -l) )); then
                    send_alert "MEDIUM" "Alto Uso de Memoria" "Contenedor $container: ${memory_usage}% (umbral: 85%)"
                fi
            fi
        done
    fi
    
    log "INFO" "Verificación de performance completada"
}

# Verificar métricas de negocio
check_business_metrics() {
    log "INFO" "Verificando métricas de negocio..."
    
    # Verificar rate de mensajes procesados
    local messages_query='rate(whatsapp_messages_total[5m])'
    local messages_rate=$(curl -s "$PROMETHEUS_URL/api/v1/query?query=$messages_query" | \
        jq -r '.data.result[0].value[1]' 2>/dev/null || echo "0")
    
    if (( $(echo "$messages_rate < 0.1" | bc -l) )); then
        send_alert "LOW" "Baja Actividad de Mensajes" "Rate actual: $messages_rate msg/s"
    fi
    
    # Verificar errores de PMS
    local pms_errors_query='rate(pms_errors_total[5m])'
    local pms_error_rate=$(curl -s "$PROMETHEUS_URL/api/v1/query?query=$pms_errors_query" | \
        jq -r '.data.result[0].value[1]' 2>/dev/null || echo "0")
    
    if (( $(echo "$pms_error_rate > 0.05" | bc -l) )); then
        send_alert "HIGH" "Errores en PMS" "Rate de errores: $pms_error_rate err/s"
    fi
    
    # Verificar disponibilidad de habitaciones
    local availability_response=$(curl -s "$API_URL/api/v1/availability" || echo '{"available_rooms": 0}')
    local available_rooms=$(echo "$availability_response" | jq -r '.available_rooms' 2>/dev/null || echo "0")
    
    if [ "$available_rooms" -eq 0 ]; then
        send_alert "MEDIUM" "Sin Habitaciones Disponibles" "El hotel está completamente ocupado"
    fi
    
    log "INFO" "Verificación de métricas de negocio completada"
}

# Verificar integridad de la base de datos
check_database_integrity() {
    log "INFO" "Verificando integridad de base de datos..."
    
    # Verificar conexión a PostgreSQL
    if docker exec postgres-agente-prod pg_isready -U agente_user -d agente_db > /dev/null 2>&1; then
        log "INFO" "PostgreSQL: ✓ Conexión OK"
        
        # Verificar tamaño de base de datos
        local db_size=$(docker exec postgres-agente-prod psql -U agente_user -d agente_db -t -c \
            "SELECT pg_size_pretty(pg_database_size('agente_db'));" 2>/dev/null | tr -d ' ')
        
        log "INFO" "Tamaño de base de datos: $db_size"
        
        # Verificar conexiones activas
        local active_connections=$(docker exec postgres-agente-prod psql -U agente_user -d agente_db -t -c \
            "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';" 2>/dev/null | tr -d ' ')
        
        if [ "$active_connections" -gt 50 ]; then
            send_alert "MEDIUM" "Muchas Conexiones Activas" "Conexiones activas: $active_connections (umbral: 50)"
        fi
    else
        send_alert "CRITICAL" "Base de Datos No Disponible" "PostgreSQL no está respondiendo"
    fi
    
    # Verificar conexión a Redis
    if docker exec redis-agente-prod redis-cli ping > /dev/null 2>&1; then
        log "INFO" "Redis: ✓ Conexión OK"
        
        # Verificar uso de memoria Redis
        local redis_memory=$(docker exec redis-agente-prod redis-cli info memory | \
            grep used_memory_human | cut -d: -f2 | tr -d '\r')
        
        log "INFO" "Uso de memoria Redis: $redis_memory"
    else
        send_alert "CRITICAL" "Cache No Disponible" "Redis no está respondiendo"
    fi
    
    log "INFO" "Verificación de integridad de base de datos completada"
}

# Verificar seguridad
check_security() {
    log "INFO" "Verificando aspectos de seguridad..."
    
    # Verificar certificados SSL
    local cert_expiry=$(openssl x509 -in /etc/ssl/agente-hotel/server.crt -noout -enddate 2>/dev/null | \
        cut -d= -f2 || echo "")
    
    if [ -n "$cert_expiry" ]; then
        local expiry_timestamp=$(date -d "$cert_expiry" +%s)
        local current_timestamp=$(date +%s)
        local days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
        
        if [ "$days_until_expiry" -lt 30 ]; then
            send_alert "HIGH" "Certificado SSL Próximo a Expirar" "Expira en $days_until_expiry días"
        fi
    fi
    
    # Verificar logs de seguridad
    local failed_logins=$(grep -c "authentication failed" /var/log/agente-hotel/*.log 2>/dev/null || echo "0")
    
    if [ "$failed_logins" -gt 10 ]; then
        send_alert "MEDIUM" "Múltiples Fallos de Autenticación" "Fallos en las últimas horas: $failed_logins"
    fi
    
    log "INFO" "Verificación de seguridad completada"
}

# Verificar almacenamiento
check_storage() {
    log "INFO" "Verificando almacenamiento..."
    
    # Verificar espacio en disco
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [ "$disk_usage" -gt 85 ]; then
        send_alert "HIGH" "Poco Espacio en Disco" "Uso actual: ${disk_usage}% (umbral: 85%)"
    fi
    
    # Verificar tamaño de logs
    local log_size=$(du -sh /var/log/agente-hotel 2>/dev/null | cut -f1 || echo "0K")
    
    log "INFO" "Tamaño de logs: $log_size"
    
    # Limpiar logs antiguos si es necesario
    find /var/log/agente-hotel -name "*.log" -mtime +30 -delete 2>/dev/null || true
    
    log "INFO" "Verificación de almacenamiento completada"
}

# Generar reporte de estado
generate_status_report() {
    local report_file="/var/log/agente-hotel/status_$(date +%Y%m%d_%H%M).json"
    
    log "INFO" "Generando reporte de estado..."
    
    cat > "$report_file" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "system_status": {
    "api_health": "$(check_service_health "API" "$API_URL/health/ready" 5 && echo "healthy" || echo "unhealthy")",
    "prometheus_health": "$(check_service_health "Prometheus" "$PROMETHEUS_URL/-/healthy" 5 && echo "healthy" || echo "unhealthy")",
    "grafana_health": "$(check_service_health "Grafana" "$GRAFANA_URL/api/health" 5 && echo "healthy" || echo "unhealthy")"
  },
  "metrics": {
    "disk_usage": "$(df / | tail -1 | awk '{print $5}')",
    "memory_usage": "$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')",
    "cpu_load": "$(uptime | awk -F'load average:' '{ print $2 }' | cut -d, -f1 | xargs)"
  },
  "services": {
    "containers_running": $(docker ps | wc -l),
    "database_connections": "$(docker exec postgres-agente-prod psql -U agente_user -d agente_db -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | tr -d ' ' || echo "0")"
  }
}
EOF
    
    log "INFO" "Reporte generado: $report_file"
}

# Función principal de monitoreo
main_monitoring() {
    log "INFO" "=== Iniciando ciclo de monitoreo ==="
    
    # Crear directorios de logs si no existen
    mkdir -p "$(dirname "$LOG_FILE")"
    mkdir -p "$(dirname "$ALERT_LOG")"
    
    # Verificaciones principales
    check_service_health "API Principal" "$API_URL/health/ready"
    check_service_health "Prometheus" "$PROMETHEUS_URL/-/healthy"
    check_service_health "Grafana" "$GRAFANA_URL/api/health"
    
    # Verificaciones de performance y negocio
    check_performance_metrics
    check_business_metrics
    
    # Verificaciones de infraestructura
    check_database_integrity
    check_security
    check_storage
    
    # Generar reporte
    generate_status_report
    
    log "INFO" "=== Ciclo de monitoreo completado ==="
}

# Función para monitoreo continuo
continuous_monitoring() {
    local interval=${1:-300}  # 5 minutos por defecto
    
    log "INFO" "Iniciando monitoreo continuo (intervalo: ${interval}s)"
    
    while true; do
        main_monitoring
        sleep "$interval"
    done
}

# Manejo de argumentos
case "${1:-single}" in
    "single")
        main_monitoring
        ;;
    "continuous")
        continuous_monitoring "${2:-300}"
        ;;
    "quick")
        check_service_health "API Principal" "$API_URL/health/ready"
        check_service_health "Prometheus" "$PROMETHEUS_URL/-/healthy"
        check_service_health "Grafana" "$GRAFANA_URL/api/health"
        ;;
    "report")
        generate_status_report
        ;;
    *)
        echo "Uso: $0 [single|continuous|quick|report] [intervalo]"
        echo "  single      - Ejecuta un ciclo de monitoreo"
        echo "  continuous  - Monitoreo continuo con intervalo especificado"
        echo "  quick       - Verificación rápida de servicios principales"
        echo "  report      - Genera solo el reporte de estado"
        exit 1
        ;;
esac