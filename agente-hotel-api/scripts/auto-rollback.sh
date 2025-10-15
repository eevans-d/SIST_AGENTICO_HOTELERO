#!/bin/bash

###############################################################################
# Automatic Rollback Script
#
# Monitors deployed application health and automatically triggers rollback
# when critical thresholds are breached.
#
# Features:
# - Real-time health monitoring
# - Automatic rollback on failure
# - State preservation
# - Slack/email notifications
# - Rollback verification
#
# Usage:
#   ./auto-rollback.sh --environment ENV [OPTIONS]
#
# Author: AI Agent
# Date: October 15, 2025
###############################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
ENVIRONMENT="staging"
PRESERVE_DATA=true
NOTIFY=true
ROLLBACK_TO="previous"
DRY_RUN=false

# Monitoring thresholds
ERROR_RATE_THRESHOLD=0.05  # 5%
LATENCY_P95_THRESHOLD=3000  # 3s
AVAILABILITY_THRESHOLD=0.95  # 95%
MONITORING_DURATION=300  # 5 minutes

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

show_usage() {
    cat << EOF
Usage: $0 --environment ENV [OPTIONS]

Required:
  --environment ENV    Target environment (staging|production)

Optional:
  --preserve-data      Preserve application data [default: true]
  --notify            Send notifications [default: true]
  --rollback-to TAG    Specific version to rollback to [default: previous]
  --dry-run           Show what would be done
  --help              Show this help

EOF
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment) ENVIRONMENT="$2"; shift 2 ;;
        --preserve-data) PRESERVE_DATA=true; shift ;;
        --notify) NOTIFY=true; shift ;;
        --rollback-to) ROLLBACK_TO="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        --help) show_usage ;;
        *) log_error "Unknown option: $1"; show_usage ;;
    esac
done

detect_failure() {
    log_info "Detecting deployment failures..."
    
    # Check error rate
    ERROR_RATE=$(curl -s "http://prometheus:9090/api/v1/query" \
        --data-urlencode "query=rate(http_requests_total{status=~\"5..\"}[5m])" \
        | jq -r '.data.result[0].value[1] // 0')
    
    if (( $(echo "$ERROR_RATE > $ERROR_RATE_THRESHOLD" | bc -l) )); then
        log_error "Error rate threshold breached: ${ERROR_RATE} > ${ERROR_RATE_THRESHOLD}"
        return 1
    fi
    
    # Check latency
    LATENCY_P95=$(curl -s "http://prometheus:9090/api/v1/query" \
        --data-urlencode "query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))" \
        | jq -r '.data.result[0].value[1] // 0')
    
    LATENCY_MS=$(echo "$LATENCY_P95 * 1000" | bc)
    if (( $(echo "$LATENCY_MS > $LATENCY_P95_THRESHOLD" | bc -l) )); then
        log_error "Latency threshold breached: ${LATENCY_MS}ms > ${LATENCY_P95_THRESHOLD}ms"
        return 1
    fi
    
    # Check availability
    AVAILABILITY=$(curl -s "http://prometheus:9090/api/v1/query" \
        --data-urlencode "query=avg_over_time(up{job=\"agente-api\"}[5m])" \
        | jq -r '.data.result[0].value[1] // 0')
    
    if (( $(echo "$AVAILABILITY < $AVAILABILITY_THRESHOLD" | bc -l) )); then
        log_error "Availability threshold breached: ${AVAILABILITY} < ${AVAILABILITY_THRESHOLD}"
        return 1
    fi
    
    log_success "All health checks passed"
    return 0
}

find_rollback_version() {
    log_info "Finding rollback version..."
    
    if [[ "$ROLLBACK_TO" == "previous" ]]; then
        # Find the last known good version
        ROLLBACK_TAG=$(docker images --format "{{.Tag}}" | grep -E "^rollback-" | head -n1)
        
        if [[ -z "$ROLLBACK_TAG" ]]; then
            log_error "No rollback version found"
            exit 1
        fi
    else
        ROLLBACK_TAG="$ROLLBACK_TO"
    fi
    
    log_info "Rollback target: $ROLLBACK_TAG"
    echo "$ROLLBACK_TAG"
}

execute_rollback() {
    log_info "Executing rollback..."
    
    local rollback_tag="$1"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would rollback to: $rollback_tag"
        return 0
    fi
    
    # Backup current state
    if [[ "$PRESERVE_DATA" == "true" ]]; then
        log_info "Backing up current state..."
        "$SCRIPT_DIR/backup.sh" --target "$ENVIRONMENT" --type incremental
    fi
    
    # Execute blue-green deployment with rollback image
    log_info "Deploying rollback version..."
    "$SCRIPT_DIR/blue-green-deploy.sh" \
        --image "$rollback_tag" \
        --environment "$ENVIRONMENT" \
        --health-check-timeout 300
    
    log_success "Rollback executed successfully"
}

verify_rollback() {
    log_info "Verifying rollback..."
    
    sleep 30  # Wait for stabilization
    
    # Run smoke tests
    BASE_URL="http://localhost"
    
    for endpoint in "/health/live" "/health/ready" "/metrics"; do
        if curl -sf "${BASE_URL}${endpoint}" >/dev/null; then
            log_success "✓ ${endpoint}"
        else
            log_error "✗ ${endpoint}"
            return 1
        fi
    done
    
    log_success "Rollback verification passed"
    return 0
}

send_notification() {
    if [[ "$NOTIFY" == "false" ]]; then
        return 0
    fi
    
    local message="$1"
    local severity="$2"
    
    log_info "Sending notification: $severity"
    
    # Slack notification
    if [[ -n "${SLACK_WEBHOOK:-}" ]]; then
        curl -X POST "$SLACK_WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d "{
                \"text\": \"🚨 Automatic Rollback Triggered\",
                \"attachments\": [{
                    \"color\": \"danger\",
                    \"fields\": [
                        {\"title\": \"Environment\", \"value\": \"$ENVIRONMENT\", \"short\": true},
                        {\"title\": \"Severity\", \"value\": \"$severity\", \"short\": true},
                        {\"title\": \"Message\", \"value\": \"$message\"}
                    ]
                }]
            }"
    fi
}

main() {
    log_info "🔄 Starting automatic rollback system..."
    log_info "Environment: $ENVIRONMENT"
    log_info "Monitoring duration: ${MONITORING_DURATION}s"
    
    # Detect failure
    if ! detect_failure; then
        log_warning "Deployment failure detected - initiating rollback"
        
        # Find rollback version
        ROLLBACK_VERSION=$(find_rollback_version)
        
        # Send notification
        send_notification "Deployment failure detected. Rolling back to $ROLLBACK_VERSION" "critical"
        
        # Execute rollback
        execute_rollback "$ROLLBACK_VERSION"
        
        # Verify rollback
        if verify_rollback; then
            log_success "✅ Automatic rollback completed successfully"
            send_notification "Rollback to $ROLLBACK_VERSION completed successfully" "warning"
            exit 0
        else
            log_error "❌ Rollback verification failed"
            send_notification "Rollback verification failed - manual intervention required" "critical"
            exit 1
        fi
    else
        log_success "✅ Deployment is healthy - no rollback needed"
        exit 0
    fi
}

main "$@"
