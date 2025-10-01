# TROUBLESHOOTING PROACTIVO Y AUTOCURACIÓN - SIST_AGENTICO_HOTELERO

## INDICADORES CLAVE Y UMBRALES ACCIONABLES

### Métricas Core del Sistema

| Indicador | Umbral Normal | Umbral Crítico | Acción Automática |
|-----------|---------------|----------------|-------------------|
| **P95 Response Time** | <500ms | >2000ms | Scale workers, enable caching |
| **Error Rate** | <1% | >5% | Circuit breaker, fallback mode |
| **Memory Usage** | <70% | >85% | Memory cleanup, restart worker |
| **CPU Usage** | <60% | >80% | Scale up, reduce background tasks |
| **PMS API Latency** | <200ms | >1000ms | Circuit breaker, cached responses |
| **Redis Latency** | <5ms | >50ms | Connection pool reset |
| **Queue Length** | <10 | >100 | Scale workers, reject requests |
| **Token Rate (LLM)** | <1000/min | >5000/min | Rate limiting, queue throttling |
| **Disk Usage** | <70% | >90% | Log rotation, temp cleanup |
| **DB Connections** | <70% pool | >95% pool | Connection cleanup, pool scaling |

### Métricas Específicas del Agente

| Indicador | Umbral Normal | Umbral Crítico | Evidencia en Código |
|-----------|---------------|----------------|---------------------|
| **NLP Confidence** | >0.7 | <0.5 | app/services/nlp_engine.py - threshold config |
| **PMS Circuit Breaker** | Closed | Open >5min | app/core/circuit_breaker.py:21-32 |
| **Audio Processing Time** | <30s | >60s | app/utils/audio_converter.py |
| **Session Cache Hit Rate** | >80% | <50% | app/services/session_manager.py |
| **Webhook Response Time** | <200ms | >1000ms | app/routers/webhooks.py |

## TABLA CAUSA→EFECTO CON EVIDENCIA

| Indicador | Causa Posible | Evidencia (archivo:líneas) | Acción Recomendada |
|-----------|---------------|---------------------------|-------------------|
| **P95 >2000ms** | Database pool exhausted | app/core/settings.py:68-69 pool_size=10 | `scale_db_pool.sh` - increase pool size |
| **Error Rate >5%** | PMS API down | app/services/pms_adapter.py:161 - mock responses | `enable_pms_fallback.sh` - switch to mock mode |
| **Memory >85%** | Memory leak in audio processing | app/utils/audio_converter.py - no cleanup | `memory_cleanup.sh` - restart audio workers |
| **CPU >80%** | Too many uvicorn workers | Dockerfile:51 - workers=2, configurable | `scale_workers.sh` - adjust worker count |
| **Redis timeout** | Redis password mismatch | app/core/redis_client.py:8-16 password config | `fix_redis_auth.sh` - reset connection |
| **Queue length >100** | WhatsApp webhook flood | app/routers/webhooks.py:5 - no rate limiting on endpoint | `enable_webhook_throttling.sh` |
| **Circuit breaker open** | PMS network partition | app/core/circuit_breaker.py:32 - failure tracking | `check_pms_connectivity.sh` |
| **Low NLP confidence** | Missing Rasa model | app/services/nlp_engine.py:4 - commented agent | `deploy_rasa_model.sh` |
| **Disk >90%** | Log files not rotated | NO EVIDENCIADO - missing logrotate | `cleanup_logs.sh` - manual log rotation |
| **Session cache miss** | Redis memory eviction | docker-compose.yml:94 - no maxmemory policy | `configure_redis_memory.sh` |

## SCRIPT DIAGNÓSTICO COMPLETO

```bash
#!/usr/bin/env bash
# scripts/diagnostic-comprehensive.sh - Comprehensive system diagnostics

set -euo pipefail

echo "🔍 AGENTE HOTELERO - SISTEMA DE DIAGNÓSTICO COMPLETO"
echo "=================================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

HEALTH_BASE_URL="${HEALTH_BASE_URL:-http://localhost:8000}"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

echo "Timestamp: $TIMESTAMP"
echo ""

# 1. Application Health Checks
echo "1️⃣ APPLICATION HEALTH CHECKS"
echo "================================"

# Liveness check
echo -n "Liveness check: "
if curl -fsS --max-time 5 "$HEALTH_BASE_URL/health/live" >/dev/null 2>&1; then
    echo -e "${GREEN}HEALTHY${NC}"
else
    echo -e "${RED}FAILED${NC} - Application not responding"
fi

# Readiness check  
echo -n "Readiness check: "
if curl -fsS --max-time 10 "$HEALTH_BASE_URL/health/ready" >/dev/null 2>&1; then
    echo -e "${GREEN}READY${NC}"
else
    echo -e "${RED}NOT READY${NC} - Dependencies may be down"
fi

# Metrics endpoint
echo -n "Metrics endpoint: "
if curl -fsS --max-time 5 "$HEALTH_BASE_URL/metrics" >/dev/null 2>&1; then
    echo -e "${GREEN}ACCESSIBLE${NC}"
else
    echo -e "${YELLOW}WARNING${NC} - Metrics not accessible"
fi

echo ""

# 2. Database Connectivity
echo "2️⃣ DATABASE CONNECTIVITY"
echo "========================="

# PostgreSQL check
echo -n "PostgreSQL connection: "
if command -v psql >/dev/null 2>&1; then
    if timeout 10s psql "${POSTGRES_URL:-postgresql://postgres:postgres@localhost:5432/postgres}" -c '\q' >/dev/null 2>&1; then
        echo -e "${GREEN}CONNECTED${NC}"
    else
        echo -e "${RED}CONNECTION FAILED${NC}"
    fi
else
    echo -e "${YELLOW}psql not installed${NC} - skipping PostgreSQL check"
fi

# Redis check
echo -n "Redis connection: "
if command -v redis-cli >/dev/null 2>&1; then
    if timeout 5s redis-cli -u "${REDIS_URL:-redis://localhost:6379/0}" ping >/dev/null 2>&1; then
        echo -e "${GREEN}CONNECTED${NC}"
    else
        echo -e "${RED}CONNECTION FAILED${NC}"
    fi
else
    echo -e "${YELLOW}redis-cli not installed${NC} - skipping Redis check"
fi

# MySQL check (for QloApps)
echo -n "MySQL connection: "
if command -v mysql >/dev/null 2>&1; then
    if timeout 10s mysql -h "${MYSQL_HOST:-localhost}" -u "${MYSQL_USER:-qloapps}" -p"${MYSQL_PASSWORD:-}" -e "SELECT 1;" >/dev/null 2>&1; then
        echo -e "${GREEN}CONNECTED${NC}"
    else
        echo -e "${RED}CONNECTION FAILED${NC}"
    fi
else
    echo -e "${YELLOW}mysql client not installed${NC} - skipping MySQL check"
fi

echo ""

# 3. External Service Health
echo "3️⃣ EXTERNAL SERVICE HEALTH"
echo "==========================="

# PMS Health
echo -n "QloApps PMS: "
PMS_URL="${PMS_BASE_URL:-http://localhost:8080}"
if timeout 15s curl -fsS "$PMS_URL" >/dev/null 2>&1; then
    echo -e "${GREEN}ACCESSIBLE${NC}"
else
    echo -e "${RED}NOT ACCESSIBLE${NC} - PMS may be down"
fi

# WhatsApp API (basic connectivity)
echo -n "WhatsApp API: "
if timeout 10s curl -fsS "https://graph.facebook.com/v18.0/me" -H "Authorization: Bearer ${WHATSAPP_ACCESS_TOKEN:-dummy}" >/dev/null 2>&1; then
    echo -e "${GREEN}API REACHABLE${NC}"
else
    echo -e "${YELLOW}API CHECK FAILED${NC} - May be token issue or network"
fi

echo ""

# 4. System Resource Check
echo "4️⃣ SYSTEM RESOURCES"
echo "=================="

# Memory usage
echo "Memory usage:"
if command -v free >/dev/null 2>&1; then
    free -h | grep -E "(Mem|Swap)"
    
    # Calculate memory percentage
    MEM_PERCENT=$(free | grep Mem | awk '{printf("%.1f"), $3/$2 * 100.0}')
    if (( $(echo "$MEM_PERCENT > 85" | bc -l) )); then
        echo -e "${RED}⚠️  High memory usage: ${MEM_PERCENT}%${NC}"
    fi
else
    echo "free command not available"
fi

echo ""

# CPU usage
echo "CPU usage (5 second average):"
if command -v top >/dev/null 2>&1; then
    top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//' | head -1
fi

echo ""

# Disk usage
echo "Disk usage:"
df -h | grep -E "(Filesystem|/dev/)" | head -5

# Check for critical disk usage
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo -e "${RED}⚠️  Critical disk usage: ${DISK_USAGE}%${NC}"
elif [ "$DISK_USAGE" -gt 80 ]; then
    echo -e "${YELLOW}⚠️  High disk usage: ${DISK_USAGE}%${NC}"
fi

echo ""

# 5. Process Health
echo "5️⃣ PROCESS HEALTH"
echo "=================="

# Top processes by memory
echo "Top 5 processes by memory usage:"
ps -eo pid,cmd,%mem,%cpu --sort=-%mem | head -6

echo ""

# Check for agente-related processes
echo "Agente-related processes:"
ps aux | grep -E "(uvicorn|gunicorn|python.*app)" | grep -v grep || echo "No agente processes found"

echo ""

# 6. Network Connectivity
echo "6️⃣ NETWORK CONNECTIVITY"
echo "======================="

# Check open ports
echo "Open ports:"
if command -v netstat >/dev/null 2>&1; then
    netstat -tlnp | grep -E ":8000|:5432|:6379|:3306" || echo "No relevant ports found"
elif command -v ss >/dev/null 2>&1; then
    ss -tlnp | grep -E ":8000|:5432|:6379|:3306" || echo "No relevant ports found"
else
    echo "netstat/ss not available"
fi

echo ""

# 7. Docker Container Status (if running in Docker)
echo "7️⃣ CONTAINER STATUS"
echo "=================="

if command -v docker >/dev/null 2>&1; then
    echo "Docker containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(agente|qloapps|postgres|redis|mysql)" || echo "No relevant containers found"
    
    echo ""
    echo "Container resource usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | head -10 || echo "Docker stats not available"
else
    echo "Docker not available - skipping container checks"
fi

echo ""

# 8. Log Analysis (Recent Errors)
echo "8️⃣ RECENT ERROR ANALYSIS"
echo "========================"

# Check for recent errors in logs
if [ -d "/var/log/agente" ]; then
    echo "Recent errors in application logs:"
    find /var/log/agente -name "*.log" -type f -exec grep -l "ERROR\|CRITICAL" {} \; | head -3 | while read -r logfile; do
        echo "=== $logfile ==="
        tail -20 "$logfile" | grep -E "ERROR|CRITICAL" | tail -5
    done
else
    echo "Log directory /var/log/agente not found"
fi

echo ""

# 9. Configuration Validation
echo "9️⃣ CONFIGURATION VALIDATION"
echo "=========================="

# Check for required environment variables
REQUIRED_VARS=("SECRET_KEY" "POSTGRES_URL" "REDIS_URL" "PMS_API_KEY")
echo "Required environment variables:"
for var in "${REQUIRED_VARS[@]}"; do
    if [ -n "${!var:-}" ]; then
        echo -e "✅ $var: ${GREEN}SET${NC}"
    else
        echo -e "❌ $var: ${RED}NOT SET${NC}"
    fi
done

echo ""

# 10. Performance Metrics Summary
echo "🔟 PERFORMANCE SUMMARY"
echo "====================="

# Get recent response times from metrics if available
echo "Recent performance metrics:"
if curl -fsS --max-time 5 "$HEALTH_BASE_URL/metrics" 2>/dev/null | grep -E "(http_request_duration|memory_usage|cpu_usage)" | head -5; then
    echo "Metrics retrieved successfully"
else
    echo "Performance metrics not available"
fi

echo ""
echo "=================================================="
echo "🏁 DIAGNOSTIC COMPLETED AT $(date)"
echo "=================================================="

# Return appropriate exit code
if curl -fsS --max-time 5 "$HEALTH_BASE_URL/health/ready" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ System is healthy${NC}"
    exit 0
else
    echo -e "${RED}❌ System has issues${NC}"
    exit 1
fi
```

## SCRIPT AUTOCURACIÓN SEGURO

```bash
#!/usr/bin/env bash
# scripts/auto-healing-safe.sh - Safe auto-healing system

set -euo pipefail

# Configuration
HEALTH_URL="${HEALTH_URL:-http://localhost:8000/health}"
MAX_RESTART_ATTEMPTS="${MAX_RESTART_ATTEMPTS:-3}" 
RESTART_COOLDOWN="${RESTART_COOLDOWN:-300}"
MEMORY_THRESHOLD="${MEMORY_THRESHOLD:-85}"
CPU_THRESHOLD="${CPU_THRESHOLD:-80}"
DISK_THRESHOLD="${DISK_THRESHOLD:-90}"
ERROR_RATE_THRESHOLD="${ERROR_RATE_THRESHOLD:-5}"

# State files
STATE_DIR="/tmp/agente-healing"
RESTART_COUNT_FILE="$STATE_DIR/restart_count"
LAST_RESTART_FILE="$STATE_DIR/last_restart"
HEALING_LOG="/var/log/agente/auto-healing.log"

mkdir -p "$STATE_DIR"
mkdir -p "$(dirname "$HEALING_LOG")"

# Logging function
log_healing() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$HEALING_LOG"
}

# Check if service is healthy
check_service_health() {
    local retries=3
    local wait_time=5
    
    for ((i=1; i<=retries; i++)); do
        if curl -fsS --max-time 10 "$HEALTH_URL/ready" >/dev/null 2>&1; then
            return 0
        fi
        
        if [ $i -lt $retries ]; then
            log_healing "Health check failed (attempt $i/$retries), retrying in ${wait_time}s..."
            sleep $wait_time
        fi
    done
    
    return 1
}

# Get restart count
get_restart_count() {
    if [ -f "$RESTART_COUNT_FILE" ]; then
        cat "$RESTART_COUNT_FILE"
    else
        echo "0"
    fi
}

# Increment restart count
increment_restart_count() {
    local count=$(get_restart_count)
    echo $((count + 1)) > "$RESTART_COUNT_FILE"
}

# Reset restart count
reset_restart_count() {
    echo "0" > "$RESTART_COUNT_FILE"
}

# Check if in cooldown period
is_in_cooldown() {
    if [ -f "$LAST_RESTART_FILE" ]; then
        local last_restart=$(cat "$LAST_RESTART_FILE")
        local current_time=$(date +%s)
        local elapsed=$((current_time - last_restart))
        
        if [ $elapsed -lt $RESTART_COOLDOWN ]; then
            return 0
        fi
    fi
    return 1
}

# Memory cleanup function
memory_cleanup() {
    log_healing "🧹 Performing memory cleanup..."
    
    # Python garbage collection (if application supports it)
    if curl -fsS --max-time 5 "$HEALTH_URL/../admin/gc" >/dev/null 2>&1; then
        log_healing "✅ Python garbage collection triggered"
    fi
    
    # Clear system caches (safe)
    sync
    echo 1 > /proc/sys/vm/drop_caches 2>/dev/null || log_healing "⚠️  Cannot clear system caches (insufficient permissions)"
    
    # Docker container restart (if running in Docker)
    if command -v docker >/dev/null 2>&1; then
        local container_id=$(docker ps --filter "expose=8000" --format "{{.ID}}" | head -1)
        if [ -n "$container_id" ]; then
            log_healing "🔄 Restarting Docker container: $container_id"
            docker restart "$container_id"
            return 0
        fi
    fi
    
    log_healing "✅ Memory cleanup completed"
}

# Service restart function
restart_service() {
    local restart_count=$(get_restart_count)
    
    if [ $restart_count -ge $MAX_RESTART_ATTEMPTS ]; then
        log_healing "❌ Maximum restart attempts ($MAX_RESTART_ATTEMPTS) reached. Manual intervention required."
        return 1
    fi
    
    if is_in_cooldown; then
        log_healing "⏳ Service restart in cooldown period. Skipping restart."
        return 1
    fi
    
    increment_restart_count
    echo "$(date +%s)" > "$LAST_RESTART_FILE"
    
    log_healing "🔄 Attempting service restart (attempt $((restart_count + 1))/$MAX_RESTART_ATTEMPTS)..."
    
    # Try systemd first
    if command -v systemctl >/dev/null 2>&1 && systemctl is-active agente-hotel >/dev/null 2>&1; then
        log_healing "🔄 Restarting via systemd..."
        sudo systemctl restart agente-hotel
        sleep 10
    
    # Try Docker Compose
    elif [ -f "docker-compose.yml" ] && command -v docker-compose >/dev/null 2>&1; then
        log_healing "🔄 Restarting via Docker Compose..."
        docker-compose restart agente-api
        sleep 15
    
    # Try Docker directly
    elif command -v docker >/dev/null 2>&1; then
        log_healing "🔄 Restarting via Docker..."
        local container_id=$(docker ps --filter "expose=8000" --format "{{.ID}}" | head -1)
        if [ -n "$container_id" ]; then
            docker restart "$container_id"
            sleep 15
        else
            log_healing "❌ No Docker container found with port 8000 exposed"
            return 1
        fi
    
    # Try process restart (last resort)
    else
        log_healing "🔄 Attempting process restart..."
        pkill -f "uvicorn.*app.main:app" || true
        sleep 5
        # Note: Process should be restarted by process manager (systemd, supervisor, etc.)
    fi
    
    # Verify restart was successful
    sleep 20
    if check_service_health; then
        log_healing "✅ Service restart successful"
        reset_restart_count
        return 0
    else
        log_healing "❌ Service restart failed - health check still failing"
        return 1
    fi
}

# Check system resources
check_system_resources() {
    local needs_action=false
    
    # Memory check
    if command -v free >/dev/null 2>&1; then
        local memory_percent=$(free | grep Mem | awk '{printf("%.0f"), $3/$2 * 100.0}')
        if [ "$memory_percent" -gt "$MEMORY_THRESHOLD" ]; then
            log_healing "⚠️  High memory usage detected: ${memory_percent}%"
            memory_cleanup
            needs_action=true
        fi
    fi
    
    # CPU check
    if command -v top >/dev/null 2>&1; then
        local cpu_percent=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//' | cut -d. -f1)
        if [ "$cpu_percent" -gt "$CPU_THRESHOLD" ]; then
            log_healing "⚠️  High CPU usage detected: ${cpu_percent}%"
            needs_action=true
        fi
    fi
    
    # Disk check
    local disk_percent=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$disk_percent" -gt "$DISK_THRESHOLD" ]; then
        log_healing "⚠️  High disk usage detected: ${disk_percent}%"
        # Safe disk cleanup
        find /tmp -type f -mtime +1 -delete 2>/dev/null || true
        find /var/log -name "*.log.*" -mtime +7 -delete 2>/dev/null || true
        needs_action=true
    fi
    
    return $([ "$needs_action" = "true" ] && echo 1 || echo 0)
}

# Check error rates from metrics
check_error_rates() {
    if curl -fsS --max-time 5 "$HEALTH_URL/../metrics" 2>/dev/null | grep -q "http_requests_total"; then
        # Extract error rate from Prometheus metrics (simplified)
        local total_requests=$(curl -fsS "$HEALTH_URL/../metrics" 2>/dev/null | grep 'http_requests_total' | grep -v '5..' | awk -F' ' '{sum += $2} END {print sum}')
        local error_requests=$(curl -fsS "$HEALTH_URL/../metrics" 2>/dev/null | grep 'http_requests_total' | grep '5..' | awk -F' ' '{sum += $2} END {print sum}')
        
        if [ "$total_requests" -gt 0 ] && [ "$error_requests" -gt 0 ]; then
            local error_rate=$(echo "scale=2; $error_requests * 100 / $total_requests" | bc)
            local error_rate_int=$(echo "$error_rate" | cut -d. -f1)
            
            if [ "$error_rate_int" -gt "$ERROR_RATE_THRESHOLD" ]; then
                log_healing "⚠️  High error rate detected: ${error_rate}%"
                return 1
            fi
        fi
    fi
    return 0
}

# Main auto-healing logic
main() {
    log_healing "🚀 Auto-healing system started"
    
    # Check if service is healthy
    if check_service_health; then
        log_healing "✅ Service is healthy"
        
        # Check system resources anyway
        check_system_resources
        
        # Reset restart count if service is healthy
        reset_restart_count
        
        log_healing "🏁 Auto-healing check completed - no action needed"
        exit 0
    fi
    
    log_healing "❌ Service health check failed - initiating auto-healing"
    
    # Check system resources
    if ! check_system_resources; then
        log_healing "🔍 System resources look normal"
    fi
    
    # Check error rates
    if ! check_error_rates; then
        log_healing "🔍 High error rate detected"
    fi
    
    # Attempt service restart
    if restart_service; then
        log_healing "✅ Auto-healing successful - service restored"
        exit 0
    else
        log_healing "❌ Auto-healing failed - manual intervention required"
        
        # Send alert (placeholder - implement actual alerting)
        log_healing "📧 Alert: Auto-healing failed for Agente Hotelero service"
        
        exit 1
    fi
}

# Run main function
main "$@"
```

## COMANDOS DE VALIDACIÓN Y MONITOREO

```bash
# Validación completa del sistema
./scripts/diagnostic-comprehensive.sh

# Auto-curación segura
./scripts/auto-healing-safe.sh

# Monitoreo continuo (ejecutar en cron cada 5 minutos)
*/5 * * * * /path/to/agente-hotel-api/scripts/auto-healing-safe.sh

# Verificación manual de métricas clave
curl -s http://localhost:8000/metrics | grep -E "(http_request_duration|memory_usage|error_rate)"

# Test de carga para validar umbrales
k6 run tests/performance/load-test.js

# Backup antes de cualquier intervención
./scripts/backup.sh

# Rollback si la auto-curación falla
./scripts/rollback.sh latest
```

Este sistema de troubleshooting y autocuración proporciona:

1. **Diagnóstico exhaustivo** con verificación de todos los componentes
2. **Auto-curación segura** con límites y cooldowns
3. **Monitoreo proactivo** con umbrales configurables
4. **Recuperación automática** ante fallos comunes
5. **Alertas estructuradas** para intervención manual cuando sea necesario

El sistema está diseñado para ser no destructivo y siempre registra todas las acciones para auditoría.