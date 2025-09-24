#!/bin/bash
# Chaos Engineering Script - Database Connection Failures
# Simula fallos en la base de datos PostgreSQL

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../guardrails.conf" 2>/dev/null || true

# Configuración
EXPERIMENT_DURATION=${CHAOS_EXPERIMENT_DURATION:-60}  # segundos
DB_CONTAINER=${DB_CONTAINER:-agente_db}
MONITORING_INTERVAL=5
LOG_FILE="/tmp/chaos-db-experiment-$(date +%s).log"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date -Iseconds)
    echo -e "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

check_prerequisites() {
    log "INFO" "${BLUE}🔍 Checking prerequisites...${NC}"
    
    # Verificar Docker
    if ! command -v docker >/dev/null 2>&1; then
        log "ERROR" "Docker not found"
        exit 1
    fi
    
    # Verificar contenedor existe
    if ! docker ps -a --format "table {{.Names}}" | grep -q "^${DB_CONTAINER}$"; then
        log "ERROR" "Database container '$DB_CONTAINER' not found"
        exit 1
    fi
    
    # Verificar que la aplicación esté funcionando
    if ! curl -f http://localhost:8000/health/live >/dev/null 2>&1; then
        log "ERROR" "Application not responding - cannot run chaos experiment"
        exit 1
    fi
    
    log "INFO" "${GREEN}✅ Prerequisites met${NC}"
}

start_monitoring() {
    log "INFO" "${BLUE}📊 Starting monitoring...${NC}"
    
    # Función de monitoreo en background
    monitor_system() {
        while true; do
            local timestamp=$(date -Iseconds)
            local health_status="UNKNOWN"
            local ready_status="UNKNOWN"
            local db_status="UNKNOWN"
            
            # Health check
            if curl -f http://localhost:8000/health/live >/dev/null 2>&1; then
                health_status="OK"
            else
                health_status="FAIL"
            fi
            
            # Readiness check  
            if curl -f http://localhost:8000/health/ready >/dev/null 2>&1; then
                ready_status="OK"
            else
                ready_status="FAIL"
            fi
            
            # Database status
            if docker exec "$DB_CONTAINER" pg_isready >/dev/null 2>&1; then
                db_status="OK"
            else
                db_status="FAIL"
            fi
            
            echo "$timestamp,health:$health_status,ready:$ready_status,db:$db_status" >> "${LOG_FILE}.metrics"
            sleep $MONITORING_INTERVAL
        done
    }
    
    monitor_system &
    MONITOR_PID=$!
    log "INFO" "Monitoring started (PID: $MONITOR_PID)"
}

stop_monitoring() {
    if [[ -n "${MONITOR_PID:-}" ]]; then
        kill $MONITOR_PID 2>/dev/null || true
        log "INFO" "Monitoring stopped"
    fi
}

run_db_chaos_experiment() {
    log "INFO" "${YELLOW}🌪️ Starting Database Chaos Experiment${NC}"
    log "INFO" "Duration: ${EXPERIMENT_DURATION}s"
    log "INFO" "Target: $DB_CONTAINER"
    
    # Baseline metrics
    log "INFO" "${BLUE}📈 Recording baseline metrics...${NC}"
    sleep 5
    
    # Simular fallo de DB - detener contenedor
    log "INFO" "${RED}💥 CHAOS: Stopping database container${NC}"
    docker stop "$DB_CONTAINER"
    
    local chaos_start=$(date +%s)
    log "INFO" "Database stopped at $(date -Iseconds)"
    
    # Esperar y observar comportamiento
    log "INFO" "${YELLOW}⏳ Observing system behavior during outage...${NC}"
    sleep $((EXPERIMENT_DURATION / 2))
    
    # Restaurar DB
    log "INFO" "${GREEN}🔄 RECOVERY: Restarting database container${NC}"
    docker start "$DB_CONTAINER"
    
    # Esperar a que DB esté listo
    log "INFO" "Waiting for database to be ready..."
    local recovery_start=$(date +%s)
    local max_wait=30
    local wait_count=0
    
    while ! docker exec "$DB_CONTAINER" pg_isready >/dev/null 2>&1; do
        if [[ $wait_count -ge $max_wait ]]; then
            log "ERROR" "Database failed to recover within ${max_wait}s"
            break
        fi
        sleep 1
        ((wait_count++))
    done
    
    local recovery_end=$(date +%s)
    local recovery_time=$((recovery_end - recovery_start))
    log "INFO" "${GREEN}✅ Database recovered in ${recovery_time}s${NC}"
    
    # Observar recuperación del sistema
    log "INFO" "${BLUE}📊 Observing system recovery...${NC}"
    sleep $((EXPERIMENT_DURATION / 2))
    
    local chaos_end=$(date +%s)
    local total_experiment_time=$((chaos_end - chaos_start))
    log "INFO" "Total experiment duration: ${total_experiment_time}s"
}

generate_report() {
    log "INFO" "${BLUE}📋 Generating experiment report...${NC}"
    
    local report_file="${LOG_FILE}.report"
    
    cat > "$report_file" << EOF
# Database Chaos Experiment Report
Generated: $(date -Iseconds)

## Experiment Configuration
- Duration: ${EXPERIMENT_DURATION}s
- Target: $DB_CONTAINER
- Log File: $LOG_FILE
- Metrics File: ${LOG_FILE}.metrics

## Summary
EOF
    
    if [[ -f "${LOG_FILE}.metrics" ]]; then
        echo "## Health Status During Experiment" >> "$report_file"
        echo '```' >> "$report_file"
        tail -20 "${LOG_FILE}.metrics" >> "$report_file"
        echo '```' >> "$report_file"
        
        # Count failures
        local health_failures=$(grep -c "health:FAIL" "${LOG_FILE}.metrics" || echo "0")
        local ready_failures=$(grep -c "ready:FAIL" "${LOG_FILE}.metrics" || echo "0")
        
        echo "" >> "$report_file"
        echo "- Health check failures: $health_failures" >> "$report_file"
        echo "- Readiness check failures: $ready_failures" >> "$report_file"
    fi
    
    echo "" >> "$report_file"
    echo "## Recommendations" >> "$report_file"
    echo "1. Review circuit breaker behavior during DB outage" >> "$report_file"
    echo "2. Validate error responses are graceful" >> "$report_file"
    echo "3. Check recovery time meets SLO targets" >> "$report_file"
    echo "4. Monitor for connection pool exhaustion" >> "$report_file"
    
    log "INFO" "${GREEN}📄 Report generated: $report_file${NC}"
}

cleanup() {
    log "INFO" "${BLUE}🧹 Cleaning up...${NC}"
    stop_monitoring
    
    # Asegurar que la DB esté funcionando
    if ! docker ps --format "table {{.Names}}" | grep -q "^${DB_CONTAINER}$"; then
        log "WARN" "Restarting database container as part of cleanup"
        docker start "$DB_CONTAINER" || true
    fi
}

main() {
    log "INFO" "${BLUE}🌪️ Database Chaos Engineering Experiment${NC}"
    
    # Setup cleanup trap
    trap cleanup EXIT
    
    check_prerequisites
    start_monitoring
    run_db_chaos_experiment
    generate_report
    
    log "INFO" "${GREEN}✅ Chaos experiment completed successfully${NC}"
    log "INFO" "Check logs: $LOG_FILE"
    log "INFO" "Check metrics: ${LOG_FILE}.metrics"
    log "INFO" "Check report: ${LOG_FILE}.report"
}

# Help
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    cat <<EOF
Database Chaos Engineering Experiment

This script simulates database failures to test system resilience.

Usage: $0 [options]

Environment Variables:  
  CHAOS_EXPERIMENT_DURATION   Experiment duration in seconds (default: 60)
  DB_CONTAINER               Database container name (default: agente_db)

Example:
  CHAOS_EXPERIMENT_DURATION=120 $0

IMPORTANT: Only run this against development/testing environments!
EOF
    exit 0
fi

main "$@"