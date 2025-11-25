#!/bin/bash
# Chaos Engineering Script - Redis Cache Failure
# Simula fallos en Redis para probar degradación graceful

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../guardrails.conf" 2>/dev/null || true

# Configuración
EXPERIMENT_DURATION=${CHAOS_EXPERIMENT_DURATION:-90}
REDIS_CONTAINER=${REDIS_CONTAINER:-agente_redis}
MONITORING_INTERVAL=3
LOG_FILE="/tmp/chaos-redis-experiment-$(date +%s).log"

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
    log "INFO" "${BLUE}🔍 Checking Redis chaos prerequisites...${NC}"
    
    # Verificar contenedor Redis existe
    if ! docker ps -a --format "table {{.Names}}" | grep -q "^${REDIS_CONTAINER}$"; then
        log "ERROR" "Redis container '$REDIS_CONTAINER' not found"
        exit 1
    fi
    
    # Verificar aplicación funcionando
    if ! curl -f http://localhost:8000/health/live >/dev/null 2>&1; then
        log "ERROR" "Application not responding"
        exit 1
    fi
    
    log "INFO" "${GREEN}✅ Prerequisites met${NC}"
}

start_cache_monitoring() {
    log "INFO" "${BLUE}📊 Starting cache performance monitoring...${NC}"
    
    monitor_cache_performance() {
        while true; do
            local timestamp=$(date -Iseconds)
            local app_status="UNKNOWN"
            local ready_status="UNKNOWN"
            local redis_status="UNKNOWN"
            local response_time="0"
            
            # Medir tiempo de respuesta de health check
            local start_time=$(date +%s%N)
            if curl -f http://localhost:8000/health/live >/dev/null 2>&1; then
                local end_time=$(date +%s%N)
                response_time=$(( (end_time - start_time) / 1000000 )) # convertir a ms
                app_status="OK"
            else
                app_status="FAIL"
            fi
            
            # Readiness (incluye dependencias como Redis)
            if curl -f http://localhost:8000/health/ready >/dev/null 2>&1; then
                ready_status="OK"
            else
                ready_status="FAIL"
            fi
            
            # Estado directo de Redis
            if docker exec "$REDIS_CONTAINER" redis-cli ping >/dev/null 2>&1; then
                redis_status="OK"
            else
                redis_status="FAIL"
            fi
            
            echo "$timestamp,app:$app_status,ready:$ready_status,redis:$redis_status,response_ms:$response_time" >> "${LOG_FILE}.metrics"
            sleep $MONITORING_INTERVAL
        done
    }
    
    monitor_cache_performance &
    MONITOR_PID=$!
    log "INFO" "Cache monitoring started (PID: $MONITOR_PID)"
}

simulate_redis_failure() {
    log "INFO" "${YELLOW}🌪️ Starting Redis Cache Chaos Experiment${NC}"
    log "INFO" "Duration: ${EXPERIMENT_DURATION}s"
    log "INFO" "Target: $REDIS_CONTAINER"
    
    # Baseline
    log "INFO" "${BLUE}📈 Recording baseline cache performance...${NC}"
    sleep 10
    
    # Simular diferentes tipos de fallos Redis
    local failure_scenarios=("stop" "network" "memory")
    local selected_scenario=${failure_scenarios[$((RANDOM % ${#failure_scenarios[@]}))]}
    
    case $selected_scenario in
        "stop")
            log "INFO" "${RED}💥 CHAOS: Stopping Redis container completely${NC}"
            docker stop "$REDIS_CONTAINER"
            ;;
        "network")
            log "INFO" "${RED}💥 CHAOS: Blocking Redis network traffic${NC}"
            # Simular problemas de red bloqueando puerto Redis
            docker exec "$REDIS_CONTAINER" sh -c "iptables -A INPUT -p tcp --dport 6379 -j DROP" 2>/dev/null || true
            ;;
        "memory")
            log "INFO" "${RED}💥 CHAOS: Inducing Redis memory pressure${NC}"
            # Llenar Redis con datos para simular memory pressure
            docker exec "$REDIS_CONTAINER" redis-cli flushall >/dev/null 2>&1 || true
            for i in {1..1000}; do
                docker exec "$REDIS_CONTAINER" redis-cli set "chaos_key_$i" "$(head -c 1024 /dev/zero | tr '\0' 'A')" >/dev/null 2>&1 || break
            done
            ;;
    esac
    
    local chaos_start=$(date +%s)
    log "INFO" "Redis chaos ($selected_scenario) started at $(date -Iseconds)"
    
    # Observar degradación
    log "INFO" "${YELLOW}⏳ Observing cache degradation for $((EXPERIMENT_DURATION / 3))s...${NC}"
    sleep $((EXPERIMENT_DURATION / 3))
    
    # Evaluar comportamiento de la aplicación
    log "INFO" "${BLUE}🔍 Testing application behavior during Redis outage...${NC}"
    
    local consecutive_failures=0
    for i in {1..10}; do
        if curl -f http://localhost:8000/health/live >/dev/null 2>&1; then
            log "INFO" "Health check $i: ✅ OK (graceful degradation)"
            consecutive_failures=0
        else
            log "WARN" "Health check $i: ❌ FAIL"
            ((consecutive_failures++))
        fi
        sleep 2
    done
    
    if [[ $consecutive_failures -gt 5 ]]; then
        log "ERROR" "Application appears to be failing hard without graceful degradation"
    else
        log "INFO" "${GREEN}✅ Application showing graceful degradation${NC}"
    fi
    
    # Mantener chaos por más tiempo
    sleep $((EXPERIMENT_DURATION / 3))
    
    # Recuperación
    log "INFO" "${GREEN}🔄 RECOVERY: Restoring Redis service${NC}"
    case $selected_scenario in
        "stop")
            docker start "$REDIS_CONTAINER"
            ;;
        "network")
            docker exec "$REDIS_CONTAINER" sh -c "iptables -F" 2>/dev/null || true
            ;;
        "memory")
            docker exec "$REDIS_CONTAINER" redis-cli flushall >/dev/null 2>&1 || true
            ;;
    esac
    
    # Esperar recuperación
    local recovery_start=$(date +%s)
    local max_wait=30
    local wait_count=0
    
    while ! docker exec "$REDIS_CONTAINER" redis-cli ping >/dev/null 2>&1; do
        if [[ $wait_count -ge $max_wait ]]; then
            log "ERROR" "Redis failed to recover within ${max_wait}s"
            break
        fi
        sleep 1
        ((wait_count++))
    done
    
    local recovery_end=$(date +%s)
    local recovery_time=$((recovery_end - recovery_start))
    log "INFO" "${GREEN}✅ Redis recovered in ${recovery_time}s${NC}"
    
    # Observar recuperación del rendimiento
    log "INFO" "${BLUE}📊 Observing cache performance recovery...${NC}"
    sleep $((EXPERIMENT_DURATION / 3))
    
    local chaos_end=$(date +%s)
    local total_experiment_time=$((chaos_end - chaos_start))
    log "INFO" "Total experiment duration: ${total_experiment_time}s"
}

generate_cache_report() {
    log "INFO" "${BLUE}📋 Generating Redis chaos experiment report...${NC}"
    
    local report_file="${LOG_FILE}.report"
    
    cat > "$report_file" << EOF
# Redis Cache Chaos Experiment Report
Generated: $(date -Iseconds)

## Experiment Configuration
- Duration: ${EXPERIMENT_DURATION}s
- Target: $REDIS_CONTAINER
- Log File: $LOG_FILE
- Metrics File: ${LOG_FILE}.metrics

## Performance Analysis
EOF
    
    if [[ -f "${LOG_FILE}.metrics" ]]; then
        # Analizar métricas de rendimiento
        local avg_response_baseline=$(head -20 "${LOG_FILE}.metrics" | grep -o 'response_ms:[0-9]*' | cut -d: -f2 | awk '{sum+=$1} END {print sum/NR}' 2>/dev/null || echo "0")
        local avg_response_chaos=$(tail -20 "${LOG_FILE}.metrics" | grep -o 'response_ms:[0-9]*' | cut -d: -f2 | awk '{sum+=$1} END {print sum/NR}' 2>/dev/null || echo "0")
        
        local app_failures=$(grep -c "app:FAIL" "${LOG_FILE}.metrics" || echo "0")
        local ready_failures=$(grep -c "ready:FAIL" "${LOG_FILE}.metrics" || echo "0")
        
        echo "- Baseline avg response time: ${avg_response_baseline}ms" >> "$report_file"
        echo "- Chaos avg response time: ${avg_response_chaos}ms" >> "$report_file"
        echo "- Application failures: $app_failures" >> "$report_file"
        echo "- Readiness failures: $ready_failures" >> "$report_file"
        
        echo "" >> "$report_file"
        echo "## Latest Metrics Sample" >> "$report_file"
        echo '```' >> "$report_file"
        tail -10 "${LOG_FILE}.metrics" >> "$report_file"
        echo '```' >> "$report_file"
    fi
    
    echo "" >> "$report_file"
    echo "## Resilience Assessment" >> "$report_file"
    echo "1. Cache-aside pattern effectiveness" >> "$report_file"
    echo "2. Circuit breaker behavior during cache outage" >> "$report_file"
    echo "3. Performance degradation graceful vs hard failure" >> "$report_file"
    echo "4. Recovery time and cache warming behavior" >> "$report_file"
    
    log "INFO" "${GREEN}📄 Cache chaos report generated: $report_file${NC}"
}

cleanup() {
    log "INFO" "${BLUE}🧹 Redis chaos cleanup...${NC}"
    
    if [[ -n "${MONITOR_PID:-}" ]]; then
        kill $MONITOR_PID 2>/dev/null || true
    fi
    
    # Asegurar que Redis esté funcionando
    if ! docker ps --format "table {{.Names}}" | grep -q "^${REDIS_CONTAINER}$"; then
        log "WARN" "Restarting Redis container as part of cleanup"
        docker start "$REDIS_CONTAINER" || true
    fi
    
    # Limpiar reglas iptables si quedaron
    docker exec "$REDIS_CONTAINER" sh -c "iptables -F" 2>/dev/null || true
    # Limpiar datos de chaos
    docker exec "$REDIS_CONTAINER" redis-cli flushall >/dev/null 2>&1 || true
}

main() {
    log "INFO" "${BLUE}🌪️ Redis Cache Chaos Engineering Experiment${NC}"
    
    trap cleanup EXIT
    
    check_prerequisites
    start_cache_monitoring
    simulate_redis_failure
    generate_cache_report
    
    log "INFO" "${GREEN}✅ Redis chaos experiment completed${NC}"
    log "INFO" "Logs: $LOG_FILE"
    log "INFO" "Metrics: ${LOG_FILE}.metrics"
    log "INFO" "Report: ${LOG_FILE}.report"
}

if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    cat <<EOF
Redis Cache Chaos Engineering Experiment

Simulates Redis cache failures to test graceful degradation.

Usage: $0 [options]

Environment Variables:
  CHAOS_EXPERIMENT_DURATION   Duration in seconds (default: 90)
  REDIS_CONTAINER            Redis container name (default: agente_redis)

Types of failures tested:
- Complete Redis container stop
- Network partition simulation  
- Memory pressure induction

IMPORTANT: Only run against development/testing environments!
EOF
    exit 0
fi

main "$@"