#!/bin/bash
# Script de monitoreo sintético para health checks externos
# Úsalo desde cron o sistemas de monitoreo externos

set -euo pipefail

# Configuración
BASE_URL="${HEALTH_CHECK_URL:-http://localhost:8000}"
TIMEOUT="${TIMEOUT:-10}"
MAX_RETRIES="${MAX_RETRIES:-3}"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"

# GUARDRAILS: Cargar configuración central si está disponible
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/guardrails.conf" ]]; then
    source "$SCRIPT_DIR/guardrails.conf"
    ABSOLUTE_MAX_RETRIES=${HEALTH_CHECK_MAX_RETRIES:-10}
    ABSOLUTE_MAX_TIMEOUT=${HEALTH_CHECK_MAX_TIMEOUT:-60}
    RATE_LIMIT_DELAY=${HEALTH_CHECK_RATE_LIMIT:-1}
else
    # Fallback values si no existe configuración central
    ABSOLUTE_MAX_RETRIES=10   # Límite duro sin importar configuración
    ABSOLUTE_MAX_TIMEOUT=60   # Timeout máximo en segundos
    RATE_LIMIT_DELAY=1        # Delay mínimo entre requests (segundos)
fi

# Aplicar guardrails
if [[ $MAX_RETRIES -gt $ABSOLUTE_MAX_RETRIES ]]; then
    log "WARN" "MAX_RETRIES limitado a $ABSOLUTE_MAX_RETRIES (era $MAX_RETRIES)"
    MAX_RETRIES=$ABSOLUTE_MAX_RETRIES
fi

if [[ $TIMEOUT -gt $ABSOLUTE_MAX_TIMEOUT ]]; then
    log "WARN" "TIMEOUT limitado a $ABSOLUTE_MAX_TIMEOUT (era $TIMEOUT)"
    TIMEOUT=$ABSOLUTE_MAX_TIMEOUT
fi

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "$(date -Iseconds) [$1] $2"
}

send_alert() {
    local status="$1"
    local message="$2"
    
    # GUARDRAIL: Circuit breaker simple para alertas
    local alert_lockfile="/tmp/agente-health-alert.lock"
    local alert_cooldown=${HEALTH_CHECK_ALERT_COOLDOWN:-300}  # Desde guardrails.conf
    
    if [[ -f "$alert_lockfile" ]]; then
        local last_alert=$(stat -c %Y "$alert_lockfile" 2>/dev/null || echo 0)
        local current_time=$(date +%s)
        local time_diff=$((current_time - last_alert))
        
        if [[ $time_diff -lt $alert_cooldown ]]; then
            log "INFO" "Alert rate-limited (cooldown: $((alert_cooldown - time_diff))s remaining)"
            return 0
        fi
    fi
    
    if [[ -n "$SLACK_WEBHOOK" ]]; then
        if curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚨 Agente Hotel Health Check: $status\\n$message\"}" \
            "$SLACK_WEBHOOK" >/dev/null 2>&1; then
            # Actualizar lockfile solo si el alert se envió exitosamente
            touch "$alert_lockfile"
        fi
    fi
}

check_endpoint() {
    local endpoint="$1"
    local description="$2"
    local retry_count=0
    
    while [[ $retry_count -lt $MAX_RETRIES ]]; do
        if curl -fsSL --max-time "$TIMEOUT" "$BASE_URL$endpoint" >/dev/null 2>&1; then
            log "INFO" "${GREEN}✓${NC} $description"
            return 0
        fi
        
        ((retry_count++))
        if [[ $retry_count -lt $MAX_RETRIES ]]; then
            log "WARN" "${YELLOW}⚠${NC} $description - Retry $retry_count/$MAX_RETRIES"
            # GUARDRAIL: Exponential backoff + rate limiting
            local backoff_delay=$((RATE_LIMIT_DELAY * retry_count))
            sleep $backoff_delay
        fi
    done
    
    log "ERROR" "${RED}✗${NC} $description - FAILED after $MAX_RETRIES attempts"
    return 1
}

main() {
    log "INFO" "Starting synthetic health checks for $BASE_URL"
    
    local failed_checks=0
    
    # Liveness check (crítico)
    if ! check_endpoint "/health/live" "Liveness check"; then
        ((failed_checks++))
        send_alert "CRITICAL" "Liveness check failed - service may be down"
    fi
    
    # Readiness check (importante pero no crítico)
    if ! check_endpoint "/health/ready" "Readiness check"; then
        ((failed_checks++))
        send_alert "WARNING" "Readiness check failed - dependencies may be unhealthy"
    fi
    
    # Metrics endpoint (opcional)
    if ! check_endpoint "/metrics" "Metrics endpoint"; then
        log "WARN" "${YELLOW}⚠${NC} Metrics endpoint failed (non-critical)"
    fi
    
    # Resumen
    if [[ $failed_checks -eq 0 ]]; then
        log "INFO" "${GREEN}✓${NC} All critical health checks passed"
        exit 0
    else
        log "ERROR" "${RED}✗${NC} $failed_checks critical health checks failed"
        exit 1
    fi
}

# Help
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    cat <<EOF
Synthetic Health Monitor for Agente Hotel API

Usage: $0 [options]

Environment Variables:
  HEALTH_CHECK_URL    Base URL to check (default: http://localhost:8000)
  TIMEOUT            Request timeout in seconds (default: 10)
  MAX_RETRIES        Maximum retry attempts (default: 3)
  SLACK_WEBHOOK      Slack webhook URL for alerts (optional)

Examples:
  # Check local development
  $0
  
  # Check production with alerts
  HEALTH_CHECK_URL=https://api.hotel.com SLACK_WEBHOOK=https://hooks.slack.com/... $0
  
  # Quick check with short timeout
  TIMEOUT=5 MAX_RETRIES=1 $0

Exit codes:
  0  All critical checks passed
  1  One or more critical checks failed
EOF
    exit 0
fi

main "$@"